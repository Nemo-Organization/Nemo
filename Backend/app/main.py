from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.db import create_database_engine
from app.demo.router import customer_router as demo_customer_router
from app.demo.router import router as demo_router
from app.errors import ErrorEnvelope, install_error_handlers
from app.health import router as health_router
from app.middleware import RequestContextMiddleware
from app.settings import Settings
from app.transfers.router import router as transfers_router


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = (
            create_database_engine(configuration)
            if configuration.database_url is not None
            else None
        )
        app.state.db_engine = engine
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()

    app = FastAPI(
        title="Guardian API",
        version="0.1.0",
        lifespan=lifespan,
        responses={
            code: {"model": ErrorEnvelope} for code in (400, 401, 403, 404, 409, 422, 429, 500, 503)
        },
    )
    app.state.settings = configuration
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(demo_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(demo_customer_router, prefix="/api/v1")
    app.include_router(transfers_router, prefix="/api/v1")
    return app


app = create_app()
