import copy
from backend import main,catalog
from backend.artwork_library import build_project
from backend.removal import remove_person


def test_person_removal_cleans_graph_and_preserves_authored_text(client):
    p=main.save(build_project('chongping','/api/images/test.jpg'),0,'test')
    target=p['characters'][0]['id'];aid=p['annotations'][0]['id']
    unit=p['scenes'][0]['units'][-1]
    unit['speakerId']=target
    unit['references']=[dict(sourceId=p['sources'][0]['id'],sourceVersion=1,quote=p['sources'][0]['text'],annotationId=aid)]
    p=main.save(p,p['version'],'test')
    r=client.post(f"/api/projects/{p['id']}/people/{aid}/remove",json={'version':p['version']})
    assert r.status_code==200,r.text
    new=r.json();catalog.validate(new)
    assert target not in {c['id'] for c in new['characters']}
    assert aid not in {a['id'] for a in new['annotations']}
    assert all(target not in s['characterIds'] for s in new['scenes'])
    assert all(target not in (r['fromId'],r['toId']) for r in new['personRelations'])
    assert all(target not in e['characterIds'] for e in new['historicalEvents'])
    assert all(q['personId']!=target for c in new['interaction']['chapters'] for q in c['questions'])
    saved_unit=new['scenes'][0]['units'][-1]
    assert saved_unit['text']==unit['text'] and saved_unit['speakerId']==''
    assert saved_unit['references'][0]['annotationId']=='' and saved_unit['status']=='pending'
    assert client.post(f"/api/projects/{p['id']}/people/{aid}/remove",json={'version':p['version']}).status_code==409


def test_remove_shared_annotation_keeps_character_but_character_removal_cleans_all(client):
    p=build_project('chongping','/api/images/test.jpg')
    a=copy.deepcopy(p['annotations'][0]);a['id']='second-box';p['annotations'].append(a)
    result=remove_person(p,annotation_id=a['id'])
    assert result['characters']==p['characters']
    p=main.save(p,0,'test')
    r=client.post(f"/api/projects/{p['id']}/characters/{a['characterId']}/remove",json={'version':p['version']})
    assert r.status_code==200,r.text
    assert all(x.get('characterId')!=a['characterId'] for x in r.json()['annotations'])


def test_removing_guide_clears_guide_selection_and_locked_text_requires_unlock(client):
    p=build_project('bunian','/api/images/test.jpg')
    guide=p['interaction']['guideAnnotationIds'][0]
    result=remove_person(p,annotation_id=guide)
    assert result['interaction']['guideAnnotationIds']==[]
    p['scenes'][0]['units'][-1].update(speakerId=p['characters'][0]['id'],locked=True)
    p=main.save(p,0,'test')
    r=client.post(f"/api/projects/{p['id']}/characters/{p['characters'][0]['id']}/remove",json={'version':p['version']})
    assert r.status_code==422
    assert main.get(p['id'])['version']==p['version']


def test_deleted_project_can_be_restored_even_when_last_project(client):
    p=client.post('/api/projects').json()
    removed=client.post(f"/api/projects/{p['id']}/archive",json={'version':p['version']}).json()
    assert client.get('/api/projects').json()==[]
    url=f"/api/projects/{p['id']}/restore"
    assert client.post(url,json={'version':p['version']}).status_code==409
    restored=client.post(url,json={'version':removed['version']})
    assert restored.status_code==200 and not restored.json()['archived']
    assert client.get('/api/projects').json()[0]['id']==p['id']
