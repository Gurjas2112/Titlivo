"""Titlivo API: REST + SSE + MCP, all on one service layer (spec §10)."""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastmcp.utilities.lifespan import combine_lifespans
from pydantic import BaseModel, Field
from scalar_fastapi import get_scalar_api_reference
from sse_starlette.sse import EventSourceResponse

from titlivo import __version__
from titlivo.auth import Caller, get_caller
from titlivo.constants import coverage_header
from titlivo.db import pool as db
from titlivo.mcp_server import MCPAuth, mcp
from titlivo.services import ask as ask_service
from titlivo.services import did, glossary, monitor, parcels, passport, passport_verify, status_list
from titlivo.settings import get_settings

ERR = "https://titlivo.dev/errors/"
mcp_app = mcp.http_app(path="/")


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    monitor.broker.loop = asyncio.get_running_loop()
    yield
    db.close()


app = FastAPI(
    title="Titlivo API",
    version=__version__,
    summary="One canonical parcel API across Maharashtra, Karnataka and Gujarat, with Title Passports.",
    description=(
        "All data is **synthetic**. Facts come from deterministic SQL; red flags cite their source record. "
        "Anonymous callers see masked names; send `Authorization: Bearer <key>` with scope `parcels:pii` to see them. "
        "Errors follow RFC 9457 (`application/problem+json`). Every response carries an `X-Coverage` header."
    ),
    lifespan=combine_lifespans(app_lifespan, mcp_app.lifespan),
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_list,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Coverage", "ETag"],
)


@app.middleware("http")
async def coverage_middleware(request: Request, call_next: Any) -> Response:
    response = await call_next(request)
    response.headers["X-Coverage"] = coverage_header()
    return response


def problem(status: int, slug: str, title: str, detail: str | None = None) -> JSONResponse:
    return JSONResponse(
        {"type": ERR + slug, "title": title, "status": status, "detail": detail},
        status_code=status,
        media_type="application/problem+json",
    )


@app.exception_handler(parcels.NotFound)
async def not_found(_: Request, exc: parcels.NotFound) -> JSONResponse:
    return problem(404, "not-found", "Not found", f"No record with id {exc}")


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    slug = {401: "unauthorized", 403: "forbidden", 404: "not-found", 400: "bad-request"}.get(exc.status_code, "error")
    return problem(exc.status_code, slug, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return problem(422, "validation", "Invalid request", json.dumps(exc.errors(), default=str))


@app.exception_handler(ValueError)
async def value_error(_: Request, exc: ValueError) -> JSONResponse:
    return problem(400, "bad-request", "Bad request", str(exc))


def require_admin(caller: Caller = Depends(get_caller)) -> Caller:
    if not caller.is_admin:
        raise HTTPException(401, "Admin API key required")
    return caller


# ---------------- health & docs ----------------
@app.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/healthz/db", tags=["health"])
def healthz_db() -> dict[str, Any]:
    with db.pool().connection() as conn:
        n = conn.execute("select count(*) as n from titlivo.parcels").fetchone()["n"]
    return {"status": "ok", "parcels": n}


@app.get("/docs", include_in_schema=False)
def docs() -> Any:
    return get_scalar_api_reference(openapi_url=app.openapi_url, title="Titlivo API reference")


# ---------------- parcels ----------------
@app.get("/v1/parcels/search", tags=["parcels"])
def search(
    q: str = Query(..., min_length=1, description="Survey no, owner name (any script) or village"),
    limit: int = Query(20, le=50),
    caller: Caller = Depends(get_caller),
) -> dict[str, Any]:
    return {"query": q, "results": parcels.search(q, caller, limit)}


@app.get("/v1/parcels/{parcel_id}", tags=["parcels"])
def get_parcel(parcel_id: str, request: Request, response: Response, lang: str = "en", caller: Caller = Depends(get_caller)) -> Any:
    d = parcels.dossier(parcel_id, caller, lang)
    etag = f'"{parcel_id}-v{d["version"]}-{"pii" if caller.can_see_names else "masked"}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    response.headers["ETag"] = etag
    d["passports"] = passport.for_parcel(parcel_id)
    return d


@app.get("/v1/parcels/{parcel_id}/title-chain", tags=["parcels"])
def get_title_chain(parcel_id: str, since_year: int = 1900, caller: Caller = Depends(get_caller)) -> dict[str, Any]:
    return {"parcel_id": parcel_id, "events": parcels.title_chain(parcel_id, caller, since_year)}


@app.get("/v1/parcels/{parcel_id}/flags", tags=["parcels"])
def get_flags(parcel_id: str, lang: str = "en") -> dict[str, Any]:
    flags = parcels.get_flags(parcel_id, lang)
    return {"parcel_id": parcel_id, "flags": flags, "count": len(flags)}


@app.get("/v1/map", tags=["map"])
def map_layer(response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "public, max-age=30"
    return parcels.map_layer()


@app.get("/v1/coverage", tags=["reference"])
def coverage() -> dict[str, Any]:
    return parcels.coverage()


@app.get("/v1/glossary", tags=["reference"])
def get_glossary() -> dict[str, Any]:
    return {"terms": glossary.entries()}


# ---------------- Ask the Property ----------------
class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    parcel_id: str
    language: str = "en"


@app.post("/v1/ask", tags=["ask"])
def ask(body: AskIn, caller: Caller = Depends(get_caller)) -> dict[str, Any]:
    return ask_service.answer(body.question, body.parcel_id, body.language, caller)


# ---------------- Title Passports ----------------
@app.post("/v1/parcels/{parcel_id}/passports", tags=["passports"], status_code=201)
def issue_passport(parcel_id: str) -> dict[str, Any]:
    return passport.issue(parcel_id)


@app.get("/v1/passports/{passport_id}", tags=["passports"])
def get_passport(passport_id: str) -> dict[str, Any]:
    return passport.get(passport_id)


class VerifyIn(BaseModel):
    jwt: str = Field(min_length=10)


def _resolve(url: str) -> str:
    """Fetch a published document. The issuer's own documents are rendered in-process."""
    base = get_settings().public_api_base
    if url == did.did_web_url(did.issuer()):
        return json.dumps(did.document())
    if url.startswith(f"{base}/status/"):
        return status_list.credential_jwt(int(url.rsplit("/", 1)[1]))[0]
    return httpx.get(url, timeout=5).raise_for_status().text


@app.post("/v1/passports/verify", tags=["passports"])
def verify_passport(body: VerifyIn) -> dict[str, Any]:
    return passport_verify.verify(body.jwt, _resolve)


@app.get("/.well-known/did.json", tags=["passports"])
def did_document() -> JSONResponse:
    return JSONResponse(did.document(), media_type="application/did+json", headers={"Cache-Control": "public, max-age=300"})


@app.get("/status/{list_id}", tags=["passports"])
def status(list_id: int, request: Request) -> Response:
    try:
        token, etag = status_list.credential_jwt(list_id)
    except KeyError as e:
        raise parcels.NotFound(f"status list {list_id}") from e
    headers = {"ETag": f'"{etag}"', "Cache-Control": "public, max-age=60"}
    if request.headers.get("if-none-match") == f'"{etag}"':
        return Response(status_code=304, headers=headers)
    return Response(token, media_type="application/vc+jwt", headers=headers)


@app.get("/v/{passport_id}/events", tags=["passports"])
async def passport_events(passport_id: str) -> EventSourceResponse:
    q = monitor.broker.subscribe(passport_id)

    async def stream() -> AsyncIterator[dict[str, str]]:
        try:
            yield {"event": "hello", "data": json.dumps({"passport_id": passport_id})}
            while True:
                msg = await q.get()
                yield {"event": msg.get("event", "status"), "data": json.dumps(msg)}
        finally:
            monitor.broker.unsubscribe(passport_id, q)

    return EventSourceResponse(stream(), ping=15)


@app.get("/v1/parcels/{parcel_id}/events", tags=["parcels"])
async def parcel_events(parcel_id: str) -> EventSourceResponse:
    key = f"parcel:{parcel_id}"
    q = monitor.broker.subscribe(key)

    async def stream() -> AsyncIterator[dict[str, str]]:
        try:
            while True:
                msg = await q.get()
                yield {"event": "changed", "data": json.dumps(msg)}
        finally:
            monitor.broker.unsubscribe(key, q)

    return EventSourceResponse(stream(), ping=15)


# ---------------- admin (live-revocation demo) ----------------
class EventIn(BaseModel):
    parcel_id: str
    preset: str = Field(description="heir_impersonation | double_sale | new_mortgage | court_case")


@app.get("/v1/admin/presets", tags=["admin"])
def presets() -> dict[str, str]:
    return monitor.PRESETS


@app.post("/v1/admin/events", tags=["admin"])
def inject_event(body: EventIn, _: Caller = Depends(require_admin)) -> dict[str, Any]:
    return monitor.inject(body.parcel_id, body.preset)


class ResetIn(BaseModel):
    parcel_id: str


@app.post("/v1/admin/demo/reset", tags=["admin"])
def demo_reset(body: ResetIn, _: Caller = Depends(require_admin)) -> dict[str, Any]:
    return monitor.reset(body.parcel_id)


@app.get("/v1/demo/parcels", tags=["reference"])
def demo_parcels() -> dict[str, Any]:
    """Example parcel per flag, for tours, screenshots and the Postman collection."""
    with db.pool().connection() as conn:
        return {r["key"]: r["parcel_id"] for r in conn.execute("select key, parcel_id from titlivo.demo_parcels order by key")}


app.mount("/mcp", MCPAuth(mcp_app))
