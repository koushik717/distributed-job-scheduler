"""
Prometheus metrics for the Job Scheduler.

Tracks:
  - jobs_submitted_total   — Counter by type and queue
  - jobs_started_total     — Counter by type
  - jobs_completed_total   — Counter by type
  - jobs_failed_total      — Counter by type
  - job_duration_seconds   — Histogram by type
  - jobs_retried_total     — Counter by type
  - jobs_dead_letter_total — Counter by type
"""

from prometheus_client import Counter, Histogram, Gauge

# ─── Counters ────────────────────────────────────────────────

jobs_submitted_total = Counter(
    'jobs_submitted_total',
    'Total number of jobs submitted',
    ['job_type', 'queue'],
)

jobs_started_total = Counter(
    'jobs_started_total',
    'Total number of jobs that started execution',
    ['job_type'],
)

jobs_completed_total = Counter(
    'jobs_completed_total',
    'Total number of jobs completed successfully',
    ['job_type'],
)

jobs_failed_total = Counter(
    'jobs_failed_total',
    'Total number of job failures (including retries)',
    ['job_type'],
)

jobs_retried_total = Counter(
    'jobs_retried_total',
    'Total number of job retries',
    ['job_type'],
)

jobs_dead_letter_total = Counter(
    'jobs_dead_letter_total',
    'Total number of jobs sent to dead letter queue',
    ['job_type'],
)

# ─── Histogram ───────────────────────────────────────────────

job_duration_seconds = Histogram(
    'job_duration_seconds',
    'Time spent processing a job',
    ['job_type'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)


# ─── Helper functions ────────────────────────────────────────

def track_job_submitted(job_type: str, queue: str):
    jobs_submitted_total.labels(job_type=job_type, queue=queue).inc()


def track_job_started(job_type: str):
    jobs_started_total.labels(job_type=job_type).inc()


def track_job_completed(job_type: str):
    jobs_completed_total.labels(job_type=job_type).inc()


def track_job_failed(job_type: str):
    jobs_failed_total.labels(job_type=job_type).inc()


def track_retry(job_type: str):
    jobs_retried_total.labels(job_type=job_type).inc()


def track_dead_letter(job_type: str):
    jobs_dead_letter_total.labels(job_type=job_type).inc()


def observe_job_duration(job_type: str, duration: float):
    job_duration_seconds.labels(job_type=job_type).observe(duration)
