# Dokumentasi Teknis Lengkap — Excel Automation Tool

## 1) Tentang apa tool ini?

**Excel Automation Tool** adalah aplikasi desktop untuk mengotomasi proses olah data Excel/CSV berbasis konfigurasi YAML, lalu menghasilkan workbook output `.xlsx` siap pakai.

Fokus utamanya:
- mengurangi pekerjaan manual copy/paste/filter/rumus,
- membuat proses transformasi data konsisten,
- dan memastikan hasil bisa direproduksi dari config yang sama.

Tool dijalankan via UI desktop (`CustomTkinter`) dan engine pemrosesan data (`pandas` + `openpyxl`).

---

## 2) Arsitektur teknis singkat

### Entry point & runtime
- `run.py` menjalankan app dan memastikan folder runtime tersedia.
- Folder runtime otomatis dibuat: `configs/`, `masters/`, `uploads/`, `outputs/`.
- Mode runtime mendukung:
  - **source mode** (jalan dari source code),
  - **bundle mode** (hasil build PyInstaller).

### Layer utama
- **UI layer**: pemilihan source, pemilihan `Pekerjaan` berbasis registry job profile, eksekusi pipeline, log proses, buka folder output.
- **Service layer**:
  1. validasi source,
  2. validasi+load config YAML,
  3. load data,
  4. master lookup / recipe step,
  5. transform,
  6. build output sheet,
  7. tulis workbook `.xlsx`.
- **Utility layer**: safety path, dialog file native per OS, buka file manager.

---

## 3) Fitur utama yang tersedia

## A. Input & validasi data
- Source file yang didukung: **`.xlsx`** dan **`.csv`**.
- Validasi source:
  - file harus ada,
  - harus file (bukan folder),
  - ekstensi valid,
  - tidak kosong.
- Pembacaan Excel mendukung pencocokan nama sheet **case-insensitive**.
- Error pembacaan file rusak ditangani sebagai pesan domain yang jelas.

## B. Konfigurasi YAML (2 mode)
Tool mendukung dua gaya konfigurasi:

1. **Mode config klasik** (`name`, `source_sheet`, `masters`, `transforms`, `outputs`)  
2. **Mode step recipe** (`datasets`, `steps`, `outputs`) untuk flow yang lebih kompleks.

Validator YAML memeriksa struktur, tipe data, field wajib, kombinasi field yang valid, serta nilai enum yang didukung.

## C. Keamanan path (hardening)
- Path runtime divalidasi sebagai path **relatif** di dalam boundary folder yang diizinkan.
- Path master harus berada di bawah folder `masters/`.
- Path config harus berada di bawah folder `configs/`.
- Path output runtime di-resolve ulang agar tetap berada di boundary yang aman.
- Menolak absolute path, drive path Windows, serta `.` / `..` traversal.
- Mendukung normalisasi separator (`\\` → `/`) dan resolusi nama file case-insensitive.

## D. Master lookup (enrichment)
Tersedia 3 strategi:

1. **`lookup`**
   - join source ke master berbasis key,
   - dukung `source_key`/`master_key`, `rename_columns`, `key_aliases`, `key_normalizer`.

2. **`ordered_rules`**
   - rule dieksekusi berurutan dari atas ke bawah,
   - cocok untuk mapping berdasarkan kombinasi kondisi/teks.

3. **`lookup_rules`**
   - rule matching fleksibel (`equals`, `contains`, `regex`) dengan opsi normalisasi,
   - untuk sheet `symptom`, rule tervalidasi sebagai rule table berbasis `priority`, `part_name`, `match_type`, `pattern`, `symptom`, `notes`,
   - dukung `blank_as_wildcard`, wildcard custom, `first_match_wins`, dan semantik regex Python `search`.

## D1. Registry `Pekerjaan`
- Selector UI utama kini memakai registry `configs/job_profiles.yaml`.
- Setiap record job minimal berisi `id`, `label`, `config_file`, dan `enabled`.
- Loader job profile memvalidasi registry, memeriksa config target, dan mengekstrak dependensi master dari config/recipe.
- Jika config job hilang atau invalid, item job tetap dapat terdeteksi tetapi ditandai invalid dan tidak bisa dieksekusi.

## E. Transform data (mode klasik)
Transform yang didukung:
- `ensure_optional_columns` (tambah kolom kosong/default jika belum ada),
- `filter_rows` (kondisi equals/not/in/gt/gte/lt/lte/is_blank/dll),
- `formula` (add/subtract/multiply/divide + validasi numerik + proteksi divide-by-zero),
- `conditional` (if/elif/else berbasis rule).

## F. Recipe step engine (mode lanjutan)
Step yang didukung:
- `extract_sheet` (deteksi sheet + deteksi header dinamis),
- `derive_column` (ekspresi turunan),
- `update_columns` (update berbasis kondisi),
- `lookup_exact` / `lookup_exact_replace`,
- `lookup_rules`,
- `map_ranges`,
- `duplicate_group_rewrite` (penanganan duplikasi berbasis winner rules).

Ekspresi recipe mencakup operator seperti `substring`, `add`, `divide`, `ceil`, `date_diff_days`, dan `case`.

## G. Output workbook
- Multi-sheet output.
- Tipe output yang didukung:
  - `columns` (select kolom),
  - `pivot`,
  - `group_by` + `aggregations` (`sum`, `mean`, `min`, `max`, `count`, `first`, `last`).
- Styling output:
  - warna header,
  - font,
  - format tanggal/angka,
  - freeze pane,
  - auto width kolom.
- Header report otomatis: judul, periode, timestamp pembuatan.

## H. Operasional & audit trail
- Source yang diproses disalin ke `uploads/` dengan timestamp.
- Nama output otomatis aman + timestamp (`report_YYYYMMDD_HHMMSS.xlsx`).
- Log proses real-time di UI.
- Tombol buka folder output langsung dari aplikasi.

## I. Cross-platform & packaging
- Development: Linux/Windows.
- Packaging portable tersedia untuk Linux dan Windows (PyInstaller).
- Linux support native file picker (`kdialog` / `zenity`) dengan fallback.

## J. Quality assurance
- Unit/integration tests mencakup:
  - validasi source/config,
  - validasi registry `job_profiles`,
  - pipeline end-to-end,
  - hardening path runtime,
  - symptom rule table + regex lookup,
  - lookup & transform,
  - recipe monthly report,
  - output pivot/group_by.

---

## 4) Alur eksekusi end-to-end

1. User pilih source (`.xlsx`/`.csv`) di UI.  
2. App memvalidasi source.  
3. App memuat daftar `Pekerjaan` dari registry `configs/job_profiles.yaml` dan memvalidasi config target.  
4. User memilih `Pekerjaan` lalu tekan **Execute**.  
5. Engine:
   - validasi config,
   - salin source ke `uploads/`,
   - jalankan mode klasik atau mode recipe,
   - build output sheets,
   - tulis workbook `.xlsx` ke `outputs/`.
6. UI menampilkan status sukses/gagal + log detail.

---

## 5) Contoh pekerjaan otomatis lain yang bisa dilakukan tool ini

Di bawah ini contoh use case tambahan (selain contoh yang sudah ada di repo):

### 1. Rekap penjualan harian per kategori dan cabang
- Input: transaksi harian CSV.
- Otomasi:
  - filter tanggal aktif,
  - hitung `total = qty * harga`,
  - group by `cabang, kategori`,
  - hasilkan sheet `Detail` + `Summary`.

### 2. Klasifikasi tiket service ke action otomatis
- Input: data tiket + komentar teknisi.
- Otomasi:
  - `lookup_rules` berbasis kombinasi `part_name` + `repair_comment`,
  - output kolom `action` terstandar.
- Cocok untuk normalisasi data operasional sebelum dashboard.

### 3. Normalisasi nama cabang/region
- Input: data dari banyak sistem dengan kode cabang berbeda.
- Otomasi:
  - `lookup_exact_replace` dari master `init -> branch`,
  - jika tidak match bisa `keep_original`.

### 4. Skoring prioritas tiket berdasarkan SLA
- Input: tanggal beli vs tanggal gangguan.
- Otomasi (recipe):
  - hitung selisih hari (`date_diff_days`),
  - ubah ke bucket via `map_ranges` (mis. `<1 bulan`, `1-3 bulan`, dst),
  - hasilkan kolom prioritas/peringkat.

### 5. Konsolidasi multi-sheet bulanan (GQS/SASS-like)
- Input: workbook dengan banyak sheet dan header tidak selalu di baris sama.
- Otomasi:
  - `extract_sheet` dengan selector nama sheet,
  - auto-locate header via required columns,
  - append ke dataset kanonik,
  - final output satu format standar.

### 6. Deteksi dan resolusi duplikasi klaim
- Input: data klaim dengan notification sama berulang.
- Otomasi:
  - `duplicate_group_rewrite` memilih winner row,
  - agregasi biaya ke winner,
  - loser row di-set nol/flag sesuai aturan.

### 7. Pembuatan laporan keuangan operasional mingguan
- Input: transaksi biaya labor, transport, sparepart.
- Otomasi:
  - enrichment dari master part/factory,
  - hitung total biaya otomatis,
  - output pivot per kategori defect/action.

### 8. Data preparation sebelum upload ke BI
- Input: raw export ERP/CRM.
- Otomasi:
  - standardisasi kolom wajib,
  - filter data invalid,
  - generate sheet output khusus yang sudah clean.

---

## 6) Batasan penting saat ini

- Source hanya `.xlsx` / `.csv`.
- Master file hanya `.xlsx` / `.csv` dan wajib di bawah `masters/`.
- Rule dan schema config harus mengikuti validator; field di luar schema akan dianggap invalid pada konteks tertentu.
- Output selalu `.xlsx`.

---

## 7) Ringkasan nilai bisnis

Tool ini cocok untuk tim operasional/analitik yang rutin mengolah data Excel dengan pola berulang. Dengan pendekatan **config-driven**, perubahan proses cukup dilakukan di YAML tanpa mengubah kode utama, sehingga proses lebih cepat, konsisten, dan mudah diaudit.
