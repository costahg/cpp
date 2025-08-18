FROM cgr.dev/chainguard/python:latest-dev

WORKDIR /app

# Dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --user

# Código e dados
COPY extapi_core.py extapi_http.py extension_api.json ./

# Config
ENV EXTAPI_JSON=/app/extension_api.json

EXPOSE 3737

# Importante: SEM ENTRYPOINT. Apenas CMD com "python -m uvicorn".
CMD ["/usr/bin/python", "-m", "uvicorn", "extapi_http:app", "--host", "0.0.0.0", "--port", "3737"]
