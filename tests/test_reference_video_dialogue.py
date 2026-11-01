import base64,io,json
from PIL import Image,ImageDraw
from backend import video,narrative,main
from test_draft_video import ready


def test_reference_mode_sends_painting_and_correct_character_crop_without_first_frame(client,tmp_path):
    p=ready(client,tmp_path);p['annotations']=[dict(id='box',kind='character',characterId='c',x=0,y=0,w=.2,h=.8)]
    scene=p['scenes'][0];board=p['storyboards'][0]
    plan=video.reference_plan(p,scene,board)
    assert [r['kind'] for r in plan]==['painting','character']
    assert plan[1]['name']=='人物甲' and plan[1]['label']=='图2'
    im=Image.new('RGB',(1000,500),'red');ImageDraw.Draw(im).rectangle((0,0,199,399),fill='blue');im.save(tmp_path/'painting.png')
    job=dict(prompt='图2的人物出场',promptPolicyVersion=video.PROMPT_POLICY_VERSION,referencePlan=plan,requestConfig=dict(model=video.VIDEO_MODEL,parameters=dict(video.VIDEO_PARAMETERS),mediaMode=video.MEDIA_MODE))
    payload=video.payload(job,tmp_path/'painting.png')
    assert [m['type'] for m in payload['input']['media']]==['reference_image','reference_image']
    crop=Image.open(io.BytesIO(base64.b64decode(payload['input']['media'][1]['url'].split(',')[1])))
    assert min(crop.size)>=240 and crop.getpixel((crop.width//2,crop.height//2))==(0,0,255)
    prompt=video.video_prompt(p,scene,board)
    assert '图2＝人物甲' in prompt and '不是首帧或尾帧' in prompt
    moved=video.reference_plan(dict(p,annotations=[dict(p['annotations'][0],x=.5)]),scene,board)
    assert video.request_fingerprint(prompt,plan)!=video.request_fingerprint(prompt,moved)


def test_user_selected_scene_video_survives_script_edits_and_is_exported(client,tmp_path):
    p=ready(client,tmp_path);path='/api/projects/'+p['id'];sid=p['scenes'][0]['id']
    job=dict(id='selected-job',projectId=p['id'],sceneId=sid,title='旧标题',status='succeeded',test=False,time='2026-10-30',scopeFingerprint='old-scope',scriptFingerprint='',videoUrl=path+'/videos/selected-job/file')
    (tmp_path/'videos').mkdir();(tmp_path/'videos/selected-job.mp4').write_bytes(b'fake-video-for-selection-test')
    with main.db() as conn:conn.execute('INSERT INTO video_jobs VALUES (?,?,?)',(job['id'],p['id'],json.dumps(job)))
    endpoint=path+'/scenes/'+sid+'/dialogue-video'
    selected=client.post(endpoint,json=dict(version=p['version'],jobId=job['id']))
    assert selected.status_code==200,selected.text
    p=selected.json();p['scenes'][0]['title']='现在的第一幕';p=client.put(path,json=p).json()
    jobs=client.get(path+'/videos').json()['jobs']
    assert jobs[0]['selectedForDialogue'] and not jobs[0]['matchesCurrentScript']
    media=narrative.inspect(p,tmp_path,[job])['media'][0]
    assert media['kind']=='video' and media['jobId']==job['id']
    assert client.post(path+'/scenes/wrong-scene/dialogue-video',json=dict(version=p['version'],jobId=job['id'])).status_code==422


def test_reference_assets_are_capped_at_provider_limit_and_prioritize_speakers():
    p=dict(characters=[dict(id=str(i),name='人物'+str(i)) for i in range(12)],annotations=[dict(id=str(i),kind='character',characterId=str(i),x=0,y=0,w=.2,h=.4) for i in range(12)])
    plan=video.reference_plan(p,dict(characterIds=[str(i) for i in range(12)]),dict(shots=[dict(dialogue=[dict(speakerId='11',text='请听我说')],characterIds=[str(i) for i in range(12)])]))
    assert len(plan)==10 and plan[1]['characterId']=='11'
