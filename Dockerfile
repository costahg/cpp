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

# Healthcheck usando o próprio Python da imagem (sem curl/wget)
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python","-c","import os,sys,urllib.request,json; u=f'http://127.0.0.1:{os.environ.get(\"PORT\",\"3737\")}/health'; sys.exit(0 if json.loads(urllib.request.urlopen(u,timeout=2).read()).get('status')=='ok' else 1)"]

# Corrige o problema do ENTRYPOINT padrão: chamamos uvicorn via módulo do Python
ENTRYPOINT ["python","-m","uvicorn"]
CMD ["extapi_http:app","--host","0.0.0.0","--port","3737","--log-level","info"]
