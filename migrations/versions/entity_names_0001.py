"""Entity match keys, so resolution looks candidates up instead of scanning entities."""

import re
import unicodedata

import sqlalchemy as sa
from alembic import op

revision = "entity_names_0001"
down_revision = "feed_0001"
branch_labels = None
depends_on = None

# Frozen copy of aegis.intelligence.resolution.match_keys as of this revision. A
# migration must keep producing the same rows after the application code moves on.
LEGAL_FORMS = frozenset(
    [
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "co",
        "company",
        "ltd",
        "limited",
        "plc",
        "llc",
        "lp",
        "llp",
        "ag",
        "se",
        "sa",
        "nv",
        "bv",
        "gmbh",
        "spa",
        "ab",
        "asa",
        "oyj",
        "pvt",
        "private",
    ]
)


def match_keys(name: str) -> tuple[str, ...]:
    full = " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", name).casefold()))
    words = full.split()
    if len(words) > 1 and words[0] == "the":
        words = words[1:]
    while len(words) > 1 and words[-1] in LEGAL_FORMS:
        words.pop()
    return tuple(dict.fromkeys(key for key in (full, " ".join(words)) if key))


def upgrade() -> None:
    names = op.create_table(
        "entity_names",
        sa.Column(
            "entity_id", sa.String(64), sa.ForeignKey("entities.entity_id"), primary_key=True
        ),
        sa.Column("key", sa.String(512), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('name', 'alias')", name="entity_name_kind"),
        sa.CheckConstraint("key <> ''", name="entity_name_key"),
        sa.CheckConstraint(
            "entity_id ~ '^ent_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="entity_names_entity_id_format",
        ),
    )
    op.create_index("entity_name_lookup", "entity_names", ["key"])
    # Existing entities become findable under their own name.
    rows = [
        {"entity_id": entity_id, "key": key, "kind": "name", "created_at": created_at}
        for entity_id, name, created_at in op.get_bind().execute(
            sa.text("SELECT entity_id, canonical_name, created_at FROM entities")
        )
        for key in match_keys(name)
    ]
    if rows:
        op.bulk_insert(names, rows)


def downgrade() -> None:
    op.drop_index("entity_name_lookup", table_name="entity_names")
    op.drop_table("entity_names")
