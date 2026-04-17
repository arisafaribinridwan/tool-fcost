# Perhatian - Development Lintas OS untuk CustomTkinter dan PyInstaller

Ya, perbedaan OS tetap berpengaruh, tetapi sekarang fokusnya bergeser dari browser/server lokal ke desktop GUI, path runtime, dan packaging `PyInstaller` per OS target.

## Inti Jawaban

- Memakai `CustomTkinter` justru lebih cocok untuk workflow Python desktop yang ingin sederhana dan portable.
- Sebagian besar logic aplikasi tetap aman dikembangkan di Linux maupun Windows.
- Build final tetap tidak benar-benar lintas OS; binary harus dibuat di OS targetnya.
- Untuk distribusi utama saat ini, `.exe` final tetap harus dibuild dan diuji di Windows.

## Bagian yang Aman Dikerjakan Lintas OS

- Logic Python umum
- Parsing YAML
- Transformasi data dengan `pandas`
- Penulisan Excel dengan `openpyxl`
- Unit test business logic
- Struktur modul aplikasi desktop
- Sebagian besar komponen `CustomTkinter` dasar
- Validasi path runtime dan helper folder

## Bagian yang Biasanya Berbeda antara Linux dan Windows

- Path file: separator `/` vs `\`
- Case sensitivity nama file/folder
- Command shell: bash vs PowerShell/CMD
- Cara aktivasi virtual environment
- Line endings `LF` vs `CRLF`
- Tampilan tema, font, atau perilaku kecil widget GUI
- Packaging `PyInstaller`
- Cara membuka file/folder hasil dari aplikasi
- Permission file tertentu

## Hal Paling Penting untuk Proyek Ini

- `PyInstaller` bukan alat yang nyaman untuk membuat `.exe` Windows dari Linux.
- `PyInstaller` juga pada praktiknya dibuild per OS target: Windows build di Windows, Linux build di Linux, macOS build di macOS.
- Jadi yang disebut build lintas OS di proyek ini sebaiknya dipahami sebagai: basis kode yang sama bisa didevelop lintas OS, lalu dibuild terpisah sesuai target.
- Karena distribusi MVP difokuskan ke Windows, build final dan testing final tetap wajib dilakukan di Windows.

## Kenapa CustomTkinter Lebih Mulus untuk Kasus Ini

- Tidak perlu Flask, browser lokal, port, template HTML, atau static asset web.
- Packaging lebih lurus karena UI tetap berada di proses Python yang sama.
- Alur user lebih natural untuk tool personal: buka aplikasi, pilih file, execute, ambil output.
- Development lintas OS tetap nyaman karena logic inti tidak berubah dan UI tidak bergantung browser tertentu.

## Rekomendasi Praktis

- Develop core logic di Linux atau Windows, keduanya boleh.
- Jaga kode tetap portable:
  - pakai `pathlib` atau `os.path`
  - jangan hardcode path Windows
  - jangan bergantung pada shell tertentu di logic aplikasi
  - pisahkan logic bisnis dari layer `CustomTkinter`
- Jika memungkinkan, jalankan test rutin di lebih dari satu OS.
- Lakukan tahap berikut khusus di Windows untuk distribusi utama:
  - test alur pilih file, execute, dan buka folder output
  - test folder runtime `configs/`, `masters/`, `uploads/`, `outputs/`
  - build `PyInstaller`
  - test `run.bat`
  - validasi hasil portable di PC Windows lain
- Jika nanti ingin binary Linux native, lakukan build Linux terpisah di Linux.

## Potensi Masalah Nyata

- File seperti `Masters.xlsx` bisa lolos di Windows tapi gagal di Linux jika referensi huruf besar-kecil tidak konsisten.
- Helper pembuka folder bisa beda implementasi di Windows dan Linux.
- Path relatif yang kebetulan jalan di Linux belum tentu aman di Windows.
- Resource path saat jalan dari source mode bisa berbeda dengan saat jalan dari bundle `PyInstaller`.
- Hasil build `PyInstaller` dari Linux tidak cocok untuk distribusi `.exe` Windows.

## Strategi Kerja yang Disarankan

- Linux di rumah: fokus coding modul, test logic, schema YAML, transformasi `pandas`, dan komponen UI dasar.
- Windows di kantor: fokus integrasi final desktop UI, uji runtime folder, packaging, dan validasi portable.
- Anggap Windows sebagai `source of truth` untuk runtime distribusi MVP.
- Anggap Linux sebagai environment cepat untuk development harian dan regression test logic.

## Ringkasan

- Beda OS tidak menghambat proyek.
- `CustomTkinter` membuat arsitektur lebih sederhana dibanding web UI lokal untuk tool ini.
- Namun `PyInstaller` tetap harus dibuild per OS target.
- Jadi strategi terbaik adalah: develop lintas OS, build final sesuai target OS, dan validasi distribusi utama di Windows.
