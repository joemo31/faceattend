"""FaceAttend desktop app — register faces and mark attendance from one window."""

from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from app.attendance import list_attendance, mark_present
from app.face_service import load_encodings, register_face, recognize_face

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
PREVIEW_SIZE = (640, 480)


class CameraPanel(ttk.LabelFrame):
    """Webcam preview with start/stop controls."""

    def __init__(self, master: tk.Misc, **kwargs) -> None:
        super().__init__(master, text="Camera", padding=8, **kwargs)
        self._cap: cv2.VideoCapture | None = None
        self._running = False
        self._photo: ImageTk.PhotoImage | None = None

        self.preview = ttk.Label(self, text="Camera off", anchor="center")
        self.preview.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 8))

        self.start_btn = ttk.Button(self, text="Start camera", command=self.start)
        self.start_btn.grid(row=1, column=0, sticky="ew", padx=(0, 4))

        self.stop_btn = ttk.Button(self, text="Stop camera", command=self.stop, state="disabled")
        self.stop_btn.grid(row=1, column=1, sticky="ew")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

    def start(self) -> bool:
        if self._running:
            return True
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Camera", "Could not open webcam.")
            return False
        self._cap = cap
        self._running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._tick()
        return True

    def stop(self) -> None:
        self._running = False
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.preview.configure(image="", text="Camera off")
        self._photo = None

    def _tick(self) -> None:
        if not self._running or self._cap is None:
            return
        ok, frame = self._cap.read()
        if ok:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb).resize(PREVIEW_SIZE, Image.Resampling.LANCZOS)
            self._photo = ImageTk.PhotoImage(img)
            self.preview.configure(image=self._photo, text="")
        self.preview.after(30, self._tick)

    def capture_frame(self) -> Path | None:
        if self._cap is None or not self._running:
            messagebox.showwarning("Camera", "Start the camera first.")
            return None
        ok, frame = self._cap.read()
        if not ok:
            messagebox.showerror("Camera", "Could not read from webcam.")
            return None
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        path = UPLOAD_DIR / f"{uuid.uuid4()}.jpg"
        cv2.imwrite(str(path), frame)
        return path


class FaceAttendApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FaceAttend")
        self.minsize(900, 620)
        self._api_thread: threading.Thread | None = None
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(12, 10, 12, 0))
        header.pack(fill="x")
        ttk.Label(header, text="FaceAttend", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(header, text="Start API server", command=self._start_api).pack(side="right")

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self.camera = CameraPanel(body)
        self.camera.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        notebook = ttk.Notebook(body)
        notebook.grid(row=0, column=1, sticky="nsew")

        self._build_register_tab(notebook)
        self._build_attendance_tab(notebook)
        self._build_students_tab(notebook)
        self._build_log_tab(notebook)

        self.status = ttk.Label(self, text="Ready", relief="sunken", anchor="w", padding=(8, 4))
        self.status.pack(fill="x", side="bottom")

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def _build_register_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text="Register")

        ttk.Label(tab, text="Student ID").grid(row=0, column=0, sticky="w")
        self.register_id = ttk.Entry(tab, width=28)
        self.register_id.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        ttk.Button(tab, text="Capture & register", command=self._register_from_camera).grid(
            row=2, column=0, sticky="ew", pady=(0, 6)
        )
        ttk.Button(tab, text="Register from photo file…", command=self._register_from_file).grid(
            row=3, column=0, sticky="ew"
        )
        tab.columnconfigure(0, weight=1)

    def _build_attendance_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text="Mark attendance")

        ttk.Label(tab, text="Course (optional)").grid(row=0, column=0, sticky="w")
        self.course = ttk.Entry(tab, width=28)
        self.course.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        ttk.Button(tab, text="Capture & mark present", command=self._mark_from_camera).grid(
            row=2, column=0, sticky="ew", pady=(0, 6)
        )
        ttk.Button(tab, text="Mark from photo file…", command=self._mark_from_file).grid(
            row=3, column=0, sticky="ew"
        )

        self.last_result = tk.Text(tab, height=8, wrap="word", state="disabled")
        self.last_result.grid(row=4, column=0, sticky="nsew", pady=(12, 0))
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(4, weight=1)

    def _build_students_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text="Students")

        self.students_list = tk.Listbox(tab, height=16)
        self.students_list.pack(fill="both", expand=True)
        ttk.Button(tab, text="Refresh", command=self._refresh_students).pack(fill="x", pady=(8, 0))
        self._refresh_students()

    def _build_log_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text="Attendance log")

        columns = ("student_id", "course", "timestamp")
        self.log_tree = ttk.Treeview(tab, columns=columns, show="headings", height=16)
        self.log_tree.heading("student_id", text="Student")
        self.log_tree.heading("course", text="Course")
        self.log_tree.heading("timestamp", text="Time (UTC)")
        self.log_tree.column("student_id", width=120)
        self.log_tree.column("course", width=120)
        self.log_tree.column("timestamp", width=220)
        self.log_tree.pack(fill="both", expand=True)
        ttk.Button(tab, text="Refresh", command=self._refresh_log).pack(fill="x", pady=(8, 0))
        self._refresh_log()

    def _register_from_camera(self) -> None:
        student_id = self.register_id.get().strip()
        if not student_id:
            messagebox.showwarning("Register", "Enter a student ID.")
            return
        if not self.camera.start():
            return
        path = self.camera.capture_frame()
        if path is None:
            return
        try:
            result = register_face(student_id, path)
        finally:
            path.unlink(missing_ok=True)
        self._handle_register_result(result)

    def _register_from_file(self) -> None:
        student_id = self.register_id.get().strip()
        if not student_id:
            messagebox.showwarning("Register", "Enter a student ID.")
            return
        path = filedialog.askopenfilename(
            title="Select face photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png"), ("All files", "*.*")],
        )
        if not path:
            return
        result = register_face(student_id, path)
        self._handle_register_result(result)

    def _handle_register_result(self, result: dict) -> None:
        if result.get("status") == "success":
            self._set_status(f"Registered {result['student_id']}")
            messagebox.showinfo("Register", f"Registered {result['student_id']}.")
            self.register_id.delete(0, "end")
            self._refresh_students()
        else:
            self._set_status(result.get("message", "Registration failed"))
            messagebox.showerror("Register", result.get("message", "Registration failed"))

    def _mark_from_camera(self) -> None:
        if not self.camera.start():
            return
        path = self.camera.capture_frame()
        if path is None:
            return
        try:
            self._mark_with_image(path)
        finally:
            path.unlink(missing_ok=True)

    def _mark_from_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select face photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png"), ("All files", "*.*")],
        )
        if not path:
            return
        self._mark_with_image(Path(path))

    def _mark_with_image(self, path: Path) -> None:
        result = recognize_face(path)
        course = self.course.get().strip() or None

        if result.get("status") != "success":
            self._show_result(result)
            self._set_status(result.get("message", "Not recognized"))
            messagebox.showerror("Attendance", result.get("message", "Face not recognized"))
            return

        record = mark_present(result["student_id"], course=course)
        payload = {
            "status": "success",
            **result,
            "attendance": record,
        }
        self._show_result(payload)
        self._set_status(f"Marked present: {result['student_id']}")
        messagebox.showinfo(
            "Attendance",
            f"{result['student_id']} marked present\nConfidence: {result.get('confidence')}",
        )
        self._refresh_log()

    def _show_result(self, result: dict) -> None:
        lines = [f"{key}: {value}" for key, value in result.items()]
        text = "\n".join(lines)
        self.last_result.configure(state="normal")
        self.last_result.delete("1.0", "end")
        self.last_result.insert("1.0", text)
        self.last_result.configure(state="disabled")

    def _refresh_students(self) -> None:
        self.students_list.delete(0, "end")
        for student_id in sorted(load_encodings().keys()):
            self.students_list.insert("end", student_id)

    def _refresh_log(self) -> None:
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)
        for record in reversed(list_attendance(limit=200)):
            self.log_tree.insert(
                "",
                "end",
                values=(
                    record.get("student_id", ""),
                    record.get("course") or "",
                    record.get("timestamp", ""),
                ),
            )

    def _start_api(self) -> None:
        if self._api_thread and self._api_thread.is_alive():
            messagebox.showinfo("API", "API server is already running at http://localhost:8000")
            return

        def run_server() -> None:
            import uvicorn

            uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")

        self._api_thread = threading.Thread(target=run_server, daemon=True)
        self._api_thread.start()
        self._set_status("API running at http://localhost:8000/docs")
        messagebox.showinfo("API", "API server started.\nDocs: http://localhost:8000/docs")

    def _on_close(self) -> None:
        self.camera.stop()
        self.destroy()


def main() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app = FaceAttendApp()
    app.mainloop()


if __name__ == "__main__":
    main()
