# Task Plan - Excel Automation Tool

Dokumen ini adalah checklist implementasi utama untuk MVP.
Fokusnya dibuat sederhana, jelas, dan bisa dipakai monitoring progress harian.

## Cara Pakai

- Centang item yang sudah selesai.
- Jika ada perubahan scope, update `prd.md` dulu.
- Jika ada rule bisnis baru dari sample nyata, tambahkan di sub-tugas terkait.
- Detail lookup, conditional, dan formula lanjutan diisi per use case, tidak perlu dipaksa final dari awal.

## 1. Gate Awal

- [ ] PRD sudah cukup jelas untuk mulai coding.
- [ ] Scope MVP sudah dikunci.
- [ ] Platform target dikunci: Windows 10/11 64-bit.
- [ ] Format output dikunci: 1 file `.xlsx` multi-sheet.
- [ ] Struktur folder runtime dikunci: `configs/`, `masters/`, `uploads/`, `outputs/`.
- [ ] Use case awal dikunci: `1 source -> 1 output utama`.
- [ ] Support source awal dikunci: `.xlsx` dan `.csv`.
- [ ] Satu resep boleh memakai banyak master file.
- [ ] Model live log dikunci: polling per awal/akhir sub-tugas.

## 2. Setup Development

- [ ] Install Python 3.11.x 64-bit.
- [ ] Install Git.
- [ ] Install editor kerja.
- [ ] Buat virtual environment `.venv`.
- [ ] Upgrade `pip`.
- [ ] Install dependency runtime.
- [ ] Install dependency testing/linting.
- [ ] Buat `requirements.txt`.
- [ ] Buat `.gitignore`.
- [ ] Buat `README.md` setup singkat.

## 3. Install Manual yang Diperlukan

### Software

- [ ] Python 3.11.x 64-bit
- [ ] Git
- [ ] VS Code atau editor lain
- [ ] Chrome atau Edge untuk testing UI lokal

### Library Python

- [ ] `Flask`
- [ ] `pandas`
- [ ] `openpyxl`
- [ ] `PyYAML`
- [ ] `pyinstaller`
- [ ] `pytest`
- [ ] `ruff`
- [ ] `python-dotenv` (opsional)

### Perintah install manual

```bash
python -m venv .venv
python -m pip install --upgrade pip
pip install Flask pandas openpyxl PyYAML pyinstaller pytest ruff python-dotenv
```

PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

CMD:

```bat
.venv\Scripts\activate.bat
```

## 4. Struktur Proyek

- [ ] Buat folder `app/`.
- [ ] Buat folder `app/web/`.
- [ ] Buat folder `app/web/templates/`.
- [ ] Buat folder `app/web/static/css/`.
- [ ] Buat folder `app/web/static/js/`.
- [ ] Buat folder `app/services/`.
- [ ] Buat folder `app/utils/`.
- [ ] Buat folder `configs/`.
- [ ] Buat folder `masters/`.
- [ ] Buat folder `uploads/`.
- [ ] Buat folder `outputs/`.
- [ ] Buat folder `tests/`.
- [ ] Buat file `run.py`.

## 5. Breakdown Fase Implementasi

### Fase 1 - Skeleton aplikasi

- [ ] Buat app Flask dasar.
- [ ] Buat route halaman utama.
- [ ] Buat template `index.html` awal.
- [ ] Pastikan app bisa dijalankan lokal.

Definition of done:

- [ ] Halaman utama tampil di browser lokal.

### Fase 2 - Web UI dasar

- [ ] Buat area upload file.
- [ ] Buat dropdown/list config YAML.
- [ ] Buat tombol `Execute`.
- [ ] Buat area log proses.
- [ ] Buat area hasil/download.
- [ ] Tambahkan validasi frontend sederhana.

Definition of done:

- [ ] User bisa melihat alur dasar dari UI walau backend belum lengkap.

### Fase 3 - Config loader dan schema dasar

- [ ] Baca semua file `.yaml` dari folder `configs/`.
- [ ] Parse YAML.
- [ ] Validasi field root minimum.
- [ ] Validasi struktur `masters`.
- [ ] Validasi struktur `outputs`.
- [ ] Validasi struktur `styling`.
- [ ] Buat error message yang mudah dipahami.
- [ ] Buat minimal 2 config contoh.

Definition of done:

- [ ] Config valid bisa dibaca.
- [ ] Config invalid menghasilkan error jelas.

### Fase 4 - Source reader

- [ ] Implement reader `.xlsx`.
- [ ] Implement reader `.csv`.
- [ ] Validasi ekstensi file.
- [ ] Validasi sheet source untuk Excel.
- [ ] Validasi file kosong atau rusak.
- [ ] Validasi kolom minimum jika dibutuhkan config.

Definition of done:

- [ ] File source `.xlsx` dan `.csv` bisa dibaca ke DataFrame.

### Fase 5 - Master loader

- [ ] Implement loader master `.xlsx`.
- [ ] Implement loader master `.csv`.
- [ ] Validasi file master ada.
- [ ] Validasi path aman dan tidak path traversal.
- [ ] Validasi key master ada.
- [ ] Support banyak master file dalam satu resep.
- [ ] Siapkan helper merge dasar.

Definition of done:

- [ ] Banyak master bisa dibaca dan siap dipakai transformasi.

### Fase 6 - Transform engine dasar

- [ ] Implement filter data.
- [ ] Implement pilih kolom output.
- [ ] Implement rename kolom bila diperlukan.
- [ ] Implement merge/mapping ala lookup.
- [ ] Implement group by dan agregasi.
- [ ] Implement pivot table.
- [ ] Tambahkan warning untuk kolom opsional yang hilang.

Definition of done:

- [ ] Transformasi dasar berjalan untuk config sederhana.

### Fase 7 - Formula dan conditional engine

- [ ] Implement formula aritmatika sederhana.
- [ ] Siapkan struktur untuk conditional rule.
- [ ] Siapkan struktur untuk lookup rule lanjutan.
- [ ] Validasi rule agar tidak unsafe.
- [ ] Buat pesan error formula/rule yang jelas.

Sub-tugas rule bisnis yang akan diisi nanti:

- [ ] Definisikan jenis lookup yang dibutuhkan sample nyata.
- [ ] Definisikan jenis conditional yang dibutuhkan sample nyata.
- [ ] Definisikan formula lanjutan yang dibutuhkan sample nyata.
- [ ] Definisikan prioritas urutan eksekusi rule.

Definition of done:

- [ ] Engine siap menampung rule bisnis nyata tanpa bongkar arsitektur dasar.

### Fase 8 - Output writer Excel

- [ ] Tulis output ke multi-sheet.
- [ ] Tambahkan header laporan 2-3 baris.
- [ ] Ambil info periode dari kolom tanggal yang ditentukan config.
- [ ] Terapkan warna header tabel.
- [ ] Terapkan border.
- [ ] Terapkan font.
- [ ] Terapkan format angka.
- [ ] Terapkan format tanggal.
- [ ] Terapkan freeze pane.
- [ ] Validasi nama sheet Excel.
- [ ] Simpan file ke folder `outputs/`.

Definition of done:

- [ ] File `.xlsx` hasil bisa dibuka dan tampil rapi secara dasar.

### Fase 9 - Logging dan progress

- [ ] Buat logger proses per langkah.
- [ ] Log awal sub-tugas.
- [ ] Log akhir sub-tugas.
- [ ] Log warning.
- [ ] Log error.
- [ ] Tampilkan log ke UI dengan polling.

Definition of done:

- [ ] User bisa melihat progress proses utama dari UI.

### Fase 10 - Integrasi end-to-end

- [ ] Hubungkan upload + pilih config + execute.
- [ ] Load source saat execute.
- [ ] Load semua master saat execute.
- [ ] Jalankan transformasi sesuai config.
- [ ] Tulis output Excel.
- [ ] Tampilkan status sukses/gagal.
- [ ] Tampilkan link download hasil.

Definition of done:

- [ ] Alur dari upload sampai download berjalan lokal.

### Fase 11 - Hardening dan error handling

- [ ] Tangani file source tidak valid.
- [ ] Tangani config invalid.
- [ ] Tangani master file hilang.
- [ ] Tangani sheet source tidak ditemukan.
- [ ] Tangani kolom wajib hilang.
- [ ] Tangani rule formula/conditional invalid.
- [ ] Tangani nama sheet invalid.
- [ ] Tangani file output gagal ditulis karena sedang dibuka.
- [ ] Pastikan pesan error mudah dipahami user non-teknis.

Definition of done:

- [ ] Error umum tidak membuat aplikasi crash diam-diam.

### Fase 12 - Testing

- [ ] Buat fixture kecil untuk source.
- [ ] Buat fixture kecil untuk master.
- [ ] Buat fixture kecil untuk YAML.
- [ ] Buat unit test config loader.
- [ ] Buat unit test source reader.
- [ ] Buat unit test master loader.
- [ ] Buat unit test transform engine.
- [ ] Buat unit test formula/rule engine.
- [ ] Buat unit test output writer.
- [ ] Buat minimal 1 integration test.

Definition of done:

- [ ] Happy path dan error path utama tercakup.

### Fase 13 - Packaging Windows portable

- [ ] Buat konfigurasi PyInstaller.
- [ ] Pastikan template HTML ikut terbundle.
- [ ] Pastikan static asset ikut terbundle.
- [ ] Pastikan folder runtime tersedia.
- [ ] Buat `run.bat`.
- [ ] Pastikan browser lokal terbuka otomatis.
- [ ] Uji hasil build di Windows lain.

Definition of done:

- [ ] Folder hasil build bisa dipakai tanpa install Python.

### Fase 14 - Validasi use case nyata

- [ ] Minta 1 sample source nyata.
- [ ] Minta contoh output final yang dianggap benar.
- [ ] Catat kolom wajib dari sample.
- [ ] Catat lookup yang dibutuhkan.
- [ ] Catat conditional yang dibutuhkan.
- [ ] Catat format custom per sheet.
- [ ] Revisi YAML dan logic jika diperlukan.

Definition of done:

- [ ] 1 use case nyata lolos validasi user.

## 6. Checklist Rule Bisnis yang Akan Diisi Nanti

Bagian ini sengaja disiapkan sebagai placeholder agar saat sample nyata datang, kita tinggal isi tanpa mengubah struktur task plan.

### Source nyata pertama

- [ ] Nama use case:
- [ ] Format source: `.xlsx` / `.csv`
- [ ] Nama sheet source jika Excel:
- [ ] Daftar kolom wajib:
- [ ] Daftar kolom opsional:

### Master file

- [ ] Master 1:
- [ ] Key source:
- [ ] Key master:
- [ ] Kolom yang diambil:
- [ ] Join type:
- [ ] Master 2:
- [ ] Key source:
- [ ] Key master:
- [ ] Kolom yang diambil:
- [ ] Join type:

### Rule transformasi

- [ ] Filter utama:
- [ ] Lookup utama:
- [ ] Conditional utama:
- [ ] Formula utama:
- [ ] Grouping utama:
- [ ] Pivot utama:

### Output custom

- [ ] Nama sheet 1:
- [ ] Layout sheet 1:
- [ ] Nama sheet 2:
- [ ] Layout sheet 2:
- [ ] Header title:
- [ ] Penentuan periode:
- [ ] Format angka:
- [ ] Format tanggal:

## 7. Definition of Done MVP

- [ ] User bisa upload `.xlsx` dan `.csv`.
- [ ] User bisa memilih config `.yaml`.
- [ ] Sistem bisa load banyak master dari folder `masters/`.
- [ ] Sistem bisa menjalankan lookup, conditional, formula, grouping, dan pivot sesuai use case nyata.
- [ ] Sistem menghasilkan 1 file `.xlsx` multi-sheet.
- [ ] Output punya header dan styling dasar.
- [ ] UI menampilkan log proses yang jelas.
- [ ] Error tampil jelas dan tidak membingungkan.
- [ ] Hasil bisa didownload.
- [ ] Aplikasi bisa dibundle menjadi folder portable Windows.
- [ ] Hasil build bisa jalan tanpa install Python.
- [ ] Minimal 1 use case nyata lolos validasi user.

## 8. Skills AI yang Dibutuhkan

### Skill teknis

- [ ] Python modular project structure
- [ ] Flask routing, upload, template, download
- [ ] pandas untuk read, merge, groupby, pivot, transform
- [ ] openpyxl untuk writer dan styling Excel
- [ ] PyYAML untuk parsing dan validasi config
- [ ] PyInstaller untuk packaging Windows portable
- [ ] pytest untuk unit dan integration test
- [ ] Dasar validasi input dan keamanan rule evaluation

### Skill kerja

- [ ] Menjaga scope tetap di MVP
- [ ] Memecah kerja jadi modul kecil dan testable
- [ ] Menulis error message yang jelas
- [ ] Membaca traceback dan memperbaiki bug
- [ ] Menerjemahkan kebutuhan bisnis ke operasi DataFrame
- [ ] Menjaga kompatibilitas path Windows
- [ ] Menulis dokumentasi yang mudah dipahami developer junior

## 9. Urutan Eksekusi yang Direkomendasikan

- [ ] Setup environment
- [ ] Buat skeleton Flask dan UI dasar
- [ ] Buat config loader
- [ ] Buat source reader
- [ ] Buat master loader
- [ ] Buat transform engine dasar
- [ ] Buat formula/conditional engine dasar
- [ ] Buat output writer
- [ ] Tambahkan logging dan integrasi end-to-end
- [ ] Tambahkan testing
- [ ] Tambahkan packaging
- [ ] Validasi dengan sample nyata
