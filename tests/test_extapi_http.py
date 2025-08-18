# -*- coding: utf-8 -*-
import os
import sys
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
EXTAPI_JSON_DEFAULT = os.environ.get("EXTAPI_JSON") or str(ROOT / "extension_api.json")

def reload_app(monkeypatch, **env):
    monkeypatch.setenv("EXTAPI_KEY", env.get("EXTAPI_KEY", "sekret"))
    monkeypatch.setenv("EXTAPI_JSON", env.get("EXTAPI_JSON", EXTAPI_JSON_DEFAULT))
    monkeypatch.setenv("ALLOWED_ORIGINS", env.get("ALLOWED_ORIGINS", "https://cpp.lizapeproprio.shop"))
    monkeypatch.setenv("EXTAPI_CONFIGS", env.get("EXTAPI_CONFIGS", "float_32,float_64"))
    monkeypatch.setenv("OPEN_DOCS", env.get("OPEN_DOCS", "0"))
    if "extapi_http" in sys.modules:
        del sys.modules["extapi_http"]
    import extapi_http
    importlib.reload(extapi_http)
    return extapi_http

pytestmark = pytest.mark.skipif(not Path(EXTAPI_JSON_DEFAULT).exists(), reason="extension_api.json não encontrado")

def test_health_sem_chave(monkeypatch):
    mod = reload_app(monkeypatch, ALLOWED_ORIGINS="*")
    with TestClient(mod.app) as c:
        r = c.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert isinstance(body["json_mtime"], (int, float))
        assert body["allow_credentials"] is False

def test_info_requer_api_key(monkeypatch):
    mod = reload_app(monkeypatch)
    with TestClient(mod.app) as c:
        r = c.get("/info")
        assert r.status_code == 401
        r2 = c.get("/info", headers={"x-api-key": "sekret"})
        assert r2.status_code == 200

def test_bearer_token_funciona(monkeypatch):
    mod = reload_app(monkeypatch)
    with TestClient(mod.app) as c:
        r = c.get("/singletons", headers={"Authorization": "Bearer sekret"})
        assert r.status_code == 200

def test_config_invalida_retorna_400(monkeypatch):
    mod = reload_app(monkeypatch)
    with TestClient(mod.app) as c:
        r = c.get("/builtin/Color/layout", params={"config": "banana"})
        assert r.status_code == 401
        r2 = c.get("/builtin/Color/layout", params={"config": "banana"}, headers={"x-api-key": "sekret"})
        assert r2.status_code == 400
        assert "config inválida" in r2.json()["detail"]

def test_cors_wildcard_nao_manda_credentials(monkeypatch):
    mod = reload_app(monkeypatch, ALLOWED_ORIGINS="*")
    with TestClient(mod.app) as c:
        r = c.options(
            "/info",
            headers={"Origin": "http://example.com", "Access-Control-Request-Method": "GET"},
        )
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-credentials") != "true"

def test_cors_com_origem_especifica_manda_credentials(monkeypatch):
    mod = reload_app(monkeypatch, ALLOWED_ORIGINS="https://cpp.lizapeproprio.shop")
    with TestClient(mod.app) as c:
        r = c.options(
            "/info",
            headers={"Origin": "https://cpp.lizapeproprio.shop", "Access-Control-Request-Method": "GET"},
        )
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-credentials") == "true"

def test_open_docs_paths_sem_chave_quando_open_docs(monkeypatch):
    mod = reload_app(monkeypatch, OPEN_DOCS="1")
    with TestClient(mod.app) as c:
        assert c.get("/openapi.json").status_code == 200
        assert c.get("/docs").status_code in (200, 307)
        assert c.get("/redoc").status_code in (200, 307)

def test_docs_bloqueadas_quando_open_docs_zero(monkeypatch):
    mod = reload_app(monkeypatch, OPEN_DOCS="0")
    with TestClient(mod.app) as c:
        assert c.get("/openapi.json").status_code == 401
        assert c.get("/docs").status_code == 401
