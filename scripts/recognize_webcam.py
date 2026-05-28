"""
Live face recognition from webcam using an OpenCV LBPH model.
Train first with: python scripts/train_lbph.py

Usage:
  python scripts/recognize_webcam.py
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2

MODEL_PATH = Path(os.getenv("MODEL_PATH", "data/trainer.yml"))
DATASET_PATH = Path(os.getenv("DATASET_PATH", "dataset"))


def build_id_map(dataset_path: Path) -> dict[int, str]:
    """Map numeric IDs (from filenames) to student folder names."""
    id_map: dict[int, str] = {}
    for student_name in sorted(dataset_path.iterdir()):
        if not student_name.is_dir():
            continue
        for image in student_name.iterdir():
            if image.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                try:
                    numeric_id = int(image.stem)
                    id_map[numeric_id] = student_name.name
                except ValueError:
                    pass
    return id_map


def main() -> None:
    if not MODEL_PATH.exists():
        raise SystemExit(f"Model not found at {MODEL_PATH}. Run scripts/train_lbph.py first.")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(str(MODEL_PATH))

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    id_map = build_id_map(DATASET_PATH) if DATASET_PATH.exists() else {}

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise SystemExit("Could not open webcam.")

    print("Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)

        for (x, y, w, h) in faces:
            id_, conf = recognizer.predict(gray[y : y + h, x : x + w])
            label = id_map.get(id_, str(id_))
            color = (0, 255, 0) if conf < 70 else (0, 0, 255)
            cv2.putText(
                frame,
                f"{label} ({conf:.0f})",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

        cv2.imshow("Face Recognition", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
