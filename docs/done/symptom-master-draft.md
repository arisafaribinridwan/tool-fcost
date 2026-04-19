# Draft Sheet Symptom

Draft ini adalah kandidat isi sheet `symptom` yang lebih lengkap, diturunkan dari pola pada `example/result.xlsx`.

File data:

- [symptom-master-draft.csv](/home/arsya/sharp/tool-fcost/docs/symptom-master-draft.csv)

## Struktur Kolom

- `priority`: urutan evaluasi rule, makin kecil makin dulu dieksekusi
- `part_name`: filter exact terhadap `part_name`
- `match_type`: untuk sekarang dipakai `contains_any` atau `wildcard`
- `pattern`: daftar keyword dengan separator `|`
- `symptom`: label hasil yang sudah dinormalkan
- `notes`: catatan manusia agar rule lebih mudah direview

## Label Kanonik

Draft ini sengaja menormalkan label symptom ke gaya:

- uppercase
- underscore untuk pemisah kata

Contoh:

- `TOTAL_OFF`
- `DISPLAY_NG`
- `NO_PICTURE`
- `SENSOR_NG`

## Aturan Eksekusi Yang Disarankan

1. Normalisasi `part_name` dan `symptom_comment`
2. Urutkan rule berdasarkan `priority`
3. Ambil rule pertama yang match
4. Jika tidak ada rule yang match, hasilkan `null`

## Catatan Review

- File ini tetap bernama `draft` untuk jejak review, tetapi isinya sekarang menjadi baseline master final untuk `sub-13` batch 4
- Beberapa keyword masih bisa dipertajam setelah kita uji ke seluruh sample
- Rule `MAIN_UNIT + MATI -> TOTAL_OFF` sengaja diletakkan paling belakang di grup `MAIN_UNIT` agar tidak memakan kasus yang lebih spesifik seperti `STANDBY`, `PROTECT`, atau `NO_PICTURE`
- Rule `MAIN_UNIT + REMOTE/SENSOR -> SENSOR_NG` sengaja didahulukan atas `NO_PICTURE` bila komentar memuat keduanya
- Rule `MAIN_UNIT + SIARAN/SIGNAL/CHANNEL -> NO_CHANNEL` sengaja didahulukan atas `ERROR` mengikuti sample
- Rule `MAIN_UNIT + PROTECT` dipersempit ke konteks `INDIKATOR KEDIP` atau `PROTECT`; gejala layar/display berkedip diarahkan ke `PICTURE_NG`
- Rule `PANEL + MATI -> TOTAL_OFF` mengikuti sample historis, bukan `BLANK`
- Coverage `TOTAL_OFF` dan `DISPLAY_NG` masih sengaja diperluas berbasis variasi teks pada sample agar false null berkurang
- Data sisa yang belum cukup jelas sengaja tidak dipaksa masuk rule; hasilnya dibiarkan kosong (`null`)
