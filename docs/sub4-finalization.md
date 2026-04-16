# Finalisasi Sub-4

Dokumen ini mengunci review dan keputusan untuk `sub-4 - Update Value Costs Column GQS`.

## Tujuan

Menormalkan nilai biaya pada dataset `result` agar baris yang berasal dari `GQS` berada pada satuan yang konsisten dengan hasil akhir laporan.

Kolom yang diproses:

- `labor_cost`
- `transportation_cost`
- `parts_cost`

## Temuan Utama Dari Sample

Perbandingan `example/source.xlsx` dengan `example/result.xlsx` menunjukkan pola berikut:

- Baris `SASS` tetap sama persis
- Baris `GQS` dikali `100` untuk ketiga kolom biaya
- Baris `GQS` yang nilainya `0` tetap `0`

Hasil pengecekan sample:

- `GQS x100`: `1684` row
- `GQS tetap sama`: `166` row
- `SASS tetap sama`: `379` row
- `unmatched`: `34` row

Catatan penting:

- `166` row `GQS tetap sama` semuanya adalah kasus biaya `0, 0, 0`, jadi secara logika tetap konsisten dengan aturan `x100`
- `34` row `unmatched` sangat mungkin sudah terkena dampak step lain, terutama duplicate-handling pada `sub-10`, sehingga tidak dipakai untuk membantah rule utama `sub-4`

## Koreksi Terhadap Teks Di Workbook

Teks flow di workbook saat ini mengandung dua typo logika:

1. Kondisi tertulis `jika kolom "Notification" = "GQS"`
   - Ini tidak literal benar
   - `notification` berisi nomor notifikasi, bukan label `GQS`
   - Indikator yang benar adalah asal row `GQS`, paling aman memakai kolom `section = "GQS"`

2. Rule untuk `Transportation Cost` dan `Parts Cost` masih menulis referensi ke `Labor Cost`
   - Ini typo
   - Yang benar: masing-masing kolom memperbarui nilainya sendiri

## Rule Final Yang Dikunci

### Kondisi

Jika `section == "GQS"`:

- `labor_cost = labor_cost * 100`
- `transportation_cost = transportation_cost * 100`
- `parts_cost = parts_cost * 100`

Jika `section != "GQS"`:

- semua kolom biaya dibiarkan apa adanya

## Bentuk Pseudocode

```text
if section == "GQS":
    labor_cost = labor_cost * 100
    transportation_cost = transportation_cost * 100
    parts_cost = parts_cost * 100
else:
    keep original values
```

## Contoh Dari Sample

### GQS

- `430.61` -> `43061`
- `168` -> `16800`
- `1000` -> `100000`
- `0` -> `0`

### SASS

- `153000` tetap `153000`
- `34000` tetap `34000`
- `361500` tetap `361500`

## Keputusan Implementasi

- Output harus berupa nilai statis final, bukan formula Excel
- Rule dieksekusi setelah `sub-3` sehingga kolom `section` sudah tersedia
- Nilai kosong diperlakukan konservatif:
  - jika kosong, tetap kosong
  - jika `0`, hasil tetap `0`
- Tipe hasil harus numerik bila input numerik

## Interaksi Dengan Step Lain

`sub-4` hanya melakukan normalisasi satuan biaya.

Step ini tidak menangani:

- deduplikasi notifikasi
- override biaya karena duplicate notification
- penyesuaian `job_sheet_section`

Perubahan biaya lanjutan karena duplicate notification adalah tanggung jawab `sub-10`.

## Validasi Minimal

Sebelum `sub-4` dijalankan, kolom berikut harus tersedia:

- `section`
- `labor_cost`
- `transportation_cost`
- `parts_cost`

Jika salah satu kolom hilang:

- engine harus memberi error yang jelas
- proses tidak boleh diam-diam lanjut

## Draft Bentuk Recipe Config

```yaml
steps:
  - id: sub_4_normalize_gqs_costs
    type: update_columns
    when:
      column: section
      equals: "GQS"
    updates:
      labor_cost:
        multiply:
          column: labor_cost
          value: 100
      transportation_cost:
        multiply:
          column: transportation_cost
          value: 100
      parts_cost:
        multiply:
          column: parts_cost
          value: 100
```

## Keputusan Yang Sudah Dikunci

- `sub-4` berlaku untuk row `GQS`, bukan dengan membandingkan literal `notification == "GQS"`
- indikator resmi yang dipakai adalah `section == "GQS"`
- ketiga kolom biaya diproses dengan logika yang sama: `x100`
- `SASS` tidak diubah oleh `sub-4`
- hasil ditulis sebagai angka statis final
