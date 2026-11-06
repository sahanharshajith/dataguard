"""FastAPI application entry point."""

import logging

from fastapi import FastAPI

from app.api import health
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Data Quality & Observability Platform API",
)

app.include_router(health.router)
