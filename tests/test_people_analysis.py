import pytest
from fastapi.testclient import TestClient
from backend import main,vision,relations
from test_import import wait


def box(aid='saved'):
    return dict(id=aid,x=.1,y=.1,w=.2,h=.3,kind='character',description='',characterId='',confirmed=False,origin='detector')


@pytest.fixture
def analysis_client(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DATA',tmp_path)
    monkeypatch.setenv('AIHUBMIX_API_KEY','test-only-key')
    with TestClient(main.app) as client:yield client


def test_saved_boxes_match_names_without_detection_or_per_person_calls(analysis_client,monkeypatch):
    client=analysis_client;p=client.post('/api/sample?example=zhekan').json();path='/api/projects/'+p['id'];calls=[]
    p['annotations']=[box()];p=client.put(path,json=p).json()
    def forbidden(*args):raise AssertionError('should reuse saved annotations')
    async def no_extra_calls(*args):raise AssertionError('no per-person or relation analysis')
    async def match(path,project):
        calls.append('match')
        return [dict(id='m',annotationId='saved',characterId=p['characters'][0]['id'],confirmed=False)]
    monkeypatch.setattr(vision,'detect',forbidden);monkeypatch.setattr(vision,'analyze',no_extra_calls);monkeypatch.setattr(relations,'extract',no_extra_calls);monkeypatch.setattr(vision,'match_people',match)
    assert client.post(path+'/tasks',json=dict(version=p['version'],kind='people_analysis')).status_code==200
    assert wait(client,p['id'])['status']=='completed'
    saved=client.get(path).json()
    assert calls==['match'] and saved['annotations'][0]['id']=='saved'
    assert saved['annotations'][0]['characterId']==p['characters'][0]['id']


def test_legacy_empty_project_only_detects_and_matches_once(analysis_client,monkeypatch):
    client=analysis_client;p=client.post('/api/sample?example=zhekan').json();path='/api/projects/'+p['id'];calls=[]
    def detect(*args):calls.append('detect');return [box('found')]
    async def match(path,project):
        calls.append('match');return [dict(id='m',annotationId='found',characterId=p['characters'][0]['id'],confirmed=False)]
    async def forbidden(*args):raise AssertionError('slow stages should not run')
    monkeypatch.setattr(vision,'detect',detect);monkeypatch.setattr(vision,'match_people',match);monkeypatch.setattr(vision,'analyze',forbidden);monkeypatch.setattr(relations,'extract',forbidden)
    assert client.post(path+'/tasks',json=dict(version=p['version'],kind='people_analysis')).status_code==200
    assert wait(client,p['id'])['status']=='completed'
    assert calls==['detect','match']


def test_browsing_preserves_saved_labels_without_any_model(analysis_client,monkeypatch):
    client=analysis_client;p=client.post('/api/sample?example=zhekan').json();path='/api/projects/'+p['id']
    a=box();a['characterId']=p['characters'][0]['id'];p['annotations']=[a];p=client.put(path,json=p).json()
    def forbidden(*args):raise AssertionError('browsing should not analyze')
    for method in ('detect','analyze','match_people'):monkeypatch.setattr(vision,method,forbidden)
    monkeypatch.setattr(relations,'extract',forbidden)
    assert client.get(path).json()['annotations']==p['annotations']
    listing=next(r for r in client.get('/api/projects').json() if r['id']==p['id'])
    assert listing['annotationCount']==1
    assert client.get(path+'/tasks').json()==[]


def test_fast_name_match_preserves_manual_identity(analysis_client,monkeypatch):
    client=analysis_client;p=client.post('/api/sample?example=zhekan').json();path='/api/projects/'+p['id'];cid=p['characters'][0]['id']
    a=box();a['characterId']=cid;p['annotations']=[a];p=client.put(path,json=p).json()
    p=client.post(path+'/people/saved/confirm',json=dict(version=p['version'],characterId=cid)).json()
    async def match(*args):return [dict(id='m',annotationId='saved',characterId=p['characters'][1]['id'],confirmed=False)]
    monkeypatch.setattr(vision,'match_people',match)
    assert client.post(path+'/tasks',json=dict(version=p['version'],kind='people_analysis')).status_code==200
    assert wait(client,p['id'])['status']=='completed'
    assert client.get(path).json()['annotations'][0]['characterId']==cid


def test_failed_matching_preserves_project(analysis_client,monkeypatch):
    client=analysis_client;p=client.post('/api/sample?example=zhekan').json();path='/api/projects/'+p['id']
    p['annotations']=[box()];p=client.put(path,json=p).json()
    async def fail(*args):raise ValueError('service unavailable')
    monkeypatch.setattr(vision,'match_people',fail)
    assert client.post(path+'/tasks',json=dict(version=p['version'],kind='people_analysis')).status_code==200
    assert wait(client,p['id'])['status']=='failed'
    assert client.get(path).json()==p


def test_missing_detector_dependency_is_actionable(analysis_client,monkeypatch):
    client=analysis_client;p=client.post('/api/sample?example=zhekan').json();path='/api/projects/'+p['id']
    def fail(*args):raise ModuleNotFoundError("No module named 'torch'",name='torch')
    monkeypatch.setattr(vision,'detect',fail)
    assert client.post(path+'/tasks',json=dict(version=p['version'],kind='detect')).status_code==200
    task=wait(client,p['id'])
    assert task['status']=='failed' and 'torch' in task['progress'] and '缺少组件' in task['progress']
    assert client.get(path).json()==p


def test_detector_preflight_reports_all_missing_packages(monkeypatch):
    monkeypatch.setattr(vision,'missing_detector_modules',lambda:['torch','transformers'])
    with pytest.raises(ValueError,match='torch, transformers'):vision.detect('not-opened.png')
