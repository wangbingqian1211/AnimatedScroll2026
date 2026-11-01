import copy
from PIL import Image
from backend import video
from test_draft_video import ready


def test_every_editable_storyboard_field_affects_compiled_prompt(client,tmp_path):
    p=ready(client,tmp_path);s=p['scenes'][0];b=p['storyboards'][0]
    original=video.video_prompt(p,s,b)
    for key in ('prompt','framing','camera','narration','action','sound'):
        changed=copy.deepcopy(b)
        if key=='prompt':changed[key]='独特补充要求'
        else:changed['shots'][0][key]='独特镜头要求'
        assert video.video_prompt(p,s,changed)!=original,key
    assert '人物面貌' not in original or '画风' in original
    assert '双脚固定' not in original


def test_prompt_preview_save_and_review_never_reserve_video_quota(client,tmp_path):
    p=ready(client,tmp_path);path='/api/projects/'+p['id'];url=path+'/scenes/s/video-prompt'
    before=video.remaining(tmp_path)
    preview=client.get(url).json()
    assert preview['customized'] and not preview['stale']
    text='保持古画画风与人物，朱云近景抬手。\n不要增加字幕。'
    saved=client.post(url,json=dict(version=p['version'],text=text,baseFingerprint=preview['baseFingerprint']))
    assert saved.status_code==200,saved.text
    p=saved.json()
    assert client.get(url).json()['prompt']==text
    p=client.post(path+'/scenes/s/confirm-video',json=dict(version=p['version'])).json()
    assert p['sceneVideoApprovals']['s']['promptFingerprint']==video.scene_request_fingerprint(p,p['scenes'][0],p['storyboards'][0],text)
    assert video.remaining(tmp_path)==before
    assert not (tmp_path/'video-budget').exists()


def test_stale_prompt_or_unreviewed_prompt_cannot_generate_even_in_test_mode(client,tmp_path):
    p=ready(client,tmp_path);path='/api/projects/'+p['id'];url=path+'/scenes/s/video-prompt'
    p=client.post(path+'/scenes/s/confirm-video',json=dict(version=p['version'])).json()
    preview=client.get(url).json()
    p['storyboards'][0]['shots'][0]['camera']='缓慢推近至面部特写'
    p=client.put(path,json=p).json()
    assert client.get(url).json()['stale']
    assert client.post(path+'/scenes/s/confirm-video',json=dict(version=p['version'])).status_code==422
    assert client.post(path+'/videos',json=dict(version=p['version'],sceneId='s',test=True)).status_code==422
    assert client.post(url,json=dict(version=p['version'],text='旧版修改',baseFingerprint=preview['baseFingerprint'])).status_code==409
    p['sceneVideoPrompts']={};p=client.put(path,json=p).json()
    assert client.post(path+'/scenes/s/confirm-video',json=dict(version=p['version'])).status_code==422
    assert not (tmp_path/'video-budget').exists()


def test_actual_model_receives_reviewed_text_verbatim_and_only_reference_images(client,tmp_path,monkeypatch):
    p=ready(client,tmp_path);path='/api/projects/'+p['id'];url=path+'/scenes/s/video-prompt'
    preview=client.get(url).json();text='保持古画画风，人物甲面部特写。\n允许切镜。'
    p=client.post(url,json=dict(version=p['version'],text=text,baseFingerprint=preview['baseFingerprint'])).json()
    p=client.post(path+'/scenes/s/confirm-video',json=dict(version=p['version'])).json()
    calls=[];monkeypatch.setenv('DASHSCOPE_API_KEY','unit-test-key')
    class Response:
        def raise_for_status(self):pass
        def json(self):return dict(output=dict(task_id='fake-id',task_status='FAILED'))
    class Client:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,*args,**kwargs):calls.append(kwargs['json']);return Response()
        async def get(self,*args,**kwargs):return Response()
    monkeypatch.setattr(video.httpx,'AsyncClient',Client)
    r=client.post(path+'/videos',json=dict(version=p['version'],sceneId='s'))
    assert r.status_code==200,r.text
    assert calls[0]['input']['prompt']==text
    assert [m['type'] for m in calls[0]['input']['media']]==['reference_image']
    job=r.json()
    assert job['requestFingerprint']==video.request_fingerprint(text,job['referencePlan'])
    assert video.payload(job,tmp_path/'painting.png')==calls[0]
    # Saving an edited final prompt revokes the previous approval.
    p=client.post(url,json=dict(version=p['version'],text=text+'不说话。',baseFingerprint=preview['baseFingerprint'])).json()
    assert client.post(path+'/videos',json=dict(version=p['version'],sceneId='s')).status_code==422
    assert len(calls)==1


def test_request_parameters_change_invalidates_prompt_and_request_fingerprint(client,tmp_path,monkeypatch):
    p=ready(client,tmp_path);s=p['scenes'][0];b=p['storyboards'][0]
    old=video.prompt_preview(p,s,b)
    monkeypatch.setitem(video.VIDEO_PARAMETERS,'seed',12345)
    new=video.prompt_preview(p,s,b)
    assert new['stale'] and new['requestFingerprint']!=old['requestFingerprint']


def test_empty_dialogue_rows_are_silent_but_real_lines_stay_validated(client,tmp_path):
    from backend import workflow
    p=ready(client,tmp_path);boards=copy.deepcopy(p['storyboards']);shot=boards[0]['shots'][0]
    shot['dialogue']=[dict(speakerId='',text=''),dict(speakerId='missing',text='   '),dict(speakerId='c',text='请赐尚方剑',category='fiction')]
    validated=workflow.validate_boards(boards,p)
    assert len(validated[0]['shots'][0]['dialogue'])==1
    assert len(shot['dialogue'])==3  # Do not mutate the saved draft.
    prompt=video.video_prompt(p,p['scenes'][0],boards[0])
    assert '请赐尚方剑' in prompt and '：“”' not in prompt
    shot['dialogue']=shot['dialogue'][:2]
    assert workflow.validate_boards(boards,p)[0]['shots'][0]['dialogue']==[]
    assert '无人物对白' in video.video_prompt(p,p['scenes'][0],boards[0])
    shot['dialogue']=[dict(speakerId='missing',text='有效台词')]
    import pytest
    with pytest.raises(ValueError,match='人物无效'):workflow.validate_boards(boards,p)
