# Task Plan Perubahan Kolom `action` (mengikuti pola `symptom`)

## Context
Kita akan ubah pengisian `action` agar memakai parameter:
- `job_sheet_section = 1`
- `part_name`
- `symptom_comment`
- `repair_comment`

Komentar final user yang dikunci:
1. `symptom_comment` -> `mode: regex`
2. `repair_comment` -> `mode: regex`
3. Tambah kolom `priority` di sheet `action`
4. Arsitektur pilihan: **upgrade `lookup_rules` umum** (bukan jalur khusus `action`)

Target hasil:
- Rule lebih presisi dan maintainable.
- Hanya row section 1 yang bisa menghasilkan `action`.
- Non-match tetap kosong.
- Priority menentukan rule winner secara deterministik.

## Feasibility
**Memungkinkan** dengan perubahan terkontrol.

Alasan:
- Validator sudah menerima `mode: regex`.
- Runtime `lookup_rules` recipe tinggal di-upgrade agar eksekusi matcher regex dan urutan priority bisa dipakai lintas step.

## Rekomendasi Implementasi (final)

### 1) Update recipe `sub_15_add_action`
File: `configs/monthly-report-recipe.yaml`

Ubah `sub_15_add_action` menjadi 4 matcher:
- `job_sheet_section` (`equals`)
- `part_name` (`equals`)
- `symptom_comment` (`regex`)
- `repair_comment` (`regex`)

Tetap:
- `first_match_wins: true`
- `on_missing_match: null`

Tambahkan konfigurasi urutan rule berbasis prioritas pada `matching`, agar engine umum bisa mengurutkan rule sebelum matching (misalnya field `priority_column: "priority"` dengan default asc).

### 2) Update master `action`
File: `masters/master_table.xlsx` (sheet `action`)

Kolom yang dipakai:
- `priority` (baru, integer positif)
- `job_sheet_section` (baru)
- `part_name`
- `symptom_comment` (regex pattern)
- `repair_comment` (regex pattern)
- `action`

Rule data:
- semua rule aktif `job_sheet_section = 1`
- regex wajib valid
- priority kecil = dievaluasi lebih dulu

### 3) Upgrade engine `lookup_rules` umum
File utama: `app/services/recipe_service.py`

Perubahan engine generik:
- Extend `_matcher_matches`:
  - dukung `mode: regex`
  - compile/match regex dengan error handling yang jelas
- Extend `_apply_lookup_rules_step`:
  - dukung opsi sorting master by priority (generik, tidak hardcode `action`)
  - validasi kolom priority ada jika opsi aktif
  - validasi nilai priority integer positif
  - sort stable (priority asc lalu row order)

Dengan ini, semua step `lookup_rules` bisa memakai kemampuan regex + priority bila diperlukan.

### 4) Validasi schema config (bila perlu)
File: `app/services/config_service.py`

Jika menambah key baru pada `matching` (contoh `priority_column`), perlu perluasan validasi schema agar config tidak ditolak.

## Reuse yang dipakai
- Tetap reuse flow `lookup_rules` existing (tanpa membuat engine baru)
- Reuse util normalisasi existing untuk `equals/contains`
- Reuse pola validasi regex error-friendly seperti di komponen symptom/transform sebagai referensi perilaku

## File kritikal yang akan diubah
1. `configs/monthly-report-recipe.yaml`
2. `masters/master_table.xlsx` (sheet `action`)
3. `app/services/recipe_service.py`
4. `app/services/config_service.py` (jika ada field config baru)
5. `tests/test_pipeline_service.py`
6. `tests/test_config_service.py`

## Rencana Test

### A. Update test E2E monthly recipe
File: `tests/test_pipeline_service.py`
- fixture master `action` pakai kolom baru (`priority`, `job_sheet_section`, `symptom_comment`, `repair_comment`)
- assertion:
  - section != 1 -> `action` kosong
  - section 1 + regex cocok -> `action` terisi
  - efek downstream `defect_category`/`defect` konsisten

### B. Tambah test spesifik regex + priority (lookup_rules umum)
File: `tests/test_pipeline_service.py`
Kasus wajib:
1. regex match keduanya -> success
2. salah satu regex gagal -> kosong
3. section bukan 1 -> kosong
4. dua rule overlap -> priority lebih kecil menang
5. invalid regex -> error runtime jelas
6. invalid priority (non-int / <=0) -> error runtime jelas

### C. Update/ tambah test schema
File: `tests/test_config_service.py`
- pastikan config `lookup_rules` dengan mode regex valid
- jika ada field priority config baru: valid/invalid schema ter-cover

## Risiko & Mitigasi
- **Regex terlalu ketat** -> banyak kosong
  - mitigasi: fallback rule regex generic (`.*`) yang aman
- **Regex invalid di master** -> failure runtime
  - mitigasi: validasi + pesan error spesifik
- **Priority data buruk** -> urutan salah
  - mitigasi: enforce integer positif + stable sort
- **Dampak ke downstream** (`sub-16/17`)
  - mitigasi: wajib verifikasi E2E kolom turunan

## Verification
1. `pytest tests/test_pipeline_service.py -k "action or monthly_step_recipe"`
2. `pytest tests/test_config_service.py`
3. `pytest tests/test_symptom_rules.py`
4. Verifikasi output nyata:
   - `action` hanya terisi saat section=1 dan regex match
   - overlap rule mengikuti priority
   - non-match kosong

## Urutan Implementasi
1. Ubah config `sub_15` (4 matcher, 2 regex, priority-aware matching config)
2. Ubah master `action` (priority + kolom baru)
3. Upgrade engine `lookup_rules` umum (regex + priority sorting)
4. Update test (pipeline + config)
5. Jalankan verification suite dan sanity check output akhir
