# Manual QA Checklist

Checklist ini dipakai untuk real test manual aplikasi desktop, terutama pada bundle Linux hasil `PyInstaller`.

## Target Test

- Bundle Linux: `dist/ExcelAutoTool/`
- Launcher: `dist/ExcelAutoTool/run.sh`
- Alternatif source mode: `python run.py`

## Prasyarat

- Bundle sudah berhasil dibuild
- Folder `outputs/` writable
- Ada minimal 1 source file `.xlsx` atau `.csv` yang valid
- Ada minimal 1 config YAML valid di `configs/`
- Jika ingin melihat traceback, jalankan dari terminal

## 1. Launch

Jalankan:

```bash
cd /home/arsya/sharp/tool-fcost/dist/ExcelAutoTool
./run.sh
```

Pass criteria:

- Window aplikasi muncul
- UI responsif
- Tidak ada traceback/error fatal di terminal

## 2. Initial UI

Periksa:

- Field source tampil
- Dropdown config tampil
- Area log tampil
- Tombol `Execute` awalnya nonaktif
- Tombol `Buka Folder Outputs` tampil

Pass criteria:

- Semua komponen utama muncul
- Layout tidak rusak
- `Execute` belum aktif sebelum input lengkap

## 3. Config Load

Langkah:

1. Lihat daftar config di dropdown
2. Pilih salah satu config valid
3. Klik `Refresh Config`
4. Amati area log dan info config

Pass criteria:

- Config valid muncul
- Refresh tidak error
- Info config sesuai item yang dipilih

## 4. Happy Path

Langkah:

1. Klik `Pilih Source`
2. Pilih file `.xlsx` atau `.csv` valid
3. Pilih config valid
4. Klik `Execute`
5. Amati log sampai proses selesai
6. Klik `Buka Folder Outputs`
7. Buka file hasil `.xlsx`

Pass criteria:

- Dialog `Pilih Source` muncul saat tombol diklik
- Khusus Linux: jika `kdialog` atau `zenity` terpasang, dialog tampil native sesuai desktop
- `Execute` aktif setelah source dan config valid
- Log bergerak selama proses
- Status berubah ke sukses
- File output berhasil dibuat
- Workbook bisa dibuka

## 5. Output Validation

Periksa file hasil:

- Jumlah sheet sesuai ekspektasi
- Header/title muncul benar
- Nama kolom benar
- Data tidak kosong
- Formatting dasar terlihat benar jika relevan

Pass criteria:

- Struktur workbook sesuai
- Tidak ada sheet rusak
- Isi output masuk akal

## 6. Invalid Source

Langkah:

1. Klik `Pilih Source`
2. Pilih file yang tidak valid atau file rusak
3. Amati popup error dan area log

Pass criteria:

- Error message jelas
- App tidak freeze
- App tidak menandai proses sebagai sukses

## 7. Re-run

Langkah:

1. Jalankan 1 proses sukses
2. Pilih source lain
3. Jalankan lagi
4. Ulangi 2-3 kali bila perlu

Pass criteria:

- UI tetap responsif
- Log tetap update
- Output baru tetap terbentuk
- Tidak ada crash setelah run berulang

## 8. Folder Action

Langkah:

1. Klik `Buka Folder Outputs`
2. Pastikan file manager membuka folder yang benar

Pass criteria:

- Folder terbuka ke lokasi yang tepat
- Tidak ada error popup

## 9. Close App

Langkah:

1. Tutup window aplikasi
2. Pastikan proses berakhir normal

Pass criteria:

- Aplikasi menutup bersih
- Tidak hang di terminal

## 10. Optional Source Mode

Jika ingin membandingkan perilaku bundle vs source mode:

```bash
cd /home/arsya/sharp/tool-fcost
source .venv-linux-build/bin/activate
python run.py
```

Gunakan checklist yang sama seperti di atas.

## Hasil Uji

Template pencatatan:

```txt
Launch: PASS
Initial UI: PASS
Config Load: PASS
Happy Path: PASS/FAIL
Output Validation: PASS/FAIL
Invalid Source: PASS/FAIL
Re-run: PASS/FAIL
Folder Action: PASS/FAIL
Close App: PASS/FAIL

Notes:
- ...
- ...
```
