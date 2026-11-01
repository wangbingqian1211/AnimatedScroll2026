import pytest
from fastapi.testclient import TestClient
from backend import main

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main,'DATA',tmp_path)
    return TestClient(main.app)


@pytest.fixture(autouse=True)
def isolate_storage(monkeypatch):
    # Unit tests never write into the configured creator database.
    monkeypatch.setenv('CREATION_DB_BACKEND','sqlite')
    monkeypatch.setenv('MODEL_PROVIDER','aihubmix')
    monkeypatch.setenv('AIHUBMIX_API_KEY','test-only-key')
    monkeypatch.delenv('DASHSCOPE_API_KEY',raising=False)
