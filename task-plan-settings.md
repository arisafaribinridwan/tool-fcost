## Context
Prioritas implementasi diubah: **bereskan UI dulu**, baru sambungkan logic/service.
Scope UI awal: tambah dua aksi baru (**Pilih/Import Config** dan **Pilih/Import Master**) + status precheck simpel (**Valid / Non Valid**) + alert dialog untuk detail error.

## Task-plan (Checklist ringkas, UI-first)

### Phase 1 — UI Skeleton Lengkap (tanpa logic backend)
- [x] Tambah komponen UI di [app/ui/settings.py][def]:
  - [x] Tombol `Pilih/Import Config (.yaml/.yml)`
  - [x] Tombol `Pilih/Import Master (.csv/.xlsx)`
  - [x] Selector mode config: `Pilih existing` / `Import config`
  - [x] Label status precheck: `Valid` / `Non Valid`
- [x] Tambah area form agar alur jelas secara visual:
  - [x] Input nama job
  - [x] Dropdown config target
  - [x] Section daftar master terpilih (visual list)
- [x] Tambah stub handler UI (no-op / mock event):
  - [x] `on_import_config_click()`
  - [x] `on_import_master_click()`
  - [x] `on_run_precheck_click()` (set label status dummy)
- [x] Tambah pola alert dialog standar (placeholder):
  - [x] Saat status `Non Valid`, detail error hanya lewat alert dialog.

### Phase 2 — UI State & Navigasi Internal (masih tanpa service I/O)
- [x] Hubungkan state visual antar komponen:
  - [x] mode create/edit
  - [x] mode config existing/import
  - [x] list master terpilih (dummy data)
- [x] Pastikan perubahan state tidak menulis file apa pun.
- [x] Rapikan UX tombol (enabled/disabled) sesuai state form.

### Phase 3 — Integrasi Logic (setelah UI disetujui)
- [ ] Wire data nyata job/config (`discover_job_profiles`, `discover_configs`).
- [ ] Implement import config ke `configs/` (service baru).
- [ ] Implement import master ke `masters/` (service baru).
- [ ] Implement precheck bundle config+master.
- [ ] Save final ke `job_profiles.yaml` via `upsert_job_profile_record`.

## Aturan UX yang dikunci
- [x] Status precheck di halaman settings **hanya label**: `Valid` / `Non Valid`.
- [x] Jika `Non Valid` atau error pemeriksaan, detail **hanya** tampil di alert dialog.
- [x] Jangan tampilkan panel detail error di halaman settings.

## File target per fase
- Phase 1–2 (UI-only):
  - [app/ui/settings.py][def]
  - [task-plan-settings.md](task-plan-settings.md)
- Phase 3 (logic):
  - [app/services/config_service.py](app/services/config_service.py)
  - [app/services/source_service.py](app/services/source_service.py)
  - [app/services/preflight_service.py](app/services/preflight_service.py)
  - [app/services/__init__.py](app/services/__init__.py)
  - [app/ui/main_window.py](app/ui/main_window.py)

## QC Checklist Manual (siap eksekusi)
- [ ] Aplikasi terbuka tanpa error; sidebar & detail panel tampil normal.
- [ ] Mode create/edit berpindah dengan benar (klik job vs tombol `+`).
- [ ] Mode config existing/import mengubah enable state:
  - [ ] existing: dropdown config aktif, tombol import config nonaktif.
  - [ ] import: dropdown config nonaktif, tombol import config aktif.
- [ ] Import config menampilkan nama file pada label config import.
- [ ] Import master menambah list visual tanpa duplikasi item yang sama.
- [ ] `Run Precheck` hanya aktif jika nama job + config + master terpenuhi.
- [ ] Precheck gagal menampilkan detail via alert dialog saja.
- [ ] Precheck lulus mengubah badge ke `Valid`.
- [ ] Setelah status `Valid`, perubahan field reset badge ke `Non Valid`.
- [ ] `Simpan Perubahan` hanya aktif saat nama job terisi dan status `Valid`.
- [ ] Selama UI-only, tidak ada file runtime yang ditulis (`configs/`, `masters/`, `job_profiles.yaml`).

## Verification singkat
- [x] UI menampilkan 2 tombol import baru.
- [x] Label precheck tampil dan bisa berubah `Valid/Non Valid` via stub.
- [x] Saat `Non Valid`, detail muncul via alert dialog (bukan inline UI).
- [x] Tidak ada perubahan file runtime (`configs/`, `masters/`, `job_profiles.yaml`) pada fase UI-only.
- [x] UX tombol terhubung ke state form:
  - [x] `Run Precheck` aktif hanya jika nama job + config + master terpenuhi.
  - [x] `Simpan Perubahan` aktif hanya saat nama job terisi dan status precheck `Valid`.
- [x] Perubahan field setelah status `Valid` akan reset status ke `Non Valid`.

[def]: app/ui/settings.py