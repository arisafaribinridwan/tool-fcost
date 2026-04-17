from __future__ import annotations

from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app import AppPaths
from app.services import (
    ConfigSummary,
    PipelineResult,
    discover_configs,
    run_pipeline,
    validate_source_file,
)
from app.utils import open_in_file_manager


class DesktopApp(ctk.CTk):
    def __init__(self, paths: AppPaths) -> None:
        super().__init__()
        self.paths = paths
        self.source_path: Path | None = None
        self.config_by_label: dict[str, ConfigSummary] = {}
        self._worker_queue: Queue[tuple[str, object]] | None = None
        self._worker_thread: Thread | None = None

        self.title("Excel Automation Tool - CustomTkinter")
        self.geometry("1120x720")
        self.minsize(960, 620)

        self.source_var = ctk.StringVar(value="")
        self.selected_config_var = ctk.StringVar(value="")
        self.config_info_var = ctk.StringVar(value="Belum ada config terpilih.")
        self.status_var = ctk.StringVar(value="Status: Idle")
        self.last_output_var = ctk.StringVar(value="-")

        self._build_layout()
        self.refresh_configs(initial=True)
        self._append_log("Aplikasi siap digunakan.")

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left_panel = ctk.CTkFrame(self, width=360)
        left_panel.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="nsew")
        left_panel.grid_columnconfigure(0, weight=1)

        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            left_panel,
            text="Excel Automation Tool",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        ctk.CTkLabel(
            left_panel,
            text="Pilih source, pilih config YAML, lalu jalankan proses.",
            justify="left",
            wraplength=300,
        ).grid(row=1, column=0, padx=16, pady=(0, 16), sticky="w")

        ctk.CTkLabel(left_panel, text="Source file (.xlsx / .csv)").grid(
            row=2, column=0, padx=16, sticky="w"
        )
        ctk.CTkEntry(left_panel, textvariable=self.source_var).grid(
            row=3, column=0, padx=16, pady=(4, 8), sticky="ew"
        )
        ctk.CTkButton(
            left_panel,
            text="Pilih Source",
            command=self._select_source,
        ).grid(row=4, column=0, padx=16, pady=(0, 16), sticky="ew")

        ctk.CTkLabel(left_panel, text="Config YAML").grid(
            row=5, column=0, padx=16, sticky="w"
        )
        self.config_menu = ctk.CTkOptionMenu(
            left_panel,
            variable=self.selected_config_var,
            values=["Belum ada config"],
            command=self._on_config_selected,
        )
        self.config_menu.grid(row=6, column=0, padx=16, pady=(4, 8), sticky="ew")

        ctk.CTkButton(
            left_panel,
            text="Refresh Config",
            command=self.refresh_configs,
        ).grid(row=7, column=0, padx=16, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(
            left_panel,
            textvariable=self.config_info_var,
            justify="left",
            wraplength=300,
        ).grid(row=8, column=0, padx=16, pady=(0, 16), sticky="w")

        self.execute_button = ctk.CTkButton(
            left_panel,
            text="Execute",
            command=self._execute_pipeline,
            state="disabled",
            height=42,
        )
        self.execute_button.grid(row=9, column=0, padx=16, pady=(0, 8), sticky="ew")

        ctk.CTkButton(
            left_panel,
            text="Buka Folder Outputs",
            command=self._open_outputs_dir,
        ).grid(row=10, column=0, padx=16, pady=(0, 16), sticky="ew")

        ctk.CTkLabel(
            left_panel,
            textvariable=self.status_var,
            justify="left",
            wraplength=300,
        ).grid(row=11, column=0, padx=16, pady=(0, 8), sticky="w")

        ctk.CTkLabel(left_panel, text="Target output").grid(
            row=12, column=0, padx=16, sticky="w"
        )
        ctk.CTkLabel(
            left_panel,
            textvariable=self.last_output_var,
            justify="left",
            wraplength=300,
        ).grid(row=13, column=0, padx=16, pady=(0, 16), sticky="w")

        ctk.CTkLabel(
            right_panel,
            text="Process Log",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self.log_box = ctk.CTkTextbox(right_panel, wrap="word")
        self.log_box.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        self.log_box.configure(state="disabled")

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_status(self, text: str) -> None:
        self.status_var.set(f"Status: {text}")

    def _select_source(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Pilih file source",
            initialdir=str(self.paths.project_root),
            filetypes=[
                ("Excel/CSV", "*.xlsx *.csv"),
                ("Excel", "*.xlsx"),
                ("CSV", "*.csv"),
                ("All Files", "*.*"),
            ],
        )
        if not file_path:
            self._append_log("Pemilihan source dibatalkan.")
            return

        source_path = Path(file_path)
        errors = validate_source_file(source_path)
        if errors:
            error_message = "\n".join(errors)
            messagebox.showerror("Source tidak valid", error_message)
            self._append_log(f"Source invalid: {error_message}")
            return

        self.source_path = source_path
        self.source_var.set(str(source_path))
        self._append_log(f"Source dipilih: {source_path.name}")
        self._update_execute_state()

    def _on_config_selected(self, _: str) -> None:
        self._update_config_info()
        self._update_execute_state()

    def refresh_configs(self, initial: bool = False) -> None:
        config_items = discover_configs(self.paths.configs_dir)
        self.config_by_label = {}
        selectable_labels: list[str] = []
        invalid_count = 0

        for item in config_items:
            label = item.name
            if label in self.config_by_label:
                label = f"{item.name} ({item.path.name})"
            self.config_by_label[label] = item
            if item.is_valid:
                selectable_labels.append(label)
            else:
                invalid_count += 1

        if selectable_labels:
            self.config_menu.configure(values=selectable_labels)
            if self.selected_config_var.get() not in selectable_labels:
                self.selected_config_var.set(selectable_labels[0])
        else:
            placeholder = "Tidak ada config valid"
            self.config_menu.configure(values=[placeholder])
            self.selected_config_var.set(placeholder)

        self._update_config_info()
        self._update_execute_state()

        valid_count = len(selectable_labels)
        if initial:
            self._append_log(
                f"Config loaded: {valid_count} valid, {invalid_count} invalid."
            )
        else:
            self._append_log(
                f"Refresh config selesai: {valid_count} valid, {invalid_count} invalid."
            )

    def _update_config_info(self) -> None:
        selected_label = self.selected_config_var.get()
        selected = self.config_by_label.get(selected_label)
        if selected is None:
            self.config_info_var.set("Belum ada config YAML valid di folder configs/.")
            return
        if selected.is_valid:
            self.config_info_var.set(f"Config aktif: {selected.path.name}")
            return
        self.config_info_var.set(
            "Config invalid: " + "; ".join(selected.errors[:2])
        )

    def _selected_config(self) -> ConfigSummary | None:
        selected = self.config_by_label.get(self.selected_config_var.get())
        if selected is None or not selected.is_valid:
            return None
        return selected

    def _update_execute_state(self) -> None:
        worker_running = self._worker_thread is not None and self._worker_thread.is_alive()
        if worker_running:
            self.execute_button.configure(state="disabled")
            return
        if self.source_path is not None and self._selected_config() is not None:
            self.execute_button.configure(state="normal")
        else:
            self.execute_button.configure(state="disabled")

    def _execute_pipeline(self) -> None:
        config = self._selected_config()
        if self.source_path is None or config is None:
            messagebox.showwarning(
                "Input belum lengkap",
                "Pilih source dan config yang valid terlebih dahulu.",
            )
            return

        worker_running = self._worker_thread is not None and self._worker_thread.is_alive()
        if worker_running:
            return

        self.execute_button.configure(state="disabled")
        self._set_status("Running")
        self._append_log("Eksekusi dimulai.")
        self._worker_queue = Queue()
        self._worker_thread = Thread(
            target=self._run_pipeline_worker,
            args=(self.source_path, config.path, self._worker_queue),
            daemon=True,
        )
        self._worker_thread.start()
        self.after(120, self._poll_worker_events)

    def _run_pipeline_worker(
        self,
        source_path: Path,
        config_path: Path,
        event_queue: Queue[tuple[str, object]],
    ) -> None:
        def worker_log(message: str) -> None:
            event_queue.put(("log", message))

        try:
            result = run_pipeline(
                paths=self.paths,
                source_path=source_path,
                config_path=config_path,
                log=worker_log,
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
            elif kind == "success":
                result = payload
                if isinstance(result, PipelineResult):
                    self.last_output_var.set(str(result.output_path))
                    self._set_status("Sukses")
                    self._append_log(
                        f"Output berhasil dibuat ({result.sheets_written} sheet)."
                    )
            elif kind == "error":
                error_message = str(payload)
                self._set_status("Gagal")
                self._append_log(f"Error: {error_message}")
                messagebox.showerror("Eksekusi gagal", error_message)
            elif kind == "done":
                done_received = True

        if done_received:
            self._worker_queue = None
            self._worker_thread = None
            self._update_execute_state()
            return

        self.after(120, self._poll_worker_events)

    def _open_outputs_dir(self) -> None:
        try:
            open_in_file_manager(self.paths.outputs_dir)
        except RuntimeError as exc:
            messagebox.showerror("Gagal membuka folder", str(exc))
            self._append_log(str(exc))
            return
        self._append_log(f"Membuka folder output: {self.paths.outputs_dir}")


def run_desktop_app(paths: AppPaths) -> None:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = DesktopApp(paths)
    app.mainloop()
