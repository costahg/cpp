# syntax=docker/dockerfile:1
FROM python:3.11-slim

# System settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY extapi_core.py extapi_http.py extension_api.json ./

# Run as non-root
RUN useradd -m appuser
USER appuser

# Service envs
ENV EXTAPI_JSON=/app/extension_api.json \
    HOST=0.0.0.0 \
    PORT=3737

EXPOSE 3737

# Start server
CMD ["uvicorn", "extapi_http:app", "--host", "0.0.0.0", "--port", "3737"]
