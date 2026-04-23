from fastapi import APIRouter

from app.routers.web import dashboard, exports, imports, iocs

web_router = APIRouter()
web_router.include_router(dashboard.router)
web_router.include_router(iocs.router)
web_router.include_router(imports.router)
web_router.include_router(exports.router)

__all__ = ["web_router"]
