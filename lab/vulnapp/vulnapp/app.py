import re
import uuid
from collections.abc import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from vulnapp.db import OracleLog, PostgresRunner, QueryOutcome, QueryRecord
from vulnapp.queries import ENDPOINTS, EndpointSpec, build_sql

QueryRunner = Callable[..., QueryOutcome]
QueryRecorder = Callable[[QueryRecord], None]

REQUEST_ID_HEADER = "X-Request-ID"
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


class QueryExecutor:
    """Runs each query and records it; oracle_log is built from these records."""

    def __init__(self, runner: QueryRunner, recorder: QueryRecorder):
        self._runner = runner
        self._recorder = recorder

    async def run(
        self, request_id: str, endpoint: str, sql: str, params: tuple | None = None
    ) -> QueryOutcome:
        outcome = await run_in_threadpool(self._runner, sql, params)
        await run_in_threadpool(self._recorder, QueryRecord(request_id, endpoint, sql, outcome))
        return outcome


def request_id_of(request: Request) -> str:
    return request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex


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


def register_vulnerable_endpoint(app: FastAPI, spec: EndpointSpec, executor: QueryExecutor) -> None:
    async def handle(request: Request) -> JSONResponse:
        values = await read_values(request, spec)
        outcome = await executor.run(request_id_of(request), spec.name, build_sql(spec, values))
        if spec.returns_rows or outcome.error is not None:
            return outcome_response(outcome)
        return JSONResponse({"ok": True})

    app.add_api_route(spec.path, handle, methods=list(spec.methods), name=spec.name)


def parse_identifier(raw: str) -> int:
    if not INTEGER_PATTERN.match(raw):
        raise HTTPException(status_code=400, detail="invalid identifier")
    return int(raw)


def register_benign_endpoints(app: FastAPI, executor: QueryExecutor) -> None:
    @app.get("/")
    async def home(request: Request) -> JSONResponse:
        outcome = await executor.run(request_id_of(request), "home", FEATURED_PRODUCTS_SQL)
        return outcome_response(outcome)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/comments")
    async def list_comments(request: Request, product_id: str) -> JSONResponse:
        outcome = await executor.run(
            request_id_of(request), "comments", COMMENTS_SQL, (parse_identifier(product_id),)
        )
        return outcome_response(outcome)

    @app.get("/cart")
    async def list_cart(request: Request) -> JSONResponse:
        outcome = await executor.run(request_id_of(request), "cart", CART_SQL, (CART_OWNER_ID,))
        return outcome_response(outcome)


def create_app(runner: QueryRunner | None = None, recorder: QueryRecorder | None = None) -> FastAPI:
    executor = QueryExecutor(runner or PostgresRunner(), recorder or OracleLog())
    app = FastAPI(title="vulnapp", docs_url=None, redoc_url=None)
    register_benign_endpoints(app, executor)
    for spec in ENDPOINTS:
        register_vulnerable_endpoint(app, spec, executor)
    return app
