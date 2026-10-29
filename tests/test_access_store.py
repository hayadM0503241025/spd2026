from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import sqlite3
import pytest
from studio.config import new_design,new_component,export_design
from studio.security import hash_password,verify_password
from studio.store import Store,AccessDenied,Conflict,StoreUnavailable


def design_for(bundle,name='Label tidak menentukan pemilik'):
    design=new_design(bundle)
    design['group_name']=name
    design['components']=[new_component(title='Penduduk')]
    return design


def test_password_verifier_is_salted_and_not_plaintext():
    a,b=hash_password('test-access-123'),hash_password('test-access-123')
    assert a!=b and 'test-access-123' not in a
    assert verify_password('test-access-123',a)
    assert not verify_password('wrong',a)
    assert not verify_password('test-access-123','malformed')


def test_ownership_checked_for_every_read_write_and_management(store,bundle):
    a,b=store.create_group('Kelompok A'),store.create_group('Kelompok B')
    design=design_for(bundle,'Kelompok B')  # A label or imported design cannot claim B.
    assert store.save_result(a['token'],a['id'],design,0)==1
    assert store.get_result(a['token'],a['id'])['design']['group_name']=='Kelompok A'
    attempts=[lambda:store.get_result(a['token'],b['id']),
              lambda:store.save_result(a['token'],b['id'],design,0),
              lambda:store.history(a['token'],b['id']),
              lambda:store.restore(a['token'],b['id'],1,0),
              lambda:store.archive(a['token'],a['id'],1),
              lambda:store.list_results(a['token']),
              lambda:store.list_results({'kind':'facilitator'}),
              lambda:store.list_results('fake-token-'*8)]
    for attempt in attempts:
        with pytest.raises(AccessDenied):
            attempt()
    assert store.get_result(b['token'],b['id'])['revision']==0


def test_same_group_name_does_not_share_identity(store,bundle):
    a,b=store.create_group('Nama Sama'),store.create_group('Nama Sama')
    assert a['id']!=b['id'] and a['code']!=b['code']
    store.save_result(a['token'],a['id'],design_for(bundle),0)
    assert store.get_result(b['token'],b['id'])['design'] is None
    with pytest.raises(AccessDenied):
        store.login_group('Nama Sama')


def test_results_and_access_survive_store_restart_and_logout_revokes_token(store,bundle):
    group=store.create_group('Kelompok Persisten')
    design=design_for(bundle)
    store.save_result(group['token'],group['id'],design,0)
    reopened=Store(store.database_url,store.facilitator_hash)
    assert reopened.authenticate(group['token'])['group_id']==group['id']
    assert reopened.get_result(group['token'],group['id'])['revision']==1
    new_token=reopened.login_group(group['code'])
    assert reopened.get_result(new_token,group['id'])['design']['components']==store.get_result(group['token'],group['id'])['design']['components']
    reopened.logout(group['token'])
    assert reopened.authenticate(group['token']) is None
    assert reopened.authenticate(new_token) is not None


def test_session_expiry_and_password_rotation(store,bundle):
    group=store.create_group('Tetap punya akses kelompok')
    admin=store.login_facilitator('facilitator-test-2026')
    now=store.clock()
    store.clock=lambda:now+31*86400
    assert store.authenticate(admin) is None
    store.clock=lambda:now
    rotated=Store(store.database_url,hash_password('replacement-test-2026'))
    assert rotated.authenticate(admin) is None
    assert rotated.authenticate(group['token']) is not None
    with pytest.raises(AccessDenied):
        store.login_facilitator('facilitator-test-2026')  # A stale process cannot issue a usable old-password token.
    valid=rotated.login_facilitator('replacement-test-2026')
    assert rotated.authenticate(valid)['kind']=='facilitator'


def test_failed_login_limit_persists_across_store_restart(store):
    for _ in range(5):
        with pytest.raises(AccessDenied,match='tidak sesuai'):
            store.login_facilitator('wrong-password',client='test-client')
    reopened=Store(store.database_url,store.facilitator_hash)
    with pytest.raises(AccessDenied,match='15 menit'):
        reopened.login_facilitator('facilitator-test-2026',client='test-client')
    assert reopened.login_facilitator('facilitator-test-2026',client='another-client')


def test_versions_archive_restore_and_facilitator_revisions(store,bundle):
    group=store.create_group('Kelompok Riwayat')
    other=store.create_group('Kelompok Lain')
    design=design_for(bundle)
    assert store.save_result(group['token'],group['id'],design,0)==1
    changed=deepcopy(design)
    changed['dashboard']['title']='Versi kedua'
    assert store.save_result(group['token'],group['id'],changed,1)==2
    admin=store.login_facilitator('facilitator-test-2026')
    assert len(store.list_results(admin))==2
    assert store.archive(admin,group['id'],2)==3
    with pytest.raises(AccessDenied,match='diarsipkan'):
        store.save_result(group['token'],group['id'],design,3)
    with pytest.raises(AccessDenied):
        store.restore(group['token'],group['id'],1,3)
    assert store.restore(admin,group['id'],1,3)==4
    assert store.get_result(group['token'],group['id'])['design']['dashboard']['title']==design['dashboard']['title']
    assert store.save_result(admin,group['id'],changed,4)==5
    assert [v['action'] for v in store.history(admin,group['id'])]==['save','restore','archive','save','save']
    assert store.get_result(other['token'],other['id'])['revision']==0


def test_concurrent_saves_cannot_overwrite_silently(store,bundle):
    group=store.create_group('Dua perangkat satu kelompok')
    design=design_for(bundle)
    def save(title):
        candidate=deepcopy(design)
        candidate['dashboard']['title']=title
        try:
            store.save_result(group['token'],group['id'],candidate,0)
            return 'saved'
        except Conflict:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save,['Perangkat A','Perangkat B']))==['conflict','saved']
    assert len(store.history(group['token'],group['id']))==1


def test_exports_and_result_lists_do_not_include_credentials(store,bundle):
    group=store.create_group('Kelompok Rahasia')
    design=design_for(bundle)
    store.save_result(group['token'],group['id'],design,0)
    output=export_design(store.get_result(group['token'],group['id'])['design'],bundle).decode()
    admin=store.login_facilitator('facilitator-test-2026')
    listing=json.dumps(store.list_results(admin))
    for secret in (group['code'],group['token'],admin,store.facilitator_hash):
        assert secret not in output and secret not in listing
    path=store.database_url[len('sqlite:///'):]
    with sqlite3.connect(path) as conn:
        assert group['code'].split('.')[1] not in conn.execute('SELECT code_hash FROM studio_groups').fetchone()[0]
        assert group['token'] not in str(conn.execute('SELECT token_hash FROM studio_sessions').fetchall())


def test_unavailable_postgres_never_falls_back_to_empty_local_database():
    with pytest.raises(StoreUnavailable):
        Store('postgresql://invalid:invalid@127.0.0.1:1/invalid?connect_timeout=1')
