import pytest
from datetime import datetime

def test_tally_pull_and_analytics(client, db_session):
    # First, test pulling tally data
    resp_pull = client.post("/api/analytics/tally-pull")
    assert resp_pull.status_code == 200
    assert resp_pull.json() == {"status": "success", "message": "Imported ledgers and transactions from Tally"}

    # Test PNL Summary
    resp_pnl = client.get("/api/analytics/pnl-summary")
    assert resp_pnl.status_code == 200
    pnl_data = resp_pnl.json()
    assert "total_revenue" in pnl_data
    assert "direct_expenses" in pnl_data
    assert "gross_profit" in pnl_data
    assert "net_profit" in pnl_data

    # Test Cost Breakdown
    resp_cost = client.get("/api/analytics/cost-breakdown")
    assert resp_cost.status_code == 200
    cost_data = resp_cost.json()
    assert "direct_expenses" in cost_data
    assert "indirect_expenses" in cost_data
    assert "total_expenses" in cost_data
    assert "details" in cost_data

    # Test fetching ledgers
    resp_ledgers = client.get("/api/analytics/ledgers")
    assert resp_ledgers.status_code == 200
    ledgers = resp_ledgers.json()
    assert isinstance(ledgers, list)
    if len(ledgers) > 0:
        assert "name" in ledgers[0]
        assert "transactions" in ledgers[0]
