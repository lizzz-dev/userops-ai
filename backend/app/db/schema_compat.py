from sqlalchemy import Engine, inspect, text


def upgrade_legacy_schema(engine: Engine) -> None:
    """Apply the two small compatibility changes needed by the v1 prototype.

    This is intentionally narrow: it preserves the user's existing local
    Docker volume without introducing a full migration framework mid-project.
    New installations receive the final schema from SQLAlchemy metadata.
    """

    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    with engine.begin() as connection:
        if "owner_account_id" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE users ADD COLUMN owner_account_id INTEGER NULL "
                    "REFERENCES accounts(id) ON DELETE CASCADE"
                )
            )

        if engine.dialect.name == "postgresql":
            preparer = engine.dialect.identifier_preparer
            for constraint in inspector.get_unique_constraints("users"):
                columns_in_constraint = constraint.get("column_names") or []
                name = constraint.get("name")
                if columns_in_constraint == ["email"] and name:
                    quoted_name = preparer.quote(name)
                    connection.execute(
                        text(f"ALTER TABLE users DROP CONSTRAINT {quoted_name}")
                    )

        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_users_owner_account_id "
                "ON users (owner_account_id)"
            )
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_owner_email "
                "ON users (owner_account_id, email)"
            )
        )
