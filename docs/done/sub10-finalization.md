# Finalisasi Sub-10

Dokumen ini mengunci keputusan final untuk `sub-10 - update data duplicate notifications`.

Tujuannya supaya implementasi engine, review hasil sample, dan diskusi lanjutan memakai kontrak yang sama dan tidak lagi membuka ulang rule yang sudah diputuskan.

## Status Finalisasi

### Sudah final

- kontrak inti duplicate handling berbasis `notification`
- dispatch rule berdasarkan `section`
- rule final `SASS`
- tie-break `SASS`
- winner selection `GQS`
- bentuk rewrite row untuk duplicate group `GQS`

## Tujuan

Menangani grup row dengan `notification` yang sama agar:

- tepat satu row menjadi row utama dengan `job_sheet_section = 1`
- biaya yang relevan terkonsentrasi di row utama tersebut
- row lain pada grup menjadi row pendamping dengan `job_sheet_section = 0`

## Scope

`sub-10` berlaku untuk:

- `GQS`
- `SASS`

Tetapi:

- `GQS` dan `SASS` memakai rule winner selection yang berbeda
- `GQS` dan `SASS` boleh memakai rule pemindahan biaya yang berbeda

## Kontrak Inti Yang Sudah Dikunci

Untuk setiap grup duplicate berbasis `notification`:

1. Kelompokkan row berdasarkan `notification`
2. Jika grup hanya punya `1` row, skip
3. Jika grup duplicate, pilih tepat `1` winner row
4. Set winner row menjadi `job_sheet_section = 1`
5. Set seluruh row lain menjadi `job_sheet_section = 0`
6. Terapkan rule pemindahan biaya sesuai `section`
7. Row non-winner mengikuti rule reset biaya sesuai `section`

## Desain Engine Yang Sudah Dikunci

### Tahap 1. Deteksi duplicate group

```text
group_key = notification
```

### Tahap 2. Deteksi section grup

Section grup dibaca dari kolom:

- `section`

### Tahap 3. Jalankan rule sesuai section

- jika `section = GQS`, pakai rule duplicate `GQS`
- jika `section = SASS`, pakai rule duplicate `SASS`

### Tahap 4. Rewrite group rows

- set winner row
- pindahkan biaya sesuai section
- reset row non-winner

## Finalisasi SASS

### Keputusan Yang Sudah Dikunci

- winner `SASS` ditentukan dari `parts_cost` paling tinggi
- biaya yang dipindah ke winner hanya:
  - `labor_cost`
  - `transportation_cost`
- `parts_cost` tetap berada pada row masing-masing
- row non-winner setelah dipindah menjadi `0` untuk biaya yang memang dipindahkan

### Bentuk Rule SASS

Untuk satu grup duplicate `SASS`:

1. Cari row dengan `parts_cost` paling tinggi
2. Row itu menjadi winner
3. `labor_cost` winner = jumlah `labor_cost` seluruh grup
4. `transportation_cost` winner = jumlah `transportation_cost` seluruh grup
5. `parts_cost` setiap row tidak dipindahkan
6. Semua row non-winner:
   - `job_sheet_section = 0`
   - `labor_cost = 0`
   - `transportation_cost = 0`
   - `parts_cost` tetap pada row masing-masing

### Bentuk Pseudocode SASS

```text
winner = row with max(parts_cost)

if multiple rows share max(parts_cost):
    winner = row with highest job_sheet_section

if multiple rows still tie:
    winner = first row in group order

winner.job_sheet_section = 1
winner.labor_cost = sum(group.labor_cost)
winner.transportation_cost = sum(group.transportation_cost)

for each loser in group except winner:
    loser.job_sheet_section = 0
    loser.labor_cost = 0
    loser.transportation_cost = 0
    loser.parts_cost = keep original
```

### Tie-Break SASS Yang Sudah Dikunci

Jika ada lebih dari satu row dengan `parts_cost` tertinggi yang sama:

1. pilih row dengan `job_sheet_section` awal paling tinggi
2. jika masih tie, pilih row pertama sesuai urutan row dalam grup

Alasan keputusan ini:

- pada sumber `SASS`, `job_sheet_section` berasal dari `Qty Claim`
- pada sample duplicate group `SASS`, selalu ada tepat satu row dengan `job_sheet_section` tertinggi
- pada satu-satunya kasus tie `parts_cost` di sample, winner final juga cocok dengan rule ini

## Finalisasi GQS

### Hal Yang Sudah Bisa Dikunci

Temuan kuat dari sample dan review:

- `sub-10` pada `GQS` adalah proses `winner selection within duplicate group`
- ada tepat satu winner row per grup
- winner row menyimpan biaya utama grup
- row lain menjadi non-winner
- winner selection `GQS` final diputuskan berbasis `part_name` saja
- komentar tidak lagi menjadi input wajib untuk memilih winner `GQS`

### Bentuk Rewrite Group Yang Sudah Bisa Dikunci

Untuk grup duplicate `GQS` yang terkena rule:

- satu row dipilih sebagai winner
- `job_sheet_section` pada winner menjadi `1`
- `labor_cost`, `transportation_cost`, dan `parts_cost` dipindahkan ke winner
- row lain menjadi `job_sheet_section = 0`
- row lain memiliki biaya `0` atau `null`

### Pola Grup Yang Sering Muncul

Pola `part_name` yang sering muncul pada duplicate group `GQS`:

- `('PANEL', 'TAPE')`
- `('MAIN_UNIT', 'PANEL')`
- `('MAIN_UNIT', 'POWER_UNIT')`
- `('LED_BAR', 'PANEL')`
- `('LVDS_WIRE', 'PANEL', 'PART_KIT', 'TCON_UNIT')`

### Temuan Winner Dari Sample

Contoh agregat dari sample:

- `('PANEL', 'TAPE')` -> winner `TAPE` sebanyak `32`, winner `PANEL` sebanyak `31`
- `('MAIN_UNIT', 'PANEL')` -> winner sering `PANEL`, tetapi tidak selalu
- `('MAIN_UNIT', 'POWER_UNIT')` -> winner bisa `MAIN_UNIT` atau `POWER_UNIT`
- `('LED_BAR', 'PANEL')` -> winner sering `PANEL`
- `('LVDS_WIRE', 'PANEL', 'PART_KIT', 'TCON_UNIT')` -> winner bisa `PANEL`, `TCON_UNIT`, atau `PART_KIT`

Kesimpulan:

- rule `GQS` diposisikan sebagai rule berbasis `part_name`
- pasangan part utama sudah dikunci lewat keputusan bisnis final
- winner selection `GQS` tidak lagi bergantung pada `repair_comment` atau `symptom_comment`

## Rule GQS Yang Sudah Final

### `PANEL` vs `TAPE`

Keputusan bisnis final:

- untuk duplicate group `GQS` dengan signature part tepat `('PANEL', 'TAPE')`
- winner final dikunci menjadi `PANEL`

Konsekuensi implementasi:

- row `PANEL` menjadi winner row
- `job_sheet_section` row `PANEL` = `1`
- `labor_cost`, `transportation_cost`, dan `parts_cost` grup dipindahkan ke row `PANEL`
- row `TAPE` menjadi non-winner
- `job_sheet_section` row `TAPE` = `0`
- biaya row `TAPE` di-reset mengikuti rule non-winner `GQS`

Catatan keputusan:

- sample historis memang menunjukkan winner `PANEL` dan `TAPE` yang hampir seimbang
- komentar juga belum cukup menjelaskan perbedaan winner secara konsisten
- tetapi keputusan bisnis terbaru untuk finalisasi `sub-10` mengunci bahwa kasus `PANEL` vs `TAPE` harus memenangkan `PANEL`
- jadi untuk pasangan ini, keputusan bisnis harus meng-override pola sample historis

### `MAIN_UNIT` vs `PANEL`

Keputusan bisnis final:

- untuk duplicate group `GQS` dengan signature part tepat `('MAIN_UNIT', 'PANEL')`
- winner final dikunci menjadi `PANEL`

Konsekuensi implementasi:

- row `PANEL` menjadi winner row
- `job_sheet_section` row `PANEL` = `1`
- `labor_cost`, `transportation_cost`, dan `parts_cost` grup dipindahkan ke row `PANEL`
- row `MAIN_UNIT` menjadi non-winner
- `job_sheet_section` row `MAIN_UNIT` = `0`
- biaya row `MAIN_UNIT` di-reset mengikuti rule non-winner `GQS`

Catatan keputusan:

- sample historis menunjukkan winner sering `PANEL`, tetapi tidak selalu
- keputusan bisnis terbaru untuk finalisasi `sub-10` mengunci bahwa pasangan `MAIN_UNIT` vs `PANEL` harus memenangkan `PANEL`
- jadi untuk pasangan ini, keputusan bisnis harus meng-override variasi historis pada sample

### `LED_BAR` vs `PANEL`

Keputusan bisnis final:

- untuk duplicate group `GQS` dengan signature part tepat `('LED_BAR', 'PANEL')`
- winner final dikunci menjadi `PANEL`

Konsekuensi implementasi:

- row `PANEL` menjadi winner row
- `job_sheet_section` row `PANEL` = `1`
- `labor_cost`, `transportation_cost`, dan `parts_cost` grup dipindahkan ke row `PANEL`
- row `LED_BAR` menjadi non-winner
- `job_sheet_section` row `LED_BAR` = `0`
- biaya row `LED_BAR` di-reset mengikuti rule non-winner `GQS`

Catatan keputusan:

- sample historis menunjukkan winner sering `PANEL`
- keputusan bisnis terbaru untuk finalisasi `sub-10` mengunci bahwa pasangan `LED_BAR` vs `PANEL` harus memenangkan `PANEL`
- jadi pasangan ini sudah tidak perlu menunggu rule komentar tambahan

### `MAIN_UNIT` vs `POWER_UNIT`

Keputusan bisnis final:

- untuk duplicate group `GQS` dengan signature part tepat `('MAIN_UNIT', 'POWER_UNIT')`
- winner final dikunci menjadi `MAIN_UNIT`

Konsekuensi implementasi:

- row `MAIN_UNIT` menjadi winner row
- `job_sheet_section` row `MAIN_UNIT` = `1`
- `labor_cost`, `transportation_cost`, dan `parts_cost` grup dipindahkan ke row `MAIN_UNIT`
- row `POWER_UNIT` menjadi non-winner
- `job_sheet_section` row `POWER_UNIT` = `0`
- biaya row `POWER_UNIT` di-reset mengikuti rule non-winner `GQS`

Catatan keputusan:

- sample historis menunjukkan winner bisa `MAIN_UNIT` maupun `POWER_UNIT`
- keputusan bisnis terbaru untuk finalisasi `sub-10` mengunci bahwa pasangan `MAIN_UNIT` vs `POWER_UNIT` harus memenangkan `MAIN_UNIT`
- jadi untuk pasangan ini, keputusan bisnis harus meng-override variasi historis pada sample

### Grup 4-part

Keputusan bisnis final:

- untuk duplicate group `GQS` dengan signature part tepat `('LVDS_WIRE', 'PANEL', 'PART_KIT', 'TCON_UNIT')`
- winner final dikunci menjadi `PANEL`

Konsekuensi implementasi:

- row `PANEL` menjadi winner row
- `job_sheet_section` row `PANEL` = `1`
- `labor_cost`, `transportation_cost`, dan `parts_cost` grup dipindahkan ke row `PANEL`
- row `LVDS_WIRE`, `PART_KIT`, dan `TCON_UNIT` menjadi non-winner
- `job_sheet_section` seluruh row non-winner = `0`
- biaya seluruh row non-winner di-reset mengikuti rule non-winner `GQS`

Catatan keputusan:

- sample historis menunjukkan winner bisa `PANEL`, `TCON_UNIT`, atau `PART_KIT`
- keputusan bisnis terbaru untuk finalisasi `sub-10` mengunci bahwa grup 4-part ini harus memenangkan `PANEL`
- jadi untuk grup ini, keputusan bisnis harus meng-override variasi historis pada sample

## Area GQS Yang Sudah Tertutup

Saat ini tidak ada lagi pola duplicate `GQS` utama di dokumen ini yang masih terbuka.

## Batas Implementasi Yang Aman Saat Ini

Dengan keputusan final saat ini, batas implementasi yang aman adalah:

- engine `sub-10` wajib dipisah per `section`
- rule `SASS` boleh langsung diimplementasi penuh
- `GQS` diimplementasi berbasis rule `part_name`
- rule `GQS` sebaiknya dibaca dari master/config yang bisa diubah tanpa mengubah kode engine

Rekomendasi aman untuk fase implementasi:

- jika nanti `GQS` sudah diaktifkan, evaluasi rule harus `first match wins`
- jika grup duplicate `GQS` tidak menemukan rule yang cocok, engine sebaiknya memberi warning yang jelas
- jangan diam-diam mengarang winner hanya dari ranking agregat sample
- rule `PANEL` vs `TAPE` sudah boleh dianggap final dan tidak perlu menunggu heuristik komentar
- rule `MAIN_UNIT` vs `PANEL` sudah boleh dianggap final: winner = `PANEL`
- rule `LED_BAR` vs `PANEL` sudah boleh dianggap final: winner = `PANEL`
- rule `MAIN_UNIT` vs `POWER_UNIT` sudah boleh dianggap final: winner = `MAIN_UNIT`
- rule grup 4-part sudah boleh dianggap final: winner = `PANEL`

## Draft Bentuk Master Rule

Untuk `GQS`, rule sebaiknya berbentuk master/config seperti berikut:

| priority | section | parts_signature | winner_part_name | notes |
|---|---|---|---|---|
| 10 | GQS | PANEL,TAPE | PANEL | final by business decision |
| 20 | GQS | MAIN_UNIT,PANEL | PANEL | final by business decision |
| 30 | GQS | LED_BAR,PANEL | PANEL | final by business decision |
| 40 | GQS | MAIN_UNIT,POWER_UNIT | MAIN_UNIT | final by business decision |
| 50 | GQS | LVDS_WIRE,PANEL,PART_KIT,TCON_UNIT | PANEL | final by business decision |

Untuk `SASS`, rule dasarnya lebih sederhana:

| priority | section | winner_rule | labor_rule | transportation_rule | parts_rule | loser_rule |
|---|---|---|---|---|---|---|
| 10 | SASS | max(parts_cost) | sum_to_winner | sum_to_winner | keep_per_row | loser_labor_trans_zero |

## Validasi Minimal

Sebelum `sub-10` dijalankan, kolom berikut harus tersedia:

- `notification`
- `section`
- `job_sheet_section`
- `labor_cost`
- `transportation_cost`
- `parts_cost`

Untuk `GQS`, rule final membutuhkan:

- `part_name`

Jika kolom wajib tidak tersedia:

- engine harus memberi error yang jelas
- proses tidak boleh diam-diam lanjut

## Keputusan Yang Sudah Dikunci

- duplicate group dibentuk dari `notification`
- duplicate handling wajib dispatch berdasarkan `section`
- setiap duplicate group harus menghasilkan tepat satu winner row
- winner row selalu menjadi `job_sheet_section = 1`
- seluruh non-winner menjadi `job_sheet_section = 0`
- `SASS`:
  - winner = row dengan `parts_cost` paling tinggi
  - jika tie `parts_cost`, pilih row dengan `job_sheet_section` awal paling tinggi
  - jika masih tie, pilih row pertama dalam urutan grup
  - yang dipindah hanya `labor_cost` dan `transportation_cost`
  - `parts_cost` tetap di row masing-masing
- `GQS`:
  - sudah jelas ada winner row dan relokasi biaya utama grup
  - rule `PANEL` vs `TAPE` sudah final: winner = `PANEL`
  - rule `MAIN_UNIT` vs `PANEL` sudah final: winner = `PANEL`
  - rule `LED_BAR` vs `PANEL` sudah final: winner = `PANEL`
  - rule `MAIN_UNIT` vs `POWER_UNIT` sudah final: winner = `MAIN_UNIT`
  - rule grup 4-part `LVDS_WIRE + PANEL + PART_KIT + TCON_UNIT` sudah final: winner = `PANEL`
  - implementasi final `GQS` berbasis `part_name` saja

## Ringkasan Singkat Untuk Chat Baru

Kalau melanjutkan di chat baru, konteks yang harus dianggap aktif adalah:

- `sub-10` berlaku untuk `GQS` dan `SASS`
- duplicate group dibentuk dari `notification`
- section dispatcher memakai kolom `section`
- `SASS` sudah final:
  - winner = row dengan `parts_cost` paling tinggi
  - tie-break 1 = `job_sheet_section` awal paling tinggi
  - tie-break 2 = row pertama dalam urutan grup
  - yang dipindah hanya `labor_cost` dan `transportation_cost`
  - `parts_cost` tetap di row masing-masing
- `GQS` sudah jelas butuh satu winner per grup dan relokasi biaya ke winner
- `GQS` sudah punya rule final:
  - jika duplicate signature = `PANEL` + `TAPE`, winner = `PANEL`
  - jika duplicate signature = `MAIN_UNIT` + `PANEL`, winner = `PANEL`
  - jika duplicate signature = `LED_BAR` + `PANEL`, winner = `PANEL`
  - jika duplicate signature = `MAIN_UNIT` + `POWER_UNIT`, winner = `MAIN_UNIT`
  - jika duplicate signature = `LVDS_WIRE` + `PANEL` + `PART_KIT` + `TCON_UNIT`, winner = `PANEL`
- winner selection `GQS` diputuskan berbasis `part_name` saja
- pendekatan aman untuk `GQS` adalah rule master/config berbasis `part_name`
