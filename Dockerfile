FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# curl backs the container healthcheck, libatomic1 lets playwright's bundled
# Node run before it installs Chromium's remaining shared libraries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Headless Chromium plus every system library it needs.
# Build with --build-arg INSTALL_BROWSER=false for a much smaller image that
# only uses the HTTPX engine (needed on 512 MB free instances).
ARG INSTALL_BROWSER=true
RUN if [ "$INSTALL_BROWSER" = "true" ]; then \
        playwright install --with-deps chromium; \
    else \
        echo "Skipping Chromium — browser engine will be unavailable"; \
    fi

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT:-8000}/api/ready || exit 1

# The serve command honours $PORT (Railway, Render, Fly) and falls back to 8000.
CMD ["python", "-m", "scraper.cli", "serve", "--host", "0.0.0.0"]
