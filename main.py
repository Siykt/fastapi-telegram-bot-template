"""FastApi Telegram Bot Template Application Entry Point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core import close_database, close_redis, init_database, init_logger, init_redis, settings
from app.bot import bot_manager, init_bot_manager
from app.scheduler import init_scheduler, scheduler_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    init_logger()
    await init_database()
    await init_redis()

    # 初始化并启动Bot
    init_bot_manager()
    await bot_manager.start()

    # 初始化并启动调度器
    init_scheduler()
    await scheduler_manager.start()

    yield

    # 停止调度器
    await scheduler_manager.stop()
    # 停止Bot并清理资源
    await bot_manager.stop()
    await close_redis()
    await close_database()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    enable_docs = settings.env != "prod"
    app = FastAPI(
        title=settings.app_name,
        description="FastApi Telegram Bot Template",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
        openapi_url="/openapi.json" if enable_docs else None,
    )

    from app.api.telegram_router import router as telegram_router
    app.include_router(telegram_router)

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=settings.debug)
