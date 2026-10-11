"""Portable commands for the fixed, isolated local aegis-demo Compose project."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.demo_support import (  # noqa: E402
    HEALTHY_SERVICES,
    LOG_SERVICES,
    ONE_SHOT_SERVICES,
    RESET_PHRASE,
    RUNNING_SERVICES,
    SECRET_ALLOWLIST,
    START_STEPS,
    DemoError,
    assert_project_ownership,
    assess_ports,
    classify_service,
    configured_provider_names,
    cors_allows_web,
    demo_urls,
    doppler_blocks_startup,
    failing_components,
    hidden_subprocess_kwargs,
    looks_like_aegis,
    normalize_secret_map,
    parse_compose_ps,
    parse_env_file,
    provider_environment,
    published_ports,
    python_supported,
    redact,
    reset_confirmed,
    select_doppler,
    service_state,
    stack_is_ready,
    stop_arguments,
    up_arguments,
    validate_acquire,
)

PROJECT = "aegis-demo"


def compose_command(*args: str) -> list[str]:
    return [
        "docker",
        "compose",
        "-f",
        str(ROOT / "compose.yaml"),
        *(["--env-file", str(ROOT / ".env")] if (ROOT / ".env").exists() else []),
        "--env-file",
        str(ROOT / "infrastructure/demo.env.example"),
        "-p",
        PROJECT,
        "--profile",
        "full",
        *args,
    ]


def validate_reset_context(context: str, host: str) -> None:
    if context not in {"default", "desktop-linux"} or (
        host and not host.startswith(("unix://", "npipe://"))
    ):
        raise ValueError("Demo reset requires a standard local Docker context/socket")


def validate_reset_volumes(configuration: dict[str, Any]) -> None:
    for key, volume in configuration.get("volumes", {}).items():
        if volume.get("external") or volume.get("name") != f"{PROJECT}_{key}":
            raise ValueError("Demo reset refuses volumes outside its dedicated project")


def run(
    *args: str,
    capture: bool = False,
    extra_env: dict[str, str] | None = None,
    check: bool = True,
) -> str:
    env = {key: value for key, value in os.environ.items() if not key.startswith("COMPOSE_")}
    for key, value in (extra_env or {}).items():
        if key not in SECRET_ALLOWLIST:
            raise ValueError("Refusing to inject a non-allowlisted variable")
        env[key] = value
    result = subprocess.run(
        compose_command(*args),
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        **hidden_subprocess_kwargs(),
    )
    if check and result.returncode != 0:
        detail = redact((result.stderr or result.stdout or "")[:2000])
        raise DemoError("docker compose", detail or f"exit {result.returncode}")
    if capture and args[:1] == ("logs",):
        return redact((result.stdout or "") + (result.stderr or ""))
    return result.stdout or ""


def report(script: str, output: str, *args: str, echo: bool = True) -> dict[str, Any]:
    module = script.removesuffix(".py").replace("/", ".")
    value = run("exec", "-T", "api", "python", "-m", module, *args, capture=True)
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise DemoError(module, "Command did not return a JSON object")
    destination = ROOT / ".integration-results" / output
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(parsed, indent=2) + "\n", encoding="utf-8")
    if echo:
        print(json.dumps(parsed, indent=2))
    return parsed


def demo_env() -> dict[str, str]:
    return parse_env_file(
        (ROOT / "infrastructure/demo.env.example").read_text(encoding="utf-8")
    )


def command_output(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            **hidden_subprocess_kwargs(),
        )
    except FileNotFoundError as exc:
        raise DemoError(args[0], f"{args[0]} is not installed or not on PATH") from exc


def require_local_docker() -> tuple[str, str]:
    if not python_supported(sys.version_info[:2]):
        raise DemoError("python", "Python 3.12 or newer is required")
    docker = command_output(["docker", "version", "--format", "{{.Server.Version}}"])
    if docker.returncode != 0:
        raise DemoError(
            "docker",
            redact(docker.stderr.strip() or "Docker Engine is not available"),
        )
    compose = command_output(["docker", "compose", "version", "--short"])
    if compose.returncode != 0:
        raise DemoError("docker compose", "Docker Compose v2 is not available")
    context = command_output(["docker", "context", "show"])
    if context.returncode != 0:
        raise DemoError("docker context", redact(context.stderr.strip() or "context unavailable"))
    name = context.stdout.strip()
    host = os.environ.get("DOCKER_HOST", "")
    if not host:
        inspected = command_output(
            ["docker", "context", "inspect", name, "--format", "{{.Endpoints.docker.Host}}"]
        )
        host = inspected.stdout.strip()
    try:
        validate_reset_context(name, host)
    except ValueError as exc:
        raise DemoError("docker context", str(exc)) from exc
    return name, host


def listening_ports(ports: list[int]) -> set[int]:
    found: set[int] = set()
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.3)
            try:
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    found.add(port)
            except OSError:
                found.add(port)
    return found


def demo_published_ports() -> set[int]:
    result = command_output(
        [
            "docker",
            "ps",
            "--filter",
            f"label=com.docker.compose.project={PROJECT}",
            "--format",
            "{{.Ports}}",
        ]
    )
    if result.returncode != 0:
        return set()
    return published_ports(result.stdout)


def port_map(ports: Mapping[str, str]) -> dict[str, int]:
    return {key: int(value) for key, value in ports.items() if key.endswith("_PORT")}


def check_ports(ports: Mapping[str, str]) -> None:
    relevant = port_map(ports)
    assessments = assess_ports(
        relevant, listening_ports(list(relevant.values())), demo_published_ports()
    )
    blocked = [item for item in assessments if not item.ok]
    if blocked:
        detail = ", ".join(f"{item.name} {item.port}" for item in blocked)
        raise DemoError(
            "ports",
            "Ports are occupied by processes outside the aegis-demo project: "
            + detail
            + ". This launcher will not stop unrelated containers.",
        )


def project_rows() -> list[dict[str, Any]]:
    text = run("ps", "--all", "--format", "json", capture=True, check=False)
    return parse_compose_ps(text)


def require_ownership() -> list[dict[str, Any]]:
    rows = project_rows()
    try:
        assert_project_ownership(rows, PROJECT)
    except ValueError as exc:
        raise DemoError("ownership", str(exc)) from exc
    return rows


def fetch(url: str, timeout: float = 6) -> tuple[int, str]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(65536).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(65536).decode("utf-8", "replace")
    except Exception as exc:
        return 0, type(exc).__name__


def readiness(ports: Mapping[str, str]) -> dict[str, str]:
    rows = {str(row.get("Service")): row for row in project_rows()}
    results: dict[str, str] = {}
    for name in (*HEALTHY_SERVICES, *RUNNING_SERVICES, *ONE_SHOT_SERVICES):
        row = rows.get(name)
        state = service_state(row) if row else "missing"
        results[name] = classify_service(name, state) if row else "fail"
    urls = demo_urls(port_map(ports))
    api_status, api_body = fetch(urls["api"] + "/ready")
    results["api-ready"] = "pass" if api_status == 200 and '"ready"' in api_body else "fail"
    if api_status == 200:
        try:
            dependencies = json.loads(api_body)["data"]["dependencies"]
        except (json.JSONDecodeError, KeyError, TypeError):
            dependencies = []
        for item in dependencies:
            if isinstance(item, dict) and item.get("name"):
                results[f"api-{item['name']}"] = "pass" if item.get("ready") is True else "fail"
    web_status, web_body = fetch(urls["web"])
    results["web-http"] = "pass" if web_status == 200 else "fail"
    if "Real API" in web_body:
        results["real-api-mode"] = "pass"
    else:
        results["real-api-mode"] = "unverified"
    prom_status, _ = fetch(urls["prometheus"] + "/-/ready")
    results["prometheus-http"] = "pass" if prom_status == 200 else "fail"
    grafana_status, _ = fetch(urls["grafana"] + "/api/health")
    results["grafana-http"] = "pass" if grafana_status == 200 else "fail"
    loki_status, _ = fetch(urls["loki"] + "/ready")
    results["loki-http"] = "pass" if loki_status == 200 else "fail"
    minio_port = int(ports.get("AEGIS_MINIO_PORT", "39000"))
    minio_status, _ = fetch(f"http://127.0.0.1:{minio_port}/minio/health/live")
    results["minio-live"] = "pass" if minio_status == 200 else "fail"
    otel_port = int(ports.get("AEGIS_OTEL_PORT", "34318"))
    otel_status, _ = fetch(f"http://127.0.0.1:{otel_port}/")
    results["otel-http"] = "pass" if otel_status == 200 else "unverified"
    return results


def required_ready(results: dict[str, str]) -> bool:
    required = {key: value for key, value in results.items() if value != "unverified"}
    return stack_is_ready(required)


def wait_until_ready(ports: Mapping[str, str], attempts: int = 40) -> dict[str, str]:
    results = readiness(ports)
    for _ in range(attempts - 1):
        if required_ready(results):
            return results
        time.sleep(2)
        results = readiness(ports)
    return results


def doppler_name_lists() -> tuple[bool, bool, list[str], dict[str, list[str]]]:
    try:
        version = command_output(["doppler", "--version"])
    except DemoError:
        return False, False, [], {}
    if version.returncode != 0:
        return False, False, [], {}
    identity = command_output(["doppler", "me", "--json"])
    if identity.returncode != 0:
        return True, False, [], {}
    projects_result = command_output(["doppler", "projects", "--json"])
    if projects_result.returncode != 0:
        return True, True, [], {}
    try:
        payload = json.loads(projects_result.stdout or "[]")
    except json.JSONDecodeError:
        return True, True, [], {}
    projects: list[str] = []
    entries: list[Any]
    if isinstance(payload, list):
        entries = payload
    elif isinstance(payload, dict) and isinstance(payload.get("projects"), list):
        entries = payload["projects"]
    else:
        entries = []
    for item in entries:
        if isinstance(item, str):
            projects.append(item)
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            projects.append(item["name"])
    configs: dict[str, list[str]] = {}
    explicit = os.environ.get("AEGIS_DOPPLER_PROJECT")
    inspect = [name for name in projects if looks_like_aegis(name)]
    if explicit and explicit not in inspect:
        inspect.append(explicit)
    for project in inspect:
        listed = command_output(["doppler", "configs", "--project", project, "--json"])
        if listed.returncode != 0:
            continue
        try:
            raw_configs = json.loads(listed.stdout or "[]")
        except json.JSONDecodeError:
            continue
        names: list[str] = []
        config_entries = raw_configs if isinstance(raw_configs, list) else []
        for item in config_entries:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(item["name"])
        configs[project] = names
    return True, True, projects, configs


def resolve_providers(explicit_project: str | None, explicit_config: str | None) -> dict[str, str]:
    installed, authenticated, projects, configs = doppler_name_lists()
    selection = select_doppler(
        installed=installed,
        authenticated=authenticated,
        projects=projects,
        configs=configs,
        explicit_project=explicit_project,
        explicit_config=explicit_config,
    )
    print(f"Doppler: {selection.status}. {selection.detail}")
    if selection.project:
        print(f"Doppler project: {selection.project}")
    if selection.config:
        print(f"Doppler config: {selection.config}")
    if doppler_blocks_startup(selection):
        raise DemoError("doppler", selection.detail)
    if selection.status != "selected" or not selection.project or not selection.config:
        print("Providers: none injected. Optional providers stay unconfigured.")
        return {}
    downloaded = command_output(
        [
            "doppler",
            "secrets",
            "download",
            "--no-file",
            "--format",
            "json",
            "--project",
            selection.project,
            "--config",
            selection.config,
        ]
    )
    if downloaded.returncode != 0:
        print("Doppler secret retrieval failed. Continuing offline without provider keys.")
        print(redact(downloaded.stderr)[:400])
        return {}
    try:
        payload = json.loads(downloaded.stdout or "{}")
    except json.JSONDecodeError:
        print("Doppler returned an unreadable secret document. Continuing offline.")
        return {}
    if not isinstance(payload, dict):
        return {}
    selected = provider_environment(normalize_secret_map(payload))
    del payload
    names = configured_provider_names(selected)
    print(
        "Providers configured: " + (", ".join(names) if names else "none of the optional keys")
    )
    print("Startup does not call providers.")
    return selected


def print_summary(
    ports: Mapping[str, str], seed: dict[str, Any] | None, results: dict[str, str]
) -> None:
    urls = demo_urls(port_map(ports))
    print("")
    print("Aegis News local demo")
    print(f"Project: {PROJECT}")
    for label, url in (
        ("Web", urls["web"]),
        ("API", urls["api"]),
        ("API docs", urls["api_docs"]),
        ("Temporal", urls["temporal"]),
        ("MinIO console", urls["minio"]),
        ("Prometheus", urls["prometheus"]),
        ("Grafana", urls["grafana"] + "/d/aegis-demo"),
        ("Loki", urls["loki"]),
    ):
        print(f"{label}: {url}")
    if seed:
        intelligence = seed.get("intelligence", {})
        print(
            "Seed: "
            f"{seed.get('counts_after', {}).get('documents', 'unknown')} presentation documents; "
            f"showcase {seed.get('showcase_documents', 0)}; "
            f"topics {intelligence.get('topic_count', 'unverified')}"
        )
    unverified = [name for name, value in results.items() if value == "unverified"]
    if unverified:
        print("Unverified: " + ", ".join(unverified))
    print("Token: python scripts/demo.py token --role analyst")
    print("Tokens expire after five minutes and are not printed by start.")
    print("Shutdown: python scripts/demo.py stop")


def seed_command(showcase: bool, echo: bool) -> dict[str, Any]:
    args = ["--showcase"] if showcase else []
    return report("scripts/demo_seed.py", "demo-seed.json", *args, echo=echo)


def start(args: argparse.Namespace) -> None:
    if "acquire" in START_STEPS:
        raise DemoError("startup", "Startup must not acquire provider data")
    print("1. Validating the local environment")
    context, _host = require_local_docker()
    print(f"2. Docker context {context} is local")
    ports = demo_env()
    web_port = int(ports.get("AEGIS_WEB_PORT", "33000"))
    if not cors_allows_web(ports.get("AEGIS_CORS_ORIGINS", "[]"), web_port):
        raise DemoError("cors", "Demo CORS does not include the local frontend origins")
    print("3. Checking demo ports")
    check_ports(ports)
    print("4. Resolving optional provider configuration")
    providers = resolve_providers(
        os.environ.get("AEGIS_DOPPLER_PROJECT") or None,
        os.environ.get("AEGIS_DOPPLER_CONFIG") or None,
    )
    print("5. Starting the existing full Compose profile")
    run(*up_arguments(build=args.build), extra_env=providers or None)
    print("6. Waiting for readiness", flush=True)
    results = wait_until_ready(ports)
    if not required_ready(results):
        failed = ", ".join(
            name for name in failing_components(results) if results[name] != "unverified"
        )
        raise DemoError("readiness", "Not ready: " + failed)
    print("7. Seeding synthetic demonstration records")
    try:
        seeded = seed_command(not args.basic, echo=False)
    except (DemoError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        raise DemoError("seed", redact(str(exc))[:1500]) from exc
    if seeded.get("result") != "passed":
        raise DemoError("seed", "Seed receipt did not pass")
    intelligence = seeded.get("intelligence", {})
    if intelligence.get("result") != "passed":
        raise DemoError("verify", "Intelligence verification did not pass")
    print("8. Startup summary")
    print_summary(ports, seeded, results)


def status() -> None:
    ports = demo_env()
    rows = project_rows()
    if not rows:
        print("No aegis-demo containers are running.")
    for row in rows:
        name = str(row.get("Service"))
        print(f"{name}: {service_state(row)}")
    results = readiness(ports) if rows else {}
    if results:
        print("Ready: " + ("yes" if required_ready(results) else "no"))
        failed = failing_components(
            {key: value for key, value in results.items() if value != "unverified"}
        )
        if failed:
            print("Failing: " + ", ".join(failed))
    for label, url in demo_urls(port_map(ports)).items():
        print(f"{label}: {url}")


def doctor() -> None:
    print(f"Python: {sys.version.split()[0]}")
    try:
        context, host = require_local_docker()
        print(f"Docker context: {context} ({host or 'local socket'})")
    except DemoError as exc:
        print(f"Docker problem: {exc.component}: {exc.detail}")
        return
    ports = demo_env()
    web_port = int(ports.get("AEGIS_WEB_PORT", "33000"))
    allowed = cors_allows_web(ports.get("AEGIS_CORS_ORIGINS", "[]"), web_port)
    print("CORS: " + ("local frontend origins allowed" if allowed else "missing local origins"))
    try:
        check_ports(ports)
        print("Ports: available or owned by aegis-demo")
    except DemoError as exc:
        print(f"Ports: {exc.detail}")
    installed, authenticated, projects, configs = doppler_name_lists()
    selection = select_doppler(
        installed=installed,
        authenticated=authenticated,
        projects=projects,
        configs=configs,
        explicit_project=os.environ.get("AEGIS_DOPPLER_PROJECT") or None,
        explicit_config=os.environ.get("AEGIS_DOPPLER_CONFIG") or None,
    )
    print(f"Doppler: {selection.status}. {selection.detail}")
    rows = project_rows()
    if not rows:
        print("Services: not started")
        return
    results = readiness(ports)
    for name, value in results.items():
        print(f"{name}: {value}")
    if required_ready(results):
        try:
            verified = report("scripts/demo_seed.py", "demo-verify.json", "--verify", echo=False)
            print(
                "Seed verification: "
                + verified.get("result", "unknown")
                + f" topics={verified.get('topic_count', 'unknown')}"
            )
        except (DemoError, json.JSONDecodeError) as exc:
            print("Seed verification failed: " + redact(str(exc))[:500])


def logs(service: str | None, tail: int) -> None:
    if service and service not in LOG_SERVICES:
        raise DemoError("logs", "Unknown demo service")
    bounded = min(max(tail, 1), 200)
    args = ["logs", "--tail", str(bounded), "--no-color"]
    if service:
        args.append(service)
    print(redact(run(*args, capture=True)))


def confirm_reset(accepted: bool) -> None:
    if reset_confirmed(accepted, None):
        return
    if not sys.stdin.isatty():
        raise DemoError(
            "reset", f"Re-run with --yes after reviewing ownership, or type {RESET_PHRASE}"
        )
    typed = input(f"Type '{RESET_PHRASE}' to delete only this project's containers and volumes: ")
    if not reset_confirmed(False, typed.strip()):
        raise DemoError("reset", "Reset cancelled")


def reset_demo(accepted: bool) -> None:
    require_local_docker()
    require_ownership()
    configuration = json.loads(run("config", "--format", "json", capture=True))
    try:
        validate_reset_volumes(configuration)
    except ValueError as exc:
        raise DemoError("reset", str(exc)) from exc
    confirm_reset(accepted)
    print("Removing only the local aegis-demo project's containers and volumes.")
    run("down", "--volumes", "--remove-orphans")
    run(*up_arguments(build=True))
    report("scripts/demo_seed.py", "demo-seed.json", "--showcase")


def token(role: str, subject: str) -> None:
    require_ownership()
    print(
        run(
            "exec",
            "-T",
            "api",
            "python",
            "scripts/security_dev.py",
            "token",
            "--key-id",
            "local",
            "--role",
            role,
            "--subject",
            subject,
            capture=True,
        ).strip()
    )


def acquire(provider: str, limit: int, confirm: bool) -> None:
    validate_acquire(provider, limit, confirm)
    print(f"Acquiring at most {limit} items from {provider}.")
    run(
        "exec",
        "-T",
        "api",
        "python",
        "-m",
        "aegis.providers",
        "fetch",
        "--provider",
        provider,
        "--limit",
        str(limit),
    )


def smoke() -> None:
    ports = demo_env()
    urls = demo_urls(port_map(ports))
    token_value = run(
        "exec",
        "-T",
        "api",
        "python",
        "scripts/security_dev.py",
        "token",
        "--key-id",
        "local",
        "--role",
        "admin",
        "--subject",
        "demo-smoke",
        capture=True,
    ).strip()
    env = os.environ.copy()
    env.update(
        {
            "AEGIS_DEMO_SMOKE": "1",
            "AEGIS_E2E_EXTERNAL_SERVER": "1",
            "AEGIS_E2E_BASE_URL": urls["web"],
            "AEGIS_E2E_API_URL": urls["api"],
            "AEGIS_E2E_TOKEN": token_value,
        }
    )
    pnpm = "pnpm.cmd" if sys.platform == "win32" else "pnpm"
    result = subprocess.run(
        [
            pnpm,
            "--filter",
            "@aegisnews/web",
            "exec",
            "playwright",
            "test",
            "e2e/demo-smoke.spec.ts",
            "--workers=1",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        **hidden_subprocess_kwargs(),
    )
    if result.returncode != 0:
        detail = redact(((result.stdout or "") + (result.stderr or ""))[-4000:])
        raise DemoError("browser smoke", detail or "Playwright demo smoke failed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "start",
            "status",
            "doctor",
            "logs",
            "reset",
            "seed",
            "security",
            "benchmark",
            "reliability",
            "acceptance",
            "token",
            "stop",
            "acquire",
            "smoke",
        ),
    )
    parser.add_argument("--role", choices=("admin", "analyst", "viewer"), default="analyst")
    parser.add_argument("--subject", default="presentation-demo")
    parser.add_argument(
        "--hold-tamper-seconds", type=int, choices=range(31), default=0, metavar="0..30"
    )
    parser.add_argument("--build", action="store_true", help="Rebuild images before start")
    parser.add_argument("--basic", action="store_true", help="Seed only the original five items")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive demo reset")
    parser.add_argument("--service", choices=sorted(LOG_SERVICES))
    parser.add_argument("--tail", type=int, default=80)
    parser.add_argument(
        "--provider", choices=("gdelt", "gnews", "newsapi", "newsdata", "youtube")
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--confirm", action="store_true")
    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    args = build_parser().parse_args()
    try:
        if args.command == "reset":
            reset_demo(args.yes)
        elif args.command == "start":
            start(args)
        elif args.command == "status":
            status()
        elif args.command == "doctor":
            doctor()
        elif args.command == "logs":
            logs(args.service, args.tail)
        elif args.command == "seed":
            seed_command(not args.basic, echo=True)
        elif args.command == "benchmark":
            report("scripts/demo_seed.py", "pipeline-benchmark.json", "--benchmark")
        elif args.command == "security":
            report(
                "scripts/demo_security.py",
                "security-demo.json",
                "--hold-tamper-seconds",
                str(args.hold_tamper_seconds),
            )
        elif args.command == "acceptance":
            report("scripts/mvp_acceptance.py", "acceptance.json")
        elif args.command == "reliability":
            run_key = uuid4().hex
            run("stop", "worker")
            try:
                report(
                    "scripts/demo_seed.py",
                    "recovery-submission.json",
                    "--recovery-submit",
                    "--run-key",
                    run_key,
                )
            finally:
                run("up", "-d", "worker")
            report(
                "scripts/demo_seed.py",
                "recovery-completion.json",
                "--recovery-wait",
                "--run-key",
                run_key,
            )
        elif args.command == "token":
            token(args.role, args.subject)
        elif args.command == "acquire":
            acquire(args.provider or "", args.limit, args.confirm)
        elif args.command == "smoke":
            smoke()
        else:
            require_local_docker()
            require_ownership()
            run(*stop_arguments())
    except DemoError as exc:
        print(f"Demo command failed: {exc.component}", file=sys.stderr)
        print(redact(exc.detail), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
