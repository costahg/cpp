#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
import extapi_core

# --- Config ---------------------------------------------------------------

EXTAPI_JSON = Path(os.getenv("EXTAPI_JSON", "extension_api.json")).resolve()
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "https://cpp.lizapeproprio.shop").split(",")
    if o.strip()
]
API_KEY = os.getenv("EXTAPI_KEY", "")
VALID_CONFIGS = {
    c.strip()
    for c in os.getenv("EXTAPI_CONFIGS", "float_32,float_64").split(",")
    if c.strip()
}

OPEN_DOCS = os.getenv("OPEN_DOCS", "0") == "1"
DOCS_URL = "/docs" if OPEN_DOCS else None
REDOC_URL = "/redoc" if OPEN_DOCS else None
OPENAPI_URL = "/openapi.json" if OPEN_DOCS else None

OPEN_PATHS = {"/health"}
# Se quiser docs públicos sem chave, inclua DOCS_PUBLIC=1
DOCS_PUBLIC = os.getenv("DOCS_PUBLIC", "0") == "1"
if OPEN_DOCS and DOCS_PUBLIC:
    OPEN_PATHS.update({p for p in [DOCS_URL, REDOC_URL, OPENAPI_URL] if p})

# --- App ------------------------------------------------------------------

app = FastAPI(
    title="extapi_http",
    version="1.1.0",
    docs_url=DOCS_URL,
    redoc_url=REDOC_URL,
    openapi_url=OPENAPI_URL,
)

# wildcard "*" não deve combinar com credentials=True
allow_credentials = True
if any(o == "*" for o in ALLOWED_ORIGINS):
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["authorization", "x-api-key", "content-type", "accept", "origin"],
)

# --- Estado ---------------------------------------------------------------

class _ApiState:
    def __init__(self, p: Path):
        self.p = p
        self._mtime = 0.0
        self._ext: Optional[extapi_core.ExtApi] = None
        self._load()

    def _load(self):
        if not self.p.exists():
            raise FileNotFoundError(f"extension_api.json não encontrado em {self.p}")
        self._ext = extapi_core.ExtApi(self.p)
        self._mtime = self.p.stat().st_mtime

    def maybe_reload(self):
        m = self.p.stat().st_mtime
        if m > self._mtime:
            self._load()

    @property
    def ext(self) -> extapi_core.ExtApi:
        if self._ext is None:
            self._load()
        return self._ext  # type: ignore

    @property
    def mtime(self) -> float:
        return self._mtime

state = _ApiState(EXTAPI_JSON)

# --- Auth middleware ------------------------------------------------------

@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    # Preflight/HEAD passam sem chave
    if request.method in ("OPTIONS", "HEAD"):
        return await call_next(request)

    if not API_KEY:
        return await call_next(request)

    if request.url.path in OPEN_PATHS:
        return await call_next(request)

    incoming = request.headers.get("x-api-key")
    if incoming is None:
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            incoming = auth[7:]

    incoming = (incoming or "").strip()
    expected = (API_KEY or "").strip()

    if not incoming or incoming != expected:
        return JSONResponse(
            status_code=401,
            headers={"WWW-Authenticate": "Bearer, X-Api-Key"},
            content={"detail": "invalid or missing API key"},
        )

    return await call_next(request)

# --- Utils ----------------------------------------------------------------

def _validate_config_or_400(config: Optional[str]) -> None:
    if config and VALID_CONFIGS and config not in VALID_CONFIGS:
        valid = ", ".join(sorted(VALID_CONFIGS))
        raise HTTPException(status_code=400, detail=f"config inválida, use uma destas, {valid}")

# --- Rotas ----------------------------------------------------------------

@app.get("/health")
def health():
    state.maybe_reload()
    info = state.ext.info()
    return {
        "status": "ok",
        "counts": info,
        "port": int(os.getenv("PORT", "3737")),
        "allowed_origins": ALLOWED_ORIGINS,
        "json_mtime": state.mtime,
        "open_docs": OPEN_DOCS,
        "docs_public": DOCS_PUBLIC,
        "allow_credentials": allow_credentials,
    }

@app.get("/info")
def get_info():
    state.maybe_reload()
    return state.ext.info()

@app.get("/class/{name}")
def get_class(name: str):
    state.maybe_reload()
    c = state.ext.get_class(name)
    if not c:
        raise HTTPException(status_code=404, detail="classe não encontrada")
    return c

@app.get("/class/{name}/items")
def get_class_items(name: str):
    state.maybe_reload()
    c = state.ext.list_class_items(name)
    if not c:
        raise HTTPException(status_code=404, detail="classe não encontrada")
    return c

@app.get("/methods/by-name")
def methods_by_name(name: str, cls: Optional[str] = None):
    state.maybe_reload()
    return state.ext.find_methods(name, cls=cls)

@app.get("/methods/by-hash")
def methods_by_hash(hash: str = Query(..., description="hash do método, decimal ou string")):
    state.maybe_reload()
    return state.ext.find_method_by_hash(hash)

@app.get("/enum/global/{name}")
def enum_global(name: str):
    state.maybe_reload()
    e = state.ext.get_global_enum(name)
    if not e:
        raise HTTPException(status_code=404, detail="enum global não encontrado")
    return e

@app.get("/enum/class/{qualified}")
def enum_class(qualified: str):
    state.maybe_reload()
    e = state.ext.get_class_enum(qualified)
    if not e:
        raise HTTPException(status_code=404, detail="enum de classe não encontrado")
    return e

@app.get("/singletons")
def singletons():
    state.maybe_reload()
    return state.ext.list_singletons()

@app.get("/utility")
def utility(name: Optional[str] = None, category: Optional[str] = None):
    state.maybe_reload()
    return state.ext.find_utility(name=name, category=category)

@app.get("/builtin/names")
def builtin_names():
    state.maybe_reload()
    return state.ext.list_builtin_names()

@app.get("/builtin/{name}")
def builtin_detail(name: str):
    state.maybe_reload()
    b = state.ext.get_builtin(name)
    if not b:
        raise HTTPException(status_code=404, detail="builtin não encontrado")
    return b

@app.get("/builtin/{name}/layout")
def builtin_layout(name: str, config: str = "float_32"):
    state.maybe_reload()
    _validate_config_or_400(config)
    lay = state.ext.get_builtin_layout(name, config=config)
    if not lay:
        raise HTTPException(status_code=404, detail="layout não encontrado para este builtin/config")
    return lay

@app.get("/builtin/{name}/offset/{member}")
def builtin_offset(name: str, member: str, config: str = "float_32"):
    state.maybe_reload()
    _validate_config_or_400(config)
    off = state.ext.get_builtin_member_offset(name, member, config=config)
    if off is None:
        raise HTTPException(status_code=404, detail="offset não encontrado")
    return {"offset": off}

@app.get("/native_structs")
def native_structs():
    state.maybe_reload()
    return state.ext.list_native_structs()

@app.get("/native_structs/{name}")
def native_struct_detail(name: str):
    state.maybe_reload()
    ns = state.ext.get_native_struct(name)
    if not ns:
        raise HTTPException(status_code=404, detail="native struct não encontrada")
    return ns

# --- Novo: Mapa do blob canônico e leitura por range ----------------------

@app.get("/blob/map")
def blob_map(max_items_per_section: int = Query(200, ge=0, le=10000)):
    state.maybe_reload()
    return state.ext.get_blob_map(max_items_per_section=max_items_per_section)

@app.get("/blob/range", response_class=PlainTextResponse)
def blob_range(start: int = Query(..., ge=0), end: int = Query(..., ge=0)):
    state.maybe_reload()
    if end <= start:
        raise HTTPException(status_code=400, detail="end deve ser maior que start")
    text = state.ext.get_blob_range(start, end)
    if text == "":
        raise HTTPException(status_code=416, detail="range inválido")
    return text

# --- Main -----------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "extapi_http:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "3737")),
        reload=False,
    )
