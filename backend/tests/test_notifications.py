from httpx import AsyncClient

from app.models.enums import EmployeeRole
from app.services.notifications.daily_summary_service import DailySummaryService, business_today
from tests.conftest import SeedEmployee, TestSessionLocal
from tests.test_billing import _login, _serve_employee_order, _setup_location_item_station

API = "/api/v1"


async def _run_daily_summary() -> int:
    async with TestSessionLocal() as db:
        sent = await DailySummaryService(db).send_for_day(business_today())
        await db.commit()
    return sent


async def test_daily_summary_counts_served_orders_once_per_day(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-090", email="admin90@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_item_station(client, admin_headers, "NT1")

    employee, e_password = await seed_active_employee(p_no="EMP-090", email="emp90@example.com")
    employee_headers = await _login(client, employee.p_no, e_password)
    server, s_password = await seed_active_employee(
        p_no="SRV-090", email="srv90@example.com", role=EmployeeRole.SERVER
    )
    server_headers = await _login(client, server.p_no, s_password)

    await _serve_employee_order(client, employee_headers, server_headers, setup, quantity=2)
    await _serve_employee_order(client, employee_headers, server_headers, setup, quantity=1)
    # Placed but never served: must not count.
    await client.post(
        f"{API}/orders",
        json={
            "location_id": setup["location_id"],
            "order_type": "TAKEAWAY",
            "items": [{"menu_item_id": setup["item_id"], "quantity": 5}],
        },
        headers=employee_headers,
    )

    assert await _run_daily_summary() == 1
    # Re-running the same day doesn't duplicate.
    assert await _run_daily_summary() == 0

    count = await client.get(f"{API}/notifications/unread-count", headers=employee_headers)
    assert count.json() == {"unread": 1}

    inbox = (await client.get(f"{API}/notifications", headers=employee_headers)).json()
    assert len(inbox) == 1
    assert inbox[0]["type"] == "DAILY_SERVED_SUMMARY"
    assert inbox[0]["title"] == "Today's summary: 2 orders served"
    assert "Chapli Kebab x3" in inbox[0]["body"]
    # Prices stay hidden from employees.
    assert "100" not in inbox[0]["body"]

    # Server who did the serving gets nothing of their own.
    server_count = await client.get(f"{API}/notifications/unread-count", headers=server_headers)
    assert server_count.json() == {"unread": 0}


async def test_mark_read_is_scoped_to_owner(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-091", email="admin91@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_item_station(client, admin_headers, "NT2")

    employee, e_password = await seed_active_employee(p_no="EMP-091", email="emp91@example.com")
    employee_headers = await _login(client, employee.p_no, e_password)
    other, o_password = await seed_active_employee(p_no="EMP-092", email="emp92@example.com")
    other_headers = await _login(client, other.p_no, o_password)

    await _serve_employee_order(client, employee_headers, admin_headers, setup)
    await _run_daily_summary()
    notification_id = (await client.get(f"{API}/notifications", headers=employee_headers)).json()[
        0
    ]["id"]

    stolen = await client.post(f"{API}/notifications/{notification_id}/read", headers=other_headers)
    assert stolen.status_code == 404

    read = await client.post(
        f"{API}/notifications/{notification_id}/read", headers=employee_headers
    )
    assert read.status_code == 200
    assert read.json()["read_at"] is not None

    count = await client.get(f"{API}/notifications/unread-count", headers=employee_headers)
    assert count.json() == {"unread": 0}

    all_read = await client.post(f"{API}/notifications/read-all", headers=employee_headers)
    assert all_read.status_code == 204
