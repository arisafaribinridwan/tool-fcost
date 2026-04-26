# Improvement Plan untuk Tool LCD SEID

Dokumen ini merangkum hasil audit komprehensif terhadap flow LCD SEID pada engine yang ada sekarang. Fokusnya bukan mengubah fondasi engine berbasis Excel, melainkan meningkatkan kualitas hasil klasifikasi dengan memperbaiki isi master, coverage rule, dan urutan prioritas aturan.

## Ringkasan eksekutif

Secara arsitektur, engine saat ini sudah cukup sehat. Pipeline sudah jelas: ekstraksi source dari sheet GQS dan SASS, normalisasi comment, derivasi kolom bantu, lookup part, duplicate resolution, perhitungan cost, lalu klasifikasi symptom, action, defect category, dan defect. Masalah terbesar saat ini bukan pada struktur engine, tetapi pada kualitas dan coverage master yang menggerakkan rule.

Dari sample output LCD SEID yang diaudit, terdapat 2263 row dengan temuan utama sebagai berikut. Sebanyak 898 row masih memiliki `part_name` kosong. Sebanyak 1073 row masih memiliki `symptom` kosong. Sebanyak 228 row masih memiliki `action` kosong. Sebanyak 570 row memiliki `defect_category` dan `defect` kosong. Ini menunjukkan bottleneck terbesar ada pada lookup part, coverage symptom, coverage action, dan kelengkapan mapping defect.

Secara prioritas, area improvement terbaik adalah meningkatkan kualitas `comment_synonyms`, memperbaiki coverage `partlist`, menutup gap rule symptom per part, merapikan prioritas rule action agar rule terlalu generik tidak menang terlalu dini, dan melengkapi master `defect_category` untuk action yang sudah dihasilkan engine.

## Cara kerja flow LCD SEID saat ini

Flow LCD SEID dikendalikan oleh `configs/monthly-report-recipe.yaml`. Config ini mengekstrak data dari sheet GQS dan SASS pada source workbook, lalu hanya mengambil baris dengan `Category = LCD SEID`. Setelah itu pipeline menjalankan normalisasi `symptom_comment` dan `repair_comment` dengan master `comment_synonyms`, menurunkan `section`, menyesuaikan biaya GQS, menghitung `prod_month`, `inch`, `total_cost`, `diff_month`, dan `panel_usage`, melakukan lookup `part_name` dari `part_used`, lalu melakukan klasifikasi `symptom` dan `action`.

Rule symptom berjalan berbasis `part_name + symptom_comment`, dengan prioritas dan `match_type` per rule. Rule action berjalan berbasis kombinasi `job_sheet_section + part_name + symptom_comment + repair_comment`, dan saat ini masih sangat dipengaruhi oleh regex pada `repair_comment`. Setelah action terbentuk, tool memetakan `defect_category` dan `defect` dari `defect_category.csv`.

## Temuan utama dari audit data LCD SEID

### 1. Lookup `part_name` masih menjadi bottleneck terbesar

Sebanyak 898 row memiliki `part_name` kosong. Ini adalah masalah paling berdampak karena `part_name` dipakai langsung oleh engine symptom dan action. Ketika `part_name` kosong, symptom hampir pasti gagal terisi, dan action hanya akan terisi jika ada rule global yang tidak bergantung pada part, misalnya rule `EXTERNAL`, `FACTORY_RESET`, `EXPLANATION`, atau sebagian rule repair lain.

Dari sample row dengan `part_name` kosong, terlihat ada beberapa pola seperti `EXT-BERGARIS-UNIT DISUBSTITUSI`, `UNIT-UPDATE SOFTWARE`, `UNIT-ERROR-UPDATE SOFTWARE-TES-OK`, `UNIT SENSOR IR RUSAK REPAIR SENSOR IR`, dan `UNIT CEK UNIT TEST OK (PENJELASAN)`. Ini menunjukkan bahwa banyak row kosong part sebenarnya tetap mengandung sinyal bisnis yang kuat, tetapi engine symptom kehilangan kemampuan klasifikasi karena context part tidak tersedia.

Dampaknya ke output adalah dua lapis. Pertama, symptom kosong sangat tinggi karena engine symptom memang part-specific. Kedua, action pada row kosong part menjadi sangat bergantung pada rule generik berbasis repair comment, sehingga hasilnya berisiko kurang presisi.

### 2. Coverage symptom masih belum merata antar part

Sebanyak 1073 row memiliki `symptom` kosong. Dari distribusinya, 898 di antaranya berasal dari `part_name` kosong. Sisanya tersebar terutama pada `TAPE`, `PART_KIT`, `MAIN_UNIT`, `PANEL`, dan `TCON_UNIT`.

Temuan pentingnya adalah coverage symptom tampak cukup matang untuk beberapa part inti seperti `PANEL` dan `MAIN_UNIT`, tetapi masih tipis atau tidak merata untuk part-part lain. `TCON_UNIT` sering tidak menghasilkan symptom meskipun action sudah terisi. `TAPE` juga sering mempunyai symptom final seperti `LINE` atau `NO_PICTURE`, tetapi cukup banyak kasus tetap kosong. Untuk `PART_KIT`, gap coverage juga cukup jelas.

Komentar symptom yang paling sering masih gagal dipetakan antara lain `TIDAK ADA GAMBAR`, `MATI TOTAL`, `MATI`, `LCD-OTHR-Z99/KENA BOCOR AIR`, `LCD-CNCT-F21/YOUTUBE TIDAK FUNGSI`, `MATI STANDBY`, `LAYAR BERGARIS`, `LCD-PIC-C01 TIDAK ADA GAMBAR`, `LAYAR BLANK`, dan `TIDAK ADA SIARAN`. Ini menunjukkan dua jenis gap: ada pattern umum yang sebenarnya layak dipetakan tetapi belum tertutup dengan baik untuk part tertentu, dan ada pattern berkode seperti `LCD-OTHR-Z99/...` yang belum sepenuhnya dibersihkan oleh tahap normalisasi comment.

### 3. Rule symptom masih memiliki fallback yang terlalu agresif pada beberapa part

Pada master symptom terdapat rule seperti `POWER_UNIT` dengan regex `.*` yang langsung memetakan ke `TOTAL_OFF`. Secara teknis ini memang memberi coverage, tetapi juga berarti semua case `POWER_UNIT` akan dianggap `TOTAL_OFF`, tanpa mempertimbangkan isi comment yang lebih spesifik.

Masalah seperti ini bukan bug engine, melainkan kompromi data rule. Jika fallback seperti itu dipertahankan, ia sebaiknya benar-benar diposisikan sebagai rule paling bawah untuk part terkait, dan master symptom perlu diperkaya dengan rule yang lebih spesifik di atasnya.

### 4. Coverage action lebih baik daripada symptom, tetapi masih punya lubang nyata

Sebanyak 228 row memiliki `action` kosong. Distribusi terbesarnya ada pada `TAPE`, `MAIN_UNIT`, `LVDS_WIRE`, `PART_KIT`, `TCON_UNIT`, `LED_BAR`, dan `REMOTE_CONTROL`.

Ada pola yang cukup jelas: beberapa part sudah berhasil diklasifikasikan symptom-nya, tetapi action masih kosong. Contoh pada `TAPE`, banyak case `NO_PICTURE` atau `LINE` dengan repair comment yang sangat mengarah ke penggantian panel, double tape, atau part terkait, tetapi action tetap kosong. Hal serupa terlihat pada `MAIN_UNIT`, di mana symptom seperti `NO_PICTURE`, `TOTAL_OFF`, `PICTURE_NG`, atau `STANDBY` sudah terbentuk, tetapi action tidak ditemukan karena repair comment tidak tertutup oleh regex yang ada.

Ini menunjukkan bahwa coverage action belum seimbang dengan coverage symptom. Pada sebagian besar row, action engine masih belum cukup kuat membaca variasi repair comment lapangan yang berkaitan dengan kombinasi multi-part replacement.

### 5. Rule action saat ini terlalu berat ke repair comment dan rule generik replacement

Distribusi action menunjukkan dominasi besar pada `REPLACE_MAIN_UNIT`, `REPLACE_PANEL`, dan `REPAIR_POWER_UNIT`. Dominasi ini bisa jadi valid secara bisnis, tetapi dari audit row kosong part saya juga melihat banyak action seperti `REPAIR_POWER_UNIT` muncul pada kasus yang secara teks lebih dekat ke software update, reset, sensor IR, atau problem lain yang belum tentu semestinya dibaca sebagai power repair.

Ini mengindikasikan bahwa beberapa rule action yang generik atau terlalu longgar di repair comment mungkin menang lebih cepat daripada rule yang lebih semantik. Karena engine `lookup_rules` memakai `first_match_wins`, urutan prioritas menjadi sangat menentukan. Bila regex repair terlalu luas, action bisa bias ke kelas yang tidak cukup representatif.

### 6. Mapping defect category dan defect belum lengkap untuk action yang sudah dihasilkan

Sebanyak 570 row memiliki `defect_category` kosong, dan jumlah ini sama dengan row yang `defect`-nya kosong. Sebagian memang wajar karena action juga kosong. Namun ada juga action yang sudah terisi tetapi mapping defect masih kosong. Kasus terbesar berasal dari `EXTERNAL`, `ZY`, `CANCEL`, dan `REPLACE SWITCH`.

Ini menunjukkan bahwa master `defect_category.csv` belum lengkap untuk semua action yang saat ini aktif dipakai engine. Akibatnya, hasil downstream menjadi terlihat tidak selesai meskipun action engine sudah berhasil bekerja.

## Analisis per lapisan engine

### A. Lapisan normalisasi comment (`comment_synonyms`)

Tahap ini adalah titik ungkit terbesar karena memperbaiki dua engine sekaligus: symptom dan action. Saat ini isinya sudah menangkap banyak typo dan variasi lapangan seperti `STANBY`, `RESOLDRING`, `SOFTWERE`, `UPGARDE`, dan sebagainya. Ini sudah bagus.

Tetapi masih ada kelemahan struktural. Master saat ini mencampur typo correction, singkatan, istilah teknis, dan istilah yang cukup ambigu dalam satu tabel. Alias seperti `MP -> POWER UNIT` atau `SUPPLY -> UNIT` berpotensi terlalu agresif bila dipakai tanpa konteks. Beberapa pattern kode symptom seperti `LCD-OTHR-Z99/...`, `LCD-PIC-C01 ...`, `LCD-PW-A01 ...`, dan variasi slash/hyphen juga tampak belum sepenuhnya dirapikan.

Untuk LCD SEID, kualitas tahap ini sangat menentukan karena banyak symptom comment masih membawa prefix kode, format separator campuran, dan frasa tambahan yang tidak esensial. Semakin bersih comment pada tahap ini, semakin sederhana rule symptom dan action yang dibutuhkan.

### B. Lapisan lookup part (`partlist`)

`partlist.csv` berisi 1833 row dan secara volume cukup besar. Namun hasil audit memperlihatkan hampir 40 persen output LCD SEID masih tidak mendapatkan `part_name`. Itu berarti masalahnya bukan semata jumlah isi master, melainkan ada mismatch antara kode `part_used` di source dan key yang ada di master.

Kemungkinan penyebabnya antara lain format `part_used` ganda dalam satu sel, karakter separator yang tidak distandarkan, nilai kosong atau catatan bebas di kolom part, part code yang tidak ada di master, atau kebutuhan normalisasi key tambahan sebelum lookup exact.

Selama `part_name` belum lebih penuh, kualitas symptom engine akan selalu terbatas.

### C. Lapisan symptom (`symptom.csv`)

Master symptom sudah berada di format yang lebih sehat: ada `priority`, `part_name`, `match_type`, `pattern`, `symptom`, dan `notes`. Ini sudah mendukung pengelolaan rule yang relatif sistematis.

Masalah utamanya sekarang ada pada coverage dan distribusi rule. Part seperti `PANEL` dan `MAIN_UNIT` terlihat punya rule lebih banyak dan lebih matang. Part lain seperti `TCON_UNIT`, `PART_KIT`, `TAPE`, dan sebagian `LED_BAR` tampak masih kurang tertutup. Ada juga indikasi beberapa pattern umum hanya di-cover untuk part tertentu, padahal di output LCD SEID muncul lintas part.

Selain itu, sebagian pattern masih terlalu dekat ke raw text dan belum cukup memanfaatkan normalisasi comment. Misalnya variasi `LCD-PIC-C01 TIDAK ADA GAMBAR`, `LCD-PIC-C01 / TIDAK ADA GAMBAR`, `LCD-PIC-C01-TIDAK ADA GAMBAR`, dan `TIDAK ADA GAMBAR` seharusnya bisa ditekan variannya agar symptom rules lebih ringkas.

### D. Lapisan action (`actions.csv`)

Master action saat ini memakai kombinasi `job_sheet_section`, `part_name`, `symptom_comment`, dan `repair_comment`. Ini desain yang kuat, tetapi isi rule saat ini masih berat pada regex `repair_comment` dan sebagian rule penggantian part yang generik.

Lubang coverage paling jelas ada pada kasus-kasus TAPE, MAIN_UNIT, LVDS_WIRE, dan multi-part replacement. Banyak repair comment nyata seperti `UNIT-GANTI PANEL GLASS DAN MAIN UNIT`, `UNIT-GANTI PANEL DAN TAPE`, `GANTI PANEL + TCON + LVDS`, `UNIT-GANTI PANEL TCON CONVERTER LVDS`, dan sejenisnya belum tertutup cukup baik oleh rule yang ada sekarang.

Selain coverage, urutan priority juga perlu diaudit. Rule yang sangat lebar sebaiknya tidak menang sebelum rule yang lebih kontekstual.

### E. Lapisan defect mapping (`defect_category.csv`)

Master ini belum sepenuhnya mengikuti semua action yang sudah dihasilkan engine. `EXPLANATION` sudah mapped, tetapi `EXTERNAL`, `ZY`, `CANCEL`, dan beberapa action lain masih kosong di category/defect. Akibatnya hasil akhir terlihat seperti setengah jadi meskipun action sudah benar.

## Daftar improvement yang direkomendasikan

### Prioritas 1: Tingkatkan kualitas `comment_synonyms`

Perluasan dan pembersihan master ini memberi dampak terbesar dan tercepat. Fokusnya adalah menambah normalisasi untuk pattern komentar LCD SEID yang sering muncul, terutama kode symptom berprefix seperti `LCD-PIC-C01`, `LCD-PW-A01`, `LCD-PNL-L04A`, `LCD-BRD-J02`, `LCD-CNCT-F21`, dan `LCD-OTHR-Z99`. Tujuannya bukan menghapus informasi penting, tetapi mengurangi variasi penulisan yang sebetulnya mengarah ke konsep yang sama.

Prioritas tambahan adalah merapikan separator campuran seperti slash, hyphen, dan spasi ganda, serta menormalisasi variasi frasa seperti `TIDAK ADA GAMBAR`, `TIDAK ADA GAMBAR ADA SUARA`, `LAYAR BLANK`, `MATI TOTAL`, `MATI STANDBY`, `BERGARIS`, `KEDIP`, `REMOTE TIDAK FUNGSI`, `YOUTUBE TIDAK FUNGSI`, dan sebagainya.

Yang juga penting adalah meninjau alias yang terlalu ambigu. Alias yang terlalu pendek atau terlalu luas sebaiknya dipakai hati-hati agar tidak mengubah makna komentar secara berlebihan.

### Prioritas 2: Audit dan tingkatkan coverage `partlist`

Fokus utama di sini adalah menurunkan 898 row `part_name` kosong. Langkah praktisnya adalah mengambil daftar `part_used` yang gagal lookup dari output LCD SEID, lalu mengelompokkan penyebabnya. Dari pengalaman pola seperti ini biasanya terbagi menjadi beberapa jenis: part code valid tetapi belum ada di master, part code gabungan dalam satu sel, part field berisi teks bebas, dan format part yang perlu trimming atau splitting.

Perbaikan di lapisan ini akan langsung menurunkan symptom kosong dan membuat action lebih akurat karena lebih sedikit row yang jatuh ke rule global tanpa context part.

### Prioritas 3: Lengkapi coverage symptom untuk part yang masih lemah

Setelah part lookup membaik, langkah berikutnya adalah memperkaya `symptom.csv` untuk part-part yang saat ini masih tinggi symptom kosongnya, terutama `TAPE`, `PART_KIT`, `TCON_UNIT`, dan sebagian `MAIN_UNIT`.

Audit sebaiknya dimulai dari komentar symptom yang paling sering muncul tetapi gagal dipetakan. Daftar awal yang layak diprioritaskan antara lain `TIDAK ADA GAMBAR`, `MATI TOTAL`, `MATI`, `LAYAR BERGARIS`, `LAYAR BLANK`, `TIDAK ADA SIARAN`, `STANDBY`, `REMOTE TIDAK FUNGSI`, serta pattern kode berprefix yang mengarah ke masalah yang sama.

Untuk part yang punya fallback agresif seperti `POWER_UNIT`, tambahkan rule yang lebih spesifik di atas fallback tersebut agar symptom lebih representatif.

### Prioritas 4: Lengkapi coverage action untuk kasus multi-part dan part non-inti

Audit action perlu difokuskan pada kasus symptom ada tetapi action kosong. Ini adalah bucket paling informatif karena berarti context problem sudah terbaca, tetapi regex action belum mengenali tindakannya.

Part yang paling layak diprioritaskan adalah `TAPE`, `MAIN_UNIT`, `LVDS_WIRE`, `TCON_UNIT`, dan `LED_BAR`. Repair comment nyata yang sering muncul dan layak dijadikan rule baru antara lain variasi penggantian panel+tape, panel+tcon, panel+lvds, panel+main unit, panel glass, double tape, converter, dan wire terkait.

Tujuannya bukan membuat regex makin liar, tetapi menambah rule yang lebih spesifik sehingga bisa menang sebelum rule generik. Prioritas rule perlu diatur agar kasus multi-part replacement tidak jatuh ke kelas yang salah atau kosong.

### Prioritas 5: Rapikan urutan priority action agar rule generik tidak mendominasi terlalu cepat

Karena engine action memakai `first_match_wins`, urutan priority harus benar-benar mencerminkan spesifisitas bisnis. Rule yang semata-mata menyatakan replacement per part tanpa membaca detail repair comment sebaiknya tidak menutup peluang bagi rule yang lebih spesifik. Sebaliknya, rule khusus seperti factory reset, software update, explanation, cancel, external, dan repair berbasis komponen tertentu perlu ditempatkan sedemikian rupa agar tidak tertabrak oleh rule yang terlalu umum.

Indikasi saat ini, beberapa row kosong part tetap jatuh ke `REPAIR_POWER_UNIT` hanya karena repair comment memuat kata-kata umum yang cocok ke regex power repair. Ini adalah sinyal bahwa sebagian rule generik kemungkinan terlalu longgar atau terlalu dini dalam urutan prioritas.

### Prioritas 6: Lengkapi mapping `defect_category` dan `defect`

Action yang sudah stabil tetapi belum punya mapping defect sebaiknya dilengkapi agar output akhir lebih usable. Fokus pertama adalah action paling sering yang belum terpetakan, terutama `EXTERNAL`, `ZY`, dan `CANCEL`. Bila secara bisnis memang action tertentu tidak perlu defect, tetap sebaiknya diputuskan secara eksplisit apakah kolom itu sengaja kosong atau perlu kategori khusus seperti non-defect, external handling, atau replacement outside workshop.

## Rencana kerja yang disarankan

Tahap pertama adalah membuat audit exception list dari output LCD SEID. Kelompokkan menjadi lima bucket: `part_name` kosong, `symptom` kosong tapi `action` ada, `action` kosong tapi `symptom` ada, `action` ada tapi `defect_category` kosong, dan notification multi-row dengan hasil klasifikasi campuran. Lima bucket ini akan memberi daftar kerja yang sangat konkret.

Tahap kedua adalah memperbaiki `comment_synonyms` dan `partlist`. Dua master ini memberi efek paling besar ke seluruh pipeline. Setelah itu baru lanjut memperkaya `symptom.csv` dan `actions.csv`.

Tahap ketiga adalah mengaudit `symptom.csv` dan `actions.csv` berdasarkan frekuensi exception, bukan berdasarkan intuisi. Dengan begitu penambahan rule akan benar-benar menyasar pola yang paling banyak memengaruhi output LCD SEID.

Tahap keempat adalah melengkapi `defect_category.csv` untuk action yang sudah matang.

## Checklist operasional yang bisa langsung dijalankan

Mulai dengan menarik daftar seluruh `part_used` yang gagal menghasilkan `part_name`, lalu cocokkan satu per satu apakah penyebabnya missing key, format part gabungan, atau nilai bebas. Setelah itu tarik 100 komentar symptom paling sering dari row symptom kosong, lalu tandai mana yang harus masuk `comment_synonyms` dan mana yang harus masuk `symptom.csv`. Lakukan hal serupa untuk 100 repair comment paling sering dari row action kosong. Setelah coverage action membaik, audit daftar action yang belum punya `defect_category` dan putuskan mapping bisnisnya.

## Penutup

Tool LCD SEID ini tidak perlu dirombak fondasinya untuk mendapatkan peningkatan besar. Engine yang sekarang sudah cukup baik. Ruang improvement terbesarnya ada pada kualitas isi master dan disiplin pengelolaan rule. Bila dilakukan berurutan, perbaikan pada `comment_synonyms`, `partlist`, `symptom.csv`, `actions.csv`, dan `defect_category.csv` kemungkinan akan memberi kenaikan kualitas yang jauh lebih besar dibanding perubahan kode engine.
