FROM ghcr.io/astral-sh/uv:0.11.21 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY aegis ./aegis
COPY apps/__init__.py ./apps/__init__.py
COPY apps/api ./apps/api
COPY apps/worker ./apps/worker
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts ./scripts
RUN uv sync --frozen --no-dev --no-editable && useradd --uid 10001 --create-home aegis && mkdir -p /var/log/aegis && chown aegis:aegis /var/log/aegis
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER aegis
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
