#!/bin/sh
# start-worker.sh
set -e

# Wait for Redis
until nc -z redis 6379; do echo "Waiting for redis..."; sleep 1; done

# Start Celery worker
celery -A config.celery_app worker --loglevel=info --concurrency=2
