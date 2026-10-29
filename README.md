# Studio Dashboard Desa

Aplikasi Python + Streamlit untuk merancang dashboard desa tanpa menulis kode. **Data dasar bersama dimuat otomatis, draft terpisah per sesi, dan hasil tersimpan dilindungi akses kelompok.** Fasilitator meninjau hasil melalui menu yang dilindungi kata sandi. Penggunaan lokal memakai SQLite tanpa layanan berbayar atau API key; deployment Cloud dengan hasil permanen memerlukan database PostgreSQL yang dikonfigurasi sendiri.

Revisi kebutuhan data bersama menggantikan alur unggah data peserta. Mode latihan tidak menyediakan unggah, ubah tipe, sunting, atau ganti dataset. Fasilitator menyiapkan versi data sebelum latihan. Peserta mengatur indikator, metode, visualisasi, filter, judul, dan urutan; warna serta ukuran/posisi memakai pengaturan otomatis.

## Menjalankan

Lingkungan yang diuji: **Python 3.12.5**, Streamlit **1.54.0**, Pandas **2.3.3**, Plotly **6.5.2**, openpyxl **3.1.5**, Pillow **10.4.0**, psycopg/psycopg-binary **3.2.13**, pytest **9.1.1**. Dependensi aplikasi dipatok pada versi tersebut dalam `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python tools/configure_access.py
streamlit run app.py
```

Jika PowerShell membatasi aktivasi, gunakan interpreter langsung:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tools/configure_access.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python tools/configure_access.py
streamlit run app.py
```

Buka alamat lokal yang dicetak Streamlit, biasanya `http://localhost:8501`. Dataset yang telah disiapkan disertakan dalam proyek; workbook asli tidak diperlukan saat aplikasi berjalan.

`configure_access.py` hanya dijalankan sekali pada instalasi baru: masukkan kata sandi fasilitator yang dikehendaki, tanpa ditampilkan pada terminal. Hash ber-salt disimpan pada `.streamlit/secrets.toml`, yang tidak masuk GitHub maupun ZIP. Jika Secrets sudah tersedia, lewati perintah itu. Gunakan `python tools/configure_access.py --rotate` untuk mengganti kata sandi, lalu restart aplikasi; akses fasilitator sebelumnya dicabut saat konfigurasi baru dibaca. Draft dan akun kelompok tetap ada.

## Akses peserta dan fasilitator

Peserta boleh merancang draft tanpa login. Untuk mengumpulkan atau melanjutkan hasil tersimpan:

1. Buka **Akses kelompok** di sidebar dan pilih **Buat akses kelompok** setelah mengisi nama. Jika sudah mempunyai akses, gunakan **Masuk kelompok** dengan kode pribadi yang sama.
2. Simpan kode yang muncul melalui **Unduh kode akses**. Nama kelompok bukan kata sandi; dua akun dengan nama sama tetap mempunyai ID dan kode berbeda. Kode hanya ditampilkan saat dibuat, tidak dimasukkan ke desain JSON.
3. Rancang dashboard, lalu buka **Simpan & Muat → Simpan Hasil Kelompok**. Fasilitator melihat versi terakhir yang benar-benar disimpan.
4. **Buka hasil tersimpan** memuat hasil milik akun itu. Bila draft berbeda, aplikasi meminta konfirmasi dan menawarkan unduhan cadangan.
5. Anggota satu kelompok dapat memakai kode yang sama pada perangkat lain untuk membuka hasil tersimpan yang sama. Draft tiap browser tetap terpisah. Jika hasil diperbarui pada perangkat lain, penyimpanan versi lama ditolak dengan pesan konflik; unduh draft lalu buka versi terbaru, sehingga tidak terjadi penimpaan diam-diam.

Peserta dapat mengedit/menghapus komponen sendiri. **Bersihkan pekerjaan sendiri**, **Mulai dari Kosong** pada draft berisi, penggantian JSON, dan keluar kelompok meminta konfirmasi sebelum mengganti ruang kerja. Tindakan tersebut tidak menghapus hasil di database, tidak mengubah kelompok lain, dan tidak mengeluarkan akses fasilitator. Contoh dashboard tetap hanya tampilan di Beranda.

Menu **Hasil Kelompok** selalu terlihat, tetapi daftar hasil hanya ditampilkan setelah masuk sebagai fasilitator. Fasilitator dapat:

- Melihat daftar kelompok, status, waktu penyimpanan dalam WIB, jumlah komponen, dan versi hasil.
- Membuka pratinjau baca saja dan mengunduh JSON kelompok terpilih. Membuka hasil tidak mengganti draft kelompok atau draft pribadi fasilitator.
- Mengarsipkan hasil dengan konfirmasi. Arsip mempertahankan data/riwayat, dan menutup penyimpanan peserta sampai fasilitator membukanya kembali.
- Membuka kembali hasil, memulihkan versi sebelumnya, atau menerapkan revisi JSON. Semua membuat versi baru, memerlukan konfirmasi atas kelompok sasaran, serta diperiksa ulang izinnya di server.

Tidak ada tombol hapus semua hasil atau hapus data dasar. Data latihan hanya diperbarui melalui prosedur versi oleh pengelola server.

**Ingat akses di browser ini** berlaku 30 hari secara bawaan, atau sampai keluar/akses dicabut. Setiap operasi tetap memeriksa token ke database, termasuk masa berlakunya. Keluar dari satu peran mencabut token peran itu saja; akses kelompok dan fasilitator terpisah. Masa berlaku dapat diatur 1–365 hari melalui `session_days`. Browser yang memblokir cookie masih dapat memakai akses sesi saat ini, tetapi pengguna perlu masuk ulang kemudian.

Kata sandi dan kode kelompok disimpan sebagai verifier PBKDF2-SHA256 ber-salt, bukan teks asli. Database menyimpan hash token sesi; cookie hanya memuat token acak yang tidak berisi nama, kata sandi, atau klaim peran. Komponen browser menggunakan cookie SameSite=Strict dan Secure pada HTTPS. Cookie ini diatur melalui JavaScript sehingga tidak HttpOnly; pemeriksaan izin/expiry/revocation tetap dilakukan di server. Gunakan HTTPS untuk deployment, dan jangan membagikan kode kelompok ke kelompok lain. Lima percobaan masuk gagal untuk sasaran/klien yang sama dibatasi selama 15 menit.

## Penyimpanan lokal dan Cloud

Secara bawaan hasil, akun, token yang masih berlaku, serta riwayat versi disimpan pada **`runtime/studio.sqlite3`**. Berkas ini bertahan saat browser disegarkan dan proses aplikasi lokal dijalankan ulang, selama disk/foldernya dipertahankan. Folder `runtime/` tidak dikemas ke ZIP dan tidak masuk GitHub. Untuk pencadangan lokal, hentikan server lalu cadangkan seluruh folder runtime ke lokasi penyimpanan pribadi.

Untuk **Streamlit Community Cloud**, pasang PostgreSQL pada layanan yang Anda kelola lalu isi Secrets berikut melalui pengaturan Cloud:

```toml
[studio_access]
facilitator_password_hash = "HASH_YANG_DIHASILKAN_SCRIPT"
session_days = 30
database_url = "postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require"
```

Hasilkan verifier dengan `python tools/configure_access.py --print-hash`, lalu masukkan nilainya ke Secrets. Contoh konfigurasi tanpa kredensial tersedia di `.streamlit/secrets.example.toml`. PostgreSQL perlu hak membuat tabel/index pada database tersebut; aplikasi membuat tabel `studio_*` saat pertama terhubung. Satu database/konfigurasi dipakai bersama seluruh sesi pelatihan, dengan pembatasan pemilik pada setiap operasi.

SQLite lokal di Community Cloud **tidak menjamin hasil permanen**; platform dapat menghilangkan penyimpanan lokal. Karena itu konfigurasi PostgreSQL diperlukan untuk hasil kelas yang harus tetap ada di Cloud. [Dokumentasi penyimpanan Streamlit](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data).

Kegagalan PostgreSQL tidak dialihkan diam-diam ke SQLite kosong. Aplikasi menampilkan masalah penyimpanan; draft tetap bisa diunduh sebagai JSON. Jika tidak mengisi URL database, aplikasi memakai mode SQLite lokal, sehingga jangan menganggap mode itu sebagai penyimpanan permanen Cloud.

Variabel lingkungan opsional yang menggantikan Secrets: `SPD_DATABASE_URL`, `SPD_FACILITATOR_PASSWORD_HASH`, dan `SPD_SESSION_DAYS`. Kata sandi/kode/token, hasil peserta, dan database tidak ditulis ke log atau dimasukkan ke paket proyek. Pengujian memakai database sementara terpisah.

## Dataset bersama

Sumber: `Template Database & Dashboard Pelayanan Desa (MK Kombangdes).xlsx`, empat sheet sumber. Sheet `Dashboard_Desa`, `Analisis_Pivot`, dan angka ilustrasi pada slide tidak menjadi sumber indikator.

Versi awal: **`desa-2026-10-29-2c0c5fcd8f-p1`**. Tanggal acuan usia tetap **29 Oktober 2026**, tidak mengikuti tanggal perangkat/sesi.

| Dataset | Record | Catatan |
| --- | ---: | --- |
| Data_Penduduk | 1.019 | 1.018 NIK unik valid; 334 KK unik valid |
| Data_Pelayanan | 20 | 12 selesai; persentase selesai 60,0% |
| Data_UMKM | 15 | 5 jenis usaha; total omzet tercatat Rp93.500.000, periode tidak diketahui |
| Potensi_Desa | 8 | Objek berbeda dari kategori potensi |

Semua angka tersebut berasal dari workbook. Data referensi tidak diasumsikan sebagai data lapangan terverifikasi. CSV di `data/examples/` adalah **simulasi sintetis terpisah**, hanya untuk mempelajari struktur; bukan pengganti data latihan bersama.

Aturan persiapan tercatat pada manifest dan disalin ke JSON desain:

- Baris yang hanya berisi rumus turunan, baris kosong, dan baris dengan ID saja tidak dihitung sebagai record. Sel di luar kolom tabel sumber tidak ikut dibaca.
- Rumus/cache Excel tidak dipercaya. Usia dihitung ulang sebagai tahun penuh pada tanggal acuan; kelompok usia 0–14, 15–59, dan 60+ tahun. Bulan pelayanan diturunkan dari tanggal dengan format `YYYY-MM`.
- Spasi teks dirapikan; kategori tidak disamakan berdasarkan tebakan.
- NIK dan KK hanya dianggap valid jika sumbernya teks 16 digit. **Satu NIK dan 19 KK yang numerik/tidak valid dikosongkan**, tanpa menebak digit. Record penduduknya tetap ada dalam hitungan baris.
- Identitas valid diganti token konsisten yang mempertahankan kesamaan/keunikan dalam versi itu. Nama dan tanggal lahir tidak disertakan dalam dataset latihan. Token bukan identitas asli; bukan jaminan anonimitas menyeluruh atas semua atribut.
- Seluruh 15 pasangan koordinat UMKM dan 8 pasangan potensi berada di luar rentang. Koordinat dikosongkan, tidak dibagi faktor tertentu. Karena itu peta tidak disediakan.
- Kolom `keterangan` potensi diperlakukan sebagai teks karena angka di dalamnya mempunyai makna/satuan berbeda. ID, NIK, KK, dan koordinat tidak ditawarkan sebagai ukuran untuk penjumlahan/rata-rata.
- Nilai kosong tetap kosong. Penjumlahan semua nilai kosong menghasilkan Tidak tersedia, bukan nol. Dugaan duplikasi dilaporkan dan tidak dibuang otomatis.

Lihat halaman **Periksa Data** untuk pratinjau tanpa identitas, tipe kolom, nilai kosong, nilai unik, pemetaan sumber, dan laporan pengolahan. Workbook/slide asli diabaikan `.gitignore`; aplikasi tidak menyalinnya ke repository atau log.

### Memasang versi baru oleh fasilitator

Peserta tidak menjalankan langkah ini. Untuk workbook terbaru dengan skema empat sheet yang sama:

```powershell
python tools/prepare_shared.py --workbook "path\workbook-terbaru.xlsx" --age-reference 2026-10-29
```

Skrip membaca workbook tanpa mengubahnya, membuat folder versi baru di `data/shared/`, menghasilkan laporan, lalu memperbarui `data/registry.json`. Perubahan workbook atau tanggal acuan menghasilkan versi berbeda. Aturan persiapan yang berubah harus memakai revisi baru, misalnya `p2`, pada pembentuk versi dan manifest di skrip; jangan menimpa versi yang sudah dipakai latihan. Skrip menolak folder versi yang sudah ada.

Periksa laporan pada `manifest.json` sebelum membagikan versi baru. Jika sebuah sheet gagal diproses, skrip mencatat kegagalannya dan menyiapkan sheet yang berhasil; jangan gunakan hasil parsial untuk latihan empat sumber ini sebelum masalah diperbaiki. Skema sumber berbeda perlu diadaptasi oleh fasilitator dalam skrip, bukan melalui unggahan peserta.

Pertahankan folder versi lama dan entri katalognya agar desain lama tetap bisa dipakai. Commit CSV, manifest, dan katalog versi yang telah diperiksa. Restart aplikasi setelah pemasangan karena baseline dipercaya tetap selama proses berjalan. Semua kelompok dalam satu latihan harus memakai versi dan tanggal acuan yang sama; JSON versi lain hanya dibuka bila versi itu memang terpasang. UI selalu menampilkan versi yang dipakai.

## Menggunakan builder

1. Isi **Nama kelompok** untuk draft, atau gunakan **Akses kelompok** untuk identitas penyimpanan. Nama akun ditampilkan setelah masuk; akses hasil ditentukan kode pribadi, bukan nama.
2. Dashboard kerja dimulai kosong. Di Beranda, **Lihat Contoh Dashboard** menampilkan contoh kependudukan, pelayanan, atau ekonomi desa hanya di halaman itu. Melihat contoh tidak menambah atau mengganti komponen kelompok. Pilih **Mulai dari Kosong** untuk mulai menyusun.
3. Periksa sumber dan peringatan pada **Periksa Data**.
4. Buka **Rancang Dashboard → Komponen**. Pilih dataset, jenis komponen, judul, pertanyaan belajar opsional, metode, dan kolom yang relevan. Aktifkan **Lihat pratinjau komponen** bila ingin memeriksa hasil sebelum menyimpan; pratinjau draft tidak muncul otomatis.
5. Untuk filter khusus komponen, cukup pilih kolom. Seluruh isi kolom otomatis menjadi pilihan pada komponen tersebut di halaman Pratinjau. Klik **Tambahkan ke dashboard**. Warna, baris, posisi, dan lebar terisi otomatis; tidak ada panel Warna & posisi. Tambah komponen lain untuk menggabungkan beberapa dataset.
6. Pada **Susunan dashboard**, gunakan **Edit, Duplikasi, Naik, Turun, Hapus**. Salinan mendapat ID baru dan filter lokal tersendiri. Komponen mengisi grid dua kolom secara berurutan tanpa celah baris kosong; Naik/Turun mengubah urutannya.
7. Pada **Identitas & tampilan**, ubah nama desa, judul/deskripsi, dan logo PNG/JPEG. Tema dan jumlah kolom memakai bawaan aplikasi. Logo maksimal 250 KB dan 2000 × 2000 piksel; disimpan sebagai gambar PNG kecil dalam JSON.
8. Pada **Filter dashboard**, cukup pilih kolom melalui **Kolom filter dashboard**. Misalnya pilih **Dusun — Penduduk, Pelayanan**. Kolom tersimpan langsung, tanpa tombol Simpan filter, penentuan jenis, atau pengisian daftar nilai. Nama dataset pada pilihan memperlihatkan cakupannya. Hilangkan pilihan kolom untuk menghapus filter.
9. Buka **Pratinjau**. Hanya komponen yang dibuat/disimpan kelompok yang tampil. Filter kategori memuat semua nilai unik dari seluruh kolom sumber; misalnya Dusun otomatis menyediakan Dusun I–V. Pilihan kosong berarti seluruh data, bukan data kosong. Kolom angka/tanggal menyediakan rentang sumber secara otomatis bila pembatasan diaktifkan. Nilai baru dipilih di sini, termasuk filter khusus di dalam masing-masing komponen. **Buka Mode Presentasi** menyembunyikan kontrol edit dan tetap menyediakan filter. **Reset** hanya mereset filter dashboard; filter lokal tetap tersimpan pada komponennya.
10. Buka **Simpan & Muat → Simpan Hasil Kelompok**, dan/atau unduh desain JSON sebelum menutup sesi. **Bersihkan pekerjaan sendiri** mengganti draft setelah konfirmasi; hasil di database serta akses login tetap ada.

Pengaturan serta draft komponen tetap berada di sesi saat berpindah tahap. Navigasi tidak memerlukan unggahan ulang data. Penyimpanan permanen dilakukan dengan tombol Simpan Hasil Kelompok; tidak ada penyimpanan otomatis setiap ketikan. Refresh dapat menghilangkan perubahan yang belum disimpan/diunduh.

Warna grafik bervariasi otomatis per kategori. Kategori yang sama tetap mendapat warna yang sama saat filter berubah; palet berulang setelah delapan warna. Grafik garis memakai garis yang menyambung dengan penanda berwarna. Kartu KPI mendapat aksen dan latar lembut yang bergantian menurut urutan komponen. Tidak ada pemilih warna manual. Warna dan posisi otomatis disertakan dalam JSON sehingga desain dapat dipulihkan dengan konsisten.

Filter di Pratinjau/Presentasi tampil sebagai deretan tombol ringkas di atas dashboard. Klik nama kolom untuk membuka pilihannya; status **Semua**, nilai terpilih, atau **Dibatasi** terlihat pada tombol, dan filter aktif ditandai warna. Tombol **Reset** berada pada baris yang sama. Pada layar sempit, tombol berpindah ke baris berikutnya. Filter khusus komponen dibuka lewat tombol **Filter** di dekat judul kartu; tidak memakai panel tersendiri di bawah judul. Detail cakupan tetap tersedia ketika filter dibuka.

Pada pembaruan dari versi awal, contoh bawaan yang benar-benar belum diedit dipindahkan dari dashboard kerja menjadi contoh Beranda. Nama kelompok dipertahankan. Desain yang sudah diubah peserta tidak dibersihkan otomatis, dan JSON yang dimuat secara eksplisit tetap memulihkan komponen yang tersimpan.

### Contoh penggunaan pivot

Buka **Panduan → Contoh implementasi pivot**. Contoh interaktif memakai data penduduk bersama dengan **Baris pivot = dusun**, **Kolom pivot = jenis_kelamin**, dan nilai **jumlah baris (jiwa)**. Pada data versi `desa-2026-10-29-2c0c5fcd8f-p1`, Dusun I berisi 123 laki-laki dan 81 perempuan, total 204 jiwa. Total seluruh dusun adalah 1.019 jiwa.

Ganti baris/kolom menjadi pendidikan, pekerjaan, atau kelompok usia untuk mencoba pengelompokan lain. Gunakan tombol **Filter dusun** untuk membatasi cakupan; pilihan kosong memakai semua dusun. Kolom dan baris Total mengikuti cakupan yang sama dengan indikator Jumlah baris. Kategori kosong tetap dihitung sebagai `(Kosong)`.

**Lihat kode Python pivot** menampilkan contoh `pd.pivot_table()` yang mengikuti pilihan saat ini dan versi data yang dipakai. Pilihan latihan berada di sesi masing-masing serta dipertahankan saat berpindah halaman. Contoh ini berada di Panduan; konfigurasi JSON tetap menyimpan komponen yang dibuat melalui builder.

### Ketepatan indikator

Satu mesin `studio/aggregation.py` dipakai oleh KPI, grafik, dan tabel. Grafik mengubah penyajian, bukan rumus. Dengan dataset, definisi, metode, dan filter sama, total indikator akan sama antarkelompok.

- Jumlah baris ≠ jumlah nilai terisi ≠ jumlah nilai unik. Jumlah penduduk dapat dipilih sebagai record sumber atau NIK unik valid; keduanya punya cakupan berbeda yang harus dijelaskan. Jumlah KK memakai `no_kk` unik valid, bukan jumlah penduduk. Angka 334 tidak mengestimasi KK yang identitasnya tidak valid.
- Jumlah UMKM adalah jumlah record unit; `jenis_usaha` unik adalah jumlah jenis usaha. Demikian pula objek dan kategori potensi.
- Metode: jumlah baris, nilai terisi, nilai unik, sum, mean, median, min, max, persentase. Metode angka hanya tersedia untuk ukuran numerik yang sesuai.
- Persentase menghitung record, bukan jumlah nilai kolom. Pilih kondisi pembilang dan penyebut; pembilang selalu dibatasi pada cakupan penyebut, lalu dikali 100. Penyebut kosong/nol menghasilkan **Tidak tersedia**. Filter global dan lokal diterapkan sebelum pembilang dan penyebut dihitung.
- Setiap komponen memiliki **Definisi indikator & cakupan** yang menjelaskan sumber, metode, kolom nilai, satuan, filter, record dalam cakupan, dan total. Rata-rata `lama_proses` menyebut status yang ikut dihitung; satuan sumber perlu dikonfirmasi.
- Tren memakai tanggal/urutan angka; pengelompokan bulan mengandung tahun dan diurutkan secara kronologis. Bulan tanpa record tidak dibuat seolah-olah mempunyai observasi nol.
- Pie/donut hanya menampilkan ukuran aditif nonnegatif dengan total positif. Rata-rata, median, nilai unik, dan persentase sebaiknya memakai batang/tabel; UI menampilkan penjelasan jika bentuk yang dipilih tidak sesuai.
- Total nilai unik, rata-rata, dan persentase dihitung ulang pada cakupan seluruh data; tidak dijumlahkan dari baris ringkasan.
- Format Indonesia diterapkan pada tampilan, sementara hasil perhitungan tetap numerik. Periode omzet dibiarkan kosong bila tidak diketahui. Pemberian satuan/periode oleh kelompok merupakan definisi/konfirmasi mereka, bukan fakta baru dari aplikasi.

Pilihan kolom **Dusun — Penduduk, Pelayanan** memperlihatkan bahwa filter memetakan `penduduk.dusun` dan `pelayanan.dusun`. Kolom bernama sama dengan tipe yang sama ditawarkan bersama cakupannya; alias berbeda tidak ditebak. Kolom `umkm.alamat` dan `potensi.alamat` tetap menjadi pilihan Alamat tersendiri dan tidak ikut filter Dusun. Filter tanggal pelayanan tidak memakai usia/tanggal lahir penduduk. Seluruh pilihan kategori selalu berasal dari kolom sumber lengkap, sehingga memilih satu nilai tidak menghilangkan pilihan lainnya. Filter lokal hanya berlaku pada satu ID komponen. Jika cakupan kosong, tampilan menyatakan **Tidak ada data sesuai filter**.

## Melanjutkan desain JSON

JSON versi skema 1 mencakup nama kelompok, identitas/tema dashboard, referensi dataset beserta SHA-256 sumber dan setiap berkas, aturan persiapan/tanggal acuan, komponen dengan ID unik, definisi perhitungan, jenis visualisasi, format, filter global/lokal, pemetaan kolom, dan posisi/lebar. Tidak menyertakan record sumber.

Desain JSON versi awal tetap dapat dimuat. Warna, jumlah kolom, ukuran, dan posisi disesuaikan ke bawaan otomatis, mengikuti urutan komponen tersimpan. Nama kelompok, ID, indikator, filter, dan hasil perhitungan dipertahankan.

Pada sesi berikutnya pilih **Simpan & Muat → Berkas desain JSON → Muat Desain**. Aplikasi memuat versi dataset yang disebut JSON melalui katalog lokal. Tidak perlu mengunggah workbook ulang. Versi/hash/aturan yang tidak sesuai ditolak dengan alasan, dan desain sesi yang sedang dikerjakan dipertahankan. Tidak ada penggantian diam-diam dengan dataset terkini.

JSON divalidasi sebelum diterapkan: jenis dan ukuran berkas, struktur/kunci, versi skema, metode yang diizinkan, batas panjang/jumlah komponen, warna, ID unik, filter, dan logo. Tidak ada evaluasi kode/rumus dari JSON. Maksimal 2 MB, 80 komponen, 20 filter dashboard, 20 filter lokal per komponen.

Referensi kolom yang hilang dipertahankan dan komponen diberi pesan untuk diperiksa, tanpa menghentikan komponen lain. Pilih **Edit** lalu pilih dataset/kolom yang tersedia. Untuk filter dashboard, hilangkan pilihan lama lalu pilih kolom yang tersedia. Pemetaan khusus dari JSON lama tetap dipertahankan sebagai pilihan tersimpan; ID dan nilai filter yang tidak dihapus tetap utuh. Mode latihan tetap memakai dataset yang terdaftar.

Data dasar adalah berkas baseline berversi dan diverifikasi SHA-256. Cache data bersama hanya menyimpan byte immutable baseline; setiap pembacaan menghasilkan DataFrame baru. Draft, filter, dan logo berada pada `st.session_state`, sedangkan hasil yang dikumpulkan disimpan pada database berdasarkan ID kelompok terverifikasi. Objek layanan database boleh digunakan bersama, tetapi setiap operasi membuka koneksi/transaksi sendiri dan memeriksa izin ke database; tidak ada cache hasil/izin per nama kelompok. Impor JSON tidak memberi akses ke akun asal, dan nama di JSON disesuaikan ke akun pemilik saat disimpan. Penyuntingan serentak setiap ketikan dan login melalui penyedia identitas eksternal belum disediakan.

## Mengunggah ke GitHub dan Streamlit Community Cloud

1. Buat repository GitHub baru. Sertakan `app.py`, `studio/`, `data/registry.json`, seluruh versi `data/shared/` yang dipakai, `data/examples/`, `requirements.txt`, `.streamlit/config.toml`, dan README ini. Untuk repository lengkap sertakan juga tests, tools, dan `requirements-dev.txt`.
2. Jangan sertakan workbook/slide asli, `.venv`, `.env`, `.streamlit/secrets.toml`, `runtime/`, log, kode akses, atau hasil peserta. `.gitignore` sudah mengecualikan bahan mentah dan berkas lingkungan; ZIP hanya memuat sumber, baseline terolah, dan contoh Secrets kosong. Tinjau daftar file sebelum commit.
3. Melalui terminal opsional, jalankan dari folder proyek:

   ```powershell
   git init
   git add app.py studio data requirements.txt requirements-dev.txt .streamlit/config.toml .streamlit/secrets.example.toml .gitignore README.md TESTING.md tests tools
   git status
   git commit -m "Studio Dashboard Desa dengan data bersama dan desain per sesi"
   git branch -M main
   git remote add origin https://github.com/USERNAME/NAMA-REPO.git
   git push -u origin main
   ```

4. Masuk ke [Streamlit Community Cloud](https://share.streamlit.io/), hubungkan akun GitHub, lalu pilih **Create app**. Pilih repository dan branch `main`; main file path **`app.py`**.
5. Pada pengaturan lanjutan pilih **Python 3.12**. Isi bagian `studio_access` pada Secrets dengan verifier kata sandi dan URL PostgreSQL sesuai bagian penyimpanan Cloud. Jangan unggah Secrets ke GitHub. Deploy dan tunggu instalasi `requirements.txt`.
6. Jika modul/data tidak ditemukan, periksa nama folder, huruf besar/kecil, dan apakah `data/shared/` serta katalog sudah masuk commit. Jangan mengandalkan workbook di laptop lokal. Referensi path dalam aplikasi relatif ke root proyek.
7. Lakukan penerimaan dua browser dan satu akses fasilitator sesuai `TESTING.md`, termasuk ingat akses setelah menutup browser dan hasil tetap ada setelah restart aplikasi. Semua peserta memakai URL, database hasil, dan versi baseline latihan yang sama; identitas/kode kelompok tetap terpisah.

Deployment GitHub/Cloud tidak dilakukan oleh proyek ini; langkah di atas disiapkan untuk akun pengguna.

## Struktur dan pengujian

```text
app.py                         entrypoint dan inisialisasi per sesi
studio/data.py                 katalog, pembacaan dan integritas baseline
studio/validation.py           normalisasi, usia, identitas, koordinat, profil
studio/filters.py              filter murni dengan pemetaan eksplisit
studio/aggregation.py          satu mesin perhitungan lintas visualisasi
studio/config.py               skema/validasi, JSON, contoh, urutan komponen
studio/security.py             hash kata sandi dan hash token sesi
studio/settings.py             Secrets/variabel lingkungan untuk akses dan database
studio/store.py                SQLite/PostgreSQL, kepemilikan, versi dan arsip
studio/access.py               login terverifikasi dan pengingat akses browser
studio/browser_session/        komponen browser tanpa dependensi JavaScript eksternal
studio/workspace.py            transisi draft dan konfirmasi penggantian
studio/rendering.py            rendering KPI, Plotly, tabel, catatan dan grid
studio/ui*.py                  beranda, builder, filter, simpan/muat, panduan
studio/ui_pivot.py              contoh pivot interaktif dan kode Python di Panduan
data/shared/<versi>/           baseline CSV terolah dan manifest
data/registry.json             versi aktif dan katalog versi yang tersedia
data/examples/                 empat CSV sintetis untuk pembelajaran
tools/prepare_shared.py        persiapan fasilitator; tanpa menimpa versi
tools/create_examples.py       pembentuk contoh CSV sintetis
tools/configure_access.py      pembentuk/rotasi verifier fasilitator, tanpa sandi di kode
tests/                        unit, integrasi, dan dua sesi AppTest
```

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
node --test tests/browser_session.test.js
```

Node.js hanya diperlukan untuk pengujian unit komponen browser, tidak untuk menjalankan aplikasi. Hasil pengujian yang benar-benar dilakukan dan langkah uji penerimaan ada di [TESTING.md](TESTING.md). AppTest dan simulasi JavaScript tidak menggantikan pengecekan browser nyata.

Fokus versi ini: empat sumber bersama, builder, akses kelompok, dan peninjauan fasilitator. Histogram, scatter, peta, drag-and-drop, unggahan data peserta, perbaikan data saat latihan, serta penyuntingan serentak setiap ketikan belum disediakan. Tidak ada tombol kosong untuk fitur tersebut. Layanan PostgreSQL eksternal dan deployment Cloud perlu dikonfigurasi pada akun pengguna; koneksi PostgreSQL produksi dan perilaku cookie pada browser nyata belum diuji di lingkungan pengerjaan.

## Dokumentasi teknologi

Implementasi mengacu pada dokumentasi resmi, dengan API yang tersedia pada versi teruji di atas:

- [Streamlit Session State](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state) dan [perilaku salinan cache data](https://docs.streamlit.io/develop/concepts/architecture/caching).
- [Pandas: pembacaan Excel dan tipe data](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html).
- [openpyxl: rumus tidak dihitung otomatis](https://openpyxl.readthedocs.io/en/stable/simple_formulae.html).
- [Plotly Python](https://plotly.com/python/) dan [integrasi Streamlit](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart).
- [Deployment Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app).
- [Secrets Streamlit](https://docs.streamlit.io/develop/concepts/connections/secrets-management), [komponen v1](https://docs.streamlit.io/develop/concepts/custom-components/components-v1/intro), dan [protokol komponen versi teruji](https://github.com/streamlit/streamlit/blob/1.54.0/component-lib/src/streamlit.ts).
- [Driver Psycopg](https://www.psycopg.org/psycopg3/docs/basic/install.html) dan [pemeriksaan izin di server](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).
