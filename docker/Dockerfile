# MikroTik Mass Updater - Multi-stage Docker Build

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build

WORKDIR /build

# Copy package files
COPY frontend/package*.json ./frontend/

# Install dependencies
WORKDIR /build/frontend
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Create output directory and build
RUN mkdir -p /build/backend/static && npm run build

# Stage 2: Backend + Frontend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    iputils-ping \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy frontend build from stage 1
COPY --from=frontend-build /build/backend/static ./backend/static/

# Create data directory
RUN mkdir -p /app/data

# Volume for persistent data
VOLUME ["/app/data"]

# Expose port
EXPOSE 8000

# Environment variables
ENV DATABASE_URL=sqlite:///./data/mikrotik.db
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
