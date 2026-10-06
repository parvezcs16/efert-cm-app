import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_employee, require_location_authority
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import ValidationAppError
from app.models.employee import Employee
from app.schemas.menu import (
    MenuBrowseCategory,
    MenuBrowseItem,
    MenuCategoryCreateRequest,
    MenuCategoryRead,
    MenuCategoryUpdateRequest,
    MenuItemCreateRequest,
    MenuItemLocationRead,
    MenuItemLocationUpsertRequest,
    MenuItemRead,
    MenuItemUpdateRequest,
    MenuPublishRequest,
)
from app.services.menu.menu_service import MenuService

router = APIRouter(prefix="/locations/{location_id}", tags=["menu"])


@router.get("/menu/browse", response_model=list[MenuBrowseCategory])
async def browse_menu(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> list[MenuBrowseCategory]:
    """Employee-facing menu browsing: active, available items only, no
    pricing (see app/schemas/menu.py:MenuBrowseItem)."""
    categories = await MenuService(db).browse(location_id)
    return [
        MenuBrowseCategory(
            id=category.id,
            name=category.name,
            display_order=category.display_order,
            items=[
                MenuBrowseItem(
                    id=item.id,
                    name=item.name,
                    description=item.description,
                    image_url=item.image_url,
                )
                for item in items
            ],
        )
        for category, items in categories
    ]


@router.post("/menu-categories", response_model=MenuCategoryRead, status_code=201)
async def create_menu_category(
    location_id: uuid.UUID,
    payload: MenuCategoryCreateRequest,
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> MenuCategoryRead:
    category = await MenuService(db).create_category(
        location_id=location_id,
        name=payload.name,
        display_order=payload.display_order,
        created_by_id=manager.id,
    )
    return MenuCategoryRead.model_validate(category)


@router.get("/menu-categories", response_model=list[MenuCategoryRead])
async def list_menu_categories(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> list[MenuCategoryRead]:
    categories = await MenuService(db).list_categories(location_id)
    return [MenuCategoryRead.model_validate(c) for c in categories]


@router.patch("/menu-categories/{category_id}", response_model=MenuCategoryRead)
async def update_menu_category(
    location_id: uuid.UUID,
    category_id: uuid.UUID,
    payload: MenuCategoryUpdateRequest,
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> MenuCategoryRead:
    category = await MenuService(db).update_category(
        category_id=category_id,
        name=payload.name,
        display_order=payload.display_order,
        status=payload.status,
        updated_by_id=manager.id,
    )
    return MenuCategoryRead.model_validate(category)


@router.post("/menu-categories/{category_id}/items", response_model=MenuItemRead, status_code=201)
async def create_menu_item(
    location_id: uuid.UUID,
    category_id: uuid.UUID,
    payload: MenuItemCreateRequest,
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> MenuItemRead:
    item = await MenuService(db).create_item(
        category_id=category_id,
        name=payload.name,
        description=payload.description,
        created_by_id=manager.id,
    )
    return MenuItemRead.model_validate(item)


@router.get("/menu-categories/{category_id}/items", response_model=list[MenuItemRead])
async def list_menu_items(
    location_id: uuid.UUID,
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
) -> list[MenuItemRead]:
    items = await MenuService(db).list_items(category_id)
    return [MenuItemRead.model_validate(i) for i in items]


@router.patch("/menu-items/{item_id}", response_model=MenuItemRead)
async def update_menu_item(
    location_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: MenuItemUpdateRequest,
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> MenuItemRead:
    service = MenuService(db)
    if payload.category_id is not None:
        new_category = await service.get_category(payload.category_id)
        if new_category.location_id != location_id:
            raise ValidationAppError("Target category does not belong to this location")

    item = await service.update_item(
        item_id=item_id,
        category_id=payload.category_id,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        updated_by_id=manager.id,
    )
    return MenuItemRead.model_validate(item)


@router.put("/menu-items/{item_id}/image", response_model=MenuItemRead)
async def upload_menu_item_image(
    location_id: uuid.UUID,
    item_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> MenuItemRead:
    """Attach (or replace) the item's photo. JPEG/PNG/WebP, size-limited
    by settings.max_image_upload_bytes; validated in ImageStorage."""
    # Read one byte past the limit so oversize uploads are rejected without
    # buffering an arbitrarily large body.
    data = await file.read(get_settings().max_image_upload_bytes + 1)
    item = await MenuService(db).set_item_image(
        item_id=item_id, image_data=data, updated_by_id=manager.id
    )
    return MenuItemRead.model_validate(item)


@router.delete("/menu-items/{item_id}/image", response_model=MenuItemRead)
async def remove_menu_item_image(
    location_id: uuid.UUID,
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> MenuItemRead:
    item = await MenuService(db).remove_item_image(item_id=item_id, updated_by_id=manager.id)
    return MenuItemRead.model_validate(item)


@router.put(
    "/menu-items/{item_id}/availability",
    response_model=MenuItemLocationRead,
)
async def upsert_menu_item_availability(
    location_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: MenuItemLocationUpsertRequest,
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> MenuItemLocationRead:
    entry = await MenuService(db).upsert_item_location(
        menu_item_id=item_id,
        location_id=location_id,
        is_available=payload.is_available,
        price=payload.price,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        updated_by_id=manager.id,
    )
    return MenuItemLocationRead.model_validate(entry)


@router.get("/menu-items/availability", response_model=list[MenuItemLocationRead])
async def list_menu_item_availability(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> list[MenuItemLocationRead]:
    entries = await MenuService(db).list_item_locations(location_id)
    return [MenuItemLocationRead.model_validate(e) for e in entries]


@router.put("/menu/published", response_model=list[MenuItemLocationRead])
async def publish_menu(
    location_id: uuid.UUID,
    payload: MenuPublishRequest,
    db: AsyncSession = Depends(get_db),
    manager: Employee = Depends(require_location_authority),
) -> list[MenuItemLocationRead]:
    """Publish the dishes employees and guests can order from right now.
    The full catalog is kept; unselected items are just hidden."""
    entries = await MenuService(db).publish_menu(
        location_id=location_id,
        menu_item_ids=set(payload.menu_item_ids),
        published_by_id=manager.id,
    )
    return [MenuItemLocationRead.model_validate(e) for e in entries]
