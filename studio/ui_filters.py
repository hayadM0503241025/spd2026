import pandas as pd
import streamlit as st
from studio.aggregation import public_columns
from studio.config import uid
from studio.constants import LABELS
from studio.filters import infer_kind, filter_columns, select_filter_columns, filter_is_active


def update_category_value(rule,key):
    rule['value']=list(st.session_state[key])


def update_range_value(rule,key,defaults):
    # Update before rendering so the compact button reflects this interaction.
    if not st.session_state.get(key+'_on',False):
        rule['value']=None
        return
    if rule['kind']=='number':
        bounds=[st.session_state.get(key+'_low',defaults[0]),st.session_state.get(key+'_high',defaults[1])]
        if bounds[0]<=bounds[1]:
            rule['value']=bounds
    else:
        bounds=st.session_state.get(key+'_date',tuple(pd.Timestamp(v).date() for v in defaults))
        if len(bounds)==2:
            rule['value']=[v.isoformat() for v in bounds]


def value_control(rule,series,key):
    """Values are chosen only while viewing a dashboard, using the full column."""
    kind=rule['kind']
    if kind=='category':
        options=sorted(series.dropna().astype(str).unique().tolist())
        current=rule.get('value') or []
        unknown=[x for x in current if x not in options]
        if unknown:
            st.caption('Pilihan tersimpan tidak ditemukan pada data. Kosongkan pilihan untuk menampilkan semua nilai.')
        return st.multiselect(rule.get('label',rule.get('column','Nilai')),options+unknown,default=current,key=key,
                              on_change=update_category_value,args=(rule,key),
                              placeholder='Semua nilai',help='Seluruh isi kolom otomatis tersedia. Pilihan kosong berarti semua data ditampilkan.')
    series=series.dropna()
    if series.empty:
        st.caption('Kolom tidak memiliki nilai tersedia untuk filter rentang.')
        return rule.get('value')
    defaults=([float(series.min()),float(series.max())] if kind=='number'
              else [pd.Timestamp(series.min()).date().isoformat(),pd.Timestamp(series.max()).date().isoformat()])
    callbacks={'on_change':update_range_value,'args':(rule,key,defaults)}
    enabled=st.checkbox('Batasi '+rule.get('label',rule.get('column','rentang')),value=rule.get('value') is not None,key=key+'_on',**callbacks)
    if not enabled:
        return None
    bounds=rule.get('value') or [series.min(),series.max()]
    if kind=='number':
        left,right=st.columns(2)
        low=left.number_input('Batas minimum',value=float(bounds[0]),key=key+'_low',**callbacks)
        high=right.number_input('Batas maksimum',value=float(bounds[1]),key=key+'_high',**callbacks)
        if low>high:
            st.warning('Batas minimum melebihi maksimum; perbaiki rentang.')
            return rule.get('value')
        return [low,high]
    values=st.date_input('Rentang tanggal',value=tuple(pd.Timestamp(v).date() for v in bounds),key=key+'_date',format='DD/MM/YYYY',**callbacks)
    if len(values)!=2:
        st.caption('Pilih tanggal awal dan akhir.')
        return rule.get('value')
    return [v.isoformat() for v in values]


def reset_filters():
    for rule in st.session_state['design']['filters']:
        rule['value']=[] if rule['kind']=='category' else None
    for key in list(st.session_state):
        if key.startswith('w_filter_'):
            del st.session_state[key]


def filter_button_label(rule):
    label=rule.get('label') or rule.get('column','Filter').replace('_',' ').capitalize()
    if not filter_is_active(rule):
        return label+' · Semua'
    if rule['kind']=='category':
        values=rule['value']
        summary=values[0] if len(values)==1 and len(values[0])<=22 else f'{len(values)} pilihan'
        return label+' · '+summary
    return label+' · Dibatasi'


def render_filters(bundle,design):
    if not design['filters']:
        return
    with st.container(horizontal=True,vertical_alignment='center',gap='xsmall',key='dashboard_filterbar'):
        for rule in design['filters']:
            scope=', '.join(f'{LABELS.get(ds,ds)} → {col}' for ds,col in rule['mapping'].items())
            with st.popover(filter_button_label(rule),icon=':material/filter_alt:',width='content',
                            type='primary' if filter_is_active(rule) else 'secondary',
                            help='Berlaku untuk '+scope+'. Klik untuk memilih nilai; pilihan kosong berarti semua data.'):
                frames=[]
                for dataset,column in rule['mapping'].items():
                    frame=bundle.frame(dataset)
                    if column not in frame:
                        st.warning(f'Filter {rule["label"]}: kolom {column} hilang. Pilih ulang kolom di Rancang Dashboard → Filter dashboard.')
                    elif infer_kind(frame[column])!=rule['kind']:
                        st.warning(f'Filter {rule["label"]}: tipe {column} berbeda. Pilih ulang kolom filter.')
                    else:
                        frames.append(frame[column])
                if frames:
                    rule['value']=value_control(rule,pd.concat(frames,ignore_index=True),'w_filter_'+rule['id'])
                st.caption('Berlaku untuk: '+scope+'. Pilihan kosong berarti semua data.')
        st.button('Reset',icon=':material/restart_alt:',key='reset_filters',type='tertiary',width='content',
                  help='Reset semua filter dashboard.',on_click=reset_filters)


def local_filter_editor(frame,existing,prefix):
    available=public_columns(frame)
    old={r['column']:r for r in existing}
    chosen=st.multiselect('Kolom filter khusus komponen',available,default=[c for c in old if c in available],key=prefix+'_columns',
                          placeholder='Pilih kolom',help='Seluruh isi kolom otomatis menjadi pilihan filter di Pratinjau pada komponen ini.')
    output=[]
    for column in chosen:
        rule=old.get(column,{'column':column,'kind':infer_kind(frame[column]),'value':[] if infer_kind(frame[column])=='category' else None}).copy()
        output.append(rule)
    if chosen:
        st.caption('Pilihan isi kolom muncul otomatis di Pratinjau, khusus pada komponen ini. Tanpa memilih nilai, seluruh data tetap ditampilkan.')
    return output


def render_local_filters(bundle,item,key_prefix):
    if not item['local_filters']:
        return
    frame=bundle.frame(item['dataset'])
    active=sum(filter_is_active(rule) for rule in item['local_filters'])
    label=f'Filter · {active}' if active else 'Filter'
    with st.popover(label,icon=':material/filter_alt:',width='content',type='primary' if active else 'secondary',
                    help='Filter khusus komponen ini. Klik untuk memilih nilai.'):
        for rule in item['local_filters']:
            column=rule['column']
            if column not in frame:
                st.warning(f'Kolom filter {column} hilang. Edit komponen untuk memilih ulang.')
                continue
            rule['value']=value_control(rule,frame[column],f'w_local_filter_{key_prefix}_{item["id"]}_{column}')
        st.caption('Hanya memengaruhi komponen ini. Pilihan kosong berarti semua nilai.')


def update_filter_columns(options):
    design=st.session_state['design']
    design['filters']=select_filter_columns(design['filters'],st.session_state['w_dashboard_filter_columns'],options,uid)


def filter_manager(bundle,design):
    st.subheader('Pilih kolom untuk filter')
    st.write('Cukup pilih kolom yang ingin dijadikan filter. Seluruh isinya otomatis tersedia di Pratinjau; tidak perlu memasukkan pilihan satu per satu.')
    options=filter_columns(bundle,design['filters'])
    selected=[key for key,option in options.items() if any(r['kind']==option['kind'] and r['mapping']==option['mapping'] for r in design['filters'])]
    def label(key):
        option=options[key]
        return option['label']+' — '+', '.join(LABELS[d] for d in option['mapping'])
    st.multiselect('Kolom filter dashboard',list(options),default=selected,format_func=label,
                    key='w_dashboard_filter_columns',on_change=update_filter_columns,args=(options,),
                    placeholder='Pilih kolom, misalnya Dusun atau Jenis kelamin',max_selections=20)
    if not design['filters']:
        st.caption('Belum ada kolom filter dipilih. Semua data akan ditampilkan.')
    for rule in design['filters']:
        scope=', '.join(f'{LABELS[ds]}.{column}' for ds,column in rule['mapping'].items())
        st.caption(f"{rule['label']} · berlaku untuk {scope}.")
    st.info('Contoh: pilih Dusun untuk menyediakan semua dusun sebagai pilihan. Nilainya dipilih saat membuka Pratinjau. Hapus centang kolom untuk menghapus filternya.')
