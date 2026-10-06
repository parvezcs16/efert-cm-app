"""Default starter menu: 8 categories with 3-4 items each, bundled photos
(app/seed_data/menu_images, credits in CREDITS.md there) and internal
prices in PKR.

Seeding is idempotent and additive: an existing category/item (matched by
name) is reused, a photo a manager uploaded or removed is never touched,
and an existing per-location price/availability is never overwritten -- so
it's safe to re-run against a location a manager has already customized.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.menu import MenuCategory, MenuItem, MenuItemLocation
from app.repositories.menu_repository import (
    MenuCategoryRepository,
    MenuItemLocationRepository,
    MenuItemRepository,
)
from app.services.audit_service import AuditService
from app.services.media.image_storage import menu_image_storage

SEED_IMAGE_DIR = Path(__file__).resolve().parents[2] / "seed_data" / "menu_images"


@dataclass(frozen=True)
class DefaultMenuItem:
    name: str
    description: str
    price: Decimal
    image: str


DEFAULT_MENU: dict[str, list[DefaultMenuItem]] = {
    "Starters": [
        DefaultMenuItem(
            "Chicken Corn Soup",
            "Thick, comforting chicken and sweet corn soup.",
            Decimal("250.00"),
            "chicken-corn-soup.jpg",
        ),
        DefaultMenuItem(
            "Vegetable Samosa",
            "Crispy pastry filled with spiced potato and peas (2 pcs).",
            Decimal("120.00"),
            "vegetable-samosa.jpg",
        ),
        DefaultMenuItem(
            "Chicken Spring Rolls",
            "Golden-fried rolls with chicken and vegetables (4 pcs).",
            Decimal("280.00"),
            "chicken-spring-rolls.jpg",
        ),
        DefaultMenuItem(
            "Dahi Bhallay",
            "Soft lentil dumplings in yogurt with tamarind chutney.",
            Decimal("180.00"),
            "dahi-bhallay.jpg",
        ),
    ],
    "Main Course": [
        DefaultMenuItem(
            "Chicken Biryani",
            "Fragrant basmati rice layered with spiced chicken, served with raita.",
            Decimal("450.00"),
            "chicken-biryani.jpg",
        ),
        DefaultMenuItem(
            "Beef Pulao",
            "Aromatic rice cooked in beef yakhni with whole spices.",
            Decimal("480.00"),
            "beef-pulao.jpg",
        ),
        DefaultMenuItem(
            "Butter Chicken",
            "Tender chicken in a creamy tomato and butter gravy.",
            Decimal("650.00"),
            "butter-chicken.jpg",
        ),
        DefaultMenuItem(
            "Chicken Qorma",
            "Rich, mildly spiced qorma with fried onions and yogurt.",
            Decimal("550.00"),
            "chicken-qorma.jpg",
        ),
    ],
    "BBQ": [
        DefaultMenuItem(
            "Chicken Tikka",
            "Charcoal-grilled marinated chicken quarter.",
            Decimal("420.00"),
            "chicken-tikka.jpg",
        ),
        DefaultMenuItem(
            "Seekh Kabab",
            "Minced beef skewers with herbs, grilled over coal (4 pcs).",
            Decimal("480.00"),
            "seekh-kabab.jpg",
        ),
        DefaultMenuItem(
            "Malai Boti",
            "Creamy, mildly spiced boneless chicken skewers.",
            Decimal("620.00"),
            "malai-boti.jpg",
        ),
        DefaultMenuItem(
            "BBQ Chicken Wings",
            "Smoky grilled wings with garlic dip (8 pcs).",
            Decimal("520.00"),
            "bbq-chicken-wings.jpg",
        ),
    ],
    "Chinese": [
        DefaultMenuItem(
            "Chicken Chow Mein",
            "Stir-fried noodles with chicken and vegetables.",
            Decimal("550.00"),
            "chicken-chow-mein.jpg",
        ),
        DefaultMenuItem(
            "Egg Fried Rice",
            "Wok-tossed rice with egg, peas and carrots.",
            Decimal("400.00"),
            "egg-fried-rice.jpg",
        ),
        DefaultMenuItem(
            "Chicken Manchurian",
            "Crispy chicken in a tangy Manchurian sauce.",
            Decimal("600.00"),
            "chicken-manchurian.jpg",
        ),
        DefaultMenuItem(
            "Sweet and Sour Chicken",
            "Battered chicken with peppers in sweet and sour sauce.",
            Decimal("620.00"),
            "sweet-and-sour-chicken.jpg",
        ),
    ],
    "Continental": [
        DefaultMenuItem(
            "Grilled Chicken Steak",
            "Herb-marinated chicken breast with sauteed vegetables and mushroom sauce.",
            Decimal("850.00"),
            "grilled-chicken-steak.jpg",
        ),
        DefaultMenuItem(
            "Fettuccine Alfredo",
            "Fettuccine in a creamy parmesan sauce with chicken.",
            Decimal("750.00"),
            "fettuccine-alfredo.jpg",
        ),
        DefaultMenuItem(
            "Club Sandwich",
            "Triple-decker chicken and egg sandwich with fries.",
            Decimal("550.00"),
            "club-sandwich.jpg",
        ),
        DefaultMenuItem(
            "Beef Burger",
            "Grilled beef patty with cheese, lettuce and house sauce.",
            Decimal("650.00"),
            "beef-burger.jpg",
        ),
    ],
    "Desserts": [
        DefaultMenuItem(
            "Gulab Jamun",
            "Warm milk dumplings soaked in cardamom syrup (2 pcs).",
            Decimal("150.00"),
            "gulab-jamun.jpg",
        ),
        DefaultMenuItem(
            "Kheer", "Slow-cooked rice pudding with nuts.", Decimal("180.00"), "kheer.jpg"
        ),
        DefaultMenuItem(
            "Chocolate Brownie",
            "Fudgy chocolate brownie.",
            Decimal("250.00"),
            "chocolate-brownie.jpg",
        ),
        DefaultMenuItem(
            "Fruit Trifle",
            "Layers of sponge, custard, cream and fresh fruit.",
            Decimal("220.00"),
            "fruit-trifle.jpg",
        ),
    ],
    "Drinks": [
        DefaultMenuItem(
            "Doodh Patti Chai",
            "Strong milk tea brewed the traditional way.",
            Decimal("80.00"),
            "doodh-patti-chai.jpg",
        ),
        DefaultMenuItem(
            "Mango Lassi",
            "Chilled yogurt drink blended with mango.",
            Decimal("220.00"),
            "mango-lassi.jpg",
        ),
        DefaultMenuItem(
            "Mint Margarita",
            "Refreshing lemon and fresh mint cooler.",
            Decimal("200.00"),
            "mint-margarita.jpg",
        ),
    ],
    "Desi": [
        DefaultMenuItem(
            "Chicken Karahi",
            "Chicken cooked in a wok with tomatoes, ginger and green chillies.",
            Decimal("750.00"),
            "chicken-karahi.jpg",
        ),
        DefaultMenuItem(
            "Beef Nihari",
            "Slow-cooked beef shank stew, served with naan.",
            Decimal("600.00"),
            "beef-nihari.jpg",
        ),
        DefaultMenuItem(
            "Daal Mash",
            "Tempered white lentils finished with butter.",
            Decimal("300.00"),
            "daal-mash.jpg",
        ),
        DefaultMenuItem(
            "Haleem",
            "Slow-cooked wheat, lentils and meat, topped with fried onions.",
            Decimal("350.00"),
            "haleem.jpg",
        ),
    ],
}


@dataclass
class SeedResult:
    categories_created: int = 0
    items_created: int = 0
    images_attached: int = 0
    images_refreshed: int = 0
    prices_set: int = 0


# Audit actions written by MenuService when a manager changes an item photo.
_MANUAL_IMAGE_ACTIONS = frozenset({"menu_item.image_updated", "menu_item.image_removed"})


class DefaultMenuSeeder:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.categories = MenuCategoryRepository(db)
        self.items = MenuItemRepository(db)
        self.item_locations = MenuItemLocationRepository(db)
        self.audit = AuditService(db)
        self.storage = menu_image_storage()

    async def _image_managed_manually(self, item_id: uuid.UUID) -> bool:
        history = await self.audit.search(entity_type="menu_item", entity_id=str(item_id))
        return any(entry.action in _MANUAL_IMAGE_ACTIONS for entry in history)

    async def seed_location(
        self,
        location: Location,
        *,
        actor_employee_id: uuid.UUID | None = None,
        refresh_images: bool = False,
    ) -> SeedResult:
        """`refresh_images` replaces previously seeded photos with the
        current bundled ones (e.g. after the seed images are updated)."""
        result = SeedResult()
        existing = {c.name: c for c in await self.categories.list_for_location(location.id)}

        for order, (category_name, defaults) in enumerate(DEFAULT_MENU.items()):
            category = existing.get(category_name)
            if category is None:
                category = MenuCategory(
                    location_id=location.id, name=category_name, display_order=order
                )
                self.categories.add(category)
                await self.categories.flush()
                result.categories_created += 1

            items_by_name = {i.name: i for i in await self.items.list_for_category(category.id)}
            for default in defaults:
                item = items_by_name.get(default.name)
                if item is None:
                    item = MenuItem(
                        category_id=category.id,
                        name=default.name,
                        description=default.description,
                    )
                    self.items.add(item)
                    await self.items.flush()
                    result.items_created += 1

                # A photo a manager uploaded or removed is theirs -- never
                # re-attach or overwrite it.
                if item.image_url is None or refresh_images:
                    if not await self._image_managed_manually(item.id):
                        seed_bytes = (SEED_IMAGE_DIR / default.image).read_bytes()
                        if item.image_url is None:
                            item.image_url = self.storage.save(seed_bytes)
                            result.images_attached += 1
                        else:
                            old_url = item.image_url
                            item.image_url = self.storage.save(seed_bytes)
                            self.storage.delete(old_url)
                            result.images_refreshed += 1

                if await self.item_locations.get(item.id, location.id) is None:
                    self.item_locations.add(
                        MenuItemLocation(
                            menu_item_id=item.id,
                            location_id=location.id,
                            is_available=True,
                            price=default.price,
                        )
                    )
                    result.prices_set += 1

        await self.items.flush()
        await self.audit.record(
            action="menu.default_seeded",
            entity_type="location",
            entity_id=str(location.id),
            actor_employee_id=actor_employee_id,
            new_values={
                "categories_created": result.categories_created,
                "items_created": result.items_created,
                "images_attached": result.images_attached,
                "images_refreshed": result.images_refreshed,
                "prices_set": result.prices_set,
            },
        )
        return result
