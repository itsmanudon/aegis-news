from alembic.config import Config
from alembic.script import ScriptDirectory


def test_one_merge_head_preserves_both_feature_parents():
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    assert script.get_heads() == ["mvp_merge_0001"]
    assert set(script.get_revision("mvp_merge_0001").down_revision) == {
        "ingestion_0001",
        "security_0001",
    }
    for revision in ("ingestion_0001", "security_0001"):
        assert script.get_revision(revision).down_revision == "0002_contract_hardening"
