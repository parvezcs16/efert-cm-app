from httpx import AsyncClient

from app.models.enums import EmployeeRole
from tests.conftest import SeedEmployee

API = "/api/v1"


async def _login(client: AsyncClient, p_no: str, password: str) -> dict[str, str]:
    resp = await client.post(f"{API}/auth/login", json={"p_no": p_no, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _setup_location_and_item(
    client: AsyncClient, admin_headers: dict[str, str], code: str, price: str = "100.00"
) -> dict[str, str]:
    location = (
        await client.post(
            f"{API}/locations", json={"name": f"Report Branch {code}", "code": code},
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
            json={"name": "Report Item", "description": None},
            headers=admin_headers,
        )
    ).json()
    await client.put(
        f"{API}/locations/{location['id']}/menu-items/{item['id']}/availability",
        json={"is_available": True, "price": price},
        headers=admin_headers,
    )
    return {"location_id": location["id"], "item_id": item["id"]}


async def test_sales_summary_reflects_served_orders(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-090", email="admin090@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_and_item(client, admin_headers, "RP1", price="50.00")

    employee, password = await seed_active_employee(p_no="EMP-090", email="emp090@example.com")
    headers = await _login(client, employee.p_no, password)
    server, s_password = await seed_active_employee(
        p_no="SRV-090", email="srv090@example.com", role=EmployeeRole.SERVER
    )
    server_headers = await _login(client, server.p_no, s_password)

    served_order = (
        await client.post(
            f"{API}/orders",
            json={
                "location_id": setup["location_id"],
                "order_type": "TAKEAWAY",
                "items": [{"menu_item_id": setup["item_id"], "quantity": 2}],
            },
            headers=headers,
        )
    ).json()
    await client.post(f"{API}/orders/{served_order['id']}/serve-directly", headers=server_headers)

    cancelled_order = (
        await client.post(
            f"{API}/orders",
            json={
                "location_id": setup["location_id"],
                "order_type": "TAKEAWAY",
                "items": [{"menu_item_id": setup["item_id"], "quantity": 1}],
            },
            headers=headers,
        )
    ).json()
    await client.post(f"{API}/orders/{cancelled_order['id']}/cancel", headers=headers)

    summary = await client.get(
        f"{API}/reports/locations/{setup['location_id']}/sales-summary", headers=admin_headers
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["total_orders"] == 2
    assert body["orders_by_status"]["SERVED"] == 1
    assert body["orders_by_status"]["CANCELLED"] == 1
    assert body["total_revenue"] == "100.00"


async def test_reconciliation_matches_after_correction(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-091", email="admin091@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_and_item(client, admin_headers, "RP2", price="40.00")

    employee, password = await seed_active_employee(p_no="EMP-091", email="emp091@example.com")
    headers = await _login(client, employee.p_no, password)
    server, s_password = await seed_active_employee(
        p_no="SRV-091", email="srv091@example.com", role=EmployeeRole.SERVER
    )
    server_headers = await _login(client, server.p_no, s_password)

    order = (
        await client.post(
            f"{API}/orders",
            json={
                "location_id": setup["location_id"],
                "order_type": "TAKEAWAY",
                "items": [{"menu_item_id": setup["item_id"], "quantity": 3}],
            },
            headers=headers,
        )
    ).json()
    served = await client.post(
        f"{API}/orders/{order['id']}/serve-directly", headers=server_headers
    )
    item_id = served.json()["items"][0]["id"]

    await client.post(
        f"{API}/orders/{order['id']}/items/{item_id}/consumption/request-correction",
        json={"requested_quantity": 1, "reason": "Only 1 arrived"},
        headers=headers,
    )
    await client.post(
        f"{API}/orders/{order['id']}/items/{item_id}/consumption/validate-correction",
        json={"approve": True},
        headers=server_headers,
    )

    report = await client.get(
        f"{API}/reports/locations/{setup['location_id']}/reconciliation", headers=admin_headers
    )
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["mismatch_count"] == 0
    line = next(line for line in body["lines"] if line["order_id"] == order["id"])
    assert line["served_quantity"] == 1
    assert line["expected_amount"] == "40.00"
    assert line["billed_amount"] == "40.00"
    assert line["matches"] is True


async def test_audit_log_requires_system_role_and_filters(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-092", email="admin092@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)

    employee, password = await seed_active_employee(p_no="EMP-092", email="emp092@example.com")
    headers = await _login(client, employee.p_no, password)

    forbidden = await client.get(f"{API}/reports/audit-log", headers=headers)
    assert forbidden.status_code == 403

    allowed = await client.get(
        f"{API}/reports/audit-log",
        params={"entity_type": "employee", "entity_id": str(employee.id)},
        headers=admin_headers,
    )
    assert allowed.status_code == 200
    assert len(allowed.json()) >= 1
    assert all(entry["entity_type"] == "employee" for entry in allowed.json())


async def test_manual_billing_adjustment_affects_statement(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-093",
        email="admin093@example.com",
        role=EmployeeRole.FINANCE_ADMIN,
    )
    admin_headers = await _login(client, admin.p_no, admin_password)

    employee, password = await seed_active_employee(p_no="EMP-093", email="emp093@example.com")
    headers = await _login(client, employee.p_no, password)

    invalid = await client.post(
        f"{API}/billing/employees/{employee.id}/adjustments",
        json={
            "source_type": "OFFICIAL_GUEST",
            "entry_type": "CREDIT",
            "amount": "10.00",
            "reason": "invalid bucket",
        },
        headers=admin_headers,
    )
    assert invalid.status_code == 422

    adjust = await client.post(
        f"{API}/billing/employees/{employee.id}/adjustments",
        json={
            "source_type": "PERSONAL_CONSUMPTION",
            "entry_type": "DEBIT",
            "amount": "15.00",
            "reason": "Manual correction found during reconciliation",
        },
        headers=admin_headers,
    )
    assert adjust.status_code == 201, adjust.text

    bill = await client.get(f"{API}/billing/me/personal", headers=headers)
    assert bill.json()["net_balance"] == "15.00"


async def test_regular_employee_cannot_post_billing_adjustment(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    employee, password = await seed_active_employee(p_no="EMP-094", email="emp094@example.com")
    headers = await _login(client, employee.p_no, password)

    other, other_password = await seed_active_employee(p_no="EMP-095", email="emp095@example.com")

    response = await client.post(
        f"{API}/billing/employees/{other.id}/adjustments",
        json={
            "source_type": "PERSONAL_CONSUMPTION",
            "entry_type": "CREDIT",
            "amount": "5.00",
            "reason": "not allowed",
        },
        headers=headers,
    )
    assert response.status_code == 403
