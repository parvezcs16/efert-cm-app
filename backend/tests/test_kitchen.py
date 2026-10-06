from httpx import AsyncClient

from app.models.enums import EmployeeRole
from tests.conftest import SeedEmployee

API = "/api/v1"


async def _login(client: AsyncClient, p_no: str, password: str) -> dict[str, str]:
    resp = await client.post(f"{API}/auth/login", json={"p_no": p_no, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _setup_location_with_item_and_station(
    client: AsyncClient, admin_headers: dict[str, str], *, code: str
) -> dict[str, str]:
    location = (
        await client.post(
            f"{API}/locations", json={"name": f"Kitchen Branch {code}", "code": code},
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
            json={"name": "Biryani", "description": None},
            headers=admin_headers,
        )
    ).json()
    await client.put(
        f"{API}/locations/{location['id']}/menu-items/{item['id']}/availability",
        json={"is_available": True, "price": "150.00"},
        headers=admin_headers,
    )
    station = (
        await client.post(
            f"{API}/locations/{location['id']}/kitchen-stations",
            json={"name": "Main Kitchen"},
            headers=admin_headers,
        )
    ).json()
    return {"location_id": location["id"], "item_id": item["id"], "station_id": station["id"]}


async def _place_order(
    client: AsyncClient,
    headers: dict[str, str],
    location_id: str,
    item_id: str,
    order_type: str = "DINE_IN",
) -> dict:
    resp = await client.post(
        f"{API}/orders",
        json={
            "location_id": location_id,
            "order_type": order_type,
            "items": [{"menu_item_id": item_id, "quantity": 1}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_incoming_orders_lists_pending_and_confirmed_excludes_unconfirmed_bookings(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-036", email="admin36@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_with_item_and_station(client, admin_headers, code="KB7")

    employee, password = await seed_active_employee(p_no="EMP-036", email="emp36@example.com")
    headers = await _login(client, employee.p_no, password)
    immediate = await _place_order(client, headers, setup["location_id"], setup["item_id"])

    from datetime import UTC, datetime, timedelta

    future = (datetime.now(UTC) + timedelta(hours=3)).isoformat()
    booked = (
        await client.post(
            f"{API}/orders",
            json={
                "location_id": setup["location_id"],
                "order_type": "BOOK_FOR_LATER",
                "scheduled_for": future,
                "items": [{"menu_item_id": setup["item_id"], "quantity": 1}],
            },
            headers=headers,
        )
    ).json()

    operator, o_password = await seed_active_employee(
        p_no="KOP-036", email="kop36@example.com", role=EmployeeRole.KITCHEN_OPERATOR
    )
    kitchen_headers = await _login(client, operator.p_no, o_password)

    incoming = await client.get(
        f"{API}/locations/{setup['location_id']}/orders/incoming", headers=kitchen_headers
    )
    assert incoming.status_code == 200
    incoming_ids = {o["id"] for o in incoming.json()}
    assert incoming_ids == {immediate["id"]}

    await client.post(
        f"{API}/orders/{booked['id']}/booking/confirm-ingredients", headers=kitchen_headers
    )
    incoming_after = await client.get(
        f"{API}/locations/{setup['location_id']}/orders/incoming", headers=kitchen_headers
    )
    assert {o["id"] for o in incoming_after.json()} == {immediate["id"], booked["id"]}


async def test_full_kitchen_lifecycle(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-030", email="admin30@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_with_item_and_station(client, admin_headers, code="KB1")

    employee, e_password = await seed_active_employee(p_no="EMP-030", email="emp30@example.com")
    emp_headers = await _login(client, employee.p_no, e_password)
    order = await _place_order(client, emp_headers, setup["location_id"], setup["item_id"])

    operator, o_password = await seed_active_employee(
        p_no="KOP-030", email="kop30@example.com", role=EmployeeRole.KITCHEN_OPERATOR
    )
    kitchen_headers = await _login(client, operator.p_no, o_password)

    confirm = await client.post(f"{API}/orders/{order['id']}/confirm", headers=kitchen_headers)
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "CONFIRMED"

    queue = await client.post(
        f"{API}/orders/{order['id']}/queue",
        json={"station_assignments": {order["items"][0]["id"]: setup["station_id"]}},
        headers=kitchen_headers,
    )
    assert queue.status_code == 200, queue.text
    assert queue.json()["status"] == "QUEUED"
    assert queue.json()["items"][0]["kitchen_station_id"] == setup["station_id"]

    preparing = await client.post(
        f"{API}/orders/{order['id']}/start-preparing", headers=kitchen_headers
    )
    assert preparing.status_code == 200
    assert preparing.json()["status"] == "PREPARING"

    ready = await client.post(f"{API}/orders/{order['id']}/mark-ready", headers=kitchen_headers)
    assert ready.status_code == 200
    assert ready.json()["status"] == "READY"

    served = await client.post(f"{API}/orders/{order['id']}/serve", headers=kitchen_headers)
    assert served.status_code == 200
    assert served.json()["status"] == "SERVED"


async def test_employee_cannot_perform_kitchen_actions(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-031", email="admin31@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_with_item_and_station(client, admin_headers, code="KB2")

    employee, password = await seed_active_employee(p_no="EMP-031", email="emp31@example.com")
    headers = await _login(client, employee.p_no, password)
    order = await _place_order(client, headers, setup["location_id"], setup["item_id"])

    response = await client.post(f"{API}/orders/{order['id']}/confirm", headers=headers)
    assert response.status_code == 403


async def test_cannot_queue_before_confirm(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-032", email="admin32@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_with_item_and_station(client, admin_headers, code="KB3")

    employee, password = await seed_active_employee(p_no="EMP-032", email="emp32@example.com")
    headers = await _login(client, employee.p_no, password)
    order = await _place_order(client, headers, setup["location_id"], setup["item_id"])

    operator, o_password = await seed_active_employee(
        p_no="KOP-032", email="kop32@example.com", role=EmployeeRole.KITCHEN_OPERATOR
    )
    kitchen_headers = await _login(client, operator.p_no, o_password)

    response = await client.post(
        f"{API}/orders/{order['id']}/queue",
        json={"station_assignments": {order["items"][0]["id"]: setup["station_id"]}},
        headers=kitchen_headers,
    )
    assert response.status_code == 422


async def test_queue_requires_every_item_assigned(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-033", email="admin33@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_with_item_and_station(client, admin_headers, code="KB4")

    employee, password = await seed_active_employee(p_no="EMP-033", email="emp33@example.com")
    headers = await _login(client, employee.p_no, password)
    order = await _place_order(client, headers, setup["location_id"], setup["item_id"])

    operator, o_password = await seed_active_employee(
        p_no="KOP-033", email="kop33@example.com", role=EmployeeRole.KITCHEN_OPERATOR
    )
    kitchen_headers = await _login(client, operator.p_no, o_password)
    await client.post(f"{API}/orders/{order['id']}/confirm", headers=kitchen_headers)

    response = await client.post(
        f"{API}/orders/{order['id']}/queue",
        json={"station_assignments": {}},
        headers=kitchen_headers,
    )
    assert response.status_code == 422


async def test_server_can_serve_directly_bypassing_kitchen_steps(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-034", email="admin34@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_with_item_and_station(client, admin_headers, code="KB5")

    employee, password = await seed_active_employee(p_no="EMP-034", email="emp34@example.com")
    headers = await _login(client, employee.p_no, password)
    order = await _place_order(
        client, headers, setup["location_id"], setup["item_id"], order_type="TAKEAWAY"
    )

    server, s_password = await seed_active_employee(
        p_no="SRV-034", email="srv34@example.com", role=EmployeeRole.SERVER
    )
    server_headers = await _login(client, server.p_no, s_password)

    response = await client.post(
        f"{API}/orders/{order['id']}/serve-directly", headers=server_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "SERVED"


async def test_station_queue_prioritizes_immediate_over_booked_fifo(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    from datetime import UTC, datetime, timedelta

    admin, admin_password = await seed_active_employee(
        p_no="ADM-035", email="admin35@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_with_item_and_station(client, admin_headers, code="KB6")

    employee, password = await seed_active_employee(p_no="EMP-035", email="emp35@example.com")
    headers = await _login(client, employee.p_no, password)

    future = (datetime.now(UTC) + timedelta(hours=3)).isoformat()
    booked = (
        await client.post(
            f"{API}/orders",
            json={
                "location_id": setup["location_id"],
                "order_type": "BOOK_FOR_LATER",
                "scheduled_for": future,
                "items": [{"menu_item_id": setup["item_id"], "quantity": 1}],
            },
            headers=headers,
        )
    ).json()
    immediate = await _place_order(client, headers, setup["location_id"], setup["item_id"])

    operator, o_password = await seed_active_employee(
        p_no="KOP-035", email="kop35@example.com", role=EmployeeRole.KITCHEN_OPERATOR
    )
    kitchen_headers = await _login(client, operator.p_no, o_password)

    # Booked orders need ingredient confirmation (Phase 7) before the
    # normal PENDING -> CONFIRMED kitchen transition is allowed.
    confirm_ingredients = await client.post(
        f"{API}/orders/{booked['id']}/booking/confirm-ingredients", headers=kitchen_headers
    )
    assert confirm_ingredients.status_code == 200, confirm_ingredients.text

    for order in (booked, immediate):
        confirm = await client.post(f"{API}/orders/{order['id']}/confirm", headers=kitchen_headers)
        assert confirm.status_code == 200, confirm.text
        queue = await client.post(
            f"{API}/orders/{order['id']}/queue",
            json={"station_assignments": {order["items"][0]["id"]: setup["station_id"]}},
            headers=kitchen_headers,
        )
        assert queue.status_code == 200, queue.text

    queue_resp = await client.get(
        f"{API}/locations/{setup['location_id']}/kitchen-stations/{setup['station_id']}/queue",
        headers=kitchen_headers,
    )
    assert queue_resp.status_code == 200
    order_numbers = [o["order_number"] for o in queue_resp.json()]
    assert order_numbers == [immediate["order_number"], booked["order_number"]]


async def test_kitchen_board_shows_active_orders_with_item_names_and_station_filter(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-037", email="admin37@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_with_item_and_station(client, admin_headers, code="KB8")
    location_id = setup["location_id"]

    employee, password = await seed_active_employee(p_no="EMP-037", email="emp37@example.com")
    headers = await _login(client, employee.p_no, password)
    queued = await _place_order(client, headers, location_id, setup["item_id"])
    waiting = await _place_order(client, headers, location_id, setup["item_id"])
    served = await _place_order(client, headers, location_id, setup["item_id"])

    operator, o_password = await seed_active_employee(
        p_no="KOP-037", email="kop37@example.com", role=EmployeeRole.KITCHEN_OPERATOR
    )
    kitchen_headers = await _login(client, operator.p_no, o_password)

    await client.post(f"{API}/orders/{queued['id']}/confirm", headers=kitchen_headers)
    await client.post(
        f"{API}/orders/{queued['id']}/queue",
        json={"station_assignments": {queued["items"][0]["id"]: setup["station_id"]}},
        headers=kitchen_headers,
    )
    await client.post(f"{API}/orders/{served['id']}/serve-directly", headers=kitchen_headers)

    board = await client.get(
        f"{API}/locations/{location_id}/kitchen/board", headers=kitchen_headers
    )
    assert board.status_code == 200, board.text
    by_id = {o["id"]: o for o in board.json()}
    assert set(by_id) == {queued["id"], waiting["id"]}
    assert by_id[queued["id"]]["status"] == "QUEUED"
    item = by_id[queued["id"]]["items"][0]
    assert item["menu_item_name"] == "Biryani"
    assert item["quantity"] == 1
    assert item["kitchen_station_name"] == "Main Kitchen"
    assert "unit_price" not in item

    station_board = await client.get(
        f"{API}/locations/{location_id}/kitchen/board",
        params={"station_id": setup["station_id"]},
        headers=kitchen_headers,
    )
    assert [o["id"] for o in station_board.json()] == [queued["id"]]

    forbidden = await client.get(f"{API}/locations/{location_id}/kitchen/board", headers=headers)
    assert forbidden.status_code == 403
