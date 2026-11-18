"""ASGI entrypoint. HTTP routes, schemas and application actions live in separate modules."""

from fastapi import FastAPI

from clinic.middleware import install_http
from clinic.routers import admin, appointments, auth, catalog, system
from clinic.telemetry import configure_logging

configure_logging()
app = FastAPI(title="An Uyên Hospital · API đặt lịch khám", version="0.1.0")
install_http(app)
for router in (system.router, auth.router, catalog.router, appointments.router, admin.router):
    app.include_router(router)
