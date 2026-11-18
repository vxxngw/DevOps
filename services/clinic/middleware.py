import re
import time
import uuid

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from clinic.telemetry import HTTP_COUNT, HTTP_TIME, log


def install_http(app):

    @app.middleware("http")
    async def observe(request: Request, call_next):
        supplied = request.headers.get("x-request-id", "")
        request.state.request_id = (
            supplied if re.fullmatch("[A-Za-z0-9_.-]{1,64}", supplied) else str(uuid.uuid4())
        )
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as exc:
            log(
                "appointment-api",
                "unhandled_error",
                level="ERROR",
                request_id=request.state.request_id,
                error_type=type(exc).__name__,
            )
            response = JSONResponse(
                {
                    "error": {
                        "message": "Có lỗi xử lý. Vui lòng thử lại.",
                        "request_id": request.state.request_id,
                    }
                },
                status_code=500,
            )
        route = getattr(request.scope.get("route"), "path", "unmatched")
        if route not in {"/health", "/ready", "/metrics"}:
            HTTP_COUNT.labels(route, request.method, str(response.status_code)).inc()
            HTTP_TIME.labels(route, request.method).observe(time.monotonic() - start)
            log(
                "appointment-api",
                "http_request",
                level="ERROR" if response.status_code >= 500 else "INFO",
                request_id=request.state.request_id,
                route=route,
                method=request.method,
                status=response.status_code,
            )
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return JSONResponse(
            {"error": {"message": exc.detail, "request_id": request.state.request_id}},
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(
            {
                "error": {
                    "message": "Dữ liệu đầu vào không hợp lệ",
                    "request_id": request.state.request_id,
                }
            },
            status_code=422,
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        log(
            "appointment-api",
            "database_error",
            level="ERROR",
            request_id=request.state.request_id,
            error_type=type(exc).__name__,
        )
        return JSONResponse(
            {
                "error": {
                    "message": "CSDL tạm thời chưa sẵn sàng",
                    "request_id": request.state.request_id,
                }
            },
            status_code=503,
        )
