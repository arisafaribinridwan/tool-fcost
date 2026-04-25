from __future__ import annotations

from pathlib import Path
from queue import Queue
from types import SimpleNamespace

from app.services import PreflightFinding, PreflightResult
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
        self.last_kwargs: dict[str, object] = {}

    def configure(self, **kwargs):
        self.last_kwargs = kwargs
        if "state" in kwargs:
            self.state = kwargs["state"]


class DummyLabel:
    def __init__(self):
        self.text = None

    def configure(self, **kwargs):
        if "text" in kwargs:
            self.text = kwargs["text"]


class DummyTextBox:
    def __init__(self):
        self.lines: list[str] = []
        self.last_seen = None

    def insert(self, _where: str, text: str):
        self.lines.append(text)

    def see(self, where: str):
        self.last_seen = where


class DummyThread:
    def __init__(self, alive: bool):
        self._alive = alive

    def is_alive(self) -> bool:
        return self._alive


def _make_job(config_path: Path | None = None):
    return SimpleNamespace(config_path=config_path, config_file="config.yaml", is_valid=True)


def test_selected_job_returns_selected_record():
    app = DesktopApp.__new__(DesktopApp)
    app.job_records = {"Report": _make_job(Path("cfg.yaml"))}
    app.job_selection = DummyVar("Report")

    selected = DesktopApp._selected_job(app)

    assert selected is app.job_records["Report"]


def test_on_job_changed_without_job_resets_state():
    app = DesktopApp.__new__(DesktopApp)
    app.config_value_label = DummyLabel()
    app._preflight_result = object()
    calls: list[bool] = []
    app._selected_job = lambda: None
    app._set_execute_ready = lambda value: calls.append(value)

    DesktopApp._on_job_changed(app)

    assert app.config_value_label.text == "-"
    assert app._preflight_result is None
    assert calls == [False]


def test_on_job_changed_with_job_updates_config_and_runs_preflight():
    app = DesktopApp.__new__(DesktopApp)
    app.config_value_label = DummyLabel()
    app._selected_job = lambda: _make_job(Path("cfg.yaml"))
    called: list[bool] = []
    app._run_preflight = lambda: called.append(True)

    DesktopApp._on_job_changed(app)

    assert app.config_value_label.text == "config.yaml"
    assert called == [True]


def test_set_execute_ready_updates_button_style():
    app = DesktopApp.__new__(DesktopApp)
    app.execute_btn = DummyButton()

    DesktopApp._set_execute_ready(app, True)
    assert app.execute_btn.state == "normal"
    assert app.execute_btn.last_kwargs["fg_color"] == "#0f172a"

    DesktopApp._set_execute_ready(app, False)
    assert app.execute_btn.state == "disabled"
    assert app.execute_btn.last_kwargs["fg_color"] == "#cbd5e1"


def test_run_preflight_skips_when_source_or_job_missing():
    app = DesktopApp.__new__(DesktopApp)
    app.selected_source_path = None
    app._selected_job = lambda: _make_job(Path("cfg.yaml"))
    app._preflight_result = object()
    calls: list[bool] = []
    app._set_execute_ready = lambda value: calls.append(value)

    DesktopApp._run_preflight(app)

    assert app._preflight_result is None
    assert calls == [False]


def test_run_preflight_logs_findings_and_enables_execute(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    app.paths = SimpleNamespace(project_root=Path("."))
    app.selected_source_path = Path("source.csv")
    app._selected_job = lambda: _make_job(Path("config.yaml"))
    logs: list[str] = []
    states: list[bool] = []
    app.add_log = logs.append
    app._set_execute_ready = lambda value: states.append(value)

    monkeypatch.setattr(
        "app.ui.main_window.run_preflight",
        lambda **kwargs: PreflightResult(
            status="Ready",
            findings=(PreflightFinding(severity="warning", summary="cek data"),),
            output_path=None,
        ),
    )

    DesktopApp._run_preflight(app)

    assert logs[0] == "Menjalankan preflight..."
    assert "Preflight [warning]: cek data" in logs
    assert logs[-1] == "Preflight selesai: Ready"
    assert states == [False, True]


def test_run_preflight_handles_error(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    app.paths = SimpleNamespace(project_root=Path("."))
    app.selected_source_path = Path("source.csv")
    app._selected_job = lambda: _make_job(Path("config.yaml"))
    logs: list[str] = []
    app.add_log = logs.append
    states: list[bool] = []
    app._set_execute_ready = lambda value: states.append(value)
    shown: list[tuple[str, str]] = []

    monkeypatch.setattr("app.ui.main_window.run_preflight", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr("app.ui.main_window.messagebox.showerror", lambda title, message: shown.append((title, message)))

    DesktopApp._run_preflight(app)

    assert states == [False]
    assert app._preflight_result is None
    assert logs[-1] == "Preflight gagal: boom"
    assert shown and shown[0][0] == "Preflight gagal"


def test_select_source_file_cancelled(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    app.paths = SimpleNamespace(project_root=Path("."))
    logs: list[str] = []
    app.add_log = logs.append

    monkeypatch.setattr("app.ui.main_window.select_source_file", lambda _root: None)

    DesktopApp.select_source_file(app)

    assert logs == ["Pemilihan source dibatalkan."]


def test_select_source_file_invalid(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    app.paths = SimpleNamespace(project_root=Path("."))
    logs: list[str] = []
    app.add_log = logs.append
    app.source_btn = DummyButton()
    called: list[bool] = []
    app._run_preflight = lambda: called.append(True)
    shown: list[str] = []

    monkeypatch.setattr("app.ui.main_window.select_source_file", lambda _root: "source.csv")
    monkeypatch.setattr("app.ui.main_window.validate_source_file", lambda _path: ["error A", "error B"])
    monkeypatch.setattr("app.ui.main_window.messagebox.showerror", lambda _title, message: shown.append(message))

    DesktopApp.select_source_file(app)

    assert called == []
    assert logs == ["Source invalid: error A\nerror B"]
    assert shown


def test_select_source_file_valid_runs_preflight(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    app.paths = SimpleNamespace(project_root=Path("."))
    logs: list[str] = []
    app.add_log = logs.append
    app.source_btn = DummyButton()
    called: list[bool] = []
    app._run_preflight = lambda: called.append(True)

    monkeypatch.setattr("app.ui.main_window.select_source_file", lambda _root: "source.csv")
    monkeypatch.setattr("app.ui.main_window.validate_source_file", lambda _path: [])

    DesktopApp.select_source_file(app)

    assert app.selected_source_path == Path("source.csv")
    assert app.source_btn.last_kwargs["text"] == "source.csv"
    assert logs == ["Source dipilih: source.csv"]
    assert called == [True]


def test_add_log_event_blocks_when_worker_active():
    app = DesktopApp.__new__(DesktopApp)
    app._worker_thread = DummyThread(True)
    logs: list[str] = []
    app.add_log = logs.append

    DesktopApp.add_log_event(app)

    assert logs == ["Proses masih berjalan."]


def test_add_log_event_requires_source(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    app._worker_thread = None
    app.selected_source_path = None
    app._selected_job = lambda: _make_job(Path("cfg.yaml"))
    shown: list[tuple[str, str]] = []

    monkeypatch.setattr("app.ui.main_window.messagebox.showwarning", lambda title, message: shown.append((title, message)))

    DesktopApp.add_log_event(app)

    assert shown == [("Input belum lengkap", "Pilih source terlebih dahulu.")]


def test_add_log_event_requires_valid_job(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    app._worker_thread = None
    app.selected_source_path = Path("source.csv")
    app._selected_job = lambda: None
    shown: list[tuple[str, str]] = []

    monkeypatch.setattr("app.ui.main_window.messagebox.showwarning", lambda title, message: shown.append((title, message)))

    DesktopApp.add_log_event(app)

    assert shown == [("Input belum lengkap", "Pilih pekerjaan valid terlebih dahulu.")]


def test_poll_worker_events_handles_success_and_done():
    app = DesktopApp.__new__(DesktopApp)
    app.paths = SimpleNamespace(project_root=Path("."))
    app._worker_queue = Queue()
    app._worker_queue.put(("log", "langkah 1"))
    app._worker_queue.put(("success", SimpleNamespace(output_path=Path("out.xlsx"), sheets_written=2)))
    app._worker_queue.put(("done", None))
    app._worker_thread = DummyThread(False)
    app._preflight_result = object()
    logs: list[str] = []
    app.add_log = logs.append
    states: list[bool] = []
    app._set_execute_ready = lambda value: states.append(value)

    DesktopApp._poll_worker_events(app)

    assert logs[0] == "langkah 1"
    assert logs[1] == "Output berhasil dibuat (2 sheet): out.xlsx"
    assert app._worker_queue is None
    assert app._worker_thread is None
    assert app._preflight_result is None
    assert states == [False]


def test_poll_worker_events_handles_error_and_done(monkeypatch):
    app = DesktopApp.__new__(DesktopApp)
    app.paths = SimpleNamespace(project_root=Path("."))
    app._worker_queue = Queue()
    app._worker_queue.put(("error", "boom"))
    app._worker_queue.put(("done", None))
    app._worker_thread = DummyThread(False)
    logs: list[str] = []
    app.add_log = logs.append
    app._set_execute_ready = lambda _value: None
    shown: list[tuple[str, str]] = []

    monkeypatch.setattr("app.ui.main_window.messagebox.showerror", lambda title, message: shown.append((title, message)))

    DesktopApp._poll_worker_events(app)

    assert logs == ["Error: boom"]
    assert shown and shown[0][0] == "Eksekusi gagal"


def test_poll_worker_events_schedules_next_poll_when_not_done():
    app = DesktopApp.__new__(DesktopApp)
    app._worker_queue = Queue()
    app._worker_queue.put(("log", "jalan"))
    logs: list[str] = []
    app.add_log = logs.append
    scheduled: list[tuple[int, object]] = []
    app.after = lambda delay, callback: scheduled.append((delay, callback))

    DesktopApp._poll_worker_events(app)

    assert logs == ["jalan"]
    assert scheduled and scheduled[0][0] == 120


def test_add_log_writes_timestamped_line():
    app = DesktopApp.__new__(DesktopApp)
    app.paths = SimpleNamespace(project_root=Path("."))
    app.textbox = DummyTextBox()

    DesktopApp.add_log(app, "halo")

    assert len(app.textbox.lines) == 1
    assert "halo" in app.textbox.lines[0]
    assert app.textbox.lines[0].startswith("[")


def test_pipeline_step_order_matches_current_runtime_steps():
    assert PIPELINE_STEP_ORDER == (
        ("load_config", "Load config"),
        ("copy_source", "Copy source"),
        ("read_source", "Read source"),
        ("load_master", "Load master"),
        ("transform", "Transform"),
        ("build_output", "Build output"),
        ("write_output", "Write output"),
    )
