"""
Celery application configuration for the Distributed Async Job Scheduler.

Celery is used as the task queue / broker layer. Redis is the transport,
but PostgreSQL remains the source of truth for all job state.
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scheduler.settings')

app = Celery('scheduler')

# Load config from Django settings, namespace='CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in installed apps
app.autodiscover_tasks(['workers'])

# ─── Periodic Tasks (Celery Beat) ────────────────────────────
app.conf.beat_schedule = {
    # Poll for scheduled jobs that are ready to run
    'enqueue-scheduled-jobs': {
        'task': 'workers.scheduler.enqueue_scheduled_jobs',
        'schedule': 10.0,  # Every 10 seconds
    },
    # Re-enqueue failed jobs that are past their retry backoff
    'retry-failed-jobs': {
        'task': 'workers.scheduler.retry_failed_jobs',
        'schedule': 15.0,  # Every 15 seconds
    },
    # Detect stale/timed-out RUNNING jobs
    'detect-stale-jobs': {
        'task': 'workers.scheduler.detect_stale_jobs',
        'schedule': 60.0,  # Every 60 seconds
    },
}
