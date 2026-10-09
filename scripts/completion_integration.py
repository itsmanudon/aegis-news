"""Owned, disposable local sprint runtime; never uses existing volumes or provider keys.

Commands: setup, status, acceptance, stop. Stop never removes volumes.
Run with the repository .venv Python. Reports and process logs are ignored.
"""

import argparse
import hashlib
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".test-tmp/completion-runtime"
PROJECT = "aegis-completion-20261008-c1600b0"
API = "http://127.0.0.1:38000"
PORTS = (35432, 36379, 39000, 39001, 37233, 38233, 38000)

COMPOSE = """services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: aegis_completion
      POSTGRES_PASSWORD: isolated_completion_only
      POSTGRES_DB: aegis_completion
    ports: ["127.0.0.1:35432:5432"]
    tmpfs: ["/var/lib/postgresql/data"]
    healthcheck:
      test: [CMD-SHELL, "pg_isready -U aegis_completion -d aegis_completion"]
      interval: 2s
      timeout: 3s
      retries: 30
  redis:
    image: redis:7.4-alpine
    command: [redis-server, --save, "", --appendonly, "no"]
    ports: ["127.0.0.1:36379:6379"]
    tmpfs: ["/data"]
    healthcheck:
      test: [CMD, redis-cli, ping]
      interval: 2s
      timeout: 3s
      retries: 30
  minio:
    image: aegis-demo-minio:latest
    command: [server, /data, --console-address, ":9001"]
    environment:
      MINIO_ROOT_USER: aegis_dev
      MINIO_ROOT_PASSWORD: aegis_dev_only
    ports: ["127.0.0.1:39000:9000", "127.0.0.1:39001:9001"]
    tmpfs: ["/data:mode=1777"]
    healthcheck:
      test: [CMD, wget, -q, -O, /dev/null, http://localhost:9000/minio/health/live]
      interval: 2s
      timeout: 3s
      retries: 30
  temporal:
    image: temporalio/temporal:1.4.1
    command: [server, start-dev, --ip, 0.0.0.0, --db-filename, /tmp/completion-temporal.db]
    ports: ["127.0.0.1:37233:7233", "127.0.0.1:38233:8233"]
    healthcheck:
      test: [CMD, temporal, operator, cluster, health, --address, localhost:7233]
      interval: 2s
      timeout: 3s
      retries: 30
"""


def environment(*, secured: bool = True) -> dict[str, str]:
    """Override .env values explicitly; never return ambient application credentials."""
    result = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("AEGIS_", "COMPOSE_", "AWS_"))
    }
    result.update(
        AEGIS_DATABASE_URL=(
            "postgresql+psycopg://aegis_completion:isolated_completion_only"
            "@127.0.0.1:35432/aegis_completion"
        ),
        AEGIS_REDIS_URL="redis://127.0.0.1:36379/0",
        AEGIS_S3_ENDPOINT_URL="http://127.0.0.1:39000",
        AEGIS_S3_ACCESS_KEY="aegis_dev",
        AEGIS_S3_SECRET_KEY="aegis_dev_only",
        AEGIS_S3_BUCKET="aegis-completion-c1600b0",
        AEGIS_S3_REGION="us-east-1",
        AEGIS_TEMPORAL_ADDRESS="127.0.0.1:37233",
        AEGIS_TEMPORAL_NAMESPACE="default",
        AEGIS_TEMPORAL_TASK_QUEUE=PROJECT,
        AEGIS_TEMPORAL_ENABLED="true",
        AEGIS_AI_PROFILE="offline",
        AEGIS_ENVIRONMENT="development",
        AEGIS_SECURITY_ENABLED=str(secured).lower(),
        AEGIS_DEV_IDENTITY_ENABLED=str(secured).lower(),
        AEGIS_OIDC_ISSUER="http://aegis-completion.local",
        AEGIS_OIDC_AUDIENCE="aegisnews",
        AEGIS_OIDC_ALGORITHMS='["EdDSA"]' if secured else '["RS256"]',
        AEGIS_OIDC_TOKEN_TYPES='["at+jwt"]',
        AEGIS_OIDC_JWKS_URL="",
        AEGIS_OIDC_PUBLIC_KEYS="{}",
        AEGIS_SECURITY_KEY_DIRECTORY=str(RUNTIME / "keys"),
        AEGIS_PROVENANCE_KEY_ID="local",
        AEGIS_SECURITY_PERSIST_AUDIT=str(secured).lower(),
        AEGIS_SECURITY_RATE_BACKEND="redis" if secured else "memory",
        AEGIS_SECURITY_RATE_LIMIT="1000",
        AEGIS_SECURITY_MAX_BODY_BYTES="262144",
        AEGIS_CORS_ORIGINS='["http://127.0.0.1:33000","http://localhost:33000"]'
        if secured
        else '["http://localhost:3000"]',
        AEGIS_PROVIDER_INGESTION_API_URL=API,
        AEGIS_OTEL_ENABLED="false",
        AEGIS_OTEL_ENDPOINT="http://127.0.0.1:4318/v1/traces",
        AEGIS_LOG_FILE="",
        AEGIS_NEWSDATA_API_KEY="",
        AEGIS_GNEWS_API_KEY="",
        AEGIS_NEWSAPI_API_KEY="",
        AEGIS_YOUTUBE_API_KEY="",
        AWS_EC2_METADATA_DISABLED="true",
        AEGIS_RUN_INTEGRATION="1",
        AEGIS_INGESTION_TEST_DATABASE_URL=(
            "postgresql+psycopg://aegis_completion:isolated_completion_only"
            "@127.0.0.1:35432/aegis_completion"
        ),
        AEGIS_TEMPORAL_TEST_ADDRESS="127.0.0.1:37233",
        AEGIS_INGESTION_TEST_TEMPORAL="1",
        AEGIS_INGESTION_TEST_MINIO="http://127.0.0.1:39000",
        AEGIS_TEST_API_URL=API,
        AEGIS_TEST_WEB_URL="http://127.0.0.1:33000",
    )
    return result


def compose(*arguments: str) -> list[str]:
    return ["docker", "compose", "-f", str(RUNTIME / "compose.yaml"), "-p", PROJECT, *arguments]


def run(arguments: list[str], env: dict[str, str] | None = None) -> None:
    subprocess.run(arguments, cwd=ROOT, env=env or environment(), check=True)


def read_status() -> dict[str, Any]:
    with urllib.request.urlopen(API + "/ready", timeout=8) as response:
        return cast(dict[str, Any], json.load(response))


def child_process_id(wrapper: int) -> int:
    if sys.platform != "win32":
        return wrapper
    query = (
        "Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq "
        + str(wrapper)
        + " -and $_.Name -eq 'python.exe' } "
        "| Select-Object -ExpandProperty ProcessId"
    )
    return int(
        subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", query],
            text=True,
        ).strip()
    )


def setup() -> None:
    if (RUNTIME / "runtime.json").exists():
        raise RuntimeError("Runtime ownership already recorded; inspect status before any restart")
    context = subprocess.check_output(["docker", "context", "show"], text=True).strip()
    host = subprocess.check_output(
        ["docker", "context", "inspect", context, "--format", "{{.Endpoints.docker.Host}}"],
        text=True,
    ).strip()
    if context not in {"default", "desktop-linux"} or not host.startswith(("unix://", "npipe://")):
        raise RuntimeError("This disposable runtime requires a local Docker socket")
    existing = subprocess.check_output(
        ["docker", "ps", "-a", "--filter", f"label=com.docker.compose.project={PROJECT}", "-q"],
        text=True,
    ).strip()
    if existing:
        raise RuntimeError("Refusing to reuse existing project containers")
    for port in PORTS:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    RUNTIME.mkdir(parents=True, exist_ok=True)
    (RUNTIME / "compose.yaml").write_text(COMPOSE, encoding="utf-8")
    record: dict[str, Any] = {"project": PROJECT, "runtime": str(RUNTIME), "processes": {}}
    ownership = RUNTIME / "runtime.json"
    ownership.write_text(json.dumps(record, indent=2), encoding="utf-8")
    run(compose("up", "-d", "--pull", "never", "--no-build", "--wait", "--wait-timeout", "120"))
    run([sys.executable, "-m", "alembic", "upgrade", "head"])
    run([sys.executable, "-m", "scripts.init_dev_keys"])
    run([sys.executable, "-m", "scripts.init_storage"])
    commands = {
        "api": [
            sys.executable,
            "-m",
            "uvicorn",
            "apps.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "38000",
            "--no-access-log",
        ],
        "worker": [sys.executable, "-m", "apps.worker.main"],
    }
    for name, command in commands.items():
        with (RUNTIME / f"{name}.log").open("wb") as log:
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                env=environment(),
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=(subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
                if sys.platform == "win32"
                else 0,
            )
        record["processes"][name] = {"pid": process.pid, "command": command}
        ownership.write_text(json.dumps(record, indent=2), encoding="utf-8")
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            report = read_status()
            if report["data"]["status"] == "ready":
                for details in record["processes"].values():
                    details["child_pid"] = child_process_id(int(details["pid"]))
                record_launch_identity(record)
                ownership.write_text(json.dumps(record, indent=2), encoding="utf-8")
                (RUNTIME / "readiness.json").write_text(
                    json.dumps(report, indent=2), encoding="utf-8"
                )
                print(
                    json.dumps(
                        {
                            "project": PROJECT,
                            "api": API,
                            "readiness": report["data"],
                            "processes": {k: v["pid"] for k, v in record["processes"].items()},
                        },
                        indent=2,
                    )
                )
                return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(1)
    raise RuntimeError("API did not become ready; inspect owned logs")


def acceptance() -> None:
    if not (RUNTIME / "runtime.json").exists():
        raise RuntimeError("Initialize the owned runtime before running synthetic acceptance")
    assert_owned_runtime()
    if read_status()["data"]["status"] != "ready":
        raise RuntimeError("Owned API must be ready before synthetic writes")
    for module in ("mvp_acceptance", "demo_seed", "demo_security"):
        report = subprocess.check_output(
            [sys.executable, "-m", f"scripts.{module}", "--api-url", API],
            cwd=ROOT,
            env=environment(),
            text=True,
        )
        parsed = json.loads(report)
        (RUNTIME / f"{module}.json").write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "scenario": module,
                    "result": parsed["result"],
                    "checks": parsed.get("checks", []),
                    "report": str(RUNTIME / f"{module}.json"),
                },
                indent=2,
            )
        )


def path_identity(value: str) -> str:
    return os.path.normcase(str(Path(value).resolve()))


def command_arguments(value: str) -> list[str]:
    # Only fixed Python module commands are accepted; no shell syntax is executed.
    return [part.strip('"') for part in shlex.split(value, posix=False)]


def validate_stop_plan(
    record: dict[str, Any], processes: list[dict[str, Any]], containers: list[dict[str, Any]]
) -> dict[str, Any]:
    """Fail closed before mutations if a PID was reused or any container is foreign."""
    if record.get("project") != PROJECT or record.get("runtime") != str(RUNTIME):
        raise ValueError("Runtime ownership mismatch")
    commands = {
        "worker": ["-m", "apps.worker.main"],
        "api": [
            "-m",
            "uvicorn",
            "apps.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "38000",
            "--no-access-log",
        ],
    }
    wrapper_executable = str(ROOT / ".venv/Scripts/python.exe")
    child_executable = str(getattr(sys, "_base_executable", sys.executable))
    actual_processes = {value["pid"]: value for value in processes}
    stop_processes = []
    if not set(record.get("processes", {})) <= set(commands):
        raise ValueError("Unrecognized runtime process role")
    for role in ("worker", "api"):
        entry = record.get("processes", {}).get(role)
        if entry is None:
            continue
        command = entry.get("command", [])
        if (
            not command
            or path_identity(command[0]) != path_identity(wrapper_executable)
            or command[1:] != commands[role]
        ):
            raise ValueError("Recorded process command does not belong to this runtime")
        for child in (True, False):
            field = "child_pid" if child else "pid"
            created_field = "child_created_at" if child else "created_at"
            pid = entry.get(field)
            if type(pid) is not int or pid < 1:
                raise ValueError("Invalid recorded process ID")
            actual = actual_processes.get(pid)
            if actual is None:
                continue
            expected_executable = child_executable if child else wrapper_executable
            argv = command_arguments(actual["command_line"])
            if (
                not argv
                or path_identity(argv[0]) != path_identity(expected_executable)
                or path_identity(actual["executable"]) != path_identity(expected_executable)
                or argv[1:] != commands[role]
                or not entry.get(created_field)
                or actual["created_at"] != entry[created_field]
                or (child and actual["parent_pid"] != entry["pid"])
            ):
                raise ValueError("Recorded PID has a different process identity; refusing to stop")
            stop_processes.append(actual)
    expected = record.get("containers", {})
    if len(containers) != len(expected) or not set(expected) <= {
        "postgres",
        "redis",
        "minio",
        "temporal",
    }:
        raise ValueError("Runtime container membership mismatch")
    container_ids = []
    for service, prefix in expected.items():
        if not isinstance(prefix, str) or not re.fullmatch(r"[0-9a-f]{12,64}", prefix):
            raise ValueError("Invalid recorded container ID")
        matches = [value for value in containers if value["Id"].startswith(prefix)]
        if len(matches) != 1:
            raise ValueError("Recorded container was removed or recreated")
        actual_container = matches[0]
        labels = actual_container["Config"]["Labels"] or {}
        if (
            actual_container["Name"] != f"/{PROJECT}-{service}-1"
            or labels.get("com.docker.compose.project") != PROJECT
            or labels.get("com.docker.compose.service") != service
            or path_identity(labels.get("com.docker.compose.project.working_dir", ""))
            != path_identity(str(RUNTIME))
            or path_identity(labels.get("com.docker.compose.project.config_files", ""))
            != path_identity(str(RUNTIME / "compose.yaml"))
        ):
            raise ValueError("Container labels do not identify the owned runtime")
        container_ids.append(actual_container["Id"])
    return {"processes": stop_processes, "container_ids": container_ids}


def local_docker() -> list[str]:
    context = subprocess.check_output(["docker", "context", "show"], text=True).strip()
    endpoint = subprocess.check_output(
        ["docker", "context", "inspect", context, "--format", "{{.Endpoints.docker.Host}}"],
        text=True,
    ).strip()
    if context not in {"default", "desktop-linux"} or not endpoint.startswith(
        ("unix://", "npipe://")
    ):
        raise ValueError("Stopping requires an explicit local Docker context")
    return ["docker", "--context", context]


def inspect_processes(record: dict[str, Any]) -> list[dict[str, Any]]:
    identifiers = [
        int(value[key]) for value in record["processes"].values() for key in ("pid", "child_pid")
    ]
    query = (
        "$aegisCompletionIds = @("
        + ",".join(map(str, identifiers))
        + ")\n"
        + """
$aegisCompletionRows = @(Get-CimInstance Win32_Process | Where-Object {
    $aegisCompletionIds -contains $_.ProcessId
} | ForEach-Object {
    [PSCustomObject]@{
        pid=$_.ProcessId; parent_pid=$_.ParentProcessId; executable=$_.ExecutablePath;
        command_line=$_.CommandLine;
        created_at=$_.CreationDate.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
    }
})
ConvertTo-Json -InputObject $aegisCompletionRows -Compress
"""
    )
    return cast(
        list[dict[str, Any]],
        json.loads(
            subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", query],
                text=True,
            )
        ),
    )


def inspect_containers(docker: list[str]) -> list[dict[str, Any]]:
    identifiers = subprocess.check_output(
        [*docker, "ps", "-a", "--filter", f"label=com.docker.compose.project={PROJECT}", "-q"],
        text=True,
    ).split()
    if not identifiers:
        return []
    template = (
        '{"Id":{{json .Id}},"Name":{{json .Name}},"Config":{"Labels":{{json .Config.Labels}}}}'
    )
    output = subprocess.check_output(
        [*docker, "inspect", "--format", template, *identifiers], text=True
    )
    return [json.loads(line) for line in output.splitlines() if line]


def environment_fingerprint() -> str:
    # This sealed launch attestation contains only a digest, never raw settings.
    values = {key: value for key, value in environment().items() if key.startswith("AEGIS_")}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def record_launch_identity(
    record: dict[str, Any],
    *,
    roles: tuple[str, ...] = ("api", "worker"),
) -> None:
    """Capture identity immediately after owned launch; never refresh identity during stop."""
    processes = inspect_processes(record)
    by_pid = {value["pid"]: value for value in processes}
    for role in roles:
        entry = record["processes"][role]
        entry["created_at"] = by_pid[entry["pid"]]["created_at"]
        entry["child_created_at"] = by_pid[entry["child_pid"]]["created_at"]
        entry["environment_sha256"] = environment_fingerprint()
    containers = inspect_containers(local_docker())
    if not record.get("containers"):
        record["containers"] = {
            value["Config"]["Labels"]["com.docker.compose.service"]: value["Id"]
            for value in containers
        }
    validate_stop_plan(record, processes, containers)


def validate_live_api(
    record: dict[str, Any],
    processes: list[dict[str, Any]],
    containers: list[dict[str, Any]],
    listeners: list[dict[str, Any]],
) -> None:
    validate_stop_plan(record, processes, containers)
    entry = record.get("processes", {}).get("api", {})
    if (
        entry.get("environment_sha256") != environment_fingerprint()
        or not entry.get("child_pid")
        or entry["child_pid"] not in {value["pid"] for value in processes}
        or not listeners
        or any(
            value["pid"] != entry["child_pid"] or value["address"] != "127.0.0.1"
            for value in listeners
        )
    ):
        raise ValueError("Live HTTP listener or secure launch environment is not owned")


def assert_owned_runtime() -> None:
    """Bind HTTP writes to owned launch/PID, socket, keys, database and Docker labels."""
    record = json.loads((RUNTIME / "runtime.json").read_text())
    query = """
$aegisStopListeners = @(Get-NetTCPConnection -State Listen -LocalPort 38000 -ErrorAction Stop |
    ForEach-Object { [PSCustomObject]@{pid=$_.OwningProcess;address=$_.LocalAddress} })
ConvertTo-Json -InputObject $aegisStopListeners -Compress
"""
    listeners = json.loads(
        subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", query],
            text=True,
        )
    )
    validate_live_api(
        record, inspect_processes(record), inspect_containers(local_docker()), listeners
    )
    # A token issued by the owned keys must authenticate at the owned listener.
    # When a synthetic sentinel exists, SQL and HTTP must return the same source,
    # tying the live application database to the explicitly isolated connection.
    os.environ.update(environment())
    from sqlalchemy import create_engine, text

    from aegis.security.dev_identity import issue_development_token
    from aegis.security.keys import FileKeyProvider
    from aegis.settings import Settings

    settings = Settings(_env_file=None)
    token = issue_development_token(
        settings,
        FileKeyProvider(settings.security_key_directory),
        key_id="local",
        subject="completion-ownership-check",
        role="admin",
    )

    def request(path: str) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(
                urllib.request.Request(
                    API + path,
                    headers={"Authorization": "Bearer " + token},
                ),
                timeout=10,
            ) as response:
                return cast(dict[str, Any], json.load(response))
        except Exception:
            raise ValueError("Owned HTTP identity check failed; credentials withheld") from None

    identity = request("/api/v1/security/me")["data"]
    if identity["subject"] != "completion-ownership-check" or "admin" not in identity["roles"]:
        raise ValueError("HTTP identity does not match the owned key environment")
    engine = create_engine(environment()["AEGIS_DATABASE_URL"])
    try:
        with engine.connect() as connection:
            if connection.scalar(text("SELECT current_database()")) != "aegis_completion":
                raise ValueError("Isolated database identity mismatch")
            sentinel = (
                connection.execute(
                    text("SELECT source_id,name FROM sources WHERE name=:name LIMIT 1"),
                    {"name": "DEMO Completion Newsroom — Original CC0 Synthetic"},
                )
                .mappings()
                .first()
            )
        if sentinel:
            value = request("/api/v1/sources/" + sentinel["source_id"])["data"]
            if value["source_id"] != sentinel["source_id"] or value["name"] != sentinel["name"]:
                raise ValueError("HTTP database differs from the owned SQL database")
    finally:
        engine.dispose()


def stop(*, dry_run: bool = False) -> None:
    """Explicitly stop verified task processes/containers, leaving all volumes intact.

    PostgreSQL/MinIO tmpfs contents are disposable and disappear on container stop.
    This command is not called by acceptance, status, tests or session rollover.
    """
    ownership = RUNTIME / "runtime.json"
    record = json.loads(ownership.read_text())
    docker = local_docker()
    plan = validate_stop_plan(record, inspect_processes(record), inspect_containers(docker))
    if dry_run:
        print(
            json.dumps(
                {
                    "project": PROJECT,
                    "validated": True,
                    "process_ids": [value["pid"] for value in plan["processes"]],
                    "container_ids": plan["container_ids"],
                    "stopped": False,
                },
                indent=2,
            )
        )
        return
    # Revalidate process metadata after acquiring a stable Process object. Using
    # Stop-Process -InputObject avoids killing a new process if its PID is reused.
    commands = []
    for value in plan["processes"]:

        def quote(content: str) -> str:
            return "'" + content.replace("'", "''") + "'"

        pid = int(value["pid"])
        commands.append(f"""
$aegisCompletionProcess = Get-Process -Id {pid} -ErrorAction SilentlyContinue
    if ($aegisCompletionProcess) {{
    $aegisCompletionMetadata = Get-CimInstance Win32_Process -Filter 'ProcessId={pid}'
    $aegisCompletionStart = $aegisCompletionProcess.StartTime.ToUniversalTime()
    $aegisCompletionCreated = $aegisCompletionMetadata.CreationDate.ToUniversalTime()
    if (-not $aegisCompletionMetadata -or
        $aegisCompletionStart.ToString('yyyy-MM-ddTHH:mm:ss.fffZ') -ne
            {quote(value["created_at"])} -or
        $aegisCompletionCreated.ToString('yyyy-MM-ddTHH:mm:ss.fffZ') -ne
            {quote(value["created_at"])} -or
        $aegisCompletionMetadata.CommandLine -cne {quote(value["command_line"])}) {{
        throw 'Process identity changed during stop; refusing PID reuse'
    }}
    Stop-Process -InputObject $aegisCompletionProcess -ErrorAction Stop
}}
""")
    # Immutable IDs and labels must still match before any stop action begins.
    validate_stop_plan(record, inspect_processes(record), inspect_containers(docker))
    if commands:
        run(["powershell", "-NoProfile", "-Command", "\n".join(commands)])
    if plan["container_ids"]:
        run([*docker, "stop", *plan["container_ids"]])
    record["stopped_at"] = time.time()
    record["temporary_data_discarded"] = "PostgreSQL and MinIO tmpfs; no volumes removed"
    ownership.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print("Owned completion runtime stopped; no containers or volumes removed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "status", "acceptance", "stop"))
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate stop ownership without stopping"
    )
    args = parser.parse_args()
    if args.command == "setup":
        setup()
    elif args.command == "status":
        print(json.dumps(read_status(), indent=2))
    elif args.command == "stop":
        stop(dry_run=args.dry_run)
    else:
        acceptance()


if __name__ == "__main__":
    main()
