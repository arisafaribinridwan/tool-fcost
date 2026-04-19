# Finalisasi Batch 4

Dokumen ini mengunci review dan keputusan untuk batch 4:

- `sub-9` add `part_name`
- `sub-11` add `panel_usage`
- `sub-12` add `factory`
- `sub-13` add `symptom`
- `sub-14` normalize `branch`

Batch 4 memakai master lookup dan master rule dari file referensi, bukan hanya transformasi deterministic dari dataset `result`.

## Sumber Master Yang Tersedia

Berdasarkan `example/master_table.xlsx`, master yang relevan untuk batch 4 adalah:

- sheet `part_list`
- sheet `factory`
- sheet `symptom`
- sheet `panel_usage`
- sheet `branch`

## Ringkasan Finalisasi

### Sudah bisa dikunci penuh

- `sub-9` `part_name`
- `sub-11` `panel_usage`
- `sub-12` `factory`
- `sub-13` `symptom`
- `sub-14` `branch`

## Finalisasi Sub-9

### Tujuan

Mengisi kolom `part_name` dari nilai `part_used`.

### Sumber Master

- file master: `master_table.xlsx`
- sheet: `part_list`

### Struktur Master

| master column | arti |
|---|---|
| `part_used` | key lookup |
| `part_name` | hasil lookup |

### Rule Final

1. Ambil nilai `part_used` dari row `result`
2. Cari exact match ke kolom master `part_used`
3. Jika ketemu, isi `part_name` dari master
4. Jika `part_used` kosong, `part_name` dibiarkan kosong
5. Jika tidak ada di master, isi `part_name = "N/A"`

### Keputusan Implementasi

- Matching `part_used` dilakukan exact match setelah trim spasi di kiri dan kanan
- Hasil ditulis sebagai nilai statis final, bukan formula Excel
- Nama sheet master yang benar dari sample adalah `part_list`
- Teks workbook yang menyebut `Master Part List` dianggap alias bisnis dari master yang sama

### Bukti Sample

- Pada sample output, formula historis `part_name` mereferensikan sheet `[1]part_list`
- Master `part_list` di `example/master_table.xlsx` berisi pasangan `part_used -> part_name`

## Finalisasi Sub-11

### Tujuan

Mengisi kolom `panel_usage` berdasarkan integer `diff_month`.

### Sumber Master

- file master: `master_table.xlsx`
- sheet: `panel_usage`

### Struktur Master

| Diff Month | Panel Usage |
|---|---|
| `0-12` | `< 1 Year` |
| `13-24` | `1 - 2 Years` |
| `25-36` | `2 - 3 Years` |
| `=>37` | `> 3 Years` |

### Ketergantungan Dengan Batch 2

`sub-11` wajib memakai `diff_month` hasil final batch 2:

- nilai statis numerik
- integer
- dibulatkan dengan `ceil`

### Rule Final

Karena `diff_month` sudah integer:

```text
if diff_month <= 12:
    panel_usage = "< 1 Year"
elif diff_month <= 24:
    panel_usage = "1 - 2 Years"
elif diff_month <= 36:
    panel_usage = "2 - 3 Years"
else:
    panel_usage = "> 3 Years"
```

### Keputusan Implementasi

- Rule dieksekusi sebagai mapping range, bukan formula Excel
- Jika `diff_month` kosong, `panel_usage` dikosongkan
- Jika `diff_month` negatif, nilai tetap masuk bucket `<= 12`, yaitu `< 1 Year`, dan log memberi warning

### Catatan

- Sample output lama masih memakai `diff_month` pecahan, sehingga ada beberapa ketidakkonsistenan di batas `12.x`, `24.x`, `36.x`
- Keputusan final untuk sistem sekarang mengikuti `diff_month` integer hasil `ceil`

## Finalisasi Sub-12

### Tujuan

Mengisi kolom `factory` dari `model_name`.

### Sumber Master

- file master: `master_table.xlsx`
- sheet: `factory`

### Struktur Master

| master column | arti |
|---|---|
| `model_name` | key lookup |
| `factory` | hasil lookup |

### Rule Final

1. Ambil nilai `model_name`
2. Cari exact match ke master `factory.model_name`
3. Jika ketemu, isi kolom `factory`
4. Jika tidak ketemu, isi `factory = "N/A"`

### Keputusan Implementasi

- Matching dilakukan exact match setelah trim spasi
- Hasil ditulis sebagai nilai statis final
- Teks workbook yang menyebut sheet `master-factory` dianggap typo penamaan
- Nama sheet master yang benar dari sample adalah `factory`
- Teks workbook step 80 yang menulis “Buat kolom baru Panel Usage” juga typo; target yang benar adalah kolom `factory`

### Bukti Sample

Verifikasi terhadap `example/result.xlsx` dan `example/master_table.xlsx` menunjukkan:

- `2263/2263` row `factory` cocok exact dengan master `factory`

## Finalisasi Sub-13

### Tujuan

Mengisi kolom `symptom` berdasarkan kombinasi `part_name` dan `symptom_comment`.

### Sumber Master

- file master: `master_table.xlsx`
- sheet: `symptom`

### Struktur Master

| master column | arti |
|---|---|
| `part_name` | filter part yang relevan |
| `symptom_comment` | pattern pencarian |
| `symptom` | label hasil |

### Rule Engine Yang Dikunci

`sub-13` bukan exact lookup satu kolom. Rule ini adalah rule-based matching:

1. Ambil `part_name` dari row hasil `sub-9`
2. Ambil `symptom_comment`
3. Scan master `symptom` dari atas ke bawah
4. Pilih row master pertama yang cocok
5. Isi kolom `symptom` dengan nilai master `symptom`
6. Jika tidak ada rule yang cocok, biarkan `symptom` kosong

### Semantik Matching Yang Dikunci

#### `part_name`

- Exact match setelah normalisasi trim

#### `symptom_comment`

Kolom master `symptom_comment` diperlakukan sebagai pattern:

- `*` berarti wildcard: cocok untuk semua `symptom_comment`
- string biasa berarti substring match case-insensitive
- pattern dengan pemisah ` / ` berarti alternatif keyword

Contoh:

- `garis / line` cocok jika komentar mengandung `garis` atau `line`
- `STANDBY / STAND BY` cocok jika komentar mengandung `standby` atau `stand by`
- `SIGNAL / SINYAL` cocok jika komentar mengandung `signal` atau `sinyal`

### Contoh Rule Dari Master

- `POWER_UNIT` + `*` -> `TOTAL_OFF`
- `PANEL` + `garis / line` -> `LINE`
- `PANEL` + `TIDAK ADA GAMBAR` -> `BLANK`
- `MAIN_UNIT` + `MATI` -> `TOTAL_OFF`
- `MAIN_UNIT` + `HDMI` -> `HDMI_NG`
- `MAIN_UNIT` + `CHANNEL` -> `NO_CHANNEL`

### Keputusan Implementasi

- Evaluasi rule dilakukan top-to-bottom, first match wins
- Matching `symptom_comment` bersifat case-insensitive
- Jika `part_name` kosong, `symptom` dikosongkan
- Jika `symptom_comment` kosong, hanya rule wildcard `*` yang boleh match

### Catatan Penting

- Setelah review satu per satu terhadap `symptom-master-draft`, baseline master `symptom` untuk batch 4 dinyatakan terkunci
- Label hasil dikunci ke gaya uppercase dengan underscore
- Rule yang belum cukup jelas sengaja tidak dipaksa match; hasilnya dibiarkan kosong (`null`)
- Jika di masa depan ada penambahan rule, perubahan cukup dilakukan di master tanpa mengubah kode engine

### Update Kriteria Berdasarkan `result.xlsx`

Berdasarkan kolom `symptom` yang sudah dilengkapi pada `example/result.xlsx`, pola rule sudah cukup kuat untuk diperluas.

#### Rekomendasi Label Kanonik

Sebelum rule dikunci penuh di master, label hasil sebaiknya dinormalkan ke satu gaya penamaan.

Temuan inkonsistensi dari sample:

- `TOTAL_OFF` dan `total_off`
- `NO PICTURE` dan `NO_PICTURE`
- `DISPLAY NG` memakai spasi, sementara label lain banyak yang memakai underscore

Rekomendasi final:

- pakai uppercase dengan underscore untuk seluruh label

Contoh label kanonik:

- `TOTAL_OFF`
- `LINE`
- `BLANK`
- `STANDBY`
- `LOGO_FREEZE`
- `HDMI_NG`
- `NO_CHANNEL`
- `NO_PICTURE`
- `PICTURE_NG`
- `PROTECT`
- `SENSOR_NG`
- `SOUND_NG`
- `BLUR`
- `DOT`
- `DISPLAY_NG`
- `DARK`
- `BROKEN`
- `HALF`
- `SPOT`
- `BLINKING`
- `ERROR`

#### Rule Yang Dikunci

Rule di bawah ini adalah baseline criteria yang dikunci untuk master `symptom` batch 4 dan dieksekusi secara deterministic.

##### `POWER_UNIT`

- `*` -> `TOTAL_OFF`

##### `PANEL`

- mengandung `GARIS` atau `LINE` -> `LINE`
- mengandung `TIDAK ADA GAMBAR` -> `BLANK`
- mengandung `TDK ADA GAMBAR` -> `BLANK`
- mengandung `BLANK` -> `BLANK`
- mengandung `HANYA SUARA` -> `BLANK`
- mengandung `X ADA GAMBAR` -> `BLANK`
- mengandung `MATI`, `MATI TOTAL`, `TIDAK BISA HIDUP`, `TIDAK BS HIDUP` -> `TOTAL_OFF`
- mengandung `BERKEDIP`, `KEDIP` -> `BLINKING`
- mengandung `BERBAYANG`, `BAYANG`, `BURAM`, `BLUR`, `TIDAK JELAS` -> `BLUR`
- mengandung `PECAH` -> `BROKEN`
- mengandung `GELAP` -> `DARK`
- mengandung `PIXEL`, `DOT`, `BINTIK`, `VOLKADOT` -> `DOT`
- mengandung `BULATAN HITAM` -> `SPOT`
- mengandung `SETENGAH`, `SEBELAH` -> `HALF`
- mengandung `MERAH`, `BERMASALAH`, `BEMASALAH`, `DELAY`, `BLUE SCREEN`, `PUTIH`, `GOYANG`, `BERGERAK`, `KUALITAS GAMBAR`, `RUSAK PANEL`, `PANEL RUSAK`, `PESAN PANEL`, `GANTI PANEL`, `SLOW MOTION`, `UNGU` -> `DISPLAY_NG`

##### `MAIN_UNIT`

- mengandung `MATI`, `MATI TOTAL`, `TIDAK BISA HIDUP`, `TIDAK BS HIDUP`, `HIDUP MATI`, `ATI TOTAL`, `MATOL`, `MATOT`, `TIDAK BISA NYALA`, `TDK BS TV`, `TOMBOL POWER`, `TOMBOL ON/OFF`, `KENA PETIR`, `KONSLET`, `LISTRIK TURUN`, `INDIKATOR HIDUP`, `CEK FUNGSI`, `PESAN MODUL`, `STOP KONTAK ANTENA ADA KERUSAKAN`, `KABEL DIGIGIT TIKUS`, `LAYAR MATI` -> `TOTAL_OFF`
- mengandung `STANDBY`, `STAND BY`, `STANBY`, `STANDY BY` -> `STANDBY`
- mengandung `LOGO`, `STUCK LOGO`, `STUCK DILOGO` -> `LOGO_FREEZE`
- mengandung `HDMI` -> `HDMI_NG`
- mengandung `SIARAN`, `SINYAL`, `SIGNAL`, `CHANNEL`, `CHANEL`, `ANTENE` -> `NO_CHANNEL`
- mengandung `TIDAK ADA GAMBAR`, `TDK ADA GAMBAR`, `LAYAR BLANK`, `NO PICTURE`, `TUNER PATAH` -> `NO_PICTURE`
- mengandung `INDIKATOR KEDIP`, `PROTECT` -> `PROTECT`
- mengandung `REMOTE`, `REMOT`, `SENSOR` -> `SENSOR_NG`
- mengandung `SUARA` -> `SOUND_NG`
- mengandung `ERROR`, `EROR`, `SAFE MODE`, `NETFLIX`, `GOOGLE`, `PROGRAM` -> `ERROR`
- mengandung `MERAH`, `BERGARIS`, `DISPLAY`, `TAMPILAN`, `BLUR`, `DELAY`, `DISPLAY KEDIP`, `LAYAR SERING BERKEDIP`, `VERTIKAL BLOK` -> `PICTURE_NG`

#### Rekomendasi Prioritas Rule

Karena satu komentar bisa memuat beberapa keyword, urutan evaluasi perlu dikunci.

Rekomendasi urutan untuk `MAIN_UNIT`:

1. `HDMI_NG`
2. `SENSOR_NG`
3. `SOUND_NG`
4. `LOGO_FREEZE`
5. `NO_CHANNEL`
6. `NO_PICTURE`
7. `PROTECT`
8. `STANDBY`
9. `ERROR`
10. `PICTURE_NG`
11. `TOTAL_OFF`

Rekomendasi urutan untuk `PANEL`:

1. `BROKEN`
2. `DOT`
3. `SPOT`
4. `HALF`
5. `LINE`
6. `DARK`
7. `BLUR`
8. `DISPLAY_NG`
9. `BLINKING`
10. `BLANK`

Catatan:

- Urutan ini sengaja menaruh kategori yang lebih spesifik di atas kategori yang lebih umum
- `TOTAL_OFF` pada `MAIN_UNIT` ditempatkan di belakang agar tidak memakan kasus `STANDBY`, `PROTECT`, atau `NO_PICTURE` yang lebih spesifik

### Keputusan Teknis: Tanpa AI

`sub-13` sangat memungkinkan diimplementasikan full di Python tanpa bantuan AI.

Pendekatan yang direkomendasikan:

1. Normalisasi teks `symptom_comment`
2. Normalisasi label `part_name`
3. Baca rule master dari sheet `symptom`
4. Eksekusi matching top-to-bottom
5. Gunakan operator deterministic:
   - exact match
   - contains
   - list of keywords
   - wildcard `*`
   - regex bila benar-benar diperlukan
6. Ambil rule pertama yang match

Keuntungan pendekatan Python deterministic:

- hasil stabil dan mudah diaudit
- mudah ditest dengan unit test
- tidak butuh internet atau model AI
- mudah direvisi user non-teknis lewat master Excel

#### Normalisasi Teks Yang Disarankan

Sebelum matching, `symptom_comment` sebaiknya dinormalisasi:

- ubah ke uppercase
- trim spasi kiri/kanan
- kompres spasi ganda
- samakan variasi separator seperti `/`, `-`, `_`
- opsional: koreksi typo ringan yang sangat umum seperti `EROR -> ERROR`, `REMOT -> REMOTE`, `CHANEL -> CHANNEL`

#### Bentuk Rule Python Yang Direkomendasikan

```python
rules = [
    {
        "part_name": "MAIN_UNIT",
        "keywords": ["HDMI"],
        "symptom": "HDMI_NG",
    },
    {
        "part_name": "MAIN_UNIT",
        "keywords": ["REMOTE", "REMOT", "SENSOR"],
        "symptom": "SENSOR_NG",
    },
    {
        "part_name": "PANEL",
        "keywords": ["GARIS", "LINE"],
        "symptom": "LINE",
    },
]

def match_symptom(part_name: str, symptom_comment: str, rules: list[dict]) -> str | None:
    text = normalize(symptom_comment)
    part = normalize(part_name)

    for rule in rules:
        if part != rule["part_name"]:
            continue
        if any(keyword in text for keyword in rule["keywords"]):
            return rule["symptom"]
    return None
```

## Finalisasi Sub-14

### Tujuan

Menormalkan beberapa nilai `branch` ke area yang lebih besar.

### Sumber Master

- file master: `master_table.xlsx`
- sheet: `branch`

### Struktur Master

| init | branch |
|---|---|
| `CIDENG` | `JAKARTA` |
| `PULOGADUNG` | `JAKARTA` |
| `JAKARTA SELATAN` | `JAKARTA` |

### Rule Final

1. Ambil nilai `branch`
2. Cari exact match ke kolom `init`
3. Jika ada mapping, ganti dengan nilai `branch` dari master
4. Jika tidak ada mapping, pertahankan nilai asli

### Keputusan Implementasi

- Matching dilakukan exact match setelah trim spasi
- Hasil ditulis sebagai nilai statis final
- Step ini adalah normalisasi sebagian, bukan lookup penuh semua branch

### Catatan

- Sample output lama yang ada di repo belum menunjukkan hasil normalisasi ini secara konsisten
- Namun master `branch` sudah cukup jelas untuk mengunci kontrak rule

## Urutan Eksekusi Batch 4

Urutan yang dikunci:

1. `sub-9` add `part_name`
2. `sub-11` add `panel_usage`
3. `sub-12` add `factory`
4. `sub-13` add `symptom`
5. `sub-14` normalize `branch`

Catatan:

- `sub-13` bergantung pada hasil `sub-9`, karena `part_name` dipakai sebagai salah satu input rule
- `sub-14` sebaiknya dijalankan paling akhir agar normalisasi branch tidak bentrok dengan step sebelumnya

## Validasi Minimal

### Sub-9

- `part_used` tersedia
- master `part_list` tersedia

### Sub-11

- `diff_month` tersedia
- master `panel_usage` tersedia

### Sub-12

- `model_name` tersedia
- master `factory` tersedia

### Sub-13

- `part_name` tersedia
- `symptom_comment` tersedia
- master `symptom` tersedia

### Sub-14

- `branch` tersedia
- master `branch` tersedia

## Draft Bentuk Recipe Config

```yaml
steps:
  - id: sub_9_add_part_name
    type: lookup_exact
    source_column: part_used
    target_column: part_name
    master:
      file: master_table.xlsx
      sheet: part_list
      key: part_used
      value: part_name
    on_blank_source: null
    on_missing_match: "N/A"

  - id: sub_11_add_panel_usage
    type: map_ranges
    source_column: diff_month
    target_column: panel_usage
    ranges:
      - lte: 12
        value: "< 1 Year"
      - lte: 24
        value: "1 - 2 Years"
      - lte: 36
        value: "2 - 3 Years"
      - gte: 37
        value: "> 3 Years"
    on_blank_source: null

  - id: sub_12_add_factory
    type: lookup_exact
    source_column: model_name
    target_column: factory
    master:
      file: master_table.xlsx
      sheet: factory
      key: model_name
      value: factory
    on_missing_match: "N/A"

  - id: sub_13_add_symptom
    type: lookup_rules
    inputs:
      - part_name
      - symptom_comment
    target_column: symptom
    master:
      file: master_table.xlsx
      sheet: symptom
    matching:
      order: top_to_bottom
      first_match_wins: true
      part_name: exact_trimmed
      symptom_comment:
        case_sensitive: false
        wildcard: "*"
        alternative_separator: " / "
        mode: contains
    on_missing_match: null

  - id: sub_14_normalize_branch
    type: lookup_exact_replace
    source_column: branch
    target_column: branch
    master:
      file: master_table.xlsx
      sheet: branch
      key: init
      value: branch
    on_missing_match: keep_original
```

## Keputusan Yang Sudah Dikunci

- `sub-9` memakai exact lookup `part_used -> part_name`
- `sub-11` memakai range mapping dari `diff_month` integer hasil `ceil`
- `sub-12` memakai exact lookup `model_name -> factory`
- `sub-13` memakai rule matching berbasis `part_name` dan keyword `symptom_comment`
- `sub-14` memakai partial normalization `branch -> area`
- Semua hasil batch 4 ditulis sebagai nilai statis final, bukan formula Excel
