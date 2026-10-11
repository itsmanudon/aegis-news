"""Pure helpers for the isolated local aegis-demo launcher.

These functions do not read secret values, contact Docker, or start services.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

SECRET_ALLOWLIST = (
    "AEGIS_NEWSDATA_API_KEY",
    "AEGIS_GNEWS_API_KEY",
    "AEGIS_NEWSAPI_API_KEY",
    "AEGIS_YOUTUBE_API_KEY",
)
PROVIDER_NAMES = {
    "AEGIS_NEWSDATA_API_KEY": "newsdata",
    "AEGIS_GNEWS_API_KEY": "gnews",
    "AEGIS_NEWSAPI_API_KEY": "newsapi",
    "AEGIS_YOUTUBE_API_KEY": "youtube",
}
ACQUIRE_PROVIDERS = frozenset({"newsdata", "gnews", "newsapi", "gdelt", "youtube"})
RESET_PHRASE = "reset aegis-demo"
START_STEPS = (
    "validate",
    "docker",
    "ports",
    "context",
    "configuration",
    "images",
    "services",
    "readiness",
    "seed",
    "verify",
    "summary",
)
ONE_SHOT_SERVICES = frozenset({"keys-init", "minio-init", "migrate"})
HEALTHY_SERVICES = frozenset({"postgres", "redis", "minio", "temporal", "api", "web"})
RUNNING_SERVICES = frozenset({"worker", "prometheus", "grafana", "loki", "alloy", "otel-collector"})
LOG_SERVICES = ONE_SHOT_SERVICES | HEALTHY_SERVICES | RUNNING_SERVICES
_REJECTED_NAME = re.compile(r"(^|[-_])(prod|production|staging|stage|stg|prd)($|[-_])", re.I)
_PREFERRED_NAME = re.compile(r"(^|[-_])(dev|development|demo|local)($|[-_])", re.I)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-+/=]{8,}")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_ASSIGNMENT = re.compile(
    r"(?i)\b(AEGIS_(?:NEWSDATA|GNEWS|NEWSAPI|YOUTUBE)_API_KEY)(\s*[:=]\s*)(\S+)"
)
DopplerStatus = Literal["selected", "unavailable", "unauthenticated", "ambiguous", "rejected"]


class DemoError(RuntimeError):
    def __init__(self, component: str, detail: str) -> None:
        self.component = component
        self.detail = detail
        super().__init__(f"{component}: {detail}")


@dataclass(frozen=True)
class DopplerSelection:
    status: DopplerStatus
    project: str | None = None
    config: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class PortAssessment:
    name: str
    port: int
    listening: bool
    owned_by_demo: bool

    @property
    def ok(self) -> bool:
        return (not self.listening) or self.owned_by_demo


def redact(text: str) -> str:
    text = _BEARER.sub("Bearer [redacted]", text)
    text = _JWT.sub("[redacted-jwt]", text)
    return _ASSIGNMENT.sub(r"\1\2[redacted]", text)


def python_supported(version: tuple[int, int]) -> bool:
    return version >= (3, 12)


def hidden_subprocess_kwargs() -> dict[str, Any]:
    if sys.platform != "win32":
        return {}
    flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if isinstance(flag, int) and flag:
        return {"creationflags": flag}
    return {}


def parse_env_file(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def demo_urls(ports: Mapping[str, int]) -> dict[str, str]:
    def port(key: str, default: int) -> int:
        return int(ports.get(key, default))

    web = port("AEGIS_WEB_PORT", 33000)
    api = port("AEGIS_API_PORT", 38000)
    return {
        "web": f"http://127.0.0.1:{web}",
        "api": f"http://127.0.0.1:{api}",
        "api_docs": f"http://127.0.0.1:{api}/docs",
        "temporal": f"http://127.0.0.1:{port('AEGIS_TEMPORAL_UI_PORT', 38233)}",
        "minio": f"http://127.0.0.1:{port('AEGIS_MINIO_CONSOLE_PORT', 39001)}",
        "prometheus": f"http://127.0.0.1:{port('AEGIS_PROMETHEUS_PORT', 39090)}",
        "grafana": f"http://127.0.0.1:{port('AEGIS_GRAFANA_PORT', 33001)}",
        "loki": f"http://127.0.0.1:{port('AEGIS_LOKI_PORT', 33100)}",
    }


def cors_allows_web(origins_raw: str, web_port: int) -> bool:
    try:
        parsed = json.loads(origins_raw)
    except json.JSONDecodeError:
        return False
    if not isinstance(parsed, list):
        return False
    needed = {f"http://localhost:{web_port}", f"http://127.0.0.1:{web_port}"}
    return needed.issubset({str(item) for item in parsed})


def published_ports(text: str) -> set[int]:
    return {int(match) for match in re.findall(r"(?:127\.0\.0\.1|0\.0\.0\.0|\[::\]):(\d+)->", text)}


def assess_ports(
    ports: Mapping[str, int], listening: set[int], demo_ports: set[int]
) -> list[PortAssessment]:
    return [
        PortAssessment(name, port, port in listening, port in listening and port in demo_ports)
        for name, port in ports.items()
    ]


def up_arguments(*, build: bool) -> tuple[str, ...]:
    command = ["up", "-d", "--wait"]
    if build:
        command.insert(1, "--build")
    if "--volumes" in command:
        raise ValueError("startup must not delete volumes")
    return tuple(command)


def stop_arguments() -> tuple[str, ...]:
    return ("down",)


def reset_confirmed(flag: bool, typed_text: str | None) -> bool:
    return flag or typed_text == RESET_PHRASE


def parse_compose_ps(text: str) -> list[dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        payload = json.loads(stripped)
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            return [payload]
        return []
    rows: list[dict[str, Any]] = []
    for line in stripped.splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def service_state(row: Mapping[str, Any]) -> str:
    health = str(row.get("Health") or "").lower()
    state = str(row.get("State") or "").lower()
    status = str(row.get("Status") or "").lower()
    if health == "healthy" or "(healthy)" in status:
        return "healthy"
    if state == "running" or status.startswith("up "):
        return "running"
    if state in {"exited", "dead"} or status.startswith("exited"):
        code = row.get("ExitCode", 0 if "(0)" in status or status.endswith(" 0") else None)
        return f"exited:{code}"
    return state or status or "unknown"


def classify_service(name: str, state: str) -> Literal["pass", "fail"]:
    if name in ONE_SHOT_SERVICES:
        return "pass" if state.startswith("exited:0") else "fail"
    if name in HEALTHY_SERVICES:
        return "pass" if state == "healthy" else "fail"
    if name in RUNNING_SERVICES:
        return "pass" if state in {"running", "healthy"} else "fail"
    return "fail"


def assert_project_ownership(rows: Sequence[Mapping[str, Any]], project: str) -> None:
    for row in rows:
        owner = str(row.get("Project") or "")
        if owner and owner != project:
            raise ValueError("Refusing to modify a container outside the demo project")


def stack_is_ready(results: Mapping[str, str]) -> bool:
    return bool(results) and all(value == "pass" for value in results.values())


def failing_components(results: Mapping[str, str]) -> list[str]:
    return [name for name, value in results.items() if value != "pass"]


def looks_like_aegis(name: str) -> bool:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug in {"aegis-news", "aegisnews"} or slug.startswith("aegis-news-")


def is_rejected_name(name: str) -> bool:
    return bool(_REJECTED_NAME.search(name))


def is_preferred_name(name: str) -> bool:
    return bool(_PREFERRED_NAME.search(name))


def select_doppler(
    *,
    installed: bool,
    authenticated: bool,
    projects: list[str],
    configs: Mapping[str, list[str]],
    explicit_project: str | None,
    explicit_config: str | None,
) -> DopplerSelection:
    if not installed:
        return DopplerSelection(
            "unavailable", detail="Doppler CLI is not installed. The demo continues offline."
        )
    if not authenticated:
        return DopplerSelection(
            "unauthenticated",
            detail="Doppler CLI is not authenticated. The demo continues offline.",
        )
    if explicit_project or explicit_config:
        if not explicit_project or not explicit_config:
            return DopplerSelection(
                "ambiguous",
                detail=(
                    "Set both AEGIS_DOPPLER_PROJECT and AEGIS_DOPPLER_CONFIG. "
                    "The demo continues offline."
                ),
            )
        if is_rejected_name(explicit_project) or is_rejected_name(explicit_config):
            return DopplerSelection(
                "rejected",
                explicit_project,
                explicit_config,
                "Refusing a production or staging Doppler configuration.",
            )
        if not looks_like_aegis(explicit_project):
            return DopplerSelection(
                "rejected",
                explicit_project,
                explicit_config,
                "Refusing a Doppler project that is not Aegis News.",
            )
        known = configs.get(explicit_project)
        if known is not None and explicit_config not in known:
            return DopplerSelection(
                "ambiguous",
                explicit_project,
                detail=(
                    f"Configuration {explicit_config} is not in project {explicit_project}. "
                    "The demo continues offline."
                ),
            )
        return DopplerSelection(
            "selected",
            explicit_project,
            explicit_config,
            "Using the explicit Aegis development configuration.",
        )
    matches = [name for name in projects if looks_like_aegis(name)]
    if len(matches) != 1:
        return DopplerSelection(
            "ambiguous",
            detail=(
                "No single Aegis News Doppler project was identified. Set "
                "AEGIS_DOPPLER_PROJECT and AEGIS_DOPPLER_CONFIG. The demo continues offline."
            ),
        )
    project = matches[0]
    safe = [name for name in configs.get(project, []) if not is_rejected_name(name)]
    preferred = [name for name in safe if is_preferred_name(name)]
    if len(preferred) == 1:
        return DopplerSelection(
            "selected",
            project,
            preferred[0],
            "Selected the only development or demo configuration.",
        )
    return DopplerSelection(
        "ambiguous",
        project=project,
        detail=(
            "Doppler has no single development or demo configuration. Set "
            "AEGIS_DOPPLER_CONFIG. The demo continues offline."
        ),
    )


def doppler_blocks_startup(selection: DopplerSelection) -> bool:
    return selection.status == "rejected"


def normalize_secret_map(payload: Mapping[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, str):
            values[key] = value
        elif isinstance(value, dict):
            computed = value.get("computed", value.get("raw"))
            if isinstance(computed, str):
                values[key] = computed
    return values


def provider_environment(secrets: Mapping[str, str]) -> dict[str, str]:
    selected: dict[str, str] = {}
    for key in SECRET_ALLOWLIST:
        value = secrets.get(key, "")
        if value.strip():
            selected[key] = value
    return selected


def configured_provider_names(env: Mapping[str, str]) -> list[str]:
    return [name for key, name in PROVIDER_NAMES.items() if env.get(key, "").strip()]


def validate_acquire(provider: str, limit: int, confirm: bool) -> None:
    if provider not in ACQUIRE_PROVIDERS:
        raise ValueError("Unknown provider")
    if not 1 <= limit <= 5:
        raise ValueError("Acquire limit must be between 1 and 5")
    if not confirm:
        raise ValueError("Provider acquisition requires --confirm and never runs during startup")
