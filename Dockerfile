# Dockerfile 
# Multi-stage build to create a secure, lightweight, and efficient production image.

# ---- Stage 1: Builder ----
FROM python:3.11-slim-bookworm AS builder

ENV UV_VERSION=0.1.41
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/root/.local/bin:$VIRTUAL_ENV/bin:$PATH"

# Install uv
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
RUN uv venv $VIRTUAL_ENV

# Copy requirements and install dependencies
COPY requirements.txt requirements.txt
# Ensure 'playwright' is REMOVED from requirements.txt
RUN uv pip install --no-cache-dir -r requirements.txt


# ---- Stage 2: Final Production Image ----
FROM python:3.11-slim-bookworm AS final

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:/usr/local/bin:$PATH"

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV

# Copy the application source code
COPY . .

# Create and switch to a non-root user for security
RUN useradd --system --create-home --uid 1000 app_user
RUN chown -R app_user:app_user /app
USER app_user

# Default command
CMD ["python", "-m", "uvicorn", "crawler.api.main:app", "--host", "0.0.0.0", "--port", "8000"]