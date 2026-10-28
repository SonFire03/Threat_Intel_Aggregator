from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

from app.core.paths import TEMPLATES_DIR

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/imports")
def import_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "imports/upload.html", {})
