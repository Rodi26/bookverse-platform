# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config ./config

ENTRYPOINT ["python", "-m", "app.main"]
CMD ["--config", "/app/config/services.yaml", "--output-dir", "/app/manifests", "--source-stage", "PROD", "--preview"]


