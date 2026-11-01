import copy
import pytest
from fastapi.testclient import TestClient
from backend import main,relations,vision
from test_import import wait


def project():
    return dict(characters=[dict(id='a',name='成帝'),dict(id='b',name='张禹')],sources=[dict(id='s',version=3,title='人物史料',text='成帝是张禹的学生。')])


def candidate():return dict(fromId='a',toId='b',label='弟子',description='师生关系',sourceId='s',quote='成帝是张禹的学生。')


def test_relation_extraction_binds_exact_quote_and_current_version():
    rows=relations.bind(project(),[candidate(),candidate()])
    assert len(rows)==1
    assert rows[0]['origin']=='model' and not rows[0]['confirmed']
    assert rows[0]['evidence']==dict(sourceId='s',sourceVersion=3,quote='成帝是张禹的学生。')
    for field,value in [('fromId','missing'),('toId','a'),('quote','不存在的原文')]:
        row=candidate();row[field]=value
        with pytest.raises(ValueError):relations.bind(project(),[row])
    p=project();p['sources'][0]['sourceType']='creative_intent'
    with pytest.raises(ValueError):relations.bind(p,[candidate()])


def test_relation_merge_preserves_creator_edits_and_stable_candidate_ids():
    p=project();first=relations.bind(p,[candidate()])[0]
    p['personRelations']=[first]
    relations.merge(p,relations.bind(p,[candidate()]))
    assert p['personRelations'][0]['id']==first['id']
    manual=dict(first,origin='manual',label='师生',confirmed=True)
    p['personRelations']=[manual]
    reverse=dict(first,id='new',fromId='b',toId='a',label='老师')
    relations.merge(p,[reverse])
    assert p['personRelations']==[manual]
    p['personRelations']=[];p['dismissedRelationKeys']=[relations.key(first)]
    relations.merge(p,[first])
    assert not p['personRelations']


def test_relation_only_task_needs_no_image_and_persists_candidates(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DATA',tmp_path);monkeypatch.setenv('AIHUBMIX_API_KEY','fake')
    calls=[]
    async def extract(p):
        calls.append('relations')
        return relations.bind(p,[dict(fromId=p['characters'][1]['id'],toId=p['characters'][2]['id'],label='弟子',sourceId=p['sources'][0]['id'],quote=p['sources'][0]['text'])])
    monkeypatch.setattr(relations,'extract',extract)
    with TestClient(main.app) as client:
        p=client.post('/api/sample?example=zhekan').json();path='/api/projects/'+p['id']
        p['image']='';p=client.put(path,json=p).json()
        assert client.post(path+'/tasks',json=dict(version=p['version'],kind='relations_analysis',trigger='page_enter')).status_code==422
        assert client.post(path+'/tasks',json=dict(version=p['version'],kind='relations_analysis',trigger='user_button')).status_code==200
        assert wait(client,p['id'])['status']=='completed'
        saved=client.get(path).json()
        assert len(saved['personRelations'])==1 and not saved['personRelations'][0]['confirmed']
        assert client.get(path+'/catalog').json()['relations'][0]['origin']=='model'
        assert calls==['relations']


def test_fast_person_task_does_not_run_relation_stage(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DATA',tmp_path);monkeypatch.setenv('AIHUBMIX_API_KEY','fake')
    monkeypatch.setattr(vision,'detect',lambda *args:[dict(id='a',x=.1,y=.1,w=.2,h=.3,kind='character',origin='detector',description='',characterId='',confirmed=False)])
    async def analyze(*args):return dict(overview={},observations=[])
    async def match(path,p):return [dict(id='m',annotationId='a',characterId=p['characters'][0]['id'],confirmed=False)]
    async def fail(*args):raise ValueError('文本服务失败')
    monkeypatch.setattr(vision,'analyze',analyze);monkeypatch.setattr(vision,'match_people',match);monkeypatch.setattr(relations,'extract',fail)
    with TestClient(main.app) as client:
        p=client.post('/api/sample?example=zhekan').json();path='/api/projects/'+p['id']
        assert client.post(path+'/tasks',json=dict(version=p['version'],kind='people_analysis')).status_code==200
        task=wait(client,p['id'])
        assert task['status']=='completed' and task['applied']
        assert not task.get('partialFailure')
        saved=client.get(path).json()
        assert saved['annotations'][0]['characterId']==p['characters'][0]['id']
        assert not saved['personRelations']
