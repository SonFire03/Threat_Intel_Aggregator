from fastapi import APIRouter

from app.routers.api import exports, imports, iocs, stats, tags

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(iocs.router)
api_router.include_router(imports.router)
api_router.include_router(exports.router)
api_router.include_router(tags.router)
api_router.include_router(stats.router)

__all__ = ["api_router"]
