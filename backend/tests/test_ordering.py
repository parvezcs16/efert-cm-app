from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from app.models.enums import EmployeeRole
from tests.conftest import SeedEmployee

API = "/api/v1"


async def _login(client: AsyncClient, p_no: str, password: str) -> dict[str, str]:
    resp = await client.post(f"{API}/auth/login", json={"p_no": p_no, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _setup_orderable_item(
    client: AsyncClient, admin_headers: dict[str, str]
) -> tuple[str, str]:
    """Returns (location_id, menu_item_id) for an item priced and available
    for ordering."""
    location = (
        await client.post(
            f"{API}/locations", json={"name": "Ordering Branch", "code": f"OB-{id(client)}"},
            headers=admin_headers,
        )
    ).json()
    category = (
        await client.post(
            f"{API}/locations/{location['id']}/menu-categories",
            json={"name": "Mains", "display_order": 1},
            headers=admin_headers,
        )
    ).json()
    item = (
        await client.post(
            f"{API}/locations/{location['id']}/menu-categories/{category['id']}/items",
            json={"name": "Daal Chawal", "description": "Lentils and rice"},
            headers=admin_headers,
        )
    ).json()
    await client.put(
        f"{API}/locations/{location['id']}/menu-items/{item['id']}/availability",
        json={"is_available": True, "price": "120.00"},
        headers=admin_headers,
    )
    return location["id"], item["id"]


async def test_employee_can_browse_menu_without_prices(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-020", email="admin20@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    location_id, _ = await _setup_orderable_item(client, admin_headers)

    employee, password = await seed_active_employee(p_no="EMP-020", email="emp20@example.com")
    headers = await _login(client, employee.p_no, password)

    browse = await client.get(f"{API}/locations/{location_id}/menu/browse", headers=headers)
    assert browse.status_code == 200, browse.text
    body = browse.json()
    assert len(body) == 1
    assert body[0]["items"][0]["name"] == "Daal Chawal"
    assert "price" not in body[0]["items"][0]


async def test_employee_places_dine_in_order_and_views_history(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-021", email="admin21@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    location_id, item_id = await _setup_orderable_item(client, admin_headers)

    employee, password = await seed_active_employee(p_no="EMP-021", email="emp21@example.com")
    headers = await _login(client, employee.p_no, password)

    create = await client.post(
        f"{API}/orders",
        json={
            "location_id": location_id,
            "order_type": "DINE_IN",
            "items": [{"menu_item_id": item_id, "quantity": 2}],
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    order = create.json()
    assert order["status"] == "PENDING"
    assert order["items"][0]["ordered_quantity"] == 2
    assert "unit_price" not in order["items"][0]

    history = await client.get(f"{API}/orders", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["order_number"] == order["order_number"]

    detail = await client.get(f"{API}/orders/{order['id']}", headers=headers)
    assert detail.status_code == 200


async def test_book_for_later_requires_future_scheduled_time(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-022", email="admin22@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    location_id, item_id = await _setup_orderable_item(client, admin_headers)

    employee, password = await seed_active_employee(p_no="EMP-022", email="emp22@example.com")
    headers = await _login(client, employee.p_no, password)

    missing_schedule = await client.post(
        f"{API}/orders",
        json={
            "location_id": location_id,
            "order_type": "BOOK_FOR_LATER",
            "items": [{"menu_item_id": item_id, "quantity": 1}],
        },
        headers=headers,
    )
    assert missing_schedule.status_code == 422

    past_schedule = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    in_past = await client.post(
        f"{API}/orders",
        json={
            "location_id": location_id,
            "order_type": "BOOK_FOR_LATER",
            "scheduled_for": past_schedule,
            "items": [{"menu_item_id": item_id, "quantity": 1}],
        },
        headers=headers,
    )
    assert in_past.status_code == 422

    future_schedule = (datetime.now(UTC) + timedelta(hours=3)).isoformat()
    booked = await client.post(
        f"{API}/orders",
        json={
            "location_id": location_id,
            "order_type": "BOOK_FOR_LATER",
            "scheduled_for": future_schedule,
            "items": [{"menu_item_id": item_id, "quantity": 1}],
        },
        headers=headers,
    )
    assert booked.status_code == 201, booked.text


async def test_ordering_unavailable_item_is_rejected(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-023", email="admin23@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    location_id, item_id = await _setup_orderable_item(client, admin_headers)

    await client.put(
        f"{API}/locations/{location_id}/menu-items/{item_id}/availability",
        json={"is_available": False, "price": "120.00"},
        headers=admin_headers,
    )

    employee, password = await seed_active_employee(p_no="EMP-023", email="emp23@example.com")
    headers = await _login(client, employee.p_no, password)

    response = await client.post(
        f"{API}/orders",
        json={
            "location_id": location_id,
            "order_type": "TAKEAWAY",
            "items": [{"menu_item_id": item_id, "quantity": 1}],
        },
        headers=headers,
    )
    assert response.status_code == 422


async def test_cancel_order_and_reject_double_cancel(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-024", email="admin24@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    location_id, item_id = await _setup_orderable_item(client, admin_headers)

    employee, password = await seed_active_employee(p_no="EMP-024", email="emp24@example.com")
    headers = await _login(client, employee.p_no, password)

    order = (
        await client.post(
            f"{API}/orders",
            json={
                "location_id": location_id,
                "order_type": "TAKEAWAY",
                "items": [{"menu_item_id": item_id, "quantity": 1}],
            },
            headers=headers,
        )
    ).json()

    cancel = await client.post(f"{API}/orders/{order['id']}/cancel", headers=headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "CANCELLED"

    cancel_again = await client.post(f"{API}/orders/{order['id']}/cancel", headers=headers)
    assert cancel_again.status_code == 422


async def test_employee_cannot_see_or_cancel_others_orders(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-025", email="admin25@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    location_id, item_id = await _setup_orderable_item(client, admin_headers)

    owner, owner_password = await seed_active_employee(p_no="EMP-026", email="emp26@example.com")
    owner_headers = await _login(client, owner.p_no, owner_password)
    order = (
        await client.post(
            f"{API}/orders",
            json={
                "location_id": location_id,
                "order_type": "TAKEAWAY",
                "items": [{"menu_item_id": item_id, "quantity": 1}],
            },
            headers=owner_headers,
        )
    ).json()

    intruder, intruder_password = await seed_active_employee(
        p_no="EMP-027", email="emp27@example.com"
    )
    intruder_headers = await _login(client, intruder.p_no, intruder_password)

    get_resp = await client.get(f"{API}/orders/{order['id']}", headers=intruder_headers)
    assert get_resp.status_code == 404

    cancel_resp = await client.post(f"{API}/orders/{order['id']}/cancel", headers=intruder_headers)
    assert cancel_resp.status_code == 404


async def test_employee_removes_items_and_reduces_quantity_until_queued(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-028", email="admin28@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    location_id, item_id = await _setup_orderable_item(client, admin_headers)

    employee, password = await seed_active_employee(p_no="EMP-028", email="emp28@example.com")
    headers = await _login(client, employee.p_no, password)

    order = (
        await client.post(
            f"{API}/orders",
            json={
                "location_id": location_id,
                "order_type": "DINE_IN",
                "items": [
                    {"menu_item_id": item_id, "quantity": 3},
                    {"menu_item_id": item_id, "quantity": 1},
                ],
            },
            headers=headers,
        )
    ).json()
    assert order["items"][0]["menu_item_name"] == "Daal Chawal"
    keep, drop = order["items"]

    confirm = await client.post(f"{API}/orders/{order['id']}/confirm", headers=admin_headers)
    assert confirm.status_code == 200, confirm.text

    increase = await client.put(
        f"{API}/orders/{order['id']}/items",
        json={"items": [{"order_item_id": keep["id"], "quantity": 4}]},
        headers=headers,
    )
    assert increase.status_code == 422

    update = await client.put(
        f"{API}/orders/{order['id']}/items",
        json={"items": [{"order_item_id": keep["id"], "quantity": 2}]},
        headers=headers,
    )
    assert update.status_code == 200, update.text
    body = update.json()
    assert body["status"] == "CONFIRMED"
    assert [(i["id"], i["ordered_quantity"]) for i in body["items"]] == [(keep["id"], 2)]
    assert drop["id"] not in {i["id"] for i in body["items"]}

    empty = await client.put(
        f"{API}/orders/{order['id']}/items", json={"items": []}, headers=headers
    )
    assert empty.status_code == 422
