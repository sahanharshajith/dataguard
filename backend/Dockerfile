FROM python:3.12-slim

# No .pyc files; print logs immediately instead of buffering them.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first: this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations

# Mount point for the shared DuckDB warehouse. Owned like the Airflow image's copy (uid 50000)
# so the shared Docker volume has the same owner whichever container mounts it first.
RUN mkdir -p /data/warehouse && chown 50000:0 /data/warehouse && chmod 775 /data/warehouse

# Run as a non-root user.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
