"""Seed the default menu (see app/services/menu/default_menu.py) into one or
all locations.

    python -m app.scripts.seed_default_menu              # every location
    python -m app.scripts.seed_default_menu --location MAIN1
    python -m app.scripts.seed_default_menu --refresh-images   # swap in updated seed photos

Safe to re-run: existing categories, items and prices are kept, and photos a
manager uploaded or removed are never touched.
"""

import argparse
import asyncio
import sys

from app.core.database import AsyncSessionLocal, engine
from app.repositories.location_repository import LocationRepository
from app.services.menu.default_menu import DefaultMenuSeeder


async def _run(location_code: str | None, refresh_images: bool) -> int:
    async with AsyncSessionLocal() as session:
        repo = LocationRepository(session)
        if location_code:
            location = await repo.get_by_code(location_code)
            if location is None:
                print(f"No location with code {location_code!r}", file=sys.stderr)
                return 1
            locations = [location]
        else:
            locations = await repo.list_all()

        if not locations:
            print("No locations exist yet -- create one first.", file=sys.stderr)
            return 1

        seeder = DefaultMenuSeeder(session)
        for location in locations:
            result = await seeder.seed_location(location, refresh_images=refresh_images)
            print(
                f"{location.code}: {result.categories_created} categories, "
                f"{result.items_created} items, {result.images_attached} images, "
                f"{result.images_refreshed} images refreshed, "
                f"{result.prices_set} prices added"
            )
        await session.commit()

    await engine.dispose()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--location", help="Location code to seed (default: all locations)")
    parser.add_argument(
        "--refresh-images",
        action="store_true",
        help="Replace previously seeded photos with the current bundled ones",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.location, args.refresh_images)))


if __name__ == "__main__":
    main()
