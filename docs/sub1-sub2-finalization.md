# Finalisasi Sub-1 dan Sub-2

Dokumen ini mengunci aturan `sub-1` dan `sub-2` untuk flow awal automasi laporan bulanan sebelum diubah menjadi recipe config.

## Tujuan

Membentuk dataset kerja kanonik `result` dari satu workbook sumber bulanan dengan cara:

1. Mengambil data `GQS` untuk kategori `LCD SEID`
2. Mengambil data `SASS` untuk kategori `LCD SEID`
3. Menyatukan keduanya ke schema hasil yang sama

## Temuan Validasi Sample

Berdasarkan `example/source.xlsx`:

- Sheet sumber GQS: `GQS Mar26`
- Sheet sumber SASS: `SASS Mar26`
- Header GQS berada di row `2`
- Header SASS berada di row `5`
- Jumlah row `GQS` dengan `Category = LCD SEID`: `1884`
- Jumlah row `SASS` dengan `Category = LCD SEID`: `379`
- Total row hasil append: `2263`

Berdasarkan `example/result.xlsx`:

- Sheet target hasil gabungan: `result`
- Jumlah row data di `result`: `2263`
- Hasil sample konsisten dengan `1884 + 379`

## Schema Kanonik Hasil Setelah Sub-2

Urutan kolom hasil yang dikunci:

1. `notification`
2. `job_sheet_section`
3. `malfunction_start_date`
4. `basic_finish_date`
5. `model_name`
6. `category`
7. `serial_number`
8. `symptom_code`
9. `symptom_code_description`
10. `pmacttype`
11. `pmacttype_description`
12. `symptom_comment`
13. `repair_comment`
14. `description`
15. `warranty`
16. `planner_group`
17. `branch`
18. `purchased_date`
19. `labor_cost`
20. `transportation_cost`
21. `parts_cost`
22. `part_used`

Catatan:

- `sub-1` mengisi seluruh 22 kolom ini dari sumber `GQS`
- `sub-2` append ke schema yang sama dari sumber `SASS`
- Kolom yang tidak tersedia di `SASS` diisi kosong

## Finalisasi Sub-1

### Tujuan

Menyalin semua row `GQS` yang berkategori `LCD SEID` ke dataset kerja `result` dengan schema kanonik.

### Aturan

1. Baca workbook sumber utama yang dipilih user.
2. Cari sheet yang namanya mengandung `GQS`.
3. Gunakan header row `2`.
4. Filter row dengan `Category = LCD SEID`.
5. Salin row hasil filter ke dataset `result`.
6. Pertahankan urutan kolom sesuai schema kanonik.

### Mapping Kolom Sub-1

| GQS source | result |
|---|---|
| Notification | notification |
| Job Sheet Section | job_sheet_section |
| Malfunction Start Date | malfunction_start_date |
| Basic Finish Date | basic_finish_date |
| Model Name | model_name |
| Category | category |
| Serial Number | serial_number |
| Symptom Code | symptom_code |
| Symptom Code (Description) | symptom_code_description |
| PMActType | pmacttype |
| PMActType (Description) | pmacttype_description |
| Symptom Comment | symptom_comment |
| Repair Comment | repair_comment |
| Description | description |
| Warranty | warranty |
| Planner Group | planner_group |
| cabang | branch |
| Purchased Date | purchased_date |
| Labor Cost | labor_cost |
| Transportation Cost | transportation_cost |
| Parts Cost | parts_cost |
| Part used | part_used |

### Keputusan Teknis Sub-1

- Sorting `A to Z` pada `category` tidak memengaruhi hasil filter bila engine membaca langsung ke DataFrame.
- Untuk MVP, sorting tidak perlu dieksekusi jika tidak ada pengaruh ke hasil akhir.
- Nilai `branch` dari GQS diambil dari kolom sumber `cabang`.
- Tipe data dipertahankan apa adanya dari workbook sumber bila masih valid.

## Finalisasi Sub-2

### Tujuan

Mengambil semua row `SASS` yang berkategori `LCD SEID`, lalu append ke dataset `result` dengan schema yang sama seperti hasil `sub-1`.

### Aturan

1. Baca workbook sumber utama yang sama.
2. Cari sheet yang namanya mengandung `SASS`.
3. Gunakan header row `5`.
4. Filter row dengan `Category = LCD SEID`.
5. Lakukan rename dan mapping kolom ke schema kanonik.
6. Append hasilnya ke dataset `result` tanpa menghapus hasil `sub-1`.

### Mapping Kolom Sub-2

| SASS source | result |
|---|---|
| No Claim | notification |
| QTY Claim | job_sheet_section |
| Receive | malfunction_start_date |
| Finish | basic_finish_date |
| Model | model_name |
| Category | category |
| Serial No | serial_number |
| Damage | symptom_comment |
| Part Replacement | repair_comment |
| Branch | branch |
| Purchase | purchased_date |
| Service Fee | labor_cost |
| Transport Cost | transportation_cost |
| Part | parts_cost |
| Part Code | part_used |

### Kolom Result yang Diisi Kosong Oleh Sub-2

Kolom berikut tidak tersedia pada sumber `SASS` sample dan diisi kosong:

- `symptom_code`
- `symptom_code_description`
- `pmacttype`
- `pmacttype_description`
- `description`
- `warranty`
- `planner_group`

### Keputusan Teknis Sub-2

- Mapping `QTY Claim -> job_sheet_section` memang terlihat tidak intuitif, tetapi ini konsisten dengan sample `example/result.xlsx`.
- Sorting `A to Z` pada `category` tidak wajib untuk MVP jika hasil filter tetap sama.
- Append harus menjaga urutan kolom schema kanonik.

## Aturan Pencarian Sheet

Untuk saat ini, pencarian sheet dikunci seperti berikut:

- Pilih sheet pertama yang namanya mengandung `GQS` untuk `sub-1`
- Pilih sheet pertama yang namanya mengandung `SASS` untuk `sub-2`
- Pencocokan nama sheet bersifat case-insensitive

Jika lebih dari satu sheet cocok:

- engine memakai sheet cocok pertama
- log perlu mencatat sheet mana yang dipakai

## Validasi Minimal

Validasi yang harus ada sebelum `sub-1` dan `sub-2` dianggap sukses:

- Workbook sumber berhasil dibaca
- Sheet `GQS` ditemukan
- Sheet `SASS` ditemukan
- Header wajib pada masing-masing sheet tersedia
- Kolom `Category` tersedia
- Setelah filter, hasil boleh `0` row tetapi harus dicatat di log

## Error Yang Harus Dibuat Jelas

- Sheet `GQS` tidak ditemukan
- Sheet `SASS` tidak ditemukan
- Header row tidak sesuai
- Kolom wajib hilang
- File sumber rusak atau tidak bisa dibaca

## Draft Bentuk Recipe Config

Contoh bentuk config yang nanti bisa diturunkan:

```yaml
steps:
  - id: sub_1_copy_gqs
    type: extract_sheet
    sheet_selector:
      contains: "GQS"
      case_sensitive: false
      pick: first
    header_row: 2
    filters:
      - column: "Category"
        equals: "LCD SEID"
    select:
      Notification: notification
      Job Sheet Section: job_sheet_section
      Malfunction Start Date: malfunction_start_date
      Basic Finish Date: basic_finish_date
      Model Name: model_name
      Category: category
      Serial Number: serial_number
      Symptom Code: symptom_code
      Symptom Code (Description): symptom_code_description
      PMActType: pmacttype
      PMActType (Description): pmacttype_description
      Symptom Comment: symptom_comment
      Repair Comment: repair_comment
      Description: description
      Warranty: warranty
      Planner Group: planner_group
      cabang: branch
      Purchased Date: purchased_date
      Labor Cost: labor_cost
      Transportation Cost: transportation_cost
      Parts Cost: parts_cost
      Part used: part_used
    write_to: result
    mode: replace

  - id: sub_2_copy_sass
    type: extract_sheet
    sheet_selector:
      contains: "SASS"
      case_sensitive: false
      pick: first
    header_row: 5
    filters:
      - column: "Category"
        equals: "LCD SEID"
    select:
      No Claim: notification
      QTY Claim: job_sheet_section
      Receive: malfunction_start_date
      Finish: basic_finish_date
      Model: model_name
      Category: category
      Serial No: serial_number
      Damage: symptom_comment
      Part Replacement: repair_comment
      Branch: branch
      Purchase: purchased_date
      Service Fee: labor_cost
      Transport Cost: transportation_cost
      Part: parts_cost
      Part Code: part_used
    fill_missing:
      symptom_code: null
      symptom_code_description: null
      pmacttype: null
      pmacttype_description: null
      description: null
      warranty: null
      planner_group: null
    write_to: result
    mode: append
```

## Keputusan Yang Sudah Dikunci

- Output kerja awal memakai dataset logical `result`
- `sub-1` memakai `mode: replace`
- `sub-2` memakai `mode: append`
- Filter kategori yang dipakai saat ini adalah tepat sama dengan `LCD SEID`
- Sorting di source tidak dianggap rule bisnis wajib untuk MVP
- Nama kolom hasil memakai snake_case
