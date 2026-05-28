"""Simple attendance log persisted as JSON."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
ATTENDANCE_PATH = DATA_DIR / "attendance.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_records() -> list[dict]:
    if ATTENDANCE_PATH.exists():
        with ATTENDANCE_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_records(records: list[dict]) -> None:
    _ensure_data_dir()
    with ATTENDANCE_PATH.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def mark_present(student_id: str, course: str | None = None) -> dict:
    record = {
        "student_id": student_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "course": course,
    }
    records = _load_records()
    records.append(record)
    _save_records(records)
    return record


def list_attendance(limit: int = 100) -> list[dict]:
    records = _load_records()
    return records[-limit:]
