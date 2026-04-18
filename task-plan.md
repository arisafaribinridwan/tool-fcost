# Task Plan - Excel Automation Tool

Dokumen ini adalah checklist implementasi utama untuk MVP.
Fokusnya dibuat sederhana, jelas, dan bisa dipakai monitoring progress harian.
Dokumen ini mengikuti keputusan baru bahwa UI memakai `CustomTkinter`, sementara strategi kerja tetap mengutamakan development lintas OS dan build per OS target dengan `PyInstaller`.

Status sinkronisasi terakhir:

- Checklist diselaraskan dengan progres implementasi terbaru termasuk engine `Execute` real (lihat PR #9).
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

- [x] Window utama tampil dan aplikasi bisa dibuka lokal.

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
- [x] Normalisasi dan validasi path config agar tetap aman di Linux dan Windows.
- [x] Buat error message yang mudah dipahami.
- [x] Buat minimal 2 config contoh.

Definition of done:

- [x] Config valid bisa dibaca.
- [x] Config invalid menghasilkan error jelas.

### Fase 4 - Source reader

- [x] Implement reader `.xlsx`.
- [x] Implement reader `.csv`.
- [x] Validasi ekstensi file.
- [x] Validasi sheet source untuk Excel.
- [x] Validasi file kosong atau rusak.
- [x] Salin source ke folder `uploads/` bila memang dipakai sebagai jejak runtime.
- [x] Validasi kolom minimum jika dibutuhkan config.
- [x] Uji nama file/sheet dengan variasi huruf besar-kecil agar aman lintas OS.

Definition of done:

- [x] File source `.xlsx` dan `.csv` bisa dibaca ke DataFrame.

### Fase 5 - Master loader

- [x] Implement loader master `.xlsx`.
- [x] Implement loader master `.csv`.
- [x] Validasi file master ada.
- [x] Validasi path aman dan tidak path traversal.
- [x] Validasi key master ada.
- [x] Support banyak master file dalam satu resep.
- [x] Siapkan helper merge dasar.
- [x] Pastikan resolusi path master tidak bergantung slash atau case tertentu.

Definition of done:

- [x] Banyak master bisa dibaca dan siap dipakai transformasi.

### Fase 6 - Transform engine dasar

- [x] Implement filter data.
- [x] Implement pilih kolom output.
- [x] Implement rename kolom bila diperlukan.
- [x] Implement merge/mapping ala lookup.
- [x] Implement group by dan agregasi.
- [x] Implement pivot table.
- [x] Tambahkan warning untuk kolom opsional yang hilang.

Definition of done:

- [x] Transformasi dasar berjalan untuk config sederhana.

### Fase 7 - Formula dan conditional engine

- [x] Implement formula aritmatika sederhana.
- [x] Siapkan struktur untuk conditional rule.
- [ ] Siapkan struktur untuk lookup rule lanjutan.
- [x] Validasi rule agar tidak unsafe.
- [x] Buat pesan error formula/rule yang jelas.

Sub-tugas rule bisnis yang akan diisi nanti:

- [ ] Definisikan jenis lookup yang dibutuhkan sample nyata.
- [ ] Definisikan jenis conditional yang dibutuhkan sample nyata.
- [ ] Definisikan formula lanjutan yang dibutuhkan sample nyata.
- [ ] Definisikan prioritas urutan eksekusi rule.

Definition of done:

- [ ] Engine siap menampung rule bisnis nyata tanpa bongkar arsitektur dasar.

### Fase 8 - Output writer Excel

- [x] Tulis output ke multi-sheet.
- [x] Tambahkan header laporan 2-3 baris.
- [x] Ambil info periode dari kolom tanggal yang ditentukan config.
- [x] Terapkan warna header tabel.
- [x] Terapkan border.
- [x] Terapkan font.
- [x] Terapkan format angka.
- [x] Terapkan format tanggal.
- [x] Terapkan freeze pane.
- [x] Validasi nama sheet Excel.
- [x] Simpan file ke folder `outputs/`.
- [x] Pastikan penulisan file memakai path portable dan aman di Windows.

Definition of done:

- [x] File `.xlsx` hasil bisa dibuka dan tampil rapi secara dasar.

### Fase 9 - Logging dan progress

- [x] Buat logger proses per langkah.
- [x] Log awal sub-tugas.
- [x] Log akhir sub-tugas.
- [x] Log warning.
- [x] Log error.
- [x] Hubungkan log ke widget UI secara aman tanpa freeze.
- [x] Siapkan mekanisme progress dasar untuk proses yang berjalan agak lama.

Definition of done:

- [x] User bisa melihat progress proses utama dari desktop UI.

### Fase 10 - Integrasi end-to-end

- [x] Hubungkan pilih source + pilih config + execute.
- [x] Load source saat execute.
- [x] Load semua master saat execute.
- [x] Jalankan transformasi sesuai config.
- [x] Tulis output Excel.
- [x] Tampilkan status sukses/gagal.
- [x] Aktifkan tombol buka file atau buka folder hasil.
- [x] Verifikasi alur lokal di environment development utama.

Definition of done:

- [x] Alur dari pilih source sampai hasil output berjalan lokal.

### Fase 11 - Hardening dan error handling

- [x] Tangani file source tidak valid.
- [x] Tangani config invalid.
- [x] Tangani master file hilang.
- [x] Tangani sheet source tidak ditemukan.
- [x] Tangani kolom wajib hilang.
- [x] Tangani rule formula/conditional invalid.
- [x] Tangani nama sheet invalid.
- [x] Tangani file output gagal ditulis karena sedang dibuka.
- [x] Pastikan pesan error mudah dipahami user non-teknis.
- [x] Pastikan UI tidak crash diam-diam saat exception terjadi di proses background.

Definition of done:

- [x] Error umum tidak membuat aplikasi crash diam-diam.

### Fase 12 - Testing

- [ ] Buat fixture kecil untuk source.
- [ ] Buat fixture kecil untuk master.
- [ ] Buat fixture kecil untuk YAML.
- [x] Buat unit test config loader.
- [x] Buat unit test source reader.
- [x] Buat unit test master loader.
- [x] Buat unit test transform engine.
- [x] Buat unit test formula/rule engine.
- [x] Buat unit test output writer.
- [ ] Buat test UI minimal untuk helper logic yang bisa diuji tanpa full window interaktif.
- [x] Buat minimal 1 integration test.
- [x] Jalankan test rutin minimal di 1 environment development.
- [ ] Jika memungkinkan, ulangi test penting di Linux dan Windows.
- [x] Tambahkan test atau checklist untuk path handling dan case sensitivity.

Definition of done:

- [x] Happy path dan error path utama tercakup.

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

- [x] User bisa memilih `.xlsx` dan `.csv`.
- [x] User bisa memilih config `.yaml`.
- [x] Sistem bisa load banyak master dari folder `masters/`.
- [ ] Sistem bisa menjalankan lookup, conditional, formula, grouping, dan pivot sesuai use case nyata.
- [x] Sistem menghasilkan 1 file `.xlsx` multi-sheet.
- [x] Output punya header dan styling dasar.
- [x] Desktop UI menampilkan log proses yang jelas.
- [x] Error tampil jelas dan tidak membingungkan.
- [x] Hasil tersimpan dan mudah dibuka dari folder output.
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

- [x] Setup environment
- [x] Pastikan guardrail portability lintas OS
- [x] Buat skeleton `CustomTkinter` dan UI dasar
- [x] Buat config loader
- [x] Buat source reader
- [x] Buat master loader
- [x] Buat transform engine dasar
- [x] Buat formula/conditional engine dasar
- [x] Buat output writer
- [x] Tambahkan logging dan integrasi end-to-end
- [x] Tambahkan testing
- [ ] Jalankan validasi lintas OS seperlunya
- [ ] Tambahkan packaging per target OS
- [ ] Validasi dengan sample nyata
