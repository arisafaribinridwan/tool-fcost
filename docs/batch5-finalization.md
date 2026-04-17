# Finalisasi Batch 5

Dokumen ini merangkum temuan lengkap untuk update terbaru pada workbook referensi:

- `sub-15` add `action`
- `sub-16` add `defect_category`

Status saat ini:

- sumber evidence sudah cukup untuk memetakan gap
- `sub-15` sudah cukup jelas arah implementasinya
- `sub-16` belum cukup jelas untuk dikunci implementasinya tanpa keputusan tambahan

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

### Tingkat Kejelasan

`sub-15` dinilai cukup jelas untuk mulai diimplementasikan.

Yang masih perlu diputuskan hanya detail teknis kecil:

- apakah matching `repair_comment` bersifat substring atau exact setelah normalisasi
- apakah matching case-insensitive
- apa output default jika tidak ada rule yang cocok: kosong atau `N/A`

Default aman yang direkomendasikan:

- normalisasi trim
- case-insensitive
- first match wins
- jika tidak ada match, biarkan kosong

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

### Ambiguitas Utama

Workbook proses hanya mengatakan:

- tambah kolom `defect_category`
- isi berdasarkan master sheet `defect_category`

Namun master yang tersedia tidak punya kolom bernama `defect_category`.

Sebaliknya, master ini menyediakan tiga kandidat output turunan:

- `Category`
- `Defect`
- `Code`

Karena itu, nama target `defect_category` belum cukup untuk menentukan implementasi yang benar.

### Interpretasi Yang Mungkin

Ada beberapa kemungkinan arti `defect_category`:

1. `defect_category` = nilai kolom `Category`
2. `defect_category` = nilai kolom `Defect`
3. `defect_category` = gabungan `Category` + `Defect`
4. `defect_category` = label bisnis turunan yang belum tertulis eksplisit di master

Dari nama kolom target saja, kemungkinan 1 dan 2 sama-sama masuk akal.

### Ketergantungan Yang Paling Logis

Master `defect_category` memakai kolom `Repair Action` sebagai input.

Ini memberi indikasi kuat bahwa:

- `sub-16` kemungkinan besar bergantung pada hasil `sub-15`
- `action` perlu terlebih dahulu dinormalisasi atau dipetakan ke label bisnis seperti `Replace Panel`, `Factory Reset`, `External`, `Cancel`

Masalahnya, label hasil master `action` saat ini memakai gaya snake_case / lowercase:

- `replace_power_unit`
- `replace_panel`
- `replace_main_unit`
- `factory_reset`
- `external`
- `cancel`

Sedangkan master `defect_category` memakai gaya Title Case:

- `Replace Power Unit`
- `Replace Panel`
- `Replace Main Unit`
- `Factory Reset`
- `External`
- `Cancel`

Artinya ada gap kontrak antar master:

- belum jelas apakah `sub-15` harus menghasilkan label final Title Case
- atau ada normalisasi tambahan dari `action` ke `Repair Action`
- atau sheet `action` sendiri belum final

### Tingkat Kejelasan

`sub-16` belum aman untuk dikunci implementasinya.

Blokernya ada dua:

1. output mana yang harus diisikan ke kolom `defect_category`
2. bagaimana memetakan hasil `sub-15` ke key `Repair Action`

## Evidence Dari Sample Output

Pada `example/result.xlsx` sheet `result`, header row sudah menyiapkan kolom:

- `AF1 = action`
- `AG1 = defect_category`

Namun pada beberapa row sample yang diperiksa:

- nilai `action` masih kosong
- nilai `defect_category` masih kosong

Ini berarti sample output belum bisa dipakai sebagai bukti final untuk perilaku batch 5.

Sebaliknya, sample output hanya mengonfirmasi bahwa:

- kolom target memang direncanakan ada
- implementasi/isi finalnya belum dipastikan di sample tersebut

## Temuan Pada Kode Repo Saat Ini

### Engine Transformasi Belum Mendukung Batch 5

Implementasi di `app/services/transform_service.py` saat ini masih berbasis:

- lookup master generik dengan satu `key`
- merge `m:1`
- penambahan kolom dari hasil join langsung

Ini belum cukup untuk batch 5 karena:

- `sub-15` butuh rule engine ordered matching
- `sub-15` bukan merge satu key
- `sub-16` kemungkinan butuh mapping lanjutan dari hasil `action`
- pembacaan master `.xlsx` saat ini juga belum dibangun eksplisit untuk memilih sheet tertentu pada config master generik

### Schema Config Belum Mewadahi Rule Batch 5

Validasi config di `app/services/config_service.py` saat ini baru mengenal field:

- `file`
- `key`
- `columns`

Belum ada bentuk schema untuk:

- `sheet_name`
- rule top-to-bottom
- multi-source input
- wildcard/substring matching
- first-match-wins
- output turunan dari beberapa kolom master

### Test Coverage Belum Menyentuh Batch 5

Test suite saat ini masih lolos penuh pada baseline repo, tetapi belum ada coverage untuk:

- rule `action`
- mapping `defect_category`
- pembacaan sheet master batch 5

## Ringkasan Gap Yang Sudah Pasti

### Sudah pasti

- workbook proses memang menambah `sub-15` dan `sub-16`
- master workbook memang menambah sheet `action` dan `defect_category`
- repo saat ini belum mengimplementasikan batch 5
- repo saat ini belum mendokumentasikan batch 5
- sample output belum memberi bukti final nilai hasil batch 5

### Sudah cukup jelas untuk coding

- `sub-15` membutuhkan rule engine berbasis `part_name` dan `repair_comment`

### Belum cukup jelas untuk coding aman

- definisi final kolom `defect_category`
- kontrak antara output `action` dan key `Repair Action`

## Rekomendasi Keputusan Sebelum Implementasi

Sebelum batch 5 diimplementasikan, keputusan berikut perlu dikunci:

1. `sub-15`

- apakah `repair_comment` di-match sebagai substring case-insensitive
- apakah `*` di awal/akhir dianggap wildcard
- apa nilai default jika tidak match
- apakah output `action` final mengikuti snake_case atau Title Case

2. `sub-16`

- apakah `defect_category` harus diisi dari `Category`, `Defect`, atau bentuk gabungan
- apakah kolom `Code` juga perlu disimpan di masa depan
- apakah input lookup memakai hasil `action` apa adanya atau label `Repair Action` yang sudah dinormalisasi

## Rekomendasi Arah Implementasi

Jika ingin meminimalkan rework, urutan kerja yang direkomendasikan adalah:

1. Kunci spesifikasi `sub-15`
2. Kunci arti final `defect_category`
3. Tambahkan dokumen final batch 5 yang mengikat kontrak rule
4. Baru implementasikan engine rule dan test

## Kesimpulan

Batch 5 sudah nyata di workbook referensi, tetapi belum siap langsung diimplementasikan penuh tanpa keputusan tambahan.

Status final per sub-task:

- `sub-15` hampir siap dikunci
- `sub-16` masih ambigu

Dengan kondisi evidence saat ini, tindakan paling aman adalah:

- dokumentasikan temuan lebih dulu
- kunci kontrak `sub-16`
- baru lanjut ke coding dan test
