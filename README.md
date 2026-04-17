# Excel Automation Tool

Repo ini berisi fondasi untuk MVP tool automasi Excel berbasis Python desktop, `CustomTkinter`, `pandas`, dan `openpyxl`.

## Setup Singkat

Target setup development saat ini menggunakan Python `3.14.x`.

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

### Windows PowerShell

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Windows CMD

```bat
py -3.14 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Catatan Environment

- Development harian bisa dilakukan di Linux atau Windows.
- Binary final tetap dibuild per OS target dengan `PyInstaller`.
- Untuk distribusi MVP saat ini, runtime final, build `PyInstaller`, dan validasi portable tetap dilakukan di Windows.
- Hindari hardcode path OS tertentu. Gunakan `pathlib` atau `os.path`.
- Jaga nama file konsisten huruf besar-kecil agar aman lintas OS.

## Alur Aplikasi

- User membuka aplikasi desktop.
- User memilih file source `.xlsx` atau `.csv`.
- Aplikasi memuat config `.yaml` dari folder `configs/`.
- Aplikasi memuat master dari folder `masters/`.
- User menjalankan proses transformasi.
- Hasil `.xlsx` disimpan ke folder `outputs/`.

## Dependency Utama

- `customtkinter` untuk desktop UI
- `pandas` untuk transformasi data
- `openpyxl` untuk baca/tulis dan styling Excel
- `PyYAML` untuk parsing config
- `pyinstaller` untuk packaging portable
- `pytest` dan `ruff` untuk testing dan linting

## Menjalankan Saat Development

- Buat dan aktifkan virtual environment.
- Install dependency dari `requirements.txt`.
- Jalankan entrypoint aplikasi desktop yang dipakai project, misalnya `python run.py` atau `python main.py` setelah file entrypoint final dibuat.

## Build Portable

- Build Windows `.exe` dilakukan di Windows.
- Jika nanti ingin binary Linux native, build dilakukan lagi di Linux.
- Jangan mengandalkan cross-build `PyInstaller` untuk menghasilkan `.exe` Windows dari Linux.

## Status Saat Ini

- Virtual environment `.venv` sudah dipakai untuk setup lokal.
- Dependency utama sudah didaftarkan di `requirements.txt`.
- Dokumen perencanaan sudah diarahkan ke desktop app `CustomTkinter`.
- Struktur folder inti sudah disiapkan untuk runtime `configs/`, `masters/`, `uploads/`, dan `outputs/`.
