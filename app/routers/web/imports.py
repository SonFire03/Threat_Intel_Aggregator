from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/imports")
def import_page(request: Request) -> Response:
    return templates.TemplateResponse(request, "imports/upload.html", {})
