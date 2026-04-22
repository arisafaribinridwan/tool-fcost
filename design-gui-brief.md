# GUI Design Brief

## Product Overview

Tool ini adalah aplikasi desktop untuk mengubah file source Excel/CSV menjadi file output Excel terformat berdasarkan job/config yang sudah disiapkan. Produk ini dipakai untuk mempercepat pekerjaan berulang, mengurangi proses manual di Excel, dan membuat hasil lebih konsisten.

## Design Objective

Desain baru perlu membuat aplikasi terasa lebih rapi, modern, dan mudah dipakai tanpa mengubah inti alur kerja. Prioritas utamanya adalah kejelasan langkah, kejelasan status, dan rasa aman saat user menjalankan proses.

## Primary User

- Pengguna personal/internal.
- Bekerja rutin dengan file Excel/CSV.
- Tidak ingin melakukan transformasi manual berulang di Excel.
- Lebih membutuhkan kejelasan status, hasil, dan langkah berikutnya daripada banyak pengaturan di layar utama.

## Product Character

- Desktop app, bukan web app.
- Digunakan terutama di Windows desktop.
- Dapat berjalan offline.
- Karakter visual yang diharapkan: profesional, ringkas, fungsional, mudah dipahami dalam sekali lihat.

## Core User Flow

1. User membuka aplikasi.
2. User memilih atau drag-and-drop satu file source `.xlsx` atau `.csv`.
3. User memilih job aktif.
4. Sistem menjalankan preflight check otomatis.
5. Jika semua siap, user menekan `Execute`.
6. User memantau progress proses dan log.
7. User melihat hasil akhir dan membuka folder output.
8. User dapat memulai sesi baru atau memulihkan sesi terakhir.

## Main Features That Must Be Represented

- Source input dengan tombol pilih file dan area drag-and-drop.
- Pemilihan job dari daftar.
- Akses ke `Job Settings`.
- Tombol refresh daftar job.
- Opsi `Use Last Session`.
- Ringkasan preflight otomatis sebelum eksekusi.
- Tombol `Execute` yang aktif hanya jika kondisi valid.
- Progress bar dan daftar langkah proses.
- Process log yang terus terisi saat proses berjalan.
- Ringkasan hasil job setelah proses selesai.
- Informasi output terakhir / target output.
- Tombol buka folder `outputs`.
- Tombol `Start New Session` setelah status sukses atau gagal.

## Main Screen Structure

Layout utama saat ini terbagi menjadi dua area besar dan struktur ini masih relevan:

- Panel kiri untuk kontrol utama, status, dan ringkasan.
- Panel kanan untuk area log proses yang dominan.

Panel kiri perlu mengakomodasi blok informasi berikut:

- Judul aplikasi dan instruksi singkat.
- Source picker.
- Job selector.
- Informasi restore session.
- Informasi job aktif.
- Hint atau guidance status.
- Blok preflight.
- Primary action `Execute`.
- Blok progress.
- Akses output.
- Status akhir dan job summary.

## Critical States

State berikut harus sangat jelas dibedakan secara visual:

- Idle.
- Preflight checking.
- Ready to execute.
- Running.
- Success.
- Failed.
- Blocked karena preflight error.

Perbedaan state sebaiknya terlihat cepat melalui hierarki visual, warna status, penekanan CTA, dan perubahan isi panel ringkasan.

## Key Information To Keep Clear

- Nama atau path source terpilih.
- Nama job aktif.
- Status preflight dan ringkasan error/warning/info.
- Progress langkah proses berikut:
  `Load config`, `Copy source`, `Read source`, `Load master`, `Transform`, `Build output`, `Write output`.
- Status akhir pekerjaan.
- Lokasi output terakhir.

## Secondary Screen

Perlu ada konsep untuk dialog `Job Settings`.

Dialog ini perlu menampung:

- Daftar job.
- Form nama job.
- Pilihan config.
- Toggle aktif/nonaktif.
- Preview file master yang dipakai.
- Tombol simpan.

## UX Direction

- Jadikan `Execute` sebagai primary action yang paling menonjol.
- Buat user selalu tahu apa yang harus dilakukan berikutnya.
- Kurangi kesan teknis berlebih, tetapi jangan menyembunyikan status penting.
- Pastikan path panjang, log, dan summary tetap mudah dipindai.
- Optimalkan untuk layar laptop kerja standar, namun tetap nyaman ketika window diperbesar.
- Pertimbangkan desain yang tetap kuat di mode terang dan gelap.

## Design Constraints

- Jangan mengubah produk menjadi flow wizard panjang.
- Jangan mengasumsikan user akan mengedit YAML dari layar utama.
- Produk ini bukan dashboard analytics.
- UI harus tetap terasa ringan dan cepat untuk penggunaan kerja harian.

## Expected Deliverables

- 1 konsep layar utama desktop.
- 1 konsep state utama: idle, ready, running, success, failed, blocked.
- 1 konsep dialog `Job Settings`.
- Opsional: versi light dan dark mode.
