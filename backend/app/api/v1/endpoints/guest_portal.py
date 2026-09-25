import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_guest_session
from app.core.database import get_db
from app.core.security import GUEST_ACCESS_TOKEN_TTL, create_guest_access_token
from app.models.enums import ActiveStatus
from app.models.guest import GuestSession
from app.schemas.guest import GuestAuthRequest, GuestAuthResponse, GuestSessionRead
from app.schemas.location import LocationRead
from app.schemas.menu import MenuBrowseCategory, MenuBrowseItem
from app.schemas.order import OrderCreateRequest, OrderRead
from app.services.guests.guest_service import GuestService
from app.services.locations.location_service import LocationService
from app.services.menu.menu_service import MenuService
from app.services.ordering.order_service import OrderService

router = APIRouter(prefix="/guest", tags=["guest-portal"])


@router.get("/locations", response_model=list[LocationRead])
async def list_guest_locations(
    db: AsyncSession = Depends(get_db),
    _: GuestSession = Depends(get_current_guest_session),
) -> list[LocationRead]:
    """A guest needs to pick a location to order from too (orders, not
    sessions, are location-scoped) -- mirrors GET /locations but for the
    guest token instead of an employee one."""
    locations = await LocationService(db).list_all()
    return [
        LocationRead.model_validate(location)
        for location in locations
        if location.status == ActiveStatus.ACTIVE
    ]


@router.get("/locations/{location_id}/menu", response_model=list[MenuBrowseCategory])
async def browse_guest_menu(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: GuestSession = Depends(get_current_guest_session),
) -> list[MenuBrowseCategory]:
    """Same price-free browsing as the employee menu/browse endpoint (see
    app/schemas/menu.py:MenuBrowseItem) -- guests don't see prices either."""
    categories = await MenuService(db).browse(location_id)
    return [
        MenuBrowseCategory(
            id=category.id,
            name=category.name,
            display_order=category.display_order,
            items=[
                MenuBrowseItem(id=item.id, name=item.name, description=item.description)
                for item in items
            ],
        )
        for category, items in categories
    ]


@router.post("/auth", response_model=GuestAuthResponse)
async def guest_auth(
    payload: GuestAuthRequest, db: AsyncSession = Depends(get_db)
) -> GuestAuthResponse:
    """Exchanges the QR's raw token for a short-lived guest access token.
    Succeeds even for a closed session (see GuestService.authenticate);
    ordering endpoints re-check ACTIVE status live regardless."""
    session = await GuestService(db).authenticate(payload.token)
    access_token, _ = create_guest_access_token(guest_session_id=session.id)
    return GuestAuthResponse(
        access_token=access_token,
        expires_in=int(GUEST_ACCESS_TOKEN_TTL.total_seconds()),
        session=GuestSessionRead.model_validate(session),
    )


@router.post("/orders", response_model=OrderRead, status_code=201)
async def create_guest_order(
    payload: OrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    session: GuestSession = Depends(get_current_guest_session),
) -> OrderRead:
    order = await OrderService(db).create_guest_order(
        guest_session_id=session.id,
        location_id=payload.location_id,
        order_type=payload.order_type,
        scheduled_for=payload.scheduled_for,
        items=[(item.menu_item_id, item.quantity) for item in payload.items],
    )
    return OrderRead.model_validate(order)


@router.get("/orders", response_model=list[OrderRead])
async def list_guest_orders(
    db: AsyncSession = Depends(get_db),
    session: GuestSession = Depends(get_current_guest_session),
) -> list[OrderRead]:
    orders = await OrderService(db).list_for_guest_session(session.id)
    return [OrderRead.model_validate(o) for o in orders]
