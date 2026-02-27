import json
from datetime import date
from typing import List, Optional, Tuple

from supabase import create_client

from yulu_intel.config import settings
from yulu_intel.models import CompetitiveAnalysis

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client


def init_db() -> None:
    # Tables are created in Supabase dashboard — this is a no-op.
    # Kept for API compatibility with run.py.
    pass


def _normalize(name: str) -> str:
    return name.strip().lower()


def is_first_run() -> bool:
    sb = _get_client()
    result = sb.table("competitors").select("id", count="exact").limit(1).execute()
    return result.count == 0


def detect_and_store(
    analysis: CompetitiveAnalysis,
    report_html: Optional[str] = None,
) -> Tuple[List[str], List[str]]:
    """Returns (new_competitors, returning_competitors)."""
    today = date.today().isoformat()
    sb = _get_client()

    new_competitors: List[str] = []
    returning_competitors: List[str] = []

    for comp in analysis.competitors:
        norm = _normalize(comp.name)
        result = sb.table("competitors").select("id, times_seen").eq("normalized_name", norm).execute()

        if not result.data:
            sb.table("competitors").insert({
                "name": comp.name,
                "normalized_name": norm,
                "first_seen_date": today,
                "last_seen_date": today,
                "times_seen": 1,
            }).execute()
            new_competitors.append(comp.name)
        else:
            row = result.data[0]
            sb.table("competitors").update({
                "last_seen_date": today,
                "times_seen": row["times_seen"] + 1,
            }).eq("id", row["id"]).execute()
            returning_competitors.append(comp.name)

    competitor_names = [c.name for c in analysis.competitors]
    row_data = {
        "run_date": today,
        "product_name": analysis.product_name,
        "analysis_json": analysis.model_dump_json(),
        "competitor_names": json.dumps(competitor_names),
        "new_competitors": json.dumps(new_competitors),
    }
    if report_html is not None:
        row_data["report_html"] = report_html
    sb.table("analysis_runs").insert(row_data).execute()

    return new_competitors, returning_competitors


def store_report_html(run_date: str, report_html: str) -> None:
    """Update the most recent analysis_runs row for the given date with report HTML."""
    sb = _get_client()
    # Find the row we just inserted (most recent for this date)
    result = sb.table("analysis_runs").select("id").eq(
        "run_date", run_date
    ).order("id", desc=True).limit(1).execute()

    if result.data:
        row_id = result.data[0]["id"]
        sb.table("analysis_runs").update({
            "report_html": report_html,
        }).eq("id", row_id).execute()


def get_all_known_competitors() -> List[dict]:
    sb = _get_client()
    result = sb.table("competitors").select("name, normalized_name, first_seen_date, last_seen_date, times_seen").order("first_seen_date").execute()
    return result.data
