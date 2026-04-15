# Task Plan Komprehensif - Excel Automation Tool

Dokumen ini diturunkan dari `prd.md` dan ditulis sebagai panduan utama implementasi MVP end-to-end.

Target dokumen ini:
- Menjadi checklist kerja utama dari awal sampai distribusi.
- Menjadi panduan eksekusi untuk developer pemula.
- Menjadi konteks kerja yang cukup jelas untuk model AI lain yang lebih murah.
- Menjelaskan dependency yang harus di-install manual oleh user, bukan oleh AI.

## 1. Ringkasan Proyek

Nama proyek: `Excel Automation Tool`

Tujuan MVP:
- Upload file sumber `.xlsx` atau `.csv`
- Load data master otomatis dari folder `masters/`
- Pilih file config `.yaml`
- Jalankan transformasi data otomatis
- Hasilkan file output `.xlsx` multi-sheet dengan styling
- Jalankan sebagai aplikasi portable Windows tanpa install apa pun di PC tujuan

Stack utama sesuai PRD:
- Python 3.11
- Flask
- pandas
- openpyxl
- PyYAML
- PyInstaller
- HTML + JavaScript vanilla

## 2. Keputusan Scope MVP

### Fitur yang wajib selesai di MVP

- [ ] Upload file sumber `.xlsx` dan `.csv`
- [ ] Membaca data master otomatis dari folder `masters/`
- [ ] Membaca config resep dari file `.yaml`
- [ ] Filter data
- [ ] Grouping / agregasi
- [ ] Pivot / rekapitulasi
- [ ] Mapping data master setara VLOOKUP
- [ ] Kalkulasi rumus kustom berbasis kolom
- [ ] Output multi-sheet dalam satu file Excel
- [ ] Header output berisi judul dan info periode
- [ ] Styling dasar output Excel
- [ ] Web UI sederhana dengan upload, pilihan config, tombol execute, dan live log
- [ ] Error handling dan log yang mudah dipahami
- [ ] Packaging ke format portable Windows (`.exe` + `run.bat`)

### Fitur yang tidak dikerjakan di MVP

- [ ] Multi-file source merge
- [ ] Visual config builder
- [ ] Logo atau gambar pada header
- [ ] Output multi-file terpisah
- [ ] Support Mac atau Linux
- [ ] Deploy server atau cloud
- [ ] CLI mode sebagai prioritas utama

## 3. Hal yang Perlu Dipastikan Sebelum Coding

Bagian ini penting karena di PRD masih ada 1 pertanyaan terbuka.

### Open question dari PRD

- [ ] Kumpulkan contoh kasus nyata pertama: file sumber + hasil transformasi yang diinginkan

### Keputusan teknis awal yang perlu dikunci

- [ ] Pastikan hanya support Windows 10/11 64-bit untuk distribusi final
- [ ] Pastikan format output utama adalah 1 file `.xlsx` multi-sheet
- [ ] Pastikan file master boleh berupa `.xlsx` atau `.csv`
- [ ] Pastikan YAML menjadi satu-satunya sumber aturan transformasi di MVP
- [ ] Pastikan data diproses in-memory dengan pandas untuk kisaran 20 ribu baris
- [ ] Pastikan browser dibuka lokal dari aplikasi desktop portable

### Keputusan struktur proyek yang perlu disepakati sejak awal

- [ ] Tentukan nama folder root distribusi: `ExcelAutoTool/`
- [ ] Tentukan struktur folder source code development dan struktur folder hasil build
- [ ] Tentukan standar penamaan config YAML, master file, output file, dan log file
- [ ] Tentukan strategi error log: tampil di UI, simpan ke file, atau keduanya

## 4. Daftar Install Manual

Bagian ini khusus untuk user karena user ingin melakukan instalasi manual sendiri.

## 4.1 Software yang harus di-install manual di mesin development

- [ ] Install Python 3.11.x 64-bit
- [ ] Install Git
- [ ] Install VS Code atau editor lain
- [ ] Install Google Chrome atau Microsoft Edge untuk testing UI lokal

Catatan:
- Python untuk development harus di-install manual.
- Di PC tujuan hasil akhir, Python tidak perlu di-install karena akan dibundle dengan PyInstaller.

## 4.2 Library Python yang harus di-install manual

### Library runtime utama

- [ ] `Flask`
- [ ] `pandas`
- [ ] `openpyxl`
- [ ] `PyYAML`

### Library packaging

- [ ] `pyinstaller`

### Library testing dan quality yang direkomendasikan

- [ ] `pytest`
- [ ] `ruff`

### Library opsional tapi sangat direkomendasikan

- [ ] `python-dotenv`

Catatan:
- `python-dotenv` opsional. Berguna jika nanti ingin memisahkan konfigurasi environment seperti port, mode debug, atau lokasi folder kerja.
- Untuk MVP sederhana, proyek tetap bisa jalan tanpa library ini.

## 4.3 Perintah install manual yang direkomendasikan

Jalankan manual oleh user, bukan oleh AI:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Windows CMD:

```bat
.venv\Scripts\activate.bat
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install dependency inti:

```bash
pip install Flask pandas openpyxl PyYAML pyinstaller pytest ruff python-dotenv
```

## 4.4 File dependency yang perlu dibuat

- [ ] Buat `requirements.txt`
- [ ] Pin versi dependency setelah instalasi berhasil
- [ ] Simpan dependency minimum yang benar-benar dipakai proyek

Contoh awal yang direkomendasikan:

```txt
Flask>=3.0,<4.0
pandas>=2.2,<3.0
openpyxl>=3.1,<4.0
PyYAML>=6.0,<7.0
pyinstaller>=6.0,<7.0
pytest>=8.0,<9.0
ruff>=0.6,<1.0
python-dotenv>=1.0,<2.0
```

## 5. Struktur Folder Development yang Disarankan

Struktur ini tidak wajib identik, tapi sangat direkomendasikan agar rapi dan mudah diikuti oleh developer pemula.

```txt
project-root/
├── app/
│   ├── __init__.py
│   ├── web/
│   │   ├── routes.py
│   │   ├── templates/
│   │   │   └── index.html
│   │   └── static/
│   │       ├── css/
│   │       └── js/
│   ├── services/
│   │   ├── config_loader.py
│   │   ├── source_reader.py
│   │   ├── master_loader.py
│   │   ├── transformer.py
│   │   ├── formula_engine.py
│   │   ├── output_writer.py
│   │   └── logger.py
│   ├── models/
│   │   └── recipe_schema.py
│   └── utils/
│       ├── paths.py
│       ├── validators.py
│       └── dates.py
├── configs/
├── masters/
├── uploads/
├── outputs/
├── tests/
│   ├── test_config_loader.py
│   ├── test_master_loader.py
│   ├── test_transformer.py
│   ├── test_output_writer.py
│   └── fixtures/
├── run.py
├── requirements.txt
├── build.spec
├── run.bat
└── README.md
```

## 6. Arsitektur Implementasi yang Disarankan

## 6.1 Alur backend yang disarankan

Urutan eksekusi utama:

1. User upload file sumber.
2. Backend simpan file ke folder `uploads/`.
3. Backend baca daftar config YAML yang tersedia di folder `configs/`.
4. User pilih config.
5. Saat execute:
6. Validasi file source dan config.
7. Load source data ke pandas DataFrame.
8. Load semua master yang dibutuhkan dari folder `masters/`.
9. Jalankan transformasi sesuai YAML.
10. Bangun seluruh output DataFrame per sheet.
11. Tulis ke file `.xlsx`.
12. Tambahkan header, styling, format angka, format tanggal, freeze pane.
13. Simpan file ke `outputs/`.
14. Tampilkan status sukses atau error di UI.
15. Sediakan tombol download hasil.

## 6.2 Modul yang perlu ada

### Modul web

- [ ] Endpoint halaman utama
- [ ] Endpoint upload file
- [ ] Endpoint execute proses
- [ ] Endpoint download hasil
- [ ] Endpoint list config YAML yang tersedia
- [ ] Endpoint log status jika live log dibuat polling

### Modul config loader

- [ ] Baca file YAML
- [ ] Validasi struktur wajib YAML
- [ ] Beri pesan error yang jelas jika field wajib hilang
- [ ] Normalisasi nilai config agar mudah dipakai modul lain

### Modul source reader

- [ ] Baca `.xlsx`
- [ ] Baca `.csv`
- [ ] Pilih `source_sheet` jika format Excel
- [ ] Validasi sheet tersedia
- [ ] Validasi kolom minimum jika diperlukan resep

### Modul master loader

- [ ] Baca file master dari path relatif seperti `masters/produk.xlsx`
- [ ] Support file `.xlsx`
- [ ] Support file `.csv`
- [ ] Validasi kolom key master tersedia
- [ ] Return DataFrame yang siap di-merge

### Modul transformer

- [ ] Filter data
- [ ] Grouping dan agregasi
- [ ] Pivot table
- [ ] Merge ke master untuk mapping VLOOKUP-like
- [ ] Pemilihan kolom output
- [ ] Warning jika kolom opsional tidak ada

### Modul formula engine

- [ ] Evaluasi formula sederhana berbasis kolom, contoh `qty * harga`
- [ ] Validasi formula hanya memakai kolom yang diizinkan
- [ ] Tangani error formula dengan pesan yang mudah dipahami
- [ ] Hindari evaluasi expression yang berbahaya

### Modul output writer

- [ ] Tulis banyak sheet ke satu file Excel
- [ ] Tambahkan header 2-3 baris di atas tabel
- [ ] Terapkan warna header
- [ ] Terapkan border
- [ ] Terapkan font
- [ ] Terapkan format angka
- [ ] Terapkan format tanggal
- [ ] Terapkan freeze pane
- [ ] Auto width kolom bila memungkinkan

### Modul logging

- [ ] Buat log proses per langkah
- [ ] Tampilkan log ke UI
- [ ] Tulis log error detail untuk debugging
- [ ] Bedakan level `INFO`, `WARNING`, dan `ERROR`

## 7. Desain YAML yang Harus Diselesaikan

PRD sudah memberi contoh, tapi untuk implementasi stabil perlu checklist desain schema yang lebih eksplisit.

### Checklist schema YAML MVP

- [ ] Tetapkan field wajib level root: `name`, `source_sheet`, `header`, `outputs`
- [ ] Tetapkan apakah `masters` boleh kosong
- [ ] Tetapkan default `styling` jika tidak diisi
- [ ] Tetapkan format `formulas`
- [ ] Tetapkan format output `group_by`
- [ ] Tetapkan format output `pivot`
- [ ] Tetapkan aturan `columns` apakah wajib ada atau bisa otomatis
- [ ] Tetapkan aturan nama kolom case-sensitive atau tidak
- [ ] Tetapkan perilaku jika sheet output sudah ada namanya sama

### Checklist validasi YAML

- [ ] Gagal jika YAML tidak valid secara sintaks
- [ ] Gagal jika field wajib tidak ada
- [ ] Gagal jika `source_sheet` tidak ditemukan pada source Excel
- [ ] Gagal jika file master yang direferensikan tidak ada
- [ ] Warning jika kolom opsional tidak ada
- [ ] Gagal jika formula mereferensikan kolom yang tidak tersedia
- [ ] Gagal jika `pivot.aggfunc` tidak didukung

### Daftar kemampuan YAML minimal MVP

- [ ] `name`
- [ ] `source_sheet`
- [ ] `header.title`
- [ ] `header.period_from_column`
- [ ] `masters[].file`
- [ ] `masters[].key`
- [ ] `masters[].columns`
- [ ] `outputs[].sheet_name`
- [ ] `outputs[].group_by`
- [ ] `outputs[].columns`
- [ ] `outputs[].formulas`
- [ ] `outputs[].pivot.index`
- [ ] `outputs[].pivot.values`
- [ ] `outputs[].pivot.aggfunc`
- [ ] `styling.header_color`
- [ ] `styling.font`
- [ ] `styling.number_format`
- [ ] `styling.date_format`
- [ ] `styling.freeze_pane`

## 8. Checklist Implementasi Tahap demi Tahap

## 8.1 Tahap 1 - Setup awal proyek

- [ ] Buat repository atau siapkan folder proyek development
- [ ] Buat virtual environment `.venv`
- [ ] Install semua dependency manual
- [ ] Buat `requirements.txt`
- [ ] Buat struktur folder dasar proyek
- [ ] Buat file `README.md`
- [ ] Buat `.gitignore`
- [ ] Buat file entry point seperti `run.py`

Definition of done tahap 1:
- [ ] Proyek bisa dijalankan sebagai aplikasi Flask sederhana
- [ ] Struktur folder dasar sudah ada
- [ ] Dependency sudah terdokumentasi

## 8.2 Tahap 2 - Bangun skeleton web UI

- [ ] Buat halaman utama HTML
- [ ] Buat area upload file
- [ ] Buat dropdown atau list pilihan config YAML
- [ ] Buat tombol `Execute`
- [ ] Buat area live log
- [ ] Buat area hasil dan tombol download
- [ ] Tambahkan validasi frontend sederhana

Definition of done tahap 2:
- [ ] Halaman utama tampil rapi
- [ ] User bisa pilih file source
- [ ] User bisa lihat daftar config
- [ ] Tombol execute dan placeholder log sudah terlihat

## 8.3 Tahap 3 - Implement upload dan pembacaan source

- [ ] Buat endpoint upload
- [ ] Simpan file ke folder `uploads/`
- [ ] Validasi hanya `.xlsx` atau `.csv`
- [ ] Implement reader untuk Excel
- [ ] Implement reader untuk CSV
- [ ] Tangani sheet Excel yang tidak ada
- [ ] Tangani file kosong atau rusak

Definition of done tahap 3:
- [ ] File source berhasil diupload dan dibaca
- [ ] Error upload tampil jelas

## 8.4 Tahap 4 - Implement config YAML

- [ ] Baca semua file `.yaml` di folder `configs/`
- [ ] Tampilkan config yang tersedia ke UI
- [ ] Implement parser YAML
- [ ] Implement validator YAML
- [ ] Buat minimal 2 contoh file config

Definition of done tahap 4:
- [ ] Config valid bisa dipilih dan dibaca
- [ ] Config invalid menghasilkan error yang mudah dipahami

## 8.5 Tahap 5 - Implement master loader

- [ ] Buat loader file master dari folder `masters/`
- [ ] Support `.xlsx`
- [ ] Support `.csv`
- [ ] Validasi file master ada
- [ ] Validasi kolom key ada
- [ ] Siapkan merge helper untuk mapping

Definition of done tahap 5:
- [ ] Master file bisa dibaca dan di-merge ke source

## 8.6 Tahap 6 - Implement engine transformasi inti

- [ ] Implement filter data
- [ ] Implement pemilihan kolom
- [ ] Implement formula sederhana
- [ ] Implement group by dan agregasi
- [ ] Implement pivot table
- [ ] Implement mapping ke master
- [ ] Implement warning untuk kolom opsional hilang

Definition of done tahap 6:
- [ ] Satu config nyata bisa menghasilkan DataFrame output sesuai target

## 8.7 Tahap 7 - Implement writer Excel dan styling

- [ ] Tulis output ke beberapa sheet
- [ ] Tambahkan header teks di atas tabel
- [ ] Tambahkan periode berdasarkan min/max kolom tanggal
- [ ] Tambahkan styling header
- [ ] Tambahkan border tabel
- [ ] Terapkan font
- [ ] Terapkan format angka
- [ ] Terapkan format tanggal
- [ ] Terapkan freeze pane
- [ ] Simpan ke folder `outputs/`

Definition of done tahap 7:
- [ ] File `.xlsx` hasil dapat dibuka di Excel
- [ ] Format dasar terlihat sesuai PRD

## 8.8 Tahap 8 - Integrasi execute flow end-to-end

- [ ] Integrasikan upload + config + master + transform + output
- [ ] Tampilkan log per langkah di UI
- [ ] Tampilkan status sukses atau gagal
- [ ] Tampilkan link download hasil
- [ ] Pastikan proses gagal secara aman bila ada error

Definition of done tahap 8:
- [ ] User bisa menjalankan alur lengkap dari UI sampai download output

## 8.9 Tahap 9 - Error handling dan hardening

- [ ] Tangani file source rusak
- [ ] Tangani config rusak
- [ ] Tangani master file hilang
- [ ] Tangani sheet source tidak ada
- [ ] Tangani kolom wajib hilang
- [ ] Tangani formula error
- [ ] Tangani output file sedang dibuka Excel sehingga gagal overwrite
- [ ] Tangani nama sheet terlalu panjang atau tidak valid untuk Excel

Definition of done tahap 9:
- [ ] Semua error umum menghasilkan pesan yang jelas dan tidak crash diam-diam

## 8.10 Tahap 10 - Testing

- [ ] Buat unit test parser YAML
- [ ] Buat unit test source reader
- [ ] Buat unit test master loader
- [ ] Buat unit test transformer
- [ ] Buat unit test formula engine
- [ ] Buat unit test output writer minimum
- [ ] Buat minimal 1 integration test end-to-end
- [ ] Siapkan file fixture kecil untuk test

Definition of done tahap 10:
- [ ] Test kritikal lulus
- [ ] Jalur happy path dan error path utama tercakup

## 8.11 Tahap 11 - Packaging portable Windows

- [ ] Siapkan command atau file spec PyInstaller
- [ ] Pastikan template HTML dan static assets ikut terbundle
- [ ] Pastikan folder `configs/`, `masters/`, `uploads/`, `outputs/` tersedia saat runtime
- [ ] Buat `run.bat`
- [ ] Pastikan browser terbuka otomatis ke local URL
- [ ] Uji build di Windows bersih

Definition of done tahap 11:
- [ ] Folder hasil build bisa dicopy ke PC lain dan jalan tanpa install manual

## 8.12 Tahap 12 - Validasi user acceptance

- [ ] Uji dengan contoh kasus nyata dari PC kerja
- [ ] Bandingkan hasil output dengan proses manual lama
- [ ] Catat gap hasil dan revisi YAML atau logic transformasi
- [ ] Finalisasi config resep produksi pertama

Definition of done tahap 12:
- [ ] Satu use case kerja nyata berjalan stabil dan hasilnya diterima user

## 9. Checklist Detail per Fitur

## 9.1 Upload file source

- [ ] Batasi tipe file `.xlsx` dan `.csv`
- [ ] Batasi ukuran file jika diperlukan
- [ ] Cegah nama file berbahaya
- [ ] Gunakan nama file output upload yang aman dan unik

## 9.2 Load master otomatis

- [ ] Semua referensi master harus relatif terhadap folder `masters/`
- [ ] Jangan izinkan path traversal seperti `../`
- [ ] Cache load master selama satu eksekusi bila file sama dipakai berulang

## 9.3 Mapping ala VLOOKUP

- [ ] Tentukan merge key source
- [ ] Tentukan merge key master
- [ ] Tentukan join type default, rekomendasi `left join`
- [ ] Log jumlah baris yang tidak match

## 9.4 Formula kustom

- [ ] Batasi formula hanya operasi aman seperti `+`, `-`, `*`, `/`, `()`
- [ ] Dokumentasikan formula yang didukung
- [ ] Tolak fungsi Python arbitrer

## 9.5 Output multi-sheet

- [ ] Validasi nama sheet unik
- [ ] Potong nama sheet jika melebihi batas Excel
- [ ] Hindari karakter ilegal Excel pada nama sheet

## 9.6 Styling output

- [ ] Header title ada di baris atas
- [ ] Periode otomatis dari data tanggal
- [ ] Header tabel diberi warna
- [ ] Angka pakai number format
- [ ] Tanggal pakai date format
- [ ] Freeze pane aktif

## 9.7 Logging

- [ ] Log mulai proses
- [ ] Log file source yang dipakai
- [ ] Log config yang dipakai
- [ ] Log master yang berhasil dibaca
- [ ] Log langkah transformasi
- [ ] Log lokasi file output
- [ ] Log error detail bila gagal

## 10. Checklist Non-Fungsional

## 10.1 Kualitas kode

- [ ] Nama fungsi dan modul jelas
- [ ] Fungsi tidak terlalu panjang tanpa alasan
- [ ] Error message bisa dimengerti user non-teknis
- [ ] Kode dipisah berdasarkan tanggung jawab

## 10.2 Maintainability

- [ ] YAML mudah dibaca dan diedit manual
- [ ] Menambah resep baru tidak perlu ubah banyak kode
- [ ] Menambah master baru cukup drop file dan ubah YAML

## 10.3 Reliability

- [ ] Perubahan kolom opsional tidak membuat sistem crash
- [ ] Error umum tertangani dengan baik
- [ ] Output tetap konsisten untuk input yang sama

## 10.4 Portability

- [ ] Tidak bergantung pada internet
- [ ] Tidak bergantung pada admin permission
- [ ] Tidak bergantung pada Python terinstall di PC tujuan

## 11. Risk Register Sederhana

### Risiko teknis utama

- [ ] Risiko: format file sumber nyata berbeda dari asumsi PRD
Mitigasi: minta sample nyata secepat mungkin dan jadikan test fixture utama.

- [ ] Risiko: formula YAML terlalu fleksibel dan rawan error atau unsafe
Mitigasi: batasi grammar formula sejak awal.

- [ ] Risiko: styling Excel mengganggu performa atau kompleksitas
Mitigasi: mulai dari styling dasar yang stabil dulu.

- [ ] Risiko: packaging PyInstaller gagal membawa asset template/static
Mitigasi: siapkan test build khusus packaging.

- [ ] Risiko: file output gagal disimpan karena sedang dibuka di Excel
Mitigasi: gunakan nama output unik berbasis timestamp dan tampilkan error jelas.

## 12. Checklist Testing Manual

### Happy path

- [ ] Upload file `.xlsx` valid dan execute berhasil
- [ ] Upload file `.csv` valid dan execute berhasil
- [ ] Config valid menghasilkan output multi-sheet
- [ ] Header periode terisi benar
- [ ] Styling dasar muncul benar

### Error path

- [ ] Upload file dengan ekstensi tidak didukung
- [ ] Upload file Excel rusak
- [ ] Pilih config YAML rusak
- [ ] Referensi master file tidak ada
- [ ] Kolom wajib tidak ada
- [ ] Formula salah
- [ ] Nama sheet output tidak valid
- [ ] Output file sedang dibuka saat overwrite

### Packaging path

- [ ] Jalankan dari hasil build `.exe`
- [ ] Jalankan lewat `run.bat`
- [ ] Coba di PC Windows lain tanpa Python terinstall
- [ ] Pastikan browser terbuka dan halaman bisa diakses
- [ ] Pastikan upload dan download tetap jalan di hasil build

## 13. Checklist Dokumentasi yang Wajib Dibuat

- [ ] `README.md` untuk setup development
- [ ] `requirements.txt`
- [ ] Minimal 1 contoh config YAML yang valid
- [ ] Dokumentasi struktur YAML
- [ ] Dokumentasi format file source yang diharapkan
- [ ] Dokumentasi format file master yang diharapkan
- [ ] Dokumentasi build PyInstaller
- [ ] Dokumentasi cara menjalankan hasil portable
- [ ] Dokumentasi troubleshooting umum

## 14. Rekomendasi Urutan Eksekusi Paling Aman

Urutan ini direkomendasikan agar developer pemula tidak tersesat.

1. [ ] Setup environment development
2. [ ] Buat skeleton Flask + halaman index
3. [ ] Implement upload source
4. [ ] Implement parser dan validator YAML
5. [ ] Implement source reader
6. [ ] Implement master loader
7. [ ] Implement transformasi dasar
8. [ ] Implement formula engine sederhana
9. [ ] Implement writer Excel
10. [ ] Implement styling Excel
11. [ ] Integrasikan execute flow penuh
12. [ ] Tambahkan logging dan error handling
13. [ ] Tambahkan test
14. [ ] Build PyInstaller
15. [ ] Uji di Windows portable
16. [ ] Validasi dengan kasus kerja nyata

## 15. Rekomendasi Skill AI yang Dibutuhkan

Bagian ini ditulis praktis agar bisa dipakai saat bekerja dengan AI coding assistant.

## 15.1 Skill AI untuk Python dasar

Skill yang dibutuhkan:
- [ ] Paham struktur proyek Python sederhana
- [ ] Paham virtual environment, `requirements.txt`, import, package, module
- [ ] Paham error handling Python
- [ ] Paham file I/O dan path handling di Windows
- [ ] Paham testing dengan `pytest`
- [ ] Paham packaging dengan PyInstaller

Kemampuan prompt yang sebaiknya dimiliki AI:
- [ ] Bisa membuat fungsi kecil yang jelas dan testable
- [ ] Bisa membaca traceback dan memperbaiki bug Python
- [ ] Bisa menjaga kompatibilitas Windows path
- [ ] Bisa memisahkan logic web, transformasi data, dan output Excel

## 15.2 Skill AI untuk pandas

Skill yang dibutuhkan:
- [ ] Paham `read_excel`, `read_csv`, `merge`, `groupby`, `pivot_table`
- [ ] Paham handling kolom kosong, tipe data campur, parsing tanggal
- [ ] Paham agregasi dan rename kolom hasil transformasi
- [ ] Paham cara debugging mismatch merge dan hasil pivot
- [ ] Paham performa dasar pandas untuk data skala kecil-menengah

Kemampuan prompt yang sebaiknya dimiliki AI:
- [ ] Bisa menerjemahkan aturan bisnis ke operasi DataFrame
- [ ] Bisa memberi contoh input-output tabel kecil untuk verifikasi logika
- [ ] Bisa membuat transformasi yang deterministik dan mudah diuji

## 15.3 Skill AI untuk openpyxl dan Excel output

Skill yang dibutuhkan:
- [ ] Paham membuat workbook dan multi-sheet
- [ ] Paham styling sel: font, fill, border, alignment
- [ ] Paham freeze pane, merge cells, column width, number format, date format
- [ ] Paham batasan nama sheet Excel

## 15.4 Skill AI untuk Flask dan web UI sederhana

Skill yang dibutuhkan:
- [ ] Paham routing Flask dasar
- [ ] Paham upload file via form
- [ ] Paham rendering template HTML
- [ ] Paham endpoint download file
- [ ] Paham AJAX atau fetch sederhana untuk execute dan live log

## 15.5 Skill AI untuk proyek ini secara spesifik

AI yang dipakai idealnya mampu:
- [ ] Menjaga scope agar tetap sesuai MVP
- [ ] Tidak terlalu cepat menambah fitur di luar PRD
- [ ] Menulis validasi YAML yang ketat
- [ ] Menjaga keamanan dasar pada upload file dan formula
- [ ] Memprioritaskan portability Windows
- [ ] Menulis error message yang ramah user non-teknis
- [ ] Menyiapkan testing dan packaging, bukan hanya coding happy path

## 15.6 Rekomendasi peran AI dalam proyek ini

AI role yang paling berguna:
- [ ] AI sebagai implementer modul kecil
- [ ] AI sebagai reviewer logika transformasi pandas
- [ ] AI sebagai generator test case dari sample input-output
- [ ] AI sebagai penulis dokumentasi YAML dan troubleshooting
- [ ] AI sebagai checker packaging PyInstaller

## 16. Prompt Template untuk AI Lain yang Lebih Murah

Template ini bisa dipakai berulang agar model murah tetap terarah.

### Template 1 - Implement modul

```txt
Kamu membantu proyek Excel Automation Tool berbasis Python + Flask + pandas + openpyxl.
Kerjakan hanya scope MVP berikut: upload source, load master dari folder masters/, parse YAML config, transform data, output multi-sheet Excel, styling dasar, log yang jelas, packaging Windows portable.

Tugasmu saat ini:
[isi tugas spesifik di sini]

Batasan:
- Jangan tambah fitur di luar MVP.
- Gunakan Python 3.11.
  - Pisahkan logic web, transformasi data, dan output Excel.
- Jika ada asumsi, tulis asumsi secara eksplisit.
- Jika validasi perlu ditambahkan, tambahkan.
- Beri hasil dalam bentuk kode + penjelasan singkat.
```

### Template 2 - Review kode

```txt
Review kode berikut untuk proyek Excel Automation Tool.
Fokus review pada:
- bug
- edge case
- validasi input
- keamanan upload file
- keamanan evaluasi formula
- akurasi transformasi pandas
- kualitas error message
- kesiapan dipakai developer pemula

Jangan fokus ke style minor dulu. Utamakan masalah fungsional dan risiko.
```

### Template 3 - Buat test case

```txt
Buat test case `pytest` untuk modul berikut pada proyek Excel Automation Tool.
Fokus pada happy path dan error path.
Gunakan fixture kecil dan data sederhana yang mudah dipahami developer pemula.

Modul target:
[isi nama modul]
```

## 17. Definition of Done Proyek MVP

MVP dianggap selesai jika semua poin ini terpenuhi.

- [ ] User bisa upload file source `.xlsx` atau `.csv`
- [ ] User bisa memilih config `.yaml`
- [ ] Sistem otomatis load master dari folder `masters/`
- [ ] Sistem menjalankan filter, mapping, formula, group, pivot sesuai config
- [ ] Sistem menghasilkan file `.xlsx` multi-sheet
- [ ] Output memiliki header dan styling dasar
- [ ] UI menampilkan log proses dan error yang jelas
- [ ] Hasil bisa didownload
- [ ] Aplikasi bisa dibundle menjadi folder portable Windows
- [ ] Build hasil portable bisa dijalankan di PC lain tanpa install Python
- [ ] Minimal satu kasus nyata dari PC kerja lolos validasi user

## 18. Backlog Setelah MVP Valid

- [ ] Multi-file source merge
- [ ] Output multi-file terpisah
- [ ] Visual config builder
- [ ] Header dengan logo atau gambar
- [ ] Mekanisme update tool
- [ ] Refactor config schema bila use case nyata bertambah kompleks

## 19. Catatan Penting untuk Developer Pemula

- [ ] Jangan mulai dari PyInstaller. Selesaikan flow lokal dulu.
- [ ] Jangan mulai dari styling Excel yang rumit. Selesaikan data correctness dulu.
- [ ] Jangan buat YAML terlalu canggih di awal. Mulai dari kebutuhan kasus nyata pertama.
- [ ] Selalu uji dengan data kecil sebelum file nyata.
- [ ] Setiap bug nyata sebaiknya diubah menjadi test case.
- [ ] Jika hasil DataFrame sudah benar, baru lanjut ke formatting Excel.
- [ ] Jika build portable gagal, cek dulu path asset, template, dan working directory.

## 20. Pertanyaan yang Masih Perlu Jawaban User

Bagian ini belum menghalangi penyusunan task plan, tetapi perlu dijawab saat implementasi agar hasil tidak meleset.

- [ ] Seperti apa contoh file source nyata pertama?
- [ ] Kolom wajib apa saja yang hampir selalu ada?
- [ ] Bentuk output akhir yang dianggap benar seperti apa?
- [ ] Apakah satu resep bisa punya lebih dari satu master file sekaligus? PRD mengarah ke iya, tapi perlu dipastikan dengan contoh nyata.
- [ ] Apakah formula cukup aritmatika sederhana, atau nanti butuh kondisi seperti `if/else`?
- [ ] Apakah live log cukup tampil setelah proses selesai, atau harus benar-benar streaming saat proses berjalan?

Jika jawaban untuk pertanyaan di atas sudah tersedia, dokumen ini sebaiknya diperbarui agar lebih presisi sebelum coding penuh dimulai.
