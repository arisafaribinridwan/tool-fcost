from __future__ import annotations

from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from app import AppPaths
from app.services import (
    JobProfileSummary,
    clear_session_state,
    discover_job_profiles,
    load_config_payload,
    run_pipeline,
    run_preflight,
    validate_source_file,
)
from app.utils import (
    open_in_file_manager,
    sanitize_exception_message,
    sanitize_log_message,
    select_source_file,
)


PIPELINE_STEP_ORDER = (
    ("load_config", "Load config"),
    ("copy_source", "Copy source"),
    ("read_source", "Read source"),
    ("load_master", "Load master"),
    ("transform", "Transform"),
    ("build_output", "Build output"),
    ("write_output", "Write output"),
)

MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


class DesktopApp(ctk.CTk):
    def __init__(self, paths: AppPaths) -> None:
        super().__init__()
        self.paths = paths
        self.asset_dir = Path(__file__).resolve().parents[1] / "assets" / "icons"

        self.selected_source_path: Path | None = None
        self.job_records: dict[str, JobProfileSummary] = {}
        self._worker_queue: Queue[tuple[str, object]] | None = None
        self._worker_thread: Thread | None = None
        self._preflight_result: object | None = None

        self.title("XLS-Flow Automator v2.0")
        self.geometry("1000x700")

        self.grid_columnconfigure(0, minsize=300)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_content()
        self._set_execute_ready(False)

        self._refresh_job_options(initial=True)
        self.add_log("Aplikasi siap digunakan.")

    @staticmethod
    def tint_icon(image_path: Path, rgb_color: tuple[int, int, int]) -> Image.Image:
        icon_source = Image.open(image_path).convert("RGBA")
        tinted_icon = Image.new("RGBA", icon_source.size, (*rgb_color, 0))
        tinted_icon.putalpha(icon_source.getchannel("A"))
        return tinted_icon

    def _build_sidebar(self) -> None:
        self.sidebar_frame = ctk.CTkFrame(
            self,
            width=300,
            corner_radius=0,
            fg_color="#f8fafc",
            border_color="#e2e8f0",
            border_width=1,
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_columnconfigure(0, weight=1)
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="XLS-Flow",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        self.sublogo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="AUTOMATOR V2.0",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="#94a3b8",
        )
        self.sublogo_label.grid(row=1, column=0, padx=22, pady=(0, 20), sticky="w")

        self.step1_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="1. SOURCE INPUT",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#1e293b",
        )
        self.step1_label.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="w")

        self.source_icon = ctk.CTkImage(
            light_image=self.tint_icon(self.asset_dir / "folder-open.png", (148, 163, 184)),
            dark_image=self.tint_icon(self.asset_dir / "folder-open.png", (148, 163, 184)),
            size=(18, 18),
        )
        self.source_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Klik untuk Pilih Source",
            image=self.source_icon,
            compound="top",
            height=104,
            corner_radius=8,
            fg_color="white",
            border_color="#bfdbfe",
            border_width=1,
            text_color="#64748b",
            hover_color="#f8fbff",
            font=ctk.CTkFont(size=14),
            command=self.select_source_file,
        )
        self.source_btn.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")

        self.step2_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.step2_frame.grid(row=4, column=0, padx=20, pady=0, sticky="nsew")
        self.step2_frame.grid_columnconfigure(0, weight=1)

        self.step2_title = ctk.CTkLabel(
            self.step2_frame,
            text="2. JOB SELECTION",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#1e293b",
        )
        self.step2_title.grid(row=0, column=0, pady=(0, 10), sticky="w")

        self.job_inner_frame = ctk.CTkFrame(self.step2_frame, fg_color="transparent")
        self.job_inner_frame.grid(row=1, column=0, sticky="ew")
        self.job_inner_frame.grid_columnconfigure(0, weight=1)

        self.job_selection = tk.StringVar(value="Tidak ada pekerjaan valid")
        self.chevron_down_icon = ctk.CTkImage(
            light_image=self.tint_icon(self.asset_dir / "chevron-down.png", (255, 255, 255)),
            dark_image=self.tint_icon(self.asset_dir / "chevron-down.png", (255, 255, 255)),
            size=(12, 12),
        )
        self.job_select_frame = ctk.CTkFrame(
            self.job_inner_frame,
            fg_color="white",
            corner_radius=8,
            border_color="#dbeafe",
            border_width=1,
        )
        self.job_select_frame.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.job_select_frame.grid_columnconfigure(0, weight=1)

        self.job_option_label = ctk.CTkLabel(
            self.job_select_frame,
            textvariable=self.job_selection,
            text_color="#0f172a",
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        self.job_option_label.grid(row=0, column=0, padx=(12, 8), pady=4, sticky="ew")

        self.job_option_btn = ctk.CTkButton(
            self.job_select_frame,
            text="",
            image=self.chevron_down_icon,
            width=32,
            height=32,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            corner_radius=7,
            command=self.open_job_menu,
        )
        self.job_option_btn.grid(row=0, column=1, padx=4, pady=4)

        self.job_select_frame.bind("<Button-1>", lambda _event: self.open_job_menu())
        self.job_option_label.bind("<Button-1>", lambda _event: self.open_job_menu())

        self.job_menu = tk.Menu(self, tearoff=0, relief="flat", bd=0, activeborderwidth=0)
        self.job_menu.configure(
            background="white",
            foreground="#0f172a",
            activebackground="#eff6ff",
            activeforeground="#0f172a",
        )

        self.refresh_icon = ctk.CTkImage(
            light_image=self.tint_icon(self.asset_dir / "refresh.png", (100, 116, 139)),
            dark_image=self.tint_icon(self.asset_dir / "refresh.png", (100, 116, 139)),
            size=(13, 13),
        )
        self.refresh_btn = ctk.CTkButton(
            self.job_inner_frame,
            text="",
            image=self.refresh_icon,
            width=36,
            height=36,
            fg_color="white",
            border_color="#cbd5e1",
            border_width=1,
            hover_color="#f8fafc",
            command=self._refresh_job_options,
        )
        self.refresh_btn.grid(row=0, column=1)

        self.detail_card = ctk.CTkFrame(
            self.step2_frame,
            fg_color="white",
            border_color="#e2e8f0",
            border_width=1,
            corner_radius=10,
        )
        self.detail_card.grid(row=2, column=0, pady=15, sticky="ew")
        self.detail_card.grid_columnconfigure(0, weight=1)

        self.card_label = ctk.CTkLabel(
            self.detail_card,
            text="DETAIL AKTIF",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="#cbd5e1",
        )
        self.card_label.pack(anchor="w", padx=10, pady=(10, 0))

        self.config_row = ctk.CTkFrame(self.detail_card, fg_color="transparent")
        self.config_row.pack(fill="x", padx=10, pady=(5, 10))

        self.config_title_label = ctk.CTkLabel(
            self.config_row,
            text="Config File:",
            font=ctk.CTkFont(size=10),
            text_color="#94a3b8",
        )
        self.config_title_label.pack(side="left")

        self.config_value_label = ctk.CTkLabel(
            self.config_row,
            text="-",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#0f172a",
        )
        self.config_value_label.pack(side="left", padx=(6, 0))

        self.start_icon = ctk.CTkImage(
            light_image=self.tint_icon(self.asset_dir / "circle-plus.png", (37, 99, 235)),
            dark_image=self.tint_icon(self.asset_dir / "circle-plus.png", (37, 99, 235)),
            size=(14, 14),
        )
        self.start_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="NEW SESSION",
            image=self.start_icon,
            compound="left",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=36,
            fg_color="#eff6ff",
            text_color="#2563eb",
            hover_color="#dbeafe",
            command=self.start_new_session,
        )
        self.start_btn.grid(row=5, column=0, padx=20, pady=(0, 12), sticky="ew")

        self.settings_icon = ctk.CTkImage(
            light_image=self.tint_icon(self.asset_dir / "settings.png", (148, 163, 184)),
            dark_image=self.tint_icon(self.asset_dir / "settings.png", (148, 163, 184)),
            size=(14, 14),
        )
        self.settings_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="Settings",
            image=self.settings_icon,
            compound="left",
            fg_color="transparent",
            height=36,
            text_color="#94a3b8",
            hover_color="#f1f5f9",
            anchor="w",
            command=self.open_settings_window,
        )
        self.settings_btn.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")

    def _build_main_content(self) -> None:
        self.main_content = ctk.CTkFrame(self, fg_color="white", corner_radius=0)
        self.main_content.grid(row=0, column=1, sticky="nsew")
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(1, weight=1)

        self.header_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=30, pady=25, sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="3. Execute & Monitor",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Real-time process status",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w")

        self.btn_group = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.btn_group.grid(row=0, column=1, rowspan=2, sticky="e")

        self.execute_icon = ctk.CTkImage(
            light_image=self.tint_icon(self.asset_dir / "play.png", (255, 255, 255)),
            dark_image=self.tint_icon(self.asset_dir / "play.png", (255, 255, 255)),
            size=(14, 14),
        )
        self.execute_btn = ctk.CTkButton(
            self.btn_group,
            text="EXECUTE",
            image=self.execute_icon,
            compound="left",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#0f172a",
            hover_color="#1e293b",
            height=40,
            width=140,
            command=self.add_log_event,
        )
        self.execute_btn.pack(side="left", padx=5)

        self.folder_icon = ctk.CTkImage(
            light_image=self.tint_icon(self.asset_dir / "folder-open.png", (100, 116, 139)),
            dark_image=self.tint_icon(self.asset_dir / "folder-open.png", (100, 116, 139)),
            size=(14, 14),
        )
        self.folder_btn = ctk.CTkButton(
            self.btn_group,
            text="",
            image=self.folder_icon,
            width=40,
            height=40,
            fg_color="#f1f5f9",
            hover_color="#e2e8f0",
            command=self._open_outputs_dir,
        )
        self.folder_btn.pack(side="left")

        self.console_frame = ctk.CTkFrame(self.main_content, fg_color="#0f172a", corner_radius=25)
        self.console_frame.grid(row=1, column=0, padx=30, pady=(0, 30), sticky="nsew")

        self.terminal_icon = ctk.CTkImage(
            light_image=self.tint_icon(self.asset_dir / "terminal.png", (255, 255, 255)),
            dark_image=self.tint_icon(self.asset_dir / "terminal.png", (255, 255, 255)),
            size=(12, 12),
        )

        self.console_header = ctk.CTkFrame(self.console_frame, fg_color="transparent")
        self.console_header.pack(anchor="w", padx=25, pady=(20, 10))

        self.console_icon_badge = ctk.CTkLabel(
            self.console_header,
            text="",
            image=self.terminal_icon,
            width=28,
            height=28,
            fg_color="#1e293b",
            corner_radius=8,
        )
        self.console_icon_badge.pack(side="left")

        self.console_title = ctk.CTkLabel(
            self.console_header,
            text="PROCESS LOG",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="#475569",
        )
        self.console_title.pack(side="left", padx=(10, 0))

        self.textbox = ctk.CTkTextbox(
            self.console_frame,
            fg_color="transparent",
            font=ctk.CTkFont(family="Courier", size=12),
            text_color="#cbd5e1",
            border_width=0,
        )
        self.textbox.pack(fill="both", expand=True, padx=25, pady=(0, 20))

    def _refresh_job_options(self, initial: bool = False) -> None:
        job_items = discover_job_profiles(self.paths.configs_dir)
        valid_items = [item for item in job_items if item.is_valid and item.config_path is not None]

        self.job_records = {}
        self.job_menu.delete(0, "end")

        for item in valid_items:
            label = item.label
            if label in self.job_records:
                label = f"{item.label} ({item.id})"
            self.job_records[label] = item

        labels = sorted(self.job_records.keys(), key=str.casefold)
        for label in labels:
            self.job_menu.add_command(label=label, command=lambda value=label: self.set_job_option(value))

        if labels:
            if self.job_selection.get() not in labels:
                self.job_selection.set(labels[0])
        else:
            self.job_selection.set("Tidak ada pekerjaan valid")

        self._on_job_changed()
        if initial:
            self.add_log(f"Job loaded: {len(labels)} valid, {max(0, len(job_items) - len(labels))} invalid.")
        else:
            self.add_log(f"Refresh pekerjaan selesai: {len(labels)} valid, {max(0, len(job_items) - len(labels))} invalid.")

    def set_job_option(self, value: str) -> None:
        self.job_selection.set(value)
        self._on_job_changed()

    def _on_job_changed(self) -> None:
        selected = self._selected_job()
        if selected is None:
            self.config_value_label.configure(text="-")
            self._preflight_result = None
            self._set_execute_ready(False)
            return
        self.config_value_label.configure(text=selected.config_file)
        self._run_preflight()

    def open_job_menu(self) -> None:
        if not self.job_records:
            return
        x = self.job_select_frame.winfo_rootx()
        y = self.job_select_frame.winfo_rooty() + self.job_select_frame.winfo_height()
        self.job_menu.tk_popup(x, y)
        self.job_menu.grab_release()

    def _selected_job(self) -> JobProfileSummary | None:
        return self.job_records.get(self.job_selection.get())

    def _set_execute_ready(self, ready: bool) -> None:
        if ready:
            self.execute_btn.configure(
                state="normal",
                fg_color="#0f172a",
                hover_color="#1e293b",
                text_color="white",
            )
            return
        self.execute_btn.configure(
            state="disabled",
            fg_color="#cbd5e1",
            hover_color="#cbd5e1",
            text_color="#64748b",
        )

    def _run_preflight(self) -> None:
        job = self._selected_job()
        if self.selected_source_path is None or job is None or job.config_path is None:
            self._preflight_result = None
            self._set_execute_ready(False)
            return

        self._set_execute_ready(False)
        self.add_log("Menjalankan preflight...")
        try:
            result = run_preflight(
                paths=self.paths,
                source_path=self.selected_source_path,
                config_path=job.config_path,
            )
        except Exception as exc:
            self._preflight_result = None
            self.add_log(f"Preflight gagal: {exc}")
            messagebox.showerror(
                "Preflight gagal",
                sanitize_exception_message(str(exc), project_root=self.paths.project_root),
            )
            return

        self._preflight_result = result
        findings = getattr(result, "findings", ())
        for finding in findings:
            severity = getattr(finding, "severity", "info")
            summary = getattr(finding, "summary", "")
            if summary:
                self.add_log(f"Preflight [{severity}]: {summary}")

        is_ready = bool(getattr(result, "can_execute", False))
        status = getattr(result, "status", "Unknown")
        self.add_log(f"Preflight selesai: {status}")
        self._set_execute_ready(is_ready)

    def select_source_file(self) -> None:
        selected_path = select_source_file(self.paths.project_root)
        if not selected_path:
            self.add_log("Pemilihan source dibatalkan.")
            return

        source_path = Path(selected_path)
        errors = validate_source_file(source_path)
        if errors:
            error_message = "\n".join(errors)
            messagebox.showerror(
                "Source tidak valid",
                sanitize_exception_message(error_message, project_root=self.paths.project_root),
            )
            self.add_log(f"Source invalid: {error_message}")
            return

        self.selected_source_path = source_path
        self.source_btn.configure(text=self.selected_source_path.name)
        self.add_log(f"Source dipilih: {self.selected_source_path}")
        self._run_preflight()

    def start_new_session(self) -> None:
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self.add_log("Tidak bisa memulai sesi baru saat proses masih berjalan.")
            return

        clear_session_state(self.paths.project_root)
        self.selected_source_path = None
        self.source_btn.configure(text="Klik untuk Pilih Source")
        self._preflight_result = None
        self._set_execute_ready(False)
        self._refresh_job_options()
        self.textbox.delete("1.0", "end")

    def open_settings_window(self) -> None:
        subprocess.Popen([sys.executable, "-m", "app.ui.settings"])
        self.add_log("Membuka jendela Settings...")

    def add_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        sanitized = sanitize_log_message(message, project_root=self.paths.project_root)
        self.textbox.insert("end", f"[{timestamp}] {sanitized}\n")
        self.textbox.see("end")

    def _should_prompt_period(self, config_path: Path) -> bool:
        config = load_config_payload(config_path)
        ui_cfg = config.get("ui")
        if not isinstance(ui_cfg, dict):
            return False
        period_prompt_cfg = ui_cfg.get("period_prompt")
        return isinstance(period_prompt_cfg, dict) and period_prompt_cfg.get("enabled") is True

    @staticmethod
    def _parse_period_text_override(raw_value: str | None) -> str | None:
        value = (raw_value or "").strip()
        if not value:
            return None
        if len(value) != 6 or not value.isdigit():
            raise ValueError("Format periode wajib YYYYMM, contoh 202603.")

        month = int(value[4:6])
        if month < 1 or month > 12:
            raise ValueError("Bulan periode wajib 01 sampai 12.")

        return f"Periode: {MONTH_NAMES[month - 1]} {value[:4]}"

    def _prompt_period_text_override(self) -> str | None:
        while True:
            dialog = ctk.CTkInputDialog(
                title="Input Periode",
                text=(
                    "Masukkan periode laporan dengan format YYYYMM. "
                    "Contoh: 202603 untuk March 2026. "
                    "Kosongkan untuk otomatis dari source."
                ),
            )
            raw_value = dialog.get_input()
            try:
                return self._parse_period_text_override(raw_value)
            except ValueError as exc:
                messagebox.showwarning("Periode tidak valid", str(exc))

    def add_log_event(self) -> None:
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self.add_log("Proses masih berjalan.")
            return

        job = self._selected_job()
        if self.selected_source_path is None:
            messagebox.showwarning("Input belum lengkap", "Pilih source terlebih dahulu.")
            return
        if job is None or job.config_path is None:
            messagebox.showwarning("Input belum lengkap", "Pilih pekerjaan valid terlebih dahulu.")
            return

        period_text_override = None
        try:
            if self._should_prompt_period(job.config_path):
                period_text_override = self._prompt_period_text_override()
        except ValueError as exc:
            messagebox.showerror(
                "Config tidak valid",
                sanitize_exception_message(str(exc), project_root=self.paths.project_root),
            )
            return

        self._set_execute_ready(False)
        self.add_log("Memulai proses eksekusi...")
        self._worker_queue = Queue()
        self._worker_thread = Thread(
            target=self._run_pipeline_worker,
            args=(
                self.selected_source_path,
                job.config_path,
                self._worker_queue,
                period_text_override,
            ),
            daemon=True,
        )
        self._worker_thread.start()
        self.after(120, self._poll_worker_events)

    def _run_pipeline_worker(
        self,
        source_path: Path,
        config_path: Path,
        event_queue: Queue[tuple[str, object]],
        period_text_override: str | None = None,
    ) -> None:
        def worker_log(message: str) -> None:
            event_queue.put(("log", message))

        try:
            result = run_pipeline(
                paths=self.paths,
                source_path=source_path,
                config_path=config_path,
                log=worker_log,
                period_text_override=period_text_override,
            )
            event_queue.put(("success", result))
        except Exception as exc:
            event_queue.put(("error", str(exc)))
        finally:
            event_queue.put(("done", None))

    def _poll_worker_events(self) -> None:
        if self._worker_queue is None:
            return

        done_received = False
        while True:
            try:
                kind, payload = self._worker_queue.get_nowait()
            except Empty:
                break

            if kind == "log":
                self.add_log(str(payload))
            elif kind == "success":
                result = payload
                output_path = getattr(result, "output_path", None)
                sheets_written = getattr(result, "sheets_written", 0)
                if output_path is not None:
                    self.add_log(f"Output berhasil dibuat ({sheets_written} sheet): {output_path}")
                else:
                    self.add_log("Proses selesai dengan sukses!")
            elif kind == "error":
                error_message = str(payload)
                self.add_log(f"Error: {error_message}")
                messagebox.showerror(
                    "Eksekusi gagal",
                    sanitize_exception_message(error_message, project_root=self.paths.project_root),
                )
            elif kind == "done":
                done_received = True

        if done_received:
            self._worker_queue = None
            self._worker_thread = None
            self._preflight_result = None
            self._set_execute_ready(False)
            return

        self.after(120, self._poll_worker_events)

    def _open_outputs_dir(self) -> None:
        try:
            open_in_file_manager(self.paths.outputs_dir)
        except RuntimeError as exc:
            messagebox.showerror(
                "Gagal membuka folder",
                sanitize_exception_message(str(exc), project_root=self.paths.project_root),
            )
            self.add_log(str(exc))
            return
        self.add_log(f"Membuka folder output: {self.paths.outputs_dir}")


def run_desktop_app(paths: AppPaths) -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = DesktopApp(paths)
    app.mainloop()
