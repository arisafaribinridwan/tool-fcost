# Flow Pengaturan Job

Dokumen ini menjelaskan flow, logic, state, dan constraint pada halaman `Pengaturan Job` yang saat ini diimplementasikan di `JobSettingsDialog` pada `app/ui/main_window.py`.

Tujuan dokumen ini adalah memberi konteks yang cukup untuk UI/UX designer agar bisa me-define ulang tampilan dan interaksi, tanpa kehilangan behavior inti yang sudah berjalan di aplikasi.

## 1. Tujuan Halaman

Halaman `Pengaturan Job` dipakai untuk:

- melihat daftar job yang sudah terdaftar
- membuat job baru
- mengubah job existing
- memilih config yang dipakai oleh job
- mengaktifkan atau menonaktifkan job
- melihat preview file master yang dipakai oleh config/job tersebut

Secara konsep, satu `job` adalah preset kerja yang menghubungkan:

- nama job
- file config YAML
- status aktif/nonaktif

Data job disimpan ke:

- `configs/job_profiles.yaml`

## 2. Struktur Layout Saat Ini

Dialog dibuka sebagai modal popup dari halaman utama.

Karakter layout sekarang:

- ukuran awal `760x520`
- minimum size `700x480`
- modal terhadap parent window
- 2 panel horizontal

### Panel kiri

Fungsi panel kiri:

- memilih job dari daftar
- memulai form kosong untuk job baru
- menampilkan status singkat job

Komponen saat ini:

- judul `Daftar Job`
- dropdown daftar job
- tombol `Job Baru`
- label `Status Job`
- teks status dinamis

### Panel kanan

Fungsi panel kanan:

- form edit data job
- preview config dan master
- aksi simpan

Komponen saat ini:

- judul `Form Job`
- input `Nama Job`
- dropdown `Config`
- checkbox `Aktifkan job ini`
- area preview `Master yang digunakan`
- tombol `Simpan Job`

## 3. Entity dan Data yang Terlibat

Halaman ini bekerja dengan dua entity utama.

### A. Config

Sumber data:

- file YAML di folder `configs/`

Yang dipakai UI:

- nama file config
- valid/tidak valid
- daftar error jika config invalid
- daftar file master yang direferensikan config

Designer perlu tahu:

- hanya config yang valid yang masuk ke dropdown config
- config invalid tidak bisa dipilih di form

### B. Job Profile

Sumber data:

- `configs/job_profiles.yaml`

Field inti:

- `id`
- `label`
- `config_file`
- `enabled`

Yang dipakai UI:

- label job untuk dropdown
- status valid/tidak valid
- error ringkas jika invalid
- file master yang terkait

Designer perlu tahu:

- job bisa ada tapi dianggap invalid
- job invalid tetap tampil di registry internal, tapi hanya job valid yang bisa dipakai di halaman utama
- di halaman pengaturan, daftar job tetap bisa dimuat agar user bisa melihat/memperbaiki isinya

## 4. Flow Utama

## 4.1. Saat dialog dibuka

Urutan logic:

1. dialog dibuat sebagai modal
2. layout 2 panel dibangun
3. method `refresh()` dipanggil
4. sistem membaca seluruh config valid dari folder `configs/`
5. sistem membaca seluruh job profile dari `job_profiles.yaml`
6. dropdown kiri dan dropdown config diisi ulang
7. form ditentukan berdasarkan state saat ini:
   - jika belum ada job aktif, masuk mode `Job baru`
   - jika ada job terpilih dan masih tersedia, form diisi data job tersebut

Implikasi desain:

- halaman tidak punya loading state eksplisit
- semua state awal ditentukan oleh hasil `refresh()`
- screen sebenarnya punya dua mode utama: `create` dan `edit`

## 4.2. Flow mode `Job baru`

Terjadi ketika:

- dialog baru dibuka dan belum ada job aktif
- user memilih opsi `Job baru`
- user menekan tombol `Job Baru`
- job yang sebelumnya terpilih tidak lagi tersedia

Behavior:

- `selected_job_id = None`
- dropdown kiri diset ke `Job baru` jika perlu
- field `Nama Job` dikosongkan
- dropdown `Config` otomatis memilih config valid pertama jika ada
- checkbox `enabled` di-set `True`
- status menampilkan pesan: `Isi nama job dan pilih config.`
- preview master diperbarui berdasarkan config yang sedang terpilih

Implikasi desain:

- mode create saat ini tidak benar-benar kosong total, karena config bisa auto-terpilih
- preview master langsung muncul bahkan sebelum job disimpan, selama config valid tersedia

## 4.3. Flow memilih job existing

Terjadi ketika user memilih item selain `Job baru` dari dropdown kiri.

Behavior:

1. sistem mencari job berdasarkan label
2. jika job ditemukan:
   - `selected_job_id` diisi dengan id job
   - nama job masuk ke field input
   - config job dipilih di dropdown
   - status enabled disesuaikan
   - status teks diperbarui
   - preview master diperbarui
3. jika job tidak ditemukan:
   - form di-reset ke mode `Job baru`

Status yang mungkin:

- `Job valid dan siap dipakai.`
- `Job invalid: ...`

Catatan penting:

- validity job bukan cuma ditentukan oleh field job profile
- job bisa invalid karena file config tidak ada, config invalid, atau payload config gagal dibaca

Implikasi desain:

- designer sebaiknya memisahkan dengan jelas state `selected`, `editable`, dan `invalid`
- invalid state sebaiknya lebih terlihat daripada sekarang, karena saat ini hanya berupa teks

## 4.4. Flow mengganti config

Terjadi ketika user mengganti dropdown `Config`.

Behavior:

- tidak ada autosave
- tidak ada validasi berat langsung ke form
- sistem hanya me-refresh preview master

Sumber preview:

- jika ada job valid yang memakai config itu, preview master bisa mengambil `master_files` dari job summary
- jika tidak ada job valid yang cocok, sistem membaca payload config langsung dan mengekstrak file master dari:
  - root `masters`
  - `steps[].master.file`

Fallback state:

- jika config tidak valid atau tidak ada, preview menampilkan pesan error
- jika config tidak mereferensikan master, preview menampilkan pesan kosong terstruktur

Implikasi desain:

- area preview saat ini berperan sebagai feedback instan saat config berubah
- preview ini sebetulnya penting karena membantu user memahami konsekuensi pemilihan config

## 4.5. Flow simpan job

Terjadi saat user menekan tombol `Simpan Job`.

Behavior:

1. UI mengirim nilai form ke `upsert_job_profile_record()`
2. field yang dikirim:
   - `label`
   - `config_file`
   - `enabled`
   - `record_id` jika sedang edit job existing
3. jika validasi gagal:
   - muncul modal error
   - dialog tetap terbuka
   - data form tidak hilang
4. jika sukses:
   - parent window me-refresh daftar job
   - `selected_job_id` diperbarui dengan record hasil simpan
   - dropdown kiri diarahkan ke label job hasil simpan
   - status menjadi `Job berhasil disimpan.`
   - dialog `refresh()` ulang
   - log parent ditambah
   - muncul modal sukses

Implikasi desain:

- save saat ini bersifat blocking dan eksplisit
- tidak ada autosave
- user mendapat 2 feedback sukses:
  - status text di dialog
  - modal sukses

Designer bisa mempertimbangkan apakah kedua feedback ini masih perlu, atau cukup satu feedback utama yang lebih rapi.

## 5. Validasi dan Aturan Data

Aturan ini penting untuk dipertahankan walau UI berubah.

### 5.1. Validasi minimal saat save

`upsert_job_profile_record()` akan menolak save jika:

- nama job kosong
- config belum dipilih / kosong
- nama job duplikat dengan job lain

Pesan error saat ini langsung dilempar sebagai `ValueError` lalu ditampilkan ke modal error.

### 5.2. Aturan ID job

ID job:

- dibuat dari slug nama job
- huruf kecil
- karakter non-alfanumerik diganti `-`
- jika kosong, fallback ke `job`
- jika bentrok, akan diberi suffix `-2`, `-3`, dst

Implikasi desain:

- user saat ini tidak melihat atau mengedit `id`
- `id` adalah sistem field, bukan field presentasional

### 5.3. Validitas job

Job dianggap valid hanya jika:

- `enabled = True`
- config yang dirujuk ada
- config yang dirujuk valid
- payload config bisa dibaca tanpa error

Artinya:

- job disabled otomatis dianggap tidak valid untuk flow utama
- job yang disabled tetap bisa disimpan dan tetap muncul di pengaturan

Implikasi desain:

- toggle enable/disable bukan sekadar preferensi visual
- toggle ini mempengaruhi apakah job bisa dipakai di main workflow

## 6. Logic Preview Master

Preview `Master yang digunakan` adalah bagian paling informatif di halaman ini.

Current logic:

- jika ada `preferred` list, tampilkan itu
- jika tidak ada:
  - ambil config yang sedang dipilih
  - coba cari job valid lain yang memakai config tersebut
  - jika ada, pakai `master_files` yang sudah diringkas
  - jika tidak ada, parse config YAML langsung

Hasil preview bisa berupa:

- daftar nama file master
- pesan `Belum ada config valid untuk dipilih.`
- pesan `Config ini tidak mereferensikan file master.`
- pesan `Gagal membaca config: ...`

Implikasi desain:

- preview ini sebenarnya bukan field pasif
- preview adalah assistive explanation untuk mengurangi salah pilih config

## 7. State yang Perlu Dikenali Designer

Minimal ada state-state berikut saat redesign:

- default opening state
- create new job
- edit existing valid job
- edit existing invalid job
- no valid config available
- config selected but no master references
- config parse error
- save success
- save error

Kalau ingin lebih matang, bisa juga dibedakan:

- empty registry state
- duplicate-name validation state
- disabled job state

## 8. Pain Point UX dari Implementasi Saat Ini

Beberapa hal yang kemungkinan terasa kurang ideal dari sisi UX:

- mode create dan edit belum dibedakan secara visual
- status job hanya berupa teks, belum berupa badge/alert yang jelas
- preview master cukup penting, tapi belum diposisikan sebagai informasi utama
- save memakai popup sukses dan popup error, sehingga interaksi terasa agak berat
- daftar job hanya berupa dropdown, sehingga kurang nyaman jika jumlah job banyak
- belum ada affordance untuk search, duplicate, delete, atau filter enabled/disabled
- invalid job belum memiliki treatment visual yang kuat
- user tidak diberi ringkasan perubahan sebelum simpan

## 9. Constraint Fungsional yang Sebaiknya Dipertahankan

Saat UI di-redesign, behavior berikut sebaiknya tetap ada:

- ada cara untuk masuk ke mode `job baru`
- ada cara untuk memilih dan mengedit job existing
- config hanya boleh dipilih dari config valid
- enabled/disabled tetap menjadi field inti
- preview master tetap tersedia sebelum save
- save harus tetap melakukan validasi nama job dan config
- feedback error save harus tetap jelas dan spesifik
- setelah save, parent/main screen harus ikut refresh

## 10. Peluang Redefinisi untuk Designer

Designer cukup aman untuk mengubah:

- layout dua kolom menjadi master-detail, list-detail, wizard, atau drawer
- dropdown daftar job menjadi list, cards, table, atau searchable sidebar
- preview master menjadi card, accordion, chips, atau structured table
- status job menjadi badge, alert banner, inline validation, atau summary panel
- feedback sukses/error dari modal ke inline feedback

Designer perlu hati-hati agar tidak menghilangkan:

- distinction antara create vs edit
- visibility atas invalid state
- dependency antara job dan config
- visibility atas file master yang dipakai
- efek enable/disable terhadap validitas job

## 11. Rekomendasi Bahasa UX yang Lebih Eksplisit

Beberapa konsep yang saat ini implicit, tapi sebaiknya dibuat lebih jelas di desain baru:

- `Job` = preset / template kerja
- `Config` = aturan transformasi yang dipakai job
- `Master` = file referensi yang dibutuhkan config
- `Enabled` = job tersedia dipakai di halaman utama

Kalau designer ingin memperjelas mental model, istilah berikut bisa dipertimbangkan:

- `Job` menjadi `Template Proses` atau `Preset Pekerjaan`
- `Config` menjadi `Aturan Proses`
- `Master yang digunakan` menjadi `File referensi yang akan dipakai`

## 12. Ringkasan Flow Singkat

Flow singkat halaman saat ini:

1. user membuka `Pengaturan Job`
2. sistem memuat config valid dan registry job
3. user memilih salah satu:
   - job baru
   - job existing
4. user mengisi / mengubah:
   - nama job
   - config
   - status aktif
5. sistem menampilkan preview file master berdasarkan config
6. user menekan `Simpan Job`
7. sistem validasi dan menulis ke `job_profiles.yaml`
8. parent screen di-refresh agar daftar job utama ikut update

## 13. Referensi Kode

Sumber utama behavior:

- `app/ui/main_window.py`
- `app/services/job_profile_service.py`
- `app/services/config_service.py`

Method utama yang relevan:

- `JobSettingsDialog.__init__`
- `JobSettingsDialog._build_layout`
- `JobSettingsDialog.refresh`
- `JobSettingsDialog._reset_form`
- `JobSettingsDialog._populate_form`
- `JobSettingsDialog._on_job_selected`
- `JobSettingsDialog._on_config_selected`
- `JobSettingsDialog._refresh_master_preview`
- `JobSettingsDialog._save_job`
- `upsert_job_profile_record`
- `discover_job_profiles`

