from tests.api.conftest import SMA_CROSS

INVALID = {
    "long_entry": {"type": "condition", "left": {"type": "indicator", "indicator": "NOPE"},
                   "operator": ">", "right": {"type": "value", "value": 1}},
    "long_exit": SMA_CROSS["long_exit"],
}


def test_crud(client, auth):
    created = client.post("/strategies", json={"name": "first", "strategy_json": SMA_CROSS}, headers=auth)
    assert created.status_code == 201
    strategy_id = created.json()["strategy_id"]

    listing = client.get("/strategies", headers=auth).json()
    assert listing["total"] == 1 and listing["strategies"][0]["name"] == "first"

    updated = client.put(f"/strategies/{strategy_id}", json={"name": "renamed"}, headers=auth)
    assert updated.status_code == 200 and updated.json()["name"] == "renamed"
    assert updated.json()["strategy_json"] == SMA_CROSS

    assert client.delete(f"/strategies/{strategy_id}", headers=auth).status_code == 204
    assert client.get(f"/strategies/{strategy_id}", headers=auth).status_code == 404


def test_invalid_strategy_is_rejected_on_create_and_update(client, auth, strategy_id):
    created = client.post("/strategies", json={"name": "bad", "strategy_json": INVALID}, headers=auth)
    assert created.status_code == 422
    detail = created.json()["detail"]
    assert detail["message"] == "Invalid strategy"
    assert "unknown indicator 'NOPE'" in detail["errors"][0]

    updated = client.put(f"/strategies/{strategy_id}", json={"strategy_json": INVALID}, headers=auth)
    assert updated.status_code == 422


def test_validate_endpoint(client, auth):
    bad = client.post("/strategies/validate", json={"strategy_json": INVALID}, headers=auth).json()
    assert bad["valid"] is False and bad["errors"]

    good = client.post("/strategies/validate", json={"strategy_json": SMA_CROSS}, headers=auth).json()
    assert good == {"valid": True, "errors": [], "warnings": []}


def test_users_cannot_see_each_others_strategies(client, make_user, auth, strategy_id):
    other = make_user("mallory")
    assert client.get(f"/strategies/{strategy_id}", headers=other).status_code == 404
    assert client.put(f"/strategies/{strategy_id}", json={"name": "x"}, headers=other).status_code == 404
    assert client.delete(f"/strategies/{strategy_id}", headers=other).status_code == 404
    assert client.get("/strategies", headers=other).json()["total"] == 0
