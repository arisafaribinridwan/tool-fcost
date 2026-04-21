from __future__ import annotations

from types import SimpleNamespace

from app.ui.main_window import DesktopApp


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

    def configure(self, *, state):
        self.state = state


class DummyThread:
    def __init__(self, alive: bool):
        self._alive = alive

    def is_alive(self) -> bool:
        return self._alive


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
