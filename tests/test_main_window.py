from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

from app.services import PreflightResult
from app.ui.main_window import DesktopApp, _parse_dropped_files


class DummyVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class DummyButton:
    def __init__(self):
        self.state = None

    def configure(self, *, state=None, **kwargs):
        if state is not None:
            self.state = state


class DummyThread:
    def __init__(self, alive: bool):
        self._alive = alive

    def is_alive(self) -> bool:
        return self._alive


class DummyJob:
    def __init__(self, job_id: str, label: str = "Report Bulanan"):
        self.id = job_id
        self.label = label
        self.is_valid = True
        self.config_path = Path("config.yaml")
        self.config_file = "config.yaml"
        self.master_files = ("master.xlsx",)


def test_can_start_new_session_only_after_terminal_status():
    app = DesktopApp.__new__(DesktopApp)
    app._worker_thread = None
    app.status_var = DummyVar("Status: Sukses")

    assert app._can_start_new_session() is True

    app.status_var.set("Status: Idle")
    assert app._can_start_new_session() is False

    app.status_var.set("Status: Gagal")
    app._worker_thread = DummyThread(True)
    assert app._can_start_new_session() is False


def test_update_execute_state_gates_session_reset_button():
    app = DesktopApp.__new__(DesktopApp)
    app._worker_thread = None
    app._preflight_thread = None
    app.source_path = None
    app._preflight_result = None
    app.status_var = DummyVar("Status: Sukses")
    app.execute_button = DummyButton()
    app.start_new_session_button = DummyButton()
    app._selected_job = lambda: None

    DesktopApp._update_execute_state(app)

    assert app.execute_button.state == "disabled"
    assert app.start_new_session_button.state == "normal"


def test_start_new_session_resets_ui_state_without_touching_outputs(tmp_path):
    app = DesktopApp.__new__(DesktopApp)
    app.source_path = tmp_path / "source.csv"
    app.source_var = DummyVar(str(app.source_path))
    app.preflight_status_var = DummyVar("Preflight: Ready")
    app.preflight_summary_var = DummyVar("siap")
    app.status_var = DummyVar("Status: Sukses")
    app.last_output_var = DummyVar(str(tmp_path / "outputs" / "hasil.xlsx"))
    app._preflight_request_id = 2
    app._latest_preflight_request_id = 2
    app._active_preflight_request_id = 2
    app._preflight_result = object()
    app._worker_queue = SimpleNamespace()
    app._worker_thread = None
    app.execute_button = DummyButton()
    app.start_new_session_button = DummyButton()
    reset_calls: list[str] = []
    log_messages: list[str] = []

    output_path = tmp_path / "outputs" / "hasil.xlsx"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("existing", encoding="utf-8")

    app._can_start_new_session = lambda: True
    app._reset_progress_state = lambda: reset_calls.append("progress")
    app._set_status = lambda text: app.status_var.set(f"Status: {text}")
    app._clear_log_box = lambda: reset_calls.append("log")
    app._append_log = log_messages.append
    app._update_execute_state = lambda: reset_calls.append("execute")
    app.refresh_jobs = lambda initial=False: reset_calls.append(f"refresh:{initial}")

    DesktopApp._start_new_session(app)

    assert app.source_path is None
    assert app.source_var.get() == ""
    assert app._preflight_result is None
    assert app.preflight_status_var.get() == "Preflight: Belum dicek"
    assert app.preflight_summary_var.get() == "Pilih source dan pekerjaan untuk memulai pemeriksaan otomatis."
    assert app.status_var.get() == "Status: Idle"
    assert app.last_output_var.get() == "-"
    assert output_path.exists()
    assert "refresh:False" in reset_calls
    assert "progress" in reset_calls
    assert "log" in reset_calls
    assert "execute" in reset_calls
    assert log_messages == ["Sesi baru dimulai."]


def _make_hint_app() -> DesktopApp:
    app = DesktopApp.__new__(DesktopApp)
    app.job_by_label = {}
    app.selected_job_var = DummyVar("")
    app.source_path = None
    app._preflight_result = None
    app._preflight_thread = None
    app._worker_thread = None
    app.status_var = DummyVar("Status: Idle")
    app.preflight_status_var = DummyVar("Preflight: Belum dicek")
    app.primary_hint_var = DummyVar()
    app.execute_hint_var = DummyVar()
    app._selected_job = lambda: None
    return app


def _make_summary_app() -> DesktopApp:
    app = DesktopApp.__new__(DesktopApp)
    app.paths = SimpleNamespace(project_root=Path("."))
    app.source_path = Path("source.xlsx")
    app.job_summary_var = DummyVar()
    app._last_run_context = None
    app._preflight_result = PreflightResult(status="Ready", findings=(), output_path=None)
    return app


def test_update_hints_at_startup_without_valid_job():
    app = _make_hint_app()

    DesktopApp._update_hints(app)

    assert app.primary_hint_var.get() == (
        "Belum ada pekerjaan valid. Cek file configs/job_profiles.yaml dan config yang dirujuk."
    )
    assert app.execute_hint_var.get() == (
        "Tambahkan atau perbaiki pekerjaan valid sebelum menjalankan execute."
    )


def test_update_hints_when_source_not_selected():
    app = _make_hint_app()
    app.job_by_label = {"Report Bulanan": DummyJob("report-bulanan")}
    app.selected_job_var = DummyVar("Report Bulanan")
    app._selected_job = lambda: app.job_by_label["Report Bulanan"]

    DesktopApp._update_hints(app)

    assert app.primary_hint_var.get() == "Pilih source file untuk pekerjaan yang aktif."
    assert app.execute_hint_var.get() == "Pilih source terlebih dahulu."


def test_update_hints_when_preflight_blocked():
    app = _make_hint_app()
    app.job_by_label = {"Report Bulanan": DummyJob("report-bulanan")}
    app.selected_job_var = DummyVar("Report Bulanan")
    app.source_path = Path("source.xlsx")
    app._selected_job = lambda: app.job_by_label["Report Bulanan"]
    app._preflight_result = PreflightResult(status="Blocked", findings=(), output_path=None)
    app.preflight_status_var = DummyVar("Preflight: Blocked")

    DesktopApp._update_hints(app)

    assert app.primary_hint_var.get() == (
        "Execute dinonaktifkan karena masih ada error preflight. Lihat ringkasan preflight atau log untuk detail."
    )
    assert app.execute_hint_var.get() == (
        "Execute dinonaktifkan sampai semua error preflight diselesaikan."
    )


def test_update_hints_when_ready_to_execute():
    app = _make_hint_app()
    app.job_by_label = {"Report Bulanan": DummyJob("report-bulanan")}
    app.selected_job_var = DummyVar("Report Bulanan")
    app.source_path = Path("source.xlsx")
    app._selected_job = lambda: app.job_by_label["Report Bulanan"]
    app._preflight_result = PreflightResult(status="Ready", findings=(), output_path=None)
    app.preflight_status_var = DummyVar("Preflight: Ready")

    DesktopApp._update_hints(app)

    assert app.primary_hint_var.get() == "Source siap diproses. Jalankan Execute untuk membuat output."
    assert app.execute_hint_var.get() == "Execute siap dijalankan."


def test_update_hints_after_success_and_failure():
    app = _make_hint_app()
    app.job_by_label = {"Report Bulanan": DummyJob("report-bulanan")}

    app.status_var.set("Status: Sukses")
    DesktopApp._update_hints(app)
    assert app.primary_hint_var.get() == "Proses selesai. Periksa Job Summary atau buka folder outputs."

    app.status_var.set("Status: Gagal")
    DesktopApp._update_hints(app)
    assert app.primary_hint_var.get() == (
        "Proses gagal. Periksa log untuk detail lalu perbaiki source atau config aktif."
    )


def test_job_summary_empty_at_startup():
    app = _make_summary_app()

    DesktopApp._set_job_summary_idle(app)

    assert app.job_summary_var.get() == "Belum ada proses yang selesai."


def test_job_summary_success_is_filled():
    app = _make_summary_app()
    job = DummyJob("report-bulanan")
    result = SimpleNamespace(
        output_path=Path("outputs/hasil.xlsx"),
        sheets_written=2,
        duration_ms=1800,
    )

    DesktopApp._set_job_summary_success(app, job, result)

    summary = app.job_summary_var.get()
    assert "Status: Sukses" in summary
    assert "Pekerjaan: Report Bulanan" in summary
    assert "Source: source.xlsx" in summary
    assert "Durasi: 1.8 detik" in summary
    assert "Sheet output: 2" in summary
    assert f"Output: {result.output_path}" in summary
    assert "Preflight: 0 error, 0 warning, 0 info" in summary


def test_job_summary_failure_shows_failed_status_without_output():
    app = _make_summary_app()
    app._last_run_context = {
        "job_label": "Report Bulanan",
        "source_name": "source.xlsx",
        "duration_ms": None,
    }

    DesktopApp._set_job_summary_failure(app, "gagal total")

    summary = app.job_summary_var.get()
    assert "Status: Gagal" in summary
    assert "Pekerjaan: Report Bulanan" in summary
    assert "Source: source.xlsx" in summary
    assert "Output: -" in summary
    assert "Error: gagal total" in summary


def test_start_new_session_clears_job_summary():
    app = DesktopApp.__new__(DesktopApp)
    app._last_run_context = {"job_label": "lama"}
    app.job_summary_var = DummyVar("ada isi")

    DesktopApp._set_job_summary_idle(app)

    assert app.job_summary_var.get() == "Belum ada proses yang selesai."


def test_parse_dropped_files_supports_single_and_braced_paths():
    assert _parse_dropped_files(r"C:\Data\source.xlsx") == (r"C:\Data\source.xlsx",)
    assert _parse_dropped_files(r"{C:\Data Folder\source.xlsx}") == (
        r"C:\Data Folder\source.xlsx",
    )


def test_handle_dropped_source_rejects_multiple_files(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    logs: list[str] = []
    app._append_log = logs.append

    result = DesktopApp._handle_dropped_source(
        app,
        r"{C:\Data\one.xlsx} {C:\Data\two.xlsx}",
    )

    assert result is False
    assert logs == ["Drop source ditolak: hanya satu file yang boleh dijatuhkan."]


def test_handle_dropped_source_rejects_invalid_extension(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    logs: list[str] = []
    app._append_log = logs.append
    monkeypatch.setattr("app.ui.main_window.validate_source_file", lambda _path: ["format tidak didukung"])

    result = DesktopApp._handle_dropped_source(app, r"C:\Data\source.txt")

    assert result is False
    assert logs == ["Drop source invalid: format tidak didukung"]


def test_handle_dropped_source_rejects_missing_file(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    logs: list[str] = []
    app._append_log = logs.append
    monkeypatch.setattr("app.ui.main_window.validate_source_file", lambda _path: ["file tidak ditemukan"])

    result = DesktopApp._handle_dropped_source(app, r"C:\Data\missing.xlsx")

    assert result is False
    assert logs == ["Drop source invalid: file tidak ditemukan"]


def test_handle_dropped_source_applies_valid_file(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    calls: list[tuple[Path, str]] = []
    monkeypatch.setattr("app.ui.main_window.validate_source_file", lambda _path: [])
    app._apply_source_path = lambda source_path, *, log_prefix: calls.append((source_path, log_prefix))

    result = DesktopApp._handle_dropped_source(app, r"{C:\Data Folder\source.xlsx}")

    assert result is True
    assert calls == [(Path(r"C:\Data Folder\source.xlsx"), "Source dijatuhkan")]
