from httpx import AsyncClient

from app.models.enums import EmployeeRole
from tests.conftest import SeedEmployee, extract_otp

API = "/api/v1/auth"


async def test_full_registration_to_login_flow(
    client: AsyncClient, seed_active_employee: SeedEmployee, outbox: list[dict[str, str]]
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-001", email="admin@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    login = await client.post(f"{API}/login", json={"p_no": admin.p_no, "password": admin_password})
    assert login.status_code == 200
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    register = await client.post(
        f"{API}/register",
        json={"p_no": "EMP-100", "email": "newhire@example.com", "name": "New Hire"},
    )
    assert register.status_code == 201, register.text
    registration_id = register.json()["id"]

    pending = await client.get(f"{API}/registrations", headers=admin_headers)
    assert pending.status_code == 200
    assert any(r["id"] == registration_id for r in pending.json())

    approve = await client.post(
        f"{API}/registrations/{registration_id}/approve", headers=admin_headers
    )
    assert approve.status_code == 200

    approval_email = next(e for e in outbox if e["to"] == "newhire@example.com")
    temporary_password = approval_email["body"].split("temporary password is ")[1].split(".")[0]

    first_login = await client.post(
        f"{API}/login", json={"p_no": "EMP-100", "password": temporary_password}
    )
    assert first_login.status_code == 422
    assert first_login.json()["error_code"] == "activation_required"

    wrong_first_login = await client.post(
        f"{API}/login", json={"p_no": "EMP-100", "password": "not-the-temp-password"}
    )
    assert wrong_first_login.status_code == 401
    assert wrong_first_login.json()["error_code"] == "authentication_error"

    start = await client.post(
        f"{API}/activation/start",
        json={"p_no": "EMP-100", "temporary_password": temporary_password},
    )
    assert start.status_code == 200

    activation_email = next(e for e in outbox if e["subject"] == "Your activation code")
    code = extract_otp(activation_email["body"])

    verify = await client.post(
        f"{API}/activation/verify-otp", json={"p_no": "EMP-100", "code": code}
    )
    assert verify.status_code == 200
    change_token = verify.json()["change_token"]

    set_password = await client.post(
        f"{API}/activation/set-password",
        json={"p_no": "EMP-100", "change_token": change_token, "new_password": "NewPassw0rd1"},
    )
    assert set_password.status_code == 200
    tokens = set_password.json()
    assert tokens["must_change_password"] is False

    me = await client.get(
        f"{API}/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["p_no"] == "EMP-100"
    assert me.json()["status"] == "ACTIVE"

    login_again = await client.post(
        f"{API}/login", json={"p_no": "EMP-100", "password": "NewPassw0rd1"}
    )
    assert login_again.status_code == 200

    refreshed = await client.post(
        f"{API}/token/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200

    reused = await client.post(
        f"{API}/token/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reused.status_code == 401

    logout = await client.post(
        f"{API}/logout", json={"refresh_token": refreshed.json()["refresh_token"]}
    )
    assert logout.status_code == 204


async def test_password_reset_flow(
    client: AsyncClient, seed_active_employee: SeedEmployee, outbox: list[dict[str, str]]
) -> None:
    employee, old_password = await seed_active_employee(p_no="EMP-200", email="reset@example.com")

    forgot = await client.post(f"{API}/password/forgot", json={"p_no": employee.p_no})
    assert forgot.status_code == 200

    reset_email = next(e for e in outbox if e["to"] == "reset@example.com")
    code = extract_otp(reset_email["body"])

    verify = await client.post(
        f"{API}/password/reset/verify-otp", json={"p_no": employee.p_no, "code": code}
    )
    assert verify.status_code == 200
    change_token = verify.json()["change_token"]

    reset = await client.post(
        f"{API}/password/reset",
        json={"p_no": employee.p_no, "change_token": change_token, "new_password": "Reset0Pass"},
    )
    assert reset.status_code == 200

    old_login = await client.post(
        f"{API}/login", json={"p_no": employee.p_no, "password": old_password}
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        f"{API}/login", json={"p_no": employee.p_no, "password": "Reset0Pass"}
    )
    assert new_login.status_code == 200


async def test_forgot_password_unknown_p_no_does_not_leak(client: AsyncClient) -> None:
    response = await client.post(f"{API}/password/forgot", json={"p_no": "NOBODY-1"})
    assert response.status_code == 200


async def test_login_locks_account_after_too_many_failures(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    employee, _ = await seed_active_employee(p_no="EMP-300", email="lockout@example.com")

    for _ in range(5):
        resp = await client.post(
            f"{API}/login", json={"p_no": employee.p_no, "password": "WrongPass1"}
        )
        assert resp.status_code == 401

    locked = await client.post(
        f"{API}/login", json={"p_no": employee.p_no, "password": "WrongPass1"}
    )
    assert locked.status_code == 423


async def test_non_admin_cannot_approve_registrations(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    employee, password = await seed_active_employee(p_no="EMP-400", email="regular@example.com")
    login = await client.post(f"{API}/login", json={"p_no": employee.p_no, "password": password})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.get(f"{API}/registrations", headers=headers)
    assert response.status_code == 403


async def test_registration_rejects_disallowed_email_domain(client: AsyncClient) -> None:
    response = await client.post(
        f"{API}/register",
        json={"p_no": "EMP-500", "email": "someone@not-allowed.com", "name": "Someone"},
    )
    assert response.status_code == 422


async def test_employee_directory_search(
    client: AsyncClient, seed_active_employee: SeedEmployee
) -> None:
    admin, admin_password = await seed_active_employee(
        p_no="ADM-600", email="admin600@example.com", role=EmployeeRole.SYSTEM_ADMINISTRATOR
    )
    admin_login = await client.post(
        f"{API}/login", json={"p_no": admin.p_no, "password": admin_password}
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    manager, manager_password = await seed_active_employee(
        p_no="MGR-600",
        email="mgr600@example.com",
        name="Searchable Manager",
        role=EmployeeRole.LOCATION_MANAGER,
    )
    await seed_active_employee(p_no="EMP-600", email="emp600@example.com")

    manager_login = await client.post(
        f"{API}/login", json={"p_no": manager.p_no, "password": manager_password}
    )
    manager_headers = {"Authorization": f"Bearer {manager_login.json()['access_token']}"}
    forbidden = await client.get("/api/v1/employees", headers=manager_headers)
    assert forbidden.status_code == 403

    by_role = await client.get(
        "/api/v1/employees", params={"role": "LOCATION_MANAGER"}, headers=admin_headers
    )
    assert by_role.status_code == 200, by_role.text
    assert any(e["id"] == str(manager.id) for e in by_role.json())
    assert all(e["role"] == "LOCATION_MANAGER" for e in by_role.json())

    by_query = await client.get(
        "/api/v1/employees", params={"q": "Searchable"}, headers=admin_headers
    )
    assert by_query.status_code == 200
    assert [e["id"] for e in by_query.json()] == [str(manager.id)]
