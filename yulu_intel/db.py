import json
import sqlite3
from datetime import date
from typing import List, Tuple

from yulu_intel.config import settings
from yulu_intel.models import CompetitiveAnalysis


def _get_conn() -> sqlite3.Connection:
    return sqlite3.connect(settings.DB_PATH)


def init_db() -> None:
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            normalized_name TEXT UNIQUE NOT NULL,
            first_seen_date TEXT NOT NULL,
            last_seen_date TEXT NOT NULL,
            times_seen INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS analysis_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT NOT NULL,
            product_name TEXT NOT NULL,
            analysis_json TEXT NOT NULL,
            competitor_names TEXT NOT NULL,
            new_competitors TEXT NOT NULL
        );
    """)
    conn.close()


def _normalize(name: str) -> str:
    return name.strip().lower()


def is_first_run() -> bool:
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) FROM competitors").fetchone()
    conn.close()
    return row[0] == 0


def detect_and_store(analysis: CompetitiveAnalysis) -> Tuple[List[str], List[str]]:
    """Returns (new_competitors, returning_competitors)."""
    today = date.today().isoformat()
    conn = _get_conn()

    new_competitors: List[str] = []
    returning_competitors: List[str] = []

    for comp in analysis.competitors:
        norm = _normalize(comp.name)
        row = conn.execute(
            "SELECT id, times_seen FROM competitors WHERE normalized_name = ?",
            (norm,),
        ).fetchone()

        if row is None:
            conn.execute(
                "INSERT INTO competitors (name, normalized_name, first_seen_date, last_seen_date, times_seen) VALUES (?, ?, ?, ?, 1)",
                (comp.name, norm, today, today),
            )
            new_competitors.append(comp.name)
        else:
            conn.execute(
                "UPDATE competitors SET last_seen_date = ?, times_seen = times_seen + 1 WHERE id = ?",
                (today, row[0]),
            )
            returning_competitors.append(comp.name)

    competitor_names = [c.name for c in analysis.competitors]
    conn.execute(
        "INSERT INTO analysis_runs (run_date, product_name, analysis_json, competitor_names, new_competitors) VALUES (?, ?, ?, ?, ?)",
        (
            today,
            analysis.product_name,
            analysis.model_dump_json(),
            json.dumps(competitor_names),
            json.dumps(new_competitors),
        ),
    )

    conn.commit()
    conn.close()
    return new_competitors, returning_competitors


def get_all_known_competitors() -> List[dict]:
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT name, normalized_name, first_seen_date, last_seen_date, times_seen FROM competitors ORDER BY first_seen_date"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
