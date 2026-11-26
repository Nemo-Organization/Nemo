import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.schemas import ErrorDetail, ErrorEnvelope, RiskAssessment, Transfer

logger = logging.getLogger(__name__)

__all__ = ["ApplicationError", "ErrorDetail", "ErrorEnvelope", "error_response"]


class ApplicationError(Exception):
    """A safe, contract-shaped error. A 409 may carry the current transfer or a fresh assessment."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        current_transfer: Transfer | None = None,
        assessment: RiskAssessment | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.current_transfer = current_transfer
        self.assessment = assessment


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
    *,
    current_transfer: Transfer | None = None,
    assessment: RiskAssessment | None = None,
) -> JSONResponse:
    request_id = request.state.request_id
    detail = ErrorDetail(
        code=code,
        message=message,
        request_id=request_id,
        current_transfer=current_transfer,
        assessment=assessment,
    )
    # Absent optional context is omitted; nested required-nullable fields keep their nulls.
    absent = {name for name in ("current_transfer", "assessment") if getattr(detail, name) is None}
    envelope = {"error": detail.model_dump(mode="json", exclude=absent)}
    ErrorEnvelope.model_validate(envelope)
    response_headers = dict(headers or {})
    response_headers.update({"X-Request-ID": request_id, "Cache-Control": "no-store"})
    return JSONResponse(envelope, status_code=status_code, headers=response_headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        return error_response(
            request,
            exc.status_code,
            exc.code,
            exc.message,
            current_transfer=exc.current_transfer,
            assessment=exc.assessment,
        )

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
