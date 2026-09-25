from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select

from app.models.enums import EmployeeRole
from app.models.guest import GuestSession
from tests.conftest import SeedEmployee, TestSessionLocal

API = "/api/v1"


async def _login(client: AsyncClient, p_no: str, password: str) -> dict[str, str]:
    resp = await client.post(f"{API}/auth/login", json={"p_no": p_no, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _setup_orderable_item(
    client: AsyncClient, admin_headers: dict[str, str]
) -> dict[str, str]:
    location = (
        await client.post(
            f"{API}/locations", json={"name": "Guest Branch", "code": "GB1"}, headers=admin_headers
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
            json={"name": "Kebab Platter", "description": None},
            headers=admin_headers,
        )
    ).json()
    await client.put(
        f"{API}/locations/{location['id']}/menu-items/{item['id']}/availability",
        json={"is_available": True, "price": "300.00"},
        headers=admin_headers,
    )
    return {"location_id": location["id"], "item_id": item["id"]}


async def test_host_registers_guest_and_opens_session(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    host, password = await seed_active_employee(p_no="EMP-050", email="emp50@example.com")
    headers = await _login(client, host.p_no, password)

    register = await client.post(
        f"{API}/guests",
        json={
            "name": "Jane Visitor",
            "company_name": "Acme Corp",
            "cnic": "12345-6789012-3",
            "guest_type": "PRIVATE",
            "accompanying_persons": 1,
        },
        headers=headers,
    )
    assert register.status_code == 201, register.text
    guest_id = register.json()["id"]

    session = await client.post(f"{API}/guests/{guest_id}/sessions", headers=headers)
    assert session.status_code == 201, session.text
    body = session.json()
    assert body["session"]["status"] == "ACTIVE"
    assert len(body["qr_token"]) > 20

    listing = await client.get(f"{API}/guests", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


async def test_guest_orders_independently_via_qr_token(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-051", email="admin51@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_orderable_item(client, admin_headers)

    host, password = await seed_active_employee(p_no="EMP-051", email="emp51@example.com")
    headers = await _login(client, host.p_no, password)
    guest_id = (
        await client.post(
            f"{API}/guests",
            json={
                "name": "Official Visitor",
                "company_name": "Gov Dept",
                "cnic": "11111-1111111-1",
                "guest_type": "OFFICIAL",
                "accompanying_persons": 0,
            },
            headers=headers,
        )
    ).json()["id"]
    qr_token = (
        await client.post(f"{API}/guests/{guest_id}/sessions", headers=headers)
    ).json()["qr_token"]

    auth = await client.post(f"{API}/guest/auth", json={"token": qr_token})
    assert auth.status_code == 200, auth.text
    guest_headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}

    # A guest must be able to discover locations/menu on their own, not
    # just place an order once handed a location_id/menu_item_id.
    guest_locations = await client.get(f"{API}/guest/locations", headers=guest_headers)
    assert guest_locations.status_code == 200, guest_locations.text
    assert any(loc["id"] == setup["location_id"] for loc in guest_locations.json())

    guest_menu = await client.get(
        f"{API}/guest/locations/{setup['location_id']}/menu", headers=guest_headers
    )
    assert guest_menu.status_code == 200, guest_menu.text
    menu_item_ids = {item["id"] for cat in guest_menu.json() for item in cat["items"]}
    assert setup["item_id"] in menu_item_ids
    assert "price" not in guest_menu.json()[0]["items"][0]

    order = await client.post(
        f"{API}/guest/orders",
        json={
            "location_id": setup["location_id"],
            "order_type": "DINE_IN",
            "items": [{"menu_item_id": setup["item_id"], "quantity": 2}],
        },
        headers=guest_headers,
    )
    assert order.status_code == 201, order.text
    assert order.json()["customer_type"] == "GUEST"

    history = await client.get(f"{API}/guest/orders", headers=guest_headers)
    assert history.status_code == 200
    assert len(history.json()) == 1


async def test_closing_session_blocks_new_orders_but_reopen_restores(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-052", email="admin52@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    setup = await _setup_orderable_item(client, admin_headers)

    host, password = await seed_active_employee(p_no="EMP-052", email="emp52@example.com")
    headers = await _login(client, host.p_no, password)
    guest_id = (
        await client.post(
            f"{API}/guests",
            json={
                "name": "Private Visitor",
                "company_name": "Beta LLC",
                "cnic": "22222-2222222-2",
                "guest_type": "PRIVATE",
                "accompanying_persons": 0,
            },
            headers=headers,
        )
    ).json()["id"]
    session = (
        await client.post(f"{API}/guests/{guest_id}/sessions", headers=headers)
    ).json()
    session_id = session["session"]["id"]
    qr_token = session["qr_token"]

    close = await client.post(f"{API}/guests/sessions/{session_id}/close", headers=headers)
    assert close.status_code == 200
    assert close.json()["status"] == "CLOSED"

    # Re-authenticating still works even though the session is closed...
    auth = await client.post(f"{API}/guest/auth", json={"token": qr_token})
    assert auth.status_code == 200
    guest_headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}

    # ...but ordering is blocked while closed.
    blocked_order = await client.post(
        f"{API}/guest/orders",
        json={
            "location_id": setup["location_id"],
            "order_type": "TAKEAWAY",
            "items": [{"menu_item_id": setup["item_id"], "quantity": 1}],
        },
        headers=guest_headers,
    )
    assert blocked_order.status_code == 403

    reopen = await client.post(f"{API}/guests/sessions/{session_id}/reopen", headers=headers)
    assert reopen.status_code == 200
    assert reopen.json()["status"] == "ACTIVE"

    allowed_order = await client.post(
        f"{API}/guest/orders",
        json={
            "location_id": setup["location_id"],
            "order_type": "TAKEAWAY",
            "items": [{"menu_item_id": setup["item_id"], "quantity": 1}],
        },
        headers=guest_headers,
    )
    assert allowed_order.status_code == 201, allowed_order.text


async def test_expired_qr_token_cannot_reopen_or_authenticate(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    host, password = await seed_active_employee(p_no="EMP-053", email="emp53@example.com")
    headers = await _login(client, host.p_no, password)
    guest_id = (
        await client.post(
            f"{API}/guests",
            json={
                "name": "Expiring Visitor",
                "company_name": "Gamma Inc",
                "cnic": "33333-3333333-3",
                "guest_type": "PRIVATE",
                "accompanying_persons": 0,
            },
            headers=headers,
        )
    ).json()["id"]
    session = (
        await client.post(f"{API}/guests/{guest_id}/sessions", headers=headers)
    ).json()
    session_id = session["session"]["id"]
    qr_token = session["qr_token"]

    await client.post(f"{API}/guests/sessions/{session_id}/close", headers=headers)

    # Force the token past its 24h validity window directly in the DB.
    async with TestSessionLocal() as db:
        result = await db.execute(select(GuestSession).where(GuestSession.id == session_id))
        row = result.scalar_one()
        row.token_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await db.commit()

    auth = await client.post(f"{API}/guest/auth", json={"token": qr_token})
    assert auth.status_code == 401

    reopen = await client.post(f"{API}/guests/sessions/{session_id}/reopen", headers=headers)
    assert reopen.status_code == 422


async def test_employee_cannot_manage_another_hosts_guest(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    host, host_password = await seed_active_employee(p_no="EMP-054", email="emp54@example.com")
    host_headers = await _login(client, host.p_no, host_password)
    guest_id = (
        await client.post(
            f"{API}/guests",
            json={
                "name": "Owned Visitor",
                "company_name": "Delta Co",
                "cnic": "44444-4444444-4",
                "guest_type": "PRIVATE",
                "accompanying_persons": 0,
            },
            headers=host_headers,
        )
    ).json()["id"]

    other, other_password = await seed_active_employee(p_no="EMP-055", email="emp55@example.com")
    other_headers = await _login(client, other.p_no, other_password)

    get_resp = await client.get(f"{API}/guests/{guest_id}", headers=other_headers)
    assert get_resp.status_code == 404
