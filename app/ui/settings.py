from pathlib import Path
from tkinter import filedialog, messagebox
import sys

import customtkinter as ctk

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import AppPaths, ensure_runtime_dirs, get_app_paths
from app.services import (
    discover_configs,
    discover_job_profiles,
    get_config_master_refs,
    import_config_to_configs,
    import_master_to_masters,
    run_settings_precheck,
    upsert_job_profile_record,
)

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ── Design Tokens ──────────────────────────────────────────────
C = {
    # Backgrounds
    "sidebar_bg": "#F8FAFC",
    "main_bg": "#FFFFFF",
    "footer_bg": "#F8FAFC",
    "input_bg": "#F8FAFC",
    "preview_bg": "#0F172A",
    "section_bg": "#F1F5F9",
    # Text
    "text_primary": "#0F172A",
    "text_secondary": "#64748B",
    "text_muted": "#94A3B8",
    "text_on_dark": "#E2E8F0",
    # Brand / Accent (slate-blue)
    "accent": "#4F46E5",
    "accent_hover": "#4338CA",
    "accent_light": "#EEF2FF",
    "accent_border": "#C7D2FE",
    "accent_text": "#3730A3",
    "accent_sub": "#6366F1",
    # Borders
    "border": "#E2E8F0",
    "border_strong": "#CBD5E1",
    # Status
    "green": "#22C55E",
    "red": "#EF4444",
    "gray_dot": "#CBD5E1",
    # Buttons
    "btn_danger": "#EF4444",
    "btn_danger_h": "#DC2626",
    "btn_ghost_h": "#E2E8F0",
}


# ── Main App ───────────────────────────────────────────────────
class JobSettingsApp(ctk.CTk):
    def __init__(self, paths: AppPaths):
        super().__init__()
        self.paths = paths
        self.title("Job Configuration")
        self.geometry("680x580")
        self.resizable(False, False)
        self.configure(fg_color=C["main_bg"])

        self.jobs: list[dict] = []
        self.config_options: list[str] = []
        self.selected_config_path: Path | None = None

        self.selected_job_index = 0
        self.job_buttons = []
        self.search_query = ""
        self.filtered_job_indices: list[int] = []

        self.ui_mode = "edit"
        self.config_mode = "Pilih existing"
        self.precheck_status = "Non Valid"

        self.imported_config_path: str | None = None
        self.master_items: list[str] = []
        self.config_master_refs: tuple[str, ...] = ()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._reload_runtime_data()

        self._build_sidebar()
        self._build_main()
        self._apply_job_filter()
        if self.jobs:
            self._load_job_data(0)
        else:
            self._on_add_job()

    # ── SIDEBAR ────────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self,
            width=228,
            corner_radius=0,
            fg_color=C["sidebar_bg"],
            border_width=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(2, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        hdr.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="DAFTAR JOB",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=C["text_muted"],
        ).grid(row=0, column=0, sticky="w")

        self.add_btn = ctk.CTkButton(
            hdr,
            text="+",
            width=26,
            height=26,
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            corner_radius=7,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._on_add_job,
        )
        self.add_btn.grid(row=0, column=1)

        self.search_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="  Cari job...",
            height=34,
            corner_radius=8,
            border_width=1,
            border_color=C["border"],
            fg_color="white",
            font=ctk.CTkFont(size=12),
            text_color=C["text_primary"],
            placeholder_text_color=C["text_muted"],
        )
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        self.search_entry.bind("<KeyRelease>", self._on_search_changed)

        self.job_list_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent", label_text="")
        self.job_list_frame.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 10))
        self.job_list_frame.grid_columnconfigure(0, weight=1)

        self._render_job_list()

        self.job_list_frame.bind("<Configure>", self._resize_job_items)
        self.after(50, self._resize_job_items)

        ctk.CTkFrame(self.sidebar, height=1, fg_color=C["border"]).grid(row=3, column=0, sticky="ew", padx=0)

    def _create_job_item(self, index, job, job_index):
        is_sel = job_index == self.selected_job_index

        btn = ctk.CTkFrame(
            self.job_list_frame,
            width=1,
            height=58,
            fg_color=C["accent_light"] if is_sel else "transparent",
            corner_radius=8,
            border_width=1 if is_sel else 0,
            border_color=C["accent_border"] if is_sel else C["sidebar_bg"],
            cursor="hand2",
        )
        btn.grid(row=index, column=0, sticky="ew", pady=1)
        btn.grid_propagate(False)

        lbl_title = ctk.CTkLabel(
            btn,
            text=job["label"],
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["accent_text"] if is_sel else C["text_primary"],
            fg_color="transparent",
            height=14,
            cursor="hand2",
        )
        lbl_title.place(x=12, y=10)

        lbl_cfg = ctk.CTkLabel(
            btn,
            text=job["config"],
            font=ctk.CTkFont(size=10),
            text_color=C["accent_sub"] if is_sel else C["text_muted"],
            fg_color="transparent",
            height=12,
            cursor="hand2",
        )
        lbl_cfg.place(x=12, y=30)

        dot_color = C["gray_dot"] if not job["enabled"] else C["green"] if job["valid"] else C["red"]
        dot = ctk.CTkFrame(btn, width=7, height=7, corner_radius=4, fg_color=dot_color, cursor="hand2")
        dot.place(relx=1.0, x=-12, y=13, anchor="ne")

        def on_enter(_e, i=index):
            target_btn = self.job_buttons[i]
            if self.selected_job_index != target_btn._job_index:
                target_btn.configure(fg_color="#F1F5F9")

        def on_leave(_e, i=index):
            target_btn = self.job_buttons[i]
            if self.selected_job_index != target_btn._job_index:
                target_btn.configure(fg_color="transparent")

        def on_click(_e, i=index):
            self._load_job_data(self.job_buttons[i]._job_index)

        for w in (btn, lbl_title, lbl_cfg, dot):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

        btn._labels = (lbl_title, lbl_cfg)
        btn._dot = dot
        btn._job_index = job_index
        self.job_buttons.append(btn)

    def _render_job_list(self) -> None:
        self.job_buttons = []
        for child in self.job_list_frame.winfo_children():
            child.destroy()

        if not self.filtered_job_indices:
            ctk.CTkLabel(
                self.job_list_frame,
                text="Tidak ada job yang cocok.",
                font=ctk.CTkFont(size=11, slant="italic"),
                text_color=C["text_muted"],
                anchor="w",
            ).grid(row=0, column=0, sticky="ew", padx=8, pady=8)
            return

        for visible_i, job_i in enumerate(self.filtered_job_indices):
            self._create_job_item(visible_i, self.jobs[job_i], job_i)

    def _resize_job_items(self, _=None):
        w = self.job_list_frame.winfo_width()
        if w <= 1:
            return
        for btn in self.job_buttons:
            btn.configure(width=max(1, w - 4))

    def _on_search_changed(self, _event=None) -> None:
        self.search_query = self.search_entry.get().strip().casefold()
        self._apply_job_filter()

    def _apply_job_filter(self) -> None:
        if not self.search_query:
            self.filtered_job_indices = list(range(len(self.jobs)))
        else:
            self.filtered_job_indices = [
                i
                for i, job in enumerate(self.jobs)
                if self.search_query in job["label"].casefold()
            ]
        self._render_job_list()

    # ── MAIN CONTENT ───────────────────────────────────────────
    def _build_main(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=C["main_bg"], corner_radius=0, border_width=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkFrame(self.main_frame, height=1, fg_color=C["border"], corner_radius=0).grid(row=0, column=0, sticky="ew")

        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(16, 0))
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.content = self.content_frame

        self.lbl_page_title = ctk.CTkLabel(
            self.content,
            text="Detail Konfigurasi (Edit Job)",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=C["text_primary"],
        )
        self.lbl_page_title.grid(row=0, column=0, sticky="w")

        self.lbl_page_sub = ctk.CTkLabel(
            self.content,
            text="Kelola parameter preset kerja, config, dan file master.",
            font=ctk.CTkFont(size=11),
            text_color=C["text_secondary"],
        )
        self.lbl_page_sub.grid(row=1, column=0, sticky="w", pady=(1, 12))

        self._section_label(self.content, "NAMA JOB", row=2)
        self.entry_label = self._entry(self.content, row=3)
        self.entry_label.bind("<KeyRelease>", lambda _e: self._on_form_field_changed())

        self._section_label(self.content, "MODE CONFIG", row=4, pady=(8, 1))
        config_mode_row = ctk.CTkFrame(self.content, fg_color="transparent")
        config_mode_row.grid(row=5, column=0, sticky="ew", pady=(0, 0))
        config_mode_row.grid_columnconfigure(0, weight=1)

        self.config_mode_selector = ctk.CTkSegmentedButton(
            config_mode_row,
            values=["Pilih existing", "Import config"],
            command=self._on_config_mode_changed,
            fg_color=C["section_bg"],
            selected_color=C["accent"],
            selected_hover_color=C["accent_hover"],
            unselected_color="#E2E8F0",
            unselected_hover_color="#CBD5E1",
            text_color="white",
            height=32,
        )
        self.config_mode_selector.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.config_mode_selector.set("Pilih existing")

        self.btn_import_config = ctk.CTkButton(
            config_mode_row,
            text="Pilih/Import Config (.yaml/.yml)",
            height=32,
            fg_color=C["accent_light"],
            text_color=C["accent_text"],
            hover_color="#DDE6FF",
            command=self.on_import_config_click,
        )
        self.btn_import_config.grid(row=0, column=1, sticky="e")

        self.imported_config_label = ctk.CTkLabel(
            self.content,
            text="Config import: belum dipilih",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"],
            anchor="w",
        )
        self.imported_config_label.grid(row=6, column=0, sticky="ew", pady=(5, 0))

        row_cfg = ctk.CTkFrame(self.content, fg_color="transparent")
        row_cfg.grid(row=7, column=0, sticky="ew", pady=(8, 0))
        row_cfg.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            row_cfg,
            text="ATURAN CONFIG",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=C["text_muted"],
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            row_cfg,
            text="STATUS",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=C["text_muted"],
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))

        self.combo_config = ctk.CTkComboBox(
            row_cfg,
            values=self.config_options or [""],
            height=32,
            corner_radius=8,
            border_width=1,
            border_color=C["border"],
            fg_color="white",
            button_color=C["border"],
            button_hover_color=C["border_strong"],
            dropdown_fg_color="white",
            font=ctk.CTkFont(size=12),
            text_color=C["text_primary"],
            command=lambda _value: self._on_form_field_changed(),
        )
        self.combo_config.grid(row=1, column=0, sticky="ew", pady=(3, 0))
        if self.config_options:
            self.combo_config.set(self.config_options[0])

        status_card = ctk.CTkFrame(
            row_cfg,
            fg_color=C["input_bg"],
            corner_radius=8,
            border_width=1,
            border_color=C["border"],
            height=32,
        )
        status_card.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(3, 0))
        status_card.grid_propagate(False)

        self.switch_enabled = ctk.CTkSwitch(
            status_card,
            text="Aktif",
            font=ctk.CTkFont(size=11, weight="bold"),
            switch_width=32,
            switch_height=17,
            progress_color=C["accent"],
            button_color="white",
            button_hover_color="#F0F0F0",
            command=self._on_form_field_changed,
        )
        self.switch_enabled.pack(anchor="center", padx=10, pady=7)

        master_header = ctk.CTkFrame(self.content, fg_color="transparent")
        master_header.grid(row=8, column=0, sticky="ew", pady=(12, 4))
        master_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            master_header,
            text="MASTER FILE INPUT",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=C["text_muted"],
        ).grid(row=0, column=0, sticky="w")

        self.btn_import_master = ctk.CTkButton(
            master_header,
            text="Pilih/Import Master (.csv/.xlsx)",
            height=28,
            fg_color=C["accent_light"],
            text_color=C["accent_text"],
            hover_color="#DDE6FF",
            command=self.on_import_master_click,
        )
        self.btn_import_master.grid(row=0, column=1, sticky="e")

        self.master_list_box = ctk.CTkFrame(
            self.content,
            fg_color="#F8FAFC",
            corner_radius=8,
            border_width=1,
            border_color=C["border"],
            height=80,
        )
        self.master_list_box.grid(row=9, column=0, sticky="ew")
        self.master_list_box.pack_propagate(False)

        self.master_list_content = ctk.CTkScrollableFrame(self.master_list_box, fg_color="transparent", label_text="")
        self.master_list_content.pack(fill="both", expand=True, padx=8, pady=6)

        precheck_row = ctk.CTkFrame(self.content, fg_color="transparent")
        precheck_row.grid(row=10, column=0, sticky="ew", pady=(10, 0))
        precheck_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            precheck_row,
            text="PRECHECK",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=C["text_muted"],
        ).grid(row=0, column=0, sticky="w")

        self.precheck_badge = ctk.CTkLabel(
            precheck_row,
            text="Non Valid",
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=6,
            width=84,
            height=24,
            fg_color="#FEE2E2",
            text_color="#B91C1C",
        )
        self.precheck_badge.grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.btn_run_precheck = ctk.CTkButton(
            precheck_row,
            text="Run Precheck",
            width=118,
            height=28,
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            command=self.on_run_precheck_click,
        )
        self.btn_run_precheck.grid(row=0, column=2, sticky="e")

        self._build_footer()
        self._sync_control_state()

    def _section_label(self, parent, text, row, pady=(8, 3)):
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=C["text_muted"],
        ).grid(row=row, column=0, sticky="w", pady=pady)

    def _entry(self, parent, row):
        e = ctk.CTkEntry(
            parent,
            height=32,
            corner_radius=8,
            border_width=1,
            border_color=C["border"],
            fg_color="white",
            font=ctk.CTkFont(size=12),
            text_color=C["text_primary"],
            placeholder_text_color=C["text_muted"],
        )
        e.grid(row=row, column=0, sticky="ew", pady=(0, 0))
        return e

    def _build_footer(self):
        ctk.CTkFrame(self.main_frame, height=1, fg_color=C["border"], corner_radius=0).grid(row=2, column=0, sticky="ew")

        footer = ctk.CTkFrame(self.main_frame, height=54, fg_color=C["footer_bg"], corner_radius=0)
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(0, weight=1)

        self.footer_hint = ctk.CTkLabel(
            footer,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"],
        )
        self.footer_hint.grid(row=0, column=0, sticky="w", padx=16, pady=16)

        btn_frame = ctk.CTkFrame(footer, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=14, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="Batal",
            fg_color="transparent",
            text_color=C["text_secondary"],
            hover_color=C["btn_ghost_h"],
            width=68,
            height=32,
            corner_radius=8,
            font=ctk.CTkFont(size=11),
            border_width=1,
            border_color=C["border"],
            command=self.quit,
        ).pack(side="left", padx=(0, 8))

        self.btn_save = ctk.CTkButton(
            btn_frame,
            text="Simpan Perubahan",
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            text_color="white",
            width=130,
            height=32,
            corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_save,
        )
        self.btn_save.pack(side="left")

    # ── DATA SOURCE (RUNTIME) ───────────────────────────────────
    def _reload_runtime_data(self) -> None:
        self.jobs = []
        for item in discover_job_profiles(self.paths.configs_dir):
            self.jobs.append(
                {
                    "id": item.id,
                    "label": item.label,
                    "config": item.config_file,
                    "enabled": item.enabled,
                    "valid": item.is_valid,
                    "masters": list(item.master_files),
                }
            )

        configs = discover_configs(self.paths.configs_dir)
        self.config_options = [
            cfg.path.name
            for cfg in configs
            if cfg.path.name.casefold() != "job_profiles.yaml"
        ]

    # ── UI STATE ────────────────────────────────────────────────
    def _set_mode(self, mode: str) -> None:
        self.ui_mode = mode
        if mode == "create":
            self.lbl_page_title.configure(text="Detail Konfigurasi (Create Job)")
            self.footer_hint.configure(text="Mode: Create job baru")
            return
        self.lbl_page_title.configure(text="Detail Konfigurasi (Edit Job)")

    def _on_config_mode_changed(self, value: str) -> None:
        self.config_mode = value
        if self.config_mode == "Pilih existing":
            self.imported_config_label.configure(text="Config import: belum dipilih", text_color=C["text_muted"])
            self.imported_config_path = None
        else:
            text = "Config import: belum dipilih"
            if self.imported_config_path:
                text = f"Config import: {Path(self.imported_config_path).name}"
            self.imported_config_label.configure(text=text, text_color=C["accent_text"])
        self._sync_control_state()

    def _sync_control_state(self) -> None:
        use_existing = self.config_mode == "Pilih existing"

        if hasattr(self, "combo_config"):
            self.combo_config.configure(state="normal" if use_existing else "disabled")
        if hasattr(self, "btn_import_config"):
            self.btn_import_config.configure(state="disabled" if use_existing else "normal")

        if use_existing:
            selected_name = self.combo_config.get().strip() if hasattr(self, "combo_config") else ""
            self.selected_config_path = self.paths.configs_dir / selected_name if selected_name else None
        else:
            self.selected_config_path = Path(self.imported_config_path) if self.imported_config_path else None

        self._refresh_selected_config_master_refs()

        has_job_name = bool(getattr(self, "entry_label", None) and self.entry_label.get().strip())
        has_required_master = not self.config_master_refs or bool(self.master_items)
        has_config = self.selected_config_path is not None
        can_run_precheck = has_job_name and has_config and has_required_master
        if hasattr(self, "btn_run_precheck"):
            self.btn_run_precheck.configure(state="normal" if can_run_precheck else "disabled")

        can_save = bool(getattr(self, "entry_label", None) and self.entry_label.get().strip()) and self.precheck_status == "Valid"
        if hasattr(self, "btn_save"):
            self.btn_save.configure(state="normal" if can_save else "disabled")

    def _refresh_selected_config_master_refs(self) -> None:
        if self.selected_config_path is None:
            self.config_master_refs = ()
            return
        try:
            self.config_master_refs = get_config_master_refs(self.selected_config_path)
        except ValueError:
            self.config_master_refs = ()

    def _set_precheck_status(self, is_valid: bool, detail: str | None = None) -> None:
        self.precheck_status = "Valid" if is_valid else "Non Valid"
        if is_valid:
            self.precheck_badge.configure(text="Valid", fg_color="#DCFCE7", text_color="#15803D")
            self._sync_control_state()
            return
        self.precheck_badge.configure(text="Non Valid", fg_color="#FEE2E2", text_color="#B91C1C")
        self._sync_control_state()
        if detail:
            messagebox.showwarning("Precheck Non Valid", detail)

    def _on_form_field_changed(self) -> None:
        if self.precheck_status == "Valid":
            self._set_precheck_status(False)
            return
        self._sync_control_state()

    # ── DATA LOADING ───────────────────────────────────────────
    def _load_job_data(self, index):
        for btn in self.job_buttons:
            lbl_title, lbl_cfg = btn._labels
            is_sel = btn._job_index == index
            btn.configure(
                fg_color=C["accent_light"] if is_sel else "transparent",
                border_width=1 if is_sel else 0,
                border_color=C["accent_border"] if is_sel else C["sidebar_bg"],
            )
            lbl_title.configure(text_color=C["accent_text"] if is_sel else C["text_primary"])
            lbl_cfg.configure(text_color=C["accent_sub"] if is_sel else C["text_muted"])

        self.selected_job_index = index
        self._set_mode("edit")

        job = self.jobs[index]

        self.entry_label.delete(0, "end")
        self.entry_label.insert(0, job["label"])

        combo_values = tuple(self.combo_config.cget("values"))
        if job["config"] in combo_values:
            self.combo_config.set(job["config"])
        elif combo_values:
            self.combo_config.set(combo_values[0])
        else:
            self.combo_config.set("")

        if job["enabled"]:
            self.switch_enabled.select()
        else:
            self.switch_enabled.deselect()

        self.master_items = list(job.get("masters", []))
        self._refresh_master_list_box()

        self.footer_hint.configure(text=f"ID: {job['id']}  ·  {job['config']}")

        self.imported_config_path = None
        self.config_mode_selector.set("Pilih existing")
        self._on_config_mode_changed("Pilih existing")

        self._set_precheck_status(bool(job["valid"] and job["enabled"]))

    def _refresh_master_list_box(self) -> None:
        for child in self.master_list_content.winfo_children():
            child.destroy()

        if not self.master_items:
            ctk.CTkLabel(
                self.master_list_content,
                text="Belum ada master dipilih.",
                font=ctk.CTkFont(size=11, slant="italic"),
                text_color=C["text_muted"],
                anchor="w",
            ).pack(fill="x", padx=4, pady=3)
            return

        for item in self.master_items:
            row = ctk.CTkFrame(self.master_list_content, fg_color="transparent")
            row.pack(fill="x", padx=2, pady=1)

            ctk.CTkLabel(
                row,
                text="•",
                width=12,
                height=14,
                text_color=C["text_secondary"],
                font=ctk.CTkFont(size=11),
            ).pack(side="left")

            ctk.CTkLabel(
                row,
                text=item,
                anchor="w",
                height=14,
                text_color=C["text_primary"],
                font=ctk.CTkFont(size=11),
            ).pack(side="left", fill="x", expand=True)

    # ── ACTIONS ────────────────────────────────────────────────
    def on_import_config_click(self) -> None:
        selected = filedialog.askopenfilename(
            title="Pilih file config",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
        )
        if not selected:
            return

        try:
            imported = import_config_to_configs(Path(selected), self.paths.configs_dir)
        except ValueError as exc:
            messagebox.showerror("Import config gagal", str(exc))
            return

        self.imported_config_path = str(imported)
        self._reload_runtime_data()
        self._apply_job_filter()
        self.combo_config.configure(values=self.config_options or [""])
        self.config_mode_selector.set("Import config")
        self._on_config_mode_changed("Import config")
        self._set_precheck_status(False)
        self._sync_control_state()

        messagebox.showinfo("Config diimport", f"Config terimport: {imported.name}")

    def on_import_master_click(self) -> None:
        selected_items = filedialog.askopenfilenames(
            title="Pilih file master",
            filetypes=[
                ("Master files", "*.csv *.xlsx"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx"),
                ("All files", "*.*"),
            ],
        )
        if not selected_items:
            return

        added = 0
        for selected in selected_items:
            try:
                imported = import_master_to_masters(Path(selected), self.paths.masters_dir)
            except ValueError as exc:
                messagebox.showerror("Import master gagal", str(exc))
                continue

            relative_like = f"masters/{imported.name}"
            if relative_like not in self.master_items:
                self.master_items.append(relative_like)
                added += 1

        self._refresh_master_list_box()
        self._set_precheck_status(False)
        self._sync_control_state()

        messagebox.showinfo("Master diimport", f"{added} file master ditambahkan.")

    def on_run_precheck_click(self) -> None:
        errors: list[str] = []

        if not self.entry_label.get().strip():
            errors.append("Nama job wajib diisi.")

        if self.config_mode == "Pilih existing" and not self.combo_config.get().strip():
            errors.append("Config existing wajib dipilih.")
        if self.config_mode == "Import config" and not self.imported_config_path:
            errors.append("Config import belum dipilih.")

        if self.config_master_refs and not self.master_items:
            errors.append("Config ini membutuhkan minimal satu file master.")

        if errors:
            self._set_precheck_status(False, "\n".join(errors))
            return

        config_path = self.selected_config_path
        if config_path is None:
            self._set_precheck_status(False, "Config belum dipilih.")
            return

        try:
            result = run_settings_precheck(paths=self.paths, config_path=config_path)
        except Exception as exc:
            self._set_precheck_status(False, str(exc))
            return

        if result.can_execute:
            self._set_precheck_status(True)
            return

        detail = "\n".join(item.summary for item in result.findings if item.severity == "error")
        self._set_precheck_status(False, detail or "Precheck gagal.")

    def _on_add_job(self):
        self._set_mode("create")

        for i, btn in enumerate(self.job_buttons):
            lbl_title, lbl_cfg = btn._labels
            btn.configure(fg_color="transparent", border_width=0, border_color=C["sidebar_bg"])
            lbl_title.configure(text_color=C["text_primary"])
            lbl_cfg.configure(text_color=C["text_muted"])
        self.selected_job_index = -1

        self.entry_label.delete(0, "end")
        self.switch_enabled.select()

        values = self.combo_config.cget("values")
        if values:
            self.combo_config.set(values[0])

        self.imported_config_path = None
        self.config_mode_selector.set("Pilih existing")
        self._on_config_mode_changed("Pilih existing")

        self.master_items = []
        self._refresh_master_list_box()
        self._set_precheck_status(False)

        self.footer_hint.configure(text="Mode: Create job baru")
        self._sync_control_state()

    def _on_save(self):
        if self.precheck_status != "Valid":
            messagebox.showwarning("Simpan Perubahan", "Jalankan precheck valid terlebih dahulu.")
            return

        label = self.entry_label.get().strip()
        enabled = bool(self.switch_enabled.get())
        config_path = self.selected_config_path
        config_name = config_path.name if config_path is not None else ""

        if not label:
            messagebox.showwarning("Simpan Perubahan", "Nama job wajib diisi.")
            return
        if not config_name:
            messagebox.showwarning("Simpan Perubahan", "Config wajib dipilih.")
            return

        record_id = None
        if self.ui_mode == "edit" and self.selected_job_index >= 0 and self.selected_job_index < len(self.jobs):
            record_id = self.jobs[self.selected_job_index]["id"]

        try:
            saved = upsert_job_profile_record(
                self.paths.configs_dir,
                label=label,
                config_file=config_name,
                enabled=enabled,
                record_id=record_id,
            )
        except ValueError as exc:
            messagebox.showerror("Simpan Perubahan gagal", str(exc))
            return

        self._reload_runtime_data()
        self._apply_job_filter()
        self.combo_config.configure(values=self.config_options or [""])

        selected_index = next((i for i, job in enumerate(self.jobs) if job["id"] == saved.id), -1)
        if selected_index >= 0:
            self._load_job_data(selected_index)
        else:
            self._on_add_job()

        messagebox.showinfo("Simpan Perubahan", "Perubahan berhasil disimpan ke job_profiles.yaml.")


if __name__ == "__main__":
    app = JobSettingsApp(ensure_runtime_dirs(get_app_paths()))
    app.mainloop()
