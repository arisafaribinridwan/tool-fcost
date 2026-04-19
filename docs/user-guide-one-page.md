# Panduan Singkat Pemakaian Tool

Tool ini dipakai untuk mengubah file Excel/CSV menjadi laporan Excel baru.

## Langkah 1. Buka Aplikasi

Jalankan:

```bash
cd /home/arsya/sharp/tool-fcost/dist/ExcelAutoTool
./run.sh
```

Jika jendela aplikasi muncul, tool siap dipakai.

## Langkah 2. Pilih File Source

- Klik `Pilih Source`
- Di Linux, dialog akan mencoba backend native desktop (`kdialog` lalu `zenity`) jika tersedia
- Pilih file yang ingin diproses
- Format yang didukung: `.xlsx` atau `.csv`

Contoh file:

- `example/source.xlsx`

## Langkah 3. Pilih Config

- Pada bagian `Config YAML`, klik daftar pilihan
- Pilih config yang sesuai

Untuk contoh penggunaan, pilih:

- `monthly-report-recipe.yaml`

## Langkah 4. Jalankan Proses

- Klik `Execute`
- Tunggu sampai proses selesai

Selama proses berjalan:

- Log akan bergerak
- Status akan berubah

Jika berhasil, status akan menunjukkan proses selesai tanpa error.

## Langkah 5. Ambil Hasil

- Klik `Buka Folder Outputs`
- File Excel hasil proses akan muncul di folder output

Contoh hasil:

- `Monthly_Report_Final_Recipe_YYYYMMDD_HHMMSS.xlsx`

## Urutan Pakai Paling Mudah

1. Buka aplikasi
2. Klik `Pilih Source`
3. Pilih file `.xlsx` atau `.csv`
4. Pilih config
5. Klik `Execute`
6. Tunggu selesai
7. Klik `Buka Folder Outputs`
8. Buka file hasil Excel

## Jika Muncul Error

Cek hal berikut:

- File source benar dan tidak rusak
- Format file source adalah `.xlsx` atau `.csv`
- Config yang dipilih sesuai
- Jangan klik `Execute` berulang kali saat proses masih berjalan

Jika masih gagal:

- Catat pesan error
- Simpan screenshot log
- Minta bantuan dengan menyertakan nama file source dan config yang dipakai

## Contoh Uji Coba

Untuk mencoba dengan data contoh:

1. Buka aplikasi
2. Pilih file `example/source.xlsx`
3. Pilih config `monthly-report-recipe.yaml`
4. Klik `Execute`
5. Buka hasil di folder `outputs`
