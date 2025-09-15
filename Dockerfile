# ==================== BASE STAGE ====================
FROM python:3.11-slim-bookworm AS base

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip for better caching
RUN pip install --no-cache-dir --upgrade pip

# ==================== DEPENDENCIES STAGE ====================
FROM base AS dependencies

# Copy and install Python dependencies (optimized caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# ==================== PRODUCTION STAGE ====================
FROM python:3.11-slim-bookworm AS production

WORKDIR /app

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/
COPY run.py .

# Create directories for logs with proper permissions
RUN mkdir -p /var/log/flask-app /app/.flask_session /app/logs && \
    chmod 755 /var/log/flask-app /app/.flask_session /app/logs

# Create non-root user and set ownership
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /var/log/flask-app

# Switch to non-root user
USER appuser

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port
EXPOSE 5000 8000

# Environment variables
ENV LOG_LEVEL=INFO
ENV LOG_TO_FILE=true
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_ENV=production

# Use gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--keep-alive", "2", "--max-requests", "1000", "--access-logfile", "-", "--error-logfile", "-", "run:create_application()"]
