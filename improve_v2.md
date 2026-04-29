# Rencana Implementasi: Input Manual Periode Output

## Context

Saat ini teks `Periode:` di workbook output dibuat oleh `_build_period_text()` di `app/services/output_service.py`. Fungsi itu hanya bisa mengisi periode jika config punya `header.period_from_column` dan source data punya kolom tanggal yang sesuai. Karena output Anda selalu menjadi `Periode: -`, fitur ini lebih tepat dibuat sebagai input manual dari user sebelum proses execute berjalan.

Tujuan perubahan: ketika user menekan `EXECUTE` untuk config yang memang mengaktifkan fitur periode manual, aplikasi menampilkan dialog untuk mengisi periode, lalu output Excel menulis nilai seperti `Periode: March 2026` ke baris header workbook. Kondisi muncul/tidaknya dialog dibuat dinamis dari isi config, bukan dari nama file config, supaya tetap bekerja jika user mengganti nama atau menduplikasi config. Jika config tidak mengaktifkan fitur ini, dialog tidak muncul dan behavior lama tetap berjalan. Jika user mengosongkan atau membatalkan dialog pada config yang mengaktifkan fitur ini, behavior lama tetap berjalan, yaitu fallback ke `_build_period_text()`.

## Rekomendasi Pendekatan

Gunakan flag opsional di config untuk mengaktifkan dialog, lalu tetap gunakan runtime override opsional untuk mengirim hasil input user ke output writer.

Contoh config:

```yaml
ui:
  period_prompt:
    enabled: true
```

Alasan memasukkan trigger ke config:

- Dinamis: tetap berlaku walaupun file config diganti nama atau diduplikasi.
- Eksplisit: config yang butuh input periode menyatakan kebutuhannya sendiri.
- Minimal: tidak perlu mengubah recipe engine, step engine, atau transform rules.
- Aman: config yang tidak punya flag ini tetap memakai behavior lama.

Alurnya:

1. User pilih source dan job seperti biasa.
2. User klik `EXECUTE` di `app/ui/main_window.py`.
3. Setelah validasi source/job berhasil, UI membaca config yang dipilih memakai utility config yang sudah ada.
4. Jika config punya `ui.period_prompt.enabled: true`, tampilkan dialog input periode.
5. Jika flag tidak ada atau nilainya bukan `true`, jangan tampilkan dialog dan langsung execute seperti behavior saat ini.
6. Input user diparse sebagai periode dengan format fix `YYYYMM`.
7. Aplikasi membentuk teks final, misalnya `Periode: March 2026`.
8. Teks ini dikirim ke pipeline sebagai parameter opsional.
9. `output_service.write_output_workbook()` memakai teks manual jika tersedia; kalau tidak tersedia, tetap memakai `_build_period_text()` seperti sekarang.

Pendekatan ini menjaga fitur lama tetap aman, tidak memaksa semua config/source berubah, dan tidak mengubah recipe engine/transform engine yang sudah ada. Perubahan hanya berada di UI orchestration, pipeline boundary untuk meneruskan nilai opsional, dan output writer untuk memakai nilai override jika tersedia.

## File yang Akan Diubah

### 1. `app/ui/main_window.py`

Perubahan utama di UI:

- Gunakan `ctk.CTkInputDialog`, bukan `tkinter.simpledialog`, agar tampilan dialog konsisten dengan CustomTkinter.
- Import `load_config_payload` dari `app.services`; utility ini sudah ada dan sudah dipakai untuk membaca/validasi config.
- Tambahkan helper kecil di class `DesktopApp`, misalnya:
  - `_should_prompt_period(config_path: Path) -> bool`
  - `_prompt_period_text_override() -> str | None`
  - helper dialog memakai `ctk.CTkInputDialog` dan mengambil nilai lewat `dialog.get_input()`.
- `_should_prompt_period()` membaca config dan mengembalikan `True` hanya jika ada `ui.period_prompt.enabled: true`.
- Panggil helper tersebut di `add_log_event()` setelah validasi source/job dan sebelum worker thread dimulai, tetapi hanya jika `_should_prompt_period(job.config_path)` bernilai `True`.
- Untuk config tanpa flag tersebut, set `period_text_override = None` dan lanjutkan execute tanpa dialog.
- Kirim hasil periode manual ke `_run_pipeline_worker()`.
- Update `_run_pipeline_worker()` supaya meneruskan parameter periode manual ke `run_pipeline()`.

Dialog yang direkomendasikan:

```python
dialog = ctk.CTkInputDialog(
    title="Input Periode",
    text="Masukkan periode laporan dengan format YYYYMM. Contoh: 202603 untuk March 2026. Kosongkan untuk otomatis dari source.",
)
raw_value = dialog.get_input()
```

- Format input user dibuat fix hanya `YYYYMM`, contoh `202603`.
- Jika input valid: ubah menjadi teks final, contoh `Periode: March 2026`.
- Jika kosong atau Cancel: return `None`, lalu aplikasi tetap execute seperti biasa.
- Jika invalid: tampilkan warning bahwa format wajib `YYYYMM`, lalu minta input ulang.

Untuk nama bulan, gunakan mapping manual bahasa Inggris agar hasil stabil:

- January
- February
- March
- April
- May
- June
- July
- August
- September
- October
- November
- December

Input yang didukung dibuat sengaja sederhana dan konsisten:

- `YYYYMM`, contoh `202603`

Contoh hasil:

- `202603` menjadi `Periode: March 2026`

Input selain 6 digit angka dengan bulan `01` sampai `12` dianggap invalid.

### 2. `configs/monthly-report-recipe.yaml` dan `configs/monthly-report-recipe-lcd-import.yaml`

Tambahkan flag UI opsional:

```yaml
ui:
  period_prompt:
    enabled: true
```

Flag ini tidak dipakai oleh recipe engine. Fungsinya hanya sebagai instruksi untuk UI agar menampilkan dialog periode sebelum execute.

Jika user mengganti nama file config atau membuat copy config baru, selama isi config masih membawa flag ini, dialog tetap muncul.

### 3. `app/services/pipeline_service.py`

Perubahan ini hanya meneruskan nilai opsional dari UI ke output writer. Tidak ada perubahan ke recipe engine, step engine, atau transform rules.

Tambahkan parameter opsional ke `run_pipeline()`:

- `period_text_override: str | None = None`

Lalu teruskan parameter ini ke `write_output_workbook()`.

Behavior lama tetap aman karena parameter default-nya `None`, sehingga pemanggil lama tidak perlu diubah.

### 4. `app/services/output_service.py`

Tambahkan parameter opsional ke `write_output_workbook()`:

- `period_text_override: str | None = None`

Ubah logika pembuatan period text dari:

```python
period_text = _build_period_text(source_df, header_cfg)
```

menjadi konsep:

```python
period_text = period_text_override or _build_period_text(source_df, header_cfg)
```

Dengan ini:

- Jika user mengisi periode manual, workbook memakai input user.
- Jika user kosongkan/cancel, workbook tetap memakai logic lama.

## Catatan Format

Saya sarankan output header memakai format bahasa Inggris:

```text
Periode: March 2026
```

Ini memakai nama bulan bahasa Inggris secara manual agar hasil tidak bergantung pada locale sistem.

Kalau nanti tetap ingin format pendek, helper UI bisa diubah menjadi:

```text
Periode: Mar-2026
```

Namun rencana ini memilih `March 2026` sebagai default karena sudah tertulis sebagai contoh kebutuhan.

## Verifikasi

### Test otomatis

Tambahkan atau update test di:

- `tests/test_pipeline_service.py`
- jika sudah ada pola test UI yang cocok, tambahkan juga di `tests/test_main_window.py`

Skenario test utama:

1. `run_pipeline(..., period_text_override="Periode: March 2026")` menghasilkan workbook dengan cell `A2 == "Periode: March 2026"`.
2. `run_pipeline(...)` tanpa override tetap memakai `_build_period_text()` lama.
3. Jika source/config tidak punya kolom periode dan override `None`, hasil tetap `Periode: -`.
4. UI hanya memanggil dialog periode jika config punya `ui.period_prompt.enabled: true`.
5. UI tidak memanggil dialog periode jika config tidak punya flag tersebut atau nilainya bukan `true`.
6. Copy/rename config tetap memunculkan dialog selama isi config membawa flag `ui.period_prompt.enabled: true`.
7. Helper parsing periode mengubah:
   - `202603` menjadi `Periode: March 2026`
   - input kosong menjadi `None`
   - `202613`, `202600`, `03/2026`, dan `2026-03` dianggap invalid karena format wajib `YYYYMM`

### Test manual UI

1. Jalankan aplikasi desktop.
2. Pilih source.
3. Pilih job yang config-nya punya `ui.period_prompt.enabled: true`.
4. Klik `EXECUTE`.
5. Pastikan dialog periode muncul.
6. Isi periode dengan format `YYYYMM`, contoh `202603`.
7. Pastikan proses berjalan sukses.
8. Buka file output di folder `outputs/`.
9. Pastikan cell `A2` di setiap sheet berisi:

```text
Periode: March 2026
```

10. Ulangi dengan Cancel/kosong; pastikan aplikasi tetap execute dan behavior lama tetap berlaku.
11. Ulangi dengan config yang tidak punya `ui.period_prompt.enabled: true`; pastikan dialog periode tidak muncul.

## Batasan Scope

Rencana ini hanya mengisi teks `Periode:` di header workbook.

Item lain di `improve_v2.md`, yaitu penambahan kolom `keydate`, sebaiknya dikerjakan sebagai langkah berikutnya setelah input periode ini stabil, karena itu menyentuh proses pembentukan kolom output dan bukan hanya header workbook.
