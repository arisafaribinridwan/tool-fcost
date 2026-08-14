# Implementasi Update Job Summary Result: data4 dan data5c

Dokumen ini adalah sumber kebenaran untuk implementasi update fitur pada
`configs/job_summary_result.yaml`.

Status keputusan:

- Jangan ubah format sheet `result`, `sales`, atau summary lain di luar scope ini.
- `data4` harus tetap menampilkan summary overall by panel usage, lalu menambahkan panel summary by usage per factory di bawahnya.
- `data5c` harus mengikuti contoh `docs/example-create-sheet-data5c.xlsx`, yaitu summary PANEL per factory by inch, bukan copy persis `data5b`.
- Urutan inch pada `data5c` wajib berdasarkan nilai `Sum of total_cost` terbesar di masing-masing factory.
- Cost pada `data5c` tetap memakai scale factor `/1000`, sama seperti `data5a` dan `data5b`.

## Referensi Contoh

File contoh:

- `docs/example-update-sheet-data4.xlsx`
- `docs/example-create-sheet-data5c.xlsx`

Ekspektasi `data4` dari contoh:

- Sheet name: `data4`
- Baris 1 title: `PANEL USAGE SUMMARY`
- Baris 2 subtitle: `Panel summary by usage`
- Tabel pertama adalah overall usage:
  - Header: `Part Name`, `Panel Usage`, `Total`
  - Usage order fixed:
    - `< 1 Year`
    - `1 - 2 Years`
    - `2 - 3 Years`
    - `> 3 Years`
  - Diakhiri `PANEL Total`
  - Diakhiri `Grand Total`
- Setelah satu baris kosong, tampilkan subtable per factory.
- Setiap subtable factory:
  - Baris label factory, contoh: `AE TECH`
  - Header: `Part Name`, `Panel Usage`, `Total`
  - Usage order fixed seperti overall.
  - Diakhiri `PANEL Total`
  - Tidak perlu `Grand Total` per factory.
- Usage bucket tetap muncul walaupun count `0`.

Ekspektasi `data5c` dari contoh:

- Sheet name: `data5c`
- Baris 1 title: `PANEL TOP MODEL BY FACTORY`
- Baris 2 subtitle: `Top panel model summary by factory - (K.IDR)`
- Layout berisi subtable per factory.
- Setiap subtable factory:
  - Baris label factory, contoh: `AE TECH`
  - Header: `Part Name`, `Inch`, `Labor`, `Transportation`, `Parts`, `Total`, `Count`
  - Data hanya part `PANEL`
  - Group by `factory` dan `inch`
  - Sort inch descending by sum `total_cost` dalam factory tersebut
  - Diakhiri `PANEL Total`
- Tidak ada kolom `Model Name` pada `data5c`, walaupun title contoh memakai kata "MODEL".

## File yang Perlu Disentuh

Perubahan utama:

- `app/services/recipe_service.py`
- `configs/job_summary_result.yaml`
- `tests/test_pipeline_service.py`

Kemungkinan perubahan tambahan bila dibutuhkan:

- `app/services/output_service.py`

Catatan: saat diskusi terakhir ada file sementara Excel lock
`docs/.~lock.example-create-sheet-data5c.xlsx#`. Jangan sentuh file ini.

## Desain Implementasi

### 1. Tambah summary type untuk `data4`

Tambahkan summary type baru, misalnya:

```yaml
type: "panel_usage_by_factory_summary"
```

Alternatif nama yang juga boleh:

```yaml
type: "panel_usage_summary_with_factory_panels"
```

Rekomendasi: pakai `panel_usage_by_factory_summary` karena pendek dan jelas.

Behavior builder:

- Input dataset default: `result`
- Required columns:
  - `part_name`
  - `panel_usage`
  - `factory`
- Filter:
  - `part_name == "PANEL"` setelah trim string
  - `panel_usage` hanya bucket valid fixed order
- Output columns final setelah label:
  - `Part Name`
  - `Panel Usage`
  - `Total`
- Overall table:
  - Hitung count semua factory combined.
  - Buat 4 row usage fixed order.
  - Tambah `PANEL Total`.
  - Tambah `Grand Total`.
- Factory subtables:
  - Group berdasarkan `factory`.
  - Skip factory blank/null.
  - Urutan factory harus deterministic. Gunakan urutan kemunculan pertama dari data setelah filter, kecuali ada option `factory_order`.
  - Untuk setiap factory, buat baris label section, header, 4 usage rows, dan `PANEL Total`.

Karena output saat ini berupa DataFrame tunggal, ada dua opsi implementasi:

1. Representasikan row label/header/blank sebagai row DataFrame biasa.
2. Tambahkan mekanisme metadata layout baru untuk multi-table summary.

Rekomendasi praktis: pakai opsi 1 dulu agar scope kecil. Styling bisa memanfaatkan `_row_type` untuk membedakan:

- `data`
- `subtotal`
- `grand_total`
- `section_title`
- `header`
- `blank`

Jika `output_service.py` belum menangani row type `section_title`, `header`, dan `blank`, tambahkan handling minimal di `_apply_summary_sheet_style`.

### 2. Tambah summary type untuk `data5c`

Tambahkan summary type baru, misalnya:

```yaml
type: "panel_fcost_inch_by_factory_summary"
```

Behavior builder:

- Input dataset default: `result`
- Required columns:
  - `part_name`
  - `factory`
  - `inch`
  - `labor_cost`
  - `transportation_cost`
  - `parts_cost`
  - `total_cost`
- Filter:
  - `part_name == "PANEL"` setelah trim string
  - `factory` tidak blank
  - `inch` tidak blank
- Group:
  - per `factory`, `inch`
- Aggregation:
  - `Sum of labor_cost`: sum numeric `labor_cost`
  - `Sum of transportation_cost`: sum numeric `transportation_cost`
  - `Sum of parts_cost`: sum numeric `parts_cost`
  - `Sum of total_cost`: sum numeric `total_cost`
  - `Count of part_name`: count rows
- Sort:
  - within each factory, sort by `Sum of total_cost` descending
  - tie-breaker by normalized inch ascending/stable
- Output:
  - label factory row
  - header row
  - rows for inch groups
  - `PANEL Total` row per factory
- Amount scale:
  - apply `amount_scale_factor: 1000` to cost columns only
  - do not scale `Count`
- Column labels:
  - `part_name` -> `Part Name`
  - `inch` -> `Inch`
  - `Sum of labor_cost` -> `Labor`
  - `Sum of transportation_cost` -> `Transportation`
  - `Sum of parts_cost` -> `Parts`
  - `Sum of total_cost` -> `Total`
  - `Count of part_name` -> `Count`

Tidak perlu include `model_name`.

### 3. Update dispatcher summary

Di `app/services/recipe_service.py`, update `_build_summary_output_sheet` agar mengenali:

- `panel_usage_by_factory_summary`
- `panel_fcost_inch_by_factory_summary`

Pastikan unknown summary type behavior lama tetap sama.

### 4. Update YAML runtime

Update `configs/job_summary_result.yaml`.

Untuk `data4`, ganti type:

```yaml
type: "panel_usage_by_factory_summary"
```

Options minimal:

```yaml
options:
  factory_column: "factory"
  column_labels:
    part_name: "Part Name"
    panel_usage: "Panel Usage"
    Total: "Total"
```

Tambahkan output baru setelah `data5b` dan sebelum `data6`:

```yaml
- sheet_name: "data5c"
  summary:
    type: "panel_fcost_inch_by_factory_summary"
    layout_mode: "plain"
    title: "PANEL TOP MODEL BY FACTORY"
    subtitle: "Top panel model summary by factory - (K.IDR)"
    column_width: 13.0
    options:
      amount_scale_factor: 1000
      factory_column: "factory"
      column_labels:
        part_name: "Part Name"
        inch: "Inch"
        "Sum of labor_cost": "Labor"
        "Sum of transportation_cost": "Transportation"
        "Sum of parts_cost": "Parts"
        "Sum of total_cost": "Total"
        "Count of part_name": "Count"
```

## Styling dan Layout

Saat ini summary plain layout menulis title/subtitle di row 1 dan 2, lalu data mulai row 4. Untuk multi-table sheet, DataFrame akan mengandung baris header tambahan di tengah sheet.

Minimal styling yang diharapkan:

- Title row tetap merge sepanjang jumlah kolom.
- Subtitle row tetap merge sepanjang jumlah kolom.
- Header utama row 4 tetap styled.
- Header subtable juga harus styled seperti header.
- Factory label row harus bold dan terlihat sebagai section title.
- `PANEL Total` row subtotal.
- `Grand Total` row grand total.
- Blank row tetap blank tanpa border mencolok.

Jika memakai `_row_type`, pastikan kolom `_row_type` tidak ikut ditulis ke Excel. Pola ini sudah ada di output pipeline: row type dipakai sebagai metadata styling.

## Test Plan

Tambahkan test unit/integration di `tests/test_pipeline_service.py`.

### Test `data4`

Buat source minimal dengan columns:

- `part_name`
- `panel_usage`
- `factory`

Sample data harus mencakup:

- Beberapa row `PANEL` untuk factory `AE TECH`, `SMM`, `MOKA`.
- Usage bucket lengkap dan beberapa missing bucket agar output `0` bisa diverifikasi.
- Row non-PANEL yang harus diabaikan.
- Usage invalid/blank yang harus diabaikan.
- Factory blank yang boleh masuk overall tetapi tidak perlu muncul sebagai subtable factory.

Assert:

- Sheet `data4` ada.
- Overall usage rows fixed order.
- Overall count benar.
- `PANEL Total` dan `Grand Total` overall benar.
- Subtable factory muncul setelah overall.
- Tiap factory punya fixed usage order.
- Missing bucket menghasilkan `0`.
- Factory subtotal benar.

Karena pembacaan dengan `pd.read_excel(skiprows=3)` akan membaca header pertama saja, untuk multi-header di tengah sheet mungkin lebih mudah pakai `openpyxl` untuk assert posisi cell langsung.

### Test `data5c`

Buat source minimal dengan columns:

- `part_name`
- `factory`
- `inch`
- `labor_cost`
- `transportation_cost`
- `parts_cost`
- `total_cost`

Sample data:

- Factory `AE TECH`: inch `55` total lebih besar daripada `75`.
- Factory `SMM`: inch `65` total lebih besar daripada `45`, `50`, `60`.
- Factory `MOKA`: satu inch saja.
- Row `MAIN_UNIT` harus diabaikan.
- Row blank factory/inch harus diabaikan dari subtable.

Assert:

- Sheet `data5c` ada.
- Title/subtitle sesuai contoh.
- Header columns: `Part Name`, `Inch`, `Labor`, `Transportation`, `Parts`, `Total`, `Count`.
- Dalam setiap factory, inch diurutkan berdasarkan `Total` terbesar.
- Cost sudah dibagi 1000.
- `Count` tidak dibagi 1000.
- `PANEL Total` per factory benar.
- Tidak ada kolom `Model Name`.

### Regression

Jalankan minimal:

```bash
python3 -m pytest tests/test_pipeline_service.py -q
python3 -m ruff check .
```

Jika waktu cukup, jalankan:

```bash
python3 -m pytest -q
```

## Acceptance Criteria

Implementasi dianggap selesai jika:

- `configs/job_summary_result.yaml` menghasilkan sheet `data4` sesuai contoh update.
- `configs/job_summary_result.yaml` menghasilkan sheet baru `data5c` sesuai contoh.
- `data5c` mengurutkan inch per factory berdasarkan total cost terbesar.
- `data5c` tidak memiliki kolom `Model Name`.
- Summary existing `data5a` dan `data5b` tidak berubah behavior.
- Test baru lulus.
- Ruff lulus.

## Risiko dan Catatan

- Nama title `PANEL TOP MODEL BY FACTORY` tidak sepenuhnya cocok dengan isi contoh karena tidak ada kolom model. Ikuti contoh Excel dan keputusan diskusi: `data5c` tanpa `Model Name`.
- Jika factory order pada data real perlu urutan khusus, tambahkan option YAML `factory_order`. Untuk implementasi pertama, urutan kemunculan pertama dari data sudah cukup deterministic dan sesuai contoh bila source urutannya sama.
- Multi-table dalam satu sheet adalah pola baru untuk summary builder. Jaga supaya styling tambahan tidak merusak summary lama yang masih satu tabel.
