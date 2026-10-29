"""Streamlit access state. Every role is derived from a live database session."""
from pathlib import Path
from uuid import uuid4
import streamlit as st
import streamlit.components.v1 as components
from studio.settings import read_settings
from studio.store import Store

_browser_session=components.declare_component('studio_browser_session',path=str(Path(__file__).with_name('browser_session')))


@st.cache_resource(show_spinner=False)
def configured_store(database_url,facilitator_hash,session_days):
    # Only immutable configuration lives on this object; connections and all
    # permissions are evaluated per operation, never cached by group name.
    return Store(database_url,facilitator_hash,session_days)


def get_store():
    settings=read_settings()
    return configured_store(settings.database_url,settings.facilitator_hash,settings.session_days)


def queue_cookie(role,token='',remember=False):
    values=dict(st.session_state.get('auth_cookie_command',{}).get('values',{}))
    values[role]={'token':token,'remember':remember}
    st.session_state['auth_cookie_command']={'nonce':uuid4().hex,'values':values}


def sync_browser(store):
    names={role:f'spd_{store.instance_id[:12]}_{role}' for role in ('group','facilitator')}
    command=st.session_state.get('auth_cookie_command')
    reply=_browser_session(names=names,command=command,max_age=store.session_days*86400,key='auth_browser_bridge',default=None)
    if isinstance(reply,dict) and reply.get('ready'):
        st.session_state['auth_cookie_available']=bool(reply.get('available'))
        if not st.session_state.get('auth_cookie_bootstrapped'):
            for role in names:
                key='auth_'+role+'_token'
                candidate=reply.get('cookies',{}).get(role)
                if not st.session_state.get(key) and candidate:
                    actor=store.authenticate(candidate)
                    if actor and actor['kind']==role:
                        st.session_state[key]=candidate
                    else:
                        queue_cookie(role)
            st.session_state['auth_cookie_bootstrapped']=True
        current_command=st.session_state.get('auth_cookie_command')
        if current_command and reply.get('ack')==current_command['nonce']:
            st.session_state.pop('auth_cookie_command',None)
    for role in names:
        key='auth_'+role+'_token'
        token=st.session_state.get(key)
        if token:
            actor=store.authenticate(token)
            if not actor or actor['kind']!=role:
                st.session_state.pop(key,None)
                queue_cookie(role)


def group_access(store):
    token=st.session_state.get('auth_group_token','')
    actor=store.authenticate(token)
    return actor if actor and actor['kind']=='group' else None


def facilitator_access(store):
    token=st.session_state.get('auth_facilitator_token','')
    actor=store.authenticate(token)
    return actor if actor and actor['kind']=='facilitator' else None


def client_key():
    return str(getattr(st.context,'ip_address',None) or 'local')


def set_access(role,token,remember):
    st.session_state['auth_'+role+'_token']=token
    queue_cookie(role,token,remember)


def logout_facilitator(store):
    store.logout(st.session_state.get('auth_facilitator_token',''))
    st.session_state.pop('auth_facilitator_token',None)
    queue_cookie('facilitator')


def logout_group(store):
    store.logout(st.session_state.get('auth_group_token',''))
    st.session_state.pop('auth_group_token',None)
    st.session_state.pop('group_loaded_id',None)
    st.session_state.pop('result_revision',None)
    st.session_state.pop('new_group_code',None)
    queue_cookie('group')
