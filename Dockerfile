# Dockerfile
FROM cgr.dev/chainguard/python:latest-dev

# Ambiente “clean”
ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Cria venv e põe no PATH (conforme guia da Chainguard)
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:${PATH}"

# Dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código + dados
COPY extapi_core.py extapi_http.py extension_api.json ./

# Config do serviço
ENV EXTAPI_JSON=/app/extension_api.json \
    HOST=0.0.0.0 \
    PORT=3737

EXPOSE 3737

# Healthcheck sem curl/wget (usa só a stdlib do Python)
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python - <<'PY' || exit 1
import os, sys, urllib.request
u = f"http://127.0.0.1:{os.environ.get('PORT','3737')}/health"
try:
    with urllib.request.urlopen(u, timeout=2) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
PY

# **Ponto crítico**: sobrescreve o ENTRYPOINT da imagem base.
# Assim, não acontece mais "python uvicorn" acidental.
ENTRYPOINT ["python","-m","uvicorn","extapi_http:app","--host","0.0.0.0","--port","3737"]
