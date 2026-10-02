"""Exercise upgrade/downgrade/upgrade in a new owned local scratch database."""

import os
import subprocess
import sys
from uuid import uuid4

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from aegis.settings import get_settings


def main() -> None:
    configured = make_url(get_settings().database_url.get_secret_value())
    name = f"aegis_migration_test_{uuid4().hex}"
    admin_url = configured.set(drivername="postgresql", database="postgres").render_as_string(
        hide_password=False
    )
    test_url = configured.set(database=name).render_as_string(hide_password=False)
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            environment = {**os.environ, "AEGIS_DATABASE_URL": test_url}
            for args in (
                ("upgrade", "head"),
                ("check",),
                ("downgrade", "base"),
                ("upgrade", "head"),
                ("check",),
            ):
                subprocess.run(
                    [sys.executable, "-m", "alembic", *args], env=environment, check=True
                )
        finally:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )
    print("Migration roundtrip and metadata checks passed")


if __name__ == "__main__":
    main()
