from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nova_api.config import settings
from nova_api.routes import (
    ai,
    connectors,
    datasets,
    lineage,
    pipelines,
    projects,
    quality,
)
from nova_api.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown — close DB pool
    from nova_api.database import engine

    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-driven data platform API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount all routers under /api/v1
    app.include_router(projects.router, prefix="/api/v1")
    app.include_router(datasets.router, prefix="/api/v1")
    app.include_router(connectors.router, prefix="/api/v1")
    app.include_router(pipelines.router, prefix="/api/v1")
    app.include_router(lineage.router, prefix="/api/v1")
    app.include_router(quality.router, prefix="/api/v1")
    app.include_router(ai.router, prefix="/api/v1")

    @app.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(
            status="ok",
            service="nova-api",
            version=settings.app_version,
        )

    return app


app = create_app()
