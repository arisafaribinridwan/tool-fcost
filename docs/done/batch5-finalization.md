# Finalisasi Batch 5

Dokumen ini merangkum temuan lengkap untuk update terbaru pada workbook referensi:

- `sub-15` add `action`
- `sub-16` add `defect_category`
- `sub-17` add `defect` (ekstensi repo, belum tertulis di workbook proses)

Status saat ini:

- sumber evidence sudah cukup untuk memetakan gap
- `sub-15` sudah diimplementasikan di repo
- `sub-16` sudah dikunci implementasinya di repo
- `sub-17` sudah dikunci implementasinya di repo

## Catatan Sinkronisasi Repo Terkini

Dokumen ini terkait dengan state repo terbaru karena dependensi `sub-15` sampai `sub-17` sekarang berjalan di atas fondasi berikut:

- selector UI utama sudah memakai `Pekerjaan` dari registry `configs/job_profiles.yaml`
- path runtime `configs/`, `masters/`, dan output sudah di-hardening
- sheet `symptom` sudah memakai rule table baru dengan dukungan `regex`, `priority`, dan fail-fast validation

Catatan ini tidak mengubah kontrak batch 5, tetapi penting agar pembaca tidak mengira repo masih berada pada state sebelum fondasi fase 1 selesai.

## Sumber Evidence

Temuan di dokumen ini diturunkan dari file berikut:

- `example/Auto Monthly Report.xlsx`
- `example/master_table.xlsx`
- `example/result.xlsx`
- implementasi repo saat ini di folder `app/services/`
- test suite repo saat ini di folder `tests/`

## Evidence Dari Workbook Proses

Pada `example/Auto Monthly Report.xlsx` ditemukan update utama berikut:

- `Sheet1!C23` = `sub15 - add column "action"`
- `Sheet1!C24` = `sub16 - add column "defect_category"`

Belum ditemukan entry workbook untuk `sub-17`.

`sub-17` di dokumen ini dicatat sebagai keputusan implementasi repo tambahan berdasarkan kebutuhan lanjutan:

- lookup dari kolom `action`
- baca master sheet `defect_category`
- ambil nilai kolom `Defect`
- tulis ke kolom `defect`

Rincian sub-step di sheet `sub_function`:

### `sub-15`

- `A90:C93`
- baca `result.xlsx`
- notifikasi mulai proses data `action`
- buat kolom baru `action`
- isi value mengikuti aturan master tabel sheet `action`

### `sub-16`

- `A94:C97`
- baca `result.xlsx`
- notifikasi mulai proses data `defect category`
- buat kolom baru `defect_category`
- isi value mengikuti aturan master tabel sheet `defect_category`

## Evidence Dari Master Workbook

Pada `example/master_table.xlsx`, workbook master sudah memiliki sheet tambahan berikut:

- `action`
- `defect_category`

Ini berarti update batch 5 memang sudah tercermin di master referensi, bukan hanya catatan di flow workbook.

## Temuan Sub-15

### Struktur Master `action`

Sheet `action` berisi 3 kolom:

| kolom master | arti dugaan |
|---|---|
| `part_name` | filter part opsional |
| `repair_comment` | pattern pencarian |
| `action` | hasil akhir |

Contoh isi master:

| part_name | repair_comment | action |
|---|---|---|
| kosong | `*ext` | `external` |
| kosong | `BATAL` | `cancel` |
| `POWER_UNIT` | `*` | `replace_power_unit` |
| `PANEL` | `*` | `replace_panel` |
| `MAIN_UNIT` | `*` | `replace_main_unit` |
| `Remote Control` | `*` | `replace_remote_control` |
| kosong | `*bawa` | `ZY` |
| kosong | `ZY` | `ZY` |
| kosong | `UPGRADE` | `upgrade` |
| kosong | `*factor` | `factory_reset` |
| kosong | `JELAS` | `explanation` |

### Interpretasi Rule Yang Paling Masuk Akal

Master `action` tidak cocok diperlakukan sebagai lookup satu key.

Bentuk rule yang paling konsisten dengan isi master adalah:

1. Ambil `part_name` hasil step sebelumnya
2. Ambil `repair_comment`
3. Scan rule master dari atas ke bawah
4. Jika `part_name` di master terisi, maka row hanya boleh match jika `part_name` sama
5. `repair_comment` di master diperlakukan sebagai pattern
6. Rule pertama yang cocok menjadi nilai `action`

### Semantik Pattern Yang Diduga

Berdasarkan isi master, pattern `repair_comment` paling masuk akal dibaca seperti ini:

- `*` berarti wildcard penuh
- `*ext` berarti substring atau suffix match ke teks yang memuat `ext`
- `*bawa` berarti substring atau suffix match ke teks yang memuat `bawa`
- `*factor` berarti substring atau suffix match ke teks yang memuat `factor`
- string biasa seperti `BATAL`, `UPGRADE`, `ZY`, `JELAS` berarti substring match case-insensitive atau exact normalized match

### Ketergantungan Data

`sub-15` bergantung minimal pada:

- kolom `part_name`
- kolom `repair_comment`

Artinya implementasi batch 5 tidak bisa berdiri sendiri; ia harus dijalankan setelah step yang menghasilkan `part_name`.

### Kontrak Final `sub-15`

Implementasi repo untuk `sub-15` dikunci dengan kontrak berikut:

- master dibaca dari sheet `action`
- rule dievaluasi dari atas ke bawah
- `part_name` di-match dengan normalisasi trim + case-insensitive equality
- `repair_comment` di-match dengan normalisasi trim + case-insensitive contains
- karakter `*` pada pattern `repair_comment` diperlakukan sebagai wildcard ringan dan diabaikan saat pencarian token
- field master yang kosong diperlakukan sebagai wildcard
- first match wins
- jika tidak ada rule yang cocok, nilai `action` dibiarkan kosong

Implementasi ini sejalan dengan evidence workbook dan cukup aman untuk kebutuhan batch 5 saat ini.

## Temuan Sub-16

### Struktur Master `defect_category`

Sheet `defect_category` berisi 4 kolom:

| kolom master | arti |
|---|---|
| `Repair Action` | input lookup/rule |
| `Category` | klasifikasi level 1 |
| `Defect` | klasifikasi level 2 |
| `Code` | kode numerik |

Contoh isi master:

| Repair Action | Category | Defect | Code |
|---|---|---|---|
| `Repair LVDS` | `Defect` | `Other` | `0` |
| `User` | `Non Defect` | `User` | `11` |
| `Setting` | `Non Defect` | `Setting` | `12` |
| `Explanation` | `Non Defect` | `Explanation` | `13` |
| `Signal` | `Non Defect` | `Signal` | `14` |
| `Replace Panel` | `Defect` | `Panel` | `20` |
| `Repair Panel` | `Defect` | `Panel` | `21` |
| `Replace Main Unit` | `Defect` | `Main Unit` | `30` |
| `Replace Power Unit` | `Defect` | `Power Unit` | `40` |
| `Factory Reset` | `Defect` | `Software` | `50` |
| `Upgrade` | `Defect` | `Software` | `51` |
| `Cancel` | `N/A` | `N/A` | `N/A` |
| `External` | `N/A` | `N/A` | `N/A` |

### Kontrak Final `sub-16`

Keputusan final untuk `sub-16` adalah:

- input lookup memakai kolom `action`
- master dibaca dari sheet `defect_category`
- key master yang dipakai adalah `Repair Action`
- hasil yang diambil adalah kolom `Category`
- hasil akhir ditulis ke kolom `defect_category`

Secara implementasi, `sub-16` diperlakukan sebagai lookup sederhana `vlookup` dengan normalisasi key ringan:

- trim whitespace
- case-insensitive
- abaikan spasi, underscore, dan karakter non-alphanumeric ringan

Dengan normalisasi ini, pasangan seperti berikut bisa match tanpa ubah data master:

- `replace_panel` -> `Replace Panel`
- `factory_reset` -> `Factory Reset`
- `replace_main_unit` -> `Replace Main Unit`
- `external` -> `External`

Jika tidak ada key yang cocok, nilai `defect_category` dibiarkan kosong.

### Catatan Kontrak Data

Ada satu mismatch data referensi yang ditangani dengan alias lookup eksplisit:

- `replace_remote_control` dari sheet `action`
- `Replace Remote` pada sheet `defect_category`

Alias ini dikunci di implementasi batch 5 agar row remote tetap menghasilkan `defect_category` yang sesuai tanpa harus menunggu perubahan master.

## Temuan Sub-17

### Kontrak Final `sub-17`

Keputusan final untuk `sub-17` adalah:

- input lookup memakai kolom `action`
- master dibaca dari sheet `defect_category`
- key master yang dipakai adalah `Repair Action`
- hasil yang diambil adalah kolom `Defect`
- hasil akhir ditulis ke kolom `defect`

Semantik lookup untuk `sub-17` mengikuti kontrak `sub-16`:

- trim whitespace
- case-insensitive
- abaikan spasi, underscore, dan karakter non-alphanumeric ringan
- gunakan alias eksplisit `replace_remote_control` -> `Replace Remote`

Jika tidak ada key yang cocok, nilai `defect` dibiarkan kosong.

## Evidence Dari Sample Output

Pada `example/result.xlsx` sheet `result`, header row sudah menyiapkan kolom:

- `AF1 = action`
- `AG1 = defect_category`

Belum ada header sample workbook yang membuktikan kolom `defect`, karena `sub-17` belum tertulis di workbook proses referensi.

Namun pada beberapa row sample yang diperiksa:

- nilai `action` masih kosong
- nilai `defect_category` masih kosong

Ini berarti sample output belum bisa dipakai sebagai bukti final untuk perilaku batch 5.

Sebaliknya, sample output hanya mengonfirmasi bahwa:

- kolom target memang direncanakan ada
- implementasi/isi finalnya belum dipastikan di sample tersebut

## Temuan Pada Kode Repo Saat Ini

### Engine Transformasi Sekarang Mendukung Batch 5

Implementasi di `app/services/transform_service.py` sekarang mendukung dua mode master:

- lookup generik berbasis `key` seperti sebelumnya
- `ordered_rules` untuk rule top-to-bottom berbasis beberapa kolom source

Tambahan perilaku yang sudah aktif:

- pembacaan `sheet_name` untuk file master `.xlsx`
- evaluasi multi-matcher dari atas ke bawah
- overwrite langsung ke kolom target seperti `action`
- lookup dengan `source_key` dan `master_key` berbeda
- normalisasi key lookup ringan untuk kasus `action` -> `Repair Action`
- rename kolom hasil lookup seperti `Category` -> `defect_category`
- alias lookup eksplisit untuk mismatch semantik tertentu

### Schema Config Sekarang Sudah Mewadahi Batch 5

Validasi config di `app/services/config_service.py` sekarang mendukung bentuk berikut untuk `sub-15`:

- `strategy: ordered_rules`
- `sheet_name`
- `target_column`
- `value_column`
- `matchers`

Setiap item `matchers` memakai:

- `source`
- `master`
- `mode`

Mode yang saat ini didukung:

- `equals`
- `contains`

Untuk `sub-16`, config lookup sekarang juga mendukung:

- `source_key`
- `master_key`
- `key_normalizer`
- `rename_columns`
- `key_aliases`

### Test Coverage Sudah Menyentuh Batch 5

Test suite sekarang sudah menambah coverage untuk:

- validasi schema `ordered_rules`
- rule `action`
- pembacaan sheet master `action`
- lookup `defect_category` dari `action`
- lookup `defect` dari `action`
- preserve nilai literal seperti `N/A` dari master

## Ringkasan Gap Yang Sudah Pasti

### Sudah pasti

- workbook proses memang menambah `sub-15` dan `sub-16`
- master workbook memang menambah sheet `action` dan `defect_category`
- repo saat ini sudah mengimplementasikan `sub-15`
- repo saat ini sudah mengimplementasikan `sub-16`
- sample output belum memberi bukti final nilai hasil batch 5

### Sudah cukup jelas untuk coding

- `sub-15` membutuhkan rule engine berbasis `part_name` dan `repair_comment`
- `sub-17` cukup memakai kontrak lookup yang sama dengan `sub-16`, tetapi mengambil kolom `Defect`

### Residual Risk Yang Masih Perlu Dipantau

- kemungkinan ada mismatch semantik lain antar sheet master yang belum muncul di sample data
- kemungkinan kebutuhan kolom turunan lain dari master `defect_category` seperti `Defect` atau `Code` di batch berikutnya

## Rekomendasi Arah Implementasi

Batch 5 sekarang sudah cukup stabil untuk dipakai.

Jika ingin melanjutkan refinement, urutan kerja yang direkomendasikan adalah:

1. Review apakah mismatch `replace_remote_control` perlu alias khusus
2. Putuskan apakah sheet `defect_category` nantinya juga perlu expose kolom `Defect` atau `Code`

## Kesimpulan

Batch 5 sudah nyata di workbook referensi dan sekarang sudah terimplementasi di repo.

Status final per sub-task:

- `sub-15` selesai diimplementasikan
- `sub-16` selesai diimplementasikan
- `sub-17` selesai diimplementasikan

Dengan kondisi evidence saat ini, tindakan paling aman berikutnya adalah memantau mismatch data lintas master dan menambah alias hanya jika memang dibutuhkan oleh data aktual.
