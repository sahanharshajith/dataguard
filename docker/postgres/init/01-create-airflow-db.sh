#!/bin/bash
# Runs ONCE, the first time the postgres container starts with an empty data volume.
# Creates a separate role and database for Airflow's own metadata,
# so Airflow tables never mix with DataGuard tables.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE ${AIRFLOW_DB_USER} WITH LOGIN PASSWORD '${AIRFLOW_DB_PASSWORD}';
    CREATE DATABASE ${AIRFLOW_DB_NAME} OWNER ${AIRFLOW_DB_USER};
EOSQL

echo "Created database '${AIRFLOW_DB_NAME}' owned by role '${AIRFLOW_DB_USER}'."
