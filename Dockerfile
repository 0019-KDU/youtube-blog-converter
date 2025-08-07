FROM python:3.12-slim-bookworm

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copy application code
COPY app.py .
COPY src/ ./src/
COPY auth/ ./auth/
COPY templates/ ./templates/
COPY static/ ./static/

# Ensure Python can find modules
RUN touch auth/__init__.py src/__init__.py

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

# Environment variables for logging
ENV LOG_LEVEL=INFO
ENV LOG_TO_FILE=true
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
