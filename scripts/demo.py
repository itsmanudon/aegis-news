"""Portable commands for the fixed, isolated local aegis-demo Compose project."""

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
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


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        compose_command(*args),
        cwd=ROOT,
        env={key: value for key, value in os.environ.items() if not key.startswith("COMPOSE_")},
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout or ""


def report(script: str, output: str, *args: str) -> None:
    module = script.removesuffix(".py").replace("/", ".")
    value = run("exec", "-T", "api", "python", "-m", module, *args, capture=True)
    parsed = json.loads(value)
    destination = ROOT / ".integration-results" / output
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(parsed, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(parsed, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "start",
            "reset",
            "seed",
            "security",
            "benchmark",
            "reliability",
            "acceptance",
            "token",
            "stop",
        ),
    )
    parser.add_argument("--role", choices=("admin", "analyst", "viewer"), default="analyst")
    parser.add_argument(
        "--hold-tamper-seconds", type=int, choices=range(31), default=0, metavar="0..30"
    )
    args = parser.parse_args()
    if args.command == "reset":
        context = subprocess.check_output(["docker", "context", "show"], text=True).strip()
        host = (
            os.environ.get("DOCKER_HOST")
            or subprocess.check_output(
                ["docker", "context", "inspect", context, "--format", "{{.Endpoints.docker.Host}}"],
                text=True,
            ).strip()
        )
        validate_reset_context(context, host)
        validate_reset_volumes(json.loads(run("config", "--format", "json", capture=True)))
        print("Removing only the local aegis-demo project's containers and volumes.")
        run("down", "--volumes", "--remove-orphans")
        run("up", "--build", "-d", "--wait")
        report("scripts/demo_seed.py", "demo-seed.json")
    elif args.command == "start":
        run("up", "--build", "-d", "--wait")
        report("scripts/demo_seed.py", "demo-seed.json")
    elif args.command == "seed":
        report("scripts/demo_seed.py", "demo-seed.json")
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
                args.role,
                "--subject",
                "presentation-demo",
                capture=True,
            ).strip()
        )
    else:
        run("down")


if __name__ == "__main__":
    main()
