import asyncio
import json
from types import SimpleNamespace

from PIL import Image
from backend import vision, config


def test_matching_uses_one_compact_request_and_preserves_confirmed(tmp_path,monkeypatch):
    path=tmp_path/'painting.png';Image.new('RGB',(2400,1600)).save(path)
    p=dict(annotations=[dict(id='saved',kind='character',identityConfirmed=True,characterId='c',x=0,y=0,w=.2,h=.5),dict(id='new',kind='character',x=.3,y=0,w=.2,h=.5),dict(id='scene',kind='scene',x=0,y=0,w=1,h=1)],characters=[dict(id='c',name='朱云',identity='谏臣',mentions=[{'text':'duplicate'*10000}])],sources=[dict(title='史料',text=('朱云折槛\n'*10000))],observations=[],matches=[dict(id='manual',annotationId='saved',characterId='c',confirmed=True)])
    calls=[]
    async def ask(prompt,images,**options):
        payload=json.loads(prompt);calls.append(payload)
        assert len(prompt)<10000 and len(payload['annotations'])==2
        assert 'mentions' not in payload['characters'][0]
        assert max(images[0].size)<=1280 and options['fast']
        assert options['max_tokens']<4500
        assert payload['annotations'][0]['knownCharacterId']=='c'
        return {'matches':[dict(annotationId='new',characterId='c',reason='动作相符，待确认'),dict(annotationId='saved',characterId='',reason='应忽略') ]}
    monkeypatch.setattr(vision,'ask',ask)
    result=asyncio.run(vision.match_people(path,p))
    assert len(calls)==1 and len(result)==2
    assert result[0]==p['matches'][0] and not result[1]['confirmed']


def test_confirmed_people_need_no_network(monkeypatch):
    async def forbidden(*args,**kwargs):raise AssertionError('already confirmed')
    monkeypatch.setattr(vision,'ask',forbidden)
    p=dict(annotations=[dict(id='a',kind='character',identityConfirmed=True)],matches=[dict(annotationId='a',characterId='c',confirmed=True)])
    assert asyncio.run(vision.match_people('unused.png',p))==p['matches']


def test_fast_dashscope_disables_thinking_without_affecting_other_calls(monkeypatch):
    calls=[]
    monkeypatch.setattr(config,'model_settings',lambda *args:config.ModelSettings('dashscope','fake','https://example.test','deepseek-v4.1-flash'))
    class Client:
        def __init__(self,**kwargs):self.chat=SimpleNamespace(completions=self)
        async def create(self,**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{}'))])
        async def close(self):pass
    monkeypatch.setattr(vision,'AsyncOpenAI',Client)
    asyncio.run(vision.ask('match',[],fast=True,max_tokens=800))
    asyncio.run(vision.ask('ocr',[]))
    assert calls[0]['extra_body']=={'enable_thinking':False}
    assert calls[0]['max_tokens']==800
    assert 'extra_body' not in calls[1] and calls[1]['max_tokens']==4500
