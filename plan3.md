# Rencana Implementasi Kolom `code`, `ref_code`, dan `defect_detail`

Dokumen ini adalah sumber kebenaran untuk implementasi penambahan kolom baru
pada recipe monthly report berikut:

- `configs/monthly-report-recipe.yaml`
- `configs/monthly-report-recipe-lcd-import.yaml`

Status dokumen:

- Ini adalah rencana implementasi, belum perubahan kode/runtime.
- Scope hanya untuk dua recipe di atas dan kemampuan engine minimum yang
  dibutuhkan oleh kolom baru.
- Jangan ubah aturan bisnis kolom existing seperti `action`,
  `defect_category`, `defect`, dan `keydate` selain penyesuaian urutan output
  yang diperlukan.

## Tujuan

Tambahkan tiga kolom baru pada output sheet `result`:

1. `code`
2. `ref_code`
3. `defect_detail`

Kolom baru harus tersedia di kedua job monthly report:

- Monthly report LCD SEID
- Monthly report LCD Import

## Keputusan Bisnis

### `code`

Sumber nilai:

- Ambil dari kolom `action` pada dataset `result`.
- Lookup ke workbook `masters/master_table.xlsx`.
- Sheet master: `defect_category`.
- Kolom key master: `Repair Action`.
- Kolom value master: `Code`.

Jika `action` kosong atau tidak ada match di master, isi dengan text:

```text
N/A
```

### `ref_code`

Sumber nilai:

- Ambil 4 karakter paling kanan dari kolom `keydate`.
- Gabungkan dengan nilai kolom `code`.
- Hasil akhir wajib diperlakukan sebagai text/string.

Contoh:

```text
keydate = 202603
code    = 20
ref_code = 260320
```

Aturan detail:

- `keydate` normalnya berformat `YYYYMM`, contoh `202603`.
- 4 karakter paling kanan dari `202603` adalah `2603`.
- `code` harus digabung sebagai text, bukan numeric.
- Jika `code` adalah angka dari Excel, contoh `20`, hasil tidak boleh menjadi
  `20.0`.
- Jika `code = N/A`, hasil yang diharapkan adalah `2603N/A`.
- Jika `keydate` kosong atau panjangnya kurang dari 4 karakter, `ref_code`
  sebaiknya menjadi `N/A` atau kosong sesuai keputusan teknis final. Rekomendasi
  implementasi: `N/A`, agar gagal data lebih terlihat.

### `defect_detail`

Sumber nilai:

- Ambil dari kolom `action` pada dataset `result`.
- Lookup ke workbook `masters/master_table.xlsx`.
- Sheet master: `defect_category`.
- Kolom key master: `Repair Action`.
- Kolom value master: `Defect Detail`.

Jika `action` kosong atau tidak ada match di master, isi dengan text:

```text
N/A
```

## Kondisi Master Saat Ini

Workbook aktual `masters/master_table.xlsx` sudah memiliki sheet
`defect_category` dengan kolom berikut:

- `Repair Action`
- `Category`
- `Defect`
- `Code`
- `Defect Detail`

Karena kolom master sudah tersedia, implementasi tidak perlu mengubah workbook
master untuk scope ini.

## Posisi Kolom Output

Rekomendasi urutan kolom pada `datasets.canonical_columns` dan
`outputs[].columns` sheet `result`:

```text
...
symptom
action
code
ref_code
defect_category
defect
defect_detail
keydate
```

Alasan:

- `code` dan `ref_code` diletakkan dekat `action` karena keduanya turunan dari
  action.
- `defect_category`, `defect`, dan `defect_detail` tetap berdekatan sebagai
  keluarga kolom defect.
- `keydate` tetap tersedia di output untuk audit periode.

Alternatif yang masih diterima bila user ingin `keydate` tetap sebelum
`ref_code`:

```text
...
symptom
action
defect_category
defect
keydate
code
ref_code
defect_detail
```

Namun rekomendasi utama adalah urutan pertama.

## Desain YAML Recipe

Tambahkan kolom baru ke:

- `datasets.canonical_columns`
- `outputs` untuk sheet `result`

Tambahkan step baru di kedua recipe. Urutan step yang direkomendasikan:

1. Setelah `sub_17_add_defect`, tambahkan `code`.
2. Tambahkan `defect_detail`.
3. Jalankan `keydate`.
4. Setelah `keydate`, tambahkan `ref_code`.

Dengan urutan ini, `ref_code` sudah punya bahan lengkap: `keydate` dan `code`.

### Step `code`

Gunakan step `lookup_exact`, mengikuti pola `sub_16_add_defect_category` dan
`sub_17_add_defect`.

Contoh konfigurasi:

```yaml
- id: "sub_18_add_code"
  type: "lookup_exact"
  source_column: "action"
  target_column: "code"
  master:
    file: "masters/master_table.xlsx"
    sheet: "defect_category"
    key: "Repair Action"
    value: "Code"
  matching:
    trim: true
    case_sensitive: false
    normalizer: "compact_text"
    aliases:
      "replace_remote_control": "Replace Remote"
  on_blank_source: "N/A"
  on_missing_match: "N/A"
```

### Step `defect_detail`

Contoh konfigurasi:

```yaml
- id: "sub_19_add_defect_detail"
  type: "lookup_exact"
  source_column: "action"
  target_column: "defect_detail"
  master:
    file: "masters/master_table.xlsx"
    sheet: "defect_category"
    key: "Repair Action"
    value: "Defect Detail"
  matching:
    trim: true
    case_sensitive: false
    normalizer: "compact_text"
    aliases:
      "replace_remote_control": "Replace Remote"
  on_blank_source: "N/A"
  on_missing_match: "N/A"
```

### Step `keydate`

Step existing tetap dipakai:

```yaml
- id: "sub_20_add_keydate"
  type: "derive_column"
  target: "keydate"
  expression:
    runtime_value: "period_keydate"
```

Catatan:

- Nomor sub-step boleh disesuaikan agar tidak bentrok dengan step existing.
- Jika ingin menjaga ID lama `sub_18_add_keydate`, boleh juga, tetapi step baru
  harus memakai ID unik.

### Step `ref_code`

Saat ini recipe engine belum memiliki operator expression untuk menggabungkan
text. Tambahkan operator baru yang generik, misalnya `concat`.

Target YAML:

```yaml
- id: "sub_21_add_ref_code"
  type: "derive_column"
  target: "ref_code"
  expression:
    concat:
      parts:
        - substring:
            column: "keydate"
            start: 2
            length: 4
        - column: "code"
      on_invalid_part: "N/A"
```

Catatan teknis:

- `start: 2` dan `length: 4` menghasilkan 4 karakter paling kanan untuk format
  `YYYYMM`.
- Untuk `202603`, hasil substring adalah `2603`.
- Operator `concat` harus menggabungkan part sebagai string.
- Operator `concat` harus merapikan nilai numeric integer-like, contoh `20.0`
  menjadi `20` jika berasal dari Excel/pandas.

## Perubahan Engine yang Dibutuhkan

File utama:

- `app/services/recipe_service.py`

Tambahkan support expression operator `concat` di `_evaluate_expression`.

Behavior minimum:

- Payload wajib object dengan field `parts`.
- `parts` wajib list dan minimal 1 item.
- Setiap item di `parts` dievaluasi memakai `_evaluate_expression`, sehingga
  bisa memakai operator existing seperti `substring` dan `column`.
- Hasil setiap part dikonversi ke text.
- `None`, `NaN`, dan blank diperlakukan sebagai invalid part.
- Jika ada invalid part:
  - gunakan `on_invalid_part` bila disediakan, atau
  - gunakan empty string sebagai default.
- Hasil akhir berupa `pd.Series` dtype object/string.

Rekomendasi helper kecil:

```text
_stringify_concat_value(value)
```

Tanggung jawab helper:

- `None`/NaN -> invalid.
- String -> strip seperlunya, pertahankan isi text.
- Numeric integer-like, contoh `20.0` -> `20`.
- Numeric non-integer, contoh `20.5` -> `20.5`.
- Jangan mengubah `N/A`.

## Validasi Config

File:

- `app/services/config_service.py`

Validator step recipe saat ini memastikan field wajib untuk `derive_column`,
tetapi belum perlu memvalidasi semua detail expression secara ketat. Ada dua
opsi:

1. Minimal: tidak menambah validasi expression baru.
2. Lebih baik: tambahkan validasi ringan untuk `concat.parts` agar config error
   tertangkap lebih awal.

Rekomendasi: pilih opsi 2 jika perubahan kecil dan tidak mengganggu schema
existing.

Validasi ringan yang disarankan:

- `concat` harus berupa object.
- `concat.parts` harus berupa list non-kosong.
- `concat.on_invalid_part`, jika ada, harus literal sederhana.

## File yang Perlu Diubah

Wajib:

1. `configs/monthly-report-recipe.yaml`
2. `configs/monthly-report-recipe-lcd-import.yaml`
3. `app/services/recipe_service.py`
4. `tests/test_pipeline_service.py`

Opsional, tetapi direkomendasikan:

5. `app/services/config_service.py`
6. `tests/test_config_service.py`
7. `docs/monthly-report-recipe.yaml` jika dokumentasi runtime recipe ingin ikut
   sinkron.

Jangan ubah:

- `masters/master_table.xlsx`, kecuali nanti ditemukan kolom master belum ada di
  environment lain.
- `configs/job_profiles.yaml`, karena job existing sudah menunjuk ke recipe yang
  sama.

## Rencana Test

### Test unit expression `concat`

Lokasi rekomendasi:

- `tests/test_pipeline_service.py`

Kasus wajib:

1. `keydate = 202603`, `code = 20` menghasilkan `ref_code = 260320`.
2. `code` yang terbaca sebagai `20.0` tetap menghasilkan `260320`, bukan
   `260320.0`.
3. `code = "N/A"` menghasilkan `2603N/A`.
4. `keydate` invalid atau kurang dari 4 karakter menghasilkan fallback sesuai
   `on_invalid_part`, rekomendasi `N/A`.

Jika lebih nyaman, test ini bisa dibuat sebagai test pipeline recipe kecil,
bukan memanggil private function langsung.

### Test E2E monthly recipe

Update test existing end-to-end monthly recipe di `tests/test_pipeline_service.py`
yang memakai `configs/monthly-report-recipe.yaml`.

Fixture master `defect_category` perlu ditambah kolom:

- `Code`
- `Defect Detail`

Assertion tambahan:

```text
code          = ["20", "N/A", "30", "21"] atau sesuai fixture
ref_code      = ["260320", "2603N/A", "260330", "260321"]
defect_detail = ["PANEL", "N/A", "SOFTWARE", "POWER"] atau sesuai fixture
```

Pastikan assertion memakai text/string agar tipe data tidak diam-diam berubah
menjadi numeric.

### Test LCD Import recipe

Tambahkan atau update test yang menjalankan:

- `configs/monthly-report-recipe-lcd-import.yaml`

Minimal assertion:

- Kolom `code` muncul di output.
- Kolom `ref_code` muncul di output.
- Kolom `defect_detail` muncul di output.
- Nilai lookup dan gabungan text benar untuk setidaknya satu row match dan satu
  row missing.

### Test config validation

Jika `config_service.py` diperluas untuk validasi `concat`, tambahkan test:

- Recipe dengan `derive_column.expression.concat.parts` valid diterima.
- Recipe dengan `concat.parts` kosong ditolak.
- Recipe dengan `concat.parts` bukan list ditolak.

## Acceptance Criteria

Implementasi dianggap selesai jika:

1. Kedua recipe monthly report menghasilkan sheet `result` dengan kolom:
   - `code`
   - `ref_code`
   - `defect_detail`
2. `code` lookup dari `action` ke master `defect_category.Code`.
3. `defect_detail` lookup dari `action` ke master
   `defect_category.Defect Detail`.
4. Missing lookup dan blank action menghasilkan `N/A` untuk `code` dan
   `defect_detail`.
5. `ref_code` adalah text hasil gabungan 4 karakter kanan `keydate` dan `code`.
6. Contoh `keydate = 202603` dan `code = 20` menghasilkan `260320`.
7. Tidak ada regresi pada kolom existing:
   - `action`
   - `defect_category`
   - `defect`
   - `keydate`
8. Test berikut lulus:

```bash
python -m ruff check .
python -m pytest -q
```

Jika environment lokal memakai `python3`, gunakan:

```bash
python3 -m ruff check .
python3 -m pytest -q
```

## Urutan Implementasi Rekomendasi

1. Tambahkan operator `concat` di `app/services/recipe_service.py`.
2. Tambahkan test kecil untuk `concat` dan format numeric `20.0 -> 20`.
3. Update `configs/monthly-report-recipe.yaml`.
4. Update `configs/monthly-report-recipe-lcd-import.yaml`.
5. Update test E2E monthly recipe dan LCD Import recipe.
6. Tambahkan validasi config untuk `concat` jika scope masih kecil.
7. Jalankan ruff dan pytest.
8. Lakukan smoke test manual dengan source workbook nyata jika tersedia.

## Risiko dan Mitigasi

### Risiko: `Code` terbaca numeric

Excel sering membuat `Code` terbaca sebagai angka. Jika langsung digabung,
hasil bisa menjadi `260320.0`.

Mitigasi:

- `concat` wajib punya konversi text yang mengubah numeric integer-like menjadi
  integer text.

### Risiko: `keydate` tidak selalu 6 digit

Jika `keydate` kosong atau formatnya berubah, substring bisa gagal atau hasil
tidak sesuai.

Mitigasi:

- Tetapkan fallback `on_invalid_part: "N/A"` pada step `ref_code`.
- Test kasus invalid keydate.

### Risiko: urutan step salah

Jika `ref_code` dijalankan sebelum `code` atau `keydate`, pipeline akan gagal
karena kolom belum ada.

Mitigasi:

- Letakkan `ref_code` setelah step `code` dan `keydate`.
- Test E2E harus menjalankan recipe aktual, bukan recipe mini saja.

### Risiko: dua recipe tidak sinkron

LCD SEID dan LCD Import punya struktur hampir sama, sehingga mudah salah update
salah satu saja.

Mitigasi:

- Update dua file dalam patch yang sama.
- Test dua config secara eksplisit.

## Checklist Implementasi

- [ ] `concat` expression tersedia di recipe engine.
- [ ] `concat` menggabungkan value sebagai text.
- [ ] `concat` menangani numeric integer-like tanpa `.0`.
- [ ] `monthly-report-recipe.yaml` memiliki `code`, `ref_code`,
      `defect_detail`.
- [ ] `monthly-report-recipe-lcd-import.yaml` memiliki `code`, `ref_code`,
      `defect_detail`.
- [ ] Output sheet `result` kedua recipe menyertakan tiga kolom baru.
- [ ] Test E2E monthly recipe diperbarui.
- [ ] Test LCD Import recipe ditambahkan atau diperbarui.
- [ ] Ruff lulus.
- [ ] Pytest lulus.
