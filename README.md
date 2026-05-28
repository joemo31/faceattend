# FaceAttend

REST API for registering student faces and marking attendance from uploaded photos. Optional local scripts use a webcam and OpenCV LBPH for offline demos.

## How it works

```mermaid
flowchart LR
  subgraph api [Docker API]
    A[Upload photo] --> B[face_recognition]
    B --> C{Match?}
    C -->|yes| D[attendance.json]
    C -->|no| E[Error response]
  end
  subgraph local [Optional local scripts]
    F[Webcam] --> G[capture_faces.py]
    G --> H[dataset/]
    H --> I[train_lbph.py]
    I --> J[recognize_webcam.py]
  end
```

1. **Register** — `POST /register/{student_id}` with a clear face photo. The API stores a 128-dimensional face encoding in `data/face_encodings.json`.
2. **Recognize** — `POST /recognize` with a photo; returns the matched `student_id` and confidence.
3. **Mark attendance** — `POST /attendance/mark` recognizes the face and appends a timestamped record to `data/attendance.json`.

Interactive API docs: **http://localhost:8000/docs**

### Optional local workflow (webcam)

1. `python scripts/capture_faces.py --name "Alice"` — saves grayscale images under `dataset/Alice/`.
2. `python scripts/train_lbph.py` — trains `data/trainer.yml`.
3. `python scripts/recognize_webcam.py` — live recognition from the webcam.

## Quick start with Docker

**Requirements:** [Docker](https://docs.docker.com/get-docker/) and Docker Compose.

```bash
docker compose up --build
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

### Example requests

Register a student:

```bash
curl -X POST "http://localhost:8000/register/student001" \
  -F "file=@photo.jpg"
```

Mark attendance:

```bash
curl -X POST "http://localhost:8000/attendance/mark?course=Math101" \
  -F "file=@photo.jpg"
```

List attendance:

```bash
curl "http://localhost:8000/attendance"
```

## Local development (without Docker)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

On Windows, `face_recognition` / `dlib` may need [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/). Docker is the recommended way to run the API.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `data` | Encodings and attendance storage |
| `UPLOAD_DIR` | `uploads` | Temporary upload directory |
| `FACE_TOLERANCE` | `0.5` | Lower = stricter matching (0.4–0.6 typical) |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

## Project layout

```
faceattend/
├── app/
│   ├── main.py           # FastAPI routes
│   ├── face_service.py   # Register / recognize
│   └── attendance.py     # Attendance log
├── scripts/              # Optional webcam + LBPH tools
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Privacy

Do **not** commit real student photos. `dataset/`, `data/`, and `uploads/` are listed in `.gitignore`.

## License

MIT (adjust as needed for your course or organization).
