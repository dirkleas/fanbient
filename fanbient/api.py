"""FastAPI REST wrapper for fanbient service.

Exposes the same core functionality as the CLI via HTTP endpoints.
Start with: fanbient serve
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from fanbient.config import FanbientConfig
from fanbient.service import FanbientService


# --- Request/Response models ---

class StartRequest(BaseModel):
    model_path: str | None = None
    dry_run: bool = False

class TriggerRequest(BaseModel):
    trigger_type: str  # "panting", "temperature", "manual"

class TempRequest(BaseModel):
    temp_f: float
    source: str = "external"

class FanCommandRequest(BaseModel):
    on: bool


# --- App factory ---

_service: FanbientService | None = None


def create_app(config: FanbientConfig | None = None) -> FastAPI:
    """Create a FastAPI app wrapping the fanbient service."""
    if config is None:
        config = FanbientConfig()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global _service
        _service = FanbientService(config, dry_run=True)
        yield
        if _service and _service.status().running:
            _service.stop()

    api = FastAPI(
        title="fanbient",
        description="Ambient smart fan system REST API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @api.get("/status")
    def get_status():
        """Get current service status."""
        if _service is None:
            raise HTTPException(503, "Service not initialized")
        return _service.status().to_dict()

    @api.post("/start")
    def start(req: StartRequest):
        """Start the fanbient service."""
        if _service is None:
            raise HTTPException(503, "Service not initialized")
        _service.dry_run = req.dry_run
        _service.start(model_path=req.model_path, background=True)
        return {"status": "started"}

    @api.post("/stop")
    def stop():
        """Stop the fanbient service."""
        if _service is None:
            raise HTTPException(503, "Service not initialized")
        _service.stop()
        return {"status": "stopped"}

    @api.post("/fan")
    def fan_command(req: FanCommandRequest):
        """Manually control the fan."""
        if _service is None:
            raise HTTPException(503, "Service not initialized")
        if req.on:
            _service.manual_fan_on()
        else:
            _service.manual_fan_off()
        return {"fan": "on" if req.on else "off"}

    @api.post("/trigger")
    def fire_trigger(req: TriggerRequest):
        """Fire a trigger programmatically."""
        if _service is None:
            raise HTTPException(503, "Service not initialized")
        _service.trigger(req.trigger_type)
        return {"triggered": req.trigger_type}

    @api.post("/trigger/clear")
    def clear_trigger(req: TriggerRequest):
        """Clear a trigger."""
        if _service is None:
            raise HTTPException(503, "Service not initialized")
        _service.clear_trigger(req.trigger_type)
        return {"cleared": req.trigger_type}

    @api.post("/temperature")
    def push_temperature(req: TempRequest):
        """Push a temperature reading."""
        if _service is None:
            raise HTTPException(503, "Service not initialized")
        _service.push_temperature(req.temp_f, req.source)
        return {"temp_f": req.temp_f, "source": req.source}

    return api
