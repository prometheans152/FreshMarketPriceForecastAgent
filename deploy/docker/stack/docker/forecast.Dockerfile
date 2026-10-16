FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app/deploy/oracle-forecastengine \
    TZ=Asia/Taipei

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && \
    groupadd --gid 10001 fmpa && \
    useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin fmpa

COPY src /app/src
COPY deploy /app/deploy
COPY models /app/models
COPY catalog /app/catalog
COPY docker/engine_entrypoint.py /app/docker/engine_entrypoint.py

RUN find /app -type d -exec chmod 0755 {} \; && \
    find /app -type f -exec chmod 0644 {} \;

# Entrypoint reads a root-only Docker secret then drops to UID 10001 BEFORE
# serving HTTP. The secret is never in the image, public JS or Docker config.
EXPOSE 8767
ENTRYPOINT ["python", "/app/docker/engine_entrypoint.py"]
