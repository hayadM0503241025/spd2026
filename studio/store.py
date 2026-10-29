"""Persistent results with server-side ownership, expiry and revision checks.

Each operation opens its own transaction. No user data is held in shared caches.
SQLite is for a durable local disk; PostgreSQL is available for hosted deployments.
"""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import secrets
import sqlite3
import time
from uuid import uuid4
from studio.config import export_design
from studio.data import load_shared
from studio.security import hash_password, verify_password, token_digest


class AccessDenied(ValueError):
    pass


class Conflict(ValueError):
    pass


class StoreUnavailable(RuntimeError):
    pass


class Store:
    def __init__(self,database_url,facilitator_hash='',session_days=30,clock=time.time):
        self.database_url=database_url
        self.facilitator_hash=facilitator_hash
        self.session_days=session_days
        self.clock=clock
        self.postgres=database_url.startswith(('postgresql://','postgres://'))
        if not self.postgres and not database_url.startswith('sqlite:///'):
            raise StoreUnavailable('Penyimpanan harus menggunakan SQLite atau PostgreSQL.')
        self._initialize()

    @contextmanager
    def connection(self):
        connection=None
        try:
            if self.postgres:
                import psycopg
                from psycopg.rows import dict_row
                connection=psycopg.connect(self.database_url,row_factory=dict_row,connect_timeout=10)
            else:
                path=Path(self.database_url[len('sqlite:///'):])
                path.parent.mkdir(parents=True,exist_ok=True)
                connection=sqlite3.connect(path,timeout=20)
                connection.row_factory=sqlite3.Row
                connection.execute('PRAGMA foreign_keys=ON')
                connection.execute('PRAGMA busy_timeout=20000')
            yield connection
            connection.commit()
        except (sqlite3.Error,ImportError) as exc:
            if connection:
                connection.rollback()
            raise StoreUnavailable('Penyimpanan hasil tidak tersedia. Periksa konfigurasi atau koneksi database; data tidak dialihkan ke database lain.') from exc
        except Exception as exc:
            if connection:
                connection.rollback()
            if self.postgres and type(exc).__module__.startswith('psycopg'):
                raise StoreUnavailable('Database PostgreSQL tidak dapat diakses. Periksa koneksi/Secrets; tidak ada penyimpanan pengganti otomatis.') from exc
            raise
        finally:
            if connection:
                connection.close()

    def sql(self,conn,query,params=()):
        return conn.execute(query.replace('?', '%s') if self.postgres else query,params)

    def _initialize(self):
        schema=(
            'CREATE TABLE IF NOT EXISTS studio_settings (key TEXT PRIMARY KEY,value TEXT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS studio_groups (id TEXT PRIMARY KEY,name TEXT NOT NULL,code_hash TEXT NOT NULL,created BIGINT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS studio_sessions (token_hash TEXT PRIMARY KEY,kind TEXT NOT NULL,group_id TEXT REFERENCES studio_groups(id),created BIGINT NOT NULL,expires BIGINT NOT NULL,verifier_fingerprint TEXT NOT NULL DEFAULT \'\')',
            'CREATE TABLE IF NOT EXISTS studio_results (group_id TEXT PRIMARY KEY REFERENCES studio_groups(id),payload TEXT,revision INTEGER NOT NULL DEFAULT 0,archived INTEGER NOT NULL DEFAULT 0,updated BIGINT NOT NULL)',
            'CREATE TABLE IF NOT EXISTS studio_versions (group_id TEXT NOT NULL REFERENCES studio_groups(id),revision INTEGER NOT NULL,payload TEXT NOT NULL,created BIGINT NOT NULL,action TEXT NOT NULL,actor_kind TEXT NOT NULL,PRIMARY KEY(group_id,revision))',
            'CREATE TABLE IF NOT EXISTS studio_attempts (key TEXT PRIMARY KEY,count INTEGER NOT NULL,started BIGINT NOT NULL)',
            'CREATE INDEX IF NOT EXISTS studio_sessions_expiry ON studio_sessions(expires)',
        )
        with self.connection() as conn:
            if not self.postgres:
                conn.execute('PRAGMA journal_mode=WAL')
            for query in schema:
                self.sql(conn,query)
            if self.postgres:
                self.sql(conn,"ALTER TABLE studio_sessions ADD COLUMN IF NOT EXISTS verifier_fingerprint TEXT NOT NULL DEFAULT ''")
            elif 'verifier_fingerprint' not in {r['name'] for r in conn.execute('PRAGMA table_info(studio_sessions)')}:
                conn.execute("ALTER TABLE studio_sessions ADD COLUMN verifier_fingerprint TEXT NOT NULL DEFAULT ''")
            self.sql(conn,'INSERT INTO studio_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO NOTHING',('instance_id',uuid4().hex))
            fingerprint=hashlib.sha256(self.facilitator_hash.encode()).hexdigest()
            row=self.sql(conn,'SELECT value FROM studio_settings WHERE key=?',('facilitator_hash',)).fetchone()
            if row is not None and row['value']!=fingerprint:
                self.sql(conn,"DELETE FROM studio_sessions WHERE kind='facilitator'")
            self.sql(conn,'INSERT INTO studio_settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',('facilitator_hash',fingerprint))
            row=self.sql(conn,'SELECT value FROM studio_settings WHERE key=?',('instance_id',)).fetchone()
            self.instance_id=row['value']

    def _now(self):
        return int(self.clock())

    def _new_session(self,conn,kind,group_id,remember):
        token=secrets.token_urlsafe(32)
        now=self._now()
        duration=self.session_days*86400 if remember else 86400
        fingerprint=hashlib.sha256(self.facilitator_hash.encode()).hexdigest() if kind=='facilitator' else ''
        self.sql(conn,'INSERT INTO studio_sessions(token_hash,kind,group_id,created,expires,verifier_fingerprint) VALUES(?,?,?,?,?,?)',
                 (token_digest(token),kind,group_id,now,now+duration,fingerprint))
        self.sql(conn,'DELETE FROM studio_sessions WHERE expires<=?',(now,))
        return token

    def _actor(self,conn,token):
        actor=self.sql(conn,'SELECT s.kind,s.group_id,s.expires,s.verifier_fingerprint,g.name FROM studio_sessions s LEFT JOIN studio_groups g ON s.group_id=g.id WHERE s.token_hash=? AND s.expires>?',
                       (token_digest(token),self._now())).fetchone()
        if actor is None:
            raise AccessDenied('Akses belum masuk atau sudah berakhir. Silakan masuk kembali.')
        if actor['kind']=='facilitator':
            current=self.sql(conn,'SELECT value FROM studio_settings WHERE key=?',('facilitator_hash',)).fetchone()
            if not current or current['value']!=actor['verifier_fingerprint']:
                raise AccessDenied('Akses fasilitator sudah dicabut. Silakan masuk kembali.')
        return dict(actor)

    def authenticate(self,token):
        if not token_digest(token):
            return None
        with self.connection() as conn:
            try:
                return self._actor(conn,token)
            except AccessDenied:
                return None

    def _scope(self,conn,token,group_id,admin_only=False):
        actor=self._actor(conn,token)
        if actor['kind']=='facilitator':
            return actor
        if admin_only or actor['kind']!='group' or actor['group_id']!=group_id:
            raise AccessDenied('Tindakan ini tidak diizinkan untuk kelompok lain.')
        return actor

    def _attempt_key(self,kind,target,client):
        return hashlib.sha256(f'{kind}:{target}:{client}'.encode()).hexdigest()

    def _check_attempts(self,conn,key):
        row=self.sql(conn,'SELECT count,started FROM studio_attempts WHERE key=?',(key,)).fetchone()
        if row and row['count']>=5 and self._now()-row['started']<900:
            raise AccessDenied('Terlalu banyak percobaan masuk. Coba lagi setelah 15 menit.')

    def _failed_attempt(self,conn,key):
        now=self._now()
        # Atomic increments prevent simultaneous failed attempts from resetting a counter.
        self.sql(conn,'INSERT INTO studio_attempts(key,count,started) VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=CASE WHEN studio_attempts.started<=? THEN 1 ELSE studio_attempts.count+1 END,started=CASE WHEN studio_attempts.started<=? THEN excluded.started ELSE studio_attempts.started END',
                 (key,now,now-900,now-900))

    def login_facilitator(self,password,remember=True,client='local'):
        if not self.facilitator_hash:
            raise AccessDenied('Kata sandi fasilitator belum dikonfigurasi pada Secrets.')
        key=self._attempt_key('facilitator','facilitator',client)
        token=None
        with self.connection() as conn:
            self._check_attempts(conn,key)
            current=self.sql(conn,'SELECT value FROM studio_settings WHERE key=?',('facilitator_hash',)).fetchone()
            if not current or current['value']!=hashlib.sha256(self.facilitator_hash.encode()).hexdigest():
                raise AccessDenied('Konfigurasi fasilitator telah berubah. Muat ulang aplikasi.')
            if verify_password(password,self.facilitator_hash):
                self.sql(conn,'DELETE FROM studio_attempts WHERE key=?',(key,))
                token=self._new_session(conn,'facilitator',None,remember)
            else:
                self._failed_attempt(conn,key)
        if token is None:
            raise AccessDenied('Kata sandi fasilitator tidak sesuai.')
        return token

    def create_group(self,name,remember=True):
        name=' '.join(str(name).split())
        if not 1<=len(name)<=120:
            raise ValueError('Nama kelompok wajib diisi, maksimal 120 karakter.')
        group_id=uuid4().hex
        secret=secrets.token_urlsafe(18)
        verifier=hash_password(secret)
        now=self._now()
        with self.connection() as conn:
            self.sql(conn,'INSERT INTO studio_groups(id,name,code_hash,created) VALUES(?,?,?,?)',(group_id,name,verifier,now))
            self.sql(conn,'INSERT INTO studio_results(group_id,revision,archived,updated) VALUES(?,0,0,?)',(group_id,now))
            token=self._new_session(conn,'group',group_id,remember)
        return {'id':group_id,'name':name,'code':group_id+'.'+secret,'token':token}

    def login_group(self,code,remember=True,client='local'):
        code=code.strip() if isinstance(code,str) else ''
        group_id,separator,password=code.partition('.')
        if not separator or len(group_id)!=32 or len(password)>256:
            group_id='invalid'
        key=self._attempt_key('group',group_id,client)
        token=None
        with self.connection() as conn:
            self._check_attempts(conn,key)
            row=self.sql(conn,'SELECT code_hash FROM studio_groups WHERE id=?',(group_id,)).fetchone()
            if row and verify_password(password,row['code_hash']):
                self.sql(conn,'DELETE FROM studio_attempts WHERE key=?',(key,))
                token=self._new_session(conn,'group',group_id,remember)
            else:
                self._failed_attempt(conn,key)
        if token is None:
            raise AccessDenied('Kode akses kelompok tidak sesuai.')
        return token

    def logout(self,token):
        with self.connection() as conn:
            self.sql(conn,'DELETE FROM studio_sessions WHERE token_hash=?',(token_digest(token),))

    def _payload(self,design,name):
        design=deepcopy(design)
        design['group_name']=name
        bundle=load_shared(design['dataset_ref']['version'])
        return export_design(design,bundle).decode('utf-8')

    def get_result(self,token,group_id):
        with self.connection() as conn:
            self._scope(conn,token,group_id)
            row=self.sql(conn,'SELECT r.*,g.name FROM studio_results r JOIN studio_groups g ON g.id=r.group_id WHERE r.group_id=?',(group_id,)).fetchone()
            if row is None:
                raise AccessDenied('Hasil kelompok tidak ditemukan.')
            output=dict(row)
            payload=output.pop('payload')
            output['design']=json.loads(payload) if payload else None
            return output

    def _commit_result(self,conn,actor,group_id,payload,expected_revision,action='save',archived=0):
        if type(expected_revision) is not int or expected_revision<0:
            raise Conflict('Versi hasil belum diketahui. Muat hasil tersimpan terlebih dahulu.')
        now=self._now()
        cursor=self.sql(conn,'UPDATE studio_results SET payload=?,revision=revision+1,archived=?,updated=? WHERE group_id=? AND revision=?',
                        (payload,archived,now,group_id,expected_revision))
        if cursor.rowcount!=1:
            raise Conflict('Hasil sudah diperbarui pada sesi lain. Unduh draft ini lalu muat versi terbaru sebelum menyimpan lagi.')
        revision=expected_revision+1
        self.sql(conn,'INSERT INTO studio_versions(group_id,revision,payload,created,action,actor_kind) VALUES(?,?,?,?,?,?)',
                 (group_id,revision,payload,now,action,actor['kind']))
        return revision

    def save_result(self,token,group_id,design,expected_revision):
        with self.connection() as conn:
            actor=self._scope(conn,token,group_id)
            row=self.sql(conn,'SELECT r.archived,g.name FROM studio_results r JOIN studio_groups g ON g.id=r.group_id WHERE r.group_id=?',(group_id,)).fetchone()
            if row is None:
                raise AccessDenied('Kelompok tidak ditemukan.')
            if row['archived'] and actor['kind']!='facilitator':
                raise AccessDenied('Hasil sedang diarsipkan fasilitator. Hubungi fasilitator untuk membuka kembali.')
            payload=self._payload(design,row['name'])
            return self._commit_result(conn,actor,group_id,payload,expected_revision)

    def list_results(self,token):
        with self.connection() as conn:
            self._scope(conn,token,None,admin_only=True)
            rows=self.sql(conn,'SELECT g.id,g.name,g.created,r.payload,r.revision,r.archived,r.updated FROM studio_groups g JOIN studio_results r ON r.group_id=g.id ORDER BY r.updated DESC,g.id').fetchall()
            output=[]
            for row in rows:
                record=dict(row)
                payload=record.pop('payload')
                design=json.loads(payload) if payload else None
                record['components']=len(design['components']) if design else 0
                record['dataset_version']=design['dataset_ref']['version'] if design else ''
                record['has_result']=design is not None
                output.append(record)
            return output

    def history(self,token,group_id):
        with self.connection() as conn:
            self._scope(conn,token,group_id)
            rows=self.sql(conn,'SELECT revision,created,action,actor_kind FROM studio_versions WHERE group_id=? ORDER BY revision DESC',(group_id,)).fetchall()
            return [dict(row) for row in rows]

    def archive(self,token,group_id,expected_revision):
        with self.connection() as conn:
            actor=self._scope(conn,token,group_id,admin_only=True)
            row=self.sql(conn,'SELECT payload FROM studio_results WHERE group_id=?',(group_id,)).fetchone()
            if row is None or row['payload'] is None:
                raise ValueError('Belum ada hasil untuk diarsipkan.')
            return self._commit_result(conn,actor,group_id,row['payload'],expected_revision,'archive',1)

    def restore(self,token,group_id,source_revision,expected_revision):
        with self.connection() as conn:
            actor=self._scope(conn,token,group_id)
            current=self.sql(conn,'SELECT archived FROM studio_results WHERE group_id=?',(group_id,)).fetchone()
            if current and current['archived'] and actor['kind']!='facilitator':
                raise AccessDenied('Hanya fasilitator yang dapat membuka hasil yang diarsipkan.')
            row=self.sql(conn,'SELECT payload FROM studio_versions WHERE group_id=? AND revision=?',(group_id,source_revision)).fetchone()
            if row is None:
                raise ValueError('Versi hasil tidak ditemukan.')
            return self._commit_result(conn,actor,group_id,row['payload'],expected_revision,'restore',0)
