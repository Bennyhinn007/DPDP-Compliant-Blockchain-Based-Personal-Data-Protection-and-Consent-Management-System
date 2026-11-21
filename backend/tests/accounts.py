"""Create synthetic accounts for tests that require an authenticated role."""

from app.config import get_config
from app.extensions import get_db
from app.services.auth_service import AuthService


def create_test_account(client, *, email, password, role, full_name):
    if role == "patient":
        response = client.post("/api/v1/auth/register", json={
            "email": email, "password": password, "full_name": full_name,
        })
        assert response.status_code == 201
        return response.json["user"]

    with client.application.app_context():
        service = AuthService(get_db(), get_config("testing"))
        return service.register(email, password, role, full_name, allow_privileged_roles=True)
