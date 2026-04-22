from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

from app.services import PreflightResult
from app.services.session_state_service import SessionState
from app.ui.main_window import PIPELINE_STEP_ORDER, DesktopApp


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


class DummyGridWidget:
    def __init__(self):
        self.hidden = False

    def grid_remove(self):
        self.hidden = True

    def grid(self):
        self.hidden = False


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


def test_clear_source_resets_preflight_and_updates_actions(tmp_path):
    app = DesktopApp.__new__(DesktopApp)
    app.source_path = tmp_path / "source.csv"
    app.source_var = DummyVar(str(app.source_path))
    app._preflight_request_id = 3
    app._latest_preflight_request_id = 3
    app._active_preflight_request_id = 3
    calls: list[str] = []
    logs: list[str] = []
    app._set_preflight_idle = lambda: calls.append("preflight")
    app._persist_session_state = lambda: calls.append("persist")
    app._append_log = logs.append
    app._update_execute_state = lambda: calls.append("execute")
    app._update_hints = lambda: calls.append("hints")
    app._update_source_actions = lambda: calls.append("actions")

    DesktopApp._clear_source(app)

    assert app.source_path is None
    assert app.source_var.get() == ""
    assert app._latest_preflight_request_id == 4
    assert app._active_preflight_request_id is None
    assert calls == ["preflight", "persist", "execute", "hints", "actions"]
    assert logs == ["Source dibersihkan dari sesi aktif."]


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
    assert app.primary_hint_var.get() == "Proses selesai. Periksa output terakhir atau buka folder outputs."

    app.status_var.set("Status: Gagal")
    DesktopApp._update_hints(app)
    assert app.primary_hint_var.get() == (
        "Proses gagal. Periksa log untuk detail lalu perbaiki source atau config aktif."
    )


def test_refresh_last_session_info_uses_real_saved_session(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    app.paths = SimpleNamespace(project_root=Path("."))
    app.last_session_info_var = DummyVar()
    app.last_session_info_label = DummyGridWidget()

    monkeypatch.setattr(
        "app.ui.main_window.load_session_state",
        lambda _root: SessionState(
            version=1,
            last_job_id="report-bulanan",
            last_source_path=Path("C:/Data/source.xlsx"),
            window_geometry=None,
            updated_at="2026-04-22T22:40:00",
        ),
    )

    DesktopApp._refresh_last_session_info(app)

    assert app.last_session_info_var.get() == (
        "Sesi terakhir tersedia. Job terakhir: report-bulanan | "
        "Source terakhir: source.xlsx | Tersimpan: 2026-04-22T22:40:00"
    )
    assert app.last_session_info_label.hidden is False


def test_refresh_last_session_info_hides_block_when_session_has_no_job_or_source(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    app.paths = SimpleNamespace(project_root=Path("."))
    app.last_session_info_var = DummyVar("awal")
    app.last_session_info_label = DummyGridWidget()

    monkeypatch.setattr(
        "app.ui.main_window.load_session_state",
        lambda _root: SessionState(
            version=1,
            last_job_id=None,
            last_source_path=None,
            window_geometry=None,
            updated_at="2026-04-22T22:40:00",
        ),
    )

    DesktopApp._refresh_last_session_info(app)

    assert app.last_session_info_var.get() == ""
    assert app.last_session_info_label.hidden is True


def test_persist_session_state_saves_selected_job_and_source(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    app.paths = SimpleNamespace(project_root=Path("."))
    app._restoring_session = False
    app.source_path = Path("source.xlsx")
    app.last_session_info_var = DummyVar()
    app.last_session_info_label = DummyGridWidget()
    app._selected_job_id = lambda: "report-bulanan"
    app._current_window_geometry = lambda: "1120x720"

    captured: dict[str, object] = {}

    def fake_save_session_state(runtime_root, *, last_job_id, last_source_path, window_geometry):
        captured["runtime_root"] = runtime_root
        captured["last_job_id"] = last_job_id
        captured["last_source_path"] = last_source_path
        captured["window_geometry"] = window_geometry
        return None

    monkeypatch.setattr("app.ui.main_window.save_session_state", fake_save_session_state)
    monkeypatch.setattr("app.ui.main_window.load_session_state", lambda _root: None)

    DesktopApp._persist_session_state(app)

    assert captured == {
        "runtime_root": Path("."),
        "last_job_id": "report-bulanan",
        "last_source_path": Path("source.xlsx"),
        "window_geometry": "1120x720",
    }


def test_pipeline_step_order_matches_design_brief():
    assert PIPELINE_STEP_ORDER == (
        ("load_config", "Load config"),
        ("copy_source", "Copy source"),
        ("read_source", "Read source"),
        ("load_master", "Load master"),
        ("transform", "Transform"),
        ("build_output", "Build output"),
        ("write_output", "Write output"),
    )


def test_format_pipeline_step_lines_uses_defined_order():
    app = DesktopApp.__new__(DesktopApp)

    result = DesktopApp._format_pipeline_step_lines(app)

    assert result == (
        "- Load config\n"
        "- Copy source\n"
        "- Read source\n"
        "- Load master\n"
        "- Transform\n"
        "- Build output\n"
        "- Write output"
    )


def test_resolve_visual_state_prefers_running():
    app = _make_hint_app()
    app._worker_thread = DummyThread(True)
    app._preflight_thread = DummyThread(True)
    app._preflight_result = PreflightResult(status="Ready", findings=(), output_path=None)
    app.status_var = DummyVar("Status: Idle")

    assert DesktopApp._resolve_visual_state(app) == "running"


def test_resolve_visual_state_reports_blocked_and_ready():
    blocked_app = _make_hint_app()
    blocked_app._preflight_result = PreflightResult(status="Blocked", findings=(), output_path=None)
    blocked_app.preflight_status_var = DummyVar("Preflight: Blocked")
    assert DesktopApp._resolve_visual_state(blocked_app) == "blocked"

    ready_app = _make_hint_app()
    ready_app._preflight_result = PreflightResult(status="Ready", findings=(), output_path=None)
    ready_app.preflight_status_var = DummyVar("Preflight: Ready")
    assert DesktopApp._resolve_visual_state(ready_app) == "ready"


def test_resolve_visual_state_reports_success_failed_and_idle():
    success_app = _make_hint_app()
    success_app.status_var = DummyVar("Status: Sukses")
    assert DesktopApp._resolve_visual_state(success_app) == "success"

    failed_app = _make_hint_app()
    failed_app.status_var = DummyVar("Status: Gagal")
    assert DesktopApp._resolve_visual_state(failed_app) == "failed"

    idle_app = _make_hint_app()
    assert DesktopApp._resolve_visual_state(idle_app) == "idle"
