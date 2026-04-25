# Guide Pengisian Sheet `action` (master_table.xlsx)

Panduan ini untuk mengisi sheet `action` pada `masters/master_table.xlsx` agar cocok dengan step [configs/monthly-report-recipe.yaml](configs/monthly-report-recipe.yaml#L465-L500) (`sub_15_add_action`).

## 1) Struktur kolom (wajib, urutan kolom)

Header sheet `action` harus:

1. `priority`
2. `job_sheet_section`
3. `part_name`
4. `symptom_comment`
5. `repair_comment`
6. `action`

## 2) Arti tiap kolom

- `priority`  
  Integer positif (`1, 2, 3, ...`). Nilai lebih kecil diproses lebih dulu.

- `job_sheet_section`  
  Isi `1` untuk rule `action` aktif.

- `part_name`  
  Nama part untuk match exact (contoh: `PANEL`, `MAIN_UNIT`).  
  Boleh kosong jika rule tidak spesifik part.

- `symptom_comment`  
  Regex untuk filter symptom.  
  Jika ingin tidak membatasi symptom, gunakan: `(?s).*`

- `repair_comment`  
  Regex untuk filter repair comment.

- `action`  
  Nilai output action final (contoh: `REPLACE_PANEL`, `REPAIR_MAIN_UNIT`, `CANCEL`).

## 3) Aturan pengisian

1. Satu baris = satu rule.
2. Semua rule aktif isi `job_sheet_section = 1`.
3. `priority` wajib angka positif.
4. Hindari duplikasi priority (disarankan unik per baris).
5. Regex harus valid.
6. Rule paling spesifik beri `priority` lebih kecil.
7. Rule generic/fallback beri `priority` lebih besar.

## 4) Pola regex yang aman (contoh)

- Cocokkan kata kunci bebas huruf besar/kecil:  
  `(?i).*upgrade.*`

- Cocokkan beberapa kata kunci:  
  `(?i).*(upgrade|update|software).*`

- Fallback (selalu cocok):  
  `(?s).*`

## 5) Contoh baris

| priority | job_sheet_section | part_name    | symptom_comment | repair_comment                     | action             |
|---:|---:|---|---|---|---|
| 1 | 1 | PANEL     | (?s).* | (?s).* | REPLACE_PANEL |
| 2 | 1 | MAIN_UNIT | (?s).* | (?i).*(repair main|resoldering).* | REPAIR_MAIN_UNIT |
| 3 | 1 | *(kosong)* | (?s).* | (?i).*batal.* | CANCEL |
| 99 | 1 | *(kosong)* | (?s).* | (?s).* | USER |

## 6) Template rule siap pakai (berbasis data riil saat ini)

Gunakan template ini sebagai starter agar tim bisa langsung isi. Kolom `symptom_comment` diset `(?s).*` jika belum ada filter symptom khusus.

| priority | job_sheet_section | part_name | symptom_comment | repair_comment | action |
|---:|---:|---|---|---|---|
| 1 | 1 | PANEL | (?s).* | (?s).* | REPLACE_PANEL |
| 2 | 1 | MAIN_UNIT | (?s).* | (?s).* | REPLACE_MAIN_UNIT |
| 3 | 1 | POWER_UNIT | (?s).* | (?s).* | REPLACE_POWER_UNIT |
| 4 | 1 | REMOTE_CONTROL | (?s).* | (?s).* | REPLACE_REMOTE |
| 5 | 1 | LED_BAR | (?s).* | (?s).* | REPLACE_LED_BAR |
| 6 | 1 | PART_KIT | (?s).* | (?s).* | REPAIR_POWER_UNIT |
| 7 | 1 | IC | (?s).* | (?s).* | REPAIR_MAIN_UNIT |
| 10 | 1 | *(kosong)* | (?s).* | (?i).*(upgrade|update|software|sofware|soft).* | UPGRADE |
| 11 | 1 | *(kosong)* | (?s).* | (?i).*(batal|tdk acc|acc biaya|ditukar|sudah oke|tes ok).* | CANCEL |
| 12 | 1 | *(kosong)* | (?s).* | (?i).*(ext|exs|kotor|kardus rusak|cairan|cleaning).* | EXTERNAL |
| 13 | 1 | *(kosong)* | (?s).* | (?i).*(zy|bawa|to ws|ws|ditarik|kirim|carry).* | ZY |
| 14 | 1 | *(kosong)* | (?s).* | (?i).*(reset program|reset ulang|reset unit|setting|r(i|e)set program|service mode|factor).* | SETTING |
| 15 | 1 | *(kosong)* | (?s).* | (?i).*(repair main|resoldering main|resolder pcb main|solder main|tuner|ganti mainboard).* | REPAIR_MAIN_UNIT |
| 16 | 1 | *(kosong)* | (?s).* | (?i).*(repair power|resoldering psu|repair regulator|repair modul|resoldering modul).* | REPAIR_POWER_UNIT |
| 17 | 1 | *(kosong)* | (?s).* | (?i).*(repair remote|perbaiki remote).* | REPAIR_REMOTE |
| 98 | 1 | *(kosong)* | (?s).* | (?i).*(cek normal|cek ok|unit cek ok|normal|cek fungsi ok|fungsi-ok|cek unit|test fungsi|set up data).* | USER |
| 99 | 1 | *(kosong)* | (?s).* | (?i).*(jelas).* | EXPLANATION |

### Urutan prioritas yang disarankan

1. Rule `part_name` spesifik + replacement (`REPLACE_*`) di paling atas.
2. Rule intent kuat (`UPGRADE`, `CANCEL`, `EXTERNAL`, `ZY`, `SETTING`).
3. Rule perbaikan (`REPAIR_MAIN_UNIT`, `REPAIR_POWER_UNIT`, `REPAIR_REMOTE`).
4. Rule umum (`USER`, `EXPLANATION`) di prioritas besar.

## 7) Minimal Baseline (10–12 rule inti)

Gunakan baseline ini kalau ingin mulai dari rule paling penting dulu, lalu tambah rule detail bertahap.

| priority | job_sheet_section | part_name | symptom_comment | repair_comment | action |
|---:|---:|---|---|---|---|
| 1 | 1 | PANEL | (?s).* | (?s).* | REPLACE_PANEL |
| 2 | 1 | MAIN_UNIT | (?s).* | (?s).* | REPLACE_MAIN_UNIT |
| 3 | 1 | POWER_UNIT | (?s).* | (?s).* | REPLACE_POWER_UNIT |
| 4 | 1 | REMOTE_CONTROL | (?s).* | (?s).* | REPLACE_REMOTE |
| 10 | 1 | *(kosong)* | (?s).* | (?i).*(upgrade|update|software|sofware|soft).* | UPGRADE |
| 11 | 1 | *(kosong)* | (?s).* | (?i).*(batal|tdk acc|acc biaya|ditukar).* | CANCEL |
| 12 | 1 | *(kosong)* | (?s).* | (?i).*(ext|exs|kotor|kardus rusak|cairan|cleaning).* | EXTERNAL |
| 13 | 1 | *(kosong)* | (?s).* | (?i).*(zy|bawa|to ws|ws|ditarik|kirim|carry).* | ZY |
| 14 | 1 | *(kosong)* | (?s).* | (?i).*(reset program|reset ulang|reset unit|setting|r(i|e)set program|service mode|factor).* | SETTING |
| 15 | 1 | *(kosong)* | (?s).* | (?i).*(repair main|resoldering main|resolder pcb main|solder main|tuner|ganti mainboard).* | REPAIR_MAIN_UNIT |
| 16 | 1 | *(kosong)* | (?s).* | (?i).*(repair power|resoldering psu|repair regulator|repair modul|resoldering modul).* | REPAIR_POWER_UNIT |
| 98 | 1 | *(kosong)* | (?s).* | (?i).*(cek normal|cek ok|unit cek ok|normal|cek fungsi ok|fungsi-ok|cek unit|test fungsi|set up data).* | USER |

Jika butuh coverage lebih detail, tambahkan rule setelah baseline ini dengan priority di antara 17 sampai 97.

## 8) Checklist sebelum simpan

- Header kolom persis sesuai format baru.
- Tidak ada `priority <= 0`.
- Semua `job_sheet_section` terisi `1`.
- Semua regex valid (tidak typo pattern).
- Rule spesifik berada di priority lebih kecil dibanding rule generic.
- Tidak ada overlap besar antara rule level atas dan fallback level bawah.

## 8) Catatan penting

- Step `sub_15_add_action` saat ini memakai 4 matcher: `job_sheet_section`, `part_name`, `symptom_comment`, `repair_comment`.
- `on_missing_match` bernilai `null`, jadi jika tidak ada rule yang cocok maka `action` akan kosong.
