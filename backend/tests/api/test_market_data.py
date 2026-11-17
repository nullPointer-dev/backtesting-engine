from tests.api.conftest import BARS, SYMBOL


def test_symbols_report_coverage(client, auth):
    symbols = client.get("/market-data/symbols", headers=auth).json()["symbols"]
    assert symbols[0]["symbol"] == SYMBOL
    coverage = symbols[0]["timeframes"][0]
    assert coverage["timeframe"] == "1d" and coverage["bars"] == BARS
    assert coverage["first"] < coverage["last"]


def test_history_latest_bars_by_default(client, auth):
    data = client.get(f"/market-data/{SYMBOL}/history?limit=5", headers=auth).json()["data"]
    assert len(data) == 5
    times = [bar["datetime"] for bar in data]
    assert times == sorted(times)
    latest = client.get(f"/market-data/{SYMBOL.lower()}/latest", headers=auth).json()
    assert latest["datetime"] == times[-1]


def test_history_from_start_date(client, auth):
    data = client.get(
        f"/market-data/{SYMBOL}/history?start_date=2022-01-01&limit=3", headers=auth
    ).json()["data"]
    assert [bar["datetime"][:10] for bar in data] == ["2022-01-03", "2022-01-04", "2022-01-05"]


def test_unknown_symbol(client, auth):
    assert client.get("/market-data/NOPE.NS/latest", headers=auth).status_code == 404
    assert client.get("/market-data/NOPE.NS/history", headers=auth).json()["data"] == []
