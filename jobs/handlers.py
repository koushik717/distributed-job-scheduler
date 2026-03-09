"""
Job handler registry — maps job types to handler functions.

Each handler receives the job's payload dict and returns a result dict.
Handlers simulate real work with configurable delays and failure rates.
"""

import time
import random
import logging

logger = logging.getLogger('jobs')


def handle_send_email(payload: dict) -> dict:
    """Simulate sending an email."""
    to = payload.get('to', 'unknown@example.com')
    subject = payload.get('subject', 'No Subject')

    # Simulate API call latency
    time.sleep(random.uniform(0.5, 2.0))

    # 10% failure rate to demonstrate retry logic
    if random.random() < 0.10:
        raise Exception(f"SMTP connection timeout sending to {to}")

    logger.info(f"Email sent to {to}: {subject}")
    return {'sent_to': to, 'subject': subject, 'status': 'delivered'}


def handle_generate_report(payload: dict) -> dict:
    """Simulate generating a report — longer running task."""
    report_type = payload.get('report_type', 'summary')
    date_range = payload.get('date_range', 'last_30_days')

    # Reports take longer
    time.sleep(random.uniform(2.0, 5.0))

    # 5% failure rate
    if random.random() < 0.05:
        raise Exception(f"Database query timeout generating {report_type} report")

    row_count = random.randint(100, 10000)
    logger.info(f"Report generated: {report_type} ({row_count} rows)")
    return {
        'report_type': report_type,
        'date_range': date_range,
        'row_count': row_count,
        'file_url': f'/reports/{report_type}_{date_range}.pdf',
    }


def handle_process_data(payload: dict) -> dict:
    """Simulate a data processing pipeline."""
    source = payload.get('source', 'unknown')
    batch_size = payload.get('batch_size', 100)

    # Processing time scales with batch size
    time.sleep(random.uniform(1.0, 3.0))

    # 15% failure rate — data processing can be flaky
    if random.random() < 0.15:
        raise Exception(f"Data validation error in batch from {source}")

    records_processed = random.randint(
        int(batch_size * 0.8),
        batch_size
    )
    logger.info(f"Processed {records_processed}/{batch_size} records from {source}")
    return {
        'source': source,
        'records_processed': records_processed,
        'records_total': batch_size,
        'processing_rate': f'{records_processed / 2.0:.1f} records/sec',
    }


def handle_cleanup(payload: dict) -> dict:
    """Simulate a cleanup/maintenance task."""
    target = payload.get('target', 'temp_files')
    older_than_days = payload.get('older_than_days', 30)

    time.sleep(random.uniform(0.3, 1.5))

    # 2% failure rate — cleanup is usually reliable
    if random.random() < 0.02:
        raise Exception(f"Permission denied cleaning {target}")

    items_removed = random.randint(0, 500)
    space_freed_mb = round(items_removed * random.uniform(0.1, 5.0), 2)
    logger.info(f"Cleanup: removed {items_removed} items from {target}")
    return {
        'target': target,
        'items_removed': items_removed,
        'space_freed_mb': space_freed_mb,
    }


def handle_webhook(payload: dict) -> dict:
    """Simulate sending a webhook notification."""
    url = payload.get('url', 'https://example.com/webhook')
    event = payload.get('event', 'unknown')

    time.sleep(random.uniform(0.2, 1.0))

    # 8% failure rate — external APIs can be unreliable
    if random.random() < 0.08:
        raise Exception(f"HTTP 503 from webhook endpoint {url}")

    logger.info(f"Webhook delivered: {event} → {url}")
    return {'url': url, 'event': event, 'status_code': 200}


def handle_image_resize(payload: dict) -> dict:
    """Simulate image processing."""
    image_id = payload.get('image_id', 'unknown')
    dimensions = payload.get('dimensions', '800x600')

    time.sleep(random.uniform(1.0, 4.0))

    # 3% failure rate
    if random.random() < 0.03:
        raise Exception(f"Corrupt image data for {image_id}")

    logger.info(f"Image resized: {image_id} → {dimensions}")
    return {
        'image_id': image_id,
        'dimensions': dimensions,
        'output_url': f'/images/{image_id}_{dimensions}.webp',
    }


# ─── Handler Registry ───────────────────────────────────────
# Maps job type strings to handler functions.
# This is the single source of truth for available job types.
HANDLER_REGISTRY = {
    'send_email': handle_send_email,
    'generate_report': handle_generate_report,
    'process_data': handle_process_data,
    'cleanup': handle_cleanup,
    'webhook': handle_webhook,
    'image_resize': handle_image_resize,
}
