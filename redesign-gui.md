# Redesign GUI Implementation Plan

## Tujuan Dokumen

Dokumen ini adalah panduan implementasi redesign GUI untuk aplikasi desktop berbasis `customtkinter` agar mendekati arah visual dan hierarki interaksi pada `desain-ui.jsx`, tanpa merusak flow kerja aplikasi yang sudah ada.

Gunakan dokumen ini sebagai source of truth implementasi redesign sampai pekerjaan utama layar utama dan dialog `Job Settings` selesai.

Dokumen ini ditulis agar bisa langsung dipakai oleh:

- junior developer yang akan mengerjakan redesign bertahap
- AI model lain yang perlu melanjutkan implementasi
- reviewer yang ingin memastikan perubahan UI tetap sejalan dengan brief produk

Fokus dokumen ini adalah:

- apa yang harus diubah
- urutan pengerjaan yang aman
- mapping antara prototype JSX dan kode Python yang sudah ada
- acceptance criteria per tahap
- risiko teknis dan cara menghindarinya

## Referensi Utama

- Brief desain: `design-gui-brief.md`
- Prototype visual: `desain-ui.jsx`
- Implementasi UI saat ini: `app/ui/main_window.py`
- Test UI saat ini: `tests/test_main_window.py`

## Ringkasan Kondisi Saat Ini

UI saat ini sudah memakai `customtkinter` dan bukan aplikasi Tkinter polos. Ini penting karena redesign tidak perlu memulai dari nol.

Komponen inti yang sudah tersedia:

- main window di `DesktopApp`
- dialog `Job Settings` di `JobSettingsDialog`
- source picker dan drag-and-drop source
- pemilihan job aktif
- refresh job list
- preflight otomatis
- tombol `Execute` yang digating oleh kondisi valid
- output target dan job summary
- process log
- tombol `Start New Session`

Artinya, pekerjaan redesign seharusnya difokuskan pada:

- perombakan layout dan visual hierarchy
- penguatan representasi state
- pemecahan area kiri menjadi section/card yang lebih jelas
- penyelarasan dialog `Job Settings` dengan prototype
- penambahan progress presentation yang saat ini belum diimplementasikan visualnya

## Prinsip Implementasi

- Jangan ubah flow inti aplikasi.
- Jangan pindahkan logika bisnis keluar dari tempatnya jika tidak perlu.
- Jangan membuat wizard baru.
- Jangan memasukkan editing YAML ke layar utama.
- Prioritaskan perubahan kecil yang aman tetapi terasa signifikan secara visual.
- Pisahkan perubahan visual dari perubahan perilaku jika memungkinkan.
- Pertahankan kompatibilitas dengan test yang sudah ada, lalu perbarui test hanya jika struktur UI memang berubah dan butuh coverage tambahan.

## Status Implementasi

### Tahap 1

Status: selesai.

Keputusan yang sudah diimplementasikan:

- urutan langkah pipeline dijadikan konstanta bersama `PIPELINE_STEP_ORDER` di `app/ui/main_window.py`
- fondasi reference widget redesign diinisialisasi eksplisit lewat `_init_redesign_foundation_refs()`
- state visual dasar dirapikan lewat helper `_resolve_visual_state()`
- formatter awal daftar step dirapikan lewat `_format_pipeline_step_lines()`
- coverage test ditambahkan untuk urutan step dan resolver visual state

Catatan:

- Tahap 1 belum mengubah layout atau tampilan utama
- perubahan sengaja dibatasi pada fondasi internal agar Tahap 2 dan seterusnya lebih aman

### Tahap 2

Status: selesai.

Keputusan yang sudah diimplementasikan:

- `DesktopApp._build_layout()` dipecah menjadi builder method yang lebih kecil dan spesifik
- struktur main window dipisah menjadi:
  - `_build_header_section()`
  - `_build_source_card()`
  - `_build_job_card()`
  - `_build_execute_card()`
  - `_build_result_card()`
  - `_build_log_panel()`
- area kiri sekarang tersusun sebagai section/card yang lebih jelas dibanding layout linear sebelumnya
- header utama sekarang memiliki title, subtitle, dan akses cepat ke `Pengaturan Job`
- panel kanan tetap dominan untuk `Process Log`
- wiring widget existing tetap dipertahankan untuk `self.job_menu`, `self.execute_button`, `self.start_new_session_button`, `self.source_drop_label`, dan `self.log_box`

Catatan:

- Tahap 2 berfokus pada refactor struktur dan segmentasi layout
- perubahan visual detail untuk source experience, readiness emphasis, progress, dan state badge tetap ditangani pada tahap berikutnya
- selama review Tahap 2 ditambahkan fallback aman untuk drag-and-drop jika `tkinterdnd2` terimpor tetapi runtime `tkdnd` tidak aktif pada package Linux

### Tahap 3

Status: selesai.

Keputusan yang sudah diimplementasikan:

- `Source card` sekarang menampilkan panel `Source aktif` yang lebih mudah dipindai daripada field input polos
- area dropzone source dibuat lebih menonjol secara visual dan tetap memakai wiring `self.source_drop_label` yang sudah ada
- aksi `Clear Source` ditambahkan untuk mengosongkan source aktif tanpa mengubah flow validasi yang sudah ada
- implementasi `Clear Source` disinkronkan dengan reset preflight, update hint, dan gating `Execute`
- `Job/readiness card` dirapikan menjadi blok yang lebih jelas untuk pemilihan job, ringkasan job aktif, dan readiness/preflight
- info sesi terakhir sekarang ditampilkan hanya jika `session_state_service` benar-benar memiliki `last_job_id` atau `last_source_path`
- persistence session state diperbaiki agar menyimpan `last_job_id` dan `last_source_path` nyata, bukan hanya geometry window
- coverage test ditambahkan untuk clear source, info sesi terakhir, dan persistence session state

Catatan:

- Tahap 3 tetap tidak menambahkan auto-restore session baru; perubahan dibatasi pada presentasi info sesi terakhir yang memang sudah punya backend data
- perubahan progress bar, state badge, dan execute card yang lebih ekspresif tetap ditangani pada Tahap 4

## Gap Analysis: JSX Prototype vs UI Python Saat Ini

### Sudah ada di UI Python

- panel kiri untuk kontrol utama
- panel kanan untuk log
- source file input
- area drag-and-drop hint
- pemilihan job
- tombol pengaturan job
- tombol refresh pekerjaan
- hint kesiapan dan hint execute
- preflight status dan summary
- tombol `Execute`
- hasil akhir, output target, job summary
- tombol `Buka Folder Outputs`
- tombol `Start New Session`
- dialog `Job Settings`

### Belum setara dengan prototype JSX

- header bar modern dengan identitas aplikasi yang lebih kuat
- pembagian area kiri menjadi 3 card utama seperti prototype
- badge/status chip yang jelas per state
- dropzone source yang terasa lebih seperti area interaktif utama
- section execution yang menempatkan `Execute` sebagai CTA paling dominan
- progress bar dan step list yang benar-benar tampil di UI
- success panel yang lebih eksplisit dan mudah dipindai
- log panel dengan nuansa visual terminal yang lebih kuat
- dialog `Job Settings` dengan sidebar daftar job dan form yang lebih rapi

### Hal yang tidak perlu dipaksakan identik 1:1

- animasi web seperti fade/slide/zoom
- shadow kompleks dan backdrop blur
- ikon `lucide-react` persis
- perilaku responsive seperti CSS grid web

Target implementasi adalah kesetaraan fungsi dan hierarki visual, bukan pixel-perfect clone.

## Area Kode yang Menjadi Titik Integrasi

### Main window

Lokasi utama:

- `app/ui/main_window.py:388` `DesktopApp._build_layout`

Method terkait perilaku UI yang harus tetap dipertahankan saat redesign:

- `_select_source`
- `_on_job_selected`
- `refresh_jobs`
- `_update_job_info`
- `_update_execute_state`
- `_set_preflight_idle`
- `_apply_preflight_result`
- `_schedule_preflight`
- `_execute_pipeline`
- `_start_new_session`
- `_open_job_settings`
- `_open_outputs_dir`
- `_append_log`
- `_update_hints`

Method yang saat ini masih placeholder dan perlu diisi saat redesign:

- `app/ui/main_window.py:691` `_reset_progress_state`
- `app/ui/main_window.py:694` `_apply_progress_update`

### Job settings dialog

Lokasi utama:

- `app/ui/main_window.py:109` `JobSettingsDialog._build_layout`

Method penting yang perlu tetap bekerja:

- `refresh`
- `_on_job_selected`
- `_on_config_selected`
- `_refresh_master_preview`
- `_save_job`

### Test yang relevan

- `tests/test_main_window.py`

Test existing terutama memverifikasi:

- gating tombol `Execute`
- gating `Start New Session`
- hint text per state
- job summary success/failure
- reset session behavior

## Arsitektur UI Target

### Struktur umum main window

Gunakan dua area utama seperti brief:

- kiri: control surface dan ringkasan
- kanan: process log dominan

Namun area kiri dipecah lagi menjadi blok berikut:

1. Header app
2. Source card
3. Job and readiness card
4. Execute and progress card
5. Result/output card

### Struktur visual target

#### Header app

Isi:

- nama aplikasi
- subheading singkat
- tombol `Pengaturan Job`

Tujuan:

- memberi identitas visual yang lebih kuat
- membuat area utama terasa modern dan terarah

#### Source card

Isi:

- label langkah `1`
- source picker button
- field/path source aktif
- dropzone area
- tombol clear source jika source sudah dipilih

Tujuan:

- user langsung tahu langkah pertama
- source menjadi elemen pertama yang paling mudah ditemukan

#### Job and readiness card

Isi:

- label langkah `2`
- dropdown job aktif
- tombol refresh
- akses `Job Settings`
- info restore/last session jika ada
- info job aktif
- primary hint
- preflight status
- preflight summary

Tujuan:

- menggabungkan konteks job dan readiness dalam satu blok yang koheren

#### Execute and progress card

Isi:

- label langkah `3`
- state badge aplikasi
- tombol `Execute` sebagai CTA utama
- execute hint
- progress bar
- daftar step proses

Tujuan:

- user selalu tahu kapan bisa menjalankan job
- user bisa memantau proses secara lokal tanpa harus membaca log panjang

#### Result card

Isi:

- status akhir
- target output / output terakhir
- job summary
- tombol buka folder outputs
- tombol `Start New Session`

Tujuan:

- memperjelas hasil akhir
- memudahkan tindakan setelah proses selesai

#### Process log panel

Isi:

- judul panel log
- indikator status ringan, misalnya `Online` atau `Ready`
- textbox log besar dengan styling gelap

Tujuan:

- log tetap dominan seperti brief
- log terasa sebagai area observasi proses, bukan sekadar textbox default

## Strategi Implementasi Bertahap

Implementasi disarankan dalam 6 tahap utama. Urutan ini dipilih agar perubahan besar tetap aman, mudah direview, dan mudah dites.

## Tahap 1: Audit State dan Persiapan Fondasi UI

### Tujuan

Membuat fondasi teknis agar redesign visual tidak bercampur dengan logika bisnis inti.

### Tugas

1. Baca penuh `DesktopApp._build_layout` dan identifikasi widget yang perlu dipertahankan.
2. Inventaris semua `StringVar`, button reference, dan widget reference yang sudah dipakai method lain.
3. Tentukan widget mana yang perlu tetap punya reference instance, misalnya:
   - `self.execute_button`
   - `self.start_new_session_button`
   - `self.job_menu`
   - `self.log_box`
   - `self.source_drop_label`
4. Tambahkan reference baru yang akan dibutuhkan untuk redesign, misalnya:
   - `self.state_badge_label`
   - `self.progress_bar`
   - `self.progress_label_var`
   - `self.progress_steps_var`
   - `self.source_card_frame`
   - `self.preflight_card_frame`
5. Definisikan helper visual kecil jika memang perlu, tetapi jangan berlebihan. Contoh:
   - helper untuk membuat section title
   - helper untuk apply style state badge
   - helper untuk update progress step list

### Output tahap

- daftar widget reference yang dipakai ulang oleh logic runtime
- daftar state visual yang harus dimapping
- keputusan naming widget baru yang konsisten

### Acceptance criteria

- tidak ada behavior yang berubah
- belum ada perubahan visual besar
- developer lain bisa melihat titik integrasi UI secara jelas

## Tahap 2: Redesign Struktur Main Window

### Tujuan

Mengubah layout utama agar mengikuti komposisi prototype JSX, tetapi tetap memakai behavior existing.

### Tugas

1. Pecah `DesktopApp._build_layout` menjadi struktur yang lebih mudah dibaca.
2. Pertimbangkan memecah builder menjadi beberapa method privat, misalnya:
   - `_build_header_section`
   - `_build_source_card`
   - `_build_job_card`
   - `_build_execute_card`
   - `_build_result_card`
   - `_build_log_panel`
3. Tetap bangun semua widget di dalam `DesktopApp` agar akses ke state dan method existing tidak rumit.
4. Ubah area kiri dari layout linear menjadi susunan card/section dengan spacing lebih jelas.
5. Tambahkan header atas yang memuat:
   - title app
   - subtitle singkat
   - tombol `Pengaturan Job`
6. Jaga lebar panel kiri agar tidak terlalu sempit untuk summary dan path panjang.
7. Jaga panel kanan tetap dominan untuk log.

### Catatan implementasi

- Jika builder method dipisah, hindari passing argumen berlebihan. Simpan referensi widget di `self` bila memang akan dipakai method lain.
- Jangan ubah behavior `_bind_drop_target`, `_append_log`, atau `_update_execute_state` pada tahap ini kecuali diperlukan untuk wiring widget baru.

### Acceptance criteria

- main window masih terbuka normal
- source selection, job selection, execute, dan log tetap berfungsi
- struktur kiri-kanan masih sesuai brief, tetapi visual sudah lebih modern dan tersegmentasi

## Tahap 3: Samakan Source, Job, dan Readiness Experience

### Tujuan

Menyamakan area interaksi awal user dengan prototype, terutama langkah 1 dan 2.

### Tugas

1. Source card:
   - tampilkan label langkah `1`
   - tampilkan area dropzone yang lebih menonjol
   - tampilkan source terpilih dalam panel yang mudah dipindai
   - sediakan aksi clear source jika source sudah dipilih
2. Job/readiness card:
   - tampilkan label langkah `2`
   - rapikan dropdown job + tombol refresh + akses settings
   - tampilkan info job aktif dalam blok ringkas
   - gabungkan primary hint dan preflight summary dalam hierarki yang lebih jelas
3. Jika ada data session terakhir yang memang tersedia di codebase, tampilkan informasi `Use Last Session` atau status restore terakhir dalam bentuk info block.

### Mapping ke code existing

- source path tetap memakai `self.source_var`
- info job tetap memakai `self.job_info_var`
- hint tetap memakai `self.primary_hint_var` dan `self.execute_hint_var`
- preflight tetap memakai `self.preflight_status_var` dan `self.preflight_summary_var`

### Catatan penting

- Jangan mengganti flow validasi source.
- Jika menambah tombol clear source, implementasinya harus konsisten dengan reset preflight dan update execute state.
- Jangan menambah session restore fiktif jika data backend-nya belum tersedia. Tampilkan hanya jika benar-benar bisa diambil dari state/session service yang ada.

### Acceptance criteria

- user bisa memahami langkah awal tanpa membaca banyak teks
- source terpilih, job aktif, dan preflight state terlihat jelas dalam sekali lihat
- gating `Execute` tetap benar

## Tahap 4: Implementasi Visual State, Execute Card, dan Progress

### Tujuan

Membuat state kritis aplikasi terlihat jelas dan menambahkan progress presentation yang saat ini belum ada.

### State yang wajib terlihat jelas

- `Idle`
- `Preflight checking`
- `Ready to execute`
- `Running`
- `Success`
- `Failed`
- `Blocked`

### Tugas

1. Tambahkan state badge di execute card.
2. Buat helper untuk memetakan state internal ke teks dan warna badge.
3. Implementasikan progress bar nyata di UI.
4. Implementasikan daftar step proses berikut di UI:
   - `Load config`
   - `Copy source`
   - `Read source`
   - `Load master`
   - `Transform`
   - `Build output`
   - `Write output`
5. Isi method yang saat ini placeholder:
   - `_reset_progress_state`
   - `_apply_progress_update`
6. Pastikan selama proses berjalan:
   - `Execute` disabled
   - progress tampil bergerak sesuai event pipeline
   - step yang sedang aktif terlihat berbeda
7. Pastikan setelah sukses atau gagal:
   - progress berhenti di state terminal yang sesuai
   - hint dan result card ikut berubah

### Mapping teknis yang disarankan

Gunakan widget seperti:

- `CTkProgressBar` untuk progress utama
- satu atau beberapa `StringVar` untuk text status progress
- satu `CTkTextbox` read-only atau beberapa `CTkLabel` untuk step list

### Implementasi state mapping yang disarankan

Buat fungsi/helper internal yang menggabungkan state dari beberapa sumber:

- `self.status_var`
- `self._preflight_thread`
- `self._worker_thread`
- `self._preflight_result`

Contoh state resolusi:

- jika worker aktif: `running`
- jika preflight aktif: `checking`
- jika status sukses: `success`
- jika status gagal: `failed`
- jika preflight blocked: `blocked`
- jika preflight ready dan execute bisa jalan: `ready`
- sisanya: `idle`

### Acceptance criteria

- user bisa memahami status aplikasi tanpa harus membaca log
- progress bar dan step list bergerak sesuai proses
- state visual sinkron dengan behavior tombol `Execute` dan `Start New Session`

## Tahap 5: Redesign Result Panel dan Log Panel

### Tujuan

Membuat area hasil dan log lebih mirip prototype dan lebih mudah dipindai.

### Tugas untuk result panel

1. Ubah result area agar lebih menyerupai success/output panel di JSX.
2. Tampilkan status akhir secara tegas.
3. Tampilkan target output / output terakhir dengan wrapping yang rapi.
4. Pertahankan `job_summary_var`, tetapi susun layout sehingga summary tidak terasa seperti blok teks acak.
5. Pastikan tombol:
   - `Buka Folder Outputs`
   - `Start New Session`
   tetap mudah ditemukan.

### Tugas untuk log panel

1. Ubah container log menjadi panel gelap.
2. Tambahkan header panel log yang terasa seperti terminal/proses monitor.
3. Pastikan `self.log_box` tetap read-only.
4. Jika perlu, gunakan font monospace agar log mudah dipindai.
5. Jangan mengubah format sanitasi log yang sudah ada di `_append_log`.

### Acceptance criteria

- hasil akhir sukses/gagal mudah dibaca
- log tetap dominan di area kanan
- path panjang masih terbaca dan tidak memecah layout parah

## Tahap 6: Redesign Dialog Job Settings

### Tujuan

Menyelaraskan dialog `Job Settings` dengan brief dan prototype JSX.

### Tugas

1. Refactor `JobSettingsDialog._build_layout` menjadi dua area besar:
   - sidebar daftar job
   - panel form editor
2. Sidebar job list perlu memuat:
   - judul daftar job
   - selector/list job
   - tombol `Job Baru`
3. Form editor perlu memuat:
   - nama job
   - pilihan config
   - toggle aktif/nonaktif
   - preview master file
   - tombol simpan
4. Perjelas status job valid/invalid di area yang mudah terlihat.
5. Jika `CTkOptionMenu` untuk daftar job terasa terlalu terbatas, pertimbangkan mengganti daftar job menjadi tumpukan button selectable. Hanya lakukan ini jika wiring state tetap sederhana.
6. Pertahankan semua logic existing pada:
   - `refresh`
   - `_populate_form`
   - `_refresh_master_preview`
   - `_save_job`

### Catatan implementasi

- Jangan mengubah format penyimpanan job profile.
- Jangan menambah fitur manajemen job yang belum diminta, misalnya delete job, import/export config, atau edit YAML langsung.

### Acceptance criteria

- dialog tetap bisa dipakai penuh untuk membuat dan mengedit job
- preview master file tetap akurat
- tampilan lebih rapi dan mudah dipahami dibanding versi sekarang

## Rencana Eksekusi Teknis yang Direkomendasikan

Urutan commit internal atau unit kerja yang disarankan:

1. Refactor ringan layout builder tanpa mengubah behavior.
2. Main window visual redesign.
3. Progress widget dan state badge.
4. Result panel dan log panel redesign.
5. Job settings dialog redesign.
6. Test adjustment dan polish.

Jika dikerjakan oleh junior dev, sangat disarankan membuat PR kecil per tahap, bukan satu perubahan besar sekaligus.

## Daftar Widget dan State yang Sebaiknya Dijaga Stabil

Reference existing yang sebaiknya tetap dipertahankan agar logic lain tidak rusak:

- `self.source_var`
- `self.selected_job_var`
- `self.job_info_var`
- `self.primary_hint_var`
- `self.execute_hint_var`
- `self.preflight_status_var`
- `self.preflight_summary_var`
- `self.status_var`
- `self.last_output_var`
- `self.job_summary_var`
- `self.execute_button`
- `self.start_new_session_button`
- `self.job_menu`
- `self.source_drop_label`
- `self.log_box`

Jika perlu menambah widget baru, lakukan tanpa mengganti kontrak internal existing kecuali memang diperlukan.

## Risiko Implementasi dan Mitigasi

### Risiko 1: Layout jadi lebih bagus tetapi logic state tidak sinkron

Mitigasi:

- jangan buat state visual terpisah yang tidak disinkronkan dengan state runtime
- buat helper resolver satu pintu untuk state badge

### Risiko 2: Refactor `_build_layout` memutus reference widget yang dipakai method lain

Mitigasi:

- cari semua penggunaan atribut `self.<widget>` sebelum rename atau hapus
- pertahankan nama reference penting

### Risiko 3: Progress UI ditambahkan tetapi event pipeline tidak dimapping dengan benar

Mitigasi:

- audit bentuk `PipelineStepStatus` dan titik pemanggilan `_apply_progress_update`
- mulai dari implementasi paling sederhana: progress label + progress bar + satu daftar step

### Risiko 4: Dialog settings jadi terlalu rumit untuk `customtkinter`

Mitigasi:

- prioritaskan layout yang rapi, bukan widget custom berlebihan
- gunakan `CTkFrame`, `CTkLabel`, `CTkTextbox`, `CTkButton`, `CTkOptionMenu`, `CTkCheckBox` secara konsisten

### Risiko 5: Test lama gagal karena coupling ke widget tertentu

Mitigasi:

- jalankan `tests/test_main_window.py`
- revisi test hanya jika behavior tetap benar tetapi representasi UI berubah

## Checklist Implementasi Detail

### Main window

- header baru dibuat
- panel kiri dipecah menjadi card yang jelas
- source card menonjol
- job card rapi dan informatif
- preflight tampil lebih jelas
- execute card menjadi fokus utama
- progress bar tampil
- step list tampil
- result card jelas
- log panel gelap dan dominan

### State dan behavior

- idle terlihat berbeda dari ready
- blocked terlihat berbeda dari failed
- running terlihat berbeda dari checking
- execute hanya aktif saat valid
- start new session hanya aktif di state terminal
- hint tetap konsisten

### Job settings dialog

- daftar job jelas
- form job jelas
- config selector jelas
- toggle aktif jelas
- preview master tetap bekerja
- tombol simpan tetap berfungsi

### QA manual

- pilih source valid
- pilih source invalid
- drag-and-drop satu file valid
- drag-and-drop banyak file
- ganti job saat source sudah dipilih
- preflight ready
- preflight blocked
- execute sukses
- execute gagal
- buka folder outputs
- start new session
- buka dialog settings dan simpan job

## Saran Pembagian Tugas untuk Junior Dev

Jika dikerjakan oleh satu junior dev, gunakan urutan kerja ini:

1. Rapikan `DesktopApp._build_layout` menjadi beberapa builder method.
2. Implementasikan header dan card layout main window.
3. Tambahkan progress widget dan state badge.
4. Rapikan result panel dan log panel.
5. Redesign `JobSettingsDialog`.
6. Jalankan dan perbaiki test.
7. Lakukan QA manual berdasarkan checklist.

Jika dikerjakan oleh AI model lain, prompt lanjutan yang disarankan adalah:

`Implement tahap 2 dan 3 pada redesign-gui.md di app/ui/main_window.py tanpa mengubah flow bisnis. Gunakan apply_patch, pertahankan widget references existing, lalu jalankan test terkait main window.`

## Definition of Done

Redesign dianggap selesai jika semua kondisi berikut terpenuhi:

- main window secara visual jelas lebih modern dan sejalan dengan `desain-ui.jsx`
- brief di `design-gui-brief.md` tercermin pada layar utama
- semua state penting terlihat berbeda secara visual
- progress proses terlihat jelas di UI
- `Job Settings` dialog lebih rapi dan mudah dipahami
- flow existing tetap bekerja
- test terkait UI tetap lulus atau diperbarui secara tepat
- tidak ada fitur baru yang menyimpang dari ruang lingkup redesign

## Rekomendasi Implementasi Praktis

Pendekatan terbaik adalah mulai dari redesign `main window` terlebih dahulu, lalu `Job Settings` dialog setelah struktur utama stabil.

Alasannya:

- dampak ke user paling besar ada di layar utama
- risiko regressi lebih mudah dikontrol
- progress dan state visual bisa divalidasi lebih awal
- dialog settings bisa mengikuti visual language yang sudah matang dari layar utama

Dengan urutan ini, hasil redesign akan lebih konsisten dan lebih aman untuk diintegrasikan ke codebase yang sudah berjalan.
