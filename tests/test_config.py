import pytest
from pydantic import ValidationError


def test_chat_credentials_are_required(monkeypatch):
    from app.config import Settings
    monkeypatch.delenv("CHAT_API_KEY")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_token_budget_can_be_configured(monkeypatch):
    from app.config import Settings
    monkeypatch.setenv("TOKEN_BUDGET", "500")
    assert Settings(_env_file=None).token_budget == 500


def test_application_loads_without_future_services():
    from app.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").json()["info"]["title"] == "MewHelp"
