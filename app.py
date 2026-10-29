"""Run with: streamlit run app.py"""
import streamlit as st
from studio.data import load_shared, DatasetError
from studio.config import new_design, retire_untouched_example
from studio.ui import styles, sidebar, home, inspection, preview, save_load, guide, apply_design
from studio.ui_builder import builder
from studio.presentation import apply_visual_defaults
from studio.access import get_store,sync_browser
from studio.ui_access import bind_group,results_page
from studio.workspace import render_confirmation
from studio.store import StoreUnavailable,AccessDenied,Conflict

st.set_page_config(page_title='Studio Dashboard Desa',page_icon='🌾',layout='wide',initial_sidebar_state='expanded')


@st.cache_data(show_spinner=False)
def cached_shared(version=None):
    # The only shared cache contains immutable, versioned baseline bytes.
    # Streamlit returns an independent deserialized result to every caller.
    return load_shared(version)


try:
    if 'design' not in st.session_state:
        baseline=cached_shared()
        st.session_state['design']=new_design(baseline)
    design=st.session_state['design']
    bundle=cached_shared(design['dataset_ref']['version'])
    if 'workspace_flow_revision' not in st.session_state:
        migrated=retire_untouched_example(design,bundle)
        if migrated is not None:
            apply_design(migrated)
            design=st.session_state['design']
            st.session_state['notice']='Contoh bawaan sekarang hanya tampil di Beranda. Dashboard kelompok dimulai kosong.'
        st.session_state['workspace_flow_revision']=2
    apply_visual_defaults(design)
except (OSError,DatasetError,ValueError) as exc:
    st.error('Data bersama belum dapat dimuat: '+str(exc))
    st.info('Fasilitator perlu memasang berkas data/shared dan data/registry.json yang sesuai README.')
    st.stop()

store=None
try:
    store=get_store()
    sync_browser(store)
    bind_group(store)
    design=st.session_state['design']
except (StoreUnavailable,OSError,ValueError) as exc:
    st.warning('Penyimpanan kelompok belum dapat digunakan: '+str(exc))
    store=None

if 'stage' not in st.session_state:
    st.session_state['stage']='Beranda'
if '_next_stage' in st.session_state:
    st.session_state['stage']=st.session_state.pop('_next_stage')
styles(design['dashboard']['primary_color'])

if st.session_state.get('presentation',False):
    with st.sidebar:
        st.caption('MODE PRESENTASI')
        st.write(design['group_name'] or 'Kelompok belum diberi nama')
        st.button('Kembali ke Mode Rancang',on_click=lambda:st.session_state.update(presentation=False,stage='Rancang Dashboard'))
    preview(bundle,design,presentation=True)
else:
    page=sidebar(bundle,design,store)
    if st.session_state.get('notice'):
        st.success(st.session_state.pop('notice'))
    if st.session_state.get('notice_error'):
        st.error(st.session_state.pop('notice_error'))
    try:
        render_confirmation(bundle,store)
        if page=='Beranda':
            home(bundle,design)
        elif page=='Periksa Data':
            inspection(bundle)
        elif page=='Rancang Dashboard':
            builder(bundle,design)
        elif page=='Pratinjau':
            preview(bundle,design)
        elif page=='Simpan & Muat':
            save_load(bundle,design,store)
        elif page=='Hasil Kelompok':
            results_page(store)
        elif page=='Panduan':
            guide(bundle)
    except (StoreUnavailable,AccessDenied,Conflict) as exc:
        st.error(str(exc))
