"""
Background scheduler tasks — run by Celery Beat.

These periodic tasks handle:
1. Enqueuing scheduled jobs (run_at support)
2. Re-enqueuing failed jobs past their backoff window
3. Detecting stale/timed-out RUNNING jobs
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger('workers')


@shared_task(name='workers.scheduler.enqueue_scheduled_jobs')
def enqueue_scheduled_jobs():
    """
    Poll for SCHEDULED jobs whose run_at time has passed.
    Transition them to PENDING and enqueue to Celery.
    """
    from jobs.models import Job, JobStatus
    from workers.tasks import execute_job

    now = timezone.now()
    ready_jobs = Job.objects.filter(
        status=JobStatus.SCHEDULED,
        run_at__lte=now,
    ).select_for_update(skip_locked=True)

    count = 0
    for job in ready_jobs:
        job.status = JobStatus.PENDING
        job.save(update_fields=['status', 'updated_at'])

        execute_job.apply_async(
            args=[str(job.id)],
            queue=job.queue_name,
        )
        count += 1

    if count > 0:
        logger.info(f"Scheduler: enqueued {count} scheduled jobs")


@shared_task(name='workers.scheduler.retry_failed_jobs')
def retry_failed_jobs():
    """
    Poll for FAILED jobs whose next_retry_at has passed.
    Re-enqueue them to Celery for another attempt.
    """
    from jobs.models import Job, JobStatus
    from workers.tasks import execute_job

    now = timezone.now()
    retry_jobs = Job.objects.filter(
        status=JobStatus.FAILED,
        next_retry_at__lte=now,
    ).select_for_update(skip_locked=True)

    count = 0
    for job in retry_jobs:
        execute_job.apply_async(
            args=[str(job.id)],
            queue=job.queue_name,
        )
        count += 1

    if count > 0:
        logger.info(f"Scheduler: re-enqueued {count} failed jobs for retry")


@shared_task(name='workers.scheduler.detect_stale_jobs')
def detect_stale_jobs():
    """
    Detect RUNNING jobs that have exceeded the timeout threshold.
    This handles the case where a worker crashes mid-execution.

    Mark them as FAILED so the retry logic can pick them up.
    """
    from jobs.models import Job, JobStatus

    timeout_seconds = getattr(settings, 'JOB_TIMEOUT_SECONDS', 1800)
    cutoff = timezone.now() - timezone.timedelta(seconds=timeout_seconds)

    stale_jobs = Job.objects.filter(
        status=JobStatus.RUNNING,
        started_at__lt=cutoff,
    )

    count = 0
    for job in stale_jobs:
        job.status = JobStatus.FAILED
        job.error_message = (
            f"Job timed out after {timeout_seconds}s "
            f"(worker may have crashed: {job.worker_id})"
        )
        job.worker_id = None
        job.started_at = None

        # Set up for retry if retries remain
        if job.retry_count < job.max_retries:
            from workers.retry import calculate_backoff
            delay = calculate_backoff(job.retry_count)
            job.next_retry_at = timezone.now() + timezone.timedelta(seconds=delay)
            job.retry_count += 1
        else:
            job.status = 'DEAD'
            job.completed_at = timezone.now()

        job.save()
        count += 1

    if count > 0:
        logger.warning(f"Scheduler: detected {count} stale/timed-out jobs")
