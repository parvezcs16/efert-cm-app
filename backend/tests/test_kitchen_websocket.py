from httpx import AsyncClient
from starlette.testclient import TestClient

from app.main import app
from app.models.enums import EmployeeRole
from tests.conftest import SeedEmployee

API = "/api/v1"


async def _login(client: AsyncClient, p_no: str, password: str) -> str:
    resp = await client.post(f"{API}/auth/login", json={"p_no": p_no, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def test_kitchen_websocket_receives_status_broadcast(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-040", email="admin40@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_token = await _login(client, admin.p_no, admin_password)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    location = (
        await client.post(
            f"{API}/locations", json={"name": "WS Branch", "code": "WSB1"}, headers=admin_headers
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
            json={"name": "Nihari", "description": None},
            headers=admin_headers,
        )
    ).json()
    await client.put(
        f"{API}/locations/{location['id']}/menu-items/{item['id']}/availability",
        json={"is_available": True, "price": "200.00"},
        headers=admin_headers,
    )

    employee, e_password = await seed_active_employee(p_no="EMP-040", email="emp40@example.com")
    employee_token = await _login(client, employee.p_no, e_password)
    order = (
        await client.post(
            f"{API}/orders",
            json={
                "location_id": location["id"],
                "order_type": "TAKEAWAY",
                "items": [{"menu_item_id": item["id"], "quantity": 1}],
            },
            headers={"Authorization": f"Bearer {employee_token}"},
        )
    ).json()

    operator, o_password = await seed_active_employee(
        p_no="KOP-040", email="kop40@example.com", role=EmployeeRole.KITCHEN_OPERATOR
    )
    operator_token = await _login(client, operator.p_no, o_password)

    # Starlette's TestClient drives the websocket handshake synchronously in
    # a background thread, reusing the same `app` (and its dependency
    # overrides set up by the async `client` fixture) as the REST calls
    # above -- so it sees the same test database.
    sync_client = TestClient(app)
    with sync_client.websocket_connect(
        f"/ws/kitchen/{location['id']}?token={operator_token}"
    ) as websocket:
        confirm = await client.post(
            f"{API}/orders/{order['id']}/confirm",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert confirm.status_code == 200

        message = websocket.receive_json()
        assert message["type"] == "order.status_changed"
        assert message["order_id"] == order["id"]
        assert message["status"] == "CONFIRMED"


async def test_kitchen_websocket_rejects_non_kitchen_staff(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    employee, password = await seed_active_employee(p_no="EMP-041", email="emp41@example.com")
    token = await _login(client, employee.p_no, password)

    import uuid

    from starlette.websockets import WebSocketDisconnect

    sync_client = TestClient(app)
    fake_location_id = uuid.uuid4()
    try:
        with sync_client.websocket_connect(f"/ws/kitchen/{fake_location_id}?token={token}"):
            raise AssertionError("expected the connection to be rejected during handshake")
    except WebSocketDisconnect as exc:
        assert exc.code == 1008
