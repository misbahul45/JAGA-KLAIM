# syntax=docker/dockerfile:1

FROM python:3.13-slim-bookworm AS base
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
RUN useradd --create-home --uid 1000 app
WORKDIR /app

FROM base AS deps-prod
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    UV_COMPILE_BYTECODE=1 uv sync --frozen --no-install-project --no-dev

FROM base AS dev
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["fastapi", "dev", "main.py", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.13-slim-bookworm AS runner
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"
RUN useradd --create-home --uid 1000 app
WORKDIR /app
COPY --from=deps-prod /opt/venv /opt/venv
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
