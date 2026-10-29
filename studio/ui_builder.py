from copy import deepcopy
import base64
from io import BytesIO
import pandas as pd
from PIL import Image, UnidentifiedImageError
import streamlit as st
from studio.aggregation import public_columns, numeric_columns
from studio.constants import LABELS, KINDS, METHODS, NUMERIC_METHODS
from studio.config import (new_component, check_component, uid, ordered_components,
                           move_component, duplicate_component, DesignError)
from studio.rendering import render_component, render_dashboard
from studio.ui_filters import local_filter_editor, filter_manager
from studio.presentation import DEFAULT_COLUMNS, automatic_color, apply_visual_defaults


def index_of(options,value):
    return options.index(value) if value in options else 0


def edit_target(component_id=None):
    st.session_state['editing_id']=component_id
    st.session_state['editor_epoch']=st.session_state.get('editor_epoch',0)+1
    st.session_state.pop('component_draft',None)


def save_current(bundle,item,existing_id):
    design=st.session_state['design']
    try:
        item=deepcopy(item)
        item['id']=existing_id or uid()
        check_component(item,bundle,design['dashboard']['columns'])
        if existing_id:
            index=next(i for i,c in enumerate(design['components']) if c['id']==existing_id)
            design['components'][index]=item
        else:
            design['components'].append(item)
        apply_visual_defaults(design)
        edit_target()
        st.session_state['notice']='Komponen disimpan pada sesi kelompok ini.'
    except DesignError as exc:
        st.session_state['notice_error']=str(exc)


def change_component(action,component_id,offset=0):
    design=st.session_state['design']
    if action=='duplicate':
        duplicate_component(design,component_id)
    elif action=='move':
        move_component(design,component_id,offset)
    elif action=='delete':
        design['components']=[c for c in design['components'] if c['id']!=component_id]
        if st.session_state.get('editing_id')==component_id:
            edit_target()


def condition_editor(frame,conditions,label,prefix):
    old=conditions[0] if conditions else {}
    options=[None]+public_columns(frame)
    column=st.selectbox(f'Kolom {label}',options,index=index_of(options,old.get('column')),
                         format_func=lambda x:'Semua record dalam cakupan' if x is None else x,key=prefix+'_column')
    if column is None:
        return []
    operations=['equals','not_equals','not_null','is_null']
    if pd.api.types.is_numeric_dtype(frame[column]):
        operations+=['gte','lte']
    labels={'equals':'Sama dengan','not_equals':'Tidak sama dengan','not_null':'Terisi','is_null':'Kosong','gte':'Lebih besar atau sama','lte':'Lebih kecil atau sama'}
    operator=st.selectbox(f'Kondisi {label}',operations,index=index_of(operations,old.get('operator')),
                          format_func=lambda x:labels[x],key=prefix+'_'+column+'_operator')
    value=None
    if operator not in ('not_null','is_null'):
        if operator in ('gte','lte'):
            value=st.number_input(f'Nilai {label}',value=float(old.get('value') or 0),key=prefix+'_'+column+'_number')
        else:
            series=frame[column].dropna()
            values=sorted(series.dt.strftime('%Y-%m-%d').unique().tolist()) if pd.api.types.is_datetime64_any_dtype(series) else sorted(series.unique().tolist())
            if not values:
                st.warning('Kolom kosong; pilih kondisi Kosong/Terisi.')
                return []
            value=st.selectbox(f'Nilai {label}',values,index=index_of(values,old.get('value')),key=prefix+'_'+column+'_value')
    return [{'column':column,'operator':operator,'value':value}]


def component_editor(bundle,design):
    editing=st.session_state.get('editing_id')
    existing=next((c for c in design['components'] if c['id']==editing),None)
    draft=st.session_state.get('component_draft')
    initial=deepcopy(draft) if draft else deepcopy(existing) if existing else new_component()
    epoch=st.session_state.get('editor_epoch',0)
    prefix=f'w_editor_{epoch}'
    st.subheader('Edit komponen' if existing else 'Komponen baru')
    st.caption('Tentukan informasi, cara menghitung, lalu bentuk penyajiannya. Pratinjau memakai filter dashboard yang tersimpan.')
    left,right=st.columns(2)
    datasets=list(bundle.ids)
    source=left.selectbox('Dataset sumber',datasets,index=index_of(datasets,initial['dataset']),format_func=lambda x:LABELS[x],key=prefix+'_dataset')
    kind=right.selectbox('Jenis komponen',list(KINDS),index=index_of(list(KINDS),initial['kind']),format_func=lambda x:KINDS[x],key=prefix+'_kind')
    frame=bundle.frame(source)
    prefix=prefix+'_'+source
    item=deepcopy(initial)
    item.update(dataset=source,kind=kind)
    item['title']=st.text_input('Judul komponen',value=initial['title'],key=prefix+'_title',max_chars=200)
    item['question']=st.text_input('Informasi apa yang ingin diketahui? (opsional)',value=initial['question'],key=prefix+'_question',max_chars=1000)
    item['description']=st.text_area('Keterangan singkat',value=initial['description'],key=prefix+'_description',max_chars=1000,height=80)
    if kind=='note':
        item['note']=st.text_area('Isi catatan',value=initial['note'],key=prefix+'_note',max_chars=5000)
        item['method']='count'
        item['dimension']=None
        item['value_column']=None
    else:
        methods=list(METHODS) if numeric_columns(frame) else [m for m in METHODS if m not in NUMERIC_METHODS]
        method=st.selectbox('Metode perhitungan',methods,index=index_of(methods,initial['method']),format_func=lambda x:METHODS[x],key=prefix+'_method')
        item['method']=method
        item['value_column']=None
        item['numerator']=[]
        item['denominator']=[]
        if method not in ('count','percentage'):
            choices=numeric_columns(frame) if method in NUMERIC_METHODS else [c for c in frame if c not in ('ID',)]
            item['value_column']=st.selectbox('Kolom nilai',choices,index=index_of(choices,initial['value_column']),key=prefix+'_'+method+'_value')
            if item['value_column'] in ('nik','no_kk'):
                st.caption('Menggunakan token identitas valid. Identitas kosong/numerik/rusak tidak ikut hitungan nilai terisi/unik.')
        if method=='percentage':
            st.caption('Persentase = record pembilang dalam cakupan penyebut ÷ record penyebut × 100%. Filter dashboard dan lokal diterapkan sebelum keduanya dihitung.')
            a,b=st.columns(2)
            with a:
                item['numerator']=condition_editor(frame,initial['numerator'],'pembilang',prefix+'_num')
            with b:
                item['denominator']=condition_editor(frame,initial['denominator'],'penyebut',prefix+'_den')
        item['dimension']=None
        item['granularity']='category'
        if kind!='kpi':
            dimensions=public_columns(frame)
            if kind=='line':
                dimensions=[c for c in dimensions if pd.api.types.is_datetime64_any_dtype(frame[c]) or pd.api.types.is_numeric_dtype(frame[c]) and c in numeric_columns(frame)]
            if dimensions:
                default=initial['dimension'] or ('dusun' if 'dusun' in dimensions else dimensions[0])
                dim=st.selectbox('Kolom kategori / dimensi',dimensions,index=index_of(dimensions,default),key=prefix+'_'+kind+'_dimension')
                item['dimension']=dim
                if pd.api.types.is_datetime64_any_dtype(frame[dim]):
                    groups=['month','year','day']
                    item['granularity']=st.selectbox('Kelompok waktu',groups,index=index_of(groups,initial['granularity']),
                        format_func=lambda x:{'month':'Bulan & tahun','year':'Tahun','day':'Tanggal'}[x],key=prefix+'_'+dim+'_time')
            else:
                st.warning('Dataset ini tidak memiliki dimensi tanggal/urutan yang sesuai untuk grafik garis.')
        a,b=st.columns(2)
        item['unit']=a.text_input('Satuan (jiwa, layanan, unit, Rp, %)',value='%' if method=='percentage' else initial['unit'],key=prefix+'_'+method+'_unit',max_chars=200)
        item['decimals']=b.number_input('Angka di belakang koma',min_value=0,max_value=4,value=initial['decimals'],key=prefix+'_decimals')
        if item['value_column']=='omset':
            item['period']=st.text_input('Periode omzet yang sudah dikonfirmasi (opsional)',value=initial['period'],key=prefix+'_period',max_chars=200)
            st.caption('Workbook tidak menjelaskan periode omzet. Kosongkan jika belum diketahui; jangan menganggap bulanan atau tahunan.')
        with st.expander('Filter khusus komponen',expanded=bool(initial['local_filters'])):
            item['local_filters']=local_filter_editor(frame,initial['local_filters'],prefix+'_local')
    ordered=ordered_components(design)
    slot=next((i for i,c in enumerate(ordered) if existing and c['id']==existing['id']),len(ordered))
    item.update(color=automatic_color(slot),row=slot//DEFAULT_COLUMNS+1,
                position=slot%DEFAULT_COLUMNS+1,span=1)
    item['id']=initial['id'] if existing else '0'*32  # Preview identity only; save assigns a fresh ID.
    st.session_state['component_draft']=deepcopy(item)
    if st.toggle('Lihat pratinjau komponen',value=False,key=prefix+'_show_preview'):
        render_component(bundle,design,item,key_prefix='draft')
    save,cancel=st.columns(2)
    blocked=(kind not in ('kpi','note') and not item['dimension']) or (kind in ('pie','donut') and item['method'] not in ('count','count_filled','sum'))
    save.button('Simpan perubahan' if existing else 'Tambahkan ke dashboard',type='primary',key='save_component',
                disabled=blocked or not existing and len(design['components'])>=80,width='stretch',
                on_click=save_current,args=(bundle,item,existing['id'] if existing else None))
    cancel.button('Batalkan edit' if existing else 'Kosongkan isian',key='cancel_component',width='stretch',on_click=edit_target)


def component_list(bundle,design):
    st.subheader(f"Susunan dashboard · {len(design['components'])} komponen")
    if not design['components']:
        st.info('Tambahkan komponen pertama di panel Komponen baru.')
    for index,item in enumerate(ordered_components(design)):
        with st.expander(f"{index+1:02d} · {item['title']} · {KINDS[item['kind']]}"):
            st.caption(LABELS[item['dataset']])
            controls=st.columns(5)
            controls[0].button('Edit',key='edit_'+item['id'],width='stretch',on_click=edit_target,args=(item['id'],))
            controls[1].button('Duplikasi',key='duplicate_'+item['id'],disabled=len(design['components'])>=80,width='stretch',on_click=change_component,args=('duplicate',item['id']))
            controls[2].button('Naik',key='up_'+item['id'],disabled=index==0,width='stretch',on_click=change_component,args=('move',item['id'],-1))
            controls[3].button('Turun',key='down_'+item['id'],disabled=index==len(design['components'])-1,width='stretch',on_click=change_component,args=('move',item['id'],1))
            controls[4].button('Hapus',key='delete_'+item['id'],width='stretch',on_click=change_component,args=('delete',item['id']))


def dashboard_settings(design):
    dash=design['dashboard']
    st.subheader('Identitas & tampilan')
    dash['village']=st.text_input('Nama desa',value=dash['village'],max_chars=1000,key='w_village')
    dash['title']=st.text_input('Judul dashboard',value=dash['title'],max_chars=1000,key='w_dash_title')
    dash['description']=st.text_area('Deskripsi dashboard',value=dash['description'],max_chars=1000,key='w_dash_description')
    st.caption('Warna grafik, aksen KPI, ukuran, dan posisi diatur otomatis. Gunakan Naik/Turun pada susunan komponen untuk mengubah urutan.')
    upload=st.file_uploader('Logo opsional (PNG/JPEG, maksimal 250 KB dan 2000 × 2000 piksel)',type=['png','jpg','jpeg'],key='w_logo')
    if upload is not None:
        try:
            if upload.size>250000:
                raise ValueError('Logo melebihi 250 KB.')
            with Image.open(BytesIO(upload.getvalue())) as image:
                if image.format not in ('PNG','JPEG') or image.width>2000 or image.height>2000:
                    raise ValueError('Logo harus PNG/JPEG maksimal 2000 × 2000 piksel.')
                image.thumbnail((480,480))
                output=BytesIO()
                image.convert('RGBA').save(output,format='PNG',optimize=True)
                if len(output.getvalue())>290000:
                    raise ValueError('Logo terlalu kompleks; gunakan gambar lebih kecil.')
                dash['logo']=base64.b64encode(output.getvalue()).decode('ascii')
        except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombError) as exc:
            st.error(str(exc))
    if dash['logo']:
        st.image(BytesIO(base64.b64decode(dash['logo'])),width=76)
        if st.button('Hapus logo',key='remove_logo'):
            dash['logo']=None
            st.session_state.pop('w_logo',None)
            st.rerun()


def builder(bundle,design):
    st.caption('02 / RUANG RANCANG')
    title,add=st.columns([4,1])
    title.title('Rancang cerita desamu.')
    add.button('Tambah Komponen',type='primary',width='stretch',key='add_component',on_click=edit_target)
    st.write('Data yang sama, sudut pandang kelompokmu. Atur indikator, penyajian, dan susunannya di sini.')
    components,settings,filters=st.tabs(['Komponen','Identitas & tampilan','Filter dashboard'])
    # Apply setting/filter widget values before computing the draft preview.
    with settings:
        dashboard_settings(design)
    with filters:
        filter_manager(bundle,design)
    with components:
        component_editor(bundle,design)
        st.divider()
        component_list(bundle,design)
    st.divider()
    if st.toggle('Tampilkan kanvas dashboard',value=False,key='w_show_canvas'):
        render_dashboard(bundle,design)
