# Excel Automation Tool

Repo ini berisi aplikasi desktop automasi Excel berbasis `CustomTkinter`, `pandas`, dan `openpyxl`.

## Setup Singkat

Target setup development saat ini menggunakan Python `3.14.x`.

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

Catatan Linux desktop: Python yang dipakai untuk menjalankan app atau build bundle harus punya dukungan Tk/Tcl. Pada Ubuntu atau Linux Mint biasanya ini berarti perlu paket `python3-tk`.

Untuk pengalaman dialog pilih file yang lebih native di Linux, install helper desktop opsional `kdialog` (KDE) atau `zenity` (GNOME/umum). Jika tidak tersedia, aplikasi otomatis fallback ke dialog Tk.

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
- Repo ini menyiapkan packaging portable untuk Windows dan Linux.
- Hindari hardcode path OS tertentu. Gunakan `pathlib` atau `os.path`.
- Jaga nama file konsisten huruf besar-kecil agar aman lintas OS.

## Alur Aplikasi

- User membuka aplikasi desktop.
- User memilih file source `.xlsx` atau `.csv`.
- Aplikasi memuat config `.yaml` valid dari folder `configs/`.
- User menjalankan `Execute`.
- Progress ditampilkan di panel log.
- Folder `outputs/` bisa dibuka langsung dari UI.

## Dependency Utama

- `customtkinter` untuk desktop UI
- `pandas` untuk transformasi data
- `openpyxl` untuk baca/tulis dan styling Excel
- `PyYAML` untuk parsing config
- `pyinstaller` untuk packaging portable
- `tkinterdnd2` untuk drag-and-drop source file di desktop
- `pytest` dan `ruff` untuk testing dan linting

## Menjalankan Saat Development

- Buat dan aktifkan virtual environment.
- Install dependency dari `requirements.txt`.
- Jalankan desktop app:

```bash
python run.py
```

### Struktur runtime penting

- `configs/` untuk file YAML recipe
- `masters/` untuk file master
- `uploads/` untuk jejak source (opsional, disiapkan helper)
- `outputs/` untuk hasil output

Repo sudah menyertakan 2 contoh config:

- `configs/sample_sales.yaml`
- `configs/sample_summary.yaml`

## Build Portable

- Build harus dilakukan di OS targetnya masing-masing.
- Jangan mengandalkan cross-build `PyInstaller` untuk menghasilkan binary OS lain.
- Folder runtime `configs/`, `masters/`, `uploads/`, dan `outputs/` dibuat otomatis saat first run. Script build juga menyiapkan folder-folder ini di hasil `dist/`.
- Build Windows membawa hidden import `tkinterdnd2` agar drag-and-drop source tetap aktif pada bundle yang mendukung.

### Build di Linux

Best practice yang direkomendasikan untuk Linux desktop/build machine:

```bash
sudo apt-get update
sudo apt-get install -y python3-tk python3.12-venv zenity kdialog
./packaging/linux/bootstrap-build-env.sh
./packaging/linux/build.sh
./packaging/linux/smoke-test.sh
```

Catatan:

- Build Linux sebaiknya memakai interpreter distro (`/usr/bin/python3.12`) dalam virtualenv build terpisah seperti `.venv-linux-build`.
- Script `packaging/linux/build.sh` akan otomatis memprioritaskan `.venv-linux-build` bila tersedia.

Alternatif manual:

```bash
chmod +x packaging/linux/build.sh
./packaging/linux/build.sh
```

Jika ingin memakai Python lain:

```bash
./packaging/linux/build.sh /path/to/python3
```

Jika ingin menyiapkan env build secara eksplisit:

```bash
./packaging/linux/bootstrap-build-env.sh /usr/bin/python3.12 /path/to/.venv-linux-build
./packaging/linux/build.sh /path/to/.venv-linux-build/bin/python
./packaging/linux/smoke-test.sh
```

Hasil build akan tersedia di:

```txt
dist/ExcelAutoTool/
|- ExcelAutoTool
|- run.sh
|- configs/
|- masters/
|- uploads/
`- outputs/
```

Script Linux juga membuat archive portable:

```txt
dist/ExcelAutoTool-linux-x86_64.tar.gz
```

Untuk pemakaian harian di Linux, simpan bundle di folder yang writable oleh user, misalnya `~/Apps/ExcelAutoTool`, lalu jalankan `./run.sh`.

- Spec build Linux disiapkan di `packaging/linux/ExcelAutoTool.spec`.
- Bootstrap env build Linux disiapkan di `packaging/linux/bootstrap-build-env.sh`.
- Script build Linux disiapkan di `packaging/linux/build.sh`.
- Smoke test bundle Linux disiapkan di `packaging/linux/smoke-test.sh`.
- Launcher bundle Linux disiapkan di `packaging/linux/run.sh`.
- Checklist build machine Linux disiapkan di `docs/linux-build-checklist.md`.
- Isi folder `configs/` dan `masters/` dari repo akan disalin ke hasil build Linux.
- Script build Linux akan gagal lebih awal jika Python yang dipakai belum punya modul `tkinter`.

### Build di Windows

Build Windows harus memakai Python environment yang sama dengan dependency project. PyInstaller membundel package dari interpreter Python yang menjalankan build, bukan otomatis dari environment development di PC lain. Jika build memakai Python global atau virtualenv yang belum lengkap, bundle bisa tetap terbentuk tetapi gagal saat runtime, misalnya `ModuleNotFoundError: No module named 'PIL'` karena `Pillow` tidak ikut terbawa.

Checklist saat build di PC berbeda:

- Pastikan repo sudah terbaru dan virtualenv dibuat di root project.
- Install ulang dependency ke virtualenv build dari `requirements.txt`.
- Jangan mengandalkan command `python` global untuk build final.
- Jalankan build melalui script Windows agar `.venv` dari root project diprioritaskan.
- Validasi hasil bundle dari folder `dist\ExcelAutoTool\`, bukan dari source tree.

Setup environment build yang direkomendasikan:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Validasi dependency penting sebelum build:

```powershell
.\.venv\Scripts\python.exe -c "import PIL, customtkinter, pandas, openpyxl, PyInstaller; print('OK')"
```

PowerShell:

```powershell
.\packaging\windows\build.ps1
```

Jika ingin memakai Python lain:

```powershell
.\packaging\windows\build.ps1 -PythonExe "C:\Path\To\python.exe"
```

Catatan: script build Windows akan mengecek `PIL` dan `PyInstaller` lebih awal. Jika dependency belum lengkap, jalankan kembali install dependency dengan `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` sebelum build ulang.

Hasil build akan tersedia di:

```txt
dist\ExcelAutoTool\
|- ExcelAutoTool.exe
|- run.bat
|- configs\
|- masters\
|- uploads\
`- outputs\
```

## Status Saat Ini

- UI desktop `CustomTkinter` sudah aktif (`pilih source`, `pilih config`, `execute`, `log`, `buka outputs`).
- Pipeline transform dan penulisan output `.xlsx` sudah berjalan dan ditest.
- Validasi source, config YAML, lookup master, transform, dan output workbook sudah tersedia di layer service.
- Runtime path sudah disiapkan untuk mode source dan mode bundle (`PyInstaller`).
- Packaging portable sudah tersedia untuk Windows dan Linux.
