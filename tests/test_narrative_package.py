import copy
import io
import json
import zipfile
from PIL import Image
from backend import narrative,video


def ready(client,tmp_path):
    p=client.post('/api/projects').json()
    Image.new('RGB',(300,200),'tan').save(tmp_path/'painting.png')
    p.update(image='/api/images/painting.png',sceneCount=1,characters=[dict(id='guide',name='宫人：德福',identity='宫人',relationships='',evidence='',confirmed=True),dict(id='actor',name='朱云',identity='直谏者',relationships='',evidence='',confirmed=True)],annotations=[dict(id='guide-box',kind='character',identityConfirmed=True,characterId='guide',x=.1,y=.1,w=.2,h=.7,description='宫人'),dict(id='actor-box',kind='character',identityConfirmed=True,characterId='actor',x=.5,y=.1,w=.2,h=.7,description='朱云')],scenes=[dict(id='scene',title='一场',goal='目标',connection='衔接',characterIds=['actor'],units=[dict(id='unit',text='角色抬手。',kind='action',category='fiction',rationale='演绎',references=[],speakerId='actor',status='approved',locked=False)])],interaction=dict(guideAnnotationIds=['guide-box'],chapters=[dict(id='scene',title='第一幕',lead='引路词',outro='收束语',questions=[dict(id='question',personId='actor',question='你为何而来？',answer='我来进谏。',clue='听取来意。')])]))
    p=client.put('/api/projects/'+p['id'],json=p).json()
    # Explicit editorial confirmation after initial creation, not an automatic approval.
    p['outlineConfirmed']=True
    for c in p['characters']:c['confirmed']=True
    p['scenes'][0]['units'][0]['status']='approved'
    return client.put('/api/projects/'+p['id'],json=p).json()


def test_inspect_is_read_only_and_ai_and_video_are_optional(client,tmp_path):
    p=ready(client,tmp_path);path='/api/projects/'+p['id']
    result=client.post(path+'/narrative/inspect',json=p)
    assert result.status_code==200 and result.json()['ready']
    assert {x['code'] for x in result.json()['issues']} >= {'ai_optional','video_optional'}
    assert client.get(path).json()==p
    p['version']-=1
    assert client.post(path+'/narrative/inspect',json=p).status_code==409


def test_formal_package_requires_review_and_includes_portable_assets(client,tmp_path):
    p=ready(client,tmp_path);path='/api/projects/'+p['id']+'/narrative/export'
    assert client.get(path+'?draft=false').status_code==422
    result=client.get(path+'?draft=false&reviewed=true')
    assert result.status_code==200
    with zipfile.ZipFile(io.BytesIO(result.content)) as z:
        names=z.namelist();manifest=json.loads(z.read('manifest.json'))
        assert {'manifest.json','project.json','story.md','README.md','assets/painting/painting.png'}<=set(names)
        assert all(not name.startswith('/') and '..' not in name.split('/') for name in names)
        assert manifest['state']=='approved' and manifest['review']['humanConfirmed']
        assert manifest['interaction']['chapters'][0]['unlock']['requiresQuestionIds']==['question']
        for portrait in manifest['artwork']['portraits']:assert portrait['path'] in names
        assert manifest['media'][0]['kind']=='painting'
        assert not any('events' in name or 'progress' in name for name in names)
    bundle=client.get(path+'?format=json').json()
    assert bundle['schemaVersion']=='2.0' and bundle['state']=='draft'
    assert '我来进谏' in client.get(path+'?format=md').text


def test_missing_question_and_broken_source_block_formal_but_not_draft(client,tmp_path):
    p=ready(client,tmp_path);path='/api/projects/'+p['id']
    p['interaction']['chapters'][0]['questions']=[]
    p=client.put(path,json=p).json()
    assert client.get(path+'/narrative/export?draft=false&reviewed=true').status_code==422
    assert client.get(path+'/narrative/export?draft=true').status_code==200
    p['interaction']['chapters'][0]['questions']=[dict(id='q',personId='actor',question='问题',answer='回答',clue='线索',sourceId='missing',sourceVersion=1,quote='不存在的引文')]
    result=client.post(path+'/narrative/inspect',json=p).json()
    assert any(i['code']=='question_citation' for i in result['issues'])


def test_changed_scene_order_and_missing_portrait_are_rejected(client,tmp_path):
    p=ready(client,tmp_path)
    broken=copy.deepcopy(p);broken['interaction']['chapters'][0]['id']='unknown'
    broken['annotations']=[a for a in broken['annotations'] if a['characterId']!='actor']
    codes={i['code'] for i in narrative.inspect(broken,tmp_path)['issues']}
    assert {'chapters_mismatch','speaker_missing'}<=codes


def test_media_selects_exact_current_scene_and_excludes_tests_and_stale_jobs(client,tmp_path):
    p=ready(client,tmp_path)
    p['storyboards']=[dict(sceneId='scene',shots=[dict(duration=5,framing='全幅',action='动作',characterIds=['actor'])])]
    folder=tmp_path/'videos';folder.mkdir();(folder/'valid.mp4').write_bytes(b'video-fixture')
    valid=dict(id='valid',sceneId='scene',status='succeeded',time='2026',scopeFingerprint=video.scene_fingerprint(p,'scene'))
    assert narrative.inspect(p,tmp_path,[valid])['media'][0]['jobId']=='valid'
    assert narrative.inspect(p,tmp_path,[dict(valid,test=True)])['media'][0]['kind']=='storyboard'
    assert narrative.inspect(p,tmp_path,[dict(valid,scopeFingerprint='stale')])['media'][0]['kind']=='storyboard'
    assert narrative.inspect(p,tmp_path,[dict(valid,sceneId='other')])['media'][0]['kind']=='storyboard'


def test_zip_member_names_cannot_escape_and_local_file_rejects_traversal(client,tmp_path):
    p=ready(client,tmp_path);p['annotations'][1]['id']='../../escape'
    bundle=narrative.package(p,tmp_path,[],True)
    with zipfile.ZipFile(io.BytesIO(narrative.archive(bundle,tmp_path))) as z:
        assert all('..' not in name.split('/') for name in z.namelist())
    assert narrative.local_file(tmp_path,'../outside') is None
    assert narrative.local_file(tmp_path,'C:\\private.png') is None
    assert narrative.local_file(tmp_path,'https://example.com/file') is None


def test_unconfirmed_source_is_one_repair_item_and_blocks_release(client,tmp_path):
    p=ready(client,tmp_path)
    p['sources']=[dict(id='src',title='待核对来源',version=1,text='逐字引文',confirmed=False)]
    q=p['interaction']['chapters'][0]['questions'][0]
    q.update(quote='逐字引文',sourceId='src',sourceVersion=1)
    status=narrative.inspect(p,tmp_path)
    assert sum(i['code']=='source_pending' for i in status['issues'])==1
    assert not any(i['section']=='interaction' for i in status['issues'])
    assert not status['ready']
    assert narrative.package(p,tmp_path,[],True)['state']=='draft'


def test_broken_image_blocks_release_but_draft_zip_remains_exportable(client,tmp_path):
    p=ready(client,tmp_path);(tmp_path/'painting.png').write_bytes(b'not-an-image')
    bundle=narrative.package(p,tmp_path,[],True)
    assert any(i['code']=='painting_missing' for i in bundle['readiness']['issues'])
    with zipfile.ZipFile(io.BytesIO(narrative.archive(bundle,tmp_path))) as z:
        assert 'manifest.json' in z.namelist()
        assert not any(name.startswith('assets/painting/') for name in z.namelist())


def test_source_confirmation_is_explicit_versioned_and_keeps_quote_versions(client,tmp_path):
    p=ready(client,tmp_path);path='/api/projects/'+p['id']
    p['sources']=[dict(id='src',title='资料',version=1,text='引文',confirmed=False)]
    p=client.put(path,json=p).json();source_version=p['sources'][0]['version']
    r=client.post(path+'/sources/src/confirm',json=dict(version=p['version']))
    assert r.status_code==200
    saved=r.json();assert saved['sources'][0]['confirmed']
    assert saved['sources'][0]['version']==source_version
    assert saved['version']==p['version']+1
    assert client.post(path+'/sources/src/confirm',json=dict(version=p['version'])).status_code==409
