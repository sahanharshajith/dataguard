FROM apache/airflow:3.4.0

USER root
# Mount points for the shared warehouse volume and the landing zone. They are created here,
# owned by the airflow user (uid 50000), so a brand-new Docker volume inherits the right owner.
RUN mkdir -p /data/warehouse /data/landing \
    && chown -R airflow:0 /data \
    && chmod -R 775 /data/warehouse

# `import pipelines` works because the repo's pipelines/ folder is mounted at /opt/airflow/pipelines.
ENV PYTHONPATH=/opt/airflow

USER airflow
# Pinning apache-airflow here stops pip from ever upgrading Airflow by accident.
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" "duckdb>=1.1,<2.0"