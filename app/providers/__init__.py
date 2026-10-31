from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from app.config import Settings
from app.providers.api_football import ApiFootballProvider
from app.providers.odds_api import TheOddsApiProvider


@pytest.fixture
def settings() -> Settings:
    import os

    os.environ["API_FOOTBALL_KEY"] = "test-football-key"
    os.environ["ODDS_API_KEY"] = "test-odds-key"
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    return Settings()


def test_api_football_provider_uses_rapidapi_headers(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    provider = ApiFootballProvider(settings)

    class FakeResponse:
        def __init__(self) -> None:
            self.headers = {"x-ratelimit-requests-remaining": "12"}
            self.elapsed = None

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "response": [
                    {
                        "fixture": {"id": 101, "date": "2026-10-31T18:00:00+00:00", "status": {"long": "Scheduled"}},
                        "teams": {"home": {"name": "Arsenal"}, "away": {"name": "Chelsea"}},
                        "league": {"name": "Premier League"},
                    }
                ]
            }

    def fake_get(url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: int = 15) -> FakeResponse:
        assert headers is not None
        assert headers["x-rapidapi-key"] == "test-football-key"
        assert headers["x-rapidapi-host"] == "api-football-v1.p.rapidapi.com"
        return FakeResponse()

    monkeypatch.setattr("app.providers.api_football.httpx.get", fake_get)
    fixtures = provider.synchronize_fixtures("2026-10-31")

    assert fixtures[0]["home_team"] == "Arsenal"
    assert fixtures[0]["away_team"] == "Chelsea"
    assert "test-football-key" not in str(fixtures)


def test_odds_provider_uses_official_api_key_auth(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    provider = TheOddsApiProvider(settings)

    class FakeResponse:
        def __init__(self) -> None:
            self.headers = {"x-requests-remaining": "9"}
            self.elapsed = None

        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, Any]]:
            return [
                {
                    "id": "soccer_epl",
                    "bookmakers": [
                        {
                            "title": "Pinnacle",
                            "markets": [
                                {"key": "h2h", "outcomes": [{"name": "Arsenal", "price": 2.4}, {"name": "Chelsea", "price": 3.1}]}
                            ],
                        }
                    ],
                }
            ]

    def fake_get(url: str, params: dict[str, Any] | None = None, timeout: int = 15) -> FakeResponse:
        assert params is not None
        assert params["api_key"] == "test-odds-key"
        return FakeResponse()

    monkeypatch.setattr("app.providers.odds_api.httpx.get", fake_get)
    odds = provider.fetch_odds(101)

    assert odds[0]["bookmaker"] == "Pinnacle"
    assert odds[0]["outcome"] == "Arsenal"
    assert "test-odds-key" not in str(odds)


def test_missing_credentials_are_handled_gracefully(settings: Settings) -> None:
    settings.api_football_key = None
    provider = ApiFootballProvider(settings)
    result = provider.check_connection()
    assert result["connection_status"] == "missing_credentials"
    assert "None" not in str(result)


def test_status_response_does_not_expose_credentials(settings: Settings) -> None:
    provider = ApiFootballProvider(settings)
    provider.connection_status = "connected"
    provider.successful_requests = 4
    provider.failed_requests = 2
    provider.last_successful_sync = datetime.utcnow()
    status = provider.get_status().to_dict()
    assert "test-football-key" not in str(status)
    assert status["provider_name"] == "API-Football"


@pytest.mark.live
def test_live_provider_checks_require_real_credentials() -> None:
    football_key = __import__("os").environ.get("API_FOOTBALL_KEY")
    odds_key = __import__("os").environ.get("ODDS_API_KEY")
    if not football_key or not odds_key:
        pytest.skip("No live credentials have been configured; skipping live provider verification.")

    settings = Settings()
    football_status = ApiFootballProvider(settings).check_connection()
    odds_status = TheOddsApiProvider(settings).check_connection()
    assert football_status["connection_status"] in {"connected", "failed", "invalid_credentials"}
    assert odds_status["connection_status"] in {"connected", "failed", "invalid_credentials"}
    assert "API_FOOTBALL_KEY" not in str(football_status)
    assert "ODDS_API_KEY" not in str(odds_status)

