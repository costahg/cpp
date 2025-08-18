FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código e dados
COPY extapi_core.py extapi_http.py extension_api.json ./

# Usuário não-root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Config do serviço
ENV EXTAPI_JSON=/app/extension_api.json \
    HOST=0.0.0.0 \
    PORT=3737

EXPOSE 3737

CMD ["uvicorn", "extapi_http:app", "--host", "0.0.0.0", "--port", "3737"]
