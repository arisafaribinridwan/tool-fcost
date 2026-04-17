# PRD - Excel Automation Tool

**Versi:** 2.4
**Status:** Siap mulai coding MVP
**Platform:** Windows 10/11 64-bit, portable tanpa install
**Stack:** Python 3.14 + CustomTkinter + pandas + openpyxl + PyYAML + PyInstaller

---

## 1. Tujuan

Membuat tool desktop lokal untuk mengotomatisasi proses olah file Excel/CSV menjadi output Excel yang sudah ditransformasi dan diformat, tanpa proses manual berulang di Excel.

Tool ini ditujukan untuk alur kerja personal dan dikembangkan dengan prioritas pengalaman development yang mulus di Linux maupun Windows, sementara distribusi final tetap berupa aplikasi portable untuk Windows.

---

## 2. Masalah yang Ingin Diselesaikan

Saat ini proses kerja dilakukan manual:

1. Ambil file sumber
2. Lakukan filter, lookup, kalkulasi, grouping, pivot, dan penyesuaian format
3. Buat output laporan Excel

Masalah utama:

- Proses repetitif dan memakan waktu
- Rawan salah rumus atau salah copy-paste
- Sulit dijaga konsisten antar periode
- Sulit diulang dengan cara yang sama tanpa checklist jelas

Tambahan masalah teknis yang ingin dihindari sejak awal:

- Alur web lokal menambah kompleksitas browser, port, dan static asset
- Packaging UI web lokal cenderung lebih ribet saat dibundle portable
- Development lintas OS lebih nyaman jika UI langsung berupa desktop app Python

---

## 3. Pengguna dan Konteks

- Pengguna utama: 1 orang, personal use
- Sistem operasi target runtime final: Windows 10/11 64-bit
- Sistem operasi development: Linux atau Windows
- Koneksi internet: tidak diperlukan setelah folder aplikasi dikopi
- Admin permission: tidak diperlukan
- Distribusi: folder portable hasil build PyInstaller

---

## 4. Alur Kerja Utama MVP

```txt
Buka aplikasi desktop
        ->
Pilih file sumber (.xlsx / .csv)
        ->
Load data master otomatis dari folder masters/
        ->
Pilih config resep (.yaml)
        ->
Klik Execute
        ->
Lihat log proses
        ->
Ambil file output (.xlsx) dari folder outputs/
```

Catatan:

- File master tidak dipilih per sesi; cukup diletakkan di folder `masters/`
- Satu resep boleh memakai lebih dari satu file master
- Satu use case awal difokuskan ke `1 source -> 1 output utama`
- Hasil output disimpan ke folder `outputs/` dan bisa dibuka dari aplikasi

---

## 5. Distribusi dan Cara Pakai

Tool didistribusikan sebagai folder portable:

```txt
ExcelAutoTool/
|- ExcelAutoTool.exe
|- run.bat
|- configs/
|- masters/
|- uploads/
`- outputs/
```

Cara pakai di PC tujuan:

1. Copy folder `ExcelAutoTool/`
2. Jalankan `run.bat` atau `ExcelAutoTool.exe`
3. Letakkan file master di folder `masters/`
4. Buka aplikasi desktop
5. Pilih file sumber
6. Pilih config YAML
7. Klik `Execute`
8. Ambil hasil dari folder `outputs/`

Target distribusi:

- Tanpa install Python
- Tanpa install library tambahan
- Tanpa internet
- Tanpa admin permission
- Packaging portable yang konsisten dengan `PyInstaller`

---

## 6. Scope MVP

### Wajib ada

- Pilih file sumber `.xlsx` dan `.csv` dari desktop app
- Load master otomatis dari folder `masters/`
- Config resep berbasis file YAML
- Filter data
- Mapping/lookup ke master
- Kalkulasi berbasis rule config
- Conditional rule dasar sesuai use case nyata
- Grouping dan agregasi
- Pivot/rekapitulasi
- Output 1 file `.xlsx` multi-sheet
- Header laporan berisi judul dan info periode
- Styling dasar Excel: warna header, border, font, number/date format, freeze pane
- Desktop UI sederhana berbasis `CustomTkinter`: pilih source, pilih config, execute, log, buka folder output
- Log proses yang jelas
- Error message yang mudah dipahami
- Packaging portable Windows dengan `PyInstaller`

### Tidak dikerjakan di MVP

- Multi-file source merge
- Visual config builder
- Logo/gambar di header
- Output multi-file terpisah
- Native installer `.msi` atau `.pkg`
- Support runtime final Mac/Linux
- Deploy ke server/cloud
- Multi-user concurrency

---

## 7. Input dan Output

### Input

- File sumber: `.xlsx` atau `.csv`
- File master: `.xlsx` atau `.csv`
- File config: `.yaml`

### Output

- Format utama: 1 file `.xlsx`
- Isi output: multi-sheet
- Bentuk output: custom spesifik mengikuti use case nyata pertama
- Nama file output sebaiknya unik untuk menghindari konflik overwrite
- Output fisik disimpan ke folder `outputs/`

---

## 8. Prinsip Desain Config YAML

YAML adalah sumber aturan transformasi untuk MVP.

Prinsip awal:

- Mudah dibaca dan diedit manual
- Cukup fleksibel untuk banyak master file
- Bisa berkembang per sub-tugas saat rule bisnis nyata sudah tersedia
- Validasi harus ketat agar error cepat terlihat

Contoh baseline:

```yaml
name: "Laporan Penjualan"
source_sheet: "Sheet1"

header:
  title: "Laporan Penjualan"
  period_from_column: "tanggal"

masters:
  - file: "masters/produk.xlsx"
    key: "kode_produk"
    columns: ["nama_produk", "kategori"]

outputs:
  - sheet_name: "Detail"
    columns: ["tanggal", "kode_produk", "qty", "harga"]

  - sheet_name: "Summary"
    pivot:
      index: "kategori"
      values: "qty"
      aggfunc: "sum"

styling:
  header_color: "4472C4"
  font: "Arial"
  number_format: "#,##0"
  date_format: "DD/MM/YYYY"
  freeze_pane: "A2"
```

Keputusan awal yang sudah jelas:

- Field root minimum: `name`, `source_sheet`, `header`, `outputs`
- `masters` boleh kosong
- `outputs` minimal 1 item
- `styling` boleh kosong dan memakai default internal
- Referensi master harus relatif ke folder `masters/`
- Nama kolom sementara dianggap case-sensitive
- Rule detail lookup, conditional, dan formula lanjutan akan difinalkan per sub-tugas berdasarkan sample nyata

---

## 9. Arsitektur Teknis

- Desktop UI: `CustomTkinter`
- Orkestrasi aplikasi: Python modular app
- Transformasi data: `pandas`
- Baca/tulis Excel: `openpyxl`
- Parsing config: `PyYAML`
- Packaging: `PyInstaller` `onedir`

Struktur modul yang diharapkan:

- `app/ui/` untuk komponen `CustomTkinter`
- `config_loader`
- `source_reader`
- `master_loader`
- `transformer`
- `formula_engine`
- `output_writer`
- `logger`
- `app_context` atau helper path runtime

Prinsip arsitektur:

- Logic bisnis harus terpisah dari layer UI
- UI hanya menangani input user, status proses, dan navigasi folder/file
- Resolusi path harus portable di Linux dan Windows
- Packaging harus mempertimbangkan mode source dan mode bundle PyInstaller

---

## 10. Constraint Teknis

- Target distribusi final tetap Windows 10/11 64-bit
- Development harian harus nyaman dilakukan di Linux maupun Windows
- Build tidak dianggap truly cross-build; binary final harus dibuild di OS targetnya
- Jika nanti ingin distribusi Linux atau macOS, build dilakukan terpisah di OS masing-masing
- Target ukuran data sekitar 20 ribu baris, diproses in-memory
- Log di UI cukup polling internal atau callback per awal dan akhir sub-tugas
- Kolom opsional yang hilang tidak boleh membuat sistem crash; cukup warning jika memang tidak kritikal
- Error umum harus tampil jelas ke user non-teknis
- Aplikasi harus tetap berjalan lokal tanpa internet
- Hasil build harus bisa dipakai di PC lain tanpa install Python

---

## 11. Asumsi Implementasi

- Use case pertama adalah `1 source -> 1 output utama`
- Format source yang harus diprioritaskan sejak awal adalah campuran `.xlsx` dan `.csv`
- Satu resep bisa memakai banyak master file
- Kebutuhan lookup dan conditional dipastikan ada, tetapi rule detailnya akan diisi saat breakdown sub-tugas
- Output target pertama adalah format custom spesifik, bukan sekadar summary generik
- Runtime directory `configs/`, `masters/`, `uploads/`, `outputs/` tetap dipakai agar konsisten di source mode maupun build mode
- UI tidak memerlukan browser lokal, web server, atau port tertentu
- Build final Windows dibuat di Windows; build Linux hanya bila memang ingin binary Linux terpisah

---

## 12. Kriteria Sukses MVP

MVP dianggap sukses jika:

- User bisa memilih file `.xlsx` atau `.csv`
- User bisa memilih config `.yaml`
- Sistem bisa load banyak master file dari folder `masters/`
- Sistem bisa menjalankan transformasi utama sesuai config dan use case nyata
- Sistem menghasilkan file `.xlsx` multi-sheet yang bisa dibuka di Excel
- Output punya header dan styling dasar
- UI desktop menampilkan log proses dan error yang jelas
- Hasil tersimpan ke folder `outputs/` dengan nama unik
- Aplikasi bisa dibundle dan dijalankan di PC Windows lain tanpa install Python
- Struktur kode tetap nyaman didevelop di Linux maupun Windows
- Minimal 1 use case nyata lolos validasi user

---

## 13. Hal yang Sengaja Ditunda Detailnya

Bagian ini memang belum dirinci final di PRD karena akan diturunkan saat breakdown task per sub-tugas:

- Rule lookup detail per master
- Conditional rule detail
- Formula lanjutan di luar aritmatika sederhana
- Kolom wajib per use case nyata
- Bentuk layout output custom final per sheet
- Detail polish UI desktop di luar kebutuhan alur MVP

Pendekatannya:

- PRD tetap simple dan jelas
- Detail bisnis diturunkan ke `task-plan.md`
- Saat sample nyata tersedia, detail rule ditambahkan per sub-tugas, bukan memenuhi PRD dengan banyak pengecualian

---

## 14. Kriteria Siap Coding

Dokumen dianggap cukup siap untuk mulai coding jika:

- Scope MVP tetap seperti di dokumen ini
- Struktur folder runtime disepakati: `configs/`, `masters/`, `uploads/`, `outputs/`
- Arsitektur UI disepakati: `CustomTkinter`, bukan web UI
- `task-plan.md` dipakai sebagai checklist implementasi utama
- Rule bisnis detail boleh menyusul per sub-tugas, selama arsitektur dasar sudah mendukungnya
- Strategi build lintas OS dipahami: develop bebas lintas OS, build final per target OS

---

*Dokumen ini adalah PRD v2.4 yang diperbarui untuk pendekatan desktop app `CustomTkinter` dan packaging `PyInstaller` yang lebih mulus untuk development serta build lintas OS.*
