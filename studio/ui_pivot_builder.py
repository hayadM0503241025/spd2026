"""Dataset → axes → pivot table → visualization → one saved component."""
from copy import deepcopy
import json
import pandas as pd
import streamlit as st
from studio.aggregation import compute_component, public_columns, numeric_columns
from studio.config import new_component
from studio.constants import LABELS, METHODS, NUMERIC_METHODS, PIVOT_VISUALS, pivot_visuals
from studio.rendering import render_pivot_table, render_pivot_chart
from studio.ui_builder import index_of, condition_editor, save_current
from studio.ui_filters import local_filter_editor, render_local_filters
from studio.workspace import go


def time_group(series, previous, label, key):
    if not pd.api.types.is_datetime64_any_dtype(series):
        return 'category'
    groups=['month','year','day']
    return st.selectbox(label,groups,index=index_of(groups,previous),
                         format_func=lambda value:{'month':'Bulan & tahun','year':'Tahun','day':'Tanggal'}[value],key=key)


def pivot_builder(bundle,design):
    st.caption('RUANG RANCANG / PIVOT')
    st.title('Tambah pivot ke dashboard.')
    st.button('Kembali ke Rancang Dashboard',on_click=go,args=('Rancang Dashboard',),key='pivot_back')
    st.write('Pilih sumber, baris, dan kolom. Tampilkan tabelnya, lalu pilih grafik. '
             'Tabel dan grafik disimpan bersama sebagai satu komponen dashboard.')
    editing=st.session_state.get('pivot_editing_id')
    existing=next((item for item in design['components'] if item['id']==editing and item['kind']=='pivot'),None)
    initial=deepcopy(st.session_state.get('pivot_draft') or existing or new_component(
        'penduduk','pivot','Analisis pivot desa',dimension='dusun',unit='jiwa',
        pivot={'column':'jenis_kelamin','granularity':'category','visualization':'bar'}))
    epoch=st.session_state.get('pivot_editor_epoch',0)
    base=f'w_pivot_builder_{epoch}'
    source=st.selectbox('Dataset sumber pivot',list(bundle.ids),index=index_of(list(bundle.ids),initial['dataset']),
                         format_func=lambda value:LABELS[value],key=base+'_dataset')
    frame=bundle.frame(source)
    prefix=base+'_'+source
    choices=public_columns(frame)
    if len(choices)<2:
        st.info('Dataset ini belum memiliki dua kolom publik untuk pivot.')
        return
    item=deepcopy(initial)
    item.update(dataset=source,kind='pivot')
    item['id']=existing['id'] if existing else '0'*32
    left,right=st.columns(2)
    rows=left.selectbox('Baris pivot',choices,index=index_of(choices,initial['dimension']),key=prefix+'_rows')
    column_choices=[column for column in choices if column!=rows]
    columns=right.selectbox('Kolom pivot',column_choices,index=index_of(column_choices,initial['pivot']['column']),
                             key=prefix+'_columns_'+rows)
    item['dimension']=rows
    item['pivot']['column']=columns
    with left:
        item['granularity']=time_group(frame[rows],initial['granularity'],'Kelompok waktu baris',prefix+'_time_'+rows)
    with right:
        item['pivot']['granularity']=time_group(frame[columns],initial['pivot']['granularity'],
                                               'Kelompok waktu kolom',prefix+'_column_time_'+columns)
    item['title']=st.text_input('Judul pivot',value=initial['title'],max_chars=200,key=prefix+'_title')
    with st.expander('Nilai & filter pivot',expanded=bool(initial['local_filters']) or initial['method']!='count'):
        methods=[method for method in METHODS if method not in NUMERIC_METHODS or numeric_columns(frame)]
        item['method']=st.selectbox('Metode perhitungan pivot',methods,index=index_of(methods,initial['method']),
                                    format_func=lambda value:METHODS[value],key=prefix+'_method')
        item['value_column']=None
        item['numerator'],item['denominator']=[],[]
        if item['method'] not in ('count','percentage'):
            values=numeric_columns(frame) if item['method'] in NUMERIC_METHODS else [column for column in frame if column!='ID']
            item['value_column']=st.selectbox('Kolom nilai pivot',values,index=index_of(values,initial['value_column']),
                                              key=prefix+'_value_'+item['method'])
        if item['method']=='percentage':
            st.caption('Pembilang dibatasi pada cakupan penyebut, sama dengan indikator dashboard.')
            a,b=st.columns(2)
            with a:
                item['numerator']=condition_editor(frame,initial['numerator'],'pembilang',prefix+'_numerator')
            with b:
                item['denominator']=condition_editor(frame,initial['denominator'],'penyebut',prefix+'_denominator')
        default_unit=initial['unit'] if source==initial['dataset'] else {
            'penduduk':'jiwa','pelayanan':'layanan','umkm':'unit','potensi':'objek'}[source]
        if item['method'] in NUMERIC_METHODS and (item['method']!=initial['method'] or item['value_column']!=initial['value_column']):
            default_unit={'usia':'tahun','omset':'Rp'}.get(item['value_column'],'')
        a,b=st.columns(2)
        item['unit']=a.text_input('Satuan pivot',value='%' if item['method']=='percentage' else default_unit,
                                   max_chars=200,key=prefix+'_unit_'+item['method'])
        item['decimals']=b.number_input('Desimal pivot',min_value=0,max_value=4,value=initial['decimals'],key=prefix+'_decimals')
        if item['value_column']=='omset':
            item['period']=st.text_input('Periode omzet (jika sudah dikonfirmasi)',value=initial['period'],max_chars=200,key=prefix+'_period')
            st.caption('Workbook tidak menjelaskan periode omzet; kosongkan jika belum diketahui.')
        old_filters=initial['local_filters'] if source==initial['dataset'] else []
        item['local_filters']=local_filter_editor(frame,old_filters,prefix+'_filters')
    # Store the actual draft object so filter callbacks update this session's
    # draft before the next rerun. Saved components always receive a deep copy.
    st.session_state['pivot_draft']=item
    render_local_filters(bundle,item,prefix+'_draft')
    signature=json.dumps({'version':bundle.version,**{key:item[key] for key in (
        'dataset','dimension','granularity','method','value_column','numerator','denominator')},
        'column':columns,'column_granularity':item['pivot']['granularity']},sort_keys=True)
    if existing and 'pivot_ready_signature' not in st.session_state:
        st.session_state['pivot_ready_signature']=signature
    if st.button('Tampilkan Pivot',type='primary',key='show_pivot'):
        st.session_state['pivot_ready_signature']=signature
    if st.session_state.get('pivot_ready_signature')!=signature:
        st.info('Klik Tampilkan Pivot untuk melihat tabel sebelum memilih visualisasi.')
        return
    try:
        result=compute_component(bundle,design,item)
    except (ValueError,KeyError,TypeError) as exc:
        st.warning('Pivot perlu diperiksa: '+str(exc))
        return
    st.subheader('Hasil pivot')
    if result.rows:
        render_pivot_table(result,item)
    else:
        st.info('Tidak ada data sesuai filter.')
    visuals=pivot_visuals(item['method'])
    item['pivot']['visualization']=st.selectbox('Visualisasi pivot',visuals,
                index=index_of(visuals,initial['pivot']['visualization']),format_func=lambda value:PIVOT_VISUALS[value],
                key=prefix+'_visual_'+item['method'])
    if result.rows:
        render_pivot_chart(bundle,result,item,prefix+'_preview')
    st.caption(result.explanation)
    st.button('Simpan perubahan pivot' if existing else 'Tambahkan ke Dashboard',type='primary',key='save_pivot',
               disabled=not existing and len(design['components'])>=80,
               on_click=save_current,args=(bundle,item,existing['id'] if existing else None,True))
