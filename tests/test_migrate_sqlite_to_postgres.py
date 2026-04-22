from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


def test_migration_script_can_copy_sqlite_into_another_sqlite(tmp_path: Path) -> None:
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"

    source_engine = create_engine(f"sqlite:///{source_db}", future=True)
    with source_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE interviews (
                    id TEXT PRIMARY KEY,
                    target_role TEXT NOT NULL,
                    level TEXT NOT NULL,
                    round_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    resume_filename TEXT,
                    resume_text TEXT,
                    max_turns INTEGER NOT NULL,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO interviews (
                    id, target_role, level, round_type, status, provider, model_name, prompt_version, max_turns, created_at, updated_at
                ) VALUES (
                    'itv-1', '后端工程师', '高级', 'standard', 'running', 'mock', 'mock-interviewer-v1', 'v1', 8, '2026-04-21 12:00:00', '2026-04-21 12:00:00'
                )
                """
            )
        )

    subprocess.run(
        [
            sys.executable,
            "scripts/migrate_sqlite_to_postgres.py",
            "--source-url",
            f"sqlite:///{source_db}",
            "--target-url",
            f"sqlite:///{target_db}",
            "--truncate-target",
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
    )

    target_engine = create_engine(f"sqlite:///{target_db}", future=True)
    with target_engine.connect() as connection:
        rows = connection.execute(text("SELECT id, target_role, level FROM interviews")).all()

    assert rows == [("itv-1", "后端工程师", "高级")]
