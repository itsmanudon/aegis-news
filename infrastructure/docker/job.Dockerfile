# The daily news job: the API image's code plus a pinned Temporal CLI, which the job
# starts as a throwaway in-memory development server. Same version as compose.yaml.
FROM temporalio/temporal:1.4.1 AS temporal
FROM ghcr.io/astral-sh/uv:0.11.21 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /uvx /bin/
COPY --from=temporal /usr/local/bin/temporal /usr/local/bin/temporal
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY aegis ./aegis
COPY apps/__init__.py ./apps/__init__.py
COPY apps/api ./apps/api
COPY apps/worker ./apps/worker
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts ./scripts
RUN uv sync --frozen --no-dev --no-editable && useradd --uid 10001 --create-home aegis
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER aegis
CMD ["python", "-m", "aegis.jobs.daily"]
