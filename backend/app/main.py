import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.websocket.kitchen import router as kitchen_ws_router
from app.workers.daily_summary_scheduler import run_daily_summary_scheduler
from app.workers.statement_scheduler import run_statement_scheduler

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    logger.info("Starting %s (%s)", settings.app_name, settings.environment)
    scheduler_tasks = [
        asyncio.create_task(run_statement_scheduler()),
        asyncio.create_task(run_daily_summary_scheduler()),
    ]
    yield
    for task in scheduler_tasks:
        task.cancel()
    for task in scheduler_tasks:
        with contextlib.suppress(asyncio.CancelledError):
            await task
    await engine.dispose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    if settings.is_production and settings.secret_key == "change-me-in-production":
        raise RuntimeError(
            "SECRET_KEY is still the default placeholder in a production environment. "
            "Set a real, random SECRET_KEY before starting the app."
        )

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.include_router(kitchen_ws_router)

    # Uploaded menu images. Only files ImageStorage wrote (signature-checked
    # JPEG/PNG/WebP with random names) live here.
    media_root = Path(settings.media_root)
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount(settings.media_url_prefix, StaticFiles(directory=media_root), name="media")

    return app


app = create_app()
