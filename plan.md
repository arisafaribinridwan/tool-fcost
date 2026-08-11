# Rencana Fitur: Append Data dari Banyak Excel ke Satu Excel Target

## 1. Tujuan fitur

Membuat fitur baru pada aplikasi XLS-Flow Automator untuk membantu user menggabungkan data dari banyak file Excel `.xlsx` di satu folder sumber ke satu file Excel target yang dipilih user.

Fitur ini tidak membuat output workbook baru sebagai hasil utama. Fitur ini akan membuka file target yang dipilih, lalu menambahkan baris baru ke bawah data yang sudah ada pada sheet target.

Konsep utama:

- File target menjadi acuan struktur data.
- Header kolom yang digunakan untuk append mengikuti header pada file target.
- User memilih filter berdasarkan salah satu header di file target.
- Nilai filter diambil dari data yang sudah ada di file target.
- File sumber berada dalam satu folder dan semuanya `.xlsx`.
- Nama sheet dan format kolom file sumber diasumsikan sama dengan file target.
- Data duplikat dicegah berdasarkan gabungan kolom `notification`, `model name`, dan `keydate`.

## 2. Ringkasan workflow user

Alur penggunaan yang diinginkan:

1. User membuka mode fitur baru, misalnya menu `Append Folder Excel`.
2. User memilih file Excel target.
3. Tool membaca daftar sheet dari file target.
4. User memilih sheet target.
5. Tool membaca header pada sheet target.
6. Tool menampilkan daftar header tersebut.
7. User memilih satu header sebagai kolom filter.
8. Tool membaca nilai unik dari kolom filter di sheet target.
9. Tool menampilkan nilai unik tersebut dalam daftar checklist.
10. User mencentang nilai filter yang ingin digunakan.
11. User memilih folder sumber yang berisi banyak file `.xlsx`.
12. User menekan tombol proses.
13. Tool membaca semua file `.xlsx` dari folder sumber.
14. Untuk setiap file sumber, tool membaca sheet dengan nama yang sama seperti sheet target.
15. Tool mengambil baris yang nilai kolom filternya termasuk pilihan user.
16. Tool menyusun data mengikuti urutan header file target.
17. Tool mengosongkan kolom target yang tidak ditemukan di file sumber.
18. Tool mengecek duplikasi berdasarkan `notification + model name + keydate`.
19. Tool hanya menambahkan baris yang belum ada ke file target.
20. Tool menyimpan file target.
21. Tool menampilkan ringkasan hasil proses.

## 3. Definisi input dan output

### Input dari user

- File Excel target.
- Sheet target.
- Header yang dijadikan filter.
- Nilai filter yang dicentang.
- Folder sumber berisi file `.xlsx`.

### Input implisit dari file target

- Daftar sheet.
- Header pada sheet terpilih.
- Daftar nilai unik pada kolom filter.
- Data existing untuk pengecekan duplikat.

### Input dari folder sumber

- Semua file dengan ekstensi `.xlsx`.
- Untuk tahap awal, file temporary Excel seperti `~$nama_file.xlsx` sebaiknya diabaikan.
- Subfolder tidak perlu diproses pada versi awal kecuali nanti diminta.

### Output utama

- File target yang sama, dengan data baru ditambahkan di bawah data lama.

### Output pendukung

- Ringkasan proses di UI/log:
  - jumlah file ditemukan,
  - jumlah file berhasil dibaca,
  - jumlah file dilewati,
  - jumlah file gagal,
  - jumlah baris cocok filter,
  - jumlah baris baru ditambahkan,
  - jumlah baris dilewati karena duplikat,
  - daftar error per file.

## 4. Aturan pembacaan workbook

### Sheet

- User memilih nama sheet dari file target.
- File sumber diproses memakai nama sheet yang sama.
- Jika file sumber tidak memiliki sheet tersebut:
  - file tersebut dilewati,
  - status dicatat sebagai gagal atau skipped dengan alasan `Sheet target tidak ditemukan`.

### Header

- Header target menjadi acuan utama.
- Pada versi awal, header diasumsikan berada di baris pertama.
- Semua kolom output mengikuti urutan header pada file target.
- Header kosong di target diabaikan sebagai kolom data.
- Matching header sebaiknya dibuat toleran:
  - trim spasi di awal/akhir,
  - case-insensitive untuk pencocokan,
  - tetapi nama asli header target tetap dipertahankan untuk penulisan.

Contoh:

- Header target: `Notification`
- Header source: `notification`
- Dianggap cocok.

Catatan penting:

- Jika ada dua header yang menjadi sama setelah normalisasi, misalnya `Model Name` dan `model name`, tool perlu menolak proses dengan pesan validasi karena mapping kolom menjadi ambigu.

### Kolom yang ditulis

- Tool menulis seluruh kolom sesuai header target.
- Jika kolom target ditemukan di source, isi diambil dari source.
- Jika kolom target tidak ditemukan di source, nilai ditulis kosong.
- Kolom tambahan di source yang tidak ada di target diabaikan.

## 5. Aturan filter

### Sumber nilai filter

Nilai filter diambil dari kolom filter pada file target, bukan dari folder sumber.

Alasannya:

- File target berperan sebagai template dan daftar acuan.
- User ingin memilih kriteria dari nilai yang sudah ada di target.
- Folder sumber tidak perlu discan lebih awal hanya untuk membangun daftar filter.

### Pemilihan kolom filter

- Tool menampilkan semua header target.
- User memilih satu header sebagai kolom filter.
- Setelah kolom dipilih, tool membaca nilai unik pada kolom tersebut.

### Pemilihan nilai filter

- Tool menampilkan nilai unik dalam bentuk checklist.
- User bisa mencentang satu atau banyak nilai.
- Nilai kosong sebaiknya ditampilkan sebagai label khusus, misalnya `(kosong)`.
- Perlu tersedia kontrol pencarian/filter daftar checklist jika jumlah nilai unik banyak.
- Perlu tersedia tombol `Pilih Semua` dan `Kosongkan Pilihan`.

### Matching nilai filter

Rekomendasi awal:

- Matching nilai filter dilakukan dengan normalisasi:
  - trim spasi,
  - case-insensitive,
  - nilai numerik seperti `123.0` dan `123` dianggap sama jika aman.

Untuk tanggal:

- Jika kolom filter berisi tanggal, nilai yang ditampilkan ke user harus stabil dan mudah dibaca.
- Matching tanggal perlu dinormalisasi agar tanggal Excel, `datetime`, dan string tanggal yang sama tidak dianggap berbeda.
- Format tampilan yang disarankan: `YYYY-MM-DD` untuk tanggal murni.

## 6. Aturan anti-duplikasi

Duplikasi dicegah dengan gabungan tiga kolom:

- `notification`
- `model name`
- `keydate`

Baris dari source dianggap duplikat jika kombinasi tiga nilai tersebut sudah ada di target, atau sudah muncul lebih dulu dalam batch source yang sedang diproses.

### Normalisasi duplicate key

Untuk mengurangi false duplicate dan false new row:

- Nama kolom key dicocokkan case-insensitive dan trim spasi.
- Nilai key dinormalisasi dengan trim spasi.
- Text dibandingkan case-insensitive.
- Angka dengan akhiran `.0` dapat disamakan dengan bentuk integer text.
- Tanggal pada `keydate` perlu dinormalisasi ke bentuk stabil, misalnya `YYYY-MM-DD`, jika memungkinkan.

### Validasi duplicate key

Jika salah satu dari tiga kolom key tidak ada di file target:

- proses tidak boleh dilanjutkan,
- tampilkan pesan bahwa kolom duplicate key wajib ada di target.

Jika salah satu dari tiga kolom key tidak ada di file source:

- ada dua opsi, tetapi rekomendasi untuk versi awal adalah proses file tersebut gagal/skipped.
- Alasannya, tanpa key lengkap, anti-duplikasi tidak bisa dipercaya.

Catatan:

- Ini berbeda dari aturan kolom target lain yang boleh kosong jika tidak ada di source.
- Khusus duplicate key, kolom wajib ada agar proses aman.

### Baris dengan key kosong

Perlu diputuskan sebelum implementasi final.

Rekomendasi awal:

- Jika ketiga nilai key kosong, baris dianggap tidak valid dan dilewati.
- Jika sebagian key kosong, baris tetap diproses tetapi dicatat sebagai warning, atau dilewati agar anti-duplikasi lebih aman.

Rekomendasi paling aman:

- Lewati baris jika salah satu dari `notification`, `model name`, atau `keydate` kosong.
- Tampilkan jumlah baris yang dilewati karena duplicate key tidak lengkap.

## 7. Perilaku append ke target

### Lokasi append

- Data baru ditambahkan mulai dari baris setelah data terakhir di sheet target.
- Header tidak ditulis ulang.
- Urutan kolom mengikuti header target.

### Format dan style

Pilihan awal yang sederhana:

- Append value saja.
- Tidak memaksakan style baru.

Opsional yang bisa ditambahkan:

- Copy style dari baris data terakhir di target ke baris baru.
- Highlight baris baru dengan warna tertentu.
- Resize Excel Table jika sheet target memakai tabel Excel.

Catatan arsitektur:

- Repo sudah memiliki `app/services/target_workbook_update_service.py` yang punya kemampuan append, anti-duplikasi, highlight baris baru, dan resize table untuk use case lain.
- Fitur baru bisa mengambil pola atau helper dari service tersebut, tetapi use case ini sebaiknya dibuat sebagai service baru karena arahnya berbeda: banyak source ke satu target.

## 8. Rencana UI

### Lokasi fitur

Ada dua pendekatan:

1. Tambah mode baru di main window.
2. Buat window/tool terpisah dari main workflow.

Rekomendasi:

- Buat mode/window terpisah, misalnya `Append Folder Excel`.
- Alasannya, workflow ini tidak memakai job profile/config pipeline utama.
- Ini menghindari main workflow yang sekarang menjadi terlalu padat.

### Komponen UI yang dibutuhkan

- Tombol pilih file target.
- Label path file target terpilih.
- Dropdown sheet target.
- Dropdown header filter.
- Kotak pencarian nilai filter.
- Scrollable checklist nilai filter.
- Tombol `Pilih Semua`.
- Tombol `Kosongkan`.
- Tombol pilih folder sumber.
- Label path folder sumber terpilih.
- Tombol `Precheck`.
- Tombol `Proses Append`.
- Progress/status area.
- Log area.
- Summary area setelah proses selesai.

### State tombol

- `Pilih sheet` aktif setelah target berhasil dibaca.
- `Pilih header filter` aktif setelah sheet dipilih dan header valid.
- Checklist aktif setelah header filter dipilih.
- `Proses Append` aktif hanya jika:
  - target valid,
  - sheet dipilih,
  - header filter dipilih,
  - minimal satu nilai filter dicentang,
  - folder sumber valid,
  - duplicate key columns tersedia di target.

### Precheck

Precheck sebaiknya tersedia sebelum proses write.

Precheck memvalidasi:

- file target ada dan `.xlsx`,
- file target bisa dibuka,
- sheet target ada,
- header target tidak kosong,
- kolom filter ada,
- duplicate key columns ada di target,
- folder sumber ada,
- ada file `.xlsx` yang bisa diproses,
- minimal beberapa file source memiliki sheet target,
- minimal beberapa file source memiliki kolom filter,
- duplicate key columns ada di source.

Precheck sebaiknya tidak menulis apapun ke target.

## 9. Rencana service layer

Disarankan membuat service baru:

`app/services/folder_excel_append_service.py`

Service ini bertanggung jawab untuk:

- membaca metadata file target,
- membaca daftar sheet,
- membaca header target,
- membaca nilai unik filter dari target,
- melakukan precheck folder source,
- membaca dan memfilter data source,
- menyusun row sesuai header target,
- mengecek duplikasi,
- append data ke target,
- menghasilkan result object untuk UI.

### Dataclass yang disarankan

`TargetWorkbookMetadata`

- `path: Path`
- `sheet_names: list[str]`

`TargetSheetMetadata`

- `sheet_name: str`
- `headers: list[str]`
- `duplicate_key_columns_present: bool`
- `warnings: list[str]`

`FilterValueOption`

- `raw_value: object`
- `display_value: str`
- `normalized_value: str`
- `count: int`

`SourceFileAppendResult`

- `file_name: str`
- `status: str`
- `matched_rows: int`
- `appended_rows: int`
- `duplicate_rows: int`
- `invalid_key_rows: int`
- `reason: str`

`FolderAppendResult`

- `target_file: Path`
- `target_sheet_name: str`
- `source_folder: Path`
- `files_found: int`
- `files_processed: int`
- `files_skipped: int`
- `files_failed: int`
- `matched_rows: int`
- `appended_rows: int`
- `duplicate_rows: int`
- `invalid_key_rows: int`
- `file_results: list[SourceFileAppendResult]`

### Fungsi service yang disarankan

`load_target_workbook_metadata(target_file: Path) -> TargetWorkbookMetadata`

- Membuka workbook target.
- Mengembalikan daftar sheet.
- Tidak membaca semua data.

`load_target_sheet_metadata(target_file: Path, sheet_name: str) -> TargetSheetMetadata`

- Membaca header.
- Memvalidasi duplicate key columns.

`load_filter_value_options(target_file: Path, sheet_name: str, filter_column: str) -> list[FilterValueOption]`

- Membaca nilai unik filter dari target.
- Mengembalikan display value dan count.

`precheck_folder_append_request(...) -> FolderAppendPrecheckResult`

- Validasi semua input.
- Scan file source.
- Baca metadata ringan dari source.
- Menghasilkan warning/error tanpa menulis file.

`append_folder_excels_to_target(...) -> FolderAppendResult`

- Menjalankan proses utama.
- Membuka target workbook.
- Mengumpulkan existing duplicate keys.
- Membaca tiap source workbook.
- Filter data.
- Append row baru.
- Save target.
- Mengembalikan ringkasan detail.

## 10. Rencana integrasi dengan UI

### File UI baru

Kemungkinan file:

- `app/ui/folder_append_window.py`

Atau jika ingin tetap di main app:

- Tambahkan tombol di `app/ui/main_window.py` untuk membuka window baru.

Rekomendasi:

- Tambahkan tombol kecil di sidebar atau area bawah main window: `Append Folder Excel`.
- Tombol ini membuka window terpisah agar workflow utama tetap fokus ke job pipeline.

### Threading

Proses append harus berjalan di worker thread seperti pipeline utama, karena:

- membaca banyak workbook bisa lama,
- menulis target bisa lama,
- UI tidak boleh freeze.

Pola yang bisa diikuti:

- gunakan `Queue`,
- worker mengirim event log/progress,
- UI polling queue dengan `after`.

### Logging

Contoh log:

- `Target dipilih: file_target.xlsx`
- `Sheet dipilih: Raw Data`
- `Header target ditemukan: 42 kolom`
- `Filter: Model Name, nilai dipilih: 5`
- `Folder sumber: D:/Data/Source`
- `File sumber ditemukan: 128`
- `[updated] source_001.xlsx - matched=20, appended=18, duplicate=2`
- `[skipped] source_002.xlsx - sheet tidak ditemukan`
- `Selesai: appended=430, duplicate=88, failed=3`

## 11. Rencana validasi dan error handling

### Error yang menghentikan seluruh proses

- Target file tidak ditemukan.
- Target file bukan `.xlsx`.
- Target file tidak bisa dibuka.
- Sheet target tidak ditemukan.
- Header target kosong.
- Kolom filter tidak ada di target.
- Duplicate key columns tidak lengkap di target.
- Folder source tidak ditemukan.
- Tidak ada file `.xlsx` di folder source.
- User belum memilih nilai filter.
- Target file sedang terkunci oleh Excel sehingga tidak bisa disimpan.

### Error per file source

Error ini tidak harus menghentikan seluruh proses:

- file source tidak bisa dibuka,
- sheet target tidak ada di source,
- header source kosong,
- kolom filter tidak ada di source,
- duplicate key columns tidak lengkap di source.

Setiap error per source dicatat di result dan log.

### File target termasuk di folder source

Jika file target ada di dalam folder source:

- file target harus di-skip saat scan source.
- Alasannya agar data target tidak dibaca sebagai source dan menimbulkan duplikasi aneh.

## 12. Rencana normalisasi data

Normalisasi perlu dibuat konsisten untuk:

- header matching,
- filter matching,
- duplicate key matching.

### Header normalization

Fungsi helper:

`normalize_header(value: object) -> str`

Aturan:

- convert ke string,
- trim,
- collapse spasi berulang menjadi satu spasi,
- casefold.

### Value normalization

Fungsi helper:

`normalize_cell_value(value: object) -> str`

Aturan:

- `None` dan NaN menjadi string kosong,
- trim text,
- casefold untuk matching,
- angka integer-like tidak ditampilkan sebagai `123.0`,
- tanggal dinormalisasi jika tipe datanya date/datetime/pandas Timestamp.

### Display value

Fungsi helper:

`format_filter_display_value(value: object) -> str`

Aturan:

- kosong menjadi `(kosong)`,
- tanggal menjadi `YYYY-MM-DD`,
- angka integer-like menjadi tanpa `.0`,
- text ditampilkan dengan trim.

## 13. Rencana testing

Tambahkan test service baru, misalnya:

`tests/test_folder_excel_append_service.py`

Test minimum:

1. Membaca sheet names dari target.
2. Membaca header target.
3. Membaca nilai unik filter dari target.
4. Append data dari satu source ke target.
5. Append data dari banyak source ke target.
6. Hanya baris dengan nilai filter terpilih yang diappend.
7. Urutan kolom hasil mengikuti header target.
8. Kolom target yang tidak ada di source diisi kosong.
9. Kolom tambahan di source diabaikan.
10. Duplicate existing di target tidak diappend.
11. Duplicate antar source dalam batch yang sama tidak diappend.
12. Duplicate key memakai `notification + model name + keydate`.
13. Proses gagal jika duplicate key columns tidak ada di target.
14. Source file dilewati jika sheet target tidak ditemukan.
15. Source file dilewati jika kolom filter tidak ditemukan.
16. File temporary `~$...xlsx` diabaikan.
17. Target file di dalam source folder tidak ikut diproses sebagai source.
18. Tanggal `keydate` yang sama tidak dianggap berbeda hanya karena format cell berbeda.
19. Proses mengembalikan summary jumlah file/baris yang benar.
20. Target workbook tetap bisa dibuka setelah proses save.

Test UI bisa ditambahkan lebih ringan:

- tombol proses disabled sampai input lengkap,
- daftar sheet berubah setelah target dipilih,
- daftar header berubah setelah sheet dipilih,
- daftar checklist muncul setelah filter dipilih.

## 14. Tahapan implementasi yang disarankan

### Tahap 1: Finalisasi aturan

- Konfirmasi posisi header selalu baris pertama.
- Konfirmasi source folder tidak recursive.
- Konfirmasi baris dengan duplicate key tidak lengkap dilewati.
- Konfirmasi apakah style baris baru perlu dicopy atau cukup value saja.

### Tahap 2: Service metadata target

- Buat service baru untuk membaca workbook target.
- Implementasi baca sheet names.
- Implementasi baca header sheet.
- Implementasi baca nilai unik filter.
- Tambahkan unit test metadata.

### Tahap 3: Service append core

- Implementasi scan source folder.
- Implementasi mapping header source ke header target.
- Implementasi filter row.
- Implementasi duplicate key detection.
- Implementasi append ke target.
- Tambahkan unit test proses utama.

### Tahap 4: Precheck

- Implementasi precheck tanpa write.
- Tambahkan ringkasan warning/error.
- Pastikan UI bisa menampilkan precheck result.

### Tahap 5: UI window

- Buat window `Append Folder Excel`.
- Tambahkan pilih target, sheet, header filter, checklist nilai filter, pilih source folder.
- Tambahkan tombol precheck dan proses.
- Tambahkan log dan summary.
- Jalankan proses di worker thread.

### Tahap 6: Integrasi ke aplikasi utama

- Tambahkan entry point dari main window.
- Pastikan packaging tetap menyertakan module baru.
- Pastikan tidak mengganggu workflow job profile yang sudah ada.

### Tahap 7: Polishing

- Tambahkan search pada checklist filter.
- Tambahkan pilih semua/kosongkan.
- Tambahkan progress per file.
- Tambahkan pesan error yang ramah.
- Tambahkan opsi highlight baris baru jika dibutuhkan.

## 15. Keputusan desain sementara

Keputusan yang sudah disepakati:

- File source hanya `.xlsx`.
- Folder source berisi file dengan format kolom dan nama sheet yang sama.
- User tetap bisa memilih sheet target.
- Header target menjadi acuan kolom yang dicopy.
- Nilai filter diambil dari Excel target.
- Data hasil copy ditambahkan ke bawah data target yang sudah ada.
- Jika kolom target tidak ditemukan di source, isi dikosongkan.
- Duplikasi dicegah berdasarkan `notification + model name + keydate`.

Keputusan yang masih perlu dikonfirmasi sebelum coding:

- Header selalu berada di baris pertama atau ada kemungkinan header mulai di baris lain.
- Apakah scan folder source perlu recursive ke subfolder.
- Apakah baris dengan salah satu duplicate key kosong harus dilewati atau tetap boleh ditambahkan.
- Apakah baris baru perlu mengikuti style baris terakhir target.
- Apakah perlu membuat backup file target sebelum proses append.

## 16. Rekomendasi tambahan

Sebelum proses append, sangat disarankan tool membuat backup otomatis file target.

Contoh:

- Target: `report.xlsx`
- Backup: `report.backup-20260812-153000.xlsx`

Alasannya:

- Fitur ini menulis langsung ke file target.
- Jika user salah memilih filter atau source folder, data target bisa bertambah banyak.
- Backup membuat proses lebih aman dan mudah dikembalikan.

Rekomendasi default:

- Backup otomatis aktif.
- Backup disimpan di folder yang sama dengan target.
- Nama backup memakai timestamp.
- UI menampilkan lokasi backup setelah proses selesai.

## 17. Nama fitur yang mungkin digunakan

Beberapa opsi nama:

- `Append Folder Excel`
- `Copy Multi Excel`
- `Import dari Folder Excel`
- `Tarik Data dari Folder`
- `Append ke Target Excel`

Rekomendasi nama UI:

`Append Folder Excel`

Nama ini cukup singkat dan menggambarkan bahwa fitur membaca banyak Excel dari folder lalu append ke target.
