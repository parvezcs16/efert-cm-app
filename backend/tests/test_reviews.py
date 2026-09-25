from httpx import AsyncClient

from app.models.enums import EmployeeRole
from tests.conftest import SeedEmployee

API = "/api/v1"


async def _login(client: AsyncClient, p_no: str, password: str) -> dict[str, str]:
    resp = await client.post(f"{API}/auth/login", json={"p_no": p_no, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_default_categories_are_seeded_and_visible(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-080", email="admin80@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    location = (
        await client.post(
            f"{API}/locations", json={"name": "Review Branch", "code": "RB1"},
            headers=admin_headers,
        )
    ).json()

    employee, password = await seed_active_employee(p_no="EMP-080", email="emp80@example.com")
    headers = await _login(client, employee.p_no, password)

    categories = await client.get(
        f"{API}/locations/{location['id']}/review-categories", headers=headers
    )
    assert categories.status_code == 200
    names = {c["name"] for c in categories.json()}
    assert names == {"Food", "Environment", "Hygiene", "Server Behavior"}
    assert all(c["is_manager_defined"] is False for c in categories.json())


async def test_manager_can_add_location_specific_category(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-081", email="admin81@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    location = (
        await client.post(
            f"{API}/locations", json={"name": "Review Branch 2", "code": "RB2"},
            headers=admin_headers,
        )
    ).json()

    create = await client.post(
        f"{API}/locations/{location['id']}/review-categories",
        json={"name": "Wait Time"},
        headers=admin_headers,
    )
    assert create.status_code == 201, create.text
    assert create.json()["is_manager_defined"] is True

    employee, password = await seed_active_employee(p_no="EMP-081", email="emp81@example.com")
    headers = await _login(client, employee.p_no, password)
    categories = await client.get(
        f"{API}/locations/{location['id']}/review-categories", headers=headers
    )
    names = {c["name"] for c in categories.json()}
    assert "Wait Time" in names


async def test_overall_review_can_be_submitted_multiple_times_with_category_ratings(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-082", email="admin82@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    location = (
        await client.post(
            f"{API}/locations", json={"name": "Review Branch 3", "code": "RB3"},
            headers=admin_headers,
        )
    ).json()
    categories = (
        await client.get(
            f"{API}/locations/{location['id']}/review-categories", headers=admin_headers
        )
    ).json()
    food_category = next(c for c in categories if c["name"] == "Food")

    employee, password = await seed_active_employee(p_no="EMP-082", email="emp82@example.com")
    headers = await _login(client, employee.p_no, password)

    for _ in range(2):
        response = await client.post(
            f"{API}/reviews",
            json={
                "location_id": location["id"],
                "review_type": "OVERALL",
                "is_anonymous": False,
                "overall_rating": 4,
                "comment": "Great food today",
                "category_ratings": [{"category_id": food_category["id"], "rating": 5}],
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text

    mine = await client.get(f"{API}/reviews/me", headers=headers)
    assert len(mine.json()) == 2
    assert mine.json()[0]["category_ratings"][0]["rating"] == 5


async def test_anonymous_review_hides_identity_in_listing(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-083", email="admin83@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    location = (
        await client.post(
            f"{API}/locations", json={"name": "Review Branch 4", "code": "RB4"},
            headers=admin_headers,
        )
    ).json()

    employee, password = await seed_active_employee(p_no="EMP-083", email="emp83@example.com")
    headers = await _login(client, employee.p_no, password)

    await client.post(
        f"{API}/reviews",
        json={
            "location_id": location["id"],
            "review_type": "OVERALL",
            "is_anonymous": True,
            "overall_rating": 2,
            "comment": "Needs improvement",
        },
        headers=headers,
    )

    other, other_password = await seed_active_employee(p_no="EMP-084", email="emp84@example.com")
    other_headers = await _login(client, other.p_no, other_password)

    listing = await client.get(f"{API}/locations/{location['id']}/reviews", headers=other_headers)
    assert listing.status_code == 200
    review = next(r for r in listing.json() if r["comment"] == "Needs improvement")
    assert review["is_anonymous"] is True
    assert review["employee_id"] is None


async def test_order_review_requires_own_served_order(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-085", email="admin85@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_headers = await _login(client, admin.p_no, admin_password)
    location = (
        await client.post(
            f"{API}/locations", json={"name": "Review Branch 5", "code": "RB5"},
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
            json={"name": "Pulao", "description": None},
            headers=admin_headers,
        )
    ).json()
    await client.put(
        f"{API}/locations/{location['id']}/menu-items/{item['id']}/availability",
        json={"is_available": True, "price": "70.00"},
        headers=admin_headers,
    )

    employee, password = await seed_active_employee(p_no="EMP-086", email="emp86@example.com")
    headers = await _login(client, employee.p_no, password)

    unserved_order = (
        await client.post(
            f"{API}/orders",
            json={
                "location_id": location["id"],
                "order_type": "TAKEAWAY",
                "items": [{"menu_item_id": item["id"], "quantity": 1}],
            },
            headers=headers,
        )
    ).json()

    too_early = await client.post(
        f"{API}/reviews",
        json={
            "location_id": location["id"],
            "review_type": "ORDER",
            "order_id": unserved_order["id"],
            "overall_rating": 5,
        },
        headers=headers,
    )
    assert too_early.status_code == 422

    server, s_password = await seed_active_employee(
        p_no="SRV-086", email="srv86@example.com", role=EmployeeRole.SERVER
    )
    server_headers = await _login(client, server.p_no, s_password)
    await client.post(
        f"{API}/orders/{unserved_order['id']}/serve-directly", headers=server_headers
    )

    ok = await client.post(
        f"{API}/reviews",
        json={
            "location_id": location["id"],
            "review_type": "ORDER",
            "order_id": unserved_order["id"],
            "overall_rating": 5,
        },
        headers=headers,
    )
    assert ok.status_code == 201, ok.text

    other, other_password = await seed_active_employee(p_no="EMP-087", email="emp87@example.com")
    other_headers = await _login(client, other.p_no, other_password)
    forbidden = await client.post(
        f"{API}/reviews",
        json={
            "location_id": location["id"],
            "review_type": "ORDER",
            "order_id": unserved_order["id"],
            "overall_rating": 1,
        },
        headers=other_headers,
    )
    assert forbidden.status_code == 404
