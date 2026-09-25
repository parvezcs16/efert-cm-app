from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from starlette.testclient import TestClient

from app.main import app
from app.models.enums import EmployeeRole
from tests.conftest import SeedEmployee

API = "/api/v1"


async def _login(client: AsyncClient, p_no: str, password: str) -> dict[str, str]:
    resp = await client.post(f"{API}/auth/login", json={"p_no": p_no, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _setup_orderable_item(
    client: AsyncClient, admin_headers: dict[str, str], code: str
) -> dict[str, str]:
    location = (
        await client.post(
            f"{API}/locations", json={"name": f"Booking Branch {code}", "code": code},
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
            json={"name": "Karahi", "description": None},
            headers=admin_headers,
        )
    ).json()
    await client.put(
        f"{API}/locations/{location['id']}/menu-items/{item['id']}/availability",
        json={"is_available": True, "price": "500.00"},
        headers=admin_headers,
    )
    return {"location_id": location["id"], "item_id": item["id"]}


async def _place_booking(
    client: AsyncClient, headers: dict[str, str], location_id: str, item_id: str
) -> dict:
    future = (datetime.now(UTC) + timedelta(hours=4)).isoformat()
    resp = await client.post(
        f"{API}/orders",
        json={
            "location_id": location_id,
            "order_type": "BOOK_FOR_LATER",
            "scheduled_for": future,
            "items": [{"menu_item_id": item_id, "quantity": 1}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_booked_order_starts_pending_ingredient_review(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-060", email="admin60@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_orderable_item(client, admin_headers, "BK1")

    employee, password = await seed_active_employee(p_no="EMP-060", email="emp60@example.com")
    headers = await _login(client, employee.p_no, password)
    order = await _place_booking(client, headers, setup["location_id"], setup["item_id"])

    assert order["ingredient_status"] == "PENDING"


async def test_kitchen_confirm_blocked_until_ingredients_confirmed(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-061", email="admin61@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_orderable_item(client, admin_headers, "BK2")

    employee, password = await seed_active_employee(p_no="EMP-061", email="emp61@example.com")
    headers = await _login(client, employee.p_no, password)
    order = await _place_booking(client, headers, setup["location_id"], setup["item_id"])

    manager, m_password = await seed_active_employee(
        p_no="MGR-061", email="mgr61@example.com", role=EmployeeRole.SYSTEM_MANAGER
    )
    manager_headers = await _login(client, manager.p_no, m_password)

    blocked = await client.post(f"{API}/orders/{order['id']}/confirm", headers=manager_headers)
    assert blocked.status_code == 422

    confirm_ingredients = await client.post(
        f"{API}/orders/{order['id']}/booking/confirm-ingredients", headers=manager_headers
    )
    assert confirm_ingredients.status_code == 200
    assert confirm_ingredients.json()["ingredient_status"] == "CONFIRMED"

    allowed = await client.post(f"{API}/orders/{order['id']}/confirm", headers=manager_headers)
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "CONFIRMED"


async def test_manager_delay_updates_scheduled_time_and_notifies_employee(
    client: AsyncClient, seed_active_employee: SeedEmployee, outbox: list[dict[str, str]]
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-062", email="admin62@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_orderable_item(client, admin_headers, "BK3")

    employee, password = await seed_active_employee(p_no="EMP-062", email="emp62@example.com")
    headers = await _login(client, employee.p_no, password)
    order = await _place_booking(client, headers, setup["location_id"], setup["item_id"])

    manager, m_password = await seed_active_employee(
        p_no="MGR-062", email="mgr62@example.com", role=EmployeeRole.SYSTEM_MANAGER
    )
    manager_headers = await _login(client, manager.p_no, m_password)

    new_time = (datetime.now(UTC) + timedelta(hours=6)).isoformat()
    delay = await client.post(
        f"{API}/orders/{order['id']}/booking/delay",
        json={"new_scheduled_for": new_time, "reason": "Ingredients out of stock"},
        headers=manager_headers,
    )
    assert delay.status_code == 200, delay.text
    body = delay.json()
    assert body["ingredient_status"] == "DELAYED"
    assert body["ingredient_response_message"] == "Ingredients out of stock"

    delay_email = next(e for e in outbox if e["to"] == "emp62@example.com")
    assert "delayed" in delay_email["subject"].lower()


async def test_confirming_ingredients_twice_fails(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-063", email="admin63@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_orderable_item(client, admin_headers, "BK4")

    employee, password = await seed_active_employee(p_no="EMP-063", email="emp63@example.com")
    headers = await _login(client, employee.p_no, password)
    order = await _place_booking(client, headers, setup["location_id"], setup["item_id"])

    manager, m_password = await seed_active_employee(
        p_no="MGR-063", email="mgr63@example.com", role=EmployeeRole.SYSTEM_MANAGER
    )
    manager_headers = await _login(client, manager.p_no, m_password)

    first = await client.post(
        f"{API}/orders/{order['id']}/booking/confirm-ingredients", headers=manager_headers
    )
    assert first.status_code == 200

    second = await client.post(
        f"{API}/orders/{order['id']}/booking/confirm-ingredients", headers=manager_headers
    )
    assert second.status_code == 422


async def test_ingredient_confirmation_rejected_for_non_booked_order(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-064", email="admin64@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_orderable_item(client, admin_headers, "BK5")

    employee, password = await seed_active_employee(p_no="EMP-064", email="emp64@example.com")
    headers = await _login(client, employee.p_no, password)
    immediate_order = await client.post(
        f"{API}/orders",
        json={
            "location_id": setup["location_id"],
            "order_type": "TAKEAWAY",
            "items": [{"menu_item_id": setup["item_id"], "quantity": 1}],
        },
        headers=headers,
    )
    order = immediate_order.json()

    manager, m_password = await seed_active_employee(
        p_no="MGR-064", email="mgr64@example.com", role=EmployeeRole.SYSTEM_MANAGER
    )
    manager_headers = await _login(client, manager.p_no, m_password)

    response = await client.post(
        f"{API}/orders/{order['id']}/booking/confirm-ingredients", headers=manager_headers
    )
    assert response.status_code == 422


async def test_pending_bookings_listing_for_location(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-066", email="admin66@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_orderable_item(client, admin_headers, "BK7")

    employee, password = await seed_active_employee(p_no="EMP-066", email="emp66@example.com")
    headers = await _login(client, employee.p_no, password)
    booked = await _place_booking(client, headers, setup["location_id"], setup["item_id"])
    immediate_order = await client.post(
        f"{API}/orders",
        json={
            "location_id": setup["location_id"],
            "order_type": "TAKEAWAY",
            "items": [{"menu_item_id": setup["item_id"], "quantity": 1}],
        },
        headers=headers,
    )
    assert immediate_order.status_code == 201

    manager, m_password = await seed_active_employee(
        p_no="MGR-066", email="mgr66@example.com", role=EmployeeRole.SYSTEM_MANAGER
    )
    manager_headers = await _login(client, manager.p_no, m_password)

    pending = await client.get(
        f"{API}/locations/{setup['location_id']}/bookings/pending", headers=manager_headers
    )
    assert pending.status_code == 200, pending.text
    order_ids = [o["id"] for o in pending.json()]
    assert order_ids == [booked["id"]]

    await client.post(
        f"{API}/orders/{booked['id']}/booking/confirm-ingredients", headers=manager_headers
    )

    after_confirm = await client.get(
        f"{API}/locations/{setup['location_id']}/bookings/pending", headers=manager_headers
    )
    assert after_confirm.json() == []


async def test_booking_alert_broadcast_on_creation(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-065", email="admin65@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_orderable_item(client, admin_headers, "BK6")

    manager, m_password = await seed_active_employee(
        p_no="MGR-065", email="mgr65@example.com", role=EmployeeRole.SYSTEM_MANAGER
    )
    manager_token = (await _login(client, manager.p_no, m_password))["Authorization"].split(
        " "
    )[1]

    employee, e_password = await seed_active_employee(p_no="EMP-065", email="emp65@example.com")
    headers = await _login(client, employee.p_no, e_password)

    sync_client = TestClient(app)
    with sync_client.websocket_connect(
        f"/ws/kitchen/{setup['location_id']}?token={manager_token}"
    ) as websocket:
        order = await _place_booking(client, headers, setup["location_id"], setup["item_id"])

        message = websocket.receive_json()
        assert message["type"] == "booking.alert"
        assert message["order_id"] == order["id"]
