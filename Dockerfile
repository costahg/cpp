FROM cgr.dev/chainguard/python:latest-dev

WORKDIR /app

# Ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EXTAPI_JSON=/app/extension_api.json \
    HOST=0.0.0.0 \
    PORT=3737 \
    PATH="/home/nonroot/.local/bin:${PATH}"

# Dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código e dados
COPY extapi_core.py extapi_http.py extension_api.json ./
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 3737

# ENTRYPOINT manda mais que CMD/command do Coolify
ENTRYPOINT ["/bin/sh", "/app/start.sh"]
