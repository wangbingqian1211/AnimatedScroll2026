import copy
import json
import sqlite3
from backend import main


def setup_catalog(client):
    p = client.post('/api/projects').json()
    p['characters'] = [dict(id=cid, name=name, identity='', relationships='', evidence='', confirmed=False) for cid,name in [('a','朱云'),('b','汉成帝')]]
    p['sources'] = [dict(id='s', title='事件笔记', citation='创作者整理', location='', text='朱云向成帝进谏。', version=1)]
    p['paintingInfo'] = dict(name='折槛图', period='宋代', storyPeriod='汉代')
    p['personRelations'] = [dict(id='r', fromId='a', toId='b', label='进谏', description='当廷进谏', evidence=dict(sourceId='s', sourceVersion=1, quote='朱云向成帝进谏。'))]
    p['historicalEvents'] = [dict(id='e', title='当廷进谏', time='', description='朱云向成帝进谏。', characterIds=['a','b'], evidence=dict(sourceId='s',sourceVersion=1,quote='朱云向成帝进谏。'))]
    r = client.put('/api/projects/'+p['id'], json=p)
    assert r.status_code == 200, r.text
    return r.json()


def test_catalog_persisted_and_sql_projection_updated(client):
    p=setup_catalog(client)
    path='/api/projects/'+p['id']
    data=client.get(path+'/catalog').json()
    assert data['storage']=='sqlite'
    assert data['painting']['period']=='宋代'
    assert data['relations'][0]['evidenceState']=='linked'
    assert data['events'][0]['characterIds']==['a','b']
    p['characters'][0]['identity']='直谏者'
    saved=client.put(path,json=p).json()
    assert saved['version']==p['version']+1
    # Reopen a separate connection: the UI response alone is not evidence of persistence.
    with sqlite3.connect(main.DATA/'projects.sqlite') as conn:
        row=conn.execute('SELECT body FROM artwork_people WHERE project_id=? AND id=?',(p['id'],'a')).fetchone()
        assert json.loads(row[0])['identity']=='直谏者'
        assert conn.execute('SELECT name FROM artwork_catalog WHERE project_id=?',(p['id'],)).fetchone()[0]=='折槛图'
        assert conn.execute('SELECT COUNT(*) FROM artwork_relations WHERE project_id=?',(p['id'],)).fetchone()[0]==1
    assert client.get(path).json()['characters'][0]['identity']=='直谏者'


def test_catalog_conflict_keeps_database_and_projection(client):
    p=setup_catalog(client);path='/api/projects/'+p['id'];stale=copy.deepcopy(p)
    p['paintingInfo']['artist']='佚名'
    assert client.put(path,json=p).status_code==200
    stale['paintingInfo']['artist']='错误覆盖'
    assert client.put(path,json=stale).status_code==409
    assert client.get(path).json()['paintingInfo']['artist']=='佚名'
    with main.db() as conn:
        assert json.loads(conn.execute('SELECT body FROM artwork_catalog WHERE project_id=?',(p['id'],)).fetchone()[0])['artist']=='佚名'


def test_catalog_rejects_missing_people_sources_and_fabricated_quotes(client):
    p=setup_catalog(client);path='/api/projects/'+p['id']
    for field, value in [('fromId','missing'),('toId','a')]:
        bad=copy.deepcopy(p);bad['personRelations'][0][field]=value
        assert client.put(path,json=bad).status_code==422
    bad=copy.deepcopy(p);bad['historicalEvents'][0]['characterIds']=['missing']
    assert client.put(path,json=bad).status_code==422
    bad=copy.deepcopy(p);bad['personRelations'][0]['evidence']['quote']='不存在的原文'
    assert client.put(path,json=bad).status_code==422
    assert client.get(path).json()['version']==p['version']


def test_catalog_source_edits_stale_existing_links_without_destroying_quotes(client):
    p=setup_catalog(client);path='/api/projects/'+p['id']
    p['sources'][0]['text']='新的资料原文。'
    r=client.put(path,json=p)
    assert r.status_code==200,r.text
    data=client.get(path+'/catalog').json()
    assert data['sources'][0]['version']==2
    assert data['relations'][0]['evidenceState']=='stale'
    assert data['events'][0]['evidenceState']=='stale'
    assert data['events'][0]['evidence']['quote']=='朱云向成帝进谏。'


def test_catalog_projects_isolated(client):
    p=setup_catalog(client)
    other=client.post('/api/projects').json()
    data=client.get('/api/projects/'+other['id']+'/catalog').json()
    assert not data['characters'] and not data['events'] and not data['relations']
    with main.db() as conn:
        assert conn.execute('SELECT COUNT(*) FROM artwork_events WHERE project_id=?',(p['id'],)).fetchone()[0]==1
        assert conn.execute('SELECT COUNT(*) FROM artwork_events WHERE project_id=?',(other['id'],)).fetchone()[0]==0
