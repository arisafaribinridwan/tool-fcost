# Rencana Implementasi Job Summary Result

## Ringkasan tugas

Tujuan job baru adalah membaca satu workbook source yang berisi satu sheet berformat sama dengan sheet `result` pada `outputs/result_learning_source.xlsx`, lalu men-generate sheet `result` dan summary `data1`, `data2`, `data3a`, `data3b`, `data3c`, `data4`, `data5a`, `data5b`, dan `data6`.

Batasan kerja yang wajib dipertahankan:

1. `outputs/result_learning_source.xlsx` sheet `result` menjadi sumber referensi untuk studi aturan output; source runtime adalah workbook input satu sheet dengan format tabel yang sama.
2. Tidak melakukan perubahan kode sebelum ada konfirmasi final untuk setiap tahap summary.
3. Implementasi final harus dibuat bertahap dan tervalidasi per sheet final.
4. File ini adalah rencana implementasi; belum ada perubahan kode/config engine yang dilakukan.
5. Jangan ubah perilaku engine yang sudah berjalan; implementasi hanya boleh menambahkan kemampuan baru secara additive agar job/config existing tetap aman.

Keputusan terkonfirmasi:

- Target output adalah angka dan struktur tabel yang sama; tidak perlu pixel-perfect mengikuti workbook referensi.
- Job baru membaca satu workbook source yang berisi satu sheet, lalu menghasilkan gabungan sheet `result` dan summary dari dataset tersebut dalam satu pipeline.
- Sheet final yang dihasilkan: `result`, `data1`, `data2`, `data3a`, `data3b`, `data3c`, `data4`, `data5a`, `data5b`, dan `data6`.
- Source runtime tidak bergantung pada nama sheet karena workbook input hanya berisi satu sheet.
- Header tabel source harus dibaca fleksibel dengan mencari baris yang berisi kolom wajib, bukan dikunci pada nomor baris tertentu.
- Jumlah baris data pada source runtime bersifat dinamis; engine harus memproses seluruh baris data setelah header sampai akhir data valid, bukan mengandalkan jumlah baris referensi.
- Perilaku engine existing tidak boleh diubah; kemampuan header locator, dynamic row reader, dan summary output harus ditambahkan sebagai jalur/fitur baru yang tidak mengganggu job existing.
- Untuk `data1`, `OTHER` adalah semua `part_name` non-kosong selain `PANEL`, `MAIN_UNIT`, dan `POWER_UNIT`.
- Untuk `data1` dan `data2`, section baru selain `GQS`/`SASS` ditampilkan dinamis dengan subtotal masing-masing.
- Untuk `data2`, sorting `part_name` dalam tiap section memakai `Sum of total_cost` descending.
- Untuk `data3`, tiga blok summary dipisah menjadi sheet `data3a`, `data3b`, dan `data3c`.
- Untuk `data4`, `panel_usage` kosong atau kategori baru diabaikan.
- `data5c` tidak dibuat karena isinya sama dengan `data4`.
- Untuk `data5`, summary dipisah menjadi sheet `data5a` dan `data5b`.
- Untuk `data5a`, inch utama memakai Top 5 dinamis berdasarkan `Sum of total_cost`; inch lain digabung sebagai `other`.
- Untuk `data5b`, filter inch memakai Top 1 inch dari hasil `data5a`; Top 5 model pada inch tersebut memakai sorting `Sum of total_cost` descending, dan model lain digabung sebagai `other`.
- Untuk `data6`, kolom inch diurutkan numeric ascending lalu `Grand Total`.
- Untuk kategori/kunci baru selain aturan khusus di atas, default-nya ditampilkan dinamis.
- Nama job label: `Job Summary Result`.
- Nama config YAML: `job_summary_result.yaml`.

## Hasil studi workbook

Workbook referensi `outputs/result_learning_source.xlsx` memiliki sheet berikut:

- `result`
- `data1`
- `data2`
- `data3`
- `data4`
- `data5`
- `data6`

Pada workbook referensi, sheet `result` memiliki layout report dengan 3 baris header metadata, lalu header tabel aktual pada baris ke-4. Untuk source runtime, posisi header tidak boleh diasumsikan selalu baris ke-4; engine harus menemukan baris header secara fleksibel dari nama kolom aktual berikut:

- `notification`
- `job_sheet_section`
- `malfunction_start_date`
- `basic_finish_date`
- `model_name`
- `category`
- `serial_number`
- `symptom_code`
- `symptom_code_description`
- `pmacttype`
- `pmacttype_description`
- `symptom_comment`
- `repair_comment`
- `description`
- `warranty`
- `planner_group`
- `branch`
- `purchased_date`
- `labor_cost`
- `transportation_cost`
- `parts_cost`
- `part_used`
- `section`
- `prod_month`
- `inch`
- `total_cost`
- `diff_month`
- `part_name`
- `panel_usage`
- `factory`
- `symptom`
- `action`
- `defect_category`
- `defect`

Jumlah data aktual pada sheet `result` di workbook referensi: 2.263 baris. Angka ini hanya baseline referensi; source runtime bisa memiliki jumlah baris berbeda dan harus diproses dinamis.

Kolom numerik utama yang dipakai untuk summary:

- `labor_cost`
- `transportation_cost`
- `parts_cost`
- `total_cost`
- `inch`

Filter penting yang berulang:

- Semua summary `data1` dan `data2` mengecualikan `part_name` kosong/blanks.
- Summary `data3a` sampai `data6` hanya memakai baris dengan `part_name = PANEL`.

## Analisis kebutuhan output per sheet

### data1 — static summary part utama per section

Tujuan: membuat summary biaya dan count untuk part utama per `section`.

Sumber: dataset `result` hasil pembacaan workbook source satu sheet.

Filter:

- Exclude `part_name` kosong/blanks.

Dimensi:

- `section`
- kelompok `part_name` statis:
  - `PANEL`
  - `MAIN_UNIT`
  - `POWER_UNIT`
  - `OTHER`

Definisi `OTHER`:

- Semua `part_name` non-kosong selain `PANEL`, `MAIN_UNIT`, dan `POWER_UNIT`, dikelompokkan menjadi satu baris `OTHER` per section.

Agregasi:

- `Sum of labor_cost` = sum `labor_cost`
- `Sum of transportation_cost` = sum `transportation_cost`
- `Sum of parts_cost` = sum `parts_cost`
- `Sum of total_cost` = sum `total_cost`
- `Count of part_name` = count row `part_name`

Total:

- subtotal per `section`
- section ditampilkan dinamis jika muncul section baru di data masa depan
- grand total seluruh section

Catatan layout:

- Sheet contoh menampilkan baris note: `Noted : pivot khusus part_name, exclude part_name = "blanks"`
- Sheet contoh menampilkan mode: `mode: statis`
- hasil aktualnya tidak perlu menampilkan semua catatan diatas

Status kemampuan engine saat ini:

- Belum siap sepenuhnya untuk layout ini.
- Engine dapat melakukan group-by sederhana, tetapi belum memiliki output rule untuk bucket statis `OTHER`, subtotal per section, grand total, dan note/layout custom seperti contoh.

### data2 — pivot summary semua part_name per section

Tujuan: membuat pivot biaya dan count untuk semua `part_name` non-kosong per `section`.

Sumber: dataset `result` hasil pembacaan workbook source satu sheet.

Filter:

- Exclude `part_name` kosong/blanks.

Dimensi:

- `section`
- `part_name`

Agregasi:

- `Sum of labor_cost` = sum `labor_cost`
- `Sum of transportation_cost` = sum `transportation_cost`
- `Sum of parts_cost` = sum `parts_cost`
- `Sum of total_cost` = sum `total_cost`
- `Count of part_name` = count row `part_name`

Sorting yang terlihat dari contoh:

- Dalam setiap `section`, baris `part_name` diurutkan menurun berdasarkan nilai biaya utama/total, dengan `PANEL`, `MAIN_UNIT`, dan `POWER_UNIT` muncul di atas sesuai hasil agregasi.

Total:

- subtotal per `section`
- section ditampilkan dinamis jika muncul section baru di data masa depan
- grand total seluruh section

Catatan layout:

- Ada title area `Values` di bagian atas.
- Ada note: `Noted : pivot khusus part_name, exclude part_name = "blanks"`
- Ada mode: `mode: pivot`
- hasil aktualnya tidak perlu menampilkan semua catatan diatas dan hapus baris `Values`.

Status kemampuan engine saat ini:

- Sebagian bisa ditangani dengan group-by, tetapi belum cukup untuk format pivot persis seperti workbook karena belum ada subtotal, grand total, header multi-row, note, dan layout custom.

### data3a, data3b, data3c — panel defect by model, symptom, dan area

Tujuan: membuat 3 summary khusus `part_name = PANEL` sebagai sheet terpisah.

Sumber: dataset `result` hasil pembacaan workbook source satu sheet.

Filter global:

- `part_name = PANEL`

Sheet `data3a`: `A. Panel Defect by Inch and Model`

Dimensi:

- `part_name`
- `inch`
- `model_name`

Agregasi:

- `Total` = sum `total_cost`

Total:

- subtotal per `inch`
- `PANEL Total`
- `Grand Total`

Sheet `data3b`: `B. Panel by Symptom (unit)`

Dimensi:

- `part_name`
- `symptom`

Agregasi:

- `Total` = count `symptom`

Sorting:

- `symptom` diurutkan menurun berdasarkan count.

Total:

- `PANEL Total`
- `Grand Total`

Sheet `data3c`: `C. Panel by Area (unit)`

Dimensi:

- `part_name`
- `branch`

Agregasi:

- `Total` = count `branch`

Sorting:

- `branch` diurutkan menurun berdasarkan count.

Total:

- `PANEL Total`
- `Grand Total`

Catatan layout:

- Tiga blok dipisah menjadi sheet `data3a`, `data3b`, dan `data3c`.
- Ada mode: `mode: pivot` pada referensi, tetapi output final cukup struktur tabel dan angka yang sama.

Status kemampuan engine saat ini:

- Keputusan final memecah output menjadi `data3a`, `data3b`, dan `data3c`, sehingga tidak perlu dukungan multi-block berdampingan dalam satu sheet untuk tahap ini.
- Engine tetap perlu mendukung subtotal, total row, sorting, dan layout summary tanpa header report standar.

### data4 — panel usage count

Tujuan: menghitung distribusi usia panel untuk `part_name = PANEL`.

Sumber: dataset `result` hasil pembacaan workbook source satu sheet.

Filter:

- `part_name = PANEL`

Dimensi:

- `part_name`
- `panel_usage`

Agregasi:

- `Total` = count `panel_usage`

Urutan kategori final:

1. `< 1 Year`
2. `1 - 2 Years`
3. `2 - 3 Years`
4. `> 3 Years`

`panel_usage` kosong atau kategori baru di luar daftar ini diabaikan.

Total:

- `PANEL Total`
- `Grand Total`

Catatan layout:

- Ada title `Count of panel_usage`.
- Ada mode: `mode: pivot`.

Status kemampuan engine saat ini:

- Agregasi dasarnya sederhana dan bisa didekati dengan group-by.
- Namun total row, urutan kategori custom, dan layout pivot persis masih belum didukung penuh.

### data5a, data5b — f-cost panel by inch dan top 5 model dari Top 1 inch

Tujuan: membuat 2 summary khusus `part_name = PANEL` sebagai sheet terpisah.

Sumber: dataset `result` hasil pembacaan workbook source satu sheet.

Filter global:

- `part_name = PANEL`

Sheet `data5a`: `A. F-Cost Panel based on Inch Size`

Dimensi:

- `part_name`
- `inch_bucket`

Definisi `inch_bucket`:

- Inch utama adalah Top 5 dinamis berdasarkan `Sum of total_cost` pada data runtime.
- Semua inch selain Top 5 tersebut digabung sebagai `other`.

Agregasi:

- `Sum of labor_cost`
- `Sum of transportation_cost`
- `Sum of parts_cost`
- `Sum of total_cost`
- `Count of part_name`

Sorting:

- Top 5 inch ditentukan berdasarkan `Sum of total_cost` menurun, lalu `other` ditempatkan sebagai bucket gabungan.

Total:

- `PANEL Total`
- `Grand Total`

Sheet `data5b`: `B. Detail Panel Top 1 Inch (Top 5 Model)`

Filter tambahan:

- `part_name = PANEL`
- `inch` = Top 1 inch dari hasil `data5a` berdasarkan `Sum of total_cost`

Dimensi:

- `part_name`
- `inch`
- `model_name`

Agregasi:

- `Sum of labor_cost`
- `Sum of transportation_cost`
- `Sum of parts_cost`
- `Sum of total_cost`
- `Count of part_name`

Top-N:

- Ambil Top 5 `model_name` berdasarkan `Sum of total_cost`.
- Model selain Top 5 digabung sebagai `other`.

Total:

- `PANEL Total`
- `Grand Total`

Catatan:

- `data5c` tidak dibuat karena summary panel usage sudah tersedia sebagai `data4`.

Status kemampuan engine saat ini:

- Keputusan final memecah output data5 menjadi `data5a` dan `data5b`; `data5c` tidak dibuat karena sama dengan `data4`, sehingga tidak perlu dukungan sheet multi-block vertikal untuk tahap ini.
- Engine tetap perlu mendukung Top-N + `other`, subtotal, grand total, dan layout summary tanpa header report standar.

### data6 — panel symptom by inch matrix

Tujuan: membuat matrix count symptom panel berdasarkan inch.

Sumber: dataset `result` hasil pembacaan workbook source satu sheet.

Filter:

- `part_name = PANEL`

Rows:

- `part_name`
- `symptom`

Columns:

- `inch`

Values:

- count `symptom`

Kolom inch yang terlihat:

- `24`
- `32`
- `42`
- `43`
- `50`
- `55`
- `65`
- `75`
- `Grand Total`

Sorting:

- `symptom` diurutkan menurun berdasarkan `Grand Total`.

Total:

- `PANEL Total`
- `Grand Total`

Status kemampuan engine saat ini:

- Pivot dasar bisa didekati dengan `pivot_table`, tetapi engine belum mendukung margins/total row, sorting berdasarkan `Grand Total`, dan layout pivot yang persis seperti workbook.

## Pemeriksaan kemampuan engine saat ini

Berdasarkan pembacaan service dan config yang ada, engine saat ini memiliki dua jalur besar:

1. Legacy config:
   - source sheet biasa
   - master lookup
   - transform sederhana
   - output `columns`, `group_by`, atau `pivot`
2. Step recipe:
   - `extract_sheet`
   - `derive_column`
   - `update_columns`
   - `lookup_exact`
   - `lookup_exact_replace`
   - `lookup_rules`
   - `map_ranges`
   - `duplicate_group_rewrite`
   - output saat ini berupa pemilihan kolom dari dataset final

Kemampuan yang sudah ada dan relevan:

- Bisa membaca workbook `.xlsx`.
- Bisa memilih sheet source.
- Bisa menjalankan group-by sederhana pada legacy output.
- Bisa menjalankan pivot sederhana pada legacy output.
- Bisa menulis beberapa sheet output.
- Bisa menghasilkan sheet `result` dari recipe yang sudah ada.

Gap utama untuk kebutuhan sheet summary final:

1. Source runtime adalah workbook satu sheet dengan format seperti sheet `result`, tetapi posisi header dan jumlah baris data dapat berubah; reader saat ini masih membaca header default baris pertama, sehingga perlu mekanisme header locator yang mencari baris header berdasarkan kolom wajib dan pembacaan data dinamis sampai akhir data valid.
2. Step recipe output saat ini hanya mendukung pemilihan kolom, belum mendukung output aggregate/pivot.
3. Belum ada operasi output untuk:
   - filter per output sheet/block
   - bucket `OTHER`/`other`
   - Top-N + remainder `other`
   - subtotal per group
   - grand total
   - matrix pivot dengan margins
   - menghasilkan beberapa sheet summary dari satu dataset `result`
   - pemecahan blok summary menjadi sheet terpisah seperti `data3a`-`data3c` dan `data5a`-`data5b`
   - note/mode row sesuai workbook
4. Writer output saat ini menambahkan header report standar di setiap sheet, sedangkan sheet summary final pada workbook referensi memiliki layout pivot khusus tanpa header report standar yang sama seperti `result`.

Kesimpulan kemampuan engine:

- Engine saat ini belum bisa mengakomodir kebutuhan sheet summary final secara penuh dan presisi hanya lewat config job baru.
- Implementasi memerlukan perluasan engine output recipe agar dapat membangun summary/pivot custom dari dataset `result`.
- Setelah engine diperluas, job config baru dapat dibuat untuk menghasilkan `result`, `data1`, `data2`, `data3a`, `data3b`, `data3c`, `data4`, `data5a`, `data5b`, dan `data6` dalam satu workbook.

## Rekomendasi desain implementasi

### Prinsip desain

1. Jangan ubah logika transform row-level yang sudah menghasilkan `result`, kecuali ada konfirmasi terpisah.
2. Jangan ubah perilaku engine existing; tambahkan kemampuan baru sebagai jalur additive/opt-in untuk job ini.
3. Tambahkan kemampuan summary sebagai layer output setelah dataset `result` terbentuk.
4. Buat implementasi bertahap per sheet final: `data1`, lalu `data2`, lalu `data3a`-`data3c`, lalu `data4`, lalu `data5a`-`data5b`, lalu `data6`.
5. Setiap tahap harus dikonfirmasi sebelum coding.
6. Setiap tahap harus divalidasi angka totalnya terhadap workbook referensi.
7. Setiap penambahan kemampuan harus menjaga backward compatibility untuk job/config existing.

### Opsi arsitektur yang disarankan

Tambahkan konsep `summary_outputs` atau perluas `outputs` pada step recipe.

Contoh konsep deklaratif:

```yaml
summary_outputs:
  - sheet_name: data1
    type: static_part_summary
    source_dataset: result
    filter:
      - column: part_name
        is_not_blank: true
    rows:
      section_column: section
      part_column: part_name
      static_parts: [PANEL, MAIN_UNIT, POWER_UNIT]
      other_label: OTHER
    values:
      labor_cost: sum
      transportation_cost: sum
      parts_cost: sum
      total_cost: sum
      part_name: count
    totals:
      section_subtotal: true
      grand_total: true
```

Namun untuk menjaga scope dan menghindari over-engineering, implementasi awal boleh memakai builder internal yang mengenali tipe summary khusus:

- `static_part_summary`
- `part_pivot_summary`
- `panel_model_summary`
- `panel_symptom_summary`
- `panel_area_summary`
- `panel_usage_summary`
- `panel_fcost_inch_summary`
- `panel_top1_inch_model_summary`
- `panel_symptom_inch_matrix`

Setelah semua stabil, tipe-tipe ini bisa digeneralisasi bila diperlukan.

## Rencana implementasi bertahap

### Tahap 0 — persiapan teknis dan guardrail

Tujuan:

- Menentukan bentuk schema config summary output.
- Menentukan lokasi builder summary di engine.
- Menentukan strategi penulisan layout Excel.

Aktivitas:

1. Tambahkan reader source untuk workbook input satu sheet sebagai kemampuan baru/opt-in, tanpa mengganti reader existing untuk job lama.
2. Tambahkan header locator fleksibel yang mencari baris header berdasarkan kolom wajib `result`, bukan berdasarkan nomor baris, sebagai fitur baru yang dipakai job ini.
3. Pastikan reader baru memproses jumlah baris source secara dinamis sampai akhir data valid dan tidak memakai batas jumlah baris hard-coded.
4. Tambahkan parser/validator untuk output summary baru.
5. Tambahkan builder yang menerima DataFrame `result` dan menghasilkan object sheet layout.
6. Tambahkan writer yang bisa menulis sheet summary tanpa header report standar atau dengan mode layout khusus.
7. Pastikan output existing `result` tetap tidak berubah secara struktur kolom.
8. Jalankan validasi regresi minimal untuk memastikan job existing tetap menghasilkan output yang sama.

Keputusan final sebelum coding:

- Nama job baru: `Job Summary Result`.
- Nama config YAML baru: `job_summary_result.yaml`.
- Output berada dalam satu workbook bersama `result`.
- Source runtime adalah workbook input satu sheet dengan format tabel seperti sheet `result` pada workbook referensi.
- Header source dibaca fleksibel dengan header locator berbasis kolom wajib.
- Jumlah baris source runtime dinamis dan tidak boleh di-hard-code mengikuti jumlah baris referensi.
- Semua kemampuan baru bersifat additive/opt-in dan tidak boleh mengubah perilaku job/config existing.
- Cukup angka dan struktur tabel sama; tidak perlu pixel-perfect.

### Tahap 1 — implementasi data1

Tujuan:

- Generate sheet `data1` dari dataset `result`.

Aturan:

- Filter `part_name` non-kosong.
- Group `PANEL`, `MAIN_UNIT`, `POWER_UNIT` eksplisit.
- Gabungkan part lainnya ke `OTHER`.
- Hitung sum biaya dan count.
- Tambahkan subtotal `GQS Total`, `SASS Total`, dan `Grand Total`.
- Tidak perlu menambahkan note/mode row.

Validasi:

- Cocokkan subtotal `GQS Total`.
- Cocokkan subtotal `SASS Total`.
- Cocokkan `Grand Total`.
- Cocokkan count total.

Keputusan final sebelum coding:

- `OTHER` adalah seluruh `part_name` non-kosong selain `PANEL`, `MAIN_UNIT`, dan `POWER_UNIT`.
- Section selain `GQS`/`SASS` ditampilkan dinamis jika muncul di data masa depan.

### Tahap 2 — implementasi data2

Tujuan:

- Generate sheet `data2` pivot semua `part_name` per `section`.

Aturan:

- Filter `part_name` non-kosong.
- Group by `section`, `part_name`.
- Hitung sum biaya dan count.
- Sort part dalam setiap section berdasarkan `Sum of total_cost` descending.
- Tambahkan subtotal per section dan grand total.
- Tidak perlu menambahkan note/mode row atau baris `Values`.

Validasi:

- Jumlah baris part per section cocok dengan workbook referensi.
- Subtotal `GQS Total`, `SASS Total`, dan `Grand Total` cocok.

Keputusan final sebelum coding:

- Sorting final memakai `Sum of total_cost` descending dalam tiap section.

### Tahap 3 — implementasi data3a, data3b, data3c

Tujuan:

- Generate sheet `data3a`, `data3b`, dan `data3c` sebagai tiga summary panel terpisah.

Aturan:

- Filter `part_name = PANEL`.
- `data3a`: group by `inch`, `model_name`, sum `total_cost`, subtotal per inch.
- `data3b`: group by `symptom`, count, sort descending.
- `data3c`: group by `branch`, count, sort descending.
- Tambahkan total `PANEL Total` dan `Grand Total` pada masing-masing summary.

Validasi:

- Total Blok A = total panel `total_cost`.
- Total Blok B = jumlah row panel.
- Total Blok C = jumlah row panel.

Keputusan final sebelum coding:

- Tiga blok dipisah menjadi sheet `data3a`, `data3b`, dan `data3c`.

### Tahap 4 — implementasi data4

Tujuan:

- Generate sheet `data4` count `panel_usage` untuk panel.

Aturan:

- Filter `part_name = PANEL`.
- Group by `panel_usage`.
- Count row.
- Urutkan kategori: `< 1 Year`, `1 - 2 Years`, `2 - 3 Years`, `> 3 Years`.
- Abaikan `panel_usage` kosong atau kategori baru di luar daftar final.
- Tambahkan `PANEL Total` dan `Grand Total`.

Validasi:

- Total count = jumlah row panel.
- Count per kategori cocok.

Keputusan final sebelum coding:

- `panel_usage` kosong atau kategori baru di masa depan diabaikan.

### Tahap 5 — implementasi data5a, data5b

Tujuan:

- Generate sheet `data5a` dan `data5b` sebagai dua summary panel terpisah.

Aturan `data5a`:

- Filter `part_name = PANEL`.
- Group by `inch`.
- Ambil Top 5 inch dinamis berdasarkan `Sum of total_cost`.
- Gabungkan inch sisanya sebagai `other`.
- Hitung sum biaya dan count.
- Total row.

Aturan `data5b`:

- Filter `part_name = PANEL` dan `inch` sesuai Top 1 inch dari hasil `data5a` berdasarkan `Sum of total_cost`.
- Group by `model_name`.
- Ambil Top 5 berdasarkan `Sum of total_cost` descending.
- Gabungkan sisanya sebagai `other`.
- Hitung sum biaya dan count.
- Total row.

Catatan:

- `data5c` tidak dibuat karena sama dengan `data4`.

Validasi:

- `data5a` total = total panel semua inch.
- `data5b` total = total panel khusus Top 1 inch dari hasil `data5a`.

Keputusan final sebelum coding:

- `data5a` memakai Top 5 inch dinamis berdasarkan `Sum of total_cost`; inch lain menjadi `other`.
- `data5b` memakai Top 5 model dari Top 1 inch hasil `data5a` berdasarkan `Sum of total_cost` descending; model lain menjadi `other`.
- `data5c` tidak dibuat karena sama dengan `data4`.

### Tahap 6 — implementasi data6

Tujuan:

- Generate sheet `data6` matrix count symptom x inch untuk panel.

Aturan:

- Filter `part_name = PANEL`.
- Rows: `part_name`, `symptom`.
- Columns: `inch`, diurutkan numeric ascending.
- Values: count `symptom`.
- Tambahkan `Grand Total` column setelah seluruh kolom inch.
- Tambahkan `PANEL Total` row.
- Tambahkan `Grand Total` row.
- Sort symptom descending berdasarkan `Grand Total`.

Validasi:

- Grand total = jumlah row panel.
- Total per inch cocok dengan distribusi panel per inch.
- Total per symptom cocok dengan count symptom panel.

Keputusan final sebelum coding:

- Kolom inch mengikuti urutan numeric ascending, lalu `Grand Total`.

### Tahap 7 — integrasi job baru

Tujuan:

- Membuat config job baru yang memakai engine summary output.

Aktivitas:

1. Tambahkan YAML config job baru `job_summary_result.yaml`.
2. Tambahkan entry job baru pada registry job profile dengan label `Job Summary Result`.
3. Pastikan job dapat dipilih dari UI/runner.
4. Jalankan pipeline pada workbook source satu sheet yang formatnya sama dengan sheet `result` referensi.
5. Validasi header locator dengan variasi posisi header jika tersedia.
6. Validasi reader dengan variasi jumlah baris source jika tersedia.
7. Bandingkan workbook output terhadap aturan dan angka referensi dari `result_learning_source.xlsx`.

Keputusan final sebelum coding:

- Nama job label: `Job Summary Result`.
- Nama config file: `job_summary_result.yaml`.
- Job menerima workbook source satu sheet, membaca header dan jumlah baris secara fleksibel, lalu menghasilkan `result` dan seluruh sheet summary final dalam satu workbook pipeline.

## Strategi validasi akhir

Validasi numerik minimal:

1. `data1`:
   - total GQS
   - total SASS
   - grand total
2. `data2`:
   - jumlah baris part per section
   - total GQS
   - total SASS
   - grand total
3. `data3a`, `data3b`, `data3c`:
   - `data3a`: total cost panel
   - `data3b`: total count symptom panel
   - `data3c`: total count branch panel
4. `data4`:
   - total count panel usage = jumlah row panel dengan `panel_usage` kategori final pada source runtime
   - pada workbook referensi nilainya 482
5. `data5a`, `data5b`:
   - `data5a`: total = total panel cost
   - `data5b`: total = total panel pada Top 1 inch hasil `data5a`
6. `data6`:
   - grand total = jumlah row panel pada source runtime
   - pada workbook referensi nilainya 482
   - total per inch cocok dengan data panel

Validasi layout:

- Nama sheet persis: `data1`, `data2`, `data3a`, `data3b`, `data3c`, `data4`, `data5a`, `data5b`, `data6`.
- Header kolom sesuai workbook referensi selama relevan dengan sheet yang sudah dipisah.
- Struktur sheet terpisah `data3a`-`data3c` dan `data5a`-`data5b` tetap mudah dibaca; tidak wajib pixel-perfect.
- Note/mode row tidak perlu ditampilkan.

## Keputusan final yang sudah dikonfirmasi sebelum coding

1. Output cukup struktur tabel dan angka sama; tidak perlu pixel-perfect.
2. Job menerima workbook source satu sheet dengan format tabel seperti sheet `result`, membaca header dan jumlah baris secara fleksibel, lalu menghasilkan gabungan sheet `result` dan seluruh summary final dalam satu pipeline.
3. Implementasi tidak boleh mengubah perilaku engine/job existing; semua fitur baru harus additive/opt-in untuk job ini.
4. Untuk `data1`, `OTHER` adalah seluruh `part_name` non-kosong selain `PANEL`, `MAIN_UNIT`, dan `POWER_UNIT`.
5. Untuk `data1` dan `data2`, section baru ditampilkan dinamis.
6. Untuk `data2`, sorting memakai `Sum of total_cost` descending.
7. Untuk `data3`, tiga blok dipisah menjadi `data3a`, `data3b`, dan `data3c`.
8. Untuk `data4`, `panel_usage` kosong atau kategori baru diabaikan.
9. Untuk `data5`, hanya dibuat `data5a` dan `data5b`; `data5c` tidak dibuat karena sama dengan `data4`.
10. Untuk `data5a`, daftar inch utama dinamis Top 5 berdasarkan `Sum of total_cost`; inch lain menjadi `other`.
11. Untuk `data5b`, filter inch memakai Top 1 inch dari hasil `data5a`; Top 5 model pada inch tersebut berdasarkan `Sum of total_cost` descending, dan model lain menjadi `other`.
12. Untuk `data6`, kolom inch diurutkan numeric ascending lalu `Grand Total`.
13. Untuk kategori/kunci baru selain aturan khusus di atas, default-nya ditampilkan dinamis.
14. Nama job baru: `Job Summary Result`.
15. Nama config YAML: `job_summary_result.yaml`.

## Rekomendasi final

Rekomendasi implementasi adalah menambahkan kemampuan baru pada output layer secara additive/opt-in, bukan mengubah perilaku engine existing atau membuat transform row-level baru. Alasannya:

- Sheet summary final adalah summary dari dataset `result`, bukan data mentah baru.
- Logika pembentukan `result` sudah ada dan sebaiknya tetap menjadi fondasi, tetapi input reader perlu dibuat fleksibel untuk workbook satu sheet, posisi header yang berubah, dan jumlah baris source yang dinamis.
- Summary output membutuhkan kemampuan pivot/layout khusus yang sebaiknya ditempatkan setelah dataset final tersedia.

Urutan kerja yang paling aman:

1. Gunakan keputusan final yang sudah dikonfirmasi sebagai baseline implementasi.
2. Tambahkan kemampuan engine secara additive/opt-in tanpa mengubah perilaku job existing.
3. Implementasi engine summary minimal untuk `data1`.
4. Validasi `data1` terhadap workbook referensi.
5. Lanjut `data2`, `data3a`-`data3c`, `data4`, `data5a`-`data5b`, dan `data6` satu per satu dengan validasi numerik per tahap.
6. Setelah semua summary valid, baru buat job profile/config final.
