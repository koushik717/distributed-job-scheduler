# Distributed Async Job Scheduler

A production-grade background processing system built with Django, Celery, Redis, and PostgreSQL. Demonstrates real-world patterns: priority queues, exponential backoff retries, dead letter queues, idempotency, observability, and horizontal worker scaling.

## Architecture

```
                 ┌────────────────────┐
                 │     REST API       │
                 │  (Django + DRF)    │
                 └─────────┬──────────┘
                           │
                     Create Job
                           │
                    ┌──────▼──────┐
                    │ PostgreSQL  │   ← Source of Truth
                    │ (Job Store) │
                    └──────┬──────┘
                           │
                    Enqueue Task
                           │
                    ┌──────▼──────┐
                    │   Redis     │   ← Transport Only
                    │  (Broker)   │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
      ┌─────▼─────┐  ┌─────▼─────┐  ┌────▼─────┐
      │ Worker #1 │  │ Worker #2 │  │ Worker #3│
      │ high+def  │  │ def+low   │  │ low only │
      │ +low      │  │           │  │          │
      └───────────┘  └───────────┘  └──────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **PostgreSQL = Source of Truth** | Redis is only transport. Job state persists through broker failures. |
| **Exponential Backoff** | `delay = 2^retry_count` prevents thundering herd on transient failures. |
| **Dead Letter Queue** | Jobs that exhaust retries move to `DEAD` status for investigation, not silently dropped. |
| **Idempotency Keys** | Stripe-level pattern. Duplicate submissions return the existing job, preventing double-execution. |
| **Priority Queue Routing** | 3-tier queues (high/default/low) with worker affinity. High-priority workers process all queues; low-priority workers only process low. |
| **Visibility Timeout** | If a worker crashes mid-task, the job is redelivered and marked FAILED by stale-job detection. |

## Quick Start

```bash
# Build and start all services
docker compose up --build -d

# Check service health
docker compose ps

# View logs
docker compose logs -f web celery_worker_1

# Seed demo jobs
python scripts/seed_jobs.py

# Run load test (10,000 jobs)
python scripts/load_test.py --jobs 10000 --concurrency 50
```

### Dashboard

```bash
cd dashboard
npm install
npm run dev
# Open http://localhost:5173
```

## API Reference

### Create Job
```bash
curl -X POST http://localhost:8000/api/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "type": "send_email",
    "payload": {"to": "user@example.com", "subject": "Hello"},
    "priority": 3,
    "max_retries": 3
  }'
```

### Create Idempotent Job
```bash
curl -X POST http://localhost:8000/api/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "type": "send_email",
    "payload": {"to": "user@example.com"},
    "priority": 5,
    "max_retries": 3,
    "idempotency_key": "welcome-email-user-123"
  }'
```

### Schedule a Future Job
```bash
curl -X POST http://localhost:8000/api/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "type": "generate_report",
    "payload": {"report_type": "daily"},
    "priority": 5,
    "max_retries": 2,
    "run_at": "2026-03-10T08:00:00Z"
  }'
```

### List Jobs (with filters)
```bash
curl "http://localhost:8000/api/jobs/?status=COMPLETED&type=send_email&ordering=-created_at"
```

### Get Job Stats
```bash
curl http://localhost:8000/api/jobs/stats/
```

### Cancel / Retry a Job
```bash
curl -X POST http://localhost:8000/api/jobs/<uuid>/cancel/
curl -X POST http://localhost:8000/api/jobs/<uuid>/retry/
```

### Prometheus Metrics
```bash
curl http://localhost:8000/metrics
```

## Available Job Types

| Type | Description | Avg Duration | Failure Rate |
|------|------------|--------------|--------------|
| `send_email` | Email delivery simulation | 0.5-2s | 10% |
| `generate_report` | Report generation | 2-5s | 5% |
| `process_data` | Data pipeline processing | 1-3s | 15% |
| `cleanup` | Maintenance/cleanup tasks | 0.3-1.5s | 2% |
| `webhook` | External webhook delivery | 0.2-1s | 8% |
| `image_resize` | Image processing | 1-4s | 3% |

## Job Lifecycle

```
PENDING ──→ RUNNING ──→ COMPLETED
  │            │
  │            ▼
  │         FAILED ──→ (backoff) ──→ RUNNING (retry)
  │            │
  │            ▼
  │     DEAD (DLQ) ← retries exhausted
  │
  ▼
CANCELLED

SCHEDULED ──→ (run_at reached) ──→ PENDING ──→ ...
```

## Retry Strategy

```
Attempt 1: immediate
Attempt 2: +2 seconds
Attempt 3: +4 seconds
Attempt 4: +8 seconds
Attempt 5: +16 seconds
...
Max delay: 300 seconds (5 minutes)
```

## Scaling Strategy

```bash
# Scale workers horizontally
docker compose up --scale celery_worker_1=3 --scale celery_worker_2=3 -d
```

Workers are stateless — they pull jobs from Redis and update PostgreSQL. Adding more worker replicas linearly increases throughput. The Celery Beat scheduler remains a single instance to prevent duplicate scheduling.

## Observability

### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `jobs_submitted_total` | Counter | Jobs submitted by type and queue |
| `jobs_completed_total` | Counter | Successful completions by type |
| `jobs_failed_total` | Counter | Failures by type |
| `job_duration_seconds` | Histogram | Processing time distribution |
| `jobs_retried_total` | Counter | Retry count by type |
| `jobs_dead_letter_total` | Counter | Dead letter count by type |

### Structured Logging

All workers emit structured JSON logs with job ID, type, status, worker ID, and duration for easy log aggregation.

## Project Structure

```
├── scheduler/          # Django project settings + Celery config
├── jobs/               # Job model, API views, serializers, handlers
├── workers/            # Celery tasks, retry logic, scheduler
├── metrics/            # Prometheus counters/histograms + /metrics endpoint
├── dashboard/          # React + Chart.js monitoring UI
├── scripts/            # Load test & seed data scripts
├── docker-compose.yml  # Full stack: PG, Redis, Django, 3 workers, Beat, Prometheus
└── prometheus.yml      # Prometheus scrape configuration
```

## Tech Stack

- **Backend**: Django 5.1, Django REST Framework
- **Task Queue**: Celery 5.4 with Redis broker
- **Database**: PostgreSQL 16 (source of truth)
- **Cache/Broker**: Redis 7
- **Metrics**: Prometheus + prometheus-client
- **Dashboard**: React 18, Chart.js, Vite
- **Infrastructure**: Docker Compose
