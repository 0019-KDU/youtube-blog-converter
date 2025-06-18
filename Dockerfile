# Stage 1: Build stage using Alpine
FROM python:3.12-alpine as builder

# Install build dependencies
RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Build wheels to optimize final installation
RUN pip install --no-cache-dir wheel \
    && pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt


# Stage 2: Final lightweight image
FROM python:3.12-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Copy pre-built wheels from builder
COPY --from=builder /wheels /wheels

# Install application dependencies from wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Copy application files
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]