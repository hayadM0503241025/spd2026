from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json
import streamlit as st
from studio.access import (group_access,facilitator_access,set_access,client_key,
                           logout_facilitator)
from studio.config import export_design,import_design
from studio.data import load_shared
from studio.rendering import dashboard_header,render_dashboard
from studio.store import AccessDenied,Conflict,StoreUnavailable
from studio.workspace import apply_design,go,has_work,request_action


def local_time(timestamp):
    return datetime.fromtimestamp(timestamp,timezone(timedelta(hours=7))).strftime('%d/%m/%Y %H:%M WIB')


def bind_group(store):
    actor=group_access(store)
    if actor is None:
        return None
    if st.session_state.get('group_loaded_id')!=actor['group_id']:
        result=store.get_result(st.session_state['auth_group_token'],actor['group_id'])
        if result['design'] and not has_work():
            # Validate against the registered shared dataset before replacing a draft.
            restored,_=import_design(json.dumps(result['design']).encode())
            apply_design(restored)
        st.session_state['result_revision']=result['revision']
        st.session_state['group_loaded_id']=actor['group_id']
        st.session_state['w_group_name']=actor['name']
    st.session_state['design']['group_name']=actor['name']
    return actor


def create_group(store):
    try:
        result=store.create_group(st.session_state.get('access_new_group_name',''),st.session_state.get('access_create_remember',True))
        set_access('group',result['token'],st.session_state.get('access_create_remember',True))
        st.session_state['new_group_code']={'name':result['name'],'code':result['code']}
        # Creating a new group binds the current draft; it never loads someone else's work.
        st.session_state['group_loaded_id']=result['id']
        st.session_state['result_revision']=0
        st.session_state['w_group_name']=result['name']
        st.session_state['design']['group_name']=result['name']
        st.session_state['notice']='Akses kelompok dibuat. Simpan kode akses pribadi sebelum melanjutkan.'
    except (ValueError,StoreUnavailable) as exc:
        st.session_state['notice_error']=str(exc)


def login_group(store):
    try:
        remember=st.session_state.get('access_login_remember',True)
        token=store.login_group(st.session_state.get('access_group_code',''),remember,client_key())
        set_access('group',token,remember)
        st.session_state.pop('group_loaded_id',None)
        bind_group(store)
        st.session_state['notice']='Masuk ke kelompok berhasil. Draft yang sedang dikerjakan tetap dipertahankan bila belum kosong.'
    except (ValueError,StoreUnavailable) as exc:
        st.session_state['notice_error']=str(exc)
    finally:
        st.session_state.pop('access_group_code',None)


def login_facilitator(store):
    try:
        remember=st.session_state.get('access_facilitator_remember',True)
        token=store.login_facilitator(st.session_state.get('access_facilitator_password',''),remember,client_key())
        set_access('facilitator',token,remember)
        st.session_state['notice']='Akses fasilitator aktif. Tidak perlu memasukkan kata sandi lagi selama masih masuk.'
    except (ValueError,StoreUnavailable) as exc:
        st.session_state['notice_error']=str(exc)
    finally:
        st.session_state.pop('access_facilitator_password',None)


def group_panel(store):
    if store is None:
        st.caption('Penyimpanan hasil belum tersedia. Draft tetap bisa dirancang dan diunduh sebagai JSON.')
        return
    actor=group_access(store)
    with st.expander('Akses kelompok',expanded=bool(st.session_state.get('new_group_code'))):
        if actor:
            st.write('Masuk sebagai **'+actor['name']+'**')
            st.caption('Akses ini hanya mengelola hasil kelompok tersebut.')
            code=st.session_state.get('new_group_code')
            if code:
                st.caption('Simpan kode ini. Nama kelompok saja tidak dapat membuka hasil tersimpan.')
                st.code(code['code'],language=None)
                st.download_button('Unduh kode akses',f"Kelompok: {code['name']}\nKode akses pribadi: {code['code']}\nJangan bagikan ke kelompok lain.\n",
                                   file_name='akses-kelompok.txt',mime='text/plain',key='download_group_code')
                st.button('Kode sudah saya simpan',key='dismiss_group_code',on_click=lambda:st.session_state.pop('new_group_code',None))
            st.button('Keluar kelompok',key='logout_group',on_click=request_action,args=('logout_group',),width='stretch')
        else:
            st.caption('Buat akses baru untuk menyimpan hasil, atau masuk memakai kode kelompok yang sudah ada. Draft saat ini tidak dihapus.')
            with st.form('create_group_form'):
                st.text_input('Nama kelompok baru',value=st.session_state['design']['group_name'],key='access_new_group_name',max_chars=120)
                st.checkbox('Ingat akses di browser ini',value=True,key='access_create_remember')
                st.form_submit_button('Buat akses kelompok',on_click=create_group,args=(store,),width='stretch')
            with st.form('login_group_form'):
                st.text_input('Kode akses kelompok',type='password',key='access_group_code')
                st.checkbox('Ingat akses di browser ini',value=True,key='access_login_remember')
                st.form_submit_button('Masuk kelompok',on_click=login_group,args=(store,),width='stretch')
        if st.session_state.get('auth_cookie_available') is False:
            st.caption('Browser memblokir penyimpanan akses. Simpan kode kelompok untuk masuk kembali setelah sesi berakhir.')


def facilitator_login(store):
    st.subheader('Akses fasilitator')
    st.write('Hasil semua kelompok hanya dapat dibuka oleh fasilitator.')
    if store is None:
        st.error('Penyimpanan hasil belum dikonfigurasi atau tidak dapat diakses.')
        return
    if not store.facilitator_hash:
        st.info('Fasilitator perlu mengatur kata sandi melalui Secrets. Panduan tersedia di README.')
        return
    with st.form('facilitator_login_form'):
        st.text_input('Kata sandi fasilitator',type='password',key='access_facilitator_password')
        st.checkbox('Ingat akses di browser ini',value=True,key='access_facilitator_remember')
        st.form_submit_button('Masuk fasilitator',type='primary',on_click=login_facilitator,args=(store,))


def save_own_result(store):
    try:
        actor=group_access(store)
        if not actor:
            raise AccessDenied('Masuk melalui Akses kelompok di sidebar sebelum menyimpan hasil.')
        revision=store.save_result(st.session_state['auth_group_token'],actor['group_id'],st.session_state['design'],st.session_state.get('result_revision',0))
        st.session_state['result_revision']=revision
        st.session_state['notice']=f'Hasil kelompok disimpan sebagai versi {revision}. Fasilitator dapat melihatnya pada Hasil Kelompok.'
    except (ValueError,StoreUnavailable) as exc:
        st.session_state['notice_error']=str(exc)


def load_own_result(store):
    try:
        actor=group_access(store)
        if not actor:
            raise AccessDenied('Masuk ke kelompok terlebih dahulu.')
        result=store.get_result(st.session_state['auth_group_token'],actor['group_id'])
        if result['design'] is None:
            raise ValueError('Kelompok ini belum menyimpan hasil.')
        restored,_=import_design(json.dumps(result['design']).encode())
        if has_work() and restored!=st.session_state['design']:
            request_action('load_saved',design=restored,revision=result['revision'])
        else:
            apply_design(restored)
            st.session_state['result_revision']=result['revision']
            go('Pratinjau')
    except (ValueError,StoreUnavailable) as exc:
        st.session_state['notice_error']=str(exc)


def own_save_panel(store):
    with st.container(border=True):
        st.subheader('Simpan Hasil Kelompok')
        actor=group_access(store) if store else None
        if not actor:
            st.info('Buka Akses kelompok pada sidebar untuk membuat akses pribadi atau melanjutkan kelompok yang sudah ada. JSON tetap dapat diunduh tanpa login.')
            return
        result=store.get_result(st.session_state['auth_group_token'],actor['group_id'])
        if result['archived']:
            st.warning('Hasil diarsipkan oleh fasilitator. Anda masih bisa mengunduhnya; hubungi fasilitator untuk membuka kembali penyimpanan.')
        st.caption(f"{actor['name']} · versi tersimpan {result['revision']} · "+('terakhir '+local_time(result['updated']) if result['design'] else 'belum ada hasil tersimpan'))
        a,b=st.columns(2)
        a.button('Simpan Hasil Kelompok',type='primary',key='save_group_result',on_click=save_own_result,args=(store,),disabled=bool(result['archived']),width='stretch')
        b.button('Buka hasil tersimpan',key='load_group_result',on_click=load_own_result,args=(store,),disabled=result['design'] is None,width='stretch')
        st.caption('Perubahan baru terlihat oleh fasilitator setelah disimpan. Penyimpanan baru mempertahankan riwayat versi dan tidak menimpa pekerjaan kelompok lain.')


def queue_management(kind,group_id,name,revision,**details):
    st.session_state['pending_management']={'kind':kind,'group_id':group_id,'name':name,'revision':revision,**details}


def confirm_management(store):
    action=st.session_state.get('pending_management')
    if not action:
        return
    try:
        if not facilitator_access(store):
            raise AccessDenied('Masuk sebagai fasilitator untuk melakukan pengelolaan.')
        token=st.session_state['auth_facilitator_token']
        if action['kind']=='archive':
            store.archive(token,action['group_id'],action['revision'])
        elif action['kind']=='restore':
            store.restore(token,action['group_id'],action['source_revision'],action['revision'])
        elif action['kind']=='replace':
            store.save_result(token,action['group_id'],action['design'],action['revision'])
        st.session_state['notice']='Pengelolaan hasil diterapkan. Riwayat versi sebelumnya tetap tersedia.'
    except (ValueError,StoreUnavailable) as exc:
        st.session_state['notice_error']=str(exc)
    finally:
        st.session_state.pop('pending_management',None)


def management_confirmation(store):
    action=st.session_state.get('pending_management')
    if not action:
        return
    with st.container(border=True):
        verbs={'archive':'Arsipkan hasil','restore':'Pulihkan versi hasil','replace':'Ganti hasil dengan revisi JSON'}
        st.warning(f"{verbs[action['kind']]} untuk {action['name']} (versi {action['revision']})? Tindakan hanya diterapkan pada kelompok yang dipilih.")
        a,b=st.columns(2)
        a.button('Konfirmasi tindakan fasilitator',key='confirm_management',type='primary',on_click=confirm_management,args=(store,),width='stretch')
        b.button('Batalkan tindakan',key='cancel_management',on_click=lambda:st.session_state.pop('pending_management',None),width='stretch')


def results_page(store):
    st.caption('RUANG FASILITATOR')
    st.title('Hasil Kelompok')
    if store is None or not facilitator_access(store):
        facilitator_login(store)
        return
    st.caption('Menampilkan hasil terakhir yang disimpan kelompok. Pratinjau di sini hanya baca dan tidak mengganti ruang kerja Anda.')
    management_confirmation(store)
    token=st.session_state['auth_facilitator_token']
    rows=store.list_results(token)
    if not rows:
        st.info('Belum ada kelompok yang membuat akses. Peserta dapat memulai melalui Akses kelompok di sidebar.')
        return
    st.dataframe([{'Kelompok':r['name'],'Status':'Diarsipkan' if r['archived'] else 'Tersimpan' if r['has_result'] else 'Belum disimpan',
                   'Komponen':r['components'],'Versi hasil':r['revision'],'Diperbarui':local_time(r['updated'])} for r in rows],hide_index=True,width='stretch')
    lookup={r['id']:r for r in rows}
    chosen=st.selectbox('Pilih hasil kelompok',list(lookup),format_func=lambda x:f"{lookup[x]['name']} · {x[:8]}",key='access_view_group')
    result=store.get_result(token,chosen)
    saved=result['design']
    if saved is None:
        st.info('Kelompok ini belum menyimpan dashboard.')
        return
    bundle=load_shared(saved['dataset_ref']['version'])
    history=store.history(token,chosen)
    left,right=st.columns(2)
    left.download_button('Unduh desain kelompok',export_design(saved,bundle),file_name=f'hasil-{chosen[:8]}.json',mime='application/json',key='download_result',width='stretch')
    if result['archived']:
        right.button('Buka kembali hasil',key='reopen_result',on_click=queue_management,args=('restore',chosen,result['name'],result['revision']),
                     kwargs={'source_revision':result['revision']},width='stretch')
    else:
        right.button('Arsipkan hasil',key='archive_result',on_click=queue_management,args=('archive',chosen,result['name'],result['revision']),width='stretch')
    with st.expander('Riwayat & pengelolaan'):
        st.caption('Pengarsipan menyembunyikan hasil dari penyimpanan peserta tanpa menghapus riwayat. Penggantian dan pemulihan selalu membuat versi baru.')
        versions={r['revision']:r for r in history}
        source=st.selectbox('Versi untuk dipulihkan',list(versions),format_func=lambda x:f"Versi {x} · {versions[x]['action']} · {local_time(versions[x]['created'])}",key='access_history_'+chosen)
        st.button('Pulihkan versi ini',key='restore_version',on_click=queue_management,args=('restore',chosen,result['name'],result['revision']),kwargs={'source_revision':source})
        upload=st.file_uploader('Revisi desain JSON kelompok ini',type=['json'],key='access_revision_'+chosen)
        if st.button('Tinjau penggantian JSON',disabled=upload is None,key='review_replacement'):
            try:
                if upload.size>2*1024*1024:
                    raise ValueError('Berkas desain melebihi 2 MB.')
                revised,_=import_design(upload.getvalue())
                queue_management('replace',chosen,result['name'],result['revision'],design=revised)
                st.rerun()
            except (ValueError,OSError) as exc:
                st.error(str(exc))
    st.divider()
    readonly=deepcopy(saved)
    dashboard_header(readonly,bundle)
    render_dashboard(bundle,readonly,key_prefix='saved_'+chosen,interactive_filters=False)
