from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.paths import STATIC_DIR
from app.database import Base, engine
from app.routers.api import api_router
from app.routers.web import web_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    application.include_router(web_router)
    application.include_router(api_router)

    return application


app = create_app()
