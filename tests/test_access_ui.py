from copy import deepcopy
import pytest
from streamlit.testing.v1 import AppTest
from studio.access import get_store
from test_app import APP,start,healthy,goto,text,add_population_components


@pytest.fixture(autouse=True)
def facilitator_config(monkeypatch,test_verifier):
    monkeypatch.setenv('SPD_FACILITATOR_PASSWORD_HASH',test_verifier)


def register(app,name):
    app.text_input(key='access_new_group_name').set_value(name)
    app.button(key='FormSubmitter:create_group_form-Buat akses kelompok').click().run()
    healthy(app)
    assert 'auth_group_token' in app.session_state
    return app.session_state['new_group_code']['code']


def enter_facilitator(app):
    goto(app,'Hasil Kelompok')
    app.text_input(key='access_facilitator_password').set_value('facilitator-test-2026')
    app.button(key='FormSubmitter:facilitator_login_form-Masuk fasilitator').click().run()
    healthy(app)
    assert 'auth_facilitator_token' in app.session_state


def test_two_real_app_accounts_save_own_results_and_facilitator_views_without_mutating():
    a,b=start(),start()
    register(a,'Kelompok A')
    register(b,'Kelompok B')
    add_population_components(a)
    add_population_components(b)
    for app in (a,b):
        goto(app,'Simpan & Muat')
        app.button(key='save_group_result').click().run()
        healthy(app)
        assert app.session_state['result_revision']==1
    store=get_store()
    account_a=store.authenticate(a.session_state['auth_group_token'])
    account_b=store.authenticate(b.session_state['auth_group_token'])
    original_b=deepcopy(store.get_result(b.session_state['auth_group_token'],account_b['group_id']))
    goto(a,'Rancang Dashboard')
    item_id=a.session_state['design']['components'][0]['id']
    a.button(key='delete_'+item_id).click().run()
    healthy(a)
    goto(a,'Simpan & Muat')
    a.button(key='save_group_result').click().run()
    healthy(a)
    assert store.get_result(b.session_state['auth_group_token'],account_b['group_id'])==original_b
    teacher=start()
    before=deepcopy(teacher.session_state['design'])
    goto(teacher,'Hasil Kelompok')
    assert not any(x.key=='access_view_group' for x in teacher.selectbox)
    enter_facilitator(teacher)
    assert len(teacher.selectbox(key='access_view_group').options)==2
    teacher.selectbox(key='access_view_group').select(account_b['group_id']).run()
    healthy(teacher)
    assert teacher.session_state['design']==before
    assert not any(x.key.startswith(('w_filter_','w_local_filter_')) for x in teacher.multiselect)
    assert store.get_result(b.session_state['auth_group_token'],account_b['group_id'])==original_b
    teacher.button(key='archive_result').click().run()
    healthy(teacher)
    assert not store.get_result(b.session_state['auth_group_token'],account_b['group_id'])['archived']
    teacher.button(key='confirm_management').click().run()
    healthy(teacher)
    assert store.get_result(b.session_state['auth_group_token'],account_b['group_id'])['archived']==1
    assert not store.get_result(a.session_state['auth_group_token'],account_a['group_id'])['archived']
    teacher.button(key='reopen_result').click().run()
    teacher.button(key='confirm_management').click().run()
    healthy(teacher)
    assert not store.get_result(b.session_state['auth_group_token'],account_b['group_id'])['archived']


def test_reset_and_blank_require_confirmation_without_removing_access_or_saved_results():
    app=start()
    register(app,'Kelompok Aman')
    add_population_components(app)
    goto(app,'Simpan & Muat')
    app.button(key='save_group_result').click().run()
    healthy(app)
    token=app.session_state['auth_group_token']
    store=get_store()
    group_id=store.authenticate(token)['group_id']
    enter_facilitator(app)
    facilitator=app.session_state['auth_facilitator_token']
    goto(app,'Beranda')
    original=deepcopy(app.session_state['design'])
    app.button(key='start_blank').click().run()
    healthy(app)
    assert app.session_state['design']==original
    app.button(key='cancel_workspace_action').click().run()
    healthy(app)
    assert app.session_state['design']==original
    app.button(key='clear_session').click().run()
    app.button(key='confirm_workspace_action').click().run()
    healthy(app)
    assert app.session_state['design']['components']==[]
    assert app.session_state['auth_group_token']==token
    assert app.session_state['auth_facilitator_token']==facilitator
    assert store.authenticate(facilitator)['kind']=='facilitator'
    assert len(store.get_result(token,group_id)['design']['components'])==2
    goto(app,'Simpan & Muat')
    app.button(key='load_group_result').click().run()
    healthy(app)
    assert len(app.session_state['design']['components'])==2


def test_persistent_group_restore_validates_token_and_logout_revokes_it(monkeypatch):
    app=start()
    register(app,'Kelompok Kembali')
    add_population_components(app)
    goto(app,'Simpan & Muat')
    app.button(key='save_group_result').click().run()
    healthy(app)
    token=app.session_state['auth_group_token']
    import studio.access as access
    # Simulates only the browser transport, not a real browser/cookie test.
    monkeypatch.setattr(access,'_browser_session',lambda **kwargs:{'ready':True,'available':True,'cookies':{'group':token},'ack':''})
    resumed=AppTest.from_file(str(APP),default_timeout=30).run()
    healthy(resumed)
    assert resumed.session_state['design']==app.session_state['design']
    assert resumed.session_state['auth_group_token']==token
    resumed.button(key='logout_group').click().run()
    resumed.button(key='confirm_workspace_action').click().run()
    healthy(resumed)
    assert get_store().authenticate(token) is None
    app.run()
    healthy(app)
    assert 'auth_group_token' not in app.session_state


def test_facilitator_remembered_access_is_revalidated_and_logout_revokes(monkeypatch):
    teacher=start()
    enter_facilitator(teacher)
    token=teacher.session_state['auth_facilitator_token']
    import studio.access as access
    monkeypatch.setattr(access,'_browser_session',lambda **kwargs:{'ready':True,'available':True,'cookies':{'facilitator':token},'ack':''})
    resumed=AppTest.from_file(str(APP),default_timeout=30).run()
    goto(resumed,'Hasil Kelompok')
    assert not any(x.key=='access_facilitator_password' for x in resumed.text_input)
    resumed.button(key='logout_facilitator').click().run()
    healthy(resumed)
    assert get_store().authenticate(token) is None
    assert any(x.key=='access_facilitator_password' for x in resumed.text_input)
    # A remembered but revoked token cannot grant access again in a new session.
    fresh=AppTest.from_file(str(APP),default_timeout=30).run()
    goto(fresh,'Hasil Kelompok')
    assert 'auth_facilitator_token' not in fresh.session_state
    assert any(x.key=='access_facilitator_password' for x in fresh.text_input)


def test_wrong_facilitator_password_and_forged_client_role_do_not_unlock_results():
    app=start()
    goto(app,'Hasil Kelompok')
    app.text_input(key='access_facilitator_password').set_value('wrong-password')
    app.button(key='FormSubmitter:facilitator_login_form-Masuk fasilitator').click().run()
    healthy(app)
    assert 'auth_facilitator_token' not in app.session_state
    app.session_state['is_admin']=True
    app.session_state['auth_facilitator_token']='forged-session-token-'*3
    app.run()
    healthy(app)
    assert not any(x.key=='access_view_group' for x in app.selectbox)
    assert any(x.key=='access_facilitator_password' for x in app.text_input)
