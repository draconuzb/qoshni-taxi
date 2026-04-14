from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, conint
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Route
from core.locations import REGIONS
from infrastructure.config import settings as app_settings
from webapp.deps import get_session, templates

router = APIRouter()


class DefaultRoute(BaseModel):
    route_id: conint(ge=1)


class ContactPhone(BaseModel):
    phone: str = Field(min_length=1, max_length=30)


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, session: AsyncSession = Depends(get_session)):
    total_routes = await session.scalar(select(func.count(Route.id))) or 0
    active_routes = await session.scalar(
        select(func.count(Route.id)).where(Route.is_active == True)
    ) or 0
    result = await session.execute(select(Route).where(Route.is_active == True).order_by(Route.id))
    all_routes = result.scalars().all()
    return templates.TemplateResponse(request, "settings.html", {
        "settings": app_settings, "total_routes": total_routes, "active_routes": active_routes,
        "regions": REGIONS, "all_routes": all_routes,
        "default_route_id": app_settings.default_route_id,
        "contact_phone": app_settings.contact_phone,
    })


@router.post("/api/settings/default-route")
async def api_set_default_route(data: DefaultRoute):
    app_settings.default_route_id = data.route_id
    return {"ok": True}


@router.post("/api/settings/contact-phone")
async def api_set_contact_phone(data: ContactPhone):
    app_settings.contact_phone = data.phone.strip()
    return {"ok": True}
