from httpx import AsyncClient

from app.models.enums import EmployeeRole
from tests.conftest import SeedEmployee

API = "/api/v1"


async def _login(client: AsyncClient, p_no: str, password: str) -> dict[str, str]:
    resp = await client.post(f"{API}/auth/login", json={"p_no": p_no, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _setup_location_item_station(
    client: AsyncClient, admin_headers: dict[str, str], code: str, price: str = "100.00"
) -> dict[str, str]:
    location = (
        await client.post(
            f"{API}/locations", json={"name": f"Billing Branch {code}", "code": code},
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
            json={"name": "Chapli Kebab", "description": None},
            headers=admin_headers,
        )
    ).json()
    await client.put(
        f"{API}/locations/{location['id']}/menu-items/{item['id']}/availability",
        json={"is_available": True, "price": price},
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


async def _serve_employee_order(
    client: AsyncClient,
    employee_headers: dict[str, str],
    kitchen_headers: dict[str, str],
    setup: dict[str, str],
    quantity: int = 1,
) -> dict:
    order = (
        await client.post(
            f"{API}/orders",
            json={
                "location_id": setup["location_id"],
                "order_type": "TAKEAWAY",
                "items": [{"menu_item_id": setup["item_id"], "quantity": quantity}],
            },
            headers=employee_headers,
        )
    ).json()
    resp = await client.post(f"{API}/orders/{order['id']}/serve-directly", headers=kitchen_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_serving_order_posts_personal_charge(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-070", email="admin70@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_item_station(client, admin_headers, "BL1", price="100.00")

    employee, e_password = await seed_active_employee(p_no="EMP-070", email="emp70@example.com")
    employee_headers = await _login(client, employee.p_no, e_password)

    server, s_password = await seed_active_employee(
        p_no="SRV-070", email="srv70@example.com", role=EmployeeRole.SERVER
    )
    server_headers = await _login(client, server.p_no, s_password)

    served = await _serve_employee_order(
        client, employee_headers, server_headers, setup, quantity=2
    )
    order_id = served["id"]
    item_id = served["items"][0]["id"]

    consumption = await client.get(
        f"{API}/orders/{order_id}/items/{item_id}/consumption", headers=employee_headers
    )
    assert consumption.status_code == 200
    assert consumption.json()["served_quantity"] == 2
    assert consumption.json()["status"] == "VALIDATED"

    bill = await client.get(f"{API}/billing/me/personal", headers=employee_headers)
    assert bill.status_code == 200
    body = bill.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["entry_type"] == "DEBIT"
    assert body["entries"][0]["amount"] == "200.00"
    assert body["net_balance"] == "200.00"


async def test_correction_request_and_server_approval_adjusts_ledger(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-071", email="admin71@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_item_station(client, admin_headers, "BL2", price="50.00")

    employee, e_password = await seed_active_employee(p_no="EMP-071", email="emp71@example.com")
    employee_headers = await _login(client, employee.p_no, e_password)

    server, s_password = await seed_active_employee(
        p_no="SRV-071", email="srv71@example.com", role=EmployeeRole.SERVER
    )
    server_headers = await _login(client, server.p_no, s_password)

    served = await _serve_employee_order(
        client, employee_headers, server_headers, setup, quantity=3
    )
    order_id = served["id"]
    item_id = served["items"][0]["id"]

    request = await client.post(
        f"{API}/orders/{order_id}/items/{item_id}/consumption/request-correction",
        json={"requested_quantity": 1, "reason": "Only received 1 of 3"},
        headers=employee_headers,
    )
    assert request.status_code == 200, request.text
    assert request.json()["status"] == "CORRECTION_REQUESTED"

    duplicate_request = await client.post(
        f"{API}/orders/{order_id}/items/{item_id}/consumption/request-correction",
        json={"requested_quantity": 2, "reason": "still wrong"},
        headers=employee_headers,
    )
    assert duplicate_request.status_code == 422

    approve = await client.post(
        f"{API}/orders/{order_id}/items/{item_id}/consumption/validate-correction",
        json={"approve": True},
        headers=server_headers,
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["served_quantity"] == 1
    assert approve.json()["status"] == "VALIDATED"

    bill = await client.get(f"{API}/billing/me/personal", headers=employee_headers)
    body = bill.json()
    assert len(body["entries"]) == 2
    assert body["entries"][0]["amount"] == "150.00"  # original charge for 3x
    assert body["entries"][1]["entry_type"] == "CREDIT"
    assert body["entries"][1]["amount"] == "100.00"  # reversal for the 2x difference
    assert body["net_balance"] == "50.00"


async def test_correction_rejection_leaves_billing_unchanged(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-072", email="admin72@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_item_station(client, admin_headers, "BL3", price="80.00")

    employee, e_password = await seed_active_employee(p_no="EMP-072", email="emp72@example.com")
    employee_headers = await _login(client, employee.p_no, e_password)

    server, s_password = await seed_active_employee(
        p_no="SRV-072", email="srv72@example.com", role=EmployeeRole.SERVER
    )
    server_headers = await _login(client, server.p_no, s_password)

    served = await _serve_employee_order(client, employee_headers, server_headers, setup)
    order_id = served["id"]
    item_id = served["items"][0]["id"]

    await client.post(
        f"{API}/orders/{order_id}/items/{item_id}/consumption/request-correction",
        json={"requested_quantity": 0, "reason": "Never received it"},
        headers=employee_headers,
    )

    reject = await client.post(
        f"{API}/orders/{order_id}/items/{item_id}/consumption/validate-correction",
        json={"approve": False},
        headers=server_headers,
    )
    assert reject.status_code == 200
    assert reject.json()["served_quantity"] == 1
    assert reject.json()["status"] == "VALIDATED"

    bill = await client.get(f"{API}/billing/me/personal", headers=employee_headers)
    body = bill.json()
    assert len(body["entries"]) == 1
    assert body["net_balance"] == "80.00"


async def test_correction_request_rejects_out_of_range_quantity(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-073", email="admin73@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_item_station(client, admin_headers, "BL4")

    employee, e_password = await seed_active_employee(p_no="EMP-073", email="emp73@example.com")
    employee_headers = await _login(client, employee.p_no, e_password)

    server, s_password = await seed_active_employee(
        p_no="SRV-073", email="srv73@example.com", role=EmployeeRole.SERVER
    )
    server_headers = await _login(client, server.p_no, s_password)

    served = await _serve_employee_order(
        client, employee_headers, server_headers, setup, quantity=2
    )
    order_id = served["id"]
    item_id = served["items"][0]["id"]

    response = await client.post(
        f"{API}/orders/{order_id}/items/{item_id}/consumption/request-correction",
        json={"requested_quantity": 5, "reason": "too many"},
        headers=employee_headers,
    )
    assert response.status_code == 422


async def test_other_employee_cannot_request_correction_on_foreign_order(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-074", email="admin74@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_item_station(client, admin_headers, "BL5")

    owner, owner_password = await seed_active_employee(p_no="EMP-074", email="emp74@example.com")
    owner_headers = await _login(client, owner.p_no, owner_password)

    server, s_password = await seed_active_employee(
        p_no="SRV-074", email="srv74@example.com", role=EmployeeRole.SERVER
    )
    server_headers = await _login(client, server.p_no, s_password)

    served = await _serve_employee_order(client, owner_headers, server_headers, setup)
    order_id = served["id"]
    item_id = served["items"][0]["id"]

    intruder, intruder_password = await seed_active_employee(
        p_no="EMP-075", email="emp75@example.com"
    )
    intruder_headers = await _login(client, intruder.p_no, intruder_password)

    response = await client.post(
        f"{API}/orders/{order_id}/items/{item_id}/consumption/request-correction",
        json={"requested_quantity": 0, "reason": "not mine"},
        headers=intruder_headers,
    )
    assert response.status_code == 404


async def test_private_guest_charge_posts_to_host_ledger(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-076", email="admin76@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_item_station(client, admin_headers, "BL6", price="60.00")

    host, host_password = await seed_active_employee(p_no="EMP-076", email="emp76@example.com")
    host_headers = await _login(client, host.p_no, host_password)

    guest_id = (
        await client.post(
            f"{API}/guests",
            json={
                "name": "Private Guest",
                "company_name": "Acme",
                "cnic": "55555-5555555-5",
                "guest_type": "PRIVATE",
                "accompanying_persons": 0,
            },
            headers=host_headers,
        )
    ).json()["id"]
    qr_token = (
        await client.post(f"{API}/guests/{guest_id}/sessions", headers=host_headers)
    ).json()["qr_token"]
    guest_access_token = (
        await client.post(f"{API}/guest/auth", json={"token": qr_token})
    ).json()["access_token"]
    guest_headers = {"Authorization": f"Bearer {guest_access_token}"}

    order = (
        await client.post(
            f"{API}/guest/orders",
            json={
                "location_id": setup["location_id"],
                "order_type": "DINE_IN",
                "items": [{"menu_item_id": setup["item_id"], "quantity": 1}],
            },
            headers=guest_headers,
        )
    ).json()

    server, s_password = await seed_active_employee(
        p_no="SRV-076", email="srv76@example.com", role=EmployeeRole.SERVER
    )
    server_headers = await _login(client, server.p_no, s_password)
    served = await client.post(
        f"{API}/orders/{order['id']}/serve-directly", headers=server_headers
    )
    assert served.status_code == 200

    personal_bill = await client.get(f"{API}/billing/me/personal", headers=host_headers)
    assert personal_bill.json()["entries"] == []

    private_bill = await client.get(f"{API}/billing/me/private-guests", headers=host_headers)
    body = private_bill.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["amount"] == "60.00"
    assert body["entries"][0]["guest_session_id"] is not None

    consolidated = await client.get(f"{API}/billing/me/consolidated", headers=host_headers)
    assert consolidated.json()["net_balance"] == "60.00"


async def test_official_guest_charge_posts_to_location_account_and_is_gated(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-077", email="admin77@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_location_item_station(client, admin_headers, "BL7", price="90.00")

    host, host_password = await seed_active_employee(p_no="EMP-077", email="emp77@example.com")
    host_headers = await _login(client, host.p_no, host_password)

    guest_id = (
        await client.post(
            f"{API}/guests",
            json={
                "name": "Official Guest",
                "company_name": "Gov Dept",
                "cnic": "66666-6666666-6",
                "guest_type": "OFFICIAL",
                "accompanying_persons": 0,
            },
            headers=host_headers,
        )
    ).json()["id"]
    qr_token = (
        await client.post(f"{API}/guests/{guest_id}/sessions", headers=host_headers)
    ).json()["qr_token"]
    guest_access_token = (
        await client.post(f"{API}/guest/auth", json={"token": qr_token})
    ).json()["access_token"]
    guest_headers = {"Authorization": f"Bearer {guest_access_token}"}

    order = (
        await client.post(
            f"{API}/guest/orders",
            json={
                "location_id": setup["location_id"],
                "order_type": "DINE_IN",
                "items": [{"menu_item_id": setup["item_id"], "quantity": 1}],
            },
            headers=guest_headers,
        )
    ).json()

    server, s_password = await seed_active_employee(
        p_no="SRV-077", email="srv77@example.com", role=EmployeeRole.SERVER
    )
    server_headers = await _login(client, server.p_no, s_password)
    await client.post(f"{API}/orders/{order['id']}/serve-directly", headers=server_headers)

    forbidden = await client.get(
        f"{API}/billing/official/{setup['location_id']}", headers=host_headers
    )
    assert forbidden.status_code == 403

    allowed = await client.get(
        f"{API}/billing/official/{setup['location_id']}", headers=admin_headers
    )
    assert allowed.status_code == 200
    body = allowed.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["amount"] == "90.00"

    host_personal = await client.get(f"{API}/billing/me/personal", headers=host_headers)
    assert host_personal.json()["entries"] == []


async def test_employee_can_update_statement_frequency(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    employee, password = await seed_active_employee(p_no="EMP-078", email="emp78@example.com")
    headers = await _login(client, employee.p_no, password)

    response = await client.patch(
        f"{API}/employees/me/statement-frequency",
        json={"frequency": "WEEKLY"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["statement_frequency"] == "WEEKLY"
