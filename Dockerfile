FROM python:3.12-slim-bookworm

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
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

# Create non-root user
RUN useradd -m appuser && \
    mkdir -p /app/.flask_session /app/logs && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

# Use gunicorn for production
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
