# Finalisasi Batch 2

Dokumen ini mengunci review dan keputusan awal untuk batch 2:

- `sub-3` add column `section`
- `sub-5` add column `prod_lot`
- `sub-6` add column `inch`
- `sub-7` add column `total_cost`
- `sub-8` add column `diff_month`

Batch 2 diperlakukan sebagai transformasi deterministic di atas dataset `result` yang sudah dibentuk oleh `sub-1` dan `sub-2`.

## Scope Input

Input batch 2 adalah dataset logical `result` dengan schema hasil finalisasi `sub-1` dan `sub-2`.

Kolom minimum yang harus sudah tersedia:

- `notification`
- `malfunction_start_date`
- `model_name`
- `serial_number`
- `purchased_date`
- `labor_cost`
- `transportation_cost`
- `parts_cost`

## Temuan Dari Sample Output

Berdasarkan `example/result.xlsx`, kolom hasil batch 2 muncul dengan urutan:

1. `section`
2. `prod_lot`
3. `inch`
4. `total_cost`
5. `diff_month`

Sample output juga menunjukkan rumus Excel yang dipakai untuk menjelaskan cara hitung:

- `section`: `=IF(LEN(A2)=9,"GQS","SASS")`
- `prod_lot`: `=MID(G2,6,3)`
- `inch`: `=IF(LEFT(E2,1)="L",MID(E2,3,2),MID(E2,4,2))`
- `total_cost`: `=SUM(S2:U2)`
- `diff_month`: `=(C2-R2) / 30`

Keputusan final implementasi:

- Rumus di sample diperlakukan sebagai panduan logika, bukan format output
- Hasil recipe harus menulis nilai statis/final ke file output
- Engine tidak perlu menyimpan formula Excel literal untuk batch 2

## Finalisasi Sub-3

### Tujuan

Menambahkan kolom `section` untuk menandai asal row `GQS` atau `SASS`.

### Rule

- Jika panjang karakter `notification` = `9`, maka `section = "GQS"`
- Selain itu, `section = "SASS"`

### Keputusan

- Rule ini konsisten dengan sample:
  - `1884` row GQS memiliki panjang `notification = 9`
  - `379` row SASS memiliki panjang `notification = 12`
- Untuk recipe engine, rule ini dieksekusi sebagai transformasi nilai final statis, bukan formula Excel literal.

### Bentuk Pseudocode

```text
section = "GQS" if len(str(notification)) == 9 else "SASS"
```

## Finalisasi Sub-5

### Tujuan

Menambahkan kolom `prod_lot` berdasarkan ekstraksi karakter dari `serial_number`.

### Rule

- Ambil substring `serial_number` mulai karakter ke-6 sepanjang `3` karakter.

### Keputusan

- Rule yang dikunci mengikuti sample output persis.
- Nilai yang dihasilkan bukan bulan kalender `01-12`, melainkan kode lot / kode produksi seperti `23D`, `25H`, `21F`.
- Nama `prod_lot` dipertahankan dulu agar konsisten dengan flow awal, walaupun secara semantik ini lebih dekat ke `prod_lot_code`.
- Hasil yang ditulis adalah string statis final.

### Bentuk Pseudocode

```text
prod_lot = serial_number[5:8]
```

### Catatan

- Jika `serial_number` kosong, hasil diisi kosong.
- Jika panjang `serial_number < 8`, hasil diisi kosong dan diberi warning.

## Finalisasi Sub-6

### Tujuan

Menambahkan kolom `inch` dari pola `model_name`.

### Rule

- Jika karakter pertama `model_name` adalah `L`, ambil karakter ke-3 dan ke-4
- Selain itu, ambil karakter ke-4 dan ke-5

### Contoh

- `LC24LE170I` -> `24`
- `2TC32DC1I` -> `32`
- `4TC50DK1I` -> `50`

### Bentuk Pseudocode

```text
inch = model_name[2:4] if model_name.startswith("L") else model_name[3:5]
```

### Catatan

- Rule ini konsisten dengan sample output.
- Jika `model_name` kosong atau terlalu pendek, hasil diisi kosong dan diberi warning.
- Notifikasi selesai di workbook sumber masih typo menyebut `Prod Month`; itu tidak dianggap rule bisnis.
- Hasil yang ditulis adalah string statis final.

## Finalisasi Sub-7

### Tujuan

Menambahkan kolom `total_cost` sebagai penjumlahan tiga komponen biaya.

### Rule

```text
total_cost = labor_cost + transportation_cost + parts_cost
```

### Keputusan

- Nilai kosong pada kolom biaya diperlakukan sebagai `0`
- Tipe hasil diharapkan numerik
- Hasil yang ditulis adalah angka statis final

## Finalisasi Sub-8

### Tujuan

Menambahkan kolom `diff_month` dari selisih tanggal kerusakan dengan tanggal pembelian.

### Rule

Rule historis di sample output:

```text
diff_month = (malfunction_start_date - purchased_date) / 30
```

### Keputusan

- `diff_month` harus disimpan sebagai nilai numerik statis final
- Perhitungan dasar tetap berbasis `date_diff_days / 30`
- Hasil akhir harus dibulatkan ke integer agar aman dipakai untuk rule `panel_usage`
- Metode pembulatan yang dikunci adalah `ceil` atau pembulatan ke atas

### Contoh Nilai Dasar Sebelum Pembulatan

- Selisih `1060` hari -> `35.3333333333`
- Selisih `18` hari -> `0.6`
- Selisih `1` hari -> `0.0333333333`

### Contoh Hasil Setelah `ceil`

- `35.3333333333` -> `36`
- `0.6` -> `1`
- `0.0333333333` -> `1`
- `12.0` -> `12`
- `12.1` -> `13`

### Catatan

- Ini penting untuk batch berikutnya karena `panel_usage` memakai bucket rentang `0-12`, `13-24`, `25-36`, `>=37`.
- Jika salah satu tanggal kosong, hasil diisi kosong dan diberi warning.
- Jika hasil negatif, nilainya tetap diisi sesuai hasil hitung setelah mengikuti metode pembulatan yang disepakati, lalu diberi warning.

## Urutan Eksekusi Batch 2

Urutan yang dikunci:

1. `sub-3` add `section`
2. `sub-5` add `prod_lot`
3. `sub-6` add `inch`
4. `sub-7` add `total_cost`
5. `sub-8` add `diff_month`

Urutan ini tidak saling bentrok, tetapi dipertahankan sama dengan flow kerja aslinya agar log lebih mudah ditelusuri.

## Validasi Minimal

Validasi yang harus ada:

- `notification` tersedia untuk `section`
- `serial_number` tersedia untuk `prod_lot`
- `model_name` tersedia untuk `inch`
- kolom biaya tersedia untuk `total_cost`
- `malfunction_start_date` dan `purchased_date` tersedia untuk `diff_month`

Jika kolom input hilang:

- engine harus memberi error yang jelas
- proses batch 2 tidak boleh diam-diam lanjut dengan hasil salah

## Draft Bentuk Recipe Config

```yaml
steps:
  - id: sub_3_add_section
    type: derive_column
    target: section
    expression:
      case:
        - when:
            len_eq:
              column: notification
              value: 9
          then: "GQS"
        - else: "SASS"

  - id: sub_5_add_prod_lot
    type: derive_column
    target: prod_lot
    expression:
      substring:
        column: serial_number
        start: 5
        length: 3
    on_short_input: null

  - id: sub_6_add_inch
    type: derive_column
    target: inch
    expression:
      case:
        - when:
            starts_with:
              column: model_name
              value: "L"
          then:
            substring:
              column: model_name
              start: 2
              length: 2
        - else:
            substring:
              column: model_name
              start: 3
              length: 2
    on_short_input: null

  - id: sub_7_add_total_cost
    type: derive_column
    target: total_cost
    expression:
      add:
        columns:
          - labor_cost
          - transportation_cost
          - parts_cost
        null_as_zero: true

  - id: sub_8_add_diff_month
    type: derive_column
    target: diff_month
    expression:
      ceil:
        value:
          divide:
            left:
              date_diff_days:
                start_column: purchased_date
                end_column: malfunction_start_date
            right: 30
    on_missing_input: null
```

## Keputusan Yang Sudah Dikunci

- Batch 2 adalah transformasi deterministic
- Semua rule batch 2 bisa diturunkan ke recipe config tanpa lookup master
- `section` ditentukan dari panjang `notification`, bukan dari sheet asal
- `prod_lot` mengikuti ekstraksi 3 karakter dari `serial_number`
- `inch` mengikuti pola parse `model_name`
- `total_cost` adalah penjumlahan tiga kolom biaya
- `diff_month` adalah nilai statis numerik hasil `(selisih hari / 30)` yang dibulatkan ke atas dengan `ceil`
