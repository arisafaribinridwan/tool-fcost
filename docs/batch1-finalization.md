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
- Pada sample, header GQS terdeteksi di row `2`
- Pada sample, header SASS terdeteksi di row `5`
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
3. Deteksi header secara otomatis pada `scan` row awal sheet.
4. Untuk `GQS`, header dianggap valid bila semua kolom wajib `Notification`, `Category`, `Serial Number`, dan `Labor Cost` ditemukan dalam satu row yang sama.
5. Gunakan row valid pertama sebagai header aktif.
6. Filter row dengan `Category = LCD SEID`.
7. Salin row hasil filter ke dataset `result`.
8. Pertahankan urutan kolom sesuai schema kanonik.

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
- Posisi header boleh berubah selama signature header `GQS` masih bisa dikenali.

## Finalisasi Sub-2

### Tujuan

Mengambil semua row `SASS` yang berkategori `LCD SEID`, lalu append ke dataset `result` dengan schema yang sama seperti hasil `sub-1`.

### Aturan

1. Baca workbook sumber utama yang sama.
2. Cari sheet yang namanya mengandung `SASS`.
3. Deteksi header secara otomatis pada `scan` row awal sheet.
4. Untuk `SASS`, header dianggap valid bila semua kolom wajib `No Claim`, `Category`, `Serial No`, dan `Service Fee` ditemukan dalam satu row yang sama.
5. Gunakan row valid pertama sebagai header aktif.
6. Filter row dengan `Category = LCD SEID`.
7. Lakukan rename dan mapping kolom ke schema kanonik.
8. Append hasilnya ke dataset `result` tanpa menghapus hasil `sub-1`.

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
- Posisi header boleh berubah selama signature header `SASS` masih bisa dikenali.

## Aturan Deteksi Header

Aturan ini menggantikan pendekatan fixed `header_row` agar lebih tahan terhadap perubahan format ringan pada workbook sumber.

### Prinsip Umum

- Engine memindai row `1` sampai `15` pada sheet terpilih untuk mencari header.
- Header dipilih dari row pertama yang memenuhi seluruh kolom wajib untuk step terkait.
- Pencocokan nama header bersifat case-insensitive.
- Saat membandingkan nama header, engine perlu melakukan normalisasi ringan:
  - trim spasi di awal dan akhir
  - kompres spasi ganda menjadi satu spasi
  - abaikan perbedaan huruf besar kecil
- Nilai sel kosong penuh pada row kandidat tidak dianggap header.

### Signature Header GQS

Row dianggap sebagai header `GQS` jika seluruh kolom berikut ditemukan:

- `Notification`
- `Category`
- `Serial Number`
- `Labor Cost`

Kolom lain pada mapping `GQS` tetap harus divalidasi setelah header terpilih.

### Signature Header SASS

Row dianggap sebagai header `SASS` jika seluruh kolom berikut ditemukan:

- `No Claim`
- `Category`
- `Serial No`
- `Service Fee`

Kolom lain pada mapping `SASS` tetap harus divalidasi setelah header terpilih.

### Fallback dan Batasan

- Jika lebih dari satu row cocok, engine memakai row cocok pertama dan menulis nomor row ke log.
- Jika tidak ada row yang cocok dalam jendela scan, step gagal dengan error jelas.
- Perubahan posisi header masih didukung selama header tetap berada dalam row `1..15`.
- Jika nama kolom inti berubah total, kasus itu dianggap perubahan format mayor dan config harus diperbarui.

## Desain Sistem Header Locator

Bagian ini memfinalkan bentuk desain sistem untuk MVP agar implementasi nanti tidak kembali ke pendekatan hardcoded `header_row`.

### Komponen Utama

- `config_loader`: memuat recipe YAML dan memvalidasi field `sheet_selector`, `header_locator`, `filters`, dan `select`
- `source_reader`: membuka workbook sumber dan mengambil sheet kandidat sesuai `sheet_selector`
- `header_detector`: memindai row kandidat dan memilih row header berdasarkan aturan `header_locator`
- `sheet_extractor`: membaca tabel mulai dari row header yang sudah ditemukan
- `schema_mapper`: melakukan rename kolom, pengisian kolom kosong, dan penyusunan urutan schema kanonik
- `pipeline_logger`: mencatat keputusan penting selama proses berjalan

### Kontrak Header Locator

Untuk MVP, bentuk `header_locator` dikunci seperti berikut:

```yaml
header_locator:
  type: required_columns
  scan_rows: [1, 15]
  case_sensitive: false
  normalize: true
  required:
    - "Notification"
    - "Category"
    - "Serial Number"
    - "Labor Cost"
```

Arti field:

- `type`: untuk MVP hanya mendukung `required_columns`
- `scan_rows`: jendela scan awal untuk mencari header, bukan nomor row pasti
- `case_sensitive`: untuk MVP dikunci `false`
- `normalize`: untuk MVP dikunci `true`
- `required`: daftar kolom signature minimum yang harus muncul bersama pada satu row

### Alur Eksekusi Header Detection

Urutan kerja engine dikunci seperti berikut:

1. Pilih sheet target dengan `sheet_selector`.
2. Ambil row dalam rentang `scan_rows`.
3. Normalisasi seluruh nilai sel pada tiap row kandidat.
4. Cek apakah seluruh kolom `required` ada pada row yang sama.
5. Pilih row pertama yang match penuh sebagai header aktif.
6. Validasi bahwa seluruh kolom mapping untuk step tersebut tersedia setelah header aktif dipakai.
7. Jika validasi lolos, lanjutkan pembacaan data mulai dari row setelah header.

### Aturan Normalisasi Header

Saat `normalize: true`, engine harus melakukan normalisasi ringan berikut:

- trim spasi di awal dan akhir
- kompres spasi ganda menjadi satu spasi
- abaikan perbedaan huruf besar kecil
- perlakukan sel kosong sebagai tidak bernilai untuk matching header

Untuk MVP, engine belum perlu mendukung:

- fuzzy match nama kolom
- alias header otomatis
- koreksi typo
- pencarian header di luar `scan_rows`

### Validasi Setelah Header Ditemukan

Setelah row header aktif dipilih, engine wajib memvalidasi:

- semua kolom pada `select` tersedia di sheet sumber untuk step terkait
- kolom yang dipakai pada `filters` tersedia
- struktur tabel di bawah header masih bisa dibaca sebagai data tabular

Jika signature header ditemukan tetapi sebagian kolom mapping hilang, kasus itu tetap dianggap gagal validasi.

### Model Error Yang Disiapkan

Jenis error yang perlu dibedakan sejak desain:

- `WorkbookReadError`: file sumber rusak atau tidak bisa dibaca
- `SheetNotFoundError`: sheet target tidak ditemukan
- `HeaderNotFoundError`: tidak ada row dalam `scan_rows` yang memenuhi signature header
- `RequiredColumnsMissingError`: header ditemukan tetapi kolom mapping wajib tidak lengkap

Prinsip pesan error:

- singkat
- menyebut step yang gagal
- menyebut sheet yang dipakai jika sudah ditemukan
- menyebut row scan bila masalah ada pada header detection

Contoh pesan yang diharapkan:

- `Header GQS tidak ditemukan pada row 1..15`
- `Kolom wajib GQS tidak lengkap setelah header ditemukan: PMActType, Warranty`

### Logging Minimum

Minimal log internal yang perlu dicatat untuk setiap step:

- `step_id`
- `sheet_name`
- `scan_rows`
- `header_row_detected`
- `required_columns_used`
- `missing_columns`
- `filtered_row_count`
- `status`

Tujuan log ini adalah agar perubahan format source bisa dianalisis tanpa harus menebak-nebak posisi header secara manual.

### Keputusan Desain MVP Yang Dikunci

- MVP hanya mendukung `header_locator.type = required_columns`
- Matching header bersifat case-insensitive dengan normalisasi whitespace
- Scan window default untuk use case ini adalah row `1..15`
- Bila ada lebih dari satu row yang match, engine memakai row pertama
- Perubahan posisi header didukung
- Perubahan nama kolom inti belum didukung otomatis
- Alias, fuzzy match, dan heuristik lanjutan sengaja ditunda

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
- Header untuk `GQS` berhasil terdeteksi dalam row scan yang diizinkan
- Header untuk `SASS` berhasil terdeteksi dalam row scan yang diizinkan
- Seluruh kolom mapping wajib pada masing-masing sheet tersedia setelah header terpilih
- Kolom `Category` tersedia
- Setelah filter, hasil boleh `0` row tetapi harus dicatat di log

## Error Yang Harus Dibuat Jelas

- Sheet `GQS` tidak ditemukan
- Sheet `SASS` tidak ditemukan
- Header `GQS` tidak ditemukan dalam row scan `1..15`
- Header `SASS` tidak ditemukan dalam row scan `1..15`
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
    header_locator:
      type: required_columns
      scan_rows: [1, 15]
      case_sensitive: false
      normalize: true
      required:
        - "Notification"
        - "Category"
        - "Serial Number"
        - "Labor Cost"
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
    header_locator:
      type: required_columns
      scan_rows: [1, 15]
      case_sensitive: false
      normalize: true
      required:
        - "No Claim"
        - "Category"
        - "Serial No"
        - "Service Fee"
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
- Deteksi header memakai `header_locator`, bukan fixed `header_row`
