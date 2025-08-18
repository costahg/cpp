FROM cgr.dev/chainguard/python:3.11

WORKDIR /app

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

# Chainguard já usa usuário não-root por padrão
CMD ["uvicorn", "extapi_http:app", "--host", "0.0.0.0", "--port", "3737"]
