FROM cgr.dev/chainguard/python:latest-dev

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY extapi_core.py extapi_http.py extension_api.json ./

ENV EXTAPI_JSON=/app/extension_api.json \
    HOST=0.0.0.0 \
    PORT=3737

EXPOSE 3737

CMD ["python", "-m", "uvicorn", "extapi_http:app", "--host", "0.0.0.0", "--port", "3737"]
