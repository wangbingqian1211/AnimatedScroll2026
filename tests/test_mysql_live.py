"""Opt-in real MySQL verification. Only per-test projects are created and removed."""
import copy
import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from backend import main, storage

pytestmark=pytest.mark.skipif(os.getenv('CREATION_TEST_MYSQL')!='1',reason='Real MySQL tests require CREATION_TEST_MYSQL=1')

@pytest.fixture
def mysql_client(monkeypatch):
    monkeypatch.setenv('CREATION_DB_BACKEND','mysql')
    client=TestClient(main.app)
    created=[]
    def create():
        p=client.post('/api/projects').json()
        created.append(p['id'])
        return p
    yield client,create
    with main.db() as conn:
        for pid in created:
            for table in ('artwork_events','artwork_relations','artwork_sources','artwork_people','artwork_catalog'):
                conn.execute(f'DELETE FROM {table} WHERE project_id=?',(pid,))
            for table in ('events','tasks'):
                conn.execute(f'DELETE FROM {table} WHERE project=?',(pid,))
            conn.execute('DELETE FROM projects WHERE id=?',(pid,))


def test_mysql_catalog_unicode_and_large_source_persistence(mysql_client):
    client,create=mysql_client;p=create();path='/api/projects/'+p['id']
    p['paintingInfo']['name']='折槛图 · MySQL 验证 🎨'
    p['sources']=[dict(id='source',title='长文资料',text='原文与出处。'*12000,citation='测试原文',location='',version=1)]
    saved=client.put(path,json=p)
    assert saved.status_code==200,saved.text
    catalog=client.get(path+'/catalog').json()
    assert catalog['storage']=='mysql'
    assert catalog['painting']['name']=='折槛图 · MySQL 验证 🎨'
    with main.db() as conn:
        import json
        body=conn.execute('SELECT body FROM artwork_sources WHERE project_id=? AND id=?',(p['id'],'source')).fetchone()[0]
        assert json.loads(body)['text']==p['sources'][0]['text']
    assert client.get('/api/database/status').json()==dict(backend='mysql',connected=True)


def test_mysql_concurrent_version_conflict_has_one_winner(mysql_client):
    client,create=mysql_client;p=create();path='/api/projects/'+p['id']
    def change(name):
        draft=copy.deepcopy(p);draft['title']=name
        return client.put(path,json=draft).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(change,['版本甲','版本乙']))
    assert sorted(results)==[200,409]
    assert client.get(path).json()['version']==p['version']+1
    assert len(client.get(path+'/events').json())==2


def test_mysql_catalog_and_audit_roll_back_together(mysql_client,monkeypatch):
    client,create=mysql_client;p=create();path='/api/projects/'+p['id']
    import backend.catalog as catalog
    def fail(*args):raise ValueError('Simulated SQL projection failure')
    monkeypatch.setattr(catalog,'synchronize',fail)
    p['title']='This must not be committed'
    with pytest.raises(ValueError,match='Simulated'):
        client.put(path,json=p)
    assert client.get(path).json()['title']=='未命名项目'
    assert len(client.get(path+'/events').json())==1


def test_mysql_task_upsert_and_order(mysql_client):
    client,create=mysql_client;p=create()
    import json
    with main.db() as conn:
        for tid,time in [('older','2026-01-01T00:00:00'),('newer','2026-01-02T00:00:00')]:
            task=dict(id=tid,projectId=p['id'],time=time,status='completed')
            # Globally unique task IDs, so no creator task can be overwritten.
            task['id']=p['id']+tid
            conn.execute('INSERT OR REPLACE INTO tasks VALUES (?,?,?)',(task['id'],p['id'],json.dumps(task)))
            conn.execute('INSERT OR REPLACE INTO tasks VALUES (?,?,?)',(task['id'],p['id'],json.dumps(task)))
    rows=client.get('/api/projects/'+p['id']+'/tasks').json()
    assert len(rows)==2 and rows[0]['id'].endswith('newer')
