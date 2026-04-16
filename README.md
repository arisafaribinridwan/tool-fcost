# Excel Automation Tool

Repo ini berisi fondasi untuk MVP tool automasi Excel berbasis Python, `Flask`, `pandas`, dan `openpyxl`.

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
- Runtime final, build `PyInstaller`, dan validasi portable tetap harus dilakukan di Windows.
- Hindari hardcode path OS tertentu. Gunakan `pathlib` atau `os.path`.
- Jaga nama file konsisten huruf besar-kecil agar aman lintas OS.

## Status Saat Ini

- Virtual environment `.venv` sudah dipakai untuk setup lokal.
- Dependency utama sudah didaftarkan di `requirements.txt`.
- Struktur folder inti dan skeleton Flask fase awal sudah siap.
