"""A small, interactive pivot lesson using the immutable population baseline."""
import streamlit as st
from studio.aggregation import count_pivot, format_id, scalar
from studio.filters import apply_filters


DIMENSIONS = ('dusun', 'jenis_kelamin', 'kelompok_usia', 'pendidikan', 'pekerjaan')


def pivot_example(bundle):
    st.subheader('Contoh implementasi pivot')
    st.write('Pivot merangkum data menurut dua kategori sekaligus. Contoh awal: '
             'baris berisi dusun, kolom berisi jenis kelamin, dan setiap sel '
             'berisi jumlah penduduk pada kombinasi keduanya.')
    st.caption('Sumber: Data_Penduduk · Nilai: jumlah baris (jiwa). '
               'Setiap record dihitung satu kali, sama dengan indikator Jumlah baris di dashboard.')
    settings = st.session_state.setdefault('pivot_example', {
        'rows': 'dusun', 'columns': 'jenis_kelamin', 'dusun': [],
    })
    source = bundle.frame('penduduk')
    dimensions = [column for column in DIMENSIONS if column in source]
    left, right = st.columns(2)
    rows = left.selectbox('Baris pivot', dimensions,
                          index=dimensions.index(settings['rows']),
                          key='w_pivot_example_rows')
    choices = [column for column in dimensions if column != rows]
    default_column = settings['columns'] if settings['columns'] in choices else choices[0]
    columns = right.selectbox('Kolom pivot', choices,
                              index=choices.index(default_column),
                              key='w_pivot_example_columns_'+rows)
    with st.popover('Filter dusun', icon=':material/filter_alt:'):
        selected = st.multiselect('Dusun untuk contoh pivot',
                                  sorted(source.dusun.dropna().unique().tolist()),
                                  default=settings['dusun'], key='w_pivot_example_dusun')
        st.caption('Kosong berarti semua dusun. Pilihan berasal dari seluruh isi kolom dusun.')
    settings.update(rows=rows, columns=columns, dusun=list(selected))
    scope = apply_filters(source, 'penduduk', [], [
        {'column': 'dusun', 'kind': 'category', 'value': list(selected)},
    ])
    table = count_pivot(scope, rows, columns)
    if table.empty:
        st.info('Tidak ada data sesuai filter.')
        return
    st.dataframe(table, width='stretch')
    total = scalar(scope, {'method': 'count'})
    st.caption(f'Total cakupan: {format_id(total, unit="jiwa")}. '
               'Baris dan kolom Total menjumlahkan record dalam cakupan filter yang sama.')
    st.write(f'Contoh membaca tabel: **{table.index[0]}** pada kolom '
             f'**{table.columns[0]}** berisi **{format_id(table.iloc[0, 0], unit="jiwa")}**.')
    with st.expander('Lihat kode Python pivot'):
        st.code(
            'import pandas as pd\n'
            'import streamlit as st\n'
            'from studio.data import load_shared\n\n'
            f'bundle = load_shared({bundle.version!r})\n'
            'data = bundle.frame("penduduk")\n'
            f'pilihan_dusun = {list(selected)!r}\n'
            'if pilihan_dusun:\n'
            '    data = data.loc[data["dusun"].isin(pilihan_dusun)]\n\n'
            f'baris = {rows!r}\n'
            f'kolom = {columns!r}\n'
            '# Kategori kosong tetap ikut hitungan; setiap record bernilai 1.\n'
            'data = data[[baris, kolom]].astype("string").fillna("(Kosong)")\n'
            'data["_jumlah_record"] = 1\n'
            'pivot = pd.pivot_table(\n'
            '    data, index=baris, columns=kolom, values="_jumlah_record",\n'
            '    aggfunc="sum", fill_value=0, margins=True,\n'
            f'    margins_name={table.index[-1]!r}, observed=True,\n'
            ')\n'
            'st.dataframe(pivot)', language='python',
        )
    st.caption(f'Dataset {bundle.version} · Pilihan contoh disimpan di sesi browser ini.')
