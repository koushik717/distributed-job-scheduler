"""
Job model — PostgreSQL is the source of truth for all job state.
Redis/Celery is only the transport layer.
"""

import uuid
from django.db import models
from django.utils import timezone


class JobStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SCHEDULED = 'SCHEDULED', 'Scheduled'
    RUNNING = 'RUNNING', 'Running'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'
    DEAD = 'DEAD', 'Dead (DLQ)'
    CANCELLED = 'CANCELLED', 'Cancelled'


class Job(models.Model):
    """
    Core Job model. Every field serves a purpose:

    - id: UUID primary key (no sequential IDs leaked)
    - type: maps to a handler in the registry
    - payload: arbitrary JSON data for the handler
    - priority: 1 (highest) to 10 (lowest) — routes to queues
    - status: finite state machine (PENDING → RUNNING → COMPLETED/FAILED/DEAD)
    - idempotency_key: prevent duplicate job submissions (Stripe-level pattern)
    - run_at: optional scheduled execution time
    - retry_count / max_retries: exponential backoff tracking
    - next_retry_at: calculated backoff timestamp
    - worker_id: which worker is/was processing this job
    - error_message: last failure detail
    - result: handler return value on success
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Job definition
    type = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    priority = models.IntegerField(
        default=5,
        help_text='1 = highest priority, 10 = lowest priority'
    )

    # State
    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        db_index=True,
    )

    # Idempotency
    idempotency_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        help_text='Unique key to prevent duplicate job submissions'
    )

    # Scheduling
    run_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='If set, job will not execute until this time'
    )

    # Retry tracking
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Execution details
    worker_id = models.CharField(max_length=255, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', '-created_at']
        indexes = [
            # Composite index for the scheduler polling query
            models.Index(
                fields=['status', 'next_retry_at'],
                name='idx_status_next_retry',
            ),
            models.Index(
                fields=['status', 'run_at'],
                name='idx_status_run_at',
            ),
            models.Index(
                fields=['status', 'priority', 'created_at'],
                name='idx_status_priority_created',
            ),
        ]

    def __str__(self):
        return f'Job({self.id.hex[:8]}) type={self.type} status={self.status}'

    @property
    def duration_seconds(self):
        """Calculate job processing duration if started and completed."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (timezone.now() - self.started_at).total_seconds()
        return None

    @property
    def queue_name(self):
        """Determine which Celery queue this job should be routed to."""
        if self.priority <= 3:
            return 'high_priority'
        elif self.priority <= 7:
            return 'default'
        else:
            return 'low_priority'
