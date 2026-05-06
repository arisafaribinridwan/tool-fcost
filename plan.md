# Plan: MVP Features — Job AUTOFILL RAW

## Ringkasan Alur Job Saat Ini

File config: `configs/monthly-report-recipe-autofill-raw.yaml`

```
Source .xlsx
  → extract_sheet (cari sheet nama mengandung "result", detect header baris 1–25)
  → select 38 kolom canonical → simpan ke dataset "result"
  → filter: job_sheet_section == 1
  → target_update: scan folder tujuan, cocokkan file .xlsx per model_series
      → append baris baru ke sheet "raw" (dedup by notification + model_series + part_used)
  → write output preview: sheet "autofill_preview" (hanya 2 kolom)
```

---

## Rekomendasi 1 — Perluas Kolom Output Preview

### Masalah

Sheet `autofill_preview` saat ini hanya memiliki 2 kolom:

```yaml
# configs/monthly-report-recipe-autofill-raw.yaml (baris 117–121)
outputs:
  - sheet_name: "autofill_preview"
    columns:
      - "model_series"
      - "job_sheet_section"
```

User tidak bisa memverifikasi data apa yang sudah di-append tanpa membuka file target satu per satu.

### Solusi

Tambahkan kolom-kolom kunci ke daftar `columns` di YAML. Tidak ada perubahan Python sama sekali.

```yaml
# GANTI bagian outputs di monthly-report-recipe-autofill-raw.yaml
outputs:
  - sheet_name: "autofill_preview"
    columns:
      - "notification"
      - "model_series"
      - "job_sheet_section"
      - "serial_number"
      - "part_used"
      - "part_name"
      - "total_cost"
      - "keydate"
      - "branch"
      - "warranty"
```

> Pilih kolom sesuai kebutuhan validasi. Semua kolom di atas sudah ada di `canonical_columns` (baris 23–60 config).

### File yang Diubah

| File | Perubahan |
|------|-----------|
| `configs/monthly-report-recipe-autofill-raw.yaml` | Tambah kolom di `outputs[0].columns` |

**Tidak ada perubahan Python.**

---

## Rekomendasi 2 — Sheet Ringkasan Hasil Update Target

### Masalah

Setelah job selesai, hasil per file target (updated / skipped / failed) hanya muncul di log teks di UI. Tidak ada file permanen yang bisa diaudit atau dibagikan. Kalau ada 50 file target, sulit tahu mana yang gagal.

### Data yang Sudah Tersedia

Di `app/services/pipeline_service.py` baris **257–279**, variabel `update_results` sudah berisi list `TargetFileUpdateResult` dengan field:

```python
# app/services/pipeline_types.py (via target_workbook_update_service.py)
@dataclass(frozen=True)
class TargetFileUpdateResult:
    file_name: str
    model_series_key: str
    status: str          # "updated" | "skipped" | "failed"
    rows_written: int
    reason: str = ""
```

### Solusi

**Konversi `update_results` ke DataFrame dan inject ke `output_sheets` sebelum `write_output_workbook` dipanggil.**

#### Langkah 1 — Tambah helper di `pipeline_service.py`

Tambahkan fungsi ini di dekat bagian atas file (setelah `import pandas as pd`):

```python
def _build_update_summary_df(update_results: list) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "file_name": r.file_name,
                "model_series": r.model_series_key,
                "status": r.status,
                "rows_written": r.rows_written,
                "reason": r.reason,
            }
            for r in update_results
        ]
    )
```

#### Langkah 2 — Inject ke `output_sheets` di `run_pipeline`

Cari blok di `pipeline_service.py` sekitar baris **279** (setelah `emit_progress("update_targets", ...)`). Tambahkan kode berikut tepat setelah blok `emit_progress`:

```python
# Setelah emit_progress("update_targets", ...) selesai
output_sheets["update_summary"] = _build_update_summary_df(update_results)
```

> `output_sheets` adalah `dict[str, pd.DataFrame]` yang sudah ada sebelum `write_output_workbook` dipanggil di baris 292. Sheet baru ini akan ikut ditulis otomatis ke file output Excel.

#### Hasil di Excel

Sheet `update_summary` akan berisi:

| file_name | model_series | status | rows_written | reason |
|-----------|-------------|--------|-------------|--------|
| ABC.xlsx | abc | updated | 12 | |
| DEF.xlsx | def | skipped | 0 | Semua data sudah ada |
| GHI.xlsx | ghi | failed | 0 | Sheet 'raw' tidak ditemukan |

Styling akan mengikuti `_apply_worksheet_style` (standard layout) karena sheet name tidak diawali `"data"` dan tidak masuk `plain` mode.

### File yang Diubah

| File | Perubahan |
|------|-----------|
| `app/services/pipeline_service.py` | Tambah fungsi `_build_update_summary_df`, inject ke `output_sheets` |

**Tidak ada perubahan YAML, tidak ada perubahan `output_service.py`.**

### Catatan Penting

- Blok `output_sheets["update_summary"] = ...` harus berada di dalam `if target_update_cfg is not None:` (baris 218), bukan di luar. Supaya sheet ini hanya muncul kalau job memang menjalankan target update.
- Kalau `update_results` kosong (tidak ada file .xlsx di folder tujuan), DataFrame akan kosong tapi sheet tetap dibuat — ini acceptable karena menandakan folder target memang kosong.

---

## Prioritas Eksekusi

| Urutan | Fitur | File Diubah | Estimasi Waktu |
|--------|-------|-------------|----------------|
| 1 | Perluas kolom `autofill_preview` | 1 file YAML | < 5 menit |
| 2 | Sheet `update_summary` | 1 file Python | ~30 menit |
