from fastapi.testclient import TestClient


def test_signup_login_me_and_logout(client: TestClient):
    signup = client.post(
        "/auth/signup",
        json={
            "full_name": "Ayesha Khan",
            "email": "ayesha@example.com",
            "password": "strong-password-123",
            "password_confirm": "strong-password-123",
        },
    )
    assert signup.status_code == 201
    assert signup.json()["account"]["email"] == "ayesha@example.com"

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["full_name"] == "Ayesha Khan"

    logout = client.post("/auth/logout")
    assert logout.status_code == 204
    assert client.get("/auth/me").status_code == 401

    login = client.post(
        "/auth/login",
        json={
            "email": "ayesha@example.com",
            "password": "strong-password-123",
        },
    )
    assert login.status_code == 200
    assert client.get("/auth/me").status_code == 200


def test_duplicate_signup_and_wrong_password(client: TestClient):
    payload = {
        "full_name": "Ayesha Khan",
        "email": "ayesha@example.com",
        "password": "strong-password-123",
        "password_confirm": "strong-password-123",
    }
    assert client.post("/auth/signup", json=payload).status_code == 201
    assert client.post("/auth/signup", json=payload).status_code == 409

    wrong_login = client.post(
        "/auth/login",
        json={"email": "ayesha@example.com", "password": "wrong"},
    )
    assert wrong_login.status_code == 401


def test_password_confirmation_validation(client: TestClient):
    response = client.post(
        "/auth/signup",
        json={
            "full_name": "Ayesha Khan",
            "email": "ayesha@example.com",
            "password": "strong-password-123",
            "password_confirm": "different-password",
        },
    )
    assert response.status_code == 422
