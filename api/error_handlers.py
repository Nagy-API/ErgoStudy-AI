"""Consistent, non-sensitive API error responses."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.dependencies import InvalidAPIRequestError, ServiceUnavailableError


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", uuid.uuid4()))


def _response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {"code": code, "message": message, "details": details or []},
            "request_id": _request_id(request),
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for error in exc.errors():
            location = [str(item) for item in error.get("loc", ()) if item != "body"]
            details.append(
                {"field": ".".join(location) or None, "message": str(error.get("msg", "Invalid value"))}
            )
        return _response(request, 422, "INVALID_REQUEST", "The request body is invalid.", details)

    @app.exception_handler(InvalidAPIRequestError)
    @app.exception_handler(ValueError)
    async def value_error(request: Request, exc: ValueError) -> JSONResponse:
        return _response(
            request,
            422,
            "INVALID_REQUEST",
            "The request could not be processed.",
            [{"field": None, "message": str(exc)}],
        )

    @app.exception_handler(ServiceUnavailableError)
    async def unavailable_error(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
        return _response(
            request,
            503,
            "SERVICE_UNAVAILABLE",
            "The deterministic planning service is not ready.",
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return _response(request, exc.status_code, "HTTP_ERROR", str(exc.detail))

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        return _response(
            request,
            500,
            "INTERNAL_ERROR",
            "An unexpected internal error occurred.",
        )
