from __future__ import annotations
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from arenaflow.api.routes import router
from arenaflow.config import load_settings
from arenaflow.core.retriever import Retriever

STATIC_DIR = Path(__file__).parent / "static"

# Pages are read once at startup and served from memory. A FileResponse
# would make Starlette stream the file through anyio's thread pool, which
# deadlocks under httpx.ASGITransport + asyncio.run (the test
# transport) and is needless per-request disk I/O anyway.
_PAGES = {
    "/": (STATIC_DIR / "index.html").read_text(encoding="utf-8"),
    "/fan": (STATIC_DIR / "fan.html").read_text(encoding="utf-8"),
    "/ops": (STATIC_DIR / "ops.html").read_text(encoding="utf-8"),
}


async def _security_headers(response: Response) -> None:
    """Defensive HTTP headers on every app response.

    Async (not sync) so FastAPI runs it on the event loop instead of
    pushing it to anyio's thread pool. A sync dependency deadlocks under
    httpx.ASGITransport (the test client) because the worker thread
    can't be scheduled; async avoids the thread pool and also works under
    uvicorn and Starlette TestClient.
    """
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "frame-ancestors 'none';"
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="ArenaFlow",
        version="0.1.0",
        dependencies=[Depends(_security_headers)],
    )
    app.include_router(router)
    app.state.settings = load_settings()
    app.state.retriever = Retriever()
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )

    @app.get("/")
    async def index() -> Response:
        return HTMLResponse(_PAGES["/"])

    @app.get("/fan")
    async def fan_page() -> Response:
        return HTMLResponse(_PAGES["/fan"])

    @app.get("/ops")
    async def ops_page() -> Response:
        return HTMLResponse(_PAGES["/ops"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "arenaflow.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
