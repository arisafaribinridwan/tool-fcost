# Implementasi Regex untuk VLookup Symptom (`lookup_rules`)

Dokumen ini merangkum desain dan hasil implementasi dukungan regex pada mekanisme `lookup_rules` untuk kasus lookup `symptom`, dengan fokus menjaga kompatibilitas perilaku lama (`equals` dan `contains`).

## Status Implementasi

Sudah aktif di repo saat ini:

- dukungan `regex` untuk lookup `symptom`
- validasi sheet `symptom` sebagai rule table berbasis `priority`
- urutan rule `priority` ascending dengan tie-break urutan row
- semantik regex Python `search`
- compile regex sekali per rule
- fail-fast untuk regex invalid
- guardrail panjang pattern
- regression test untuk `equals` dan `contains`

---

## 1) Tujuan Fitur

- Menambah mode matcher baru: `regex` pada `lookup_rules`.
- Memungkinkan rule symptom yang lebih fleksibel (contoh: variasi kata, alternatif token, boundary kata, dsb).
- Menjaga perilaku existing tetap aman dan konsisten (tidak breaking untuk config lama).

Contoh kemampuan baru:
- Rule master bisa pakai pattern seperti `(?<!no )power` atau `line|vertical line`.
- Rule tetap mengikuti urutan dan kebijakan `first_match_wins`.

---

## 2) Scope (In-Scope vs Out-of-Scope)

### In Scope

- Tambah `mode: regex` pada matcher `lookup_rules`.
- Validasi config agar menerima mode `regex`.
- Implement eksekusi regex pada:
  - engine master lookup (`transform_service`)
  - engine step-recipe (`recipe_service`)
- Error message yang actionable jika regex invalid.
- Unit/integration test untuk jalur sukses dan error.

### Out of Scope (untuk fase ini)

- UI editor regex interaktif.
- DSL regex custom di luar Python regex standard.
- Perubahan besar arsitektur performa (mis. indexing engine khusus pattern matching).

---

## 3) Desain Perilaku yang Diusulkan

### 3.1 Mode baru: `regex`

- Lokasi: `matching.matchers[].mode`
- Nilai didukung setelah fitur: `equals`, `contains`, `regex`

### 3.2 Semantik default regex

- Matching menggunakan **search** (pattern boleh match sebagian string), bukan `fullmatch`.
- Mengikuti normalisasi yang sudah ada:
  - `trim`
  - `case_sensitive`
  - `alternative_separator`
  - `blank_as_wildcard`
- Jika `blank_as_wildcard: true` dan nilai master kosong, tetap dianggap match (konsisten dengan mode lain).

### 3.3 Kompatibilitas

- `contains` + wildcard existing (`*`) **tetap dipertahankan**.
- Config existing tidak perlu migrasi.

---

## 4) File yang Diubah

## Core Logic

- `app/services/config_service.py`
  - Tambah dukungan `regex` di `SUPPORTED_MATCHER_MODES`.
  - (Opsional ringan) validasi field regex-specific bila perlu.

- `app/services/transform_service.py`
  - Menangani validasi rule table `symptom`.
  - Menambahkan compile pattern yang aman + error handling jelas.
  - Menghindari compile per baris source dengan compile sekali per rule.

- `app/services/recipe_service.py`
  - Menjalankan symptom lookup memakai rule table tervalidasi dari `transform_service`.

## Test

- `tests/test_config_service.py`
  - Tambah test bahwa schema menerima `mode: regex`.
  - Tambah test reject jika mode tidak valid (tetap existing).

- `tests/test_pipeline_service.py`
  - Tambah skenario lookup symptom berbasis regex (happy path).
  - Tambah skenario regex invalid -> fail dengan pesan jelas.

- `tests/test_symptom_rules.py`
  - Validasi schema rule table symptom.
  - Priority order dan tie-break urutan row.
  - Compile regex sekali per rule.
  - Reject regex terlalu panjang.
  - Regression untuk `equals` dan `contains`.

## Dokumentasi (opsional tapi direkomendasikan)

- `docs/...` (atau file recipe contoh yang relevan)
  - Tambah contoh konfigurasi `mode: regex`.
  - Catatan best practice pattern aman.

---

## 5) Rekomendasi Guardrail (Penting)

## Guardrail Wajib (implement di fase ini)

1. **Compile pattern sekali per rule**
   - Jangan compile regex di loop per baris source.
   - Mengurangi overhead signifikan untuk dataset besar.

2. **Fail-fast untuk pattern invalid**
   - Saat compile gagal, lempar error yang menyebut:
     - step/master yang gagal,
     - index rule/matcher,
     - pesan error regex engine.

3. **Batasi panjang pattern**
   - Implementasi saat ini memakai batas maksimal `512` karakter per pattern.
   - Pattern melebihi batas -> blocked dengan pesan actionable.

4. **Konsistensi normalisasi**
   - Pattern dan source harus diproses sesuai `normalize` agar hasil predictable.

5. **Backward compatibility strict**
   - Jangan ubah perilaku `equals` dan `contains` existing, bahkan jadikan prioritas.
   - setelahnya baru jalankan mode regex

## Guardrail Sangat Disarankan (bisa fase lanjutan)

1. **Preflight regex lint**
   - Validasi compile semua pattern regex saat `Preflight Check`, sebelum execute.

2. **Resource guardrail runtime**
   - Untuk mode interaktif: warning jika kombinasi `row_count x rule_count` terlalu besar.

3. **Pattern safety lint ringan**
   - Flag pola rawan backtracking ekstrem (heuristik sederhana) sebagai warning.

4. **Observability minimal**
   - Log jumlah rule regex aktif + durasi step (tanpa mengekspose data sensitif).

---

## 6) Ringkasan Implementasi

1. `transform_service.py` memvalidasi dan menyiapkan sheet `symptom` sebagai rule table tervalidasi.
2. Rule regex di-compile sekali per rule saat tabel disiapkan.
3. `recipe_service.py` dan engine pipeline memakai tabel rule yang sudah tervalidasi tersebut.
4. Error regex invalid dan pattern terlalu panjang memblokir execute lebih awal.
5. Test unit dan integration ditambahkan untuk jalur sukses dan error.

---

## 7) Acceptance Criteria (Definition of Done)

- Config dengan `mode: regex` lolos validasi schema.
- Lookup symptom regex menghasilkan output sesuai ekspektasi pada pipeline test.
- Regex invalid memunculkan error yang jelas dan tidak crash tanpa konteks.
- Config existing `equals`/`contains` tetap bekerja (regression aman).
- Tidak ada penurunan performa mencolok untuk skenario normal (dibanding baseline rule lama).

---

## 8) Contoh Konfigurasi yang Direncanakan

```yaml
matching:
  first_match_wins: true
  matchers:
    - source: "part_name"
      master: "part_name"
      mode: "equals"
      normalize:
        trim: true
        case_sensitive: false

    - source: "symptom_comment"
      master: "symptom_pattern"
      mode: "regex"
      normalize:
        trim: true
        case_sensitive: false
        blank_as_wildcard: true
```

Catatan:
- Nilai `master.symptom_pattern` berisi pattern regex, misalnya `line|vertical\s+line`.

---

## 9) Risiko dan Mitigasi

- Risiko: regex kompleks memperlambat proses.
  - Mitigasi: compile sekali per rule + batas panjang pattern + warning volume rule besar.

- Risiko: hasil berubah karena overlap rule.
  - Mitigasi: dokumentasikan urutan prioritas rule dan gunakan `first_match_wins`.

- Risiko: user bingung escaping pattern di YAML.
  - Mitigasi: berikan contoh pattern dan tips escaping pada dokumentasi.

---

## 10) Hasil Verifikasi

Verifikasi yang sudah berjalan di repo:

- unit test symptom rules lulus
- integration test pipeline symptom regex lulus
- regression test `equals` dan `contains` lulus
- full `pytest` dan `ruff check .` lulus pada perubahan terakhir
