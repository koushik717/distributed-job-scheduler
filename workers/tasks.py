"""
Celery task definitions — the execution pipeline.

Flow: Celery receives task → fetch Job from PostgreSQL → execute handler →
update Job status in PostgreSQL.

Redis is ONLY transport. PostgreSQL is source of truth.
"""

import logging
import socket
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('workers')


@shared_task(
    bind=True,
    name='workers.tasks.execute_job',
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=0,  # We handle retries ourselves via the DB
)
def execute_job(self, job_id: str):
    """
    Execute a job by its UUID.

    This is the core task that Celery workers pull from the queue.
    All state transitions happen in PostgreSQL, not in Celery's
    result backend.
    """
    from jobs.models import Job, JobStatus
    from jobs.handlers import HANDLER_REGISTRY
    from workers.retry import handle_failure
    from metrics.prometheus import (
        track_job_started, track_job_completed,
        track_job_failed, observe_job_duration,
    )

    # ── Fetch job from PostgreSQL ──────────────────────────
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.error(f"Job {job_id} not found in database — skipping")
        return

    # Guard: only process PENDING or FAILED (retry) jobs
    if job.status not in [JobStatus.PENDING, JobStatus.FAILED, JobStatus.SCHEDULED]:
        logger.warning(
            f"Job {job_id} has status {job.status}, expected PENDING/FAILED/SCHEDULED — skipping"
        )
        return

    # ── Mark RUNNING ───────────────────────────────────────
    worker_id = f"{socket.gethostname()}-{self.request.id or 'unknown'}"
    job.status = JobStatus.RUNNING
    job.started_at = timezone.now()
    job.worker_id = worker_id
    job.save(update_fields=['status', 'started_at', 'worker_id', 'updated_at'])

    track_job_started(job.type)
    logger.info(f"Job {job_id} RUNNING on worker {worker_id} (type={job.type})")

    # ── Execute handler ────────────────────────────────────
    handler = HANDLER_REGISTRY.get(job.type)
    if not handler:
        job.status = JobStatus.DEAD
        job.error_message = f"No handler registered for type: {job.type}"
        job.completed_at = timezone.now()
        job.save(update_fields=[
            'status', 'error_message', 'completed_at', 'updated_at'
        ])
        logger.error(f"Job {job_id}: no handler for type={job.type}")
        return

    try:
        result = handler(job.payload)

        # ── Success → COMPLETED ────────────────────────────
        job.status = JobStatus.COMPLETED
        job.result = result
        job.completed_at = timezone.now()
        job.save(update_fields=[
            'status', 'result', 'completed_at', 'updated_at'
        ])

        duration = job.duration_seconds
        track_job_completed(job.type)
        if duration:
            observe_job_duration(job.type, duration)

        logger.info(
            f"Job {job_id} COMPLETED in {duration:.2f}s "
            f"(type={job.type}, worker={worker_id})"
        )

    except Exception as exc:
        # ── Failure → retry or dead letter ─────────────────
        logger.warning(
            f"Job {job_id} FAILED: {exc} "
            f"(retry {job.retry_count}/{job.max_retries})"
        )
        track_job_failed(job.type)
        handle_failure(job, exc)
