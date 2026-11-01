import copy
import json
import time
import pytest
from PIL import Image
from backend import main,workflow,video


def ready(client,tmp_path):
    p=client.post('/api/projects').json();Image.new('RGB',(500,250),'tan').save(tmp_path/'painting.png')
    p.update(image='/api/images/painting.png',sceneCount=1,characters=[dict(id='c',name='人物甲',identity='身份',relationships='',knowledge='',evidence='')],scenes=[dict(id='s',title='一场',goal='微动作',connection='',characterIds=['c'],units=[dict(id='u',text='衣袖轻动',kind='action',category='fiction',rationale='动画演绎',references=[],status='pending',locked=False)])])
    p=client.put('/api/projects/'+p['id'],json=p).json()
    p['storyboards']=[dict(sceneId='s',shots=[dict(duration=5,framing='全幅',action='衣袖轻动')],prompt='保持古画全幅，微动作')]
    p['storyboardFingerprint']=video.script_fingerprint(p)
    p=client.put('/api/projects/'+p['id'],json=p).json()
    preview=client.get('/api/projects/'+p['id']+'/scenes/s/video-prompt').json()
    return client.post('/api/projects/'+p['id']+'/scenes/s/video-prompt',json=dict(version=p['version'],text=preview['prompt'],baseFingerprint=preview['baseFingerprint'])).json()


def test_drafts_only_fill_blanks_and_never_mark_human_approval(client,tmp_path,monkeypatch):
    p=ready(client,tmp_path);path='/api/projects/'+p['id']
    async def draft(*args):return dict(characters=[dict(id='c',identity='不应覆盖',knowledge='资料未提供，待核对',biography='资料未提供',summary='人物简介')],intent=dict(theme='忠谏'))
    monkeypatch.setattr(workflow,'draft',draft)
    r=client.post(path+'/workflow/draft',json=dict(version=p['version'],stage='prepare'))
    assert r.status_code==200
    saved=r.json();assert saved['characters'][0]['identity']=='身份' and saved['characters'][0]['knowledge']
    assert not saved['characters'][0]['confirmed'] and not saved.get('scriptApproval')


def test_bad_scene_count_never_overwrites_existing_outline(client,tmp_path,monkeypatch):
    p=ready(client,tmp_path);path='/api/projects/'+p['id']
    async def draft(*args):return dict(scenes=[])
    monkeypatch.setattr(workflow,'draft',draft)
    assert client.post(path+'/workflow/draft',json=dict(version=p['version'],stage='outline',regenerate=True)).status_code==502
    assert client.get(path).json()==p


def test_video_requires_explicit_confirmation_and_changes_invalidate(client,tmp_path):
    p=ready(client,tmp_path);path='/api/projects/'+p['id'];req=dict(version=p['version'],sceneId='s')
    assert client.post(path+'/videos',json=req).status_code==422
    p=client.post(path+'/script/confirm',json=dict(version=p['version'])).json()
    assert client.get(path+'/videos').json()['scriptConfirmed']
    p['scenes'][0]['units'][0]['text']='用户修改后的剧本'
    p=client.put(path,json=p).json()
    assert not client.get(path+'/videos').json()['scriptConfirmed']
    assert client.post(path+'/videos',json=dict(version=p['version'],sceneId='s')).status_code==422


def test_full_painting_is_passed_as_first_frame_and_five_seconds(tmp_path):
    path=tmp_path/'painting.png';Image.new('RGB',(1000,500)).save(path)
    body=video.payload(dict(prompt='原剧本'),path)
    assert body['model']=='wan3.0-video'
    assert body['input']['media'][0]['type']=='first_frame'
    assert body['input']['media'][0]['url'].startswith('data:image/png;base64,')
    assert body['input']['media'][1]['type']=='last_frame'
    assert body['input']['media'][0]['url']==body['input']['media'][1]['url']
    assert body['parameters']['duration']==5 and body['parameters']['resolution']=='480P'


def test_old_submission_records_do_not_limit_further_generation(tmp_path):
    for index in range(6):video.reserve(tmp_path,str(index))
    for index in range(6,20):video.reserve(tmp_path,str(index))
    assert video.remaining(tmp_path) is None and video.LIMIT is None
    assert len(list((tmp_path/'video-budget').glob('*.ticket')))==20
    video.reserve(tmp_path,'19')
    assert len(list((tmp_path/'video-budget').glob('*.ticket')))==20


def test_duplicate_submission_reuses_job_and_quota(client,tmp_path,monkeypatch):
    p=ready(client,tmp_path);path='/api/projects/'+p['id'];calls=[]
    p=client.post(path+'/scenes/s/confirm-video',json=dict(version=p['version'])).json()
    monkeypatch.setenv('DASHSCOPE_API_KEY','fake-test-key')
    class Response:
        def raise_for_status(self):pass
        def json(self):return dict(output=dict(task_id='remote-1',task_status='FAILED',code='TestStop'))
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,*args,**kwargs):calls.append(kwargs['json']);return Response()
        async def get(self,*args,**kwargs):return Response()
    monkeypatch.setattr(video.httpx,'AsyncClient',Client)
    req=dict(version=p['version'],sceneId='s',test=True)
    first=client.post(path+'/videos',json=req);second=client.post(path+'/videos',json=req)
    assert first.status_code==200 and second.json()['id']==first.json()['id']
    assert len(calls)==1 and len(list((tmp_path/'video-budget').glob('*.ticket')))==1
    assert first.json()['test'] and not client.get(path+'/videos').json()['scriptConfirmed']


def test_editing_storyboard_invalidates_confirmation(client,tmp_path):
    p=ready(client,tmp_path);path='/api/projects/'+p['id']
    p=client.post(path+'/script/confirm',json=dict(version=p['version'])).json()
    p['storyboards'][0]['prompt']='新的动作描述';client.put(path,json=p)
    assert not client.get(path+'/videos').json()['scriptConfirmed']


def test_storyboard_has_editable_camera_action_and_typed_dialogue(client,tmp_path):
    p=ready(client,tmp_path)
    rows=copy.deepcopy(p['storyboards'])
    rows[0]['shots'][0].update(camera='固定全幅镜头',characterIds=['c'],dialogue=[dict(speakerId='c',text='请听臣一言',category='fiction')])
    parsed=workflow.validate_boards(rows,p)
    assert parsed[0]['shots'][0]['camera']=='固定全幅镜头'
    assert parsed[0]['shots'][0]['dialogue'][0]['category']=='fiction'
    rows[0]['shots'][0]['dialogue'][0]['category']='supported'
    with pytest.raises(ValueError,match='逐字'):workflow.validate_boards(rows,p)
    rows[0]['shots'][0]['dialogue']=[];rows[0]['shots'][0]['duration']=4
    with pytest.raises(ValueError,match='5秒'):workflow.validate_boards(rows,p)


def test_script_draft_allows_pending_sources_but_does_not_confirm_them(client,tmp_path,monkeypatch):
    p=ready(client,tmp_path);path='/api/projects/'+p['id']
    p['sources']=[dict(id='source',title='输入材料',text='朱云折槛',version=1,confirmed=False)]
    p['scenes'][0]['units']=[];p=client.put(path,json=p).json()
    async def draft(*args):return dict(scenes=[dict(sceneId='s',units=[dict(text='朱云折槛',kind='event',category='supported',rationale='',references=[dict(sourceId='source',sourceVersion=1,quote='朱云折槛')])])])
    monkeypatch.setattr(workflow,'draft',draft)
    r=client.post(path+'/workflow/draft',json=dict(version=p['version'],stage='scripts'))
    assert r.status_code==200
    assert r.json()['sources'][0]['confirmed'] is False
    assert r.json()['scenes'][0]['units'][0]['status']=='pending'


def test_video_query_does_not_send_submission_only_async_header(monkeypatch):
    monkeypatch.setenv('DASHSCOPE_API_KEY','fake-test-key')
    assert 'X-DashScope-Async' not in video.headers()
    assert video.headers(async_mode=True)['X-DashScope-Async']=='enable'


def test_generated_untraceable_dialogue_is_fiction_not_historical_quote(client,tmp_path):
    p=ready(client,tmp_path);rows=copy.deepcopy(p['storyboards'])
    rows[0].pop('prompt')
    rows[0]['shots'][0]['dialogue']=[dict(speakerId='c',text='请听臣一言',category='supported',sourceId='missing',quote='编造引文')]
    parsed=workflow.generated_boards(rows,p)
    assert parsed[0]['prompt']
    assert parsed[0]['shots'][0]['dialogue'][0]['category']=='fiction'


def test_video_prompt_compiles_named_dialogue_and_cinematic_composition(client,tmp_path):
    p=ready(client,tmp_path);board=p['storyboards'][0]
    p['annotations']=[dict(characterId='c',x=.1,y=.2,w=.2,h=.5)]
    board['shots'][0].update(characterIds=['c'],dialogue=[dict(speakerId='c',text='请听臣言',category='fiction')])
    prompt=video.video_prompt(p,p['scenes'][0],board)
    assert '人物甲说：“请听臣言”' in prompt
    assert '允许中景、近景、特写、切镜' in prompt and '不要求回到原画布局' in prompt
    assert '禁止切镜和特写' not in prompt


def test_model_dialogue_backed_only_by_background_becomes_editable_fiction(client,tmp_path,monkeypatch):
    p=ready(client,tmp_path);path='/api/projects/'+p['id']
    p['sources']=[dict(id='source',title='人物背景',text='人物甲是忠臣。',version=1,confirmed=True)]
    p['scenes'][0]['units']=[];p=client.put(path,json=p).json()
    async def draft(*args):return dict(scenes=[dict(sceneId='s',units=[dict(text='臣愿直言！',kind='dialogue',speakerId='c',category='supported',rationale='',references=[dict(sourceId='source',sourceVersion=1,quote='人物甲是忠臣。')])])])
    monkeypatch.setattr(workflow,'draft',draft)
    r=client.post(path+'/workflow/draft',json=dict(version=p['version'],stage='scripts'))
    assert r.status_code==200
    line=r.json()['scenes'][0]['units'][0]
    assert line['text']=='臣愿直言！' and line['category']=='fiction' and line['status']=='pending'
    assert '不能当作历史原话' in line['rationale']


def test_exact_historical_dialogue_is_retained_and_bad_model_reference_is_removed():
    p=dict(sources=[dict(id='s',text='其言非，固当容之。',version=2)])
    line=dict(kind='dialogue',category='supported',text='固当容之。',references=[dict(sourceId='s',sourceVersion=2,quote='其言非，固当容之。')])
    assert workflow.generated_unit(line,p)==line
    line['references'][0]['sourceVersion']=1
    normalized=workflow.generated_unit(line,p)
    assert normalized['category']=='fiction' and normalized['references']==[]
    assert line['category']=='supported'  # No mutation of user or input records.


def test_model_inference_without_references_is_saved_as_unverified_creation():
    line=dict(kind='action',category='inference',text='他握紧了衣袖。',references=[],rationale='推测')
    parsed=workflow.generated_unit(line,dict(sources=[],annotations=[]))
    assert parsed['text']==line['text'] and parsed['category']=='fiction'
    assert '缺少有效依据' in parsed['rationale']


def test_scene_approval_works_with_other_scenes_unfinished(client,tmp_path):
    p=ready(client,tmp_path);path='/api/projects/'+p['id']
    p['sceneCount']=2;p['scenes'].append(dict(id='unfinished',title='未完成',goal='',connection='',characterIds=[],units=[]))
    p=client.put(path,json=p).json()
    r=client.post(path+'/scenes/s/confirm-video',json=dict(version=p['version']))
    assert r.status_code==200
    approved=r.json();assert 's' in approved['sceneVideoApprovals'] and not approved.get('scriptApproval')
    assert client.post(path+'/scenes/unfinished/confirm-video',json=dict(version=approved['version'])).status_code==422
    baseline=video.scene_fingerprint(approved,'s')
    changed=copy.deepcopy(approved);changed['scenes'][1]['title']='只改另一场'
    assert video.scene_fingerprint(changed,'s')==baseline
    changed['storyboards'][0]['shots'][0]['action']='修改本场动作'
    assert video.scene_fingerprint(changed,'s')!=baseline


def test_only_confirmed_scene_is_submitted_once(client,tmp_path,monkeypatch):
    p=ready(client,tmp_path);path='/api/projects/'+p['id']
    p['sceneCount']=2;p['scenes'].append(dict(id='other',title='另一场',goal='',connection='',characterIds=[],units=[]));p=client.put(path,json=p).json()
    p=client.post(path+'/scenes/s/confirm-video',json=dict(version=p['version'])).json()
    monkeypatch.setenv('DASHSCOPE_API_KEY','fake-test-key');calls=[]
    class Response:
        def raise_for_status(self):pass
        def json(self):return {'output':{'task_id':'fake-id','task_status':'FAILED'}}
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,*args,**kwargs):calls.append(kwargs['json']);return Response()
        async def get(self,*args,**kwargs):return Response()
    monkeypatch.setattr(video.httpx,'AsyncClient',Client)
    req=dict(version=p['version'],sceneId='s')
    first=client.post(path+'/videos',json=req);assert first.status_code==200
    second=client.post(path+'/videos',json=req);assert second.json()['id']==first.json()['id']
    assert len(calls)==1 and len(list((tmp_path/'video-budget').glob('*.ticket')))==1
    p['storyboards'][0]['shots'][0]['action']='本场已改'
    p=client.put(path,json=p).json()
    assert client.post(path+'/videos',json=dict(version=p['version'],sceneId='s')).status_code==422


def test_video_prompt_keeps_user_storyboard_and_forbids_duplicate_figures():
    p=dict(characters=[dict(id='c',name='朱云'),dict(id='extra',name='未定位的官员')],annotations=[dict(characterId='c',x=.1,y=.2,w=.2,h=.5)])
    scene=dict(title='廷前争辩')
    board=dict(sceneId='one',prompt='用户自己的描述，不得改写',shots=[dict(duration=5,characterIds=['c','extra'],action='朱云被侍卫拖拽，奋力挣扎',dialogue=[dict(speakerId='c',text='陛下明鉴！'),dict(speakerId='extra',text='遵旨。')],sound='衣料摩擦声')])
    original=copy.deepcopy((p,scene,board))
    prompt=video.video_prompt(p,scene,board)
    assert (p,scene,board)==original
    assert '朱云被侍卫拖拽，奋力挣扎' in prompt and '陛下明鉴！' in prompt
    assert '不把静止的原画人物留作背景又叠加会动的同一人物分身' in prompt
    assert '未定位的官员以画外声音说' in prompt
    assert '出场人物：朱云。' in prompt
    assert board['prompt'] in prompt
    assert '不要求与前后视频在机位、人物站位或首尾构图上连续' in prompt
