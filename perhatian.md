# Perhatian - Development di Linux dan Windows 11

Ya, perbedaan OS akan berpengaruh, tapi dampaknya lebih ke environment development dan packaging, bukan ke konsep inti aplikasinya.

## Inti Jawaban

- Target aplikasi tetap `Windows portable`, jadi build final `.exe` tetap harus dibuat dan diuji di Windows.
- Sebagian besar logic aplikasi tetap bisa dikembangkan di Linux.
- Perbedaan OS paling terasa pada path, shell command, line ending, dan packaging.

## Bagian yang Aman Dikerjakan Lintas OS

- Logic Python umum
- Parsing YAML
- Transformasi data dengan `pandas`
- Penulisan Excel dengan `openpyxl`
- Unit test business logic
- Struktur modul backend Flask

## Bagian yang Biasanya Berbeda antara Linux dan Windows

- Path file: separator `/` vs `\`
- Case sensitivity nama file/folder
- Command shell: bash vs PowerShell/CMD
- Cara aktivasi virtual environment
- Line endings `LF` vs `CRLF`
- Packaging `PyInstaller`
- Cara membuka browser lokal / `run.bat`
- Permission file tertentu

## Hal Paling Penting untuk Proyek Ini

- `PyInstaller` tidak ideal untuk cross-build target Windows dari Linux.
- Jika target akhir adalah file `.exe` Windows, maka build final sebaiknya dilakukan di Windows.
- Testing final juga wajib dilakukan di Windows karena aplikasi akan dipakai di sana.

## Rekomendasi Praktis

- Develop core logic di Linux atau Windows, keduanya boleh.
- Jaga kode tetap portable:
  - pakai `pathlib` atau `os.path`
  - jangan hardcode path Windows
  - jangan bergantung pada shell tertentu di logic aplikasi
- Jika memungkinkan, jalankan test rutin di kedua OS.
- Lakukan tahap berikut khusus di Windows:
  - test upload/download end-to-end
  - test folder runtime `configs/`, `masters/`, `uploads/`, `outputs/`
  - build `PyInstaller`
  - test `run.bat`
  - validasi hasil portable di PC Windows lain

## Potensi Masalah Nyata

- File seperti `Masters.xlsx` bisa lolos di Windows tapi gagal di Linux jika referensi huruf besar-kecil tidak konsisten.
- Script yang jalan di bash bisa gagal di CMD/PowerShell.
- Path relatif yang kebetulan jalan di Linux belum tentu aman di Windows.
- Hasil build `PyInstaller` dari Linux tidak cocok untuk distribusi `.exe` Windows.

## Strategi Kerja yang Disarankan

- Linux di rumah: fokus coding modul, test logic, refactor, schema YAML, dan transformasi `pandas`.
- Windows di kantor: fokus integrasi final, UI lokal, packaging, dan validasi portable.
- Anggap Windows sebagai `source of truth` untuk runtime final.

## Ringkasan

- Beda OS tidak menghambat proyek.
- Namun karena target distribusi adalah Windows, validasi akhir harus selalu di Windows.
- Kode sebaiknya dirancang OS-agnostic sejak awal agar aman dipakai di dua environment.
