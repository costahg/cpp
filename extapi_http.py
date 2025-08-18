#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extapi_http.py — API HTTP mínima/robusta para servir o extension_api.json via extapi_core

Objetivo:
- Servir endpoints REST (GET/POST) para o Custom Actions e para testes manuais.
- Auto-reload leve: se o arquivo EXTAPI_JSON mudar no disco, recarrega antes de responder.
- Zero dependências externas além de FastAPI/Uvicorn (instale com `pip install fastapi uvicorn`).

Rotas principais (todas retornam JSON):
- GET  /health
- GET  /info
- GET  /class/{name}
- GET  /class/{name}/items
- GET  /methods/by-name?name=add_child&cls=Node
- GET  /methods/by-hash?hash=3863233950
- GET  /enum/global/{name}
- GET  /enum/class/{qualified}   (ex.: Node.ProcessMode)
- GET  /singletons
- GET  /utility                   (lista todas)
- GET  /utility?name=foo         (detalhe por nome)
- GET  /utility?category=Math    (lista por categoria)
- GET  /builtin/names
- GET  /builtin/{name}
- GET  /builtin/{name}/layout?config=float_32
- GET  /builtin/{name}/offset/{member}?config=float_32
- GET  /native_structs
- GET  /global_constants/names
- GET  /global_constants/{name}
- POST /route  body: {"q": "classe Node"}

Observação:
- Em produção/CA, prefira as rotas específicas (mais determinísticas) a depender de /route.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import extapi_core

# ---------------------------
# Estado e auto-reload leve
# ---------------------------
class _ApiState:
    def __init__(self, json_path: Path):
        self.json_path = json_path
        self._ext: Optional[extapi_core.ExtApi] = None
        self._mtime: float = 0.0
        self._load()

    def _load(self) -> None:
        if not self.json_path.exists():
            raise FileNotFoundError(f"extension_api.json não encontrado em: {self.json_path}")
        self._ext = extapi_core.ExtApi(self.json_path)
        self._mtime = self.json_path.stat().st_mtime

    def maybe_reload(self) -> None:
        try:
            mtime = self.json_path.stat().st_mtime
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="EXTAPI_JSON não encontrado no disco")
        if mtime > self._mtime:
            # arquivo mudou — recarrega
            self._load()

    @property
    def ext(self) -> extapi_core.ExtApi:
        if self._ext is None:
            self._load()
        return self._ext  # type: ignore[return-value]

    @property
    def mtime(self) -> float:
        return self._mtime


EXTAPI_JSON = Path(os.getenv("EXTAPI_JSON", "extension_api.json")).resolve()
state = _ApiState(EXTAPI_JSON)

app = FastAPI(title="extapi_http", version="1.0.0", description="HTTP wrapper para extapi_core")

# CORS liberado (útil p/ CA, testes ou painéis)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------
# Schemas leves
# -------------
class RouteQuery(BaseModel):
    q: str


# ------
# Rotas
# ------
@app.get("/health")
def health():
    state.maybe_reload()
    info = state.ext.info()
    return {
        "status": "ok",
        "core_version": info.get("version"),
        "counts": info,
        "json_path": str(state.json_path),
        "json_mtime": state.mtime,
        "host": os.getenv("HOST", "0.0.0.0"),
        "port": int(os.getenv("PORT", "8000")),
        "ts": time.time(),
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
def methods_by_name(name: str = Query(..., description="nome do método"), cls: Optional[str] = Query(None, description="nome da classe (opcional)")):
    state.maybe_reload()
    out = state.ext.find_methods(name, cls=cls)
    return out

@app.get("/methods/by-hash")
def methods_by_hash(hash: str = Query(..., description="hash do método")):
    state.maybe_reload()
    out = state.ext.find_method_by_hash(hash)
    return out

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
def builtin_layout(name: str, config: str = Query("float_32")):
    state.maybe_reload()
    lay = state.ext.get_builtin_layout(name, config=config)
    if not lay:
        raise HTTPException(status_code=404, detail="layout não encontrado para este builtin/config")
    return lay

@app.get("/builtin/{name}/offset/{member}")
def builtin_offset(name: str, member: str, config: str = Query("float_32")):
    state.maybe_reload()
    off = state.ext.get_builtin_member_offset(name, member, config=config)
    if off is None:
        raise HTTPException(status_code=404, detail="offset não encontrado")
    return {"offset": off}

@app.get("/native_structs")
def native_structs():
    state.maybe_reload()
    return state.ext.list_native_structs()

@app.get("/global_constants/names")
def global_constants_names():
    state.maybe_reload()
    return state.ext.list_global_constants()

@app.get("/global_constants/{name}")
def global_constant(name: str):
    state.maybe_reload()
    gc = state.ext.get_global_constant(name)
    if not gc:
        raise HTTPException(status_code=404, detail="constante global não encontrada")
    return gc

@app.post("/route")
def route(q: RouteQuery):
    state.maybe_reload()
    return state.ext.route(q.q)
