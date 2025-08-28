from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from sqler.models import StaleVersionError


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StaleVersionError)
    async def _stale_handler(_, exc: StaleVersionError):
        return JSONResponse(
            {"detail": "version conflict", "error": "StaleVersionError"},
            status_code=409,
        )

    @app.exception_handler(RuntimeError)
    async def _runtime_handler(_, exc: RuntimeError):
        # Optional: centralize unexpected runtime failures
        raise HTTPException(status_code=500, detail=str(exc))

