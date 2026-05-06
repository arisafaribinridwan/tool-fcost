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
