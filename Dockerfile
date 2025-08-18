FROM cgr.dev/chainguard/python:latest

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código e dados
COPY extapi_core.py extapi_http.py extension_api.json ./

# Config do serviço
ENV EXTAPI_JSON=/app/extension_api.json \
    HOST=0.0.0.0 \
    PORT=3737

EXPOSE 3737

# Importante: chama o uvicorn via módulo do Python (evita PATH de binários)
CMD ["python", "-m", "uvicorn", "extapi_http:app", "--host", "0.0.0.0", "--port", "3737"]
