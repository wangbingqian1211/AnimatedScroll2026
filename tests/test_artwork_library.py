import pytest
from PIL import Image
from backend import main,catalog,narrative
from backend.models import Project
from backend.artwork_library import build_project,rectangle,SPECS,ARTICLES,ZHEKAN_BOXES


@pytest.mark.parametrize('key,count',[('chongping',8),('bunian',14)])
def test_curated_artworks_have_valid_draft_graphs_and_no_automatic_approvals(key,count,tmp_path):
    p=Project.model_validate(build_project(key,'/api/images/art.jpg')).model_dump()
    catalog.validate(p)
    Image.new('RGB',SPECS[key]['size'],'tan').save(tmp_path/'art.jpg')
    assert len(p['characters'])==len(p['annotations'])==count
    assert len(p['scenes'])==3
    assert len(p['interaction']['chapters'])==3
    assert sum(len(c['questions']) for c in p['interaction']['chapters'])==6
    assert not any(p['intent'].values()) and p['workflowPrepared']
    assert not any(c['confirmed'] for c in p['characters'])
    assert not any(a['identityConfirmed'] for a in p['annotations'])
    ids={c['id'] for c in p['characters']};sources={s['id']:s for s in p['sources']}
    for a in p['annotations']:
        assert a['characterId'] in ids
        assert 0<=a['x']<a['x']+a['w']<=1.000001
        assert 0<=a['y']<a['y']+a['h']<=1.000001
    for chapter in p['interaction']['chapters']:
        for q in chapter['questions']:
            assert q['personId'] in ids and q['quote'] in sources[q['sourceId']]['text']
            assert q['category']=='fiction'
    issues=narrative.inspect(p,tmp_path)['issues']
    assert not any(i['code'] in ('chapters_mismatch','question_citation','question_copy','question_id','speaker_missing','guide_invalid','guide_missing') for i in issues)
    assert '折槛' not in p['interaction']['presentation']['headline']
    assert '廷争' not in p['interaction']['presentation']['closing']


def test_all_requested_article_links_are_retained_without_claiming_pdf_text():
    for key in SPECS:
        p=build_project(key,'/api/images/art.jpg')
        articles=[s for s in p['sources'] if s.get('articleId')]
        assert {s['articleId'] for s in articles}=={entry[0] for entry in ARTICLES[key]}
        assert all(s['accessStatus']=='pdf_unavailable' and s['method']=='bibliography' for s in articles)
        assert all(not s['confirmed'] for s in articles)


def test_archive_removes_only_selected_project_from_list_and_is_recoverable(client):
    first=client.post('/api/projects').json();second=client.post('/api/projects').json()
    r=client.post('/api/projects/'+first['id']+'/archive',json=dict(version=first['version']))
    assert r.status_code==200 and r.json()['archived']
    assert {p['id'] for p in client.get('/api/projects').json()}=={second['id']}
    assert client.get('/api/projects/'+first['id']).status_code==200
    assert client.post('/api/projects/'+first['id']+'/archive',json=dict(version=first['version'])).status_code==409


def test_zhekan_boxes_cover_existing_names_with_valid_geometry():
    assert len(ZHEKAN_BOXES)==9
    for box in ZHEKAN_BOXES.values():rectangle(box,(1232,828))
    with pytest.raises(ValueError):rectangle((0,0,1500,900),(1232,828))


def test_curated_projects_persist_through_real_app_schema(client):
    p=build_project('chongping','/api/images/art.jpg')
    saved=main.save(p,0,'test_artwork_library')
    loaded=client.get('/api/projects/'+saved['id']).json()
    assert loaded['libraryKey']=='chongping'
    assert loaded['interaction']['presentation']['caption']=='一局会棋 · 层层重屏'
    assert len(loaded['interaction']['chapters'])==3
