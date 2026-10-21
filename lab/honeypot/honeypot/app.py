"""Honeypot: imitates vulnapp's response shape without touching the real database."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

FAKE_ROWS = [
    {"id": 1, "name": "Producto de muestra", "price": 99.0},
    {"id": 2, "name": "Artículo genérico", "price": 49.0},
]


def create_app() -> FastAPI:
    app = FastAPI(title="honeypot", docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.api_route("/{path:path}", methods=["GET", "POST"])
    async def anything(path: str, request: Request) -> JSONResponse:
        return JSONResponse({"rows": FAKE_ROWS})

    return app


app = create_app()
