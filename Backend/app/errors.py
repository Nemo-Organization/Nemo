import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail


class ApplicationError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = request.state.request_id
    envelope = ErrorEnvelope(error=ErrorDetail(code=code, message=message, request_id=request_id))
    response_headers = dict(headers or {})
    response_headers.update({"X-Request-ID": request_id, "Cache-Control": "no-store"})
    return JSONResponse(envelope.model_dump(), status_code=status_code, headers=response_headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        return error_response(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        try:
            status = HTTPStatus(exc.status_code)
        except ValueError:
            return error_response(
                request, exc.status_code, "HTTP_ERROR", "HTTP request failed.", exc.headers
            )
        code = {400: "BAD_REQUEST", 401: "SESSION_EXPIRED", 403: "FORBIDDEN"}.get(
            exc.status_code, status.name
        )
        return error_response(request, exc.status_code, code, status.phrase, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(request, 422, "VALIDATION_ERROR", "Request validation failed.")

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled request failure",
            extra={"request_id": request.state.request_id, "exception_type": type(exc).__name__},
        )
        return error_response(request, 500, "INTERNAL_ERROR", "An internal error occurred.")
