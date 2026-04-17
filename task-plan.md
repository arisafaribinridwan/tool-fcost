# Task Plan - Excel Automation Tool

Dokumen ini adalah checklist implementasi utama untuk MVP.
Fokusnya dibuat sederhana, jelas, dan bisa dipakai monitoring progress harian.
Dokumen ini mengikuti keputusan baru bahwa UI memakai `CustomTkinter`, sementara strategi kerja tetap mengutamakan development lintas OS dan build per OS target dengan `PyInstaller`.

Status sinkronisasi terakhir:

- Checklist sudah diselaraskan dengan skeleton desktop `CustomTkinter` dan helper dasar yang saat ini ada di repo.
- Item yang dicentang berarti sudah terimplementasi atau sudah diverifikasi lewat test dasar.
- Item yang masih kosong berarti belum selesai, belum terhubung end-to-end, atau belum divalidasi lintas OS target runtime final.

## Cara Pakai

- Centang item yang sudah selesai.
- Jika ada perubahan scope, update `prd.md` dulu.
- Jika ada rule bisnis baru dari sample nyata, tambahkan di sub-tugas terkait.
- Detail lookup, conditional, dan formula lanjutan diisi per use case, tidak perlu dipaksa final dari awal.
- Anggap Windows sebagai acuan runtime final distribusi pertama, walau coding harian bisa dilakukan di Linux atau Windows.

## Prinsip Environment

- [x] Kode dijaga OS-agnostic sejak awal.
- [x] Gunakan `pathlib` atau `os.path`, jangan hardcode path Windows/Linux.
- [x] Logic aplikasi tidak bergantung pada shell tertentu.
- [x] Perbedaan line ending dan case sensitivity nama file ikut diperhatikan saat development.
- [x] UI dipilih berbasis Python desktop agar lebih sederhana untuk dev lintas OS dibanding web lokal.
- [ ] Build final `.exe`, `run.bat`, dan uji portable selalu dilakukan di Windows.
- [ ] Jika nanti butuh binary Linux atau macOS, build dilakukan lagi di OS target masing-masing.

## 1. Gate Awal

- [x] PRD sudah cukup jelas untuk mulai coding.
- [x] Scope MVP sudah dikunci.
- [x] Platform target distribusi pertama dikunci: Windows 10/11 64-bit.
- [x] Environment development boleh Linux atau Windows.
- [x] Format output dikunci: 1 file `.xlsx` multi-sheet.
- [x] Struktur folder runtime dikunci: `configs/`, `masters/`, `uploads/`, `outputs/`.
- [x] Use case awal dikunci: `1 source -> 1 output utama`.
- [x] Support source awal dikunci: `.xlsx` dan `.csv`.
- [x] Satu resep boleh memakai banyak master file.
- [x] Model live log dikunci: update progress internal per awal/akhir sub-tugas.
- [x] Diputuskan memakai `CustomTkinter`, bukan web UI.
- [x] Disepakati bahwa validasi final runtime distribusi pertama dilakukan di Windows.

## 2. Setup Development

- [x] Install Python 3.14.x 64-bit.
- [x] Install Git.
- [x] Install editor kerja.
- [x] Buat virtual environment `.venv`.
- [x] Upgrade `pip`.
- [x] Install dependency runtime.
- [x] Install dependency testing/linting.
- [x] Buat `requirements.txt`.
- [x] Buat `.gitignore`.
- [x] Buat `README.md` setup singkat.
- [x] Dokumentasikan langkah setup Linux dan Windows secara terpisah jika ada beda command.
- [x] Pastikan `.gitignore` dan editor config aman untuk line ending lintas OS.

## 3. Install Manual yang Diperlukan

### Software

- [x] Python 3.14.x 64-bit
- [x] Git
- [x] VS Code atau editor lain
- [ ] Mesin Windows 10/11 untuk build final dan validasi portable
- [ ] Jika ingin build Linux native, siapkan environment Linux terpisah

### Library Python

- [x] `customtkinter`
- [x] `pandas`
- [x] `openpyxl`
- [x] `PyYAML`
- [x] `pyinstaller`
- [x] `pytest`
- [x] `ruff`
- [x] `python-dotenv` (opsional)

### Perintah install manual

```bash
python3 -m venv .venv
python3 -m pip install --upgrade pip
pip install customtkinter pandas openpyxl PyYAML pyinstaller pytest ruff python-dotenv
```

PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

CMD:

```bat
.venv\Scripts\activate.bat
```

Linux/macOS:

```bash
source .venv/bin/activate
```

## 4. Struktur Proyek

- [x] Buat folder `app/`.
- [x] Buat folder `app/ui/`.
- [x] Buat folder `app/ui/components/` jika diperlukan.
- [x] Buat folder `app/services/`.
- [x] Buat folder `app/utils/`.
- [x] Buat folder `configs/`.
- [x] Buat folder `masters/`.
- [x] Buat folder `uploads/`.
- [x] Buat folder `outputs/`.
- [x] Buat folder `tests/`.
- [x] Buat file entrypoint desktop, misalnya `run.py` atau `main.py`.
- [ ] Siapkan folder atau file config khusus packaging per OS bila diperlukan.
- [x] Siapkan helper path runtime agar source mode dan bundle mode konsisten.

## 5. Breakdown Fase Implementasi

### Fase 1 - Skeleton aplikasi

- [x] Buat app `CustomTkinter` dasar.
- [x] Buat window utama.
- [x] Buat layout dasar panel input, log, dan status.
- [ ] Pastikan app bisa dijalankan lokal di Linux dan Windows.
- [x] Pastikan bootstrap path dan lokasi file runtime tidak bergantung separator OS.

Definition of done:

- [ ] Window utama tampil dan aplikasi bisa dibuka lokal.

### Fase 2 - Desktop UI dasar

- [x] Buat tombol pilih file source.
- [x] Buat dropdown/list config YAML.
- [x] Buat tombol `Execute`.
- [x] Buat area log proses.
- [x] Buat area hasil dan tombol buka folder output.
- [x] Tambahkan validasi input sederhana.
- [x] Pastikan pemilihan file dan pembukaan folder memakai mekanisme yang aman lintas OS.

Definition of done:

- [x] User bisa melihat alur dasar dari desktop UI walau backend belum lengkap.

### Fase 3 - Config loader dan schema dasar

- [x] Baca semua file `.yaml` dari folder `configs/`.
- [x] Parse YAML.
- [x] Validasi field root minimum.
- [x] Validasi struktur `masters`.
- [x] Validasi struktur `outputs`.
- [x] Validasi struktur `styling`.
- [ ] Normalisasi dan validasi path config agar tetap aman di Linux dan Windows.
- [x] Buat error message yang mudah dipahami.
- [x] Buat minimal 2 config contoh.

Definition of done:

- [x] Config valid bisa dibaca.
- [x] Config invalid menghasilkan error jelas.

### Fase 4 - Source reader

- [ ] Implement reader `.xlsx`.
- [ ] Implement reader `.csv`.
- [x] Validasi ekstensi file.
- [ ] Validasi sheet source untuk Excel.
- [ ] Validasi file kosong atau rusak.
- [x] Salin source ke folder `uploads/` bila memang dipakai sebagai jejak runtime.
- [ ] Validasi kolom minimum jika dibutuhkan config.
- [ ] Uji nama file/sheet dengan variasi huruf besar-kecil agar aman lintas OS.

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
- [ ] Pastikan resolusi path master tidak bergantung slash atau case tertentu.

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
- [ ] Pastikan penulisan file memakai path portable dan aman di Windows.

Definition of done:

- [ ] File `.xlsx` hasil bisa dibuka dan tampil rapi secara dasar.

### Fase 9 - Logging dan progress

- [x] Buat logger proses per langkah.
- [x] Log awal sub-tugas.
- [ ] Log akhir sub-tugas.
- [ ] Log warning.
- [ ] Log error.
- [x] Hubungkan log ke widget UI secara aman tanpa freeze.
- [ ] Siapkan mekanisme progress dasar untuk proses yang berjalan agak lama.

Definition of done:

- [x] User bisa melihat progress proses utama dari desktop UI.

### Fase 10 - Integrasi end-to-end

- [x] Hubungkan pilih source + pilih config + execute.
- [ ] Load source saat execute.
- [ ] Load semua master saat execute.
- [ ] Jalankan transformasi sesuai config.
- [ ] Tulis output Excel.
- [x] Tampilkan status sukses/gagal.
- [x] Aktifkan tombol buka file atau buka folder hasil.
- [ ] Verifikasi alur lokal di environment development utama.

Definition of done:

- [ ] Alur dari pilih source sampai hasil output berjalan lokal.

### Fase 11 - Hardening dan error handling

- [x] Tangani file source tidak valid.
- [x] Tangani config invalid.
- [ ] Tangani master file hilang.
- [ ] Tangani sheet source tidak ditemukan.
- [ ] Tangani kolom wajib hilang.
- [ ] Tangani rule formula/conditional invalid.
- [ ] Tangani nama sheet invalid.
- [ ] Tangani file output gagal ditulis karena sedang dibuka.
- [x] Pastikan pesan error mudah dipahami user non-teknis.
- [ ] Pastikan UI tidak crash diam-diam saat exception terjadi di proses background.

Definition of done:

- [ ] Error umum tidak membuat aplikasi crash diam-diam.

### Fase 12 - Testing

- [ ] Buat fixture kecil untuk source.
- [ ] Buat fixture kecil untuk master.
- [ ] Buat fixture kecil untuk YAML.
- [x] Buat unit test config loader.
- [ ] Buat unit test source reader.
- [ ] Buat unit test master loader.
- [ ] Buat unit test transform engine.
- [ ] Buat unit test formula/rule engine.
- [ ] Buat unit test output writer.
- [ ] Buat test UI minimal untuk helper logic yang bisa diuji tanpa full window interaktif.
- [ ] Buat minimal 1 integration test.
- [x] Jalankan test rutin minimal di 1 environment development.
- [ ] Jika memungkinkan, ulangi test penting di Linux dan Windows.
- [x] Tambahkan test atau checklist untuk path handling dan case sensitivity.

Definition of done:

- [ ] Happy path dan error path utama tercakup.

### Fase 13 - Packaging portable

- [ ] Buat konfigurasi `PyInstaller` untuk Windows.
- [ ] Pastikan asset non-code ikut terbundle jika ada.
- [ ] Pastikan folder runtime tersedia atau dibuat otomatis saat first run.
- [ ] Buat `run.bat`.
- [ ] Uji jalan dari source mode dan bundle mode.
- [ ] Lakukan build final `PyInstaller` Windows di Windows, bukan Linux.
- [ ] Uji `run.bat` dan `ExcelAutoTool.exe` di Windows target.
- [ ] Uji hasil build di Windows lain.
- [ ] Jika ingin distribusi Linux native, buat file spec atau langkah build Linux terpisah.

Definition of done:

- [ ] Folder hasil build bisa dipakai tanpa install Python.
- [ ] Build final Windows tervalidasi sebagai target distribusi utama.

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

- [ ] User bisa memilih `.xlsx` dan `.csv`.
- [ ] User bisa memilih config `.yaml`.
- [ ] Sistem bisa load banyak master dari folder `masters/`.
- [ ] Sistem bisa menjalankan lookup, conditional, formula, grouping, dan pivot sesuai use case nyata.
- [ ] Sistem menghasilkan 1 file `.xlsx` multi-sheet.
- [ ] Output punya header dan styling dasar.
- [ ] Desktop UI menampilkan log proses yang jelas.
- [ ] Error tampil jelas dan tidak membingungkan.
- [ ] Hasil tersimpan dan mudah dibuka dari folder output.
- [ ] Aplikasi bisa dibundle menjadi folder portable Windows.
- [ ] Hasil build bisa jalan tanpa install Python.
- [ ] Validasi final folder runtime dan eksekusi lolos di Windows.
- [ ] Minimal 1 use case nyata lolos validasi user.

## 8. Skills AI yang Dibutuhkan

### Skill teknis

- [ ] Python modular project structure
- [ ] `CustomTkinter` layout, event handling, file dialog, dan state update
- [ ] `pandas` untuk read, merge, groupby, pivot, transform
- [ ] `openpyxl` untuk writer dan styling Excel
- [ ] `PyYAML` untuk parsing dan validasi config
- [ ] `PyInstaller` untuk packaging portable per OS target
- [ ] `pytest` untuk unit dan integration test
- [ ] Dasar validasi input dan keamanan rule evaluation

### Skill kerja

- [ ] Menjaga scope tetap di MVP
- [ ] Memecah kerja jadi modul kecil dan testable
- [ ] Menulis error message yang jelas
- [ ] Membaca traceback dan memperbaiki bug
- [ ] Menerjemahkan kebutuhan bisnis ke operasi DataFrame
- [ ] Menjaga kompatibilitas path lintas OS
- [ ] Menulis dokumentasi yang mudah dipahami developer junior

## 9. Urutan Eksekusi yang Direkomendasikan

- [ ] Setup environment
- [ ] Pastikan guardrail portability lintas OS
- [ ] Buat skeleton `CustomTkinter` dan UI dasar
- [ ] Buat config loader
- [ ] Buat source reader
- [ ] Buat master loader
- [ ] Buat transform engine dasar
- [ ] Buat formula/conditional engine dasar
- [ ] Buat output writer
- [ ] Tambahkan logging dan integrasi end-to-end
- [ ] Tambahkan testing
- [ ] Jalankan validasi lintas OS seperlunya
- [ ] Tambahkan packaging per target OS
- [ ] Validasi dengan sample nyata
