"""FaceAttend API — register faces and mark attendance via recognition."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.attendance import list_attendance, mark_present
from app.face_service import register_face, recognize_face

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

app = FastAPI(
    title="FaceAttend API",
    description="Register student faces and mark attendance from uploaded photos.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _save_upload(file: UploadFile) -> Path:
    suffix = Path(file.filename or "image.jpg").suffix or ".jpg"
    dest = UPLOAD_DIR / f"{uuid.uuid4()}{suffix}"
    with dest.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return dest


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/register/{student_id}")
async def register_student(student_id: str, file: UploadFile = File(...)):
    path = _save_upload(file)
    try:
        return register_face(student_id, path)
    finally:
        path.unlink(missing_ok=True)


@app.post("/recognize")
async def recognize(file: UploadFile = File(...)):
    path = _save_upload(file)
    try:
        return recognize_face(path)
    finally:
        path.unlink(missing_ok=True)


@app.post("/attendance/mark")
async def mark_attendance(
    file: UploadFile = File(...),
    course: str | None = Query(None, description="Optional course or session name"),
):
    path = _save_upload(file)
    try:
        result = recognize_face(path)
        if result.get("status") != "success":
            return result
        record = mark_present(result["student_id"], course=course)
        return {"status": "success", **result, "attendance": record}
    finally:
        path.unlink(missing_ok=True)


@app.get("/attendance")
def get_attendance(limit: int = Query(100, ge=1, le=1000)):
    return {"records": list_attendance(limit=limit)}


@app.get("/students")
def list_students():
    from app.face_service import load_encodings

    return {"students": sorted(load_encodings().keys())}
