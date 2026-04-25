import customtkinter as ctk
from PIL import Image

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ── Design Tokens ──────────────────────────────────────────────
C = {
    # Backgrounds
    "sidebar_bg":    "#F8FAFC",
    "main_bg":       "#FFFFFF",
    "footer_bg":     "#F8FAFC",
    "input_bg":      "#F8FAFC",
    "preview_bg":    "#0F172A",
    "section_bg":    "#F1F5F9",

    # Text
    "text_primary":  "#0F172A",
    "text_secondary":"#64748B",
    "text_muted":    "#94A3B8",
    "text_on_dark":  "#E2E8F0",

    # Brand / Accent (slate-blue)
    "accent":        "#4F46E5",
    "accent_hover":  "#4338CA",
    "accent_light":  "#EEF2FF",
    "accent_border": "#C7D2FE",
    "accent_text":   "#3730A3",
    "accent_sub":    "#6366F1",

    # Borders
    "border":        "#E2E8F0",
    "border_strong": "#CBD5E1",

    # Status
    "green":         "#22C55E",
    "red":           "#EF4444",
    "gray_dot":      "#CBD5E1",

    # Buttons
    "btn_danger":    "#EF4444",
    "btn_danger_h":  "#DC2626",
    "btn_ghost_h":   "#E2E8F0",
}

FONT = {
    "h1":    ("bold", 17),
    "h2":    ("bold", 13),
    "body":  ("normal", 12),
    "small": ("normal", 11),
    "label": ("bold", 9),
    "mono":  ("normal", 11),
}

def mk_font(key, override_weight=None, override_size=None):
    weight, size = FONT[key]
    return ctk.CTkFont(
        family="SF Pro Display" if key in ("h1", "h2") else "SF Pro Text",
        size=override_size or size,
        weight=override_weight or weight
    )


# ── Main App ───────────────────────────────────────────────────
class JobSettingsApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Job Configuration")
        self.geometry("720x460")
        self.resizable(False, False)
        self.configure(fg_color=C["main_bg"])

        self.jobs = [
            {"id": "1", "label": "Laporan Bulanan",  "config": "monthly-report.yaml",  "enabled": True,  "valid": True,  "masters": ["masters/table_a.xlsx", "masters/ref_b.xlsx"]},
            {"id": "2", "label": "Sync Mingguan",    "config": "weekly-sync.yaml",     "enabled": True,  "valid": True,  "masters": ["masters/data.csv"]},
            {"id": "3", "label": "Validasi Error",   "config": "error-config.yaml",    "enabled": True,  "valid": False, "masters": []},
        ]
        self.selected_job_index = 0
        self.job_buttons = []

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self._load_job_data(0)

    # ── SIDEBAR ────────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=228, corner_radius=0,
            fg_color=C["sidebar_bg"],
            border_width=0
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(2, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        # ── Header row
        hdr = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        hdr.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="DAFTAR JOB",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=C["text_muted"]
        ).grid(row=0, column=0, sticky="w")

        self.add_btn = ctk.CTkButton(
            hdr, text="+", width=26, height=26,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            corner_radius=7,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._on_add_job
        )
        self.add_btn.grid(row=0, column=1)

        # ── Search
        self.search_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="  Cari job...",
            height=34, corner_radius=8,
            border_width=1,
            border_color=C["border"],
            fg_color="white",
            font=ctk.CTkFont(size=12),
            text_color=C["text_primary"],
            placeholder_text_color=C["text_muted"]
        )
        self.search_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        # ── Job List
        self.job_list_frame = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent", label_text=""
        )
        self.job_list_frame.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 10))
        self.job_list_frame.grid_columnconfigure(0, weight=1)

        for i, job in enumerate(self.jobs):
            self._create_job_item(i, job)

        self.job_list_frame.bind("<Configure>", self._resize_job_items)
        self.after(50, self._resize_job_items)

        # ── Sidebar bottom divider
        ctk.CTkFrame(
            self.sidebar, height=1, fg_color=C["border"]
        ).grid(row=3, column=0, sticky="ew", padx=0)

    def _create_job_item(self, index, job):
        is_sel = (index == self.selected_job_index)

        btn = ctk.CTkFrame(
            self.job_list_frame,
            width=1, height=58,
            fg_color=C["accent_light"] if is_sel else "transparent",
            corner_radius=8,
            border_width=1 if is_sel else 0,
            border_color=C["accent_border"] if is_sel else C["sidebar_bg"],
            cursor="hand2"
        )
        btn.grid(row=index, column=0, sticky="ew", pady=1)
        btn.grid_propagate(False)

        lbl_title = ctk.CTkLabel(
            btn, text=job["label"],
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["accent_text"] if is_sel else C["text_primary"],
            fg_color="transparent",
            height=14,
            cursor="hand2"
        )
        lbl_title.place(x=12, y=10)

        lbl_cfg = ctk.CTkLabel(
            btn, text=job["config"],
            font=ctk.CTkFont(size=10),
            text_color=C["accent_sub"] if is_sel else C["text_muted"],
            fg_color="transparent",
            height=12,
            cursor="hand2"
        )
        lbl_cfg.place(x=12, y=30)

        # Status dot
        dot_color = (
            C["gray_dot"] if not job["enabled"]
            else C["green"] if job["valid"]
            else C["red"]
        )
        dot = ctk.CTkFrame(btn, width=7, height=7, corner_radius=4, fg_color=dot_color, cursor="hand2")
        dot.place(relx=1.0, x=-12, y=13, anchor="ne")

        def on_enter(e, i=index):
            if self.selected_job_index != i:
                self.job_buttons[i].configure(fg_color="#F1F5F9")

        def on_leave(e, i=index):
            if self.selected_job_index != i:
                self.job_buttons[i].configure(fg_color="transparent")

        def on_click(e, i=index):
            self._load_job_data(i)

        for w in (btn, lbl_title, lbl_cfg, dot):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

        btn._labels = (lbl_title, lbl_cfg)
        btn._dot    = dot
        self.job_buttons.append(btn)

    def _resize_job_items(self, _=None):
        w = self.job_list_frame.winfo_width()
        if w <= 1:
            return
        for btn in self.job_buttons:
            btn.configure(width=max(1, w - 4))

    # ── MAIN CONTENT ───────────────────────────────────────────
    def _build_main(self):
        self.main_frame = ctk.CTkFrame(
            self, fg_color=C["main_bg"], corner_radius=0,
            border_width=0
        )
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # ── Top border
        ctk.CTkFrame(
            self.main_frame, height=1, fg_color=C["border"], corner_radius=0
        ).grid(row=0, column=0, sticky="ew")

        # ── Scrollable content area
        self.content = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=20, pady=(16, 0))
        self.content.grid_columnconfigure(0, weight=1)

        # Page header
        self.lbl_page_title = ctk.CTkLabel(
            self.content, text="Detail Konfigurasi",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=C["text_primary"]
        )
        self.lbl_page_title.grid(row=0, column=0, sticky="w")

        self.lbl_page_sub = ctk.CTkLabel(
            self.content,
            text="Kelola parameter preset kerja dan file master sistem.",
            font=ctk.CTkFont(size=11),
            text_color=C["text_secondary"]
        )
        self.lbl_page_sub.grid(row=1, column=0, sticky="w", pady=(1, 12))

        # ── Section: Job Info
        self._section_label(self.content, "NAMA JOB", row=2)
        self.entry_label = self._entry(self.content, row=3)

        # ── Section: Config + Status row
        row_cfg = ctk.CTkFrame(self.content, fg_color="transparent")
        row_cfg.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        row_cfg.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(row_cfg, text="ATURAN CONFIG",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=C["text_muted"]
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(row_cfg, text="STATUS",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=C["text_muted"]
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))

        self.combo_config = ctk.CTkComboBox(
            row_cfg,
            values=["monthly-report.yaml", "weekly-sync.yaml", "error-config.yaml", "daily.yaml"],
            height=32, corner_radius=8, border_width=1,
            border_color=C["border"],
            fg_color="white",
            button_color=C["border"],
            button_hover_color=C["border_strong"],
            dropdown_fg_color="white",
            font=ctk.CTkFont(size=12),
            text_color=C["text_primary"]
        )
        self.combo_config.grid(row=1, column=0, sticky="ew", pady=(3, 0))

        # Status card
        status_card = ctk.CTkFrame(
            row_cfg, fg_color=C["input_bg"],
            corner_radius=8, border_width=1,
            border_color=C["border"], height=32
        )
        status_card.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(3, 0))
        status_card.grid_propagate(False)

        self.switch_enabled = ctk.CTkSwitch(
            status_card, text="Aktif",
            font=ctk.CTkFont(size=11, weight="bold"),
            switch_width=32, switch_height=17,
            progress_color=C["accent"],
            button_color="white",
            button_hover_color="#F0F0F0"
        )
        self.switch_enabled.pack(anchor="center", padx=10, pady=7)

        # ── Section: Master Files
        self._section_label(self.content, "PREVIEW FILE MASTER", row=5, pady=(12, 4))

        self.preview_box = ctk.CTkFrame(
            self.content,
            fg_color=C["preview_bg"],
            corner_radius=10, height=90
        )
        self.preview_box.grid(row=6, column=0, sticky="ew")
        self.preview_box.grid_propagate(False)
        self.preview_box.grid_columnconfigure(0, weight=1)

        # ── Validation badge row
        self.badge_row = ctk.CTkFrame(self.content, fg_color="transparent")
        self.badge_row.grid(row=7, column=0, sticky="ew", pady=(8, 0))
        self.badge_row.grid_columnconfigure(0, weight=1)

        self.validity_badge = ctk.CTkLabel(
            self.badge_row, text="",
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=5, height=22, width=10
        )
        self.validity_badge.grid(row=0, column=0, sticky="w")

        # ── Footer
        self._build_footer()

    def _section_label(self, parent, text, row, pady=(8, 3)):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=C["text_muted"]
        ).grid(row=row, column=0, sticky="w", pady=pady)

    def _entry(self, parent, row):
        e = ctk.CTkEntry(
            parent, height=32, corner_radius=8,
            border_width=1, border_color=C["border"],
            fg_color="white",
            font=ctk.CTkFont(size=12),
            text_color=C["text_primary"],
            placeholder_text_color=C["text_muted"]
        )
        e.grid(row=row, column=0, sticky="ew", pady=(3, 0))
        return e

    def _build_footer(self):
        # Thin top border
        ctk.CTkFrame(
            self.main_frame, height=1,
            fg_color=C["border"], corner_radius=0
        ).grid(row=2, column=0, sticky="ew")

        footer = ctk.CTkFrame(
            self.main_frame, height=54,
            fg_color=C["footer_bg"], corner_radius=0
        )
        footer.grid(row=3, column=0, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(0, weight=1)

        # Left: job id hint
        self.footer_hint = ctk.CTkLabel(
            footer, text="",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"]
        )
        self.footer_hint.grid(row=0, column=0, sticky="w", padx=16, pady=16)

        # Right: buttons
        btn_frame = ctk.CTkFrame(footer, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=14, pady=10)

        ctk.CTkButton(
            btn_frame, text="Batal",
            fg_color="transparent",
            text_color=C["text_secondary"],
            hover_color=C["btn_ghost_h"],
            width=68, height=32, corner_radius=8,
            font=ctk.CTkFont(size=11),
            border_width=1, border_color=C["border"],
            command=self.quit
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Simpan Perubahan",
            fg_color=C["accent"], hover_color=C["accent_hover"],
            text_color="white",
            width=130, height=32, corner_radius=8,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_save
        ).pack(side="left")

    # ── DATA LOADING ───────────────────────────────────────────
    def _load_job_data(self, index):
        # Update sidebar selection
        for i, btn in enumerate(self.job_buttons):
            lbl_title, lbl_cfg = btn._labels
            is_sel = (i == index)
            btn.configure(
                fg_color=C["accent_light"] if is_sel else "transparent",
                border_width=1 if is_sel else 0,
                border_color=C["accent_border"] if is_sel else C["sidebar_bg"]
            )
            lbl_title.configure(text_color=C["accent_text"] if is_sel else C["text_primary"])
            lbl_cfg.configure(text_color=C["accent_sub"] if is_sel else C["text_muted"])

        self.selected_job_index = index
        job = self.jobs[index]

        # Fill form fields
        self.entry_label.delete(0, "end")
        self.entry_label.insert(0, job["label"])
        self.combo_config.set(job["config"])

        if job["enabled"]:
            self.switch_enabled.select()
        else:
            self.switch_enabled.deselect()

        # Footer hint
        self.footer_hint.configure(text=f"ID: {job['id']}  ·  {job['config']}")

        # Validation badge
        if not job["enabled"]:
            badge_text  = "  ● Dinonaktifkan"
            badge_fg    = C["section_bg"]
            badge_color = C["text_muted"]
        elif job["valid"]:
            badge_text  = "  ✓ Konfigurasi Valid"
            badge_fg    = "#DCFCE7"
            badge_color = "#15803D"
        else:
            badge_text  = "  ✕ Konfigurasi Error"
            badge_fg    = "#FEE2E2"
            badge_color = "#B91C1C"

        self.validity_badge.configure(
            text=badge_text,
            fg_color=badge_fg,
            text_color=badge_color
        )

        # Master file preview
        for child in self.preview_box.winfo_children():
            child.destroy()

        if job["masters"]:
            for m in job["masters"]:
                row = ctk.CTkFrame(self.preview_box, fg_color="transparent")
                row.pack(fill="x", padx=14, pady=(8, 0))

                ctk.CTkLabel(
                    row, text="◆",
                    font=ctk.CTkFont(size=8),
                    text_color="#475569",
                    fg_color="transparent"
                ).pack(side="left", padx=(0, 6))

                ctk.CTkLabel(
                    row, text=m,
                    font=ctk.CTkFont(family="Courier New", size=11),
                    text_color="#CBD5E1",
                    fg_color="transparent", anchor="w"
                ).pack(side="left")
        else:
            ctk.CTkLabel(
                self.preview_box,
                text="Tidak ada file master terdaftar.",
                font=ctk.CTkFont(size=11, slant="italic"),
                text_color="#475569",
                fg_color="transparent"
            ).pack(expand=True)

    # ── ACTIONS ────────────────────────────────────────────────
    def _on_add_job(self):
        print("Tambah job baru...")

    def _on_save(self):
        job = self.jobs[self.selected_job_index]
        job["label"]   = self.entry_label.get()
        job["config"]  = self.combo_config.get()
        job["enabled"] = bool(self.switch_enabled.get())

        # Refresh sidebar label
        btn = self.job_buttons[self.selected_job_index]
        lbl_title, lbl_cfg = btn._labels
        lbl_title.configure(text=job["label"])
        lbl_cfg.configure(text=job["config"])

        print(f"[SAVED] {job}")


if __name__ == "__main__":
    app = JobSettingsApp()
    app.mainloop()
