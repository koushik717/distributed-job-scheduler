web: python manage.py migrate && gunicorn scheduler.wsgi:application --bind 0.0.0.0:$PORT --workers 3
celery-worker: celery -A scheduler worker -l INFO -Q high_priority,default,low_priority --concurrency 2
celery-beat: celery -A scheduler beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
