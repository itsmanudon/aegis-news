import json
from pathlib import Path

import pytest

from aegis.intelligence.runtime import keyword_scores
from aegis.intelligence.taxonomy import TOPICS
from scripts.demo import ROOT, build_parser, required_ready, stop_arguments, up_arguments
from scripts.demo_support import (
    START_STEPS,
    assess_ports,
    classify_service,
    configured_provider_names,
    cors_allows_web,
    doppler_blocks_startup,
    failing_components,
    hidden_subprocess_kwargs,
    normalize_secret_map,
    parse_compose_ps,
    provider_environment,
    redact,
    reset_confirmed,
    select_doppler,
    stack_is_ready,
    validate_acquire,
)


def test_unverified_checks_do_not_fail_a_ready_stack():
    assert required_ready({"api": "pass", "otel-http": "unverified"}) is True
    assert required_ready({"api": "pass", "loki-http": "fail"}) is False


def test_startup_plan_does_not_call_providers_or_delete_volumes():
    assert "acquire" not in START_STEPS
    assert "--volumes" not in up_arguments(build=False)
    assert up_arguments(build=False) == ("up", "-d", "--wait")
    assert up_arguments(build=True)[1] == "--build"
    assert stop_arguments() == ("down",)


def test_cli_accepts_lifecycle_commands():
    parser = build_parser()
    for command in ("start", "status", "doctor", "logs", "seed", "token", "stop", "reset"):
        assert parser.parse_args([command]).command == command
    reset = parser.parse_args(["reset", "--yes"])
    assert reset.yes is True
    assert parser.parse_args(["start"]).basic is False
    assert parser.parse_args(["token", "--role", "viewer"]).role == "viewer"


def test_port_ownership_refuses_unrelated_listeners():
    assessments = assess_ports({"AEGIS_WEB_PORT": 33000}, {33000}, set())
    assert assessments[0].ok is False
    owned = assess_ports({"AEGIS_WEB_PORT": 33000}, {33000}, {33000})
    assert owned[0].owned_by_demo is True
    free = assess_ports({"AEGIS_WEB_PORT": 33000}, set(), set())
    assert free[0].ok is True


def test_reset_requires_exact_confirmation():
    assert reset_confirmed(True, None) is True
    assert reset_confirmed(False, "reset aegis-demo") is True
    assert reset_confirmed(False, "yes") is False


def test_compose_ps_and_partial_stack():
    rows = parse_compose_ps(
        "\n".join(
            [
                json.dumps(
                    {
                        "Service": "api",
                        "State": "running",
                        "Health": "healthy",
                        "Project": "aegis-demo",
                    }
                ),
                json.dumps({"Service": "web", "State": "running", "Project": "aegis-demo"}),
            ]
        )
    )
    assert classify_service("api", "healthy") == "pass"
    assert classify_service("web", "running") == "fail"
    assert classify_service("migrate", "exited:0") == "pass"
    assert classify_service("worker", "running") == "pass"
    assert stack_is_ready({"api": "pass", "web": "fail"}) is False
    assert failing_components({"api": "pass", "web": "fail"}) == ["web"]
    assert rows[0]["Project"] == "aegis-demo"


def test_missing_and_rejected_doppler_configurations():
    offline = select_doppler(
        installed=False,
        authenticated=False,
        projects=[],
        configs={},
        explicit_project=None,
        explicit_config=None,
    )
    assert offline.status == "unavailable"
    assert doppler_blocks_startup(offline) is False
    rejected = select_doppler(
        installed=True,
        authenticated=True,
        projects=["aegis-news"],
        configs={"aegis-news": ["dev", "prd"]},
        explicit_project="aegis-news",
        explicit_config="prd",
    )
    assert rejected.status == "rejected"
    assert doppler_blocks_startup(rejected) is True
    ambiguous = select_doppler(
        installed=True,
        authenticated=True,
        projects=["other-product"],
        configs={},
        explicit_project=None,
        explicit_config=None,
    )
    assert ambiguous.status == "ambiguous"
    selected = select_doppler(
        installed=True,
        authenticated=True,
        projects=["aegis-news", "unrelated"],
        configs={"aegis-news": ["dev", "prd"]},
        explicit_project=None,
        explicit_config=None,
    )
    assert selected.status == "selected"
    assert selected.config == "dev"


def test_provider_secrets_are_allowlisted_and_redacted():
    selected = provider_environment(
        normalize_secret_map(
            {
                "AEGIS_NEWSDATA_API_KEY": {"computed": "news-secret"},
                "AEGIS_DATABASE_URL": "postgresql://secret",
                "AEGIS_OIDC_ISSUER": "https://prod.example",
                "AEGIS_GNEWS_API_KEY": "",
            }
        )
    )
    assert selected == {"AEGIS_NEWSDATA_API_KEY": "news-secret"}
    assert configured_provider_names(selected) == ["newsdata"]
    leaked = (
        "Authorization: Bearer eyJhbGciOi.eyJzdWIi.signature "
        "AEGIS_NEWSDATA_API_KEY=news-secret"
    )
    hidden = redact(leaked)
    assert "news-secret" not in hidden
    assert "eyJhbGciOi" not in hidden
    assert "Bearer [redacted]" in hidden


def test_acquire_is_explicit_and_bounded():
    with pytest.raises(ValueError):
        validate_acquire("newsdata", 2, False)
    with pytest.raises(ValueError):
        validate_acquire("newsdata", 30, True)
    validate_acquire("gdelt", 2, True)


def test_cors_and_subprocess_flags(monkeypatch: pytest.MonkeyPatch):
    origins = '["http://localhost:33000","http://127.0.0.1:33000"]'
    assert cors_allows_web(origins, 33000) is True
    assert cors_allows_web('["https://prod.example"]', 33000) is False
    monkeypatch.setattr("scripts.demo_support.sys.platform", "linux")
    assert "creationflags" not in hidden_subprocess_kwargs()


def test_showcase_topics_cover_the_directory():
    samples = json.loads((Path(ROOT) / "data/samples/showcase.json").read_text(encoding="utf-8"))
    labels = []
    dated = 0
    undated = 0
    for sample in samples:
        assert "original synthetic demonstration record" in sample["text"]
        scores = keyword_scores(sample["text"], TOPICS)
        label = scores[0]["label"] if scores else "general"
        assert label == sample["expected_topic"]
        labels.append(label)
        if sample.get("published_at"):
            dated += 1
        else:
            undated += 1
    assert len(samples) >= 20
    assert len(set(labels)) >= 8
    assert undated == 1
    assert dated >= 20
