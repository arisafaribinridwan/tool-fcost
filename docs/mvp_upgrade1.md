# MVP Upgrade 1 - Interaktif, Secure, dan UI/UX Lebih Baik

Dokumen ini berisi usulan fitur MVP tambahan paling bernilai untuk membuat tool lebih baik dipakai harian, lebih aman, dan lebih nyaman untuk user non-teknis.

## Tujuan Upgrade

Upgrade ini fokus pada 4 hal:

1. Mengurangi trial-error user sebelum klik `Execute`
2. Membuat proses lebih interaktif dan bisa dipahami
3. Menurunkan risiko keamanan dan kesalahan operasional
4. Meningkatkan kenyamanan UI/UX tanpa membuat arsitektur terlalu berat

## Prinsip Prioritas

Agar tetap MVP-minded, urutan prioritas dibuat seperti ini:

- **P1 (wajib dulu):** fitur yang langsung mengurangi error user dan meningkatkan rasa aman
- **P2 (sangat disarankan):** fitur yang meningkatkan pengalaman dan observabilitas
- **P3 (nice-to-have):** polish yang meningkatkan perceived quality

---

## P1 - Fitur Wajib Ditambahkan Dulu

### 1) Preflight Check Interaktif (sebelum Execute)

#### Problem
Saat ini user baru tahu ada masalah setelah menjalankan pipeline. Ini membuat trial-error, khususnya jika config/master tidak sinkron.

#### Solusi
Tambahkan tombol **`Preflight Check`** di UI untuk validasi semua input sebelum eksekusi.

#### Apa yang dicek
- Source file ada, extension valid, bisa dibaca
- Config YAML valid
- Semua master yang direferensikan config tersedia
- Kolom wajib source/master ditemukan
- Konflik nama sheet output (jika ada)
- Potensi output overwrite

#### Output ke user
- Ringkasan status: `Ready`, `Warning`, `Blocked`
- Daftar masalah dengan level:
  - `ERROR` (harus diperbaiki)
  - `WARNING` (boleh lanjut, ada risiko)
  - `INFO`

#### Dampak
- Mengurangi error runtime
- Meningkatkan kepercayaan user sebelum eksekusi

---

### 2) Dry Run / Preview Hasil Ringkas

#### Problem
User sering butuh konfirmasi bahwa resep/config yang dipilih benar sebelum menulis file output final.

#### Solusi
Tambahkan mode **`Dry Run`** (checkbox atau tombol).

#### Perilaku
- Pipeline dijalankan sampai tahap transformasi
- Tidak menulis file final ke `outputs/` (atau tulis ke file preview sementara)
- Tampilkan preview ringkas:
  - jumlah baris input vs output
  - daftar sheet yang akan dibuat
  - contoh 10 baris pertama per sheet utama

#### Dampak
- Mencegah output salah format
- Menghemat waktu user

---

### 3) Keamanan Path dan File Boundary Lebih Ketat

#### Problem
Tool berbasis file path rentan salah akses path (mis. path traversal dari config atau symlink edge case).

#### Solusi
Perketat boundary akses file di semua titik I/O.

#### Aturan minimum
- Semua path master/config/source harus resolve di root runtime yang diizinkan
- Tolak path traversal (`..`), path absolut yang keluar root, dan symlink berbahaya
- Validasi ekstensi secara eksplisit
- Jika invalid: tampilkan error yang jelas dan blokir eksekusi

#### Dampak
- Mengurangi risiko akses file tidak semestinya
- Menambah trust untuk penggunaan rutin

---

### 4) Log Sanitization (Masking Data Sensitif)

#### Problem
Log bisa berisi path penuh user atau nilai sensitif dari kolom tertentu.

#### Solusi
Tambahkan sanitasi log sebelum ditampilkan/disimpan.

#### Aturan dasar
- Mask user-home path yang terlalu detail bila tidak perlu
- Mask nilai kolom sensitif (contoh: NIK, nomor rekening, email) jika muncul di error/log
- Hindari dump dataframe mentah ke log

#### Dampak
- Lebih aman saat screenshot log dibagikan
- Mengurangi kebocoran data tidak sengaja

---

### 5) Guardrail Resource: Size Limit + Timeout

#### Problem
File sangat besar atau data rusak dapat membuat UI terasa hang dan user tidak tahu apa yang terjadi.

#### Solusi
Tambahkan batas dan proteksi:
- batas ukuran source file (mis. default 50-100 MB, configurable)
- batas jumlah baris untuk mode interaktif
- timeout untuk tahap baca/transform tertentu

Jika terlewati:
- tampilkan warning/blocked dengan instruksi jelas

#### Dampak
- Aplikasi lebih stabil
- Ekspektasi user lebih terkelola

---

## P2 - Sangat Disarankan

### 6) Progress Bar + Step Indicator

#### Solusi
Tambahkan indikator langkah proses:
1. Load source
2. Load config
3. Load masters
4. Transform
5. Write output

Masing-masing menampilkan status `running/success/failed`.

#### Dampak
- User memahami posisi proses
- Mengurangi persepsi aplikasi macet

---

### 7) Error Message yang Actionable

#### Solusi
Standarisasi format error:
- **Apa masalahnya**
- **Dampaknya**
- **Langkah perbaikan**

Contoh:
- `Kolom wajib 'tanggal' tidak ditemukan pada source.`
- `Perbaikan: cek header source atau update mapping kolom di config YAML.`

#### Dampak
- Mengurangi beban support
- User lebih mandiri

---

### 8) Recent Files / Last Session Restore

#### Solusi
Simpan preferensi ringan:
- source terakhir
- config terakhir
- ukuran/posisi window

Saat startup, tampilkan opsi `Use last session`.

#### Dampak
- Penggunaan harian lebih cepat
- UX terasa lebih profesional

---

### 9) Konfirmasi Sebelum Overwrite Output

#### Solusi
Jika nama output sudah ada, tampilkan pilihan:
- `Replace`
- `Keep both (auto suffix)`
- `Cancel`

#### Dampak
- Menghindari kehilangan output lama

---

## P3 - Nice to Have (Polish)

### 10) Panel "Job Summary"

Menampilkan ringkasan setelah run:
- source/config yang dipakai
- durasi proses
- jumlah sheet
- jumlah warning/error
- lokasi output + tombol copy path

### 11) Drag-and-Drop Source File

Untuk mempercepat input source tanpa klik dialog.

### 12) Empty State dan Hint yang Lebih Ramah

Contoh:
- Saat belum ada config valid, tampilkan call-to-action jelas.
- Saat preflight gagal, tombol execute tetap disable + alasan singkat.

---

## Rekomendasi Implementasi Bertahap (2 Sprint)

## Sprint 1 (fokus safety + correctness)

Target:
- Preflight Check
- Dry Run
- Path boundary hardening
- Overwrite confirmation
- Error message standard

Exit criteria:
- User bisa tahu kondisi input tanpa mengeksekusi penuh
- Error mayor terdeteksi di preflight
- Tidak ada overwrite tanpa konfirmasi

## Sprint 2 (fokus UX + operasional)

Target:
- Progress step indicator
- Log sanitization
- Resource guardrail (size/timeout)
- Last session restore
- Job summary panel

Exit criteria:
- UX lebih interaktif
- Risiko data leakage via log menurun
- Proses panjang lebih transparan

---

## Dampak Teknis ke Arsitektur Saat Ini

Perubahan tetap bisa mengikuti arsitektur modular yang sudah ada:

- `app/services/`
  - tambah service `preflight_service.py`
  - tambah mode `dry_run` pada orchestrator pipeline
- `app/ui/main_window.py`
  - tombol `Preflight Check`
  - toggle `Dry Run`
  - panel status langkah/progress
- `app/utils/`
  - helper sanitasi log
  - helper guardrail file/path

Testing yang perlu ditambah:
- unit test preflight rules
- unit test overwrite decision
- unit test log masking
- integration test dry run vs real run

---

## Checklist MVP Upgrade 1 (Praktis)

- [ ] Tombol `Preflight Check` tersedia dan berjalan
- [ ] Mode `Dry Run` tersedia
- [ ] Preflight menampilkan severity (`ERROR/WARNING/INFO`)
- [ ] Path traversal dan akses path di luar boundary diblokir
- [ ] Overwrite output meminta konfirmasi
- [ ] Error message menggunakan format actionable
- [ ] Progress step indicator tampil saat execute
- [ ] Log sensitif dimasking
- [ ] Size limit + timeout guardrail aktif
- [ ] Last session restore tersedia

---

## Kesimpulan

Jika harus memilih sedikit tapi paling berdampak, urutan paling efektif adalah:

1. **Preflight Check**
2. **Dry Run**
3. **Path boundary hardening + overwrite confirmation**
4. **Progress indicator + error message actionable**

Urutan ini memberi kombinasi terbaik antara **correctness**, **security**, dan **UX** tanpa mengubah fondasi tool secara radikal.