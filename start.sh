#!/bin/sh
set -eu

# Garante que os scripts do pip (uvicorn, etc.) estão no PATH
export PATH="/home/nonroot/.local/bin:${PATH}"

# Defaults
: "${HOST:=0.0.0.0}"
: "${PORT:=3737}"
: "${EXTAPI_JSON:=/app/extension_api.json}"

# Log rápido para debug
echo "[start.sh] Using HOST=$HOST PORT=$PORT EXTAPI_JSON=$EXTAPI_JSON"
echo "[start.sh] Python: $(python --version)"
echo "[start.sh] Which uvicorn: $(command -v uvicorn || true)"

# Sobe o servidor de forma à prova de override
exec python -m uvicorn extapi_http:app --host "$HOST" --port "$PORT"
