from sqlalchemy import inspect, text

from app.core.database import engine


def ensure_development_schema():
    """Keep the checked-in SQLite dev database compatible with model additions."""
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "class_groups" not in tables:
        return

    with engine.begin() as connection:
        columns = {column["name"] for column in inspector.get_columns("class_groups")}
        if "class_code" not in columns:
            connection.execute(text("ALTER TABLE class_groups ADD COLUMN class_code VARCHAR(50)"))
            connection.execute(
                text("UPDATE class_groups SET class_code = name WHERE class_code IS NULL OR class_code = ''")
            )
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_class_groups_class_code ON class_groups (class_code)"))

        if "status" not in columns:
            connection.execute(
                text("ALTER TABLE class_groups ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'active'")
            )

        if "teachers" in tables:
            teacher_columns = {column["name"] for column in inspector.get_columns("teachers")}
            if "status" not in teacher_columns:
                connection.execute(
                    text("ALTER TABLE teachers ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'active'")
                )

        if "subjects" in tables:
            subject_columns = {column["name"] for column in inspector.get_columns("subjects")}
            if "status" not in subject_columns:
                connection.execute(
                    text("ALTER TABLE subjects ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'active'")
                )
