# PRD — Excel Automation Tool
**Versi:** 2.0 (Final)
**Status:** Siap dikoding
**Platform:** Windows (portable, tanpa install)
**Stack:** Python + Flask + pandas + openpyxl + PyInstaller

---

## 1. Latar Belakang & Masalah

Setiap periode ada pekerjaan rutin: ambil file Excel sumber → lakukan serangkaian transformasi (filter, pivot, VLOOKUP, kalkulasi, styling) → hasilkan banyak sheet atau file output. Proses ini repetitif, rawan kesalahan manual, dan memakan waktu. Diperlukan satu tools yang menjalankan semua itu cukup dengan satu tombol.

---

## 2. Pengguna & Konteks

| Atribut | Detail |
|---|---|
| Pengguna | 1 orang (personal use) |
| Sistem operasi | Windows 10 / 11 (64-bit) |
| Distribusi | Folder portable — tanpa install, tanpa admin permission |
| Koneksi internet | Tidak diperlukan setelah folder dikopi |

---

## 3. Alur Kerja Utama

```
Upload file sumber (.xlsx)
        ↓
Muat data master otomatis dari folder masters/
        ↓
Pilih config resep (.yaml)
        ↓
Klik Execute
        ↓
Download file output (.xlsx)
```

> **Catatan:** Data master (file statis untuk VLOOKUP) dimuat otomatis dari folder `masters/` — tidak perlu diupload setiap kali. Cukup letakkan file master di sana sekali, tools akan selalu merujuk ke situ.

---

## 4. Distribusi & Cara Pakai di PC Baru

Tools didistribusikan sebagai **satu folder portable**. Tidak perlu install Python, tidak perlu install library, tidak perlu admin permission. Cukup copy folder ke PC manapun dan klik `run.bat`.

### Langkah pakai di PC baru

1. **Copy folder `ExcelAutoTool/`** ke PC tujuan (via flashdisk, shared drive, email, dll)
2. **Klik dua kali `run.bat`** — otomatis buka browser dan tools siap dipakai
3. **Letakkan data master** di folder `masters/` — cukup sekali, tidak perlu diulang setiap sesi
4. **Upload file sumber, pilih resep, klik Execute** — hasil langsung bisa didownload

### Detail teknis

File `run.bat` menjalankan `ExcelAutoTool.exe` yang sudah dibundle dengan PyInstaller. Di dalamnya sudah include Python runtime, Flask, pandas, openpyxl, PyYAML, dan semua dependency — tidak ada yang perlu diinstall di PC tujuan.

- Ukuran file distribusi: **~80–120 MB** (bundled, wajar untuk zero-install)
- Tidak membutuhkan koneksi internet setelah dikopi

---

## 5. Struktur Folder Distribusi

Folder ini yang dikopi ke PC lain:

```
ExcelAutoTool/
├── ExcelAutoTool.exe     ← bundled app (Python + semua library)
├── run.bat               ← klik ini untuk menjalankan
├── masters/              ← letakkan file data master di sini
├── configs/              ← file resep .yaml
├── uploads/              ← file sumber yang diupload (otomatis)
└── outputs/              ← hasil output .xlsx
```

---

## 6. Scope MVP

### Masuk scope (wajib ada)

- Upload file sumber `.xlsx` / `.csv`
- Referensi data master dari folder statis (`masters/`)
- Config resep via file YAML (bisa diedit pakai Notepad)
- Filter & grouping data
- Pivot / rekapitulasi
- VLOOKUP / mapping ke data master
- Kalkulasi rumus kustom
- Output multi-sheet dalam 1 file
- Header teks (judul + info periode)
- Styling output: warna header, border, format angka/tanggal
- Web UI sederhana (drag-drop upload + tombol execute + live log)
- Log eksekusi & pesan error yang jelas
- Portable `.exe` Windows (tanpa install apapun)

### Di luar scope — Fase 2

- Multi-file sumber (merge sebelum diproses)
- Visual config builder (drag-drop tanpa edit YAML)
- Logo / gambar di header output
- Output multi-file terpisah
- Mac / Linux support
- Deploy ke cloud / server
- CLI mode (deprioritized, sudah ter-cover oleh web UI portable)

---

## 7. Config Resep (YAML)

Semua aturan transformasi disimpan di file `.yaml` yang bisa diedit dengan text editor biasa (Notepad, VS Code, dll). Sekali dibuat, bisa dipakai berulang tanpa mengubah apapun.

### Contoh struktur config

```yaml
name: "Laporan Penjualan Bulanan"
source_sheet: "Sheet1"

header:
  title: "Laporan Penjualan"
  period_from_column: "tanggal"   # ambil otomatis dari min/max kolom ini

masters:
  - file: "masters/produk.xlsx"
    key: "kode_produk"
    columns: ["nama_produk", "kategori"]

outputs:
  - sheet_name: "Per Kategori"
    group_by: "kategori"
    columns: ["kategori", "total_qty", "total_nilai"]
    formulas:
      total_nilai: "qty * harga"

  - sheet_name: "Summary"
    pivot:
      index: "kategori"
      values: "total_nilai"
      aggfunc: "sum"

styling:
  header_color: "4472C4"
  font: "Arial"
  number_format: "#,##0"
  date_format: "DD/MM/YYYY"
  freeze_pane: "A2"
```

> Format ini akan disesuaikan lebih lanjut ketika contoh kasus nyata dari PC kerja sudah tersedia.

---

## 8. Arsitektur Teknis

| Layer | Teknologi |
|---|---|
| Web UI | HTML + JavaScript vanilla |
| Backend | Python 3.11, Flask |
| Transformasi data | pandas |
| Baca/tulis Excel | openpyxl |
| Config | YAML (PyYAML) |
| Packaging | PyInstaller (onedir mode) |

---

## 9. Constraint Teknis

| Constraint | Detail |
|---|---|
| Sistem operasi | Windows 10 / 11 (64-bit) |
| Ukuran data | ~20 ribu baris — aman in-memory dengan pandas |
| Data master | File `.xlsx` / `.csv` statis di folder `masters/`, dimuat sekali saat eksekusi |
| Header output | 2–3 baris teks: judul laporan + info periode (diambil otomatis dari data) |
| Kolom berubah | Kolom opsional tidak menyebabkan crash — cukup warning di log |
| Koneksi internet | Tidak diperlukan sama sekali setelah folder dikopi |
| Admin permission | Tidak diperlukan untuk menjalankan |

---

## 10. Rencana Pengembangan

### Fase 1 — MVP (sekarang)

Semua fitur dalam scope MVP. Output akhir: folder portable yang siap dikopi ke PC Windows manapun tanpa install apapun. Akan divalidasi menggunakan contoh kasus nyata dari PC kerja.

### Fase 2 — Setelah validasi

- Output multi-file terpisah
- Visual config builder (drag-drop tanpa edit YAML)
- Merge multi-file sumber
- Logo / gambar di header output
- Mekanisme update tools

---

## 11. Pertanyaan Terbuka

- [ ] Contoh kasus nyata (file sumber + transformasi yang diinginkan) — akan dipakai sebagai test case pertama MVP. Tersedia setelah akses ke PC kerja.

---

*Dokumen ini adalah PRD final v2.0. Siap dijadikan landasan coding.*


dari @prd.md ini. tolong buatkan checklist task plan komprehensif untuk bisa dijadika sumber kebenaran untuk coding junior developer atau model lainnya yang lebih murah.
- buatkan daftar library atau instalasi yang diperlukan agar saya bisa lakukan instalasi manual tanpa ai (lebih hemat)
- buatkan daftar skills ai yang dibutuhkan untuk projek ini
- jika ada yang belum jelas, tanyakan ke saya sebelum koding. buatkan hasilnya di file task-plan.md
