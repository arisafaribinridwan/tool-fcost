## Context
Fitur **cari job** di sidebar [app/ui/settings.py](app/ui/settings.py) saat ini belum benar-benar aktif. Input pencarian sudah dibuat pada bagian sidebar, tetapi belum ada binding event yang memicu filter, dan renderer list masih selalu menampilkan seluruh `self.jobs`. Dampaknya, saat user mengetik kata kunci, daftar job tidak berubah.

## Rencana Implementasi (Recommended)
1. **Tambahkan state filter di UI settings**
   - Tambahkan properti untuk query dan daftar indeks hasil filter, mis. `self.search_query` dan `self.filtered_job_indices`.
   - Tetap gunakan `self.jobs` sebagai source of truth (hasil `discover_job_profiles`), agar tidak mengubah layer service.

2. **Hubungkan input pencarian ke handler**
   - Di `_build_sidebar`, bind `self.search_entry` ke handler baru (mis. `_on_search_changed`) menggunakan `<KeyRelease>`.
   - Handler ini akan membaca query, normalisasi (`strip` + `casefold`), lalu panggil `_apply_job_filter()`.

3. **Implementasi filter list berbasis data existing**
   - Buat `_apply_job_filter()` yang membangun `self.filtered_job_indices` dari `self.jobs`.
   - Kriteria awal: match terhadap `job["label"]` (case-insensitive, contains).
   - Setelah filter dihitung, panggil `_render_job_list()` untuk redraw sidebar.

4. **Perbarui render sidebar agar pakai hasil filter**
   - Ubah `_render_job_list()` supaya iterasi dari `self.filtered_job_indices` (bukan langsung `enumerate(self.jobs)`).
   - Ubah `_create_job_item(...)` agar menerima **actual job index** dan menyimpan mapping itu di widget/button (mis. `btn._job_index`).
   - Event click pada item harus memanggil `_load_job_data(actual_index)` agar detail panel tetap sinkron.

5. **Sinkronkan highlight/selection saat list terfilter**
   - Di `_load_job_data`, saat mewarnai item terpilih, bandingkan menggunakan `btn._job_index` vs `selected_job_index` (actual index), bukan index visual baris.
   - Pastikan hover style hanya berlaku pada item yang tidak sedang selected.

6. **Tambah empty state saat hasil pencarian kosong**
   - Jika `self.filtered_job_indices` kosong, tampilkan label info ringan di area list (contoh: “Tidak ada job yang cocok.”).
   - Pastikan `_resize_job_items()` aman saat tidak ada item.

7. **Integrasi dengan lifecycle yang sudah ada**
   - Setelah `_reload_runtime_data()` (mis. sesudah save/import), panggil `_apply_job_filter()` agar daftar tetap mengikuti query aktif.
   - Untuk mode normal (query kosong), `_apply_job_filter()` harus menghasilkan seluruh index agar perilaku lama tetap sama.

## Fungsi/Utilitas Existing yang Direuse
- `discover_job_profiles(...)` via `_reload_runtime_data()` untuk sumber data job (tetap dipakai, tanpa perubahan service).
- `_load_job_data(...)` untuk sinkronisasi detail panel saat item sidebar dipilih.
- `_sync_control_state()` untuk state tombol/form tetap konsisten setelah perubahan selection/filter.

## File Kritis
- [app/ui/settings.py](app/ui/settings.py) — implementasi inti binding, filtering, rendering, dan selection.
- [app/services/job_profile_service.py](app/services/job_profile_service.py) — referensi sumber data job (dipastikan tidak perlu diubah untuk bug ini).

## Verifikasi End-to-End
1. Jalankan UI settings dan buka halaman konfigurasi job.
2. Ketik keyword di kolom “Cari job...” dan pastikan list sidebar terfilter real-time.
3. Uji case-insensitive (mis. huruf besar/kecil berbeda tetap ketemu).
4. Klik item dari hasil filter dan pastikan detail job yang tampil benar.
5. Hapus query pencarian dan pastikan seluruh list kembali muncul.
6. Uji query tanpa hasil: empty state tampil, tidak ada error/crash.
7. Jalankan flow save sederhana pada item yang dipilih dari hasil filter; pastikan job yang tersimpan adalah job yang benar.
8. Regression check singkat: add job, import config/master, dan precheck tetap berjalan.