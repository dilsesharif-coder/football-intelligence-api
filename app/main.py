from __future__ import annotations

from typing import Any

from app.cache import TTLCache
from app.config import Settings
from app.providers.api_football import ApiFootballProvider
from app.providers.odds_api import TheOddsApiProvider


class ProviderRegistry:
    def __init__(self, settings: Settings, cache: TTLCache | None = None) -> None:
        self.settings = settings
        self.cache = cache or TTLCache()
        self.providers = [
            ApiFootballProvider(settings, cache=self.cache),
            TheOddsApiProvider(settings, cache=self.cache),
        ]

    def get_statuses(self) -> list[dict[str, Any]]:
        status_payload: list[dict[str, Any]] = []
        for provider in self.providers:
            status = provider.get_status()
            if provider.connection_status in {"unknown", "error", "failed"}:
                try:
                    provider_status = provider.check_connection()
                    if provider_status.get("connection_status") == "connected":
                        provider.connection_status = "connected"
                    elif provider_status.get("connection_status") == "missing_credentials":
                        provider.connection_status = "missing_credentials"
                except Exception:
                    provider.connection_status = "failed"
            status_payload.append(status.to_dict())
        return status_payload

    def synchronize_all(self) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for provider in self.providers:
            if provider.provider_name == "API-Football":
                results[provider.provider_name] = provider.synchronize_fixtures()
            elif provider.provider_name == "The Odds API":
                results[provider.provider_name] = provider.fetch_odds()
        return results
