"""
Train an OpenCV LBPH face recognizer from dataset/<student>/ images.
Image filenames should be numeric (e.g. 0.jpg, 1.jpg) — used as class IDs.

Usage:
  python scripts/train_lbph.py
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

DATASET_PATH = Path(os.getenv("DATASET_PATH", "dataset"))
MODEL_PATH = Path(os.getenv("MODEL_PATH", "data/trainer.yml"))


def get_images_and_labels(dataset_path: Path):
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    face_samples = []
    ids = []

    for student_dir in sorted(dataset_path.iterdir()):
        if not student_dir.is_dir():
            continue
        for image_path in sorted(student_dir.iterdir()):
            if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            try:
                label = int(image_path.stem)
            except ValueError:
                continue

            gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
            if gray is None:
                continue

            faces = face_cascade.detectMultiScale(gray)
            for (x, y, w, h) in faces:
                face_samples.append(gray[y : y + h, x : x + w])
                ids.append(label)

    return face_samples, np.array(ids, dtype=np.int32)


def main() -> None:
    if not DATASET_PATH.exists():
        raise SystemExit(f"Dataset folder not found: {DATASET_PATH}")

    faces, ids = get_images_and_labels(DATASET_PATH)
    if len(faces) == 0:
        raise SystemExit("No face samples found. Add images under dataset/<name>/")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, ids)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    recognizer.save(str(MODEL_PATH))
    print(f"Trained on {len(faces)} samples. Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
