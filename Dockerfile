FROM cgr.dev/chainguard/python:latest-dev

WORKDIR /app

# Qualidade de vida + garantir que os binários de user install entrem no PATH
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/nonroot/.local/bin:${PATH}" \
    EXTAPI_JSON=/app/extension_api.json \
    HOST=0.0.0.0 \
    PORT=3737

# Dependências
COPY requirements.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt

# Código e dados
COPY extapi_core.py extapi_http.py extension_api.json ./

EXPOSE 3737

# Corrige o problema do ENTRYPOINT padrão: chamamos uvicorn via módulo do Python
ENTRYPOINT ["python","-m","uvicorn"]
CMD ["extapi_http:app","--host","0.0.0.0","--port","3737","--log-level","info"]
