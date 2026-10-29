import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def isolated_results_database(tmp_path,monkeypatch):
    # App tests never touch a real class's results or private facilitator verifier.
    monkeypatch.setenv('SPD_DATABASE_URL','sqlite:///'+str(tmp_path/'results.sqlite3'))


@pytest.fixture(scope='session')
def test_verifier():
    from studio.security import hash_password
    return hash_password('facilitator-test-2026')


@pytest.fixture
def store(tmp_path,test_verifier):
    from studio.store import Store
    return Store('sqlite:///'+str(tmp_path/'protected.sqlite3'),test_verifier)


@pytest.fixture
def bundle():
    from studio.data import load_shared
    return load_shared()
