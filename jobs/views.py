"""
REST API views for job management.
"""

import logging
from django.db.models import Avg, Count, Q, F
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import Job, JobStatus
from .serializers import JobSerializer, JobCreateSerializer, JobStatsSerializer
from metrics.prometheus import track_job_submitted

logger = logging.getLogger('jobs')


class JobViewSet(viewsets.ModelViewSet):
    """
    CRUD + custom actions for job management.

    Endpoints:
        GET    /api/jobs/            — List all jobs (with filters)
        POST   /api/jobs/            — Create a new job
        GET    /api/jobs/<id>/       — Retrieve a specific job
        POST   /api/jobs/<id>/cancel/ — Cancel a pending job
        POST   /api/jobs/<id>/retry/  — Retry a dead/failed job
        GET    /api/jobs/stats/      — Aggregate statistics
    """

    queryset = Job.objects.all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status', 'type', 'priority']
    ordering_fields = ['priority', 'created_at', 'updated_at', 'status']
    ordering = ['priority', '-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return JobCreateSerializer
        return JobSerializer

    def create(self, request, *args, **kwargs):
        """
        Create a new job:
        1. Validate input
        2. Check idempotency key
        3. Store in PostgreSQL (PENDING)
        4. Enqueue to Celery
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()

        # Check if this was an idempotent return (existing job)
        is_new = job.created_at >= timezone.now() - timezone.timedelta(seconds=2)

        if is_new and job.status != JobStatus.SCHEDULED:
            # Enqueue to Celery only for non-scheduled, new jobs
            self._enqueue_job(job)

        # Track metric
        track_job_submitted(job.type, job.queue_name)

        response_serializer = JobSerializer(job)
        status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK

        logger.info(
            f"Job {'created' if is_new else 'deduplicated'}: "
            f"id={job.id} type={job.type} priority={job.priority} "
            f"queue={job.queue_name}"
        )

        return Response(response_serializer.data, status=status_code)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending/scheduled job."""
        job = self.get_object()

        if job.status not in [JobStatus.PENDING, JobStatus.SCHEDULED]:
            return Response(
                {'error': f'Cannot cancel job with status {job.status}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job.status = JobStatus.CANCELLED
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'completed_at', 'updated_at'])

        logger.info(f"Job cancelled: id={job.id}")
        return Response(JobSerializer(job).data)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a dead or failed job — resets retry count and re-enqueues."""
        job = self.get_object()

        if job.status not in [JobStatus.DEAD, JobStatus.FAILED]:
            return Response(
                {'error': f'Cannot retry job with status {job.status}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job.status = JobStatus.PENDING
        job.retry_count = 0
        job.next_retry_at = None
        job.error_message = None
        job.worker_id = None
        job.started_at = None
        job.completed_at = None
        job.save(update_fields=[
            'status', 'retry_count', 'next_retry_at',
            'error_message', 'worker_id', 'started_at',
            'completed_at', 'updated_at',
        ])

        self._enqueue_job(job)

        logger.info(f"Job retried: id={job.id}")
        return Response(JobSerializer(job).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Aggregate job statistics for the dashboard.
        Returns counts by status, rates, avg duration, and queue depths.
        """
        qs = Job.objects.all()

        # Status counts
        status_counts = {}
        for s in JobStatus.values:
            status_counts[s.lower()] = qs.filter(status=s).count()

        total = qs.count()
        completed = status_counts.get('completed', 0)
        failed = status_counts.get('failed', 0)
        dead = status_counts.get('dead', 0)
        finished = completed + failed + dead

        # Success/failure rates
        success_rate = (completed / finished * 100) if finished > 0 else 0
        failure_rate = ((failed + dead) / finished * 100) if finished > 0 else 0

        # Average duration for completed jobs
        avg_duration = qs.filter(
            status=JobStatus.COMPLETED,
            started_at__isnull=False,
            completed_at__isnull=False,
        ).annotate(
            duration=F('completed_at') - F('started_at')
        ).aggregate(
            avg_dur=Avg('duration')
        )['avg_dur']

        avg_duration_seconds = (
            avg_duration.total_seconds() if avg_duration else 0
        )

        # Queue depth (pending/running by queue)
        queue_depth = {
            'high_priority': qs.filter(
                status__in=[JobStatus.PENDING, JobStatus.RUNNING],
                priority__lte=3
            ).count(),
            'default': qs.filter(
                status__in=[JobStatus.PENDING, JobStatus.RUNNING],
                priority__gt=3, priority__lte=7
            ).count(),
            'low_priority': qs.filter(
                status__in=[JobStatus.PENDING, JobStatus.RUNNING],
                priority__gt=7
            ).count(),
        }

        data = {
            'total_jobs': total,
            **status_counts,
            'success_rate': round(success_rate, 2),
            'failure_rate': round(failure_rate, 2),
            'avg_duration_seconds': round(avg_duration_seconds, 3),
            'queue_depth': queue_depth,
        }

        return Response(data)

    def _enqueue_job(self, job):
        """Push job to the appropriate Celery queue."""
        from workers.tasks import execute_job
        execute_job.apply_async(
            args=[str(job.id)],
            queue=job.queue_name,
        )
