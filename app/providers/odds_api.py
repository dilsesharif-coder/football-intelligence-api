from __future__ import annotations

from typing import Any

import httpx

from app.config import utcnow
from app.providers.base import BaseProvider, ProviderAuthenticationError


class ApiFootballProvider(BaseProvider):
    provider_name = "API-Football"
    base_url = "https://api-football-v1.p.rapidapi.com/v3"

    def _build_headers(self) -> dict[str, str]:
        api_key = self._get_api_key("api_football_key")
        return {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "api-football-v1.p.rapidapi.com",
            "Accept": "application/json",
        }

    def check_connection(self) -> dict[str, Any]:
        if not getattr(self.settings, "api_football_key", None):
            self.connection_status = "missing_credentials"
            self.last_failed_request = utcnow()
            return {"provider_name": self.provider_name, "connection_status": "missing_credentials"}

        url = f"{self.base_url}/status"
        try:
            response = httpx.get(url, headers=self._build_headers(), timeout=self.timeout_seconds)
            response.raise_for_status()
            self._record_success(response)
            return {
                "provider_name": self.provider_name,
                "connection_status": "connected",
                "available_quota": self._parse_quota(response),
            }
        except ProviderAuthenticationError:
            self.connection_status = "missing_credentials"
            self.last_failed_request = utcnow()
            return {"provider_name": self.provider_name, "connection_status": "missing_credentials"}
        except httpx.HTTPStatusError as exc:
            self._record_failure(exc)
            return {"provider_name": self.provider_name, "connection_status": "invalid_credentials"}
        except httpx.RequestError as exc:
            self._record_failure(exc)
            return {"provider_name": self.provider_name, "connection_status": "failed"}

    def synchronize_fixtures(self, match_day: str | None = None) -> list[dict[str, Any]]:
        if not getattr(self.settings, "api_football_key", None):
            raise ProviderAuthenticationError("API-Football: missing API_FOOTBALL_KEY")

        target_day = match_day or utcnow().strftime("%Y-%m-%d")
        url = f"{self.base_url}/fixtures"
        params = {"date": target_day}
        response = httpx.get(url, params=params, headers=self._build_headers(), timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        fixtures = payload.get("response", [])
        normalized = []
        for fixture in fixtures:
            fixture_data = fixture.get("fixture", {})
            teams = fixture.get("teams", {})
            league = fixture.get("league", {})
            normalized.append(
                {
                    "external_id": str(fixture_data.get("id")),
                    "provider_name": self.provider_name,
                    "league_name": league.get("name"),
                    "home_team": teams.get("home", {}).get("name"),
                    "away_team": teams.get("away", {}).get("name"),
                    "kickoff_at": fixture_data.get("date"),
                    "status": fixture_data.get("status", {}).get("long"),
                    "metadata": fixture_data,
                }
            )
        self._record_success(response)
        self.last_successful_sync = utcnow()
        return normalized

    def fetch_odds(self, fixture_id: str | int | None = None) -> list[dict[str, Any]]:
        return []
