from __future__ import annotations

from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from time import perf_counter
from tkinter import messagebox
from typing import Any

import customtkinter as ctk

from app import AppPaths
from app.runtime_info import get_build_info, get_stale_bundle_warning
from app.services import (
    ConfigSummary,
    JobProfileSummary,
    PipelineResult,
    PipelineStepStatus,
    PreflightResult,
    clear_session_state,
    discover_configs,
    discover_job_profiles,
    run_preflight,
    run_pipeline,
    save_session_state,
    upsert_job_profile_record,
    validate_source_file,
)
from app.utils import (
    open_in_file_manager,
    sanitize_exception_message,
    sanitize_log_message,
    select_source_file,
)


PIPELINE_STEP_ORDER: tuple[tuple[str, str], ...] = (
    ("load_config", "Load config"),
    ("copy_source", "Copy source"),
    ("read_source", "Read source"),
    ("load_master", "Load master"),
    ("transform", "Transform"),
    ("build_output", "Build output"),
    ("write_output", "Write output"),
)


class JobSettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent: "DesktopApp") -> None:
        super().__init__(parent)
        self.parent = parent
        self.title("Pengaturan Job")
        self.geometry("760x520")
        self.minsize(700, 480)

        self.selected_job_id: str | None = None
        self.job_options: dict[str, JobProfileSummary] = {}
        self.config_options: dict[str, ConfigSummary] = {}

        self.job_var = ctk.StringVar(value="Job baru")
        self.job_name_var = ctk.StringVar(value="")
        self.config_var = ctk.StringVar(value="")
        self.enabled_var = ctk.BooleanVar(value=True)
        self.status_var = ctk.StringVar(value="Pilih config untuk melihat master yang digunakan.")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.transient(parent)
        self.grab_set()

        self._build_layout()
        self.refresh()

    def _build_layout(self) -> None:
        left_panel = ctk.CTkFrame(self)
        left_panel.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="nsew")
        left_panel.grid_columnconfigure(0, weight=1)

        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(7, weight=1)

        ctk.CTkLabel(
            left_panel,
            text="Daftar Job",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self.job_menu = ctk.CTkOptionMenu(
            left_panel,
            variable=self.job_var,
            values=["Job baru"],
            command=self._on_job_selected,
        )
        self.job_menu.grid(row=1, column=0, padx=16, pady=(0, 8), sticky="ew")

        ctk.CTkButton(
            left_panel,
            text="Job Baru",
            command=self._reset_form,
        ).grid(row=2, column=0, padx=16, pady=(0, 16), sticky="ew")

        ctk.CTkLabel(
            left_panel,
            text="Status Job",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=3, column=0, padx=16, pady=(0, 4), sticky="w")

        ctk.CTkLabel(
            left_panel,
            textvariable=self.status_var,
            justify="left",
            wraplength=220,
        ).grid(row=4, column=0, padx=16, pady=(0, 16), sticky="w")

        ctk.CTkLabel(
            right_panel,
            text="Form Job",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        ctk.CTkLabel(right_panel, text="Nama Job").grid(row=1, column=0, padx=16, sticky="w")
        ctk.CTkEntry(right_panel, textvariable=self.job_name_var).grid(
            row=2, column=0, padx=16, pady=(4, 8), sticky="ew"
        )

        ctk.CTkLabel(right_panel, text="Config").grid(row=3, column=0, padx=16, sticky="w")
        self.config_menu = ctk.CTkOptionMenu(
            right_panel,
            variable=self.config_var,
            values=["Tidak ada config valid"],
            command=self._on_config_selected,
        )
        self.config_menu.grid(row=4, column=0, padx=16, pady=(4, 8), sticky="ew")

        ctk.CTkCheckBox(
            right_panel,
            text="Aktifkan job ini",
            variable=self.enabled_var,
            onvalue=True,
            offvalue=False,
        ).grid(row=5, column=0, padx=16, pady=(0, 12), sticky="w")

        ctk.CTkLabel(
            right_panel,
            text="Master yang digunakan",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=6, column=0, padx=16, sticky="w")

        self.master_box = ctk.CTkTextbox(right_panel, wrap="word", height=220)
        self.master_box.grid(row=7, column=0, padx=16, pady=(4, 12), sticky="nsew")
        self.master_box.configure(state="disabled")

        ctk.CTkButton(
            right_panel,
            text="Simpan Job",
            command=self._save_job,
        ).grid(row=8, column=0, padx=16, pady=(0, 16), sticky="ew")

    def refresh(self) -> None:
        config_items = discover_configs(self.parent.paths.configs_dir)
        self.config_options = {
            item.path.name: item for item in config_items if item.is_valid
        }

        config_values = sorted(self.config_options, key=str.casefold)
        if config_values:
            self.config_menu.configure(values=config_values)
            if self.config_var.get() not in config_values:
                self.config_var.set(config_values[0])
        else:
            placeholder = "Tidak ada config valid"
            self.config_menu.configure(values=[placeholder])
            self.config_var.set(placeholder)

        job_items = discover_job_profiles(self.parent.paths.configs_dir)
        self.job_options = {item.label: item for item in job_items}
        job_values = ["Job baru", *sorted(self.job_options, key=str.casefold)]
        self.job_menu.configure(values=job_values)

        current_job = self.job_var.get()
        if current_job not in job_values:
            self.job_var.set("Job baru")
            self._reset_form()
            return

        if current_job == "Job baru":
            self._reset_form(clear_job_menu=False)
            return

        self._populate_form(self.job_options[current_job])

    def _set_master_text(self, lines: list[str]) -> None:
        self.master_box.configure(state="normal")
        self.master_box.delete("1.0", "end")
        self.master_box.insert("end", "\n".join(lines))
        self.master_box.configure(state="disabled")

    def _reset_form(self, clear_job_menu: bool = True) -> None:
        self.selected_job_id = None
        if clear_job_menu:
            self.job_var.set("Job baru")
        self.job_name_var.set("")
        config_values = list(self.config_options)
        self.config_var.set(config_values[0] if config_values else "Tidak ada config valid")
        self.enabled_var.set(True)
        self.status_var.set("Isi nama job dan pilih config.")
        self._refresh_master_preview()

    def _populate_form(self, job: JobProfileSummary) -> None:
        self.selected_job_id = job.id
        self.job_var.set(job.label)
        self.job_name_var.set(job.label)
        if job.config_file in self.config_options:
            self.config_var.set(job.config_file)
        else:
            self.config_var.set(job.config_file)
        self.enabled_var.set(job.enabled)
        if job.is_valid:
            self.status_var.set("Job valid dan siap dipakai.")
        else:
            self.status_var.set("Job invalid: " + "; ".join(job.errors[:2]))
        self._refresh_master_preview(preferred=job.master_files)

    def _on_job_selected(self, selected_label: str) -> None:
        if selected_label == "Job baru":
            self._reset_form(clear_job_menu=False)
            return
        selected = self.job_options.get(selected_label)
        if selected is None:
            self._reset_form(clear_job_menu=False)
            return
        self._populate_form(selected)

    def _on_config_selected(self, _: str) -> None:
        self._refresh_master_preview()

    def _refresh_master_preview(self, preferred: tuple[str, ...] | None = None) -> None:
        if preferred is not None:
            master_files = list(preferred)
        else:
            selected_config = self.config_options.get(self.config_var.get())
            if selected_config is None:
                self._set_master_text(["Belum ada config valid untuk dipilih."])
                return
            matching_job = next(
                (
                    item
                    for item in discover_job_profiles(self.parent.paths.configs_dir)
                    if item.config_file == selected_config.path.name and item.is_valid
                ),
                None,
            )
            if matching_job is not None:
                master_files = list(matching_job.master_files)
            else:
                try:
                    from app.services import load_config_payload

                    payload = load_config_payload(selected_config.path)
                except ValueError as exc:
                    self._set_master_text([f"Gagal membaca config: {exc}"])
                    return

                master_files = []
                for master_cfg in payload.get("masters") or []:
                    if isinstance(master_cfg, dict) and isinstance(master_cfg.get("file"), str):
                        master_files.append(str(master_cfg["file"]))
                for step_cfg in payload.get("steps") or []:
                    if not isinstance(step_cfg, dict):
                        continue
                    master_cfg = step_cfg.get("master")
                    if isinstance(master_cfg, dict) and isinstance(master_cfg.get("file"), str):
                        file_ref = str(master_cfg["file"])
                        if file_ref not in master_files:
                            master_files.append(file_ref)

        if not master_files:
            self._set_master_text(["Config ini tidak mereferensikan file master."])
            return

        self._set_master_text(master_files)

    def _save_job(self) -> None:
        try:
            record = upsert_job_profile_record(
                self.parent.paths.configs_dir,
                label=self.job_name_var.get(),
                config_file=self.config_var.get(),
                enabled=bool(self.enabled_var.get()),
                record_id=self.selected_job_id,
            )
        except ValueError as exc:
            messagebox.showerror("Gagal menyimpan job", str(exc), parent=self)
            return

        self.parent.refresh_jobs(initial=False)
        self.selected_job_id = record.id
        self.job_var.set(record.label)
        self.status_var.set("Job berhasil disimpan.")
        self.refresh()
        self.parent._append_log(f"Job disimpan: {record.label} -> {record.config_file}")
        messagebox.showinfo("Job tersimpan", f"Job '{record.label}' berhasil disimpan.", parent=self)


class DesktopApp(ctk.CTk):
    def __init__(self, paths: AppPaths) -> None:
        super().__init__()
        self.paths = paths
        self.build_info = get_build_info(paths.project_root)
        self.source_path: Path | None = None
        self.config_by_label: dict[str, ConfigSummary] = {}
        self.job_by_label: dict[str, JobProfileSummary] = {}
        self._job_settings_dialog: JobSettingsDialog | None = None
        self._preflight_queue: Queue[tuple[str, object]] | None = None
        self._preflight_thread: Thread | None = None
        self._preflight_request_id = 0
        self._latest_preflight_request_id = 0
        self._active_preflight_request_id: int | None = None
        self._preflight_result: PreflightResult | None = None
        self._worker_queue: Queue[tuple[str, object]] | None = None
        self._worker_thread: Thread | None = None
        self._restoring_session = False

        self.title(f"Excel Automation Tool - {self.build_info.mode}")
        self.geometry("1280x720")
        self.minsize(1280, 720)
        self.maxsize(1280, 720)

        self.source_var = ctk.StringVar(value="")
        self.selected_job_var = ctk.StringVar(value="")
        self.job_info_var = ctk.StringVar(value="Belum ada pekerjaan terpilih.")
        self.primary_hint_var = ctk.StringVar(value="")
        self.execute_hint_var = ctk.StringVar(value="")
        self.preflight_status_var = ctk.StringVar(value="Preflight: Belum dicek")
        self.status_var = ctk.StringVar(value="Status: Idle")
        self.last_output_var = ctk.StringVar(value="-")
        self._last_run_context: dict[str, object] | None = None
        self._init_redesign_foundation_refs()

        self._build_layout()
        self._restore_window_geometry()
        self.refresh_jobs(initial=True)
        self.bind("<Configure>", self._on_window_configure)
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self._append_log(f"Aplikasi siap digunakan. Runtime: {self.build_info.summary()}")
        stale_warning = get_stale_bundle_warning(paths.project_root)
        if stale_warning:
            self._append_log(stale_warning)
            self.after(50, lambda: messagebox.showwarning("Bundle stale", stale_warning))

    def _init_redesign_foundation_refs(self) -> None:
        # Tahap 1 redesign hanya menyiapkan reference dan state foundation.
        # Widget akan diisi pada tahap layout redesign berikutnya.
        self.header_frame: ctk.CTkFrame | None = None
        self.source_card_frame: ctk.CTkFrame | None = None
        self.job_card_frame: ctk.CTkFrame | None = None
        self.execute_card_frame: ctk.CTkFrame | None = None
        self.log_panel_frame: ctk.CTkFrame | None = None
        self.state_badge_label: ctk.CTkLabel | None = None
        self.progress_bar: ctk.CTkProgressBar | None = None
        self.clear_source_button: ctk.CTkButton | None = None
        self.start_new_session_button: ctk.CTkButton | None = None
        self.progress_label_var = ctk.StringVar(value="Progress: Belum dimulai")
        self.progress_steps_var = ctk.StringVar(value=self._format_pipeline_step_lines())

    def _format_pipeline_step_lines(self) -> str:
        return "\n".join(f"- {label}" for _, label in PIPELINE_STEP_ORDER)

    def _resolve_visual_state(self) -> str:
        worker_running = self._worker_thread is not None and self._worker_thread.is_alive()
        if worker_running:
            return "running"

        preflight_running = self._preflight_thread is not None and self._preflight_thread.is_alive()
        if preflight_running or self._hint_preflight_status_text() == "Preflight: Memeriksa...":
            return "checking"

        if self._hint_status_text() == "Status: Sukses":
            return "success"

        if self._hint_status_text() == "Status: Gagal":
            return "failed"

        preflight_result = self._hint_preflight_result()
        if preflight_result is not None and preflight_result.status == "Blocked":
            return "blocked"

        if preflight_result is not None and preflight_result.can_execute:
            return "ready"

        return "idle"

    def _build_card_title(
        self,
        master: ctk.CTkFrame,
        *,
        eyebrow: str,
        title: str,
        description: str | None = None,
        description_wraplength: int = 320,
        description_bottom_pady: int = 12,
        row: int = 0,
    ) -> int:
        ctk.CTkLabel(
            master,
            text=eyebrow,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("black", "black"),
        ).grid(row=row, column=0, padx=16, pady=(16, 2), sticky="w")

        next_row = row + 1
        if title.strip():
            ctk.CTkLabel(
                master,
                text=title,
                font=ctk.CTkFont(size=18, weight="bold"),
                anchor="w",
                justify="left",
            ).grid(row=next_row, column=0, padx=16, pady=(0, 4), sticky="ew")
            next_row += 1

        if description is None or not description.strip():
            return next_row

        ctk.CTkLabel(
            master,
            text=description,
            justify="left",
            wraplength=description_wraplength,
            text_color=("gray40", "gray60"),
        ).grid(row=next_row, column=0, padx=16, pady=(0, description_bottom_pady), sticky="w")
        return next_row + 1

    def _build_header_section(self, master: ctk.CTkFrame) -> None:
        self.header_frame = ctk.CTkFrame(master, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=16, pady=(8, 12), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        title_group = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_group.grid(row=0, column=0, sticky="ew")
        title_group.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_group,
            text="Excel Automation Tool",
            font=ctk.CTkFont(size=24, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            title_group,
            text="Pilih source, pilih pekerjaan, lalu jalankan proses.",
            justify="left",
            wraplength=300,
            text_color=("gray40", "gray60"),
        ).grid(row=1, column=0, pady=(4, 0), sticky="w")

        ctk.CTkButton(
            self.header_frame,
            text="Pengaturan Job",
            command=self._open_job_settings,
            width=140,
            height=36,
        ).grid(row=0, column=1, padx=(12, 0), sticky="e")

    def _build_source_card(self, master: ctk.CTkFrame) -> None:
        self.source_card_frame = ctk.CTkFrame(master)
        self.source_card_frame.grid(row=1, column=0, padx=0, pady=(0, 12), sticky="ew")
        self.source_card_frame.grid_columnconfigure(0, weight=1)

        next_row = self._build_card_title(
            self.source_card_frame,
            eyebrow="Langkah 1. Source Input (Excel/CSV)",
            title="",
            description="",
        )

        selected_source_panel = ctk.CTkFrame(
            self.source_card_frame,
            fg_color=("gray95", "gray15"),
            border_width=1,
            border_color=("gray88", "gray25"),
            height=56,
        )
        selected_source_panel.grid(row=next_row, column=0, padx=16, pady=(0, 10), sticky="ew")
        selected_source_panel.grid_columnconfigure(0, weight=1)
        selected_source_panel.grid_rowconfigure(0, weight=1)
        selected_source_panel.grid_propagate(False)

        ctk.CTkLabel(
            selected_source_panel,
            textvariable=self.source_var,
            justify="left",
            wraplength=420,
            corner_radius=16,
            anchor="nw",
        ).grid(row=0, column=0, padx=0, pady=8, sticky="nsew")

        ctk.CTkButton(
            self.source_card_frame,
            text="Pilih Source",
            command=self._select_source,
            height=38,
        ).grid(row=next_row + 1, column=0, padx=16, pady=(0, 10), sticky="ew")

        self._update_source_actions()

    def _build_job_card(self, master: ctk.CTkFrame) -> None:
        self.job_card_frame = ctk.CTkFrame(master)
        self.job_card_frame.grid(row=2, column=0, padx=0, pady=(0, 12), sticky="ew")
        self.job_card_frame.grid_columnconfigure(0, weight=1)

        next_row = self._build_card_title(
            self.job_card_frame,
            eyebrow="Langkah 2. Job Selection",
            title="",
            description="",
            description_wraplength=1000,
            description_bottom_pady=2,
        )

        selection_panel = ctk.CTkFrame(
            self.job_card_frame,
            fg_color=("gray95", "gray16"),
            border_width=1,
            border_color=("gray88", "gray25"),
            corner_radius=14,
        )
        selection_panel.grid(row=next_row, column=0, padx=16, pady=(0, 12), sticky="ew")
        selection_panel.grid_columnconfigure(0, weight=1)
        selection_panel.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            selection_panel,
            text="Pilih pekerjaan aktif dan cek konteks job sebelum execute.",
            font=ctk.CTkFont(size=11, weight="normal"),
            text_color=("gray45", "gray55"),
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(8, 3), sticky="w")

        self.job_menu = ctk.CTkOptionMenu(
            selection_panel,
            variable=self.selected_job_var,
            values=["Belum ada pekerjaan"],
            command=self._on_job_selected,
            height=34,
        )
        self.job_menu.grid(row=1, column=0, padx=(14, 8), pady=(0, 10), sticky="ew")

        ctk.CTkButton(
            selection_panel,
            text="Refresh",
            command=self.refresh_jobs,
            width=84,
            height=34,
        ).grid(row=1, column=1, padx=(0, 14), pady=(0, 10), sticky="ew")

        job_info_panel = ctk.CTkFrame(
            self.job_card_frame,
            fg_color=("gray95", "gray16"),
            border_width=1,
            border_color=("gray88", "gray25"),
            corner_radius=14,
        )
        job_info_panel.grid(row=next_row + 1, column=0, padx=16, pady=(0, 12), sticky="ew")
        job_info_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            job_info_panel,
            text="Detail job aktif",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray45", "gray55"),
        ).grid(row=0, column=0, padx=14, pady=(12, 2), sticky="w")

        ctk.CTkLabel(
            job_info_panel,
            textvariable=self.job_info_var,
            justify="left",
            wraplength=320,
            anchor="w",
        ).grid(row=1, column=0, padx=14, pady=(0, 12), sticky="ew")

        self.start_new_session_button = ctk.CTkButton(
            self.job_card_frame,
            text="Start New Session",
            command=self._start_new_session,
            state="disabled",
            height=36,
        )
        self.start_new_session_button.grid(
            row=next_row + 2,
            column=0,
            padx=16,
            pady=(0, 16),
            sticky="ew",
        )

    def _build_execute_card(self, master: ctk.CTkFrame) -> None:
        self.execute_card_frame = ctk.CTkFrame(master)
        self.execute_card_frame.grid(row=0, column=0, padx=16, pady=(16, 12), sticky="ew")
        self.execute_card_frame.grid_columnconfigure(0, weight=1)

        next_row = self._build_card_title(
            self.execute_card_frame,
            eyebrow="Langkah 3. Execute & Monitor",
            title="",
            description="Jalankan proses saat source dan job valid, lalu pantau hasil akhirnya di panel ini.",
        )

        self.execute_button = ctk.CTkButton(
            self.execute_card_frame,
            text="Execute",
            command=self._execute_pipeline,
            state="disabled",
            height=42,
        )
        self.execute_button.grid(row=next_row, column=0, padx=16, pady=(0, 16), sticky="ew")

        ctk.CTkButton(
            self.execute_card_frame,
            text="Buka Folder Outputs",
            command=self._open_outputs_dir,
            height=36,
        ).grid(row=next_row + 1, column=0, padx=16, pady=(0, 8), sticky="ew")

    def _build_log_panel(self, master: ctk.CTkFrame) -> None:
        self.log_panel_frame = ctk.CTkFrame(master)
        self.log_panel_frame.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        self.log_panel_frame.grid_columnconfigure(0, weight=1)
        self.log_panel_frame.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.log_panel_frame, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Process Log",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="Runtime monitor",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray45", "gray55"),
        ).grid(row=0, column=1, sticky="e")

        self.log_box = ctk.CTkTextbox(self.log_panel_frame, wrap="word")
        self.log_box.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        self.log_box.configure(state="disabled")

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left_panel = ctk.CTkFrame(self, width=420, corner_radius=16)
        left_panel.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="nsew")
        left_panel.grid_columnconfigure(0, weight=1)
 
        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)

        self._build_header_section(left_panel)
        self._build_source_card(left_panel)
        self._build_job_card(left_panel)
        self._build_execute_card(right_panel)
        self._build_log_panel(right_panel)

    def _update_source_actions(self) -> None:
        if self.clear_source_button is None:
            return
        self.clear_source_button.configure(
            state="normal" if self.source_path is not None else "disabled"
        )

    def _selected_job_id(self) -> str | None:
        selected = self._selected_job()
        if selected is None:
            return None
        value = selected.id.strip()
        return value or None

    def _clear_source(self) -> None:
        if self.source_path is None:
            return

        self.source_path = None
        self.source_var.set("")
        self._preflight_request_id += 1
        self._latest_preflight_request_id = self._preflight_request_id
        self._active_preflight_request_id = None
        self._set_preflight_idle()
        self._persist_session_state()
        self._append_log("Source dibersihkan dari sesi aktif.")
        self._update_execute_state()
        self._update_hints()
        self._update_source_actions()

    def _apply_source_path(self, source_path: Path, *, log_prefix: str) -> None:
        self.source_path = source_path
        self.source_var.set(str(source_path))
        self._persist_session_state()
        self._append_log(f"{log_prefix}: {source_path.name}")
        self._schedule_preflight()
        self._update_execute_state()
        self._update_hints()
        self._update_source_actions()

    def _restore_window_geometry(self) -> None:
        self.geometry("1280x720")

    def _current_window_geometry(self) -> str | None:
        return "1280x720"

    def _persist_session_state(self) -> None:
        if getattr(self, "_restoring_session", False) or "paths" not in self.__dict__:
            return
        save_session_state(
            self.paths.project_root,
            last_job_id=self._selected_job_id(),
            last_source_path=self.source_path,
            window_geometry=self._current_window_geometry(),
        )

    def _on_window_configure(self, _: Any) -> None:
        self._persist_session_state()

    def _on_window_close(self) -> None:
        self._persist_session_state()
        self.destroy()

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        sanitized = sanitize_log_message(message, project_root=self.paths.project_root)
        line = f"[{timestamp}] {sanitized}\n"
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _reset_progress_state(self) -> None:
        return

    def _apply_progress_update(self, status: PipelineStepStatus) -> None:
        return

    def _set_status(self, text: str) -> None:
        self.status_var.set(f"Status: {text}")
        self._update_hints()

    def _format_duration_text(self, duration_ms: int | None) -> str:
        if duration_ms is None or duration_ms <= 0:
            return "-"
        if duration_ms < 1000:
            return f"{duration_ms} ms"
        return f"{duration_ms / 1000:.1f} detik"

    def _set_hint_values(self, primary: str, execute: str) -> None:
        if "primary_hint_var" not in self.__dict__ or "execute_hint_var" not in self.__dict__:
            return
        self.primary_hint_var.set(primary)
        self.execute_hint_var.set(execute)

    def _hint_job_count(self) -> int:
        job_by_label = self.__dict__.get("job_by_label")
        return len(job_by_label) if isinstance(job_by_label, dict) else 0

    def _hint_source_path(self) -> Path | None:
        source_path = self.__dict__.get("source_path")
        return source_path if isinstance(source_path, Path) else None

    def _hint_status_text(self) -> str:
        status_var = self.__dict__.get("status_var")
        if status_var is None:
            return "Status: Idle"
        return str(status_var.get())

    def _hint_preflight_status_text(self) -> str:
        preflight_status_var = self.__dict__.get("preflight_status_var")
        if preflight_status_var is None:
            return "Preflight: Belum dicek"
        return str(preflight_status_var.get())

    def _hint_preflight_result(self) -> PreflightResult | None:
        result = self.__dict__.get("_preflight_result")
        return result if isinstance(result, PreflightResult) else None

    def _resolve_primary_hint(self) -> str:
        worker_running = self._worker_thread is not None and self._worker_thread.is_alive()
        if self._hint_job_count() == 0:
            return "Belum ada pekerjaan valid. Cek file configs/job_profiles.yaml dan config yang dirujuk."
        if worker_running:
            return "Proses sedang berjalan. Tunggu hingga semua langkah selesai."
        if self._hint_status_text() == "Status: Sukses":
            return "Proses selesai. Periksa output terakhir atau buka folder outputs."
        if self._hint_status_text() == "Status: Gagal":
            return "Proses gagal. Periksa log untuk detail lalu perbaiki source atau config aktif."
        if self._hint_source_path() is None:
            return "Pilih source file untuk pekerjaan yang aktif."
        preflight_running = self._preflight_thread is not None and self._preflight_thread.is_alive()
        if preflight_running or self._hint_preflight_status_text() == "Preflight: Memeriksa...":
            return "Preflight sedang memeriksa kecocokan source, config, dan output."
        preflight_result = self._hint_preflight_result()
        if preflight_result is not None and preflight_result.status == "Blocked":
            return "Execute dinonaktifkan karena masih ada error preflight. Lihat log untuk detail."
        if preflight_result is not None and preflight_result.can_execute:
            return "Source siap diproses. Jalankan Execute untuk membuat output."
        return "Pilih source dan pekerjaan untuk memulai pemeriksaan otomatis."

    def _resolve_execute_hint(self) -> str:
        worker_running = self._worker_thread is not None and self._worker_thread.is_alive()
        if self._hint_job_count() == 0:
            return "Tambahkan atau perbaiki pekerjaan valid sebelum menjalankan execute."
        if worker_running:
            return "Execute dinonaktifkan selama proses masih berjalan."
        preflight_running = self._preflight_thread is not None and self._preflight_thread.is_alive()
        if self._hint_source_path() is None:
            return "Pilih source terlebih dahulu."
        if self._selected_job() is None:
            return "Pilih pekerjaan valid terlebih dahulu."
        if preflight_running or self._hint_preflight_status_text() == "Preflight: Memeriksa...":
            return "Tunggu preflight selesai sebelum menjalankan execute."
        preflight_result = self._hint_preflight_result()
        if preflight_result is None:
            return "Preflight belum siap."
        if not preflight_result.can_execute:
            return "Execute dinonaktifkan sampai semua error preflight diselesaikan."
        return "Execute siap dijalankan."

    def _update_hints(self) -> None:
        self._set_hint_values(self._resolve_primary_hint(), self._resolve_execute_hint())

    def _select_source(self) -> None:
        file_path = select_source_file(self.paths.project_root)
        if not file_path:
            self._append_log("Pemilihan source dibatalkan.")
            return

        source_path = Path(file_path)
        errors = validate_source_file(source_path)
        if errors:
            error_message = "\n".join(errors)
            messagebox.showerror(
                "Source tidak valid",
                sanitize_exception_message(error_message, project_root=self.paths.project_root),
            )
            self._append_log(f"Source invalid: {error_message}")
            return

        self._apply_source_path(source_path, log_prefix="Source dipilih")

    def _on_job_selected(self, _: str) -> None:
        self._update_job_info()
        self._persist_session_state()
        self._schedule_preflight()
        self._update_execute_state()
        self._update_hints()

    def refresh_jobs(self, initial: bool = False) -> None:
        job_items = discover_job_profiles(self.paths.configs_dir)
        self.job_by_label = {}
        selectable_labels: list[str] = []
        invalid_count = 0

        for item in job_items:
            label = item.label
            if label in self.job_by_label:
                label = f"{item.label} ({item.id})"
            self.job_by_label[label] = item
            if item.is_valid:
                selectable_labels.append(label)
            else:
                invalid_count += 1

        if selectable_labels:
            self.job_menu.configure(values=selectable_labels)
            if self.selected_job_var.get() not in selectable_labels:
                self.selected_job_var.set(selectable_labels[0])
        else:
            placeholder = "Tidak ada pekerjaan valid"
            self.job_menu.configure(values=[placeholder])
            self.selected_job_var.set(placeholder)

        self._update_job_info()
        self._schedule_preflight()
        self._update_execute_state()

        valid_count = len(selectable_labels)
        if initial:
            self._append_log(
                f"Job loaded: {valid_count} valid, {invalid_count} invalid."
            )
        else:
            self._append_log(
                f"Refresh pekerjaan selesai: {valid_count} valid, {invalid_count} invalid."
            )

        if self._job_settings_dialog is not None and self._job_settings_dialog.winfo_exists():
            self._job_settings_dialog.refresh()

        self._update_hints()

    def _update_job_info(self) -> None:
        selected_label = self.selected_job_var.get()
        selected = self.job_by_label.get(selected_label)
        if selected is None:
            self.job_info_var.set("Belum ada pekerjaan valid di folder configs/.")
            return
        if selected.is_valid:
            master_count = len(selected.master_files)
            self.job_info_var.set(
                f"Pekerjaan aktif: {selected.label}\nConfig: {selected.config_file}\nMaster: {master_count} file"
            )
            return
        self.job_info_var.set(
            "Pekerjaan invalid: " + "; ".join(selected.errors[:2])
        )

    def _selected_job(self) -> JobProfileSummary | None:
        selected = self.job_by_label.get(self.selected_job_var.get())
        if selected is None or not selected.is_valid or selected.config_path is None:
            return None
        return selected

    def _update_execute_state(self) -> None:
        worker_running = self._worker_thread is not None and self._worker_thread.is_alive()
        preflight_running = self._preflight_thread is not None and self._preflight_thread.is_alive()
        session_reset_enabled = self._can_start_new_session()
        self.start_new_session_button.configure(
            state="normal" if session_reset_enabled else "disabled"
        )
        if worker_running:
            self.execute_button.configure(state="disabled")
            return
        if preflight_running:
            self.execute_button.configure(state="disabled")
            return
        if (
            self.source_path is not None
            and self._selected_job() is not None
            and self._preflight_result is not None
            and self._preflight_result.can_execute
        ):
            self.execute_button.configure(state="normal")
        else:
            self.execute_button.configure(state="disabled")
        self._update_hints()

    def _set_preflight_idle(self) -> None:
        self._preflight_result = None
        self.preflight_status_var.set("Preflight: Belum dicek")
        self.last_output_var.set("-")
        self._reset_progress_state()
        self._update_hints()

    def _can_start_new_session(self) -> bool:
        worker_running = self._worker_thread is not None and self._worker_thread.is_alive()
        if worker_running:
            return False
        return self.status_var.get() in {"Status: Sukses", "Status: Gagal"}

    def _clear_log_box(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _start_new_session(self) -> None:
        if not self._can_start_new_session():
            return

        self.source_path = None
        self.source_var.set("")
        self._preflight_request_id += 1
        self._latest_preflight_request_id = self._preflight_request_id
        self._active_preflight_request_id = None
        self._worker_queue = None
        self._worker_thread = None
        self._last_run_context = None
        self._set_preflight_idle()
        if "paths" in self.__dict__:
            clear_session_state(self.paths.project_root)
        self._set_status("Idle")
        self._clear_log_box()
        self.refresh_jobs(initial=False)
        self._append_log("Sesi baru dimulai.")
        self._update_execute_state()
        self._update_hints()

    def _apply_preflight_result(self, result: PreflightResult) -> None:
        self._preflight_result = result
        self.preflight_status_var.set(f"Preflight: {result.status}")
        if result.output_path is not None:
            self.last_output_var.set(str(result.output_path))
        self._update_execute_state()
        self._update_hints()

    def _schedule_preflight(self) -> None:
        job = self._selected_job()
        if self.source_path is None or job is None or job.config_path is None:
            self._set_preflight_idle()
            self._update_execute_state()
            return

        self._preflight_request_id += 1
        request_id = self._preflight_request_id
        self._latest_preflight_request_id = request_id
        self.preflight_status_var.set("Preflight: Memeriksa...")
        self._update_execute_state()
        self._update_hints()

        if self._preflight_thread is not None and self._preflight_thread.is_alive():
            return

        self._start_preflight_worker()

    def _start_preflight_worker(self) -> None:
        if self._preflight_thread is not None and self._preflight_thread.is_alive():
            return
        if self.source_path is None:
            return
        job = self._selected_job()
        if job is None or job.config_path is None:
            return

        self._active_preflight_request_id = self._latest_preflight_request_id
        self._preflight_queue = Queue()
        self._preflight_thread = Thread(
            target=self._run_preflight_worker,
            args=(
                self._active_preflight_request_id,
                self.source_path,
                job.config_path,
                self._preflight_queue,
            ),
            daemon=True,
        )
        self._preflight_thread.start()
        self.after(120, self._poll_preflight_events)

    def _run_preflight_worker(
        self,
        request_id: int,
        source_path: Path,
        config_path: Path,
        event_queue: Queue[tuple[str, object]],
    ) -> None:
        try:
            result = run_preflight(
                paths=self.paths,
                source_path=source_path,
                config_path=config_path,
            )
            event_queue.put(("result", (request_id, result)))
        except Exception as exc:
            event_queue.put(("error", (request_id, str(exc))))
        finally:
            event_queue.put(("done", request_id))

    def _poll_preflight_events(self) -> None:
        if self._preflight_queue is None:
            return

        done_received = False
        while True:
            try:
                kind, payload = self._preflight_queue.get_nowait()
            except Empty:
                break

            if kind == "result":
                request_id, result = payload
                if (
                    isinstance(request_id, int)
                    and isinstance(result, PreflightResult)
                    and request_id == self._latest_preflight_request_id
                ):
                    self._apply_preflight_result(result)
                    self._append_log(
                        f"Preflight selesai: {result.status} "
                        f"({result.error_count} error, {result.warning_count} warning, {result.info_count} info)."
                    )
            elif kind == "error":
                request_id, error_message = payload
                if isinstance(request_id, int) and request_id == self._latest_preflight_request_id:
                    fallback = PreflightResult(
                        status="Blocked",
                        findings=(),
                        output_path=None,
                    )
                    self._preflight_result = fallback
                    self.preflight_status_var.set("Preflight: Blocked")
                    self._append_log(f"Preflight error: {error_message}")
                    self.last_output_var.set("-")
                    self._update_execute_state()
                    self._update_hints()
            elif kind == "done":
                done_received = True

        if done_received:
            completed_request_id = self._active_preflight_request_id
            self._preflight_queue = None
            self._preflight_thread = None
            self._active_preflight_request_id = None
            if (
                isinstance(completed_request_id, int)
                and self._latest_preflight_request_id > completed_request_id
            ):
                self._start_preflight_worker()
                return
            if self._preflight_result is None and self.source_path is not None and self._selected_job() is not None:
                self._schedule_preflight()
                return
            self._update_execute_state()
            self._update_hints()
            return

        self.after(120, self._poll_preflight_events)

    def _execute_pipeline(self) -> None:
        job = self._selected_job()
        if self.source_path is None or job is None or job.config_path is None:
            messagebox.showwarning(
                "Input belum lengkap",
                "Pilih source dan pekerjaan yang valid terlebih dahulu.",
            )
            return

        if self._preflight_result is None:
            messagebox.showwarning(
                "Preflight belum siap",
                "Tunggu preflight selesai sebelum menjalankan execute.",
            )
            return

        if not self._preflight_result.can_execute:
            messagebox.showwarning(
                "Preflight memblokir execute",
                "Perbaiki temuan preflight yang masih Blocked sebelum menjalankan execute.",
            )
            return

        worker_running = self._worker_thread is not None and self._worker_thread.is_alive()
        if worker_running:
            return

        self.execute_button.configure(state="disabled")
        self._set_status("Running")
        self._reset_progress_state()
        self._last_run_context = {
            "job_label": job.label,
            "source_name": self.source_path.name,
            "duration_ms": None,
            "started_at": perf_counter(),
        }
        self._append_log(f"Eksekusi dimulai untuk pekerjaan: {job.label}")
        self._worker_queue = Queue()
        self._worker_thread = Thread(
            target=self._run_pipeline_worker,
            args=(self.source_path, job.config_path, self._worker_queue),
            daemon=True,
        )
        self._worker_thread.start()
        self.after(120, self._poll_worker_events)

    def _open_job_settings(self) -> None:
        if self._job_settings_dialog is not None and self._job_settings_dialog.winfo_exists():
            self._job_settings_dialog.focus()
            return
        self._job_settings_dialog = JobSettingsDialog(self)

    def _run_pipeline_worker(
        self,
        source_path: Path,
        config_path: Path,
        event_queue: Queue[tuple[str, object]],
    ) -> None:
        def worker_log(message: str) -> None:
            event_queue.put(("log", message))

        def worker_progress(status: PipelineStepStatus) -> None:
            event_queue.put(("progress", status))

        try:
            result = run_pipeline(
                paths=self.paths,
                source_path=source_path,
                config_path=config_path,
                log=worker_log,
                progress=worker_progress,
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
                self._append_log(str(payload))
            elif kind == "progress" and isinstance(payload, PipelineStepStatus):
                self._apply_progress_update(payload)
            elif kind == "success":
                result = payload
                if isinstance(result, PipelineResult):
                    self.last_output_var.set(str(result.output_path))
                    self._set_status("Sukses")
                    self._append_log(
                        f"Output berhasil dibuat ({result.sheets_written} sheet)."
                    )
                    self._update_hints()
            elif kind == "error":
                error_message = str(payload)
                if self._last_run_context is not None:
                    started_at = self._last_run_context.get("started_at")
                    if isinstance(started_at, float):
                        self._last_run_context["duration_ms"] = max(
                            1, int(round((perf_counter() - started_at) * 1000))
                        )
                self._set_status("Gagal")
                self._append_log(f"Error: {error_message}")
                self._update_hints()
                messagebox.showerror(
                    "Eksekusi gagal",
                    sanitize_exception_message(error_message, project_root=self.paths.project_root),
                )
            elif kind == "done":
                done_received = True

        if done_received:
            self._worker_queue = None
            self._worker_thread = None
            self._update_execute_state()
            self._update_hints()
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
            self._append_log(str(exc))
            return
        self._append_log(f"Membuka folder output: {self.paths.outputs_dir}")


def run_desktop_app(paths: AppPaths) -> None:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = DesktopApp(paths)
    app.mainloop()
