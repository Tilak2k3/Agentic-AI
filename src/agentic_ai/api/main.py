"""FastAPI application entrypoint."""

from __future__ import annotations

import os

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agentic_ai.api.routers import cr, health, inputs, integrations, pipeline, plan, raid
from agentic_ai.config import get_api_cors_origins

_FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agentic AI API",
        description="CR, Plan, and RAID agents (LLM-driven), input extraction, Jira, and Smartsheet.",
        version="0.4.0",
    )
    origins = get_api_cors_origins()
    creds = not any(o.strip() == "*" for o in origins)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=creds,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(integrations.router, prefix="/api/v1")
    app.include_router(plan.router, prefix="/api/v1")
    app.include_router(cr.router, prefix="/api/v1")
    app.include_router(raid.router, prefix="/api/v1")
    app.include_router(inputs.router, prefix="/api/v1")
    app.include_router(pipeline.router, prefix="/api/v1")

    if _FRONTEND_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")

        @app.get("/")
        async def serve_ui() -> FileResponse:
            return FileResponse(_FRONTEND_DIR / "index.html")

    return app


app = create_app()


def main() -> None:
    """CLI entry: `python -m agentic_ai.api.main` or uvicorn agentic_ai.api.main:app."""
    import uvicorn

    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))
    uvicorn.run("agentic_ai.api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
