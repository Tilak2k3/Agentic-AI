"""FastAPI application entrypoint."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentic_ai.api.routers import cr, health, integrations, plan
from agentic_ai.config import get_api_cors_origins


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agentic AI API",
        description="CR agent, plan agent, inputs, Jira, and Smartsheet integrations.",
        version="0.2.0",
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
