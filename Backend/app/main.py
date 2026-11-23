from fastapi import FastAPI

from app.errors import ErrorEnvelope, install_error_handlers
from app.health import router as health_router
from app.middleware import RequestContextMiddleware
from app.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(
        title="Guardian API",
        version="0.1.0",
        responses={
            code: {"model": ErrorEnvelope} for code in (400, 401, 403, 404, 409, 422, 429, 500, 503)
        },
    )
    app.state.settings = settings or Settings()
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    return app


app = create_app()
