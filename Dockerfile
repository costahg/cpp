FROM cgr.dev/chainguard/python:latest-dev

WORKDIR /app

# Garantir que scripts do pip (uvicorn) estejam no PATH e Python sem cache
ENV PATH="/home/nonroot/.local/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EXTAPI_JSON=/app/extension_api.json \
    HOST=0.0.0.0 \
    PORT=3737

# Dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código e dados
COPY extapi_core.py extapi_http.py extension_api.json ./

EXPOSE 3737

# Sobe o servidor (robusto mesmo se Coolify não herdar PATH)
CMD ["python", "-m", "uvicorn", "extapi_http:app", "--host", "0.0.0.0", "--port", "3737"]
