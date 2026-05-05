# Plan: Update Job Summary Result

## Context

Job `configs/job_summary_result.yaml` perlu disesuaikan dengan format workbook baru. Source workbook untuk job ini sekarang berisi dua sheet: `result` dan `sales`. Output harus menambahkan sheet raw `sales`, merevisi `data1`, dan menambahkan summary `data8`, `data9`, serta `data10` seperti contoh `example/Job_Summary_Result_20260505_144300.xlsx`.

Target utama adalah perubahan minimal, reuse kode yang sudah ada, dan tidak mengganggu job/summary lain.

## Recommended implementation

1. Update `configs/job_summary_result.yaml`
   - Tambahkan step `extract_sheet` untuk sheet `sales`.
   - Gunakan selector `contains: "sales"` atau required columns sales agar tetap toleran terhadap variasi nama sheet.
   - Select kolom:
     - `Model`
     - `Category`
     - `Sales Amount`
     - `Sales (Qty)`
     - `Factory`
   - Tulis ke dataset `sales`.
   - Tambahkan output sheet `sales` dengan `dataset: "sales"`.
   - Pertahankan output `result` dan summary existing.
   - Revisi konfigurasi `data1` hanya pada opsi yang diperlukan agar tetap memakai builder existing `static_part_pivot_summary`.
   - Tambahkan output summary:
     - `data8`: summary section cost.
     - `data9`: summary sales vs FCost occupancy by factory.
     - `data10`: summary part cost by factory.

2. Update `app/services/recipe_service.py`
   - Reuse builder existing `_build_part_pivot_summary` untuk `data10` dengan opsi `section_column: "factory"` dan column label `section: "Factory"`.
   - Tambahkan builder kecil untuk `data8`, misalnya `_build_section_cost_summary`:
     - group by `section`.
     - sum `labor_cost`, `transportation_cost`, `parts_cost`, `total_cost`.
     - count baris/part non-blank sesuai kebutuhan output.
     - tambah row `Grand Total`.
     - pakai `_apply_summary_column_labels` dan `_row_type` untuk styling plain summary.
   - Tambahkan builder kecil untuk `data9`, misalnya `_build_sales_fcost_occupancy_summary`:
     - baca dataset utama `result` untuk FCost by `factory`.
     - baca dataset `sales` untuk Sales Amount by `Factory`.
     - hasilkan dua tabel side-by-side dalam satu DataFrame:
       - `Factory`, `Sales Amount`, `Occupancy`
       - blank separator column
       - `Factory`, `FCost Amount`, `Occupancy`
     - occupancy dihitung dari nilai per factory / grand total masing-masing sisi.
   - Ubah `_build_summary_output_sheet` agar dapat menerima `datasets` hanya untuk summary yang perlu dataset tambahan (`data9`).
   - Ubah `_build_output_sheets` untuk meneruskan `datasets` ke `_build_summary_output_sheet`.
   - Jangan mengubah extraction core, writer workbook, atau summary builder existing selain dispatcher minimal.

3. Update tests di `tests/test_pipeline_service.py`
   - Tambahkan test kecil dengan workbook synthetic berisi sheet `result` dan `sales`.
   - Jalankan pipeline memakai config step-recipe yang mencakup output `sales`, `data8`, `data9`, dan `data10`.
   - Assert:
     - sheet `sales`, `data8`, `data9`, `data10` ada.
     - header `sales` benar.
     - `data8` memiliki total section dan grand total yang benar.
     - `data9` menghitung Sales Amount, FCost Amount, dan occupancy per factory dengan benar.
     - `data10` memakai factory sebagai group utama dan menghasilkan subtotal/grand total.

## Verification

Run:

```bash
python -m ruff check .
python -m pytest -q
```

Manual check:

1. Jalankan job `Job Summary Result` dengan source workbook yang memiliki sheet `result` dan `sales`.
2. Buka output workbook.
3. Pastikan sheet output berurutan mencakup:
   - `result`
   - `sales`
   - `data1` sampai `data10`
4. Bandingkan layout dan angka utama dengan `example/Job_Summary_Result_20260505_144300.xlsx`.
