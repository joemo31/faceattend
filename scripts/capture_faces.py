"""
Capture face images from a webcam into dataset/<student_name>/.
Run locally (not inside Docker unless the container has camera access).

Usage:
  python scripts/capture_faces.py
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import cv2

DATASET_PATH = Path(os.getenv("DATASET_PATH", "dataset"))
DEFAULT_COUNT = int(os.getenv("CAPTURE_COUNT", "30"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture face images for training.")
    parser.add_argument("--name", help="Student name (folder under dataset/)")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Images to capture")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index")
    args = parser.parse_args()

    student_name = (args.name or input("Enter student name: ")).strip()
    if not student_name:
        raise SystemExit("Student name is required.")

    student_dir = DATASET_PATH / student_name
    student_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera {args.camera}")

    count = 0
    print(f"Capturing up to {args.count} images. Press 'q' to stop early.")

    while count < args.count:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cv2.imshow("Capture Images (press q to quit)", gray)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

        file_path = student_dir / f"{count}.jpg"
        cv2.imwrite(str(file_path), gray)
        count += 1

    cap.release()
    cv2.destroyAllWindows()
    print(f"Captured {count} images for {student_name} in {student_dir}")


if __name__ == "__main__":
    main()
