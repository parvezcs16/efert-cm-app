from httpx import AsyncClient

from app.models.enums import EmployeeRole
from tests.conftest import SeedEmployee

API = "/api/v1"


async def _login(client: AsyncClient, p_no: str, password: str) -> dict[str, str]:
    resp = await client.post(f"{API}/auth/login", json={"p_no": p_no, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_system_admin_creates_location_and_assigns_manager(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-010", email="admin10@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    manager, _ = await seed_active_employee(
        p_no="MGR-010", email="mgr10@example.com", role=EmployeeRole.LOCATION_MANAGER
    )
    admin_headers = await _login(client, admin.p_no, admin_password)

    create = await client.post(
        f"{API}/locations", json={"name": "Head Office Mess", "code": "HOM"}, headers=admin_headers
    )
    assert create.status_code == 201, create.text
    location_id = create.json()["id"]

    duplicate = await client.post(
        f"{API}/locations", json={"name": "Dup", "code": "HOM"}, headers=admin_headers
    )
    assert duplicate.status_code == 409

    assign = await client.patch(
        f"{API}/locations/{location_id}",
        json={"manager_id": str(manager.id)},
        headers=admin_headers,
    )
    assert assign.status_code == 200
    assert assign.json()["manager_id"] == str(manager.id)


async def test_non_admin_cannot_create_location(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    employee, password = await seed_active_employee(p_no="EMP-010", email="emp10@example.com")
    headers = await _login(client, employee.p_no, password)

    response = await client.post(
        f"{API}/locations", json={"name": "Somewhere", "code": "SW1"}, headers=headers
    )
    assert response.status_code == 403


async def test_assigning_ineligible_role_as_manager_is_rejected(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-011", email="admin11@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    regular, _ = await seed_active_employee(p_no="EMP-011", email="emp11@example.com")
    headers = await _login(client, admin.p_no, admin_password)

    create = await client.post(
        f"{API}/locations", json={"name": "Branch A", "code": "BRA"}, headers=headers
    )
    location_id = create.json()["id"]

    assign = await client.patch(
        f"{API}/locations/{location_id}",
        json={"manager_id": str(regular.id)},
        headers=headers,
    )
    assert assign.status_code == 422


async def test_location_manager_scoped_to_own_location(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-012", email="admin12@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    manager_a, manager_a_password = await seed_active_employee(
        p_no="MGR-012A", email="mgra12@example.com", role=EmployeeRole.LOCATION_MANAGER
    )
    admin_headers = await _login(client, admin.p_no, admin_password)

    loc_a = (
        await client.post(
            f"{API}/locations", json={"name": "Branch A2", "code": "BRA2"}, headers=admin_headers
        )
    ).json()
    loc_b = (
        await client.post(
            f"{API}/locations", json={"name": "Branch B2", "code": "BRB2"}, headers=admin_headers
        )
    ).json()

    await client.patch(
        f"{API}/locations/{loc_a['id']}",
        json={"manager_id": str(manager_a.id)},
        headers=admin_headers,
    )

    manager_headers = await _login(client, manager_a.p_no, manager_a_password)

    own_location = await client.post(
        f"{API}/locations/{loc_a['id']}/kitchen-stations",
        json={"name": "Grill Station"},
        headers=manager_headers,
    )
    assert own_location.status_code == 201, own_location.text

    other_location = await client.post(
        f"{API}/locations/{loc_b['id']}/kitchen-stations",
        json={"name": "Grill Station"},
        headers=manager_headers,
    )
    assert other_location.status_code == 403


async def test_menu_category_item_and_pricing_flow(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-013", email="admin13@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    headers = await _login(client, admin.p_no, admin_password)

    location = (
        await client.post(
            f"{API}/locations", json={"name": "Branch C", "code": "BRC"}, headers=headers
        )
    ).json()
    location_id = location["id"]

    category = await client.post(
        f"{API}/locations/{location_id}/menu-categories",
        json={"name": "Beverages", "display_order": 1},
        headers=headers,
    )
    assert category.status_code == 201, category.text
    category_id = category.json()["id"]

    duplicate_category = await client.post(
        f"{API}/locations/{location_id}/menu-categories",
        json={"name": "Beverages", "display_order": 2},
        headers=headers,
    )
    assert duplicate_category.status_code == 409

    item = await client.post(
        f"{API}/locations/{location_id}/menu-categories/{category_id}/items",
        json={"name": "Masala Chai", "description": "Spiced tea"},
        headers=headers,
    )
    assert item.status_code == 201, item.text
    item_id = item.json()["id"]

    availability = await client.put(
        f"{API}/locations/{location_id}/menu-items/{item_id}/availability",
        json={"is_available": True, "price": "45.00"},
        headers=headers,
    )
    assert availability.status_code == 200, availability.text
    assert availability.json()["price"] == "45.00"

    listing = await client.get(
        f"{API}/locations/{location_id}/menu-items/availability", headers=headers
    )
    assert listing.status_code == 200
    assert any(entry["menu_item_id"] == item_id for entry in listing.json())


async def test_publishing_menu_limits_browse_and_ordering_to_selected_dishes(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-014", email="admin14@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    employee, employee_password = await seed_active_employee(
        p_no="EMP-014", email="emp14@example.com"
    )
    headers = await _login(client, admin.p_no, admin_password)
    employee_headers = await _login(client, employee.p_no, employee_password)

    location_id = (
        await client.post(
            f"{API}/locations", json={"name": "Branch D", "code": "BRD"}, headers=headers
        )
    ).json()["id"]
    category_id = (
        await client.post(
            f"{API}/locations/{location_id}/menu-categories",
            json={"name": "Mains"},
            headers=headers,
        )
    ).json()["id"]

    item_ids: dict[str, str] = {}
    for name in ("Biryani", "Karahi", "Daal"):
        item_id = (
            await client.post(
                f"{API}/locations/{location_id}/menu-categories/{category_id}/items",
                json={"name": name},
                headers=headers,
            )
        ).json()["id"]
        await client.put(
            f"{API}/locations/{location_id}/menu-items/{item_id}/availability",
            json={"is_available": True, "price": "300.00"},
            headers=headers,
        )
        item_ids[name] = item_id

    publish = await client.put(
        f"{API}/locations/{location_id}/menu/published",
        json={"menu_item_ids": [item_ids["Biryani"], item_ids["Daal"]]},
        headers=headers,
    )
    assert publish.status_code == 200, publish.text
    live = {e["menu_item_id"]: e["is_available"] for e in publish.json()}
    assert live == {item_ids["Biryani"]: True, item_ids["Karahi"]: False, item_ids["Daal"]: True}

    browse = await client.get(
        f"{API}/locations/{location_id}/menu/browse", headers=employee_headers
    )
    assert browse.status_code == 200
    assert sorted(i["name"] for c in browse.json() for i in c["items"]) == ["Biryani", "Daal"]

    # The unpublished dish stays in the catalog for the admin.
    catalog = await client.get(
        f"{API}/locations/{location_id}/menu-categories/{category_id}/items", headers=headers
    )
    assert len(catalog.json()) == 3

    # Employees can't publish.
    forbidden = await client.put(
        f"{API}/locations/{location_id}/menu/published",
        json={"menu_item_ids": []},
        headers=employee_headers,
    )
    assert forbidden.status_code == 403


async def test_publishing_unpriced_item_is_rejected_without_changes(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-015", email="admin15@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    headers = await _login(client, admin.p_no, admin_password)

    location_id = (
        await client.post(
            f"{API}/locations", json={"name": "Branch E", "code": "BRE"}, headers=headers
        )
    ).json()["id"]
    category_id = (
        await client.post(
            f"{API}/locations/{location_id}/menu-categories",
            json={"name": "Snacks"},
            headers=headers,
        )
    ).json()["id"]
    priced_id = (
        await client.post(
            f"{API}/locations/{location_id}/menu-categories/{category_id}/items",
            json={"name": "Samosa"},
            headers=headers,
        )
    ).json()["id"]
    await client.put(
        f"{API}/locations/{location_id}/menu-items/{priced_id}/availability",
        json={"is_available": True, "price": "60.00"},
        headers=headers,
    )
    unpriced_id = (
        await client.post(
            f"{API}/locations/{location_id}/menu-categories/{category_id}/items",
            json={"name": "Pakora"},
            headers=headers,
        )
    ).json()["id"]

    rejected = await client.put(
        f"{API}/locations/{location_id}/menu/published",
        json={"menu_item_ids": [unpriced_id]},
        headers=headers,
    )
    assert rejected.status_code == 422

    listing = await client.get(
        f"{API}/locations/{location_id}/menu-items/availability", headers=headers
    )
    assert [e["is_available"] for e in listing.json()] == [True]
