import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.enums import ActiveStatus
from app.models.menu import MenuCategory, MenuItem, MenuItemLocation
from app.repositories.location_repository import LocationRepository
from app.repositories.menu_repository import (
    MenuCategoryRepository,
    MenuItemLocationRepository,
    MenuItemRepository,
)
from app.services.audit_service import AuditService
from app.services.media.image_storage import menu_image_storage


class MenuService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.categories = MenuCategoryRepository(db)
        self.items = MenuItemRepository(db)
        self.item_locations = MenuItemLocationRepository(db)
        self.locations = LocationRepository(db)
        self.audit = AuditService(db)

    # -- Categories ---------------------------------------------------

    async def create_category(
        self, *, location_id: uuid.UUID, name: str, display_order: int, created_by_id: uuid.UUID
    ) -> MenuCategory:
        if await self.locations.get_by_id(location_id) is None:
            raise NotFoundError("Location not found")

        category = MenuCategory(location_id=location_id, name=name, display_order=display_order)
        self.categories.add(category)
        try:
            await self.categories.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError(
                "A category with this name already exists for this location"
            ) from exc

        await self.audit.record(
            action="menu_category.created",
            entity_type="menu_category",
            entity_id=str(category.id),
            actor_employee_id=created_by_id,
            new_values={"location_id": str(location_id), "name": name},
        )
        return category

    async def list_categories(self, location_id: uuid.UUID) -> list[MenuCategory]:
        return await self.categories.list_for_location(location_id)

    async def get_category(self, category_id: uuid.UUID) -> MenuCategory:
        category = await self.categories.get_by_id(category_id)
        if category is None:
            raise NotFoundError("Menu category not found")
        return category

    async def update_category(
        self,
        *,
        category_id: uuid.UUID,
        name: str | None,
        display_order: int | None,
        status: ActiveStatus | None,
        updated_by_id: uuid.UUID,
    ) -> MenuCategory:
        category = await self.get_category(category_id)
        if name is not None:
            category.name = name
        if display_order is not None:
            category.display_order = display_order
        if status is not None:
            category.status = status
        await self.categories.flush()

        await self.audit.record(
            action="menu_category.updated",
            entity_type="menu_category",
            entity_id=str(category.id),
            actor_employee_id=updated_by_id,
        )
        return category

    # -- Items ----------------------------------------------------------

    async def create_item(
        self,
        *,
        category_id: uuid.UUID,
        name: str,
        description: str | None,
        created_by_id: uuid.UUID,
    ) -> MenuItem:
        await self.get_category(category_id)

        item = MenuItem(category_id=category_id, name=name, description=description)
        self.items.add(item)
        await self.items.flush()

        await self.audit.record(
            action="menu_item.created",
            entity_type="menu_item",
            entity_id=str(item.id),
            actor_employee_id=created_by_id,
            new_values={"category_id": str(category_id), "name": name},
        )
        return item

    async def get_item(self, item_id: uuid.UUID) -> MenuItem:
        item = await self.items.get_by_id(item_id)
        if item is None:
            raise NotFoundError("Menu item not found")
        return item

    async def list_items(self, category_id: uuid.UUID) -> list[MenuItem]:
        return await self.items.list_for_category(category_id)

    async def update_item(
        self,
        *,
        item_id: uuid.UUID,
        category_id: uuid.UUID | None,
        name: str | None,
        description: str | None,
        status: ActiveStatus | None,
        updated_by_id: uuid.UUID,
    ) -> MenuItem:
        item = await self.get_item(item_id)
        if category_id is not None:
            await self.get_category(category_id)
            item.category_id = category_id
        if name is not None:
            item.name = name
        if description is not None:
            item.description = description
        if status is not None:
            item.status = status
        await self.items.flush()

        await self.audit.record(
            action="menu_item.updated",
            entity_type="menu_item",
            entity_id=str(item.id),
            actor_employee_id=updated_by_id,
        )
        return item

    async def set_item_image(
        self, *, item_id: uuid.UUID, image_data: bytes, updated_by_id: uuid.UUID
    ) -> MenuItem:
        item = await self.get_item(item_id)
        storage = menu_image_storage()
        old_url = item.image_url
        item.image_url = storage.save(image_data)
        await self.items.flush()

        await self.audit.record(
            action="menu_item.image_updated",
            entity_type="menu_item",
            entity_id=str(item.id),
            actor_employee_id=updated_by_id,
            old_values={"image_url": old_url},
            new_values={"image_url": item.image_url},
        )
        storage.delete(old_url)
        return item

    async def remove_item_image(self, *, item_id: uuid.UUID, updated_by_id: uuid.UUID) -> MenuItem:
        item = await self.get_item(item_id)
        old_url = item.image_url
        if old_url is None:
            return item
        item.image_url = None
        await self.items.flush()

        await self.audit.record(
            action="menu_item.image_removed",
            entity_type="menu_item",
            entity_id=str(item.id),
            actor_employee_id=updated_by_id,
            old_values={"image_url": old_url},
        )
        menu_image_storage().delete(old_url)
        return item

    # -- Location availability/pricing -----------------------------------

    async def upsert_item_location(
        self,
        *,
        menu_item_id: uuid.UUID,
        location_id: uuid.UUID,
        is_available: bool,
        price: Decimal,
        effective_from: datetime | None,
        effective_to: datetime | None,
        updated_by_id: uuid.UUID,
    ) -> MenuItemLocation:
        await self.get_item(menu_item_id)
        if await self.locations.get_by_id(location_id) is None:
            raise NotFoundError("Location not found")

        entry = await self.item_locations.get(menu_item_id, location_id)
        old_values = None
        if entry is None:
            entry = MenuItemLocation(
                menu_item_id=menu_item_id, location_id=location_id, price=price
            )
            self.item_locations.add(entry)
        else:
            old_values = {"is_available": entry.is_available, "price": str(entry.price)}

        entry.is_available = is_available
        entry.price = price
        entry.effective_from = effective_from
        entry.effective_to = effective_to
        await self.item_locations.flush()

        await self.audit.record(
            action="menu_item_location.upserted",
            entity_type="menu_item_location",
            entity_id=str(entry.id),
            actor_employee_id=updated_by_id,
            old_values=old_values,
            new_values={"is_available": is_available, "price": str(price)},
        )
        return entry

    async def list_item_locations(self, location_id: uuid.UUID) -> list[MenuItemLocation]:
        return await self.item_locations.list_for_location(location_id)

    async def publish_menu(
        self,
        *,
        location_id: uuid.UUID,
        menu_item_ids: set[uuid.UUID],
        published_by_id: uuid.UUID,
    ) -> list[MenuItemLocation]:
        """Replace the location's live (orderable) dish set in one step: the
        given items become available, every other priced item at this
        location is unpublished but stays in the catalog. Prices and
        effective windows are left untouched."""
        if await self.locations.get_by_id(location_id) is None:
            raise NotFoundError("Location not found")

        entries = await self.item_locations.list_for_location(location_id)
        priced_ids = {entry.menu_item_id for entry in entries}
        unpriced = menu_item_ids - priced_ids
        if unpriced:
            raise ValidationAppError(
                f"{len(unpriced)} selected item(s) have no price at this location; "
                "set a price before publishing them"
            )

        published: list[str] = []
        unpublished: list[str] = []
        for entry in entries:
            is_available = entry.menu_item_id in menu_item_ids
            if entry.is_available != is_available:
                (published if is_available else unpublished).append(str(entry.menu_item_id))
            entry.is_available = is_available
        await self.item_locations.flush()

        await self.audit.record(
            action="menu.published",
            entity_type="location",
            entity_id=str(location_id),
            actor_employee_id=published_by_id,
            new_values={
                "published_item_ids": published,
                "unpublished_item_ids": unpublished,
                "live_item_count": len(menu_item_ids),
            },
        )
        return entries

    # -- Employee-facing browsing (no prices) ----------------------------

    async def browse(self, location_id: uuid.UUID) -> list[tuple[MenuCategory, list[MenuItem]]]:
        """Active categories/items currently sellable at this location.
        Small catalogs are assumed (a handful of categories/items per
        location), so the straightforward per-category/item lookups here
        are preferred over a hand-joined query for now."""
        now = datetime.now(UTC)
        result: list[tuple[MenuCategory, list[MenuItem]]] = []

        for category in await self.categories.list_for_location(location_id):
            if category.status != ActiveStatus.ACTIVE:
                continue

            available_items = []
            for item in await self.items.list_for_category(category.id):
                if item.status != ActiveStatus.ACTIVE:
                    continue
                entry = await self.item_locations.get(item.id, location_id)
                if entry is None or not entry.is_available:
                    continue
                if entry.effective_from is not None and entry.effective_from > now:
                    continue
                if entry.effective_to is not None and entry.effective_to < now:
                    continue
                available_items.append(item)

            if available_items:
                result.append((category, available_items))

        return result

    async def get_sellable_price(
        self, *, menu_item_id: uuid.UUID, location_id: uuid.UUID
    ) -> Decimal | None:
        """The current price if this item is actually sellable (active,
        available, within its effective window) at this location right
        now; None otherwise. Used by ordering to validate + snapshot price."""
        item = await self.items.get_by_id(menu_item_id)
        if item is None or item.status != ActiveStatus.ACTIVE:
            return None

        entry = await self.item_locations.get(menu_item_id, location_id)
        if entry is None or not entry.is_available:
            return None

        now = datetime.now(UTC)
        if entry.effective_from is not None and entry.effective_from > now:
            return None
        if entry.effective_to is not None and entry.effective_to < now:
            return None

        return entry.price
