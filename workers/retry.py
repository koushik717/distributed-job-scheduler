"""
Retry logic with exponential backoff and dead letter queue.

When a job fails:
  1. Increment retry_count
  2. If retries exhausted → move to DEAD (dead letter queue)
  3. If retries remain → calculate exponential backoff delay,
     set next_retry_at, mark as FAILED

The scheduler (scheduler.py) periodically polls for FAILED jobs
whose next_retry_at has passed, and re-enqueues them.
"""

import logging
from django.utils import timezone
from datetime import timedelta

from metrics.prometheus import track_retry, track_dead_letter

logger = logging.getLogger('workers')


def calculate_backoff(retry_count: int, base: int = 2, max_delay: int = 300) -> int:
    """
    Calculate exponential backoff delay in seconds.

    delay = min(base ^ retry_count, max_delay)

    Examples:
        retry_count=0 → 1s (base^0)
        retry_count=1 → 2s
        retry_count=2 → 4s
        retry_count=3 → 8s
        retry_count=4 → 16s
        retry_count=5 → 32s
        ...capped at max_delay (300s = 5 min)
    """
    delay = min(base ** retry_count, max_delay)
    return delay


def handle_failure(job, exception: Exception):
    """
    Handle a job failure:
      - Increment retry count
      - Decide: retry with backoff OR dead letter
      - Update job in PostgreSQL
    """
    from jobs.models import JobStatus

    job.retry_count += 1
    job.error_message = str(exception)[:2000]  # Truncate long errors

    if job.retry_count >= job.max_retries:
        # ── Dead Letter Queue ──────────────────────────────
        job.status = JobStatus.DEAD
        job.completed_at = timezone.now()
        job.save(update_fields=[
            'status', 'retry_count', 'error_message',
            'completed_at', 'updated_at',
        ])

        track_dead_letter(job.type)
        logger.error(
            f"Job {job.id} → DEAD LETTER QUEUE "
            f"(retries exhausted: {job.retry_count}/{job.max_retries}) "
            f"error: {exception}"
        )

    else:
        # ── Retry with exponential backoff ─────────────────
        delay = calculate_backoff(job.retry_count)
        job.status = JobStatus.FAILED
        job.next_retry_at = timezone.now() + timedelta(seconds=delay)
        job.worker_id = None
        job.started_at = None
        job.save(update_fields=[
            'status', 'retry_count', 'error_message',
            'next_retry_at', 'worker_id', 'started_at', 'updated_at',
        ])

        track_retry(job.type)
        logger.info(
            f"Job {job.id} → FAILED, will retry in {delay}s "
            f"(attempt {job.retry_count}/{job.max_retries}) "
            f"next_retry_at={job.next_retry_at.isoformat()}"
        )
