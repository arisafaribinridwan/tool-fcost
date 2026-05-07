# Plan: Rekomendasi 3 — Highlight Sementara Baris Baru di File Target

## Ide

Setiap baris yang baru di-append ke sheet `raw` di file target diberi fill warna (misal hijau muda).
Sebelum append dimulai, fill di semua baris data yang sudah ada direset ke putih terlebih dahulu.
Hasilnya: setiap kali job dijalankan, warna selalu menunjuk tepat ke batch terbaru saja — tidak menumpuk.

---

## File yang Diubah

| File | Perubahan |
|------|-----------|
| `app/services/target_workbook_update_service.py` | Tambah 2 helper, tambah param `new_row_color`, apply fill di loop append |
| `app/services/pipeline_service.py` | Baca `new_row_color` dari config, teruskan ke service |
| `configs/monthly-report-recipe-autofill-raw.yaml` | Tambah key `new_row_color` di `target_update` (opsional) |

---

## Langkah Implementasi

### 1. `target_workbook_update_service.py` — Tambah import

```python
# Tambahkan di baris 8, setelah import Worksheet
from openpyxl.styles import PatternFill
```

---

### 2. `target_workbook_update_service.py` — Tambah 2 helper function

Tambahkan setelah fungsi `_filter_new_rows` (sekitar baris 111):

```python
_NO_FILL = PatternFill(fill_type=None)


def _clear_data_row_fills(worksheet: Worksheet) -> None:
    """Reset fill semua baris data (baris 2 ke bawah) ke tanpa warna."""
    if worksheet.max_row < 2:
        return
    for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
        for cell in row:
            cell.fill = _NO_FILL


def _apply_row_fill(worksheet: Worksheet, row_idx: int, col_count: int, color: str) -> None:
    """Beri fill warna ke seluruh sel pada baris tertentu."""
    fill = PatternFill(fill_type="solid", fgColor=color.upper())
    for col_idx in range(1, col_count + 1):
        worksheet.cell(row=row_idx, column=col_idx).fill = fill
```

---

### 3. `target_workbook_update_service.py` — Tambah parameter `new_row_color`

Ubah signature fungsi `update_target_workbooks_by_model_series` (baris 114):

```python
# SEBELUM
def update_target_workbooks_by_model_series(
    *,
    data_df: pd.DataFrame,
    target_dir: Path,
    match_column: str,
    target_sheet_name: str,
    filter_column: str | None = None,
    filter_value: object | None = None,
    duplicate_key_columns: tuple[str, ...] = (),
) -> list[TargetFileUpdateResult]:

# SESUDAH — tambahkan 1 parameter baru di akhir
def update_target_workbooks_by_model_series(
    *,
    data_df: pd.DataFrame,
    target_dir: Path,
    match_column: str,
    target_sheet_name: str,
    filter_column: str | None = None,
    filter_value: object | None = None,
    duplicate_key_columns: tuple[str, ...] = (),
    new_row_color: str | None = None,   # ← TAMBAH INI
) -> list[TargetFileUpdateResult]:
```

---

### 4. `target_workbook_update_service.py` — Apply highlight di loop append

Cari blok append rows (sekitar baris 225–233). Ganti:

```python
# SEBELUM
for _, row in matched_df.iterrows():
    row_values: list[object] = []
    for target_column in target_columns:
        if target_column in matched_df.columns:
            value = row.get(target_column)
            row_values.append(None if pd.isna(value) else value)
        else:
            row_values.append(None)
    worksheet.append(row_values)
```

```python
# SESUDAH
if new_row_color:
    _clear_data_row_fills(worksheet)

for _, row in matched_df.iterrows():
    row_values: list[object] = []
    for target_column in target_columns:
        if target_column in matched_df.columns:
            value = row.get(target_column)
            row_values.append(None if pd.isna(value) else value)
        else:
            row_values.append(None)
    worksheet.append(row_values)
    if new_row_color:
        _apply_row_fill(worksheet, worksheet.max_row, len(target_columns), new_row_color)
```

> `_clear_data_row_fills` dipanggil **hanya jika ada baris baru yang akan ditulis** (karena blok ini sudah berada setelah pengecekan `matched_df.empty`). Aman — tidak akan menghapus highlight jika tidak ada data baru.

---

### 5. `pipeline_service.py` — Baca dan teruskan `new_row_color`

Cari blok `target_update_cfg` (sekitar baris 252–259). Tambahkan pembacaan `new_row_color`:

```python
# Tambahkan setelah baris pembacaan duplicate_key_columns
new_row_color: str | None = None
raw_new_row_color = target_update_cfg.get("new_row_color")
if isinstance(raw_new_row_color, str) and raw_new_row_color.strip():
    new_row_color = raw_new_row_color.strip()
```

Lalu teruskan ke function call (sekitar baris 264):

```python
update_results = update_target_workbooks_by_model_series(
    data_df=source_df,
    target_dir=target_folder_path,
    match_column=match_column,
    target_sheet_name=target_sheet_name,
    filter_column=filter_column,
    filter_value=filter_value,
    duplicate_key_columns=duplicate_key_columns,
    new_row_color=new_row_color,   # ← TAMBAH INI
)
```

---

### 6. YAML Config — Tambah key `new_row_color` (opsional)

```yaml
# configs/monthly-report-recipe-autofill-raw.yaml
target_update:
  enabled: true
  match_column: "model_series"
  sheet_name: "raw"
  new_row_color: "E2EFDA"   # ← TAMBAH INI (hijau muda). Hapus baris ini untuk nonaktifkan.
  source_filter:
    column: "job_sheet_section"
    equals: 1
  duplicate_key_columns:
    - "notification"
    - "model_series"
    - "part_used"
```

> Warna menggunakan hex 6 karakter tanpa `#`. Contoh lain: `"FFF2CC"` (kuning), `"DDEEFF"` (biru muda).
> Jika key tidak ada di YAML, fitur highlight tidak aktif — backward compatible dengan job lain.

---

## Catatan Penting

- **`_clear_data_row_fills` hanya dipanggil jika ada baris baru** — tidak akan menghapus highlight pada file yang di-skip.
- **Kolom header (baris 1) tidak disentuh** — clear dimulai dari `min_row=2`.
- **Performa**: untuk file target dengan ratusan ribu baris, iterasi seluruh baris untuk reset fill bisa lambat. Jika jadi masalah, bisa diganti dengan hanya reset baris-baris yang sebelumnya punya fill (openpyxl track ini via `cell.fill.fill_type`).
- **Tidak ada perubahan pada `output_service.py`** — highlight ini di file *target*, bukan di file output preview.

---

# Plan: Upgrade Pembacaan Symptom dengan Fallback Source Columns

## Ide

Saat ini kolom `symptom` hanya ditentukan dari kombinasi:

1. `part_name`
2. `symptom_comment`

Akibatnya, rule master `symptom` seperti `PANEL + regex blank` tidak akan match jika kata `blank` hanya muncul di kolom lain, misalnya `repair_comment` atau `symptom_code_description`.

Upgrade yang diinginkan adalah membuat pembacaan symptom mencoba beberapa kolom secara berurutan:

1. `symptom_comment`
2. `repair_comment`
3. `symptom_code_description`

Dengan urutan ini, behavior lama tetap diprioritaskan. `repair_comment` menjadi fallback kedua karena sering memuat kata kunci hasil perbaikan seperti `BLANK`, sedangkan `symptom_code_description` menjadi fallback terakhir.

---

## Prinsip Matching yang Direkomendasikan

Urutan fallback harus memakai pola **kolom dulu, rule priority kemudian**:

```text
Untuk setiap baris source:
  cocokkan part_name dengan rule master symptom
  coba semua rule berdasarkan priority terhadap symptom_comment
  kalau belum ada hasil, coba semua rule berdasarkan priority terhadap repair_comment
  kalau belum ada hasil, coba semua rule berdasarkan priority terhadap symptom_code_description
  kalau tetap belum ada hasil, pakai on_missing_match
```

Dengan pola ini:

- Match dari `symptom_comment` selalu menang atas match dari `repair_comment` atau `symptom_code_description`.
- Match dari `repair_comment` selalu menang atas match dari `symptom_code_description`.
- Priority master tetap berlaku, tetapi hanya di dalam kolom fallback yang sedang dicoba.
- Risiko false positive tetap dikontrol karena `repair_comment` hanya dipakai jika `symptom_comment` belum menghasilkan match.

Contoh penting:

```text
part_name = PANEL
symptom_comment = vertical line
repair_comment = UNIT-PANEL-GANTI-BLANK
```

Jika `symptom_comment` match rule `LINE`, hasil tetap `LINE`, bukan `BLANK`, walaupun `repair_comment` mengandung `BLANK`.

---

## File yang Diubah

| File | Perubahan |
|------|-----------|
| `app/services/recipe_service.py` | Ubah special handling symptom rules supaya bisa membaca fallback columns dari `inputs`. |
| `app/services/transform_service.py` | Update jalur legacy `lookup_rules` symptom supaya behavior konsisten dengan recipe. |
| `configs/monthly-report-recipe.yaml` | Tambah `repair_comment` dan `symptom_code_description` ke `inputs` step `sub_13_add_symptom`. |
| `configs/monthly-report-recipe-lcd-import.yaml` | Tambah input fallback yang sama untuk job LCD import. |
| `docs/monthly-report-recipe.yaml` dan/atau `docs/done/monthly-report-recipe.yaml` | Opsional, sinkronisasi dokumentasi recipe jika masih dipakai sebagai referensi. |
| `tests/test_symptom_rules.py` | Tambah test fallback dari `repair_comment` dan `symptom_code_description`, plus test prioritas fallback. |
| `tests/test_pipeline_service.py` | Opsional, tambah coverage end-to-end pada recipe monthly report jika perlu. |

---

## Langkah Implementasi

### 1. Update YAML recipe runtime

Di step `sub_13_add_symptom`, ubah `inputs` dari:

```yaml
inputs:
  - "part_name"
  - "symptom_comment"
```

menjadi:

```yaml
inputs:
  - "part_name"
  - "symptom_comment"
  - "repair_comment"
  - "symptom_code_description"
```

File yang perlu diubah:

- `configs/monthly-report-recipe.yaml`
- `configs/monthly-report-recipe-lcd-import.yaml`

Catatan:

- Tidak perlu mengubah struktur sheet master `symptom`.
- Tidak perlu menambah kolom baru di master `symptom`.
- Matcher YAML existing boleh tetap seperti sekarang karena jalur special symptom rules memakai `priority`, `part_name`, `match_type`, `pattern`, dan `symptom` dari master.

---

### 2. Tambah helper untuk mengambil fallback columns di `recipe_service.py`

Tambahkan helper kecil, misalnya dekat fungsi `_apply_lookup_rules_step`:

```python
def _get_symptom_source_columns(step_cfg: dict) -> list[str]:
    inputs = [str(column) for column in step_cfg.get("inputs", [])]
    columns = [column for column in inputs if column != "part_name"]
    return columns or ["symptom_comment"]
```

Tujuannya:

- `inputs` menjadi sumber konfigurasi urutan fallback.
- Jika config lama hanya punya `symptom_comment`, behavior tetap sama.
- Jika karena alasan tertentu `inputs` tidak berisi kolom selain `part_name`, fallback default tetap `symptom_comment`.

---

### 3. Tambah helper matching fallback di `recipe_service.py`

Tambahkan helper agar logic utama tetap pendek:

```python
def _resolve_symptom_from_sources(
    source_row: pd.Series,
    symptom_rules: pd.DataFrame,
    source_columns: list[str],
    on_missing: object,
) -> object:
    source_part = _normalize_text(source_row["part_name"], case_sensitive=True)

    for source_column in source_columns:
        source_value = source_row[source_column]
        for _, master_row in symptom_rules.iterrows():
            rule_part = _normalize_text(master_row["part_name"], case_sensitive=True)
            if source_part != rule_part:
                continue
            if match_symptom_rule(source_value, master_row):
                return master_row["symptom"]

    return on_missing
```

Poin penting:

- Loop luar adalah `source_columns`, bukan `symptom_rules`.
- Ini menjaga fallback order tetap lebih kuat daripada priority lintas-kolom.
- Priority tetap berlaku karena `symptom_rules` sudah disortir oleh `prepare_symptom_rule_table`.

---

### 4. Ubah blok special symptom rules di `_apply_lookup_rules_step`

Blok saat ini hardcoded membutuhkan dan membaca `symptom_comment`.

Ubah validasi dari konsep:

```python
if "part_name" not in data_df.columns or "symptom_comment" not in data_df.columns:
    raise ValueError(...)
```

menjadi:

```python
source_columns = _get_symptom_source_columns(step_cfg)
required_columns = ["part_name", *source_columns]
missing_columns = [column for column in required_columns if column not in data_df.columns]
if missing_columns:
    raise ValueError(
        f"Step '{step_cfg['id']}' gagal, kolom source untuk symptom rules tidak ditemukan: "
        + ", ".join(missing_columns)
    )
```

Lalu ubah loop resolve dari:

```python
for _, source_row in data_df.iterrows():
    resolved = on_missing
    source_part = _normalize_text(source_row["part_name"], case_sensitive=True)
    for _, master_row in symptom_rules.iterrows():
        ...
        if match_symptom_rule(source_row["symptom_comment"], master_row):
            resolved = master_row["symptom"]
            break
    results.append(resolved)
```

menjadi:

```python
for _, source_row in data_df.iterrows():
    results.append(
        _resolve_symptom_from_sources(
            source_row=source_row,
            symptom_rules=symptom_rules,
            source_columns=source_columns,
            on_missing=on_missing,
        )
    )
```

---

### 5. Update jalur legacy di `transform_service.py`

Ada logic legacy `lookup_rules` untuk sheet `symptom` yang juga hardcoded ke `symptom_comment`.

Agar konsisten, tambahkan helper serupa atau helper lokal di `transform_service.py`:

```python
def _get_legacy_symptom_source_columns(merged_df: pd.DataFrame) -> list[str]:
    preferred_columns = ["symptom_comment", "repair_comment", "symptom_code_description"]
    return [column for column in preferred_columns if column in merged_df.columns]
```

Lalu update validasi:

```python
source_columns = _get_legacy_symptom_source_columns(merged_df)
if "part_name" not in merged_df.columns or not source_columns:
    raise ValueError(
        "Kolom source untuk symptom rules tidak ditemukan: part_name, symptom_comment"
    )
```

Dan gunakan fallback order yang sama:

```python
for _, source_row in merged_df.iterrows():
    resolved_value = on_missing_match
    source_part = _normalize_text_with_case(source_row["part_name"], case_sensitive=True)

    for source_column in source_columns:
        for _, rule_row in symptom_rules.iterrows():
            rule_part = _normalize_text_with_case(rule_row["part_name"], case_sensitive=True)
            if source_part != rule_part:
                continue
            if match_symptom_rule(source_row[source_column], rule_row):
                resolved_value = rule_row["symptom"]
                break
        if resolved_value != on_missing_match:
            break

    output_values.append("" if pd.isna(resolved_value) else resolved_value)
```

Catatan:

- Jika legacy config/source hanya punya `symptom_comment`, hasil tetap sama seperti sebelumnya.
- Kalau `repair_comment` dan `symptom_code_description` tersedia, otomatis dipakai sebagai fallback sesuai urutan tersebut.

---

## Test Plan

### 1. Test fallback dari `repair_comment`

Tambahkan test di `tests/test_symptom_rules.py` atau pipeline-level test:

```text
Source:
part_name = PANEL
symptom_comment = ""
symptom_code_description = ""
repair_comment = "UNIT-PANEL-GANTI-BLANK"

Master symptom:
priority = 10
part_name = PANEL
match_type = regex
pattern = blank
symptom = BLANK

Expected:
symptom = BLANK
```

Tujuan: memastikan case awal yang dibahas sudah ter-cover.

---

### 2. Test fallback dari `symptom_code_description`

```text
Source:
part_name = PANEL
symptom_comment = ""
repair_comment = ""
symptom_code_description = "no picture"

Master symptom:
pattern = no picture|blank
symptom = BLANK

Expected:
symptom = BLANK
```

Tujuan: memastikan kolom `symptom_code_description` tetap dipakai sebagai fallback terakhir.

---

### 3. Test `symptom_comment` tetap menang atas `repair_comment`

```text
Source:
part_name = PANEL
symptom_comment = "vertical line"
repair_comment = "UNIT-PANEL-GANTI-BLANK"
symptom_code_description = "no picture"

Master symptom:
priority 10: pattern = blank, symptom = BLANK
priority 20: pattern = line, symptom = LINE
priority 30: pattern = no picture, symptom = NO_PICTURE

Expected:
symptom = LINE
```

Tujuan: membuktikan `symptom_comment` tetap menjadi sumber paling prioritas walaupun kolom fallback lain juga match.

---

### 4. Test priority tetap berlaku di dalam kolom yang sama

```text
Source:
part_name = PANEL
symptom_comment = "vertical line"

Master symptom:
priority 10: pattern = vertical line, symptom = VERTICAL_LINE
priority 20: pattern = line, symptom = LINE

Expected:
symptom = VERTICAL_LINE
```

Tujuan: memastikan behavior priority existing tidak rusak.

---

### 5. Test backward compatibility

```text
Config inputs hanya:
- part_name
- symptom_comment

Source hanya punya:
- part_name
- symptom_comment

Expected:
matching tetap berjalan seperti behavior lama.
```

Tujuan: memastikan config lama tidak wajib langsung diubah.

---

## Acceptance Criteria

Implementasi dianggap selesai jika:

- Data `part_name=PANEL` dengan `repair_comment=UNIT-PANEL-GANTI-BLANK` menghasilkan `symptom=BLANK` saat `symptom_comment` tidak menghasilkan match.
- Data `part_name=PANEL` dengan `symptom_code_description` berisi `no picture` atau `blank` menghasilkan `symptom=BLANK` jika `symptom_comment` dan `repair_comment` tidak match.
- Jika `symptom_comment` sudah match rule tertentu, hasil dari `repair_comment` atau `symptom_code_description` tidak boleh menimpa hasil tersebut.
- Jika `repair_comment` sudah match rule tertentu, hasil dari `symptom_code_description` tidak boleh menimpa hasil tersebut.
- Priority master symptom tetap berjalan di dalam masing-masing kolom fallback.
- Config lama yang hanya memakai `symptom_comment` tetap valid.
- `python -m pytest tests/test_symptom_rules.py -q` berhasil.
- Jika memungkinkan, `python -m pytest -q` berhasil.

---

## Risiko dan Mitigasi

| Risiko | Mitigasi |
|--------|----------|
| `repair_comment` mengandung kata action/part yang bisa false positive. | Pakai `repair_comment` hanya setelah `symptom_comment` gagal match, dan tambah test agar tidak menimpa hasil dari `symptom_comment`. |
| Priority master mengalahkan fallback order jika loop salah. | Pastikan loop luar adalah source column, loop dalam adalah sorted rules. |
| Config lama rusak karena input tambahan belum ada. | Helper fallback default tetap `symptom_comment`. |
| Legacy config dan recipe config berbeda behavior. | Update `recipe_service.py` dan `transform_service.py` secara konsisten. |
| Test existing berubah karena fallback membaca kolom ekstra. | Tambahkan test eksplisit untuk fallback order dan backward compatibility. |

---

## Out of Scope untuk Implementasi Awal

- Mengubah struktur sheet master `symptom`.
- Menambahkan kolom khusus seperti `source_column` di master symptom.
- Membuat UI setting untuk mengatur fallback order.
- Mengubah rule master existing selain jika nanti ditemukan rule yang terlalu luas.
- Menggabungkan semua kolom source menjadi satu string karena itu lebih berisiko membuat false positive.

---

## Estimasi Perubahan

Perubahan ini termasuk **minor-to-medium**:

- Minor dari sisi arsitektur karena tidak mengubah pipeline besar, format output, atau master schema.
- Medium dari sisi kehati-hatian karena matching symptom mempengaruhi hasil bisnis dan perlu test fallback order yang jelas.

Estimasi file kode inti yang berubah: 2 file.
Estimasi config runtime yang berubah: 2 file.
Estimasi test baru: 3-5 test.
