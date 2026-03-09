#!/usr/bin/env python
"""
Seed script — creates a small batch of demo jobs for development.

Usage:
    python scripts/seed_jobs.py
"""

import json
import urllib.request

API_URL = 'http://localhost:8000/api/jobs/'

SEED_JOBS = [
    {
        'type': 'send_email',
        'payload': {'to': 'alice@acme.com', 'subject': 'Welcome to Acme!'},
        'priority': 1,
        'max_retries': 3,
        'idempotency_key': 'welcome-email-alice',
    },
    {
        'type': 'generate_report',
        'payload': {'report_type': 'quarterly', 'date_range': 'Q4_2025'},
        'priority': 5,
        'max_retries': 2,
    },
    {
        'type': 'process_data',
        'payload': {'source': 'user_events', 'batch_size': 1000},
        'priority': 3,
        'max_retries': 3,
    },
    {
        'type': 'cleanup',
        'payload': {'target': 'expired_sessions', 'older_than_days': 30},
        'priority': 9,
        'max_retries': 1,
    },
    {
        'type': 'webhook',
        'payload': {'url': 'https://hooks.slack.com/example', 'event': 'deploy.success'},
        'priority': 2,
        'max_retries': 5,
    },
    {
        'type': 'image_resize',
        'payload': {'image_id': 'avatar_042', 'dimensions': '256x256'},
        'priority': 7,
        'max_retries': 2,
    },
    {
        'type': 'send_email',
        'payload': {'to': 'bob@acme.com', 'subject': 'Invoice #1234'},
        'priority': 4,
        'max_retries': 3,
    },
    {
        'type': 'process_data',
        'payload': {'source': 'payment_logs', 'batch_size': 5000},
        'priority': 2,
        'max_retries': 3,
    },
]


def main():
    print(f"🌱 Seeding {len(SEED_JOBS)} demo jobs...\n")

    for i, job_data in enumerate(SEED_JOBS, 1):
        data = json.dumps(job_data).encode('utf-8')
        req = urllib.request.Request(
            API_URL,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                print(f"  [{i}] ✅ {job_data['type']} → {result['id'][:8]}... (priority={job_data['priority']})")
        except Exception as e:
            print(f"  [{i}] ❌ {job_data['type']} → {e}")

    print(f"\n✨ Seeding complete!")


if __name__ == '__main__':
    main()
