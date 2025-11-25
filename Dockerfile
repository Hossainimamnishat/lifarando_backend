# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps (psycopg, pillow libs if needed later)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq-dev gcc \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# App code
COPY . /app

# Non-root
RUN useradd -u 1001 -ms /bin/bash appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
