from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import Settings, utcnow


class ProviderAuthenticationError(RuntimeError):
    pass


@dataclass
class ProviderStatus:
    name: str
    connection_status: str
    last_successful_sync: datetime | None = None
    last_failed_request: datetime | None = None
    available_quota: int | None = None
    successful_requests: int = 0
    failed_requests: int = 0
    response_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.name,
            "connection_status": self.connection_status,
            "last_successful_sync": self.last_successful_sync.isoformat() if self.last_successful_sync else None,
            "last_failed_request": self.last_failed_request.isoformat() if self.last_failed_request else None,
            "available_quota": self.available_quota,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "response_time_ms": self.response_time_ms,
        }


class BaseProvider:
    provider_name: str = "base"
    base_url: str = ""
    timeout_seconds: int = 15

    def __init__(self, settings: Settings, cache: Any | None = None) -> None:
        self.settings = settings
        self.cache = cache
        self.connection_status = "unknown"
        self.last_successful_sync: datetime | None = None
        self.last_failed_request: datetime | None = None
        self.available_quota: int | None = None
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_time_ms: float | None = None

    def _get_api_key(self, key_name: str) -> str:
        key = getattr(self.settings, key_name, None)
        if not key or not str(key).strip():
            raise ProviderAuthenticationError(f"{self.provider_name}: missing credential for {key_name}")
        return key

    def _build_headers(self) -> dict[str, str]:
        return {}

    def _build_query_params(self) -> dict[str, str]:
        return {}

    def _parse_quota(self, response: httpx.Response) -> int | None:
        header_candidates = [
            "x-ratelimit-requests-remaining",
            "x-requests-remaining",
            "x-api-requests-remaining",
        ]
        for header_name in header_candidates:
            value = response.headers.get(header_name)
            if value is not None:
                try:
                    return int(value)
                except ValueError:
                    continue
        return None

    def _record_success(self, response: httpx.Response | None = None) -> None:
        self.successful_requests += 1
        self.last_successful_sync = utcnow()
        self.connection_status = "connected"
        if response is not None:
            self.available_quota = self._parse_quota(response)
            if response.elapsed is not None:
                self.response_time_ms = round(response.elapsed.total_seconds() * 1000, 2)

    def _record_failure(self, exc: Exception | None = None) -> None:
        self.failed_requests += 1
        self.last_failed_request = utcnow()
        self.connection_status = "error"
        if exc is not None and self.failed_requests > 0:
            self.connection_status = "failed"

    def get_status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.provider_name,
            connection_status=self.connection_status,
            last_successful_sync=self.last_successful_sync,
            last_failed_request=self.last_failed_request,
            available_quota=self.available_quota,
            successful_requests=self.successful_requests,
            failed_requests=self.failed_requests,
            response_time_ms=self.response_time_ms,
        )

    def check_connection(self) -> dict[str, Any]:
        raise NotImplementedError

    def synchronize_fixtures(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def fetch_odds(self, fixture_id: str | int | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError
