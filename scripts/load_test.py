#!/usr/bin/env python
"""
Load test script — submits 10,000 jobs to the scheduler API
and reports throughput, success rate, and processing time.

Usage:
    python scripts/load_test.py --jobs 10000 --concurrency 50
    python scripts/load_test.py --jobs 100 --concurrency 10  # Quick test
"""

import argparse
import json
import random
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

API_URL = 'http://localhost:8000/api/jobs/'

JOB_TEMPLATES = [
    {
        'type': 'send_email',
        'payload': {'to': 'user@example.com', 'subject': 'Test Email'},
        'priority': 2,
        'max_retries': 3,
    },
    {
        'type': 'generate_report',
        'payload': {'report_type': 'monthly', 'date_range': 'last_30_days'},
        'priority': 5,
        'max_retries': 2,
    },
    {
        'type': 'process_data',
        'payload': {'source': 'api_events', 'batch_size': 500},
        'priority': 4,
        'max_retries': 3,
    },
    {
        'type': 'cleanup',
        'payload': {'target': 'temp_files', 'older_than_days': 7},
        'priority': 8,
        'max_retries': 1,
    },
    {
        'type': 'webhook',
        'payload': {'url': 'https://hooks.example.com/event', 'event': 'order.created'},
        'priority': 3,
        'max_retries': 5,
    },
    {
        'type': 'image_resize',
        'payload': {'image_id': 'img_001', 'dimensions': '1200x800'},
        'priority': 6,
        'max_retries': 2,
    },
]


def submit_job(job_index: int) -> dict:
    """Submit a single job and return timing info."""
    template = random.choice(JOB_TEMPLATES)
    job_data = {
        **template,
        'payload': {
            **template['payload'],
            'batch_id': job_index,
        },
        'priority': random.randint(1, 10),
    }

    start = time.time()
    data = json.dumps(job_data).encode('utf-8')
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            elapsed = time.time() - start
            response_data = json.loads(resp.read().decode('utf-8'))
            return {
                'success': True,
                'elapsed': elapsed,
                'job_id': response_data.get('id'),
                'status_code': resp.status,
            }
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        return {
            'success': False,
            'elapsed': elapsed,
            'error': f'HTTP {e.code}: {e.reason}',
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            'success': False,
            'elapsed': elapsed,
            'error': str(e),
        }


def wait_for_completion(timeout: int = 300, poll_interval: int = 5) -> dict:
    """Poll the stats endpoint until all jobs are processed or timeout."""
    print("\n⏳ Waiting for jobs to complete...")
    start = time.time()

    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(
                f'{API_URL}stats/',
                headers={'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                stats = json.loads(resp.read().decode('utf-8'))

            pending = stats.get('pending', 0)
            running = stats.get('running', 0)
            scheduled = stats.get('scheduled', 0)
            in_progress = pending + running + scheduled

            if in_progress == 0:
                return stats

            elapsed = time.time() - start
            print(
                f"  [{elapsed:.0f}s] "
                f"pending={pending} running={running} "
                f"completed={stats.get('completed', 0)} "
                f"failed={stats.get('failed', 0)} "
                f"dead={stats.get('dead', 0)}"
            )
        except Exception:
            pass

        time.sleep(poll_interval)

    # Timeout — return current stats
    try:
        req = urllib.request.Request(f'{API_URL}stats/')
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return {}


def main():
    parser = argparse.ArgumentParser(description='Load test the Job Scheduler')
    parser.add_argument('--jobs', type=int, default=10000, help='Number of jobs to submit')
    parser.add_argument('--concurrency', type=int, default=50, help='Max concurrent submissions')
    parser.add_argument('--wait', action='store_true', default=True, help='Wait for completion')
    parser.add_argument('--timeout', type=int, default=600, help='Wait timeout in seconds')
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════╗
║       🚀 Job Scheduler Load Test                ║
╠══════════════════════════════════════════════════╣
║  Jobs:        {args.jobs:<10}                     ║
║  Concurrency: {args.concurrency:<10}                     ║
║  API URL:     {API_URL:<33}║
╚══════════════════════════════════════════════════╝
    """)

    # ── Submit Jobs ────────────────────────────────────────
    print(f"📤 Submitting {args.jobs} jobs with {args.concurrency} concurrent threads...")
    submit_start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(submit_job, i): i
            for i in range(args.jobs)
        }

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1

            if completed % 500 == 0:
                print(f"  Submitted {completed}/{args.jobs} jobs...")

    submit_elapsed = time.time() - submit_start

    # ── Submission Stats ───────────────────────────────────
    successes = [r for r in results if r['success']]
    failures = [r for r in results if not r['success']]
    latencies = [r['elapsed'] for r in successes]

    print(f"\n{'─' * 50}")
    print(f"📊 Submission Results:")
    print(f"  Total submitted:    {len(results)}")
    print(f"  Successful:         {len(successes)}")
    print(f"  Failed to submit:   {len(failures)}")
    print(f"  Submit throughput:  {len(successes) / submit_elapsed:.1f} jobs/sec")
    print(f"  Total submit time:  {submit_elapsed:.2f}s")
    if latencies:
        print(f"  Avg latency (API):  {sum(latencies) / len(latencies) * 1000:.1f}ms")
        print(f"  P95 latency (API):  {sorted(latencies)[int(len(latencies) * 0.95)] * 1000:.1f}ms")
        print(f"  P99 latency (API):  {sorted(latencies)[int(len(latencies) * 0.99)] * 1000:.1f}ms")

    if failures:
        print(f"\n  ⚠️  Failed submissions:")
        for f in failures[:5]:
            print(f"    - {f['error']}")

    # ── Wait for Processing ────────────────────────────────
    if args.wait:
        final_stats = wait_for_completion(timeout=args.timeout)

        if final_stats:
            print(f"\n{'═' * 50}")
            print(f"🏁 Final Results:")
            print(f"  Total jobs:         {final_stats.get('total_jobs', 'N/A')}")
            print(f"  Completed:          {final_stats.get('completed', 'N/A')}")
            print(f"  Failed:             {final_stats.get('failed', 'N/A')}")
            print(f"  Dead (DLQ):         {final_stats.get('dead', 'N/A')}")
            print(f"  Success rate:       {final_stats.get('success_rate', 'N/A')}%")
            print(f"  Failure rate:       {final_stats.get('failure_rate', 'N/A')}%")
            print(f"  Avg duration:       {final_stats.get('avg_duration_seconds', 'N/A')}s")
            print(f"  Queue depth:        {final_stats.get('queue_depth', 'N/A')}")
            print(f"{'═' * 50}")

            sr = final_stats.get('success_rate', 0)
            total = final_stats.get('total_jobs', 0)
            print(f"\n📝 Resume line:")
            print(f'  "Processed {total:,} async jobs with configurable retries')
            print(f'   and maintained {sr}% successful completion rate')
            print(f'   under concurrent load."')


if __name__ == '__main__':
    main()
