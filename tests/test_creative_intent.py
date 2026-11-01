from backend import workflow


def test_title_generation_is_unsaved_and_sends_only_title(client,monkeypatch):
    p=client.post('/api/projects').json()
    p['intent']['goal']='用户原有的私密设想'
    p['sources']=[dict(id='private',title='私人资料',text='不发送的资料全文',version=1)]
    p=client.put('/api/projects/'+p['id'],json=p).json()
    prompts=[]
    async def ask(prompt,images,**kwargs):
        prompts.append(prompt)
        return {key:'模型草稿：'+key for key in p['intent']}
    monkeypatch.setattr(workflow.vision,'ask',ask)
    path='/api/projects/'+p['id']
    result=client.post(path+'/intent/draft',json=dict(version=p['version'],title='直言与回响'))
    assert result.status_code==200
    assert result.json()['intent']['theme']=='模型草稿：theme'
    assert not result.json()['humanApproved']
    assert '直言与回响' in prompts[0]
    assert '用户原有的私密设想' not in prompts[0] and '不发送的资料全文' not in prompts[0]
    assert client.get(path).json()==p


def test_intent_failure_and_invalid_output_preserve_inputs(client,monkeypatch):
    p=client.post('/api/projects').json();path='/api/projects/'+p['id']
    async def invalid(*args,**kwargs):return dict(theme='仅有主题')
    monkeypatch.setattr(workflow.vision,'ask',invalid)
    assert client.post(path+'/intent/draft',json=dict(version=p['version'],title='标题')).status_code==502
    assert client.get(path).json()==p
    async def failed(*args,**kwargs):raise RuntimeError('model failure')
    monkeypatch.setattr(workflow.vision,'ask',failed)
    assert client.post(path+'/intent/draft',json=dict(version=p['version'],title='标题')).status_code==502
    assert client.get(path).json()==p


def test_intent_rejects_stale_results_and_blank_titles(client,monkeypatch):
    p=client.post('/api/projects').json();path='/api/projects/'+p['id']
    assert client.post(path+'/intent/draft',json=dict(version=p['version'],title='  ')).status_code==422
    async def concurrent(*args,**kwargs):
        changed=client.get(path).json();changed['title']='新版本'
        assert client.put(path,json=changed).status_code==200
        return {key:'草稿' for key in p['intent']}
    monkeypatch.setattr(workflow.vision,'ask',concurrent)
    assert client.post(path+'/intent/draft',json=dict(version=p['version'],title='标题')).status_code==409
    assert client.get(path).json()['title']=='新版本'


def test_profile_preparation_does_not_fill_creative_intent(client,monkeypatch):
    p=client.post('/api/projects').json();path='/api/projects/'+p['id']
    async def draft(*args):return dict(characters=[],intent={key:'不应写入' for key in p['intent']})
    monkeypatch.setattr(workflow,'draft',draft)
    result=client.post(path+'/workflow/draft',json=dict(version=p['version'],stage='prepare'))
    assert result.status_code==200
    assert result.json()['intent']==p['intent']
