from dataclasses import dataclass
from pathlib import Path
import os
import tomllib

ROOT=Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AccessSettings:
    database_url: str
    facilitator_hash: str
    session_days: int=30


def read_settings():
    values={}
    path=ROOT/'.streamlit'/'secrets.toml'
    if path.is_file():
        values=tomllib.loads(path.read_text(encoding='utf-8')).get('studio_access',{})
    # On Community Cloud the same section is provided by the Secrets UI.
    try:
        import streamlit as st
        values={**values,**dict(st.secrets.get('studio_access',{}))}
    except (FileNotFoundError,KeyError):
        pass
    database=os.environ.get('SPD_DATABASE_URL') or values.get('database_url')
    if not database:
        database='sqlite:///'+str(ROOT/'runtime'/'studio.sqlite3')
    verifier=os.environ.get('SPD_FACILITATOR_PASSWORD_HASH') or values.get('facilitator_password_hash','')
    days=int(os.environ.get('SPD_SESSION_DAYS') or values.get('session_days',30))
    if not 1<=days<=365:
        raise ValueError('session_days harus antara 1 dan 365.')
    return AccessSettings(str(database),str(verifier),days)
