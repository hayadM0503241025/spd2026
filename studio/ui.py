from copy import deepcopy
import re
import streamlit as st
from studio.config import new_design, example_design, export_design, import_design, DesignError
from studio.constants import LABELS, PRIVATE_COLUMNS
from studio.data import ROOT, DatasetError
from studio.rendering import dashboard_header, render_dashboard
from studio.ui_filters import render_filters
from studio.validation import profile
from studio.presentation import kpi_styles
from studio.workspace import apply_design,go,start_blank,request_action,has_work
from studio.ui_access import group_panel,own_save_panel
from studio.access import group_access,facilitator_access,logout_facilitator

STAGES=('Beranda','Periksa Data','Rancang Dashboard','Pratinjau','Simpan & Muat','Hasil Kelompok','Panduan')


def styles(primary='#16715B'):
    # Only schema-validated hex colors enter CSS.
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',primary):
        primary='#16715B'
    st.markdown('''<style>
    .stApp { background: #FAFAF6; }
    .block-container { max-width: 1240px; padding-top: 2.3rem; padding-bottom: 3rem; }
    h1 { font-family: Georgia, serif !important; font-size: 2.8rem !important; font-weight: 500 !important; letter-spacing:-1.2px; }
    h1 { border-bottom:3px solid PRIMARY; padding-bottom:.5rem !important; }
    h2 { letter-spacing:-.6px; } h3 { font-weight:600 !important; }
    [data-testid="stSidebar"] { background:#EEF1E9; border-right:1px solid #DEE5D9; }
    [data-testid="stMetricValue"] { font-family: Georgia,serif; font-size:2.5rem; }
    [data-testid="stVerticalBlockBorderWrapper"] { border-radius:12px; }
    button { border-radius:8px !important; }
    [data-testid="stCaptionContainer"] { color:#53675B; }
    .studio-brand { font-weight:800; font-size:1.1rem; letter-spacing:.08em; color:#234F3D; margin:0 0 .2rem; }
    .studio-label { font-size:.7rem; letter-spacing:.18em; color:#5E7264; margin-bottom:2rem; }
    .hero-line { width:52px; height:4px; background:PRIMARY; margin:1.1rem 0; }
    .footnote { font-size:.8rem; color:#657568; border-top:1px solid #DDE4D9; padding-top:1rem; margin-top:2rem; }
    @media(max-width:640px) { h1 { font-size:2rem !important; } .block-container { padding:1rem; } }
    KPI_STYLES
    </style>'''.replace('PRIMARY',primary).replace('KPI_STYLES',kpi_styles()),unsafe_allow_html=True)


def sidebar(bundle,design,store=None):
    with st.sidebar:
        st.markdown('<div class="studio-brand">STUDIO / DESA</div><div class="studio-label">DASHBOARD & RUANG BELAJAR</div>',unsafe_allow_html=True)
        actor=group_access(store) if store else None
        if actor:
            st.session_state['w_group_name']=actor['name']
        st.text_input('Nama kelompok',value=design['group_name'],key='w_group_name',max_chars=120,disabled=bool(actor))
        design['group_name']=actor['name'] if actor else st.session_state['w_group_name']
        st.caption('Hasil tersimpan hanya dapat dikelola dengan kode akses kelompoknya. Nama yang sama tidak memberikan akses.')
        group_panel(store)
        st.radio('Tahap kerja',STAGES,key='stage',label_visibility='collapsed')
        st.divider()
        st.markdown('**Data bersama siap digunakan**')
        st.caption('Empat sumber · hanya baca · tanpa unggah data peserta')
        st.caption('Acuan usia: '+bundle.manifest['processing']['age_reference'])
        st.caption(bundle.version)
        st.caption('Simpan Hasil Kelompok atau unduh JSON sebelum menutup sesi.')
        st.button('Bersihkan pekerjaan sendiri',width='stretch',key='clear_session',on_click=request_action,args=('clear',))
        if store and facilitator_access(store):
            st.success('Akses fasilitator aktif')
            st.button('Keluar fasilitator',key='logout_facilitator',on_click=logout_facilitator,args=(store,),width='stretch')
    return st.session_state['stage']


def home(bundle,design):
    st.caption('STUDIO DASHBOARD DESA  /  MODE LATIHAN')
    st.title('Satu data.\nBanyak cerita desa.')
    st.markdown('<div class="hero-line"></div>',unsafe_allow_html=True)
    st.write('Ubah data desa menjadi informasi yang bermakna. Pilih pertanyaanmu, tentukan indikator, lalu susun dashboard bersama kelompok—tanpa menulis kode.')
    st.caption('01 Periksa data  →  02 Rancang  →  03 Presentasikan  →  04 Unduh desain')
    a,b,c=st.columns(3)
    a.button('Mulai dari Kosong',type='primary',width='stretch',key='start_blank',on_click=start_blank,args=(bundle,))
    b.button('Lanjutkan Desain',width='stretch',on_click=go,args=('Simpan & Muat',),key='continue_design')
    c.button('Periksa Data Bersama',width='stretch',on_click=go,args=('Periksa Data',),key='inspect_data')
    st.divider()
    st.subheader('Bahan yang sama untuk setiap kelompok')
    metrics=st.columns(4)
    for slot,dataset in zip(metrics,bundle.ids):
        with slot:
            with st.container(border=True):
                st.metric(LABELS[dataset],f"{bundle.manifest['datasets'][dataset]['rows']:,}".replace(',','.'))
                st.caption('record sumber valid')
    st.caption('Sumber: workbook referensi, bukan angka ilustrasi slide. Usia dihitung pada '+bundle.manifest['processing']['age_reference']+'. Data latihan ini telah dibatasi identitasnya; bukan statistik desa yang terverifikasi.')
    st.subheader('Contoh untuk inspirasi')
    examples=[('Kependudukan','Siapa warga kita?','Jumlah penduduk, KK valid, persebaran dusun, pendidikan, dan usia.'),
              ('Pelayanan','Bagaimana layanan berjalan?','Capaian layanan selesai, waktu proses, dan tren bulanan.'),
              ('Ekonomi desa','Apa yang menggerakkan desa?','UMKM, omzet yang tercatat, dan ragam objek potensi desa.')]
    for slot,(key,title,description) in zip(st.columns(3),examples):
        with slot:
            with st.container(border=True):
                st.caption(key.upper())
                st.markdown('#### '+title)
                st.write(description)
                st.button('Lihat Contoh Dashboard',key='example_'+key,width='stretch',
                          on_click=lambda name=key:st.session_state.update(home_example=name))
    st.caption('Contoh hanya ditampilkan di Beranda dan tidak ditambahkan ke dashboard kelompok. Mulai dari Kosong untuk menyusun dashboard sendiri.')
    if st.session_state.get('home_example'):
        example=st.session_state['home_example']
        st.divider()
        st.subheader('Contoh dashboard: '+example)
        st.caption('Tampilan contoh untuk dilihat. Desain kelompok tetap terpisah.')
        render_dashboard(bundle,example_design(bundle,example),key_prefix='home_example')
        st.button('Tutup contoh',on_click=lambda:st.session_state.pop('home_example',None),key='close_example')


def inspection(bundle):
    st.caption('01 / DATA BERSAMA')
    st.title('Kenali data sebelum bercerita.')
    manifest=bundle.manifest
    st.write('Pengolahan dilakukan satu kali oleh fasilitator dan dikunci dalam versi dataset. Pada mode latihan, peserta hanya mengatur desain dan filter.')
    with st.expander('Versi & aturan bersama',expanded=True):
        st.code(bundle.version,language=None)
        st.write('Tanggal acuan usia: **'+manifest['processing']['age_reference']+'**')
        st.caption('Sidik SHA-256 workbook sumber: '+manifest['source_sha256'])
        for key,value in manifest['processing'].items():
            st.write(f'**{key}:** {value}')
        st.caption('Identitas valid ditokenkan, bukan dikarang. KK/penduduk dengan identitas tidak valid tetap ikut hitungan baris sumber; hanya hitungan identitas terisi/unik yang mengecualikannya.')
    for dataset in bundle.ids:
        spec=manifest['datasets'][dataset]
        frame=bundle.frame(dataset)
        with st.expander(f"{LABELS[dataset]} · {len(frame):,} record".replace(',','.'),expanded=dataset==bundle.ids[0]):
            st.caption('Sheet sumber: '+spec['sheet'])
            for report in spec['reports']:
                if report['level']=='warning':
                    st.warning(report['message'])
                else:
                    st.caption(report['message'])
            public=frame[[c for c in frame if c not in PRIVATE_COLUMNS]]
            st.dataframe(public.head(30),hide_index=True,width='stretch')
            st.caption('Pratinjau 30 record; identitas pribadi dan token tidak ditampilkan.')
            st.dataframe(profile(frame),hide_index=True,width='stretch')
            st.caption('Pemetaan sumber → kolom latihan: '+', '.join(f'{a} → {b}' for a,b in spec['column_mapping'].items()))
    st.button('Lanjut Rancang Dashboard',type='primary',on_click=go,args=('Rancang Dashboard',),key='inspect_next')


def preview(bundle,design,presentation=False):
    dashboard_header(design,bundle)
    if not presentation:
        st.button('Buka Mode Presentasi',type='primary',on_click=lambda:st.session_state.update(presentation=True),key='open_presentation')
    if design['components']:
        render_filters(bundle,design)
    render_dashboard(bundle,design,interactive_filters=True)
    st.markdown('<div class="footnote">Studio Dashboard Desa · Data bersama, desain per kelompok · Nilai berasal dari data dan cakupan filter yang tercantum.</div>',unsafe_allow_html=True)


def save_load(bundle,design,store=None):
    st.caption('04 / SIMPAN PEKERJAAN')
    st.title('Bawa pulang desain kelompokmu.')
    st.write('JSON menyimpan nama kelompok, versi dataset, aturan indikator, visualisasi, filter, logo, dan tata letak. Record sumber dan identitas pribadi tidak dimasukkan.')
    own_save_panel(store)
    left,right=st.columns(2)
    with left:
        with st.container(border=True):
            st.subheader('Unduh desain')
            st.caption('Simpan sebelum menutup atau menyegarkan sesi. Nama kelompok tidak membuat tautan kolaborasi antarpiranti.')
            try:
                payload=export_design(design,bundle)
                safe=re.sub(r'[^A-Za-z0-9_-]+','-',design['group_name']).strip('-') or 'kelompok'
                st.download_button('Unduh Desain JSON',payload,file_name=f'dashboard-{safe}.json',mime='application/json',type='primary',key='download_design',width='stretch')
            except (DesignError,ValueError) as exc:
                st.error('Desain belum dapat diekspor: '+str(exc))
    with right:
        with st.container(border=True):
            st.subheader('Muat desain')
            st.caption('Dataset bersama yang persis sesuai akan dimuat otomatis. Versi yang belum dipasang ditolak; tidak diganti dengan versi terbaru.')
            upload=st.file_uploader('Berkas desain JSON (maksimal 2 MB)',type=['json'],key='load_design_file')
            if st.button('Muat Desain',disabled=upload is None,key='load_design',width='stretch'):
                try:
                    if upload.size>2*1024*1024:
                        raise DesignError('Desain melebihi 2 MB.')
                    restored,matched=import_design(upload.getvalue())
                    # A design file never supplies account ownership or facilitator access.
                    actor=group_access(store) if store else None
                    if actor:
                        restored['group_name']=actor['name']
                    if has_work():
                        request_action('import',design=restored)
                    else:
                        apply_design(restored)
                        st.session_state['notice']='Desain dimuat dengan dataset bersama '+matched.version+'.'
                        go('Pratinjau')
                    st.rerun()
                except (DesignError,DatasetError,OSError,ValueError,TypeError) as exc:
                    st.error('Desain tidak dimuat: '+str(exc))
    st.info('Lanjutkan melalui Akses kelompok dengan kode pribadi untuk membuka hasil tersimpan, atau muat JSON sebagai salinan desain. JSON tidak memberikan akses ke akun kelompok asalnya. Tidak perlu mengunggah ulang workbook.')


def guide():
    st.title('Dari pertanyaan ke keputusan.')
    st.write('Awali dari informasi yang dibutuhkan kepala desa atau warga. Pilih sumber yang sesuai, sepakati definisi indikator, kemudian gunakan grafik untuk menjelaskannya.')
    st.dataframe([
        {'Bentuk':'Kartu indikator','Gunakan untuk':'Satu angka utama: jumlah penduduk atau persentase layanan selesai.'},
        {'Bentuk':'Batang','Gunakan untuk':'Membandingkan kategori, misalnya jumlah warga per dusun.'},
        {'Bentuk':'Garis','Gunakan untuk':'Tren waktu. Gunakan tanggal pelayanan, dikelompokkan berdasarkan bulan dan tahun.'},
        {'Bentuk':'Pie / donut','Gunakan untuk':'Bagian dari keseluruhan; gunakan sedikit kategori dan ukuran yang dapat dijumlahkan.'},
        {'Bentuk':'Tabel ringkasan','Gunakan untuk':'Membandingkan nilai dengan teliti atau memeriksa angka pada grafik.'},
        {'Bentuk':'Catatan','Gunakan untuk':'Menjelaskan temuan, keterbatasan, atau rekomendasi kelompok.'},
    ],hide_index=True,width='stretch')
    st.subheader('Sepakati arti angka')
    st.write('Jumlah baris menghitung record. Jumlah nilai terisi mengecualikan nilai kosong. Jumlah nilai unik menghitung nilai berbeda yang terisi. Untuk jumlah KK, gunakan no_kk unik yang valid. Jumlah unit UMKM berbeda dari jumlah jenis usahanya; jumlah objek potensi berbeda dari jumlah kategorinya.')
    st.write('Persentase layanan selesai = layanan berstatus Selesai ÷ semua layanan pada cakupan yang sama × 100%. Penyebut nol ditampilkan sebagai Tidak tersedia. Rata-rata lama pelayanan harus menyebut status yang dihitung. Periode omzet tidak diketahui dari workbook.')
    st.subheader('Filter mempunyai cakupan')
    st.write('Di Rancang Dashboard → Filter dashboard, cukup pilih kolom. Seluruh isi kolom otomatis tersedia di Pratinjau. Misalnya Dusun menyediakan Dusun I sampai V tanpa mengetik pilihan tersebut. Pilihan kosong berarti semua data. Nama dataset pada pilihan kolom menunjukkan cakupannya: Dusun berlaku untuk penduduk dan pelayanan, sedangkan alamat UMKM/potensi tetap kolom terpisah. Filter khusus komponen juga cukup dipilih kolomnya; nilainya dipilih pada komponen tersebut di Pratinjau.')
    st.subheader('Latihan dengan CSV sintetis')
    st.caption('Berkas berikut terpisah dari data dasar bersama. Hanya untuk mempelajari struktur data; tidak dapat mengganti dataset latihan aplikasi.')
    for name in ('penduduk','pelayanan','umkm','potensi'):
        path=ROOT/'data'/'examples'/f'{name}.csv'
        st.download_button('Unduh CSV simulasi '+LABELS[name],path.read_bytes(),file_name=f'simulasi-{name}.csv',mime='text/csv',key='csv_'+name)
    st.subheader('Bekerja dengan dua kelompok')
    st.write('Buat akses kelompok masing-masing di sidebar, simpan kode pribadi, lalu susun dashboard. Nama kelompok yang sama tetap menjadi akun berbeda jika kodenya berbeda. Anggota satu kelompok dapat memakai kode yang sama untuk membuka hasil terakhir yang disimpan; draft setiap browser tetap terpisah. Klik Simpan Hasil Kelompok agar fasilitator dapat meninjaunya.')
    st.subheader('Akses fasilitator')
    st.write('Hasil Kelompok pada sidebar meminta kata sandi fasilitator. Setelah masuk, fasilitator dapat melihat, mengunduh, mengarsipkan, memulihkan versi, atau menerapkan revisi JSON pada kelompok yang dipilih. Pratinjau hasil hanya baca; pengelolaan memerlukan konfirmasi dan mempertahankan riwayat. Data dasar bersama tetap terkunci.')
