from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.enums import EmployeeRole
from app.models.location import Location
from app.models.menu import MenuCategory, MenuItem, MenuItemLocation
from app.services.menu.default_menu import DEFAULT_MENU, DefaultMenuSeeder
from app.services.menu.menu_service import MenuService
from tests.conftest import SeedEmployee

API = "/api/v1"
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture(autouse=True)
def _media_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(get_settings(), "media_root", str(tmp_path))
    return tmp_path


async def _login(client: AsyncClient, p_no: str, password: str) -> dict[str, str]:
    resp = await client.post(f"{API}/auth/login", json={"p_no": p_no, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _location_with_item(client: AsyncClient, headers: dict[str, str]) -> tuple[str, str]:
    location = await client.post(
        f"{API}/locations", json={"name": "Image Mess", "code": "IMG1"}, headers=headers
    )
    location_id = location.json()["id"]
    category = await client.post(
        f"{API}/locations/{location_id}/menu-categories", json={"name": "BBQ"}, headers=headers
    )
    item = await client.post(
        f"{API}/locations/{location_id}/menu-categories/{category.json()['id']}/items",
        json={"name": "Chicken Tikka"},
        headers=headers,
    )
    item_id = item.json()["id"]
    await client.put(
        f"{API}/locations/{location_id}/menu-items/{item_id}/availability",
        json={"price": "420.00"},
        headers=headers,
    )
    return location_id, item_id


async def test_manager_uploads_replaces_and_removes_item_image(
    client: AsyncClient, seed_active_employee: SeedEmployee, _media_root: Path
) -> None:
    admin, password = await seed_active_employee(
        p_no="ADM-IMG", email="admimg@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    headers = await _login(client, admin.p_no, password)
    location_id, item_id = await _location_with_item(client, headers)
    image_url = f"{API}/locations/{location_id}/menu-items/{item_id}/image"

    first = await client.put(
        image_url, files={"file": ("tikka.jpg", JPEG_BYTES, "image/jpeg")}, headers=headers
    )
    assert first.status_code == 200, first.text
    first_url = first.json()["image_url"]
    assert first_url.startswith("/media/menu/") and first_url.endswith(".jpg")
    first_file = _media_root / "menu" / first_url.rsplit("/", 1)[1]
    assert first_file.read_bytes() == JPEG_BYTES

    browse = await client.get(f"{API}/locations/{location_id}/menu/browse", headers=headers)
    assert browse.json()[0]["items"][0]["image_url"] == first_url

    replaced = await client.put(
        image_url, files={"file": ("tikka.png", PNG_BYTES, "image/png")}, headers=headers
    )
    assert replaced.json()["image_url"].endswith(".png")
    assert not first_file.exists()

    removed = await client.delete(image_url, headers=headers)
    assert removed.status_code == 200
    assert removed.json()["image_url"] is None
    assert list((_media_root / "menu").iterdir()) == []


async def test_image_upload_rejects_non_images_and_non_managers(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, password = await seed_active_employee(
        p_no="ADM-IMG2", email="admimg2@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    employee, employee_password = await seed_active_employee(
        p_no="EMP-IMG2", email="empimg2@example.com"
    )
    headers = await _login(client, admin.p_no, password)
    location_id, item_id = await _location_with_item(client, headers)
    image_url = f"{API}/locations/{location_id}/menu-items/{item_id}/image"

    # Content-Type claims an image, but the bytes aren't one.
    fake = await client.put(
        image_url,
        files={"file": ("x.jpg", b"<script>alert(1)</script>", "image/jpeg")},
        headers=headers,
    )
    assert fake.status_code == 422

    employee_headers = await _login(client, employee.p_no, employee_password)
    forbidden = await client.put(
        image_url, files={"file": ("x.jpg", JPEG_BYTES, "image/jpeg")}, headers=employee_headers
    )
    assert forbidden.status_code == 403


async def test_default_menu_seed_is_complete_and_idempotent(
    db_session: AsyncSession, _media_root: Path
) -> None:
    location = Location(name="Seed Mess", code="SEED1")
    db_session.add(location)
    await db_session.flush()

    seeder = DefaultMenuSeeder(db_session)
    first = await seeder.seed_location(location)
    expected_items = sum(len(items) for items in DEFAULT_MENU.values())
    assert first.categories_created == len(DEFAULT_MENU) == 8
    assert first.items_created == first.images_attached == first.prices_set == expected_items
    assert all(2 <= len(items) <= 4 for items in DEFAULT_MENU.values())

    second = await seeder.seed_location(location)
    assert (second.categories_created, second.items_created) == (0, 0)
    assert (second.images_attached, second.prices_set) == (0, 0)

    category_count = await db_session.scalar(
        select(func.count())
        .select_from(MenuCategory)
        .where(MenuCategory.location_id == location.id)
    )
    priced = await db_session.scalar(
        select(func.count())
        .select_from(MenuItemLocation)
        .where(MenuItemLocation.location_id == location.id)
    )
    missing_images = await db_session.scalar(
        select(func.count()).select_from(MenuItem).where(MenuItem.image_url.is_(None))
    )
    assert category_count == 8
    assert priced == expected_items
    assert missing_images == 0
    assert len(list((_media_root / "menu").iterdir())) == expected_items


async def test_refresh_images_replaces_seeded_photos_but_never_manager_ones(
    db_session: AsyncSession, _media_root: Path
) -> None:
    location = Location(name="Refresh Mess", code="SEED2")
    db_session.add(location)
    await db_session.flush()
    seeder = DefaultMenuSeeder(db_session)
    await seeder.seed_location(location)

    items = {i.name: i for i in (await db_session.scalars(select(MenuItem))).all()}
    manager_id = None
    menu = MenuService(db_session)
    # A manager replaces one photo and removes another.
    await menu.set_item_image(
        item_id=items["Haleem"].id, image_data=PNG_BYTES, updated_by_id=manager_id
    )
    await menu.remove_item_image(item_id=items["Kheer"].id, updated_by_id=manager_id)
    manager_haleem_url = items["Haleem"].image_url
    seeded_biryani_url = items["Chicken Biryani"].image_url

    expected_items = sum(len(v) for v in DEFAULT_MENU.values())
    result = await seeder.seed_location(location, refresh_images=True)
    assert result.images_refreshed == expected_items - 2
    assert result.images_attached == 0

    assert items["Haleem"].image_url == manager_haleem_url
    assert items["Kheer"].image_url is None
    assert items["Chicken Biryani"].image_url != seeded_biryani_url
    # Old seeded files are cleaned up: one file per item that has a photo.
    assert len(list((_media_root / "menu").iterdir())) == expected_items - 1

    # A plain re-run doesn't re-attach the photo the manager removed.
    again = await seeder.seed_location(location)
    assert (again.images_attached, again.images_refreshed) == (0, 0)
