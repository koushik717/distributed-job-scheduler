"""
Prometheus metrics endpoint — exposes /metrics in Prometheus text format.
"""

from django.http import HttpResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


def metrics_view(request):
    """Expose Prometheus metrics at /metrics."""
    metrics_output = generate_latest()
    return HttpResponse(
        metrics_output,
        content_type=CONTENT_TYPE_LATEST,
    )
