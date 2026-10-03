import pytest

from scripts.demo import ROOT, compose_command, validate_reset_context


def test_demo_commands_always_use_one_isolated_project():
    command = compose_command("down", "--volumes")
    assert command[command.index("-p") + 1] == "aegis-demo"
    assert "demo.env.example" in command[command.index("--env-file") + 1]
    assert "--volumes" in command


@pytest.mark.parametrize(
    "context,host", [("remote-production", ""), ("default", "tcp://remote:2375")]
)
def test_reset_refuses_nonlocal_docker_context(context, host):
    with pytest.raises(ValueError):
        validate_reset_context(context, host)


def test_reset_accepts_standard_local_contexts():
    validate_reset_context("desktop-linux", "")
    validate_reset_context("default", "unix:///var/run/docker.sock")


def test_compose_ignores_inherited_file_overrides(monkeypatch):
    monkeypatch.setenv("COMPOSE_FILE", "unrelated.yaml")
    command = compose_command("down", "--volumes")
    assert command[command.index("-f") + 1] == str(ROOT / "compose.yaml")


def test_reset_rejects_unrelated_resolved_volumes():
    from scripts.demo import validate_reset_volumes

    validate_reset_volumes({"volumes": {"postgres-data": {"name": "aegis-demo_postgres-data"}}})
    with pytest.raises(ValueError):
        validate_reset_volumes({"volumes": {"postgres-data": {"name": "unrelated-data"}}})
    with pytest.raises(ValueError):
        validate_reset_volumes(
            {"volumes": {"postgres-data": {"name": "aegis-demo_postgres-data", "external": True}}}
        )
