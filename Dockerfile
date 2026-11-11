# The Rusting Dead Mod Marketplace — single container
# Python 3.12 slim. The app + SQLite DB + uploads all live in this one
# container; the only persistent state is the /data volume.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY brand/ ./brand/
COPY app.py .

# Non-root user; /data is the only writable path the app needs.
RUN useradd -m appuser && mkdir -p /data/uploads && chown -R appuser:appuser /data
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["python", "app.py"]
