"""
DRF serializers for the Job API.
"""

from rest_framework import serializers
from .models import Job, JobStatus


class JobSerializer(serializers.ModelSerializer):
    """Read serializer — full job representation."""
    duration_seconds = serializers.FloatField(read_only=True)
    queue_name = serializers.CharField(read_only=True)

    class Meta:
        model = Job
        fields = [
            'id', 'type', 'payload', 'priority', 'status',
            'idempotency_key', 'run_at',
            'retry_count', 'max_retries', 'next_retry_at',
            'worker_id', 'started_at', 'completed_at',
            'error_message', 'result',
            'duration_seconds', 'queue_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'retry_count', 'next_retry_at',
            'worker_id', 'started_at', 'completed_at',
            'error_message', 'result',
            'created_at', 'updated_at',
        ]


class JobCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer — validates job creation input.
    Handles idempotency: if a job with the same idempotency_key exists,
    returns the existing job instead of creating a duplicate.
    """

    class Meta:
        model = Job
        fields = [
            'type', 'payload', 'priority', 'max_retries',
            'idempotency_key', 'run_at',
        ]

    def validate_type(self, value):
        """Ensure the job type has a registered handler."""
        from .handlers import HANDLER_REGISTRY
        if value not in HANDLER_REGISTRY:
            available = ', '.join(HANDLER_REGISTRY.keys())
            raise serializers.ValidationError(
                f"Unknown job type '{value}'. Available types: {available}"
            )
        return value

    def validate_priority(self, value):
        if not 1 <= value <= 10:
            raise serializers.ValidationError(
                'Priority must be between 1 (highest) and 10 (lowest).'
            )
        return value

    def validate_max_retries(self, value):
        if value < 0 or value > 20:
            raise serializers.ValidationError(
                'max_retries must be between 0 and 20.'
            )
        return value

    def create(self, validated_data):
        """
        Create job with idempotency support.
        If idempotency_key is provided and a job with that key exists,
        return the existing job (Stripe-level pattern).
        """
        idempotency_key = validated_data.get('idempotency_key')

        if idempotency_key:
            existing = Job.objects.filter(
                idempotency_key=idempotency_key
            ).first()
            if existing:
                return existing

        # If run_at is set, mark as SCHEDULED instead of PENDING
        if validated_data.get('run_at'):
            validated_data['status'] = JobStatus.SCHEDULED

        return super().create(validated_data)


class JobStatsSerializer(serializers.Serializer):
    """Serializer for aggregate job statistics."""
    total_jobs = serializers.IntegerField()
    pending = serializers.IntegerField()
    scheduled = serializers.IntegerField()
    running = serializers.IntegerField()
    completed = serializers.IntegerField()
    failed = serializers.IntegerField()
    dead = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    success_rate = serializers.FloatField()
    failure_rate = serializers.FloatField()
    avg_duration_seconds = serializers.FloatField()
    queue_depth = serializers.DictField()
