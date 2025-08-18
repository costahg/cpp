# syntax=docker/dockerfile:1.7
FROM cgr.dev/chainguard/python:latest

WORKDIR /app

# Configuração padrão
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EXTAPI_JSON=/app/extension_api.json \
    HOST=0.0.0.0 \
    PORT=3737

# Dependências
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --user -r requirements.txt

# Código e dados
# (COPY --chmod precisa de BuildKit; o Coolify já usa BuildKit por padrão)
COPY --chmod=0644 extapi_core.py extapi_http.py extension_api.json ./

EXPOSE 3737

# Healthcheck usando python -c (nada de heredoc no Dockerfile)
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request; u=f'http://127.0.0.1:{os.environ.get(\"PORT\",\"3737\")}/health'; urllib.request.urlopen(u, timeout=2).read();" || exit 1

# Rode uvicorn pelo módulo para evitar problemas de PATH (~/.local/bin)
CMD ["python", "-m", "uvicorn", "extapi_http:app", "--host", "0.0.0.0", "--port", "3737"]
