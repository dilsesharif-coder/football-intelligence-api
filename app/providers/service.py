from __future__ import annotations

from typing import Any

import httpx

from app.config import utcnow
from app.providers.base import BaseProvider, ProviderAuthenticationError


class TheOddsApiProvider(BaseProvider):
    provider_name = "The Odds API"
    base_url = "https://api.the-odds-api.com/v4"

    def _build_query_params(self) -> dict[str, str]:
        api_key = self._get_api_key("odds_api_key")
        return {
            "api_key": api_key,
            "regions": "uk",
            "markets": "h2h",
            "oddsFormat": "decimal",
        }

    def check_connection(self) -> dict[str, Any]:
        if not getattr(self.settings, "odds_api_key", None):
            self.connection_status = "missing_credentials"
            self.last_failed_request = utcnow()
            return {"provider_name": self.provider_name, "connection_status": "missing_credentials"}

        url = f"{self.base_url}/sports"
        try:
            response = httpx.get(url, params={"api_key": self._get_api_key("odds_api_key")}, timeout=self.timeout_seconds)
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

    def synchronize_fixtures(self) -> list[dict[str, Any]]:
        return []

    def fetch_odds(self, fixture_id: str | int | None = None) -> list[dict[str, Any]]:
        if not getattr(self.settings, "odds_api_key", None):
            raise ProviderAuthenticationError("The Odds API: missing ODDS_API_KEY")

        url = f"{self.base_url}/sports/soccer_epl/odds"
        params = self._build_query_params()
        response = httpx.get(url, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        odds_result = []
        for item in payload:
            bookmakers = item.get("bookmakers", [])
            for bookmaker in bookmakers:
                for market in bookmaker.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        odds_result.append(
                            {
                                "provider_name": self.provider_name,
                                "fixture_external_id": str(item.get("id")) if item.get("id") is not None else fixture_id,
                                "bookmaker": bookmaker.get("title"),
                                "market": market.get("key"),
                                "outcome": outcome.get("name"),
                                "odds": outcome.get("price"),
                                "metadata": item,
                            }
                        )
        self._record_success(response)
        self.last_successful_sync = utcnow()
        return odds_result
