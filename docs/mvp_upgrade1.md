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

### 6) Start New Session / Reset UI Setelah Worker Selesai

#### Problem
Setelah satu eksekusi selesai, state UI masih membawa konteks sesi sebelumnya: source file masih terisi, log lama masih terlihat, status terakhir masih menempel, dan target output sebelumnya masih tampil. Untuk user operasional, ini membuat sesi berikutnya terasa ambigu dan meningkatkan risiko salah pakai source/config lama.

#### Solusi
Tambahkan tombol **`Start New Session`** pada UI desktop untuk mengembalikan layar ke kondisi seperti saat aplikasi pertama dibuka.

#### Perilaku yang direkomendasikan
- Tombol hanya aktif setelah proses worker selesai, baik hasilnya `Sukses` maupun `Gagal`
- Tombol tetap nonaktif saat worker masih berjalan
- Saat diklik, UI di-reset ke kondisi awal sesi tanpa menghapus file hasil yang sudah dibuat
- Config di-refresh kembali dan default selection mengikuti perilaku startup saat ini

#### State yang di-reset
- `source` dikosongkan
- log proses dikosongkan
- status dikembalikan ke `Idle`
- target output dikembalikan ke placeholder awal
- tombol `Execute` kembali nonaktif sampai source baru dipilih
- info config diperbarui ulang sesuai config valid yang tersedia

#### Yang tidak di-reset
- file output yang sudah berhasil dibuat
- isi folder `uploads/` dan `outputs/`
- file config dan master di runtime folder

#### Dampak
- Mengurangi risiko user menjalankan sesi baru dengan konteks lama
- Membuat alur kerja harian lebih jelas untuk batch berikutnya
- Menambah rasa aman tanpa perlu menutup dan membuka aplikasi ulang

---

### 7) Pilih `Pekerjaan` sebagai Entry Point Utama

#### Problem
Saat ini user harus memilih `Config YAML`, padahal istilah ini teknis dan rawan salah pilih. Untuk user operasional, yang mereka pahami biasanya adalah jenis pekerjaan atau proses bisnis yang ingin dijalankan, bukan nama file config.

#### Solusi
Ganti atau bungkus pilihan `Config YAML` dengan selector **`Pekerjaan`** yang lebih ramah user.

#### Perilaku yang direkomendasikan
- User memilih `Pekerjaan`, bukan file config mentah
- Setiap `Pekerjaan` dipetakan ke config utama yang tepat
- Deskripsi singkat pekerjaan ditampilkan di UI agar user yakin memilih proses yang benar
- Dependensi config/master tetap dibaca dari config aktual, tetapi disembunyikan dari user non-teknis

#### Bentuk desain yang direkomendasikan
Tambahkan registry eksplisit, misalnya `configs/job_profiles.yaml`, yang berisi metadata berikut:
- `id`
- `label`
- `description`
- `config_file`
- `enabled`
- petunjuk preflight tambahan jika diperlukan

#### Dampak
- Mengurangi salah pilih config
- Membuat UI lebih mudah dipahami user non-teknis
- Menjadi fondasi untuk preflight source yang lebih kontekstual

---

### 8) Lookup Symptom Berbasis Regex + Master Rule yang Lebih Maintainable

#### Problem
Lookup symptom saat ini masih terbatas pada pola sederhana. Untuk data operasional nyata, variasi penulisan symptom comment sering sangat banyak, penuh singkatan, typo, dan frasa yang mirip tetapi tidak identik. Ini membuat master symptom cepat membengkak dan sulit dirawat jika hanya mengandalkan exact/wildcard sederhana.

#### Solusi
Tambahkan dukungan **regex-based lookup** untuk symptom dan rapikan desain master symptom menjadi rule table yang eksplisit.

#### Bentuk master yang direkomendasikan
Sheet `symptom` pada `masters/master_table.xlsx` diubah agar memakai struktur seperti:
- `priority`
- `part_name`
- `match_type`
- `pattern`
- `symptom`
- `notes`

#### Perilaku yang direkomendasikan
- Matching symptom dilakukan berdasarkan kombinasi `part_name` + `pattern`
- Rule diproses menurut `priority` (semakin kecil, semakin dulu)
- `match_type` minimal mendukung `regex`
- Engine memakai regex Python dengan semantik `search`, bukan `fullmatch`
- Rule default/fallback per `part_name` tetap dimungkinkan

#### Guardrail minimum
- compile regex sekali per rule, bukan per baris
- regex invalid harus menghasilkan error yang jelas dan memblokir execute
- panjang pattern dibatasi agar tidak terlalu berat
- perilaku existing `equals`/`contains` tetap dijaga agar tidak breaking

#### Dampak
- Master symptom lebih fleksibel dan lebih mudah dirawat
- Variasi input nyata lebih mudah ditangani tanpa ledakan jumlah rule manual
- Menjadi fondasi penting untuk preflight master yang lebih cerdas

---

## P2 - Sangat Disarankan

### 9) Progress Bar + Step Indicator

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

### 10) Error Message yang Actionable

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

### 11) Preflight Kecocokan Source terhadap `Pekerjaan`

#### Problem
Validasi source saat ini masih dominan di level file dasar atau baru terasa saat execute berjalan. User belum dibantu menjawab pertanyaan penting: apakah file source yang dipilih memang cocok untuk `Pekerjaan` yang dipilih?

#### Solusi
Perluas preflight agar tidak hanya mengecek file bisa dibaca, tetapi juga mengecek kecocokan source dengan konteks `Pekerjaan`.

#### Yang dicek
- sheet wajib untuk pekerjaan tersebut tersedia
- kolom wajib source tersedia
- format header source cukup sesuai dengan kebutuhan config
- config yang dipetakan dari `Pekerjaan` valid
- semua master yang direferensikan config tersedia
- jika ada mismatch, hasil ditandai jelas sebagai `Blocked` atau `Warning`

#### Output ke user
- status ringkas: `Ready`, `Warning`, `Blocked`
- alasan spesifik kenapa source dianggap cocok atau tidak cocok
- saran perbaikan, misalnya ganti file source atau pilih `Pekerjaan` lain

#### Dampak
- Mengurangi trial-error user saat pairing source vs proses
- Menurunkan risiko eksekusi salah resep
- Membuat tombol `Execute` bisa dikontrol lebih aman

---

### 12) Recent Files / Last Session Restore

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

### 13) Konfirmasi Sebelum Overwrite Output

#### Solusi
Jika nama output sudah ada, tampilkan pilihan:
- `Replace`
- `Keep both (auto suffix)`
- `Cancel`

#### Dampak
- Menghindari kehilangan output lama

---

## P3 - Nice to Have (Polish)

### 14) Panel "Job Summary"

Menampilkan ringkasan setelah run:
- source/config yang dipakai
- durasi proses
- jumlah sheet
- jumlah warning/error
- lokasi output + tombol copy path

### 15) Drag-and-Drop Source File

Untuk mempercepat input source tanpa klik dialog.

### 16) Empty State dan Hint yang Lebih Ramah

Contoh:
- Saat belum ada `Pekerjaan` valid, tampilkan call-to-action jelas.
- Saat source belum cocok dengan `Pekerjaan`, tombol execute tetap disable + alasan singkat.
- Saat preflight gagal, tampilkan langkah perbaikan paling mungkin.

---

## Rekomendasi Implementasi Bertahap (Blocking-First)

Urutan implementasi sebaiknya dimulai dari fondasi yang paling blocking ke fitur UX yang paling terlihat. Dengan begitu, fase awal membangun correctness dan safety lebih dulu, lalu fitur interaktif di atas fondasi yang sudah stabil.

## Fase 1 - Fondasi Domain dan Boundary (paling blocking)

Target:
- Job selector (`Pekerjaan`) + registry `job_profiles`
- Path boundary hardening
- Restrukturisasi master symptom ke rule table baru
- Regex-based lookup untuk symptom + guardrail dasar regex

Kenapa fase ini dulu:
- `Pekerjaan` adalah entry point baru untuk user dan menjadi dasar konteks preflight
- boundary file harus aman sebelum validasi dan execute diperluas
- desain master symptom baru adalah fondasi data yang perlu stabil sebelum preflight dan UX dibangun

Exit criteria:
- User memilih `Pekerjaan`, bukan config mentah
- Semua akses file berada dalam boundary yang aman
- Sheet `symptom` baru terbaca valid dan lookup regex berjalan stabil

## Fase 2 - Safety dan Correctness Sebelum Execute

Target:
- Preflight Check
- Preflight compatibility source vs pekerjaan
- Error message standard
- Overwrite confirmation
- Dry Run

Kenapa fase ini kedua:
- setelah fondasi domain dan master stabil, sistem bisa memberi validasi yang lebih akurat
- dry run baru bernilai tinggi jika config, master, dan rule matching sudah cukup dapat dipercaya

Exit criteria:
- User bisa tahu kondisi input tanpa mengeksekusi penuh
- mismatch source/config/master/rule mayor terdeteksi sebelum execute
- tidak ada overwrite tanpa konfirmasi

## Fase 3 - Stabilitas Operasional dan Transparansi Proses

Target:
- Resource guardrail (size/timeout)
- Log sanitization
- Progress step indicator
- Start New Session

Kenapa fase ini ketiga:
- fase ini memperkecil risiko sesi panjang, macet semu, dan kebocoran informasi setelah correctness dasar tercapai

Exit criteria:
- proses panjang lebih transparan
- data sensitif di log lebih aman
- user bisa memulai batch berikutnya tanpa konteks sesi lama

## Fase 4 - Efisiensi Harian dan Polish

Target:
- Last session restore
- Job summary panel
- Empty state dan hint yang lebih ramah
- Drag-and-drop source file

Kenapa fase ini terakhir:
- semuanya meningkatkan perceived quality, tetapi tidak memblokir correctness inti

Exit criteria:
- UX harian lebih cepat dan terasa lebih matang
- user lebih sedikit bingung saat startup, saat idle, dan setelah selesai run

---

## Dampak Teknis ke Arsitektur Saat Ini

Perubahan tetap bisa mengikuti arsitektur modular yang sudah ada:

- `app/services/`
  - tambah service `preflight_service.py`
  - tambah service/registry loader untuk `job_profiles`
  - update resolver lookup symptom agar mendukung regex rule table berbasis priority
  - tambah mode `dry_run` pada orchestrator pipeline
- `app/ui/main_window.py`
  - selector `Pekerjaan`
  - tombol `Preflight Check`
  - toggle `Dry Run`
  - tombol `Start New Session` yang aktif hanya setelah worker selesai
  - panel status langkah/progress
- `app/utils/`
  - helper sanitasi log
  - helper guardrail file/path
  - helper compile/validasi regex yang aman

Testing yang perlu ditambah:
- unit test resolver `job_profiles`
- unit test preflight rules
- unit test source compatibility per pekerjaan
- unit test regex lookup symptom dan priority order
- unit test invalid regex handling
- unit test overwrite decision
- unit test log masking
- integration test dry run vs real run

---

## Checklist MVP Upgrade 1 (Praktis)

- [ ] Tombol `Preflight Check` tersedia dan berjalan
- [ ] Mode `Dry Run` tersedia
- [ ] Selector `Pekerjaan` tersedia dan memetakan ke config yang tepat
- [ ] Sheet `symptom` mendukung rule table baru (`priority`, `part_name`, `match_type`, `pattern`, `symptom`, `notes`)
- [ ] Lookup symptom berbasis regex berjalan dan menghormati urutan `priority`
- [ ] Preflight menampilkan severity (`ERROR/WARNING/INFO`)
- [ ] Preflight dapat menyatakan source cocok/tidak cocok terhadap `Pekerjaan`
- [ ] Path traversal dan akses path di luar boundary diblokir
- [ ] Tombol `Start New Session` tersedia dan reset UI hanya setelah worker selesai
- [ ] Overwrite output meminta konfirmasi
- [ ] Error message menggunakan format actionable
- [ ] Progress step indicator tampil saat execute
- [ ] Log sensitif dimasking
- [ ] Size limit + timeout guardrail aktif
- [ ] Last session restore tersedia

---

## Kesimpulan

Jika harus memilih sedikit tapi paling berdampak, urutan paling efektif adalah:

1. **Pilih `Pekerjaan` + path boundary hardening**
2. **Restrukturisasi master symptom + regex lookup symptom**
3. **Preflight Check + compatibility preflight**
4. **Dry Run + overwrite confirmation + error message actionable**
5. **Resource guardrail + log sanitization + progress indicator**

Urutan ini memberi kombinasi terbaik antara **correctness**, **security**, dan **UX** tanpa mengubah fondasi tool secara radikal.
