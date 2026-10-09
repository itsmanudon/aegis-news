"""Stopping a disposable runtime must reject reused PIDs and foreign containers."""

import copy
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest

from aegis.providers.models import YouTubeReference
from scripts import completion_integration as runtime
from scripts.completion_product_probe import observed_window, refresh_synthetic_reference


def owned_snapshot():
    executable = str(runtime.ROOT / ".venv/Scripts/python.exe")
    command = [executable, "-m", "apps.worker.main"]
    created = "2026-10-08T17:47:47.100Z"
    record = {
        "project": "aegis-completion-20261008-c1600b0",
        "runtime": str(runtime.RUNTIME),
        "processes": {
            "worker": {
                "pid": 101,
                "child_pid": 102,
                "command": command,
                "created_at": created,
                "child_created_at": created,
            }
        },
        "containers": {"redis": "a" * 12},
    }
    processes = [
        {
            "pid": 101,
            "parent_pid": 10,
            "executable": executable,
            "command_line": subprocess.list2cmdline(command),
            "created_at": created,
        },
        {
            "pid": 102,
            "parent_pid": 101,
            "executable": sys._base_executable,
            "command_line": subprocess.list2cmdline([sys._base_executable, *command[1:]]),
            "created_at": created,
        },
    ]
    containers = [
        {
            "Id": "a" * 64,
            "Name": "/aegis-completion-20261008-c1600b0-redis-1",
            "Config": {
                "Labels": {
                    "com.docker.compose.project": "aegis-completion-20261008-c1600b0",
                    "com.docker.compose.service": "redis",
                    "com.docker.compose.project.working_dir": str(runtime.RUNTIME),
                    "com.docker.compose.project.config_files": str(
                        runtime.RUNTIME / "compose.yaml"
                    ),
                }
            },
        }
    ]
    return record, processes, containers


def test_stop_plan_uses_immutable_container_ids_and_owned_processes():
    record, processes, containers = owned_snapshot()
    plan = runtime.validate_stop_plan(record, processes, containers)
    assert plan["container_ids"] == ["a" * 64]
    assert [value["pid"] for value in plan["processes"]] == [102, 101]


@pytest.mark.parametrize(
    "field,value",
    [
        ("created_at", "2026-10-09T17:47:47.100Z"),
        ("command_line", "python.exe -m unrelated.worker"),
        ("executable", "C:\\Unrelated\\python.exe"),
        ("parent_pid", 999),
    ],
)
def test_stop_plan_refuses_reused_or_unrelated_child_process(field, value):
    record, processes, containers = owned_snapshot()
    processes[1][field] = value
    with pytest.raises(ValueError):
        runtime.validate_stop_plan(record, processes, containers)


def test_stop_plan_refuses_reused_wrapper_even_when_child_is_gone():
    record, processes, containers = owned_snapshot()
    processes[0]["created_at"] = "2026-10-09T17:47:47.100Z"
    with pytest.raises(ValueError):
        runtime.validate_stop_plan(record, processes[:1], containers)


def test_stop_plan_ignores_already_absent_processes_without_killing_any_pid():
    record, _, containers = owned_snapshot()
    assert runtime.validate_stop_plan(record, [], containers)["processes"] == []


@pytest.mark.parametrize(
    "label,value",
    [
        ("com.docker.compose.project", "user-owned-database"),
        ("com.docker.compose.service", "postgres"),
        ("com.docker.compose.project.working_dir", "D:\\User Data"),
        ("com.docker.compose.project.config_files", "D:\\User Data\\compose.yaml"),
    ],
)
def test_stop_plan_refuses_foreign_container_even_with_recorded_id(label, value):
    record, processes, containers = owned_snapshot()
    containers[0]["Config"]["Labels"][label] = value
    with pytest.raises(ValueError):
        runtime.validate_stop_plan(record, processes, containers)


def test_stop_plan_refuses_recreated_container_with_different_immutable_id():
    record, processes, containers = owned_snapshot()
    containers[0]["Id"] = "b" * 64
    with pytest.raises(ValueError):
        runtime.validate_stop_plan(record, processes, containers)


def test_stop_plan_refuses_extra_container_outside_recorded_project_membership():
    record, processes, containers = owned_snapshot()
    extra = copy.deepcopy(containers[0])
    extra["Id"] = "b" * 64
    containers.append(extra)
    with pytest.raises(ValueError):
        runtime.validate_stop_plan(record, processes, containers)


def test_stop_plan_refuses_record_command_that_changes_owned_api_port():
    record, _, containers = owned_snapshot()
    record["processes"] = {
        "api": {
            "pid": 101,
            "child_pid": 102,
            "command": [
                str(runtime.ROOT / ".venv/Scripts/python.exe"),
                "-m",
                "uvicorn",
                "apps.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--no-access-log",
            ],
            "created_at": "2026-10-08T17:47:47.100Z",
            "child_created_at": "2026-10-08T17:47:47.100Z",
        }
    }
    with pytest.raises(ValueError):
        runtime.validate_stop_plan(record, [], containers)


def live_snapshot():
    record, processes, containers = owned_snapshot()
    command = [
        str(runtime.ROOT / ".venv/Scripts/python.exe"),
        "-m",
        "uvicorn",
        "apps.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "38000",
        "--no-access-log",
    ]
    created = "2026-10-08T17:47:47.100Z"
    record["processes"]["api"] = {
        "pid": 201,
        "child_pid": 202,
        "command": command,
        "created_at": created,
        "child_created_at": created,
        "environment_sha256": runtime.environment_fingerprint(),
    }
    processes.extend(
        [
            {
                "pid": 201,
                "parent_pid": 10,
                "executable": command[0],
                "command_line": subprocess.list2cmdline(command),
                "created_at": created,
            },
            {
                "pid": 202,
                "parent_pid": 201,
                "executable": sys._base_executable,
                "command_line": subprocess.list2cmdline([sys._base_executable, *command[1:]]),
                "created_at": created,
            },
        ]
    )
    return record, processes, containers, [{"pid": 202, "address": "127.0.0.1"}]


def test_live_ownership_accepts_the_verified_loopback_api_process():
    runtime.validate_live_api(*live_snapshot())


@pytest.mark.parametrize(
    "listeners", [[], [{"pid": 999, "address": "127.0.0.1"}], [{"pid": 202, "address": "0.0.0.0"}]]
)
def test_live_ownership_refuses_a_replacement_or_nonloopback_http_listener(listeners):
    record, processes, containers, _ = live_snapshot()
    with pytest.raises(ValueError):
        runtime.validate_live_api(record, processes, containers, listeners)


def test_live_ownership_refuses_different_secure_launch_environment():
    record, processes, containers, listeners = live_snapshot()
    record["processes"]["api"]["environment_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        runtime.validate_live_api(record, processes, containers, listeners)


def test_acceptance_refuses_stale_process_identity_before_mutating_helpers(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "RUNTIME", tmp_path)
    record, processes, containers, listeners = live_snapshot()
    processes[-1]["created_at"] = "2026-10-09T17:47:47.100Z"
    (tmp_path / "runtime.json").write_text(json.dumps(record))
    monkeypatch.setattr(runtime, "inspect_processes", lambda _: processes)
    monkeypatch.setattr(runtime, "inspect_containers", lambda _: containers)
    monkeypatch.setattr(runtime, "local_docker", lambda: ["docker", "--context", "desktop-linux"])

    def read_only_command(command, **kwargs):
        assert command[0] == "powershell", "A mutation helper must not be launched"
        return json.dumps(listeners)

    monkeypatch.setattr(runtime.subprocess, "check_output", read_only_command)
    with pytest.raises(ValueError):
        runtime.acceptance()


def test_observed_fixture_window_remains_correct_on_future_dates_and_utc_boundaries():
    assert observed_window(["2035-07-01T23:30:00-02:00", "2035-07-03T01:00:00Z"]) == {
        "start": "2035-07-02T00:00:00+00:00",
        "end": "2035-07-04T00:00:00+00:00",
    }
    with pytest.raises(ValueError):
        observed_window(["2035-07-01T00:00:00"])


def test_expired_synthetic_reference_is_refreshed_without_changing_identity_or_content():
    reference = YouTubeReference(
        video_id="DEMO0000001",
        title="Original CC0 synthetic metadata",
        channel_id="synthetic",
        channel_title="Synthetic",
        youtube_url="https://completion.example.test/video",
        last_refreshed_at=datetime(2026, 10, 8, tzinfo=UTC),
        expires_at=datetime(2026, 11, 6, tzinfo=UTC),
    )
    now = datetime(2040, 2, 1, tzinfo=UTC)
    refreshed = refresh_synthetic_reference(reference, now)
    assert refreshed.last_refreshed_at == now
    assert refreshed.expires_at == now + timedelta(days=29)
    assert refreshed.video_id == "DEMO0000001"
    assert refreshed.title == "Original CC0 synthetic metadata"
    assert refresh_synthetic_reference(refreshed, now + timedelta(hours=1)) is refreshed


def test_unused_restart_command_is_rejected_before_runtime_actions(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["completion_integration", "restart-api"])

    def forbidden_action():
        raise AssertionError("A rejected CLI command must not invoke mutation helpers")

    monkeypatch.setattr(runtime, "acceptance", forbidden_action)
    with pytest.raises(SystemExit) as result:
        runtime.main()
    assert result.value.code == 2
