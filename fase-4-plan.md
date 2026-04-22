# Fase 4 Plan - Efisiensi Harian dan Polish

Dokumen ini merinci implementasi Fase 4 berdasarkan roadmap di `docs/mvp_upgrade1.md`, tetapi disesuaikan dengan kondisi repo saat ini agar rencana tetap akurat terhadap arsitektur yang sudah berjalan.

## Ringkasan Hasil Scan

Hasil scan repo menunjukkan beberapa fondasi UX yang semula ada di fase sebelumnya sudah tersedia dan mempengaruhi cara Fase 4 sebaiknya diimplementasikan.

- UI desktop utama sudah memiliki selector `Pekerjaan`, preflight otomatis, progress per langkah, dan tombol `Start New Session` di `app/ui/main_window.py`.
- `Start New Session` sudah benar-benar me-reset state sesi UI tanpa menghapus file hasil, dan sudah punya test di `tests/test_main_window.py`.
- Pipeline sudah mengembalikan `PipelineResult`, tetapi payload hasilnya masih minimal: hanya `output_path`, `source_copy_path`, dan `sheets_written`.
- Belum ada mekanisme persistence untuk last session, recent files, atau window geometry.
- Belum ada service khusus untuk menyimpan preferensi ringan user di runtime.
- Belum ada dukungan drag-and-drop source file di UI.
- Empty state dan hint saat ini masih berupa teks statis singkat di beberapa `StringVar`, belum kontekstual terhadap state startup, idle, mismatch preflight, atau pasca-run.
- Belum ada panel ringkasan hasil run yang berdiri sendiri; informasi selesai run masih tersebar di `status`, `target output`, progress, dan log.

Implikasinya: Fase 4 sebaiknya bukan dimulai dari desain visual dulu, tetapi dari kontrak state sesi ringan yang kemudian dipakai bersama oleh `last session restore`, `job summary panel`, dan hint kontekstual.

## Prinsip Implementasi Fase 4

- Pertahankan perubahan sekecil mungkin di `app/ui/main_window.py`; pindahkan persistence ringan ke service terpisah agar UI tidak cepat membengkak.
- Jangan menyimpan data sensitif atau state yang rapuh. Simpan hanya metadata ringan yang aman dan mudah divalidasi ulang.
- Semua restore harus bersifat best-effort. Jika file/job lama sudah tidak valid, aplikasi tetap startup normal dengan fallback aman.
- Empty state dan hint harus mengikuti state nyata aplikasi, bukan string hardcoded tunggal.
- Drag-and-drop harus opsional dan punya fallback ke tombol `Pilih Source`, karena dependency DnD di Tk desktop sering berbeda antar environment.

## Dependency Teknis yang Sudah Ada

Dependensi berikut sudah bisa dipakai ulang untuk Fase 4:

- `discover_job_profiles(...)` untuk memvalidasi job yang tersedia saat startup atau restore.
- `validate_source_file(...)` untuk memvalidasi source yang direstore atau dijatuhkan via drag-and-drop.
- `_schedule_preflight()` untuk memicu validasi otomatis setelah source/job dipulihkan.
- `_start_new_session()` untuk mengembalikan UI ke baseline bila restore invalid atau user ingin memulai batch baru.
- `sanitize_log_message(...)` untuk memastikan log fitur baru tetap aman.

## Fase 4 Breakdown

### Subfitur 4.1 - Last Session Restore

#### Tujuan

Mempercepat penggunaan harian dengan memulihkan konteks kerja terakhir yang aman untuk dipakai ulang saat startup.

#### Kondisi Repo Saat Ini

- Belum ada file state sesi.
- Belum ada hook startup untuk memuat preferensi terakhir.
- Window geometry saat ini di-hardcode lewat `self.geometry("1120x720")` dan belum dipersist.
- Source terakhir, job terakhir, dan output terakhir hanya hidup di memori runtime.

#### Scope yang Direkomendasikan

Scope MVP untuk fitur ini:

- simpan `selected_job_id`
- simpan `source_path`
- simpan `window_geometry`
- simpan timestamp sesi terakhir
- tampilkan opsi ringan `Gunakan sesi terakhir` saat ada state valid

Di luar scope awal:

- restore log lama
- restore hasil preflight lama apa adanya
- restore status sukses/gagal lama secara penuh
- auto-run pipeline setelah startup

#### Desain Teknis

Tambahkan service baru, misalnya `app/services/session_state_service.py`.

Kontrak data yang disarankan:

```json
{
  "version": 1,
  "last_job_id": "report-bulanan",
  "last_source_path": "C:/Users/.../source.xlsx",
  "window_geometry": "1120x720+100+80",
  "updated_at": "2026-04-22T09:10:11"
}
```

Lokasi file yang disarankan:

- `runtime_root/.app_state/session_state.json`

Alasan:

- tidak mencampur state aplikasi dengan `configs/`, `masters/`, `uploads/`, atau `outputs/`
- mudah diabaikan dari alur bisnis utama
- aman untuk source mode maupun bundle mode

#### Aturan Restore

- jika file state tidak ada: startup normal tanpa prompt restore
- jika `last_job_id` tidak ditemukan atau job invalid: abaikan restore job
- jika `last_source_path` tidak valid atau file hilang: abaikan restore source
- jika geometry invalid: pakai geometry default
- jika job dan source valid: tampilkan CTA untuk memakai sesi terakhir, bukan langsung menjalankan execute
- setelah restore source/job, jalankan `_schedule_preflight()` agar state yang dipakai selalu fresh

#### Opsi UX yang Disarankan

Pilih implementasi ini untuk MVP:

- startup memuat state
- jika valid, tampilkan banner/hint: `Sesi terakhir ditemukan untuk pekerjaan X. Gunakan sesi terakhir atau pilih source baru.`
- sediakan tombol `Use Last Session`
- jika user tidak menekan tombol itu, UI tetap pada kondisi normal

Kenapa bukan auto-restore penuh:

- lebih aman untuk user operasional
- mengurangi risiko salah lanjut memakai source lama
- konsisten dengan prinsip bahwa `Execute` hanya aktif setelah preflight state saat ini selesai

#### Perubahan File yang Diperlukan

- tambah `app/services/session_state_service.py`
- ekspor service baru di `app/services/__init__.py`
- update `app/ui/main_window.py` untuk:
  - load state saat startup
  - simpan state saat source dipilih
  - simpan state saat job berubah
  - simpan geometry saat window ditutup atau berubah
  - tampilkan CTA `Use Last Session`

#### Test yang Perlu Ditambah

- `tests/test_session_state_service.py`
  - load state saat file belum ada
  - load state invalid JSON
  - save dan load roundtrip
  - geometry invalid diabaikan
- `tests/test_main_window.py`
  - startup tanpa state tidak menampilkan CTA restore
  - state valid memunculkan hint restore
  - restore job invalid fallback aman
  - restore source hilang fallback aman

#### Risiko dan Mitigasi

- Risiko: user tanpa sadar memakai source lama.
- Mitigasi: gunakan restore berbasis CTA, bukan auto-execute atau auto-apply diam-diam.

---

### Subfitur 4.2 - Job Summary Panel

#### Tujuan

Menampilkan ringkasan run terakhir dalam satu area yang mudah dipindai setelah proses selesai.

#### Kondisi Repo Saat Ini

- Setelah run sukses, UI hanya memperbarui `status`, `last_output_var`, progress, dan log.
- `PipelineResult` belum membawa durasi total, nama job, jumlah warning/error preflight, atau daftar sheet output.
- Ringkasan run tersebar dan belum punya panel khusus.

#### Scope yang Direkomendasikan

Panel ringkasan minimal setelah run:

- pekerjaan yang dijalankan
- nama source
- durasi run
- jumlah sheet output
- path output
- status akhir
- ringkasan preflight terakhir: jumlah `error/warning/info`

Opsional tahap berikutnya:

- daftar nama sheet yang ditulis
- tombol copy path
- tombol buka file output langsung

#### Desain Teknis

Perluas `PipelineResult` secara minimal agar summary bisa dibangun tanpa parsing log.

Kontrak tambahan yang disarankan:

- `duration_ms: int`
- `sheet_names: tuple[str, ...]`

Job label dan preflight summary sebaiknya tetap dirakit di UI karena konteksnya sudah ada di `DesktopApp`.

#### Desain UI

Tambahkan blok `Job Summary` di panel kiri, dekat area `Target output` atau tepat di bawah status akhir.

Isi awal ketika belum pernah run:

- `Belum ada proses yang selesai.`

Isi saat sukses:

- `Status: Sukses`
- `Pekerjaan: ...`
- `Source: ...`
- `Durasi: ... detik`
- `Sheet output: n`
- `Output: ...`
- `Preflight: x error, y warning, z info`

Isi saat gagal:

- tampilkan `Status: Gagal`
- tetap tampilkan job, source, dan durasi sampai gagal jika tersedia
- tampilkan `Output: -`

#### Perubahan File yang Diperlukan

- update `app/services/pipeline_types.py`
- update `app/services/pipeline_service.py` untuk mengisi durasi dan nama sheet
- update `app/ui/main_window.py` untuk menambah panel summary dan lifecycle reset-nya

#### Test yang Perlu Ditambah

- `tests/test_pipeline_service.py`
  - `PipelineResult` berisi `duration_ms`
  - `PipelineResult` berisi nama sheet hasil
- `tests/test_main_window.py`
  - summary kosong di startup
  - summary sukses terisi setelah event `success`
  - summary gagal menampilkan status gagal tanpa output palsu
  - `Start New Session` mengosongkan panel summary

#### Risiko dan Mitigasi

- Risiko: summary menduplikasi info yang sudah ada dan membuat UI penuh.
- Mitigasi: buat panel compact, 5-7 baris, bukan tabel besar.

---

### Subfitur 4.3 - Empty State dan Hint yang Lebih Ramah

#### Tujuan

Mengurangi kebingungan user pada tiga momen utama: startup, saat input belum lengkap, dan saat preflight memblokir execute.

#### Kondisi Repo Saat Ini

- Ada beberapa string default seperti `Belum ada pekerjaan terpilih.` dan `Pilih source dan pekerjaan untuk memulai pemeriksaan otomatis.`
- Hint belum berubah secara kaya berdasarkan kombinasi state nyata aplikasi.
- Empty state job invalid belum memberi CTA yang cukup jelas.
- Disable state `Execute` belum selalu menjelaskan alasan terdekat ke user.

#### Masalah UX yang Terlihat dari Struktur Sekarang

- user tahu `Execute` disable, tetapi tidak selalu tahu penyebab terdekatnya
- user dengan job registry invalid hanya melihat info pendek, belum diarahkan ke tindakan berikutnya
- setelah preflight `Blocked`, alasan detail lebih banyak hidup di log daripada di area UI utama
- setelah startup, layar belum memberi urutan aksi yang paling jelas

#### Desain State-Driven Hint

Alih-alih string statis, buat resolver kecil di UI, misalnya `_resolve_primary_hint()` dan `_resolve_execute_hint()`.

State utama yang perlu dicakup:

1. Tidak ada job valid
2. Job ada, source belum dipilih
3. Source ada, preflight sedang berjalan
4. Preflight `Blocked`
5. Preflight `Warning`
6. Ready to execute
7. Worker sedang berjalan
8. Run selesai sukses
9. Run selesai gagal

Contoh hint yang direkomendasikan:

- `Belum ada pekerjaan valid. Cek file configs/job_profiles.yaml dan config yang dirujuk.`
- `Pilih source file untuk pekerjaan yang aktif.`
- `Preflight sedang memeriksa kecocokan source, config, dan output.`
- `Execute dinonaktifkan karena masih ada error preflight. Lihat ringkasan preflight atau log untuk detail.`
- `Source siap diproses. Jalankan Execute untuk membuat output.`
- `Proses selesai. Periksa Job Summary atau buka folder outputs.`

#### Perubahan File yang Diperlukan

- update `app/ui/main_window.py`
  - tambah `StringVar` untuk primary hint dan execute hint
  - panggil updater hint dari event penting: startup, refresh job, pilih source, preflight result, worker start, worker finish, start new session

Tidak perlu service baru untuk tahap ini; cukup helper method kecil di UI karena logikanya sangat terkait presentasi.

#### Test yang Perlu Ditambah

- `tests/test_main_window.py`
  - hint startup saat tidak ada job valid
  - hint saat source belum dipilih
  - hint saat preflight blocked
  - hint saat ready
  - hint setelah sukses dan gagal

#### Risiko dan Mitigasi

- Risiko: terlalu banyak teks membuat panel kiri terasa padat.
- Mitigasi: bedakan satu hint primer dan satu hint aksi singkat, bukan banyak label baru.

---

### Subfitur 4.4 - Drag-and-Drop Source File

#### Tujuan

Mempercepat input source untuk user operasional yang sering bekerja dari File Explorer.

#### Kondisi Repo Saat Ini

- Pemilihan source hanya lewat tombol `Pilih Source`.
- Belum ada dependency atau binding drag-and-drop di aplikasi.
- Validasi source setelah pilih file sudah tersedia dan bisa dipakai ulang.

#### Constraint Penting

Tk/CustomTkinter tidak menyediakan drag-and-drop file native yang konsisten di semua environment tanpa bantuan tambahan. Karena repo saat ini belum memakai library DnD, fitur ini perlu diputuskan dengan pendekatan yang realistis.

#### Opsi Implementasi

Opsi A, direkomendasikan untuk MVP jika dependency tambahan boleh masuk:

- gunakan `tkinterdnd2`
- buat area drop sederhana di bawah field source
- saat file dijatuhkan:
  - parse path file
  - validasi hanya satu file
  - panggil alur yang sama dengan `_select_source()` setelah validasi

Opsi B, fallback jika dependency baru ingin dihindari:

- tunda implementasi drag-and-drop native
- ganti dengan tombol input yang lebih cepat dan hint eksplisit bahwa source bisa dipilih ulang dengan sekali klik

Karena user meminta plan Fase 4, bukan langsung implementasi, rekomendasi saya tetap mencantumkan Opsi A sebagai target utama dan Opsi B sebagai fallback keputusan teknis.

#### Desain Teknis Jika Memakai `tkinterdnd2`

- bungkus inisialisasi root/window agar kompatibel dengan `TkinterDnD`
- buat helper kecil `_handle_dropped_source(raw_drop_data: str)`
- normalisasi format path Windows yang biasanya dibungkus `{}` atau mengandung spasi
- jika lebih dari satu file dijatuhkan: tolak dengan pesan jelas
- reuse `validate_source_file(...)`, `_schedule_preflight()`, dan `_update_execute_state()`

#### Perubahan File yang Diperlukan

- update dependency project bila `tkinterdnd2` dipilih
- update `app/ui/main_window.py`
- kemungkinan update build/packaging bila bundle PyInstaller perlu hidden import tambahan
- update `README.md` atau panduan build bila dependency ini benar-benar dipakai

#### Test yang Perlu Ditambah

- `tests/test_main_window.py`
  - dropped single valid file mengisi source
  - dropped invalid extension ditolak
  - dropped multiple files ditolak
  - dropped missing file ditolak

Catatan: test unit sebaiknya fokus di parser/helper drop data, bukan event GUI native end-to-end.

#### Risiko dan Mitigasi

- Risiko: dependency drag-and-drop menambah kompleksitas packaging.
- Mitigasi: isolasi integrasi pada helper kecil dan siapkan fallback ke tombol biasa jika runtime tidak mendukung.

---

## Urutan Implementasi yang Direkomendasikan

Urutan terbaik untuk Fase 4 di repo ini:

1. `Last session restore`
2. `Empty state dan hint`
3. `Job summary panel`
4. `Drag-and-drop source file`

Alasannya:

- session restore membangun fondasi persistence ringan
- hint kontekstual memakai state yang sama dan bisa dikembangkan cepat setelah itu
- job summary bergantung pada kontrak hasil run yang sedikit lebih kaya
- drag-and-drop paling berisiko terhadap dependency dan packaging, jadi paling aman ditaruh terakhir

## Breakdown Task Implementasi

### Batch A - Session State Foundation

- buat `session_state_service`
- definisikan schema JSON state sesi
- load state saat startup
- simpan state saat job/source berubah
- simpan geometry saat close
- tambahkan CTA `Use Last Session`
- tambah unit test service dan UI fallback

Exit criteria:

- aplikasi bisa mendeteksi sesi terakhir valid
- restore bersifat best-effort dan tidak memblokir startup

### Batch B - Hint dan Empty State

- tambah resolver hint berbasis state
- tampilkan alasan disable `Execute`
- rapikan empty state saat tidak ada job valid
- tambahkan hint setelah sukses/gagal
- tambah test state matrix minimal

Exit criteria:

- user selalu melihat langkah berikutnya yang paling masuk akal

### Batch C - Job Summary

- perluas `PipelineResult`
- tampilkan panel summary ringkas di UI
- reset summary saat `Start New Session`
- tambah test pipeline result dan update UI

Exit criteria:

- setelah run, user bisa memahami hasil tanpa membaca seluruh log

### Batch D - Drag-and-Drop

- putuskan dependency `tkinterdnd2` atau fallback
- implement parser dropped path
- integrasikan ke flow pilih source
- update packaging/test sesuai keputusan

Exit criteria:

- user bisa mengisi source lewat drag-and-drop, atau fitur resmi ditunda dengan fallback yang jelas bila dependency tidak disetujui

## Perubahan Arsitektur yang Diusulkan

Tambahan paling masuk akal untuk struktur repo:

- `app/services/session_state_service.py`
  - baca/tulis state sesi ringan
- `app/services/pipeline_types.py`
  - perluas `PipelineResult`
- `app/ui/main_window.py`
  - restore CTA
  - summary panel
  - state-driven hint
  - drag-and-drop handler jika dipilih

Tidak perlu menambah layer arsitektur baru yang berat. Fase 4 masih bisa dijaga sebagai polish di atas fondasi yang sudah ada.

## Checklist Per Subfitur

### Last Session Restore

- [ ] Schema state sesi ditentukan dan versioned
- [ ] File state disimpan di lokasi runtime yang aman
- [ ] Restore job terakhir bersifat best-effort
- [ ] Restore source terakhir bersifat best-effort
- [ ] Restore geometry bersifat best-effort
- [ ] CTA `Use Last Session` tampil hanya saat state valid
- [ ] Test service dan fallback startup tersedia

### Job Summary Panel

- [ ] `PipelineResult` membawa data yang cukup untuk summary
- [ ] Summary kosong tampil saat startup
- [ ] Summary sukses tampil setelah run sukses
- [ ] Summary gagal tampil setelah run gagal
- [ ] Summary di-reset saat `Start New Session`
- [ ] Test summary UI tersedia

### Empty State dan Hint

- [ ] Hint startup diperjelas
- [ ] Hint saat source belum dipilih tersedia
- [ ] Alasan disable `Execute` terlihat
- [ ] Hint `Preflight Blocked` lebih actionable
- [ ] Hint pasca-run tersedia
- [ ] Test matrix state utama tersedia

### Drag-and-Drop Source File

- [ ] Keputusan dependency DnD dikunci
- [ ] Handler parser drop data diimplementasikan
- [ ] Validasi single-file ditegakkan
- [ ] Reuse flow validasi source yang sudah ada
- [ ] Packaging impact diverifikasi jika dependency baru dipakai
- [ ] Test helper drop path tersedia

## Rekomendasi Keputusan Sebelum Implementasi

Ada dua keputusan kecil yang sebaiknya dikunci sebelum coding Fase 4:

1. `Last session restore` memakai CTA manual atau auto-restore langsung. Rekomendasi: CTA manual.
2. `Drag-and-drop` boleh menambah dependency `tkinterdnd2` atau harus tanpa dependency baru. Rekomendasi: boleh dependency baru jika packaging Windows diverifikasi.

## Definition of Done Fase 4

Fase 4 dianggap selesai jika:

- startup aplikasi lebih informatif dan tidak membingungkan
- user bisa memulihkan konteks kerja terakhir dengan aman
- hasil run terakhir terbaca cepat lewat panel summary
- source bisa dipilih lebih cepat, idealnya via drag-and-drop
- seluruh tambahan punya test unit yang cukup untuk state utama

## Kesimpulan

Fase 4 di repo ini sebaiknya diposisikan sebagai `stateful UX polish`, bukan sekadar tambah widget. Fondasi yang paling penting adalah persistence sesi ringan dan resolver hint berbasis state. Setelah itu, `Job Summary` dan `Drag-and-Drop` akan lebih mudah masuk tanpa membuat `main_window.py` menjadi rapuh.
