import pytest

from scripts.demo import compose_command, validate_reset_context


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
