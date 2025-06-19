# syntax=docker/dockerfile:1.3
##################################
### Stage 1: Build wheels ###
##################################
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libssl-dev \
      pkg-config \
      cargo && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

# Build wheels with retries
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

##################################
### Stage 2: Optimized runtime image ###
##################################
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install only essential runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libgomp1 && \
    # Clean up aggressively
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY --from=builder /wheels /wheels
COPY requirements.txt ./

# Install from wheels and clean up
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels && \
    # Reduce Python package size
    find /usr/local/lib/python3.12 -depth \
        \( -type d -name __pycache__ -o -name '*.pyc' \) -exec rm -rf '{}' + && \
    rm -rf /root/.cache

# Copy only necessary application files
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]