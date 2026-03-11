# Stage 1: Build React Frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm install --no-audit
COPY dashboard/ .
RUN npm run build

# Stage 2: Build Python Backend
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python project
COPY . .

# Copy built React assets from Stage 1
COPY --from=frontend-builder /app/dashboard/dist /app/dashboard/dist

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD sh -c "python manage.py migrate && gunicorn scheduler.wsgi:application --bind 0.0.0.0:8000 --workers 3"
