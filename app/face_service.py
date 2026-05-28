"""Face registration and recognition using face_recognition encodings."""

from __future__ import annotations

import json
import os
from pathlib import Path

import face_recognition
import numpy as np

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
ENCODINGS_PATH = DATA_DIR / "face_encodings.json"
DEFAULT_TOLERANCE = float(os.getenv("FACE_TOLERANCE", "0.5"))


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_encodings() -> dict[str, list[float]]:
    if ENCODINGS_PATH.exists():
        with ENCODINGS_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_encodings(encodings: dict[str, list[float]]) -> None:
    _ensure_data_dir()
    with ENCODINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(encodings, f, indent=2)


def register_face(student_id: str, image_path: str | Path) -> dict:
    image = face_recognition.load_image_file(str(image_path))
    encodings = face_recognition.face_encodings(image)

    if not encodings:
        return {"status": "error", "message": "No face detected in image"}

    known = load_encodings()
    known[student_id] = encodings[0].tolist()
    save_encodings(known)
    return {"status": "success", "message": "Face registered", "student_id": student_id}


def recognize_face(
    image_path: str | Path,
    tolerance: float | None = None,
) -> dict:
    tolerance = DEFAULT_TOLERANCE if tolerance is None else tolerance
    image = face_recognition.load_image_file(str(image_path))
    encodings = face_recognition.face_encodings(image)

    if not encodings:
        return {"status": "error", "message": "No face detected in image"}

    known = load_encodings()
    if not known:
        return {"status": "error", "message": "No students registered yet"}

    query = encodings[0]
    best_id: str | None = None
    best_distance = float("inf")

    for student_id, known_encoding in known.items():
        distances = face_recognition.face_distance(
            [np.array(known_encoding)], query
        )
        if distances[0] < best_distance:
            best_distance = float(distances[0])
            best_id = student_id

    if best_id is not None and best_distance <= tolerance:
        return {
            "status": "success",
            "student_id": best_id,
            "confidence": round(1.0 - best_distance, 3),
        }

    return {"status": "error", "message": "Face not recognized"}
