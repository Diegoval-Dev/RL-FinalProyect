import re
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from vulnapp.db import PostgresRunner, QueryOutcome
from vulnapp.queries import ENDPOINTS, EndpointSpec, build_sql

QueryRunner = Callable[..., QueryOutcome]

FEATURED_PRODUCTS_SQL = (
    "SELECT id, name, price FROM products WHERE hidden = false ORDER BY id LIMIT 3"
)
COMMENTS_SQL = "SELECT author, body FROM comments WHERE product_id = %s ORDER BY id DESC LIMIT 50"
CART_SQL = (
    "SELECT c.product_id, p.name, c.qty FROM cart_items c "
    "JOIN products p ON p.id = c.product_id WHERE c.user_id = %s ORDER BY c.id DESC LIMIT 50"
)
CART_OWNER_ID = 2
INTEGER_PATTERN = re.compile(r"^\d{1,9}$")


def outcome_response(outcome: QueryOutcome) -> JSONResponse:
    if outcome.error is not None:
        return JSONResponse({"error": outcome.error}, status_code=500)
    return JSONResponse(jsonable_encoder({"rows": outcome.rows}))


async def read_body(request: Request, spec: EndpointSpec) -> dict:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json") and "json" in spec.locations:
        body = await request.json()
        return body if isinstance(body, dict) else {}
    is_form = content_type.startswith(("application/x-www-form-urlencoded", "multipart/form-data"))
    if is_form and "form" in spec.locations:
        return dict(await request.form())
    return {}


async def read_values(request: Request, spec: EndpointSpec) -> dict[str, str]:
    raw = dict(request.query_params) if request.method == "GET" else await read_body(request, spec)
    missing = [param for param in spec.params if param not in raw]
    if missing:
        raise HTTPException(status_code=400, detail=f"missing params: {', '.join(missing)}")
    return {param: str(raw[param]) for param in spec.params}


def register_vulnerable_endpoint(app: FastAPI, spec: EndpointSpec, runner: QueryRunner) -> None:
    async def handle(request: Request) -> JSONResponse:
        values = await read_values(request, spec)
        outcome = await run_in_threadpool(runner, build_sql(spec, values))
        if spec.returns_rows or outcome.error is not None:
            return outcome_response(outcome)
        return JSONResponse({"ok": True})

    app.add_api_route(spec.path, handle, methods=list(spec.methods), name=spec.name)


def parse_identifier(raw: str) -> int:
    if not INTEGER_PATTERN.match(raw):
        raise HTTPException(status_code=400, detail="invalid identifier")
    return int(raw)


def register_benign_endpoints(app: FastAPI, runner: QueryRunner) -> None:
    @app.get("/")
    async def home() -> JSONResponse:
        outcome = await run_in_threadpool(runner, FEATURED_PRODUCTS_SQL)
        return outcome_response(outcome)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/comments")
    async def list_comments(product_id: str) -> JSONResponse:
        outcome = await run_in_threadpool(runner, COMMENTS_SQL, (parse_identifier(product_id),))
        return outcome_response(outcome)

    @app.get("/cart")
    async def list_cart() -> JSONResponse:
        outcome = await run_in_threadpool(runner, CART_SQL, (CART_OWNER_ID,))
        return outcome_response(outcome)


def create_app(runner: QueryRunner | None = None) -> FastAPI:
    runner = runner or PostgresRunner()
    app = FastAPI(title="vulnapp", docs_url=None, redoc_url=None)
    register_benign_endpoints(app, runner)
    for spec in ENDPOINTS:
        register_vulnerable_endpoint(app, spec, runner)
    return app
