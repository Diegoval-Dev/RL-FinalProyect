FROM python:3.11-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
WORKDIR /workspace
COPY pyproject.toml uv.lock .python-version ./

FROM base AS vulnapp
RUN uv sync --frozen --no-dev --no-install-project
COPY lab/vulnapp/vulnapp /app/vulnapp
ENV PYTHONPATH=/app
WORKDIR /app
CMD ["uvicorn", "vulnapp.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS runner
RUN uv sync --frozen --no-install-project
ENV PYTHONPATH=/workspace:/workspace/lab/vulnapp
CMD ["sleep", "infinity"]

FROM base AS honeypot
RUN uv sync --frozen --no-dev --no-install-project
COPY lab/honeypot/honeypot /app/honeypot
ENV PYTHONPATH=/app
WORKDIR /app
CMD ["uvicorn", "honeypot.app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS proxy
RUN uv sync --frozen --no-dev --no-install-project
COPY wafarena /app/wafarena
COPY lab/proxy/proxy /app/proxy
ENV PYTHONPATH=/app
WORKDIR /app
CMD ["uvicorn", "proxy.entrypoint:app", "--host", "0.0.0.0", "--port", "8000"]
