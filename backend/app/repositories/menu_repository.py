import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.menu import MenuCategory, MenuItem, MenuItemLocation


class MenuCategoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, category_id: uuid.UUID) -> MenuCategory | None:
        return await self.db.get(MenuCategory, category_id)

    async def list_for_location(self, location_id: uuid.UUID) -> list[MenuCategory]:
        result = await self.db.execute(
            select(MenuCategory)
            .where(MenuCategory.location_id == location_id)
            .order_by(MenuCategory.display_order, MenuCategory.name)
        )
        return list(result.scalars().all())

    def add(self, category: MenuCategory) -> None:
        self.db.add(category)

    async def flush(self) -> None:
        await self.db.flush()


class MenuItemRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, item_id: uuid.UUID) -> MenuItem | None:
        return await self.db.get(MenuItem, item_id)

    async def list_for_category(self, category_id: uuid.UUID) -> list[MenuItem]:
        result = await self.db.execute(
            select(MenuItem).where(MenuItem.category_id == category_id).order_by(MenuItem.name)
        )
        return list(result.scalars().all())

    async def get_names(self, item_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not item_ids:
            return {}
        result = await self.db.execute(
            select(MenuItem.id, MenuItem.name).where(MenuItem.id.in_(item_ids))
        )
        return {row.id: row.name for row in result}

    def add(self, item: MenuItem) -> None:
        self.db.add(item)

    async def flush(self) -> None:
        await self.db.flush()


class MenuItemLocationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, menu_item_id: uuid.UUID, location_id: uuid.UUID) -> MenuItemLocation | None:
        result = await self.db.execute(
            select(MenuItemLocation).where(
                MenuItemLocation.menu_item_id == menu_item_id,
                MenuItemLocation.location_id == location_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_location(self, location_id: uuid.UUID) -> list[MenuItemLocation]:
        result = await self.db.execute(
            select(MenuItemLocation).where(MenuItemLocation.location_id == location_id)
        )
        return list(result.scalars().all())

    def add(self, entry: MenuItemLocation) -> None:
        self.db.add(entry)

    async def flush(self) -> None:
        await self.db.flush()
