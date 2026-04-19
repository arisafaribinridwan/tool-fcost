# Linux Build Checklist

Checklist ini dipakai untuk menjaga build GUI Linux tetap repeatable di local machine dan CI.

## Baseline Build Machine

- Distro berbasis Ubuntu 24.04 / Linux Mint 22 atau yang kompatibel
- `python3-tk` terpasang
- `python3.12-venv` terpasang
- `xvfb` tersedia untuk smoke test headless
- Build dilakukan memakai interpreter distro `python3.12`, bukan Python pihak ketiga yang tidak terhubung ke Tk distro

## One-Time Bootstrap

```bash
sudo apt-get update
sudo apt-get install -y python3-tk python3.12-venv xvfb
./packaging/linux/bootstrap-build-env.sh
```

## Build Flow

```bash
./packaging/linux/build.sh
./packaging/linux/smoke-test.sh
```

## Acceptance Gates

- `./packaging/linux/bootstrap-build-env.sh` selesai tanpa error
- `./packaging/linux/build.sh` menghasilkan `dist/ExcelAutoTool/`
- `./packaging/linux/build.sh` menghasilkan `dist/ExcelAutoTool-linux-x86_64.tar.gz`
- `./packaging/linux/smoke-test.sh` lulus
- `python -m pytest -q` lulus
- `python -m ruff check .` lulus

## Operational Notes

- Pisahkan env dev harian dari env packaging Linux
- Gunakan `dist/ExcelAutoTool-linux-x86_64.tar.gz` sebagai artifact distribusi utama
- Jika build machine berganti runner/image, validasi ulang modul `tkinter` sebelum build
- Untuk dialog file Linux yang lebih native, install salah satu helper desktop: `kdialog` (KDE) atau `zenity` (GNOME/umum)
- Jika helper tidak tersedia, aplikasi otomatis fallback ke dialog Tk
