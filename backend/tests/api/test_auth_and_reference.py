def test_register_login_me(client):
    response = client.post("/auth/register", json={"username": "bob", "password": "secret123"})
    assert response.status_code == 201
    assert response.json()["username"] == "bob"

    token = client.post("/auth/login", json={"username": "bob", "password": "secret123"}).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["username"] == "bob"


def test_form_login_for_swagger(client, make_user):
    make_user("carol")
    response = client.post("/auth/token", data={"username": "carol", "password": "secret123"})
    assert response.status_code == 200 and response.json()["token_type"] == "bearer"


def test_duplicate_username(client, make_user):
    make_user("dave")
    response = client.post("/auth/register", json={"username": "dave", "password": "secret123"})
    assert response.status_code == 400


def test_wrong_password_and_bad_token(client, make_user):
    make_user("erin")
    assert client.post("/auth/login", json={"username": "erin", "password": "nope123"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.get("/strategies").status_code == 401


def test_reference_data_is_public(client):
    response = client.get("/indicators")
    assert response.status_code == 200
    body = response.json()
    names = {item["name"] for item in body["indicators"]}
    assert {"SMA", "RSI", "MACD_LINE", "SUPERTREND"} <= names
    assert "crosses_above" in {op["value"] for op in body["comparison_operators"]}
    assert body["timeframes"] == ["1m", "5m", "15m", "30m", "60m", "1d", "1wk"]


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
