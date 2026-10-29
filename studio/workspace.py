"""Workspace-only transitions never clear authentication or another account."""
from copy import deepcopy
import streamlit as st
from studio.config import new_design,new_component


def apply_design(design):
    for key in list(st.session_state):
        if key.startswith('w_') or key in ('editing_id','editor_epoch','component_draft'):
            del st.session_state[key]
    st.session_state['design']=deepcopy(design)


def go(stage):
    st.session_state['_next_stage']=stage


def has_work():
    design=st.session_state['design']
    draft=st.session_state.get('component_draft')
    defaults=new_component()
    fields=('dataset','kind','title','description','question','dimension','method','value_column','numerator','denominator','local_filters','unit','note')
    changed=bool(draft and any(draft.get(field)!=defaults[field] for field in fields))
    return bool(design['components'] or design['filters'] or changed)


def request_action(kind,**details):
    st.session_state['pending_workspace_action']={'kind':kind,**details}


def start_blank(bundle):
    if has_work():
        request_action('blank')
        return
    blank=new_design(bundle)
    blank['group_name']=st.session_state['design']['group_name']
    blank['dashboard']=deepcopy(st.session_state['design']['dashboard'])
    apply_design(blank)
    go('Rancang Dashboard')


def cancel_action():
    st.session_state.pop('pending_workspace_action',None)


def confirm_action(bundle,store):
    action=st.session_state.get('pending_workspace_action')
    if not action:
        return
    kind=action['kind']
    if kind in ('blank','clear'):
        blank=new_design(bundle)
        blank['group_name']=st.session_state['design']['group_name']
        blank['dashboard']=deepcopy(st.session_state['design']['dashboard'])
        apply_design(blank)
        go('Rancang Dashboard' if kind=='blank' else 'Beranda')
    elif kind in ('import','load_saved'):
        apply_design(action['design'])
        if 'revision' in action:
            st.session_state['result_revision']=action['revision']
        go('Pratinjau')
    elif kind=='logout_group':
        from studio.access import logout_group
        logout_group(store)
        apply_design(new_design(bundle))
        go('Beranda')
    st.session_state.pop('pending_workspace_action',None)
    st.session_state['notice']='Tindakan diterapkan pada ruang kerja sesi ini. Hasil tersimpan dan pekerjaan kelompok lain tetap utuh.'


def render_confirmation(bundle,store):
    action=st.session_state.get('pending_workspace_action')
    if not action:
        return
    labels={'blank':'Mulai dashboard kosong','clear':'Bersihkan ruang kerja sendiri',
            'import':'Ganti ruang kerja dengan desain JSON','load_saved':'Buka hasil tersimpan',
            'logout_group':'Keluar dari kelompok'}
    with st.container(border=True):
        st.warning(labels[action['kind']]+': perubahan yang belum disimpan akan diganti. Hasil di penyimpanan tidak dihapus.')
        from studio.config import export_design
        design=st.session_state['design']
        st.download_button('Unduh cadangan sebelum lanjut',export_design(design,bundle),file_name='cadangan-dashboard.json',mime='application/json',key='backup_before_action')
        left,right=st.columns(2)
        left.button('Ya, lanjutkan',key='confirm_workspace_action',type='primary',on_click=confirm_action,args=(bundle,store),width='stretch')
        right.button('Batalkan',key='cancel_workspace_action',on_click=cancel_action,width='stretch')
