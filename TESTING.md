# Catatan pengujian Studio Dashboard Desa

Pengujian dilakukan pada **29 Oktober 2026**, Windows, Python 3.12.5. Dataset: `desa-2026-10-29-2c0c5fcd8f-p1`, tanggal acuan usia 2026-10-29.

## Hasil yang benar-benar dijalankan

Setelah implementasi akses kelompok, fasilitator, riwayat, konfirmasi, dan penyimpanan, seluruh pengujian dijalankan ulang:

```text
.venv\Scripts\python.exe -m pytest -q --tb=short
60 passed, 2 warnings in 27.28s

node --test tests/browser_session.test.js
4 passed, 0 failed
```

Versi: Streamlit 1.54.0, Pandas 2.3.3, Plotly 6.5.2, openpyxl 3.1.5, Pillow 10.4.0, psycopg/psycopg-binary 3.2.13, pytest 9.1.1, Node.js 24.11.0. Driver PostgreSQL dipasang di virtual environment proyek; pustaka yang telah tersedia digunakan dari lingkungan host melalui system-site-packages.

### Tambahan contoh pivot — 30 Oktober 2026

Seluruh suite Python dijalankan ulang setelah menambahkan contoh pivot di Panduan: **66 passed, 2 warnings in 28.20s**. Direktori sementara baru di `outputs/` dipakai melalui `--basetemp`, dengan `-p no:cacheprovider`, karena percobaan awal terhenti pada izin akses direktori sementara/cache lama sebelum tes berjalan.

Pengujian tambahan memeriksa jumlah penduduk per dusun dan jenis kelamin, kesamaan total pivot dengan indikator Jumlah baris, kategori kosong, benturan label Total, cakupan kosong, penolakan dimensi pribadi/tidak tersedia, dan sumber yang tetap utuh. AppTest memeriksa filter dusun, perubahan baris/kolom, pemulihan pilihan setelah navigasi, eksekusi contoh kode yang menghasilkan tabel sama, serta dua sesi dengan pilihan berbeda tanpa mengubah desain dashboard. Pemeriksaan ini belum mencakup tampilan browser nyata.

### Pivot sebagai komponen dashboard — 30 Oktober 2026

Sesudah menambahkan halaman Tambah Pivot, seluruh suite Python kembali lulus: **95 passed, 2 warnings in 32.72s**. Perintah menggunakan `-q --tb=short --maxfail=3 -p no:cacheprovider` dan `--basetemp` yang menunjuk direktori baru di `outputs/`.

Pengujian tambahan mencakup:

- Pemilihan keempat dataset, baris/kolom, tampilan tabel sebelum pilihan grafik, dan penambahan ke Pratinjau dengan tabel serta grafik bersama. Pasangan tersebut juga tampil dalam mode presentasi.
- Grafik batang berkelompok, bertumpuk, horizontal, serta heatmap memakai sel pivot yang sama dan mengecualikan total dari grafik.
- Sembilan metode perhitungan: sel serta total baris/kolom memakai mesin indikator yang sama, termasuk rata-rata berbobot oleh record, jumlah unik, dan persentase. Index sumber yang berulang tidak menggandakan record.
- Pengelompokan tanggal lintas tahun, kategori kosong, semua ukuran kosong, penyebut nol, serta cakupan tanpa record.
- Edit mempertahankan ID; duplikasi memisahkan konfigurasi; draft bertahan setelah navigasi; draft komponen biasa tetap utuh; bersihkan pekerjaan memerlukan konfirmasi.
- Dua sesi menggunakan dataset yang sama dengan desain/filter berbeda. Saat metode dan filter disamakan, total kedua sesi sama walau bentuk grafik berbeda.
- Filter global dan lokal beririsan, JSON memuat kembali pivot, dan penyimpanan hasil kelompok mempertahankan konfigurasinya. Komponen JSON lama tetap dapat dimuat. Kolom pribadi dan konfigurasi pivot tidak sah ditolak.

Browser dicoba kembali melalui skill Browser, tetapi tidak ada browser yang tersedia. Alur di atas diuji melalui AppTest dan perhitungan/objek grafik, belum melalui pemeriksaan visual browser langsung. Tidak ada data dasar atau hasil kelompok nyata yang diubah oleh pengujian.

### Sebelas pilihan visualisasi pivot — 30 Oktober 2026

Setelah menambahkan grafik garis, area, scatter, bubble, pie, donut, dan treemap, suite Python lulus: **116 passed, 2 warnings in 37.53s**. Perintah memakai `-q --tb=short --maxfail=3 -p no:cacheprovider` dan `--basetemp` baru di `outputs/`. Dua peringatan tetap berasal dari protobuf.

Pengujian memeriksa nilai grafik pada seluruh 11 bentuk: tiga varian batang, garis, area, scatter, bubble, pie, donut, heatmap, dan treemap. Grafik mengecualikan total pivot; jumlah irisan pie/donut dan daun treemap sesuai jumlah sel tabel. Pilihan metode dan validasi JSON memakai daftar visualisasi yang sama. Pie/donut mempertahankan warna bagian saat filter berubah. Nilai kosong pada garis tidak diubah menjadi nol; bubble melewati ukuran kosong. Grafik yang membutuhkan nilai positif/nonnegatif menangani cakupan nol/negatif dengan penjelasan tanpa mengganti nilai tabel.

AppTest mencoba tujuh bentuk baru melalui pilihan Visualisasi pivot, penambahan ke dashboard, tampilan tabel bersama grafik di Pratinjau, simpan/muat JSON, dan pembukaan ulang untuk edit. Tabel dan indikator tetap sama saat bentuk grafik diganti. Pengujian ini tidak mencakup pemeriksaan visual browser langsung; batas verifikasi browser di atas tetap berlaku.

| Pemeriksaan | Hasil |
| --- | --- |
| Jumlah baris, nilai terisi, nilai unik, dan KK unik | Lulus |
| Persentase, pembilang dalam cakupan penyebut, penyebut nol | Lulus |
| Nilai ukuran kosong tidak diubah menjadi nol | Lulus |
| Larangan menjumlahkan identitas, koordinat, keterangan campuran | Lulus |
| Filter kategori/angka/tanggal, pemetaan eksplisit, filter lokal | Lulus |
| Filter pelayanan tidak diterapkan ke tanggal lahir | Lulus |
| Pengurutan bulan lintas tahun | Lulus |
| Acuan usia, ulang tahun, tanggal masa depan/kosong | Lulus |
| Validasi koordinat tanpa koreksi dugaan | Lulus |
| NIK/KK numerik tidak direkonstruksi; token menjaga kesamaan | Lulus |
| Baris rumus saja/kosong dan sel di luar header tabel | Lulus |
| Ekspor/impor JSON mempertahankan identitas/desain/filter | Lulus |
| Penolakan JSON rusak/besar/kunci ganda/NaN/ID ganda/versi berbeda/warna dan metode tidak sah | Lulus |
| Kolom hilang diberi pesan dan dipertahankan untuk pemetaan ulang | Lulus |
| Perubahan berkas baseline terdeteksi oleh SHA-256 | Lulus |
| Salinan DataFrame/metadata tidak mengubah baseline | Lulus |
| Desain lama dimuat dengan warna/grid otomatis tanpa mengubah ID, urutan, filter, dan nilai indikator | Lulus |
| Warna kategori bervariasi dan tidak bergeser ketika kategori lain difilter | Lulus |
| Pemilih warna dan panel Warna & posisi tidak muncul pada builder | Lulus, AppTest |
| Tambah, edit jenis visualisasi, duplikasi, naik, hapus komponen melalui UI Streamlit | Lulus, AppTest |
| Filter dashboard dibuat/dihapus cukup dengan memilih kolom; seluruh isi otomatis tersedia di Pratinjau | Lulus, AppTest |
| Pratinjau baru kosong; contoh hanya di Beranda dan tidak mengubah desain kelompok | Lulus, AppTest |
| Filter lokal hanya memilih kolom di builder, lalu memilih nilai pada komponen di Pratinjau/Presentasi | Lulus, AppTest |
| Kolom angka/tanggal berawal tanpa pembatasan dan memakai rentang sumber otomatis | Lulus, AppTest |
| Pemilihan ulang kolom mempertahankan ID, nilai, dan pemetaan khusus dari JSON lama | Lulus |
| Contoh lama yang belum diedit dapat dibersihkan tanpa menghapus pekerjaan yang telah diubah | Lulus |
| Draft komponen tetap ada setelah pindah tahap | Lulus, AppTest |
| Tiga contoh, halaman pemeriksaan, pratinjau, simpan/muat, panduan | Lulus, AppTest |
| Mode Presentasi menyembunyikan kontrol edit dan bisa kembali ke builder | Lulus, AppTest |
| Dua sesi aplikasi independen memakai baseline/aturan sama dan desain berbeda | Lulus, dua AppTest |
| Nama kelompok sama tidak menyatukan sesi; bersihkan sesi tidak memengaruhi sesi lain | Lulus, dua AppTest |
| A tidak dapat membaca/menyimpan/memulihkan hasil B meski nama/desain diubah | Lulus, backend dan dua akun AppTest |
| Token palsu atau klaim is_admin di klien tidak membuka halaman hasil | Lulus |
| Kata sandi dan kode di-hash dengan salt; token mentah tidak disimpan dalam database/JSON hasil | Lulus |
| Batas percobaan login tersimpan dan tetap berlaku setelah layanan dibuka ulang | Lulus |
| Token kedaluwarsa/logout/rotasi sandi tidak dapat dipakai kembali | Lulus |
| Akun, hasil, dan akses yang masih berlaku bertahan setelah Store SQLite dibuka ulang | Lulus |
| Dua simpan serentak dari versi sama menghasilkan satu simpan dan satu konflik | Lulus |
| Arsip/pemulihan/revisi fasilitator hanya memengaruhi kelompok sasaran dan menyimpan riwayat | Lulus |
| Pratinjau fasilitator tidak mengganti draft pribadi atau hasil peserta | Lulus, AppTest |
| Bersihkan/Mulai kosong meminta konfirmasi, menyimpan akses login, dan tidak menghapus hasil database | Lulus, AppTest |
| Token dari transport cookie dipulihkan hanya setelah verifikasi server | Lulus, transport disimulasikan pada AppTest |
| Atribut cookie aman, pemisahan dua peran, penolakan pesan lintas-origin, dan tidak ada loop rerun | Lulus, empat unit JavaScript dengan DOM simulasi |

Verifikasi tambahan menggunakan konfigurasi lokal yang benar-benar dipasang dilakukan tanpa mencetak kata sandi: login menghasilkan peran `facilitator`, lalu logout membuat token tersebut tidak berlaku. Tidak ada akun/hasil peserta nyata yang dipakai dalam pengujian; pytest diarahkan ke database sementara untuk setiap tes.

Skenario dua sesi dijalankan bergantian dalam satu proses uji menggunakan dua instance `AppTest.from_file`, dengan Session State terpisah dan cache baseline yang sama:

1. Sesi A/B memakai referensi dataset dan aturan persiapan yang identik. Masing-masing mulai kosong, lalu membuat sendiri satu KPI penduduk dan satu grafik per dusun; ID komponen berbeda.
2. Masing-masing memilih kolom Dusun sebagai filter. Di Pratinjau semua pilihan Dusun I–V tersedia tanpa pembatasan, dan keduanya menampilkan **1.019 jiwa**.
3. A memilih **Dusun I** dan menampilkan **204 jiwa**; B dijalankan ulang dan tetap **1.019 jiwa** dengan filter kosong.
4. A mengedit grafik menjadi batang vertikal dan mengubah judul; B tetap batang horizontal dengan judul semula.
5. B memakai filter Dusun I yang sama. Seluruh nilai KPI kedua sesi identik, dan total mesin indikator kedua grafik sama.
6. Nama B diganti menjadi nama A. Reset filter dan Bersihkan Sesi pada A tetap tidak mengubah nama, desain, atau filter B.
7. Desain B diekspor dan diimpor kembali, mempertahankan nama, versi dataset, dan filter.

Server revisi ini juga benar-benar dijalankan dan diperiksa:

```text
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502 --server.headless true
GET /_stcore/health → HTTP 200, ok
GET /              → HTTP 200
python -m compileall -q app.py studio tools tests → berhasil
```

Server pengujian dihentikan setelah pemeriksaan. Jalankan kembali dengan `streamlit run app.py` untuk menggunakan aplikasi.

Dua peringatan pytest berasal dari dependensi protobuf tentang kompatibilitas Python 3.14; pengujian dijalankan pada Python 3.12. Pemeriksaan `pip check` pada lingkungan global host juga melaporkan konflik NumPy dengan OpenCV/TensorFlow yang telah terpasang di host. Kedua paket itu bukan dependensi aplikasi dan tidak digunakan. Instalasi bersih dalam virtual environment dianjurkan seperti di README; instalasi pada lingkungan bersih dan deployment Cloud belum dijalankan.

## Batas verifikasi browser

**Dua sesi browser nyata dan pemeriksaan visual desktop/ponsel belum dijalankan.** Koneksi Browser tersedia sebagai alat, tetapi melaporkan tidak ada browser, dan daftar browser kosong. Pengujian AppTest memverifikasi eksekusi aplikasi, kontrol, perhitungan, dan Session State; tidak memverifikasi pixel/layout, JavaScript Plotly, tooltip, upload/download pada browser, atau koneksi WebSocket dua jendela nyata.

UI file uploader JSON dan penyimpanan cookie lintas-restart browser belum diuji melalui browser. Pengujian cookie memakai simulasi protokol/DOM dan transport AppTest, bukan browser sungguhan. Fungsi parser, validator, pemilihan versi dataset, dan pemulihan JSON diuji langsung.

Koneksi PostgreSQL produksi belum dijalankan karena tidak ada database eksternal yang dikonfigurasi. Driver resmi 3.2.13 berhasil dipasang/diimpor; pengujian negatif memastikan koneksi gagal tidak dialihkan ke SQLite kosong. Operasi penyimpanan berhasil diuji pada SQLite. GitHub dan Streamlit Community Cloud belum dipublikasikan. Langkah berikut perlu dilakukan di lingkungan browser/database tujuan.

## Uji penerimaan dua browser

Jalankan aplikasi lokal, atau gunakan satu URL deployment yang sama. Gunakan dua browser berbeda, atau jendela biasa dan privat dengan koneksi terpisah. Jangan menganggap dua nama kelompok sebagai dua sesi.

| Langkah | Tindakan | Hasil yang diharapkan |
| --- | --- | --- |
| 1 | Buka sesi A dan B. Periksa versi/tanggal acuan pada sidebar | Keduanya `desa-2026-10-29-2c0c5fcd8f-p1`, acuan 2026-10-29 |
| 2 | Beri label Kelompok A dan Kelompok B | Label berbeda; kedua beranda memuat empat dataset otomatis |
| 3 | Buka Pratinjau sebelum membuat komponen, lalu lihat contoh di Beranda | Pratinjau kosong. Contoh hanya tampak di Beranda; desain kelompok tidak berubah |
| 4 | Pada kedua sesi buat KPI jumlah baris penduduk dengan satuan jiwa, grafik per dusun, dan pilih kolom Dusun sebagai filter. Di Pratinjau A pilih Dusun I, B biarkan kosong | Semua Dusun I–V tersedia. A 204 jiwa, B 1.019; seluruh data tetap ditampilkan bila pilihan kosong |
| 5 | A ubah judul/jenis grafik penduduk, duplikasi komponen dan beri filter lokal | Hanya desain A berubah; salinan dan aslinya tetap independen. Warna kategori dan aksen KPI bervariasi otomatis |
| 6 | B pilih Dusun I dan indikator/metode/filter lokal yang sama dengan grafik A, tetapi gunakan bentuk grafik berbeda | KPI dan total pada Definisi indikator & cakupan sama; bentuk grafik boleh berbeda |
| 7 | Ganti nama kedua sesi menjadi nama yang sama, lalu reset filter A | B tetap mempunyai filter dan desainnya sendiri |
| 8 | Pilih kolom Usia dan Tanggal di builder, kemudian aktifkan pembatasan rentang di Pratinjau | Jenis dan rentang sumber tersedia otomatis. Hanya komponen dari sumber yang tercantum berubah |
| 9 | Pilih kombinasi filter yang tidak mempunyai record | Komponen terkait menyatakan Tidak ada data sesuai filter |
| 10 | Buka Mode Presentasi, cek desktop lalu layar sempit | Kontrol edit tersembunyi, filter tetap berfungsi, teks dan angka terbaca |
| 11 | Periksa tooltip, legenda pie/donut, zoom/pan grafik yang relevan | Interaksi Plotly berjalan tanpa error JavaScript |
| 12 | Unduh desain A, buka sesi baru C, Muat Desain JSON tersebut | Nama, judul, indikator, warna, urutan, lebar, filter dan versi pulih; tidak perlu unggah workbook |
| 13 | Pada salinan JSON ubah versi menjadi versi yang tidak terpasang, kemudian coba muat | Ditolak dengan alasan; desain yang sedang dikerjakan tidak tertimpa |
| 14 | Pada salinan JSON ganti kolom dimensi dengan nama lama/tidak ada | Komponen terkait diberi pesan; komponen lain tetap berfungsi; Edit memungkinkan pilih kolom yang ada |
| 15 | Unggah logo valid PNG/JPEG, ekspor desain lalu muat kembali | Logo pulih; berkas terlalu besar/format salah ditolak |
| 16 | Bersihkan pekerjaan sendiri pada A, lalu batalkan; ulangi dan konfirmasikan | Pembatalan mempertahankan draft. Konfirmasi mengosongkan draft A tanpa menghapus login, hasil database, B, atau C |

## Uji penerimaan akses dan penyimpanan

1. Pada browser A dan B, buat akses kelompok masing-masing dan unduh kode pribadi. Coba gunakan nama yang sama: ID/kode tetap berbeda dan tidak membuka hasil satu sama lain.
2. Simpan dashboard A dan B melalui Simpan Hasil Kelompok. Buka menu Hasil Kelompok tanpa login fasilitator: hanya formulir masuk yang tampil. Kata sandi salah harus ditolak.
3. Masuk sebagai fasilitator dengan kata sandi yang dikonfigurasi. Daftar kedua hasil tampil. Buka setiap hasil: draft peserta dan draft pribadi fasilitator tidak berubah, serta filter pratinjau hasil tidak dapat diedit.
4. Pilih Ingat akses, tutup dan buka kembali browser yang sama: akses yang masih berlaku dipulihkan tanpa sandi ulang. Uji Keluar: token lama harus ditolak, termasuk pada tab lain ketika melakukan operasi berikutnya. Coba dengan cookie diblokir: akses sesi tetap berfungsi, tetapi pengingat tidak tersedia dan dijelaskan di sidebar.
5. Uji tombol Mulai dari Kosong, Bersihkan pekerjaan sendiri, Keluar kelompok, dan Muat JSON pada draft berisi. Semua harus meminta konfirmasi; pembatalan tidak mengubah draft. Cadangan JSON tersedia sebelum melanjutkan. Hasil database tetap tersimpan.
6. Arsipkan satu hasil dari akses fasilitator setelah konfirmasi. Kelompok lain tetap utuh. Kelompok yang diarsipkan tidak bisa menimpa hasil sampai fasilitator membuka kembali. Pulihkan versi lama: muncul revisi baru dengan riwayat lama tetap tersedia.
7. Coba revisi JSON melalui Riwayat & pengelolaan. Pastikan sasaran kelompok ditunjukkan sebelum konfirmasi; nama/kode dalam berkas tidak boleh menentukan kepemilikan akun.
8. Buka kode kelompok yang sama pada dua perangkat. Muat versi sama, ubah dan simpan pada A, lalu simpan versi lama pada B: B mendapat konflik dan draftnya tetap dapat diunduh.
9. Restart server lokal dengan runtime yang sama: akun/hasil/riwayat tetap ada. Untuk Cloud, ulangi pada PostgreSQL yang benar-benar dikonfigurasi, termasuk setelah restart/redeploy aplikasi. Jangan menggunakan SQLite Cloud sebagai bukti penyimpanan permanen.

Simpan hasil pelaksanaan browser dan versi dataset bersama catatan pelatihan. Hindari menyimpan desain peserta atau data mentah ke repository.
