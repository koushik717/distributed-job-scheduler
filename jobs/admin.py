"""
Django admin configuration for Job model.
"""

from django.contrib import admin
from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'type', 'status', 'priority', 'retry_count',
        'max_retries', 'created_at', 'updated_at',
    ]
    list_filter = ['status', 'type', 'priority']
    search_fields = ['id', 'type', 'idempotency_key']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'started_at',
        'completed_at', 'worker_id', 'duration_seconds',
    ]
    ordering = ['priority', '-created_at']
