.PHONY: check check-backend check-web check-integration check-e2e audit schemas core full
check: check-backend check-web
check-backend:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy
	uv run pytest -q
	uv run python scripts/scan_secrets.py
	uv run python scripts/export_schemas.py --check
check-web:
	pnpm web:api:check
	pnpm web:test
	pnpm web:lint
	pnpm web:typecheck
	NEXT_TELEMETRY_DISABLED=1 pnpm web:build
check-integration:
	AEGIS_RUN_INTEGRATION=1 uv run pytest -q tests/integration
	uv run python scripts/verify_migrations.py
check-e2e:
	AEGIS_RUN_E2E=1 uv run pytest -q tests/e2e
audit:
	uv export --frozen --no-dev --no-emit-project --format requirements-txt --output-file /tmp/aegisnews-audit-requirements.txt --quiet
	uv run pip-audit --disable-pip --no-deps -r /tmp/aegisnews-audit-requirements.txt
	pnpm audit --prod
schemas:
	uv run python scripts/export_schemas.py
core:
	docker compose --profile core up --build -d --wait
full:
	AEGIS_TEMPORAL_ENABLED=true AEGIS_OTEL_ENABLED=true docker compose --profile full up --build -d --wait

.PHONY: demo-start demo-reset demo-seed demo-security demo-benchmark demo-reliability demo-observe evaluate
demo-start:
	python3 scripts/demo.py start
demo-reset:
	python3 scripts/demo.py reset
demo-seed:
	python3 scripts/demo.py seed
demo-security:
	python3 scripts/demo.py security
demo-benchmark:
	python3 scripts/demo.py benchmark
demo-reliability:
	python3 scripts/demo.py reliability
demo-observe:
	python3 -m scripts.demo_observability
evaluate:
	uv run python -m aegis.intelligence.assessment --profile offline --output ml/evaluation/results/offline.json
