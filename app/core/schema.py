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

        if "department" not in columns:
            connection.execute(text("ALTER TABLE class_groups ADD COLUMN department VARCHAR(100)"))

        if "group_code" not in columns:
            connection.execute(text("ALTER TABLE class_groups ADD COLUMN group_code VARCHAR(50)"))
            connection.execute(
                text("UPDATE class_groups SET group_code = class_code WHERE group_code IS NULL OR group_code = ''")
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

        if "sessions" in tables:
            session_columns = {column["name"] for column in inspector.get_columns("sessions")}

            if "schedule_id" not in session_columns:
                connection.execute(text("ALTER TABLE sessions ADD COLUMN schedule_id INTEGER"))
                if "weekly_schedule_id" in session_columns:
                    connection.execute(
                        text("UPDATE sessions SET schedule_id = weekly_schedule_id WHERE schedule_id IS NULL")
                    )
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_sessions_schedule_id ON sessions (schedule_id)"))

            if "class_group_id" not in session_columns:
                connection.execute(text("ALTER TABLE sessions ADD COLUMN class_group_id INTEGER"))
                connection.execute(
                    text(
                        """
                        UPDATE sessions
                        SET class_group_id = (
                            SELECT class_group_id
                            FROM weekly_schedules
                            WHERE weekly_schedules.id = sessions.schedule_id
                        )
                        WHERE class_group_id IS NULL
                        """
                    )
                )
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_sessions_class_group_id ON sessions (class_group_id)"))

            if "teacher_id" not in session_columns:
                connection.execute(text("ALTER TABLE sessions ADD COLUMN teacher_id INTEGER"))
                connection.execute(
                    text(
                        """
                        UPDATE sessions
                        SET teacher_id = (
                            SELECT teacher_id
                            FROM weekly_schedules
                            WHERE weekly_schedules.id = sessions.schedule_id
                        )
                        WHERE teacher_id IS NULL
                        """
                    )
                )
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_sessions_teacher_id ON sessions (teacher_id)"))

            if "subject_id" not in session_columns:
                connection.execute(text("ALTER TABLE sessions ADD COLUMN subject_id INTEGER"))
                connection.execute(
                    text(
                        """
                        UPDATE sessions
                        SET subject_id = (
                            SELECT subject_id
                            FROM weekly_schedules
                            WHERE weekly_schedules.id = sessions.schedule_id
                        )
                        WHERE subject_id IS NULL
                        """
                    )
                )
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_sessions_subject_id ON sessions (subject_id)"))

            if "title" not in session_columns:
                connection.execute(text("ALTER TABLE sessions ADD COLUMN title VARCHAR(255)"))
                connection.execute(text("UPDATE sessions SET title = 'Scheduled Class' WHERE title IS NULL OR title = ''"))

            if "start_time" not in session_columns:
                connection.execute(text("ALTER TABLE sessions ADD COLUMN start_time TIME"))
                connection.execute(
                    text(
                        """
                        UPDATE sessions
                        SET start_time = (
                            SELECT start_time
                            FROM weekly_schedules
                            WHERE weekly_schedules.id = sessions.schedule_id
                        )
                        WHERE start_time IS NULL
                        """
                    )
                )

            if "late_time" not in session_columns:
                connection.execute(text("ALTER TABLE sessions ADD COLUMN late_time TIME"))

            if "end_time" not in session_columns:
                connection.execute(text("ALTER TABLE sessions ADD COLUMN end_time TIME"))
                connection.execute(
                    text(
                        """
                        UPDATE sessions
                        SET end_time = (
                            SELECT end_time
                            FROM weekly_schedules
                            WHERE weekly_schedules.id = sessions.schedule_id
                        )
                        WHERE end_time IS NULL
                        """
                    )
                )

            if "room" not in session_columns:
                connection.execute(text("ALTER TABLE sessions ADD COLUMN room VARCHAR(100)"))
                connection.execute(
                    text(
                        """
                        UPDATE sessions
                        SET room = (
                            SELECT room
                            FROM weekly_schedules
                            WHERE weekly_schedules.id = sessions.schedule_id
                        )
                        WHERE room IS NULL OR room = ''
                        """
                    )
                )

            connection.execute(text("UPDATE sessions SET status = 'scheduled' WHERE status = 'planned'"))

            if "updated_at" not in session_columns:
                connection.execute(
                    text("ALTER TABLE sessions ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
                )

        if "attendance" in tables:
            attendance_columns = {column["name"] for column in inspector.get_columns("attendance")}

            if "class_group_id" not in attendance_columns:
                connection.execute(text("ALTER TABLE attendance ADD COLUMN class_group_id INTEGER"))
                connection.execute(
                    text(
                        """
                        UPDATE attendance
                        SET class_group_id = (
                            SELECT class_group_id
                            FROM sessions
                            WHERE sessions.id = attendance.session_id
                        )
                        WHERE class_group_id IS NULL
                        """
                    )
                )
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_attendance_class_group_id ON attendance (class_group_id)"))

            if "schedule_id" not in attendance_columns:
                connection.execute(text("ALTER TABLE attendance ADD COLUMN schedule_id INTEGER"))
                connection.execute(
                    text(
                        """
                        UPDATE attendance
                        SET schedule_id = (
                            SELECT schedule_id
                            FROM sessions
                            WHERE sessions.id = attendance.session_id
                        )
                        WHERE schedule_id IS NULL
                        """
                    )
                )
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_attendance_schedule_id ON attendance (schedule_id)"))

            if "source" not in attendance_columns:
                connection.execute(text("ALTER TABLE attendance ADD COLUMN source VARCHAR(30) NOT NULL DEFAULT 'manual'"))
                if "method" in attendance_columns:
                    connection.execute(text("UPDATE attendance SET source = method WHERE source IS NULL OR source = ''"))

            if "note" not in attendance_columns:
                connection.execute(text("ALTER TABLE attendance ADD COLUMN note VARCHAR(500)"))
