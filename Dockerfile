# syntax=docker/dockerfile:1.3
##################################
### Stage 1: Build wheels ###
##################################
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Fix repository sources first!
RUN sed -i 's|http://.*.debian.org|http://deb.debian.org|g' /etc/apt/sources.list

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      chromium \
      chromium-driver \
      libxml2-dev \
      libxslt-dev \
      build-essential \
      libssl-dev \
      pkg-config \
      cargo \
      libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

# Build wheels with retries
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

##################################
### Stage 2: Optimized runtime ###
##################################
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Fix repository sources again
RUN sed -i 's|http://.*.debian.org|http://deb.debian.org|g' /etc/apt/sources.list

# Install only RUNTIME dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      chromium \
      chromium-driver \
      libgomp1 \
      libffi8 \
      ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY --from=builder /wheels /wheels
COPY requirements.txt ./

# Install from wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels && \
    find /usr/local/lib/python3.12 -depth \( -type d -name __pycache__ -o -name '*.pyc' \) -exec rm -rf '{}' + && \
    rm -rf /root/.cache

# Setup application
RUN mkdir -p /app/.flask_session /app/logs && \
    chmod 755 /app/.flask_session /app/logs

COPY . .

RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

# Important: Remove healthcheck during build
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#    CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

EXPOSE 5000 8000

CMD ["python", "app.py"]