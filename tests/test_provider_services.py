from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.db import Base, engine
from app.providers.service import ProviderRegistry

app = FastAPI(title="Football Intelligence API")


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(bind=engine)
    app.state.registry = ProviderRegistry(settings)


@app.get("/health")
def health() -> dict[str, Any]:
    with engine.begin() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name}


@app.get("/admin/integrations")
def admin_integrations() -> dict[str, Any]:
    registry: ProviderRegistry | None = getattr(app.state, "registry", None)
    if registry is None:
        registry = ProviderRegistry(settings)
    return {"providers": registry.get_statuses()}


@app.get("/admin/integrations/{provider_name}")
def admin_integration(provider_name: str) -> JSONResponse:
    registry: ProviderRegistry | None = getattr(app.state, "registry", None)
    if registry is None:
        registry = ProviderRegistry(settings)

    matches = [status for status in registry.get_statuses() if status["provider_name"].lower() == provider_name.lower()]
    if not matches:
        return JSONResponse(status_code=404, content={"detail": "Provider not found"})
    return JSONResponse(content={"provider": matches[0]})


@app.post("/admin/sync")
def sync_integrations() -> dict[str, Any]:
    registry: ProviderRegistry | None = getattr(app.state, "registry", None)
    if registry is None:
        registry = ProviderRegistry(settings)
    return {"sync_results": registry.synchronize_all()}
