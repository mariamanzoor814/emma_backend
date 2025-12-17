# Use official Python slim
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# system deps (add build-essential if you need to compile packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev netcat-openbsd && rm -rf /var/lib/apt/lists/*

# install pip tools
COPY pyproject.toml poetry.lock* /app/ 2>/dev/null || true
# if you're using requirements.txt
COPY requirements.txt /app/ 2>/dev/null || true

# Install dependencies (pick your preferred method)
RUN pip install --upgrade pip
# if using requirements.txt:
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Copy project
COPY . /app

# Make start scripts executable (created below)
RUN chmod +x /app/start-web.sh /app/start-worker.sh

# Expose port used by Django
EXPOSE 8000

# Default command (overridden by docker-compose)
CMD ["./start-web.sh"]
