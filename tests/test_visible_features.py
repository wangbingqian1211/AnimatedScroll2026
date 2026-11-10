import asyncio
import copy
import pytest
from backend import vision, task_runtime


def project():
    return dict(annotations=[dict(id='named',kind='character',characterId='zhang',description='侧立',confirmed=False),dict(id='unnamed',kind='character',characterId='',description='',confirmed=True),dict(id='done',kind='character',characterId='',description='黄色衣袍',confirmed=True)],observations=[dict(id='old',annotationId='done',description='黄色衣袍',confirmed=True)])


def test_missing_appearance_is_independent_of_identity_and_confirmation():
    p=project()
    assert [a['id'] for a in vision.missing_observations(p)]==['named','unnamed']


def test_only_missing_people_are_analyzed_without_changing_identity(monkeypatch):
    p=project();before=copy.deepcopy(p);calls=[]
    async def analyze(path,annotations,progress):
        calls.append([a['id'] for a in annotations])
        return dict(overview={},observations=[dict(id='obs-'+a['id'],annotationId=a['id'],description='深色长袍，双手交叠于身前，站立于座椅右侧。',confirmed=False) for a in annotations])
    monkeypatch.setattr(vision,'analyze',analyze)
    assert asyncio.run(vision.complete_observations('image',p))==2
    assert calls==[['named','unnamed']]
    assert all(a['description'] for a in p['annotations'])
    assert p['observations'][0]==before['observations'][0]
    assert [a['characterId'] for a in p['annotations']]==[a['characterId'] for a in before['annotations']]
    assert asyncio.run(vision.complete_observations('image',p))==0


def test_visual_analysis_rejects_empty_description(tmp_path,monkeypatch):
    from PIL import Image
    path=tmp_path/'image.png';Image.new('RGB',(50,50)).save(path)
    responses=iter([{'summary':'全图'},{'description':'  '}])
    async def ask(*args):return next(responses)
    monkeypatch.setattr(vision,'ask',ask)
    with pytest.raises(ValueError,match='不能为空'):
        asyncio.run(vision.analyze(path,[dict(id='a',kind='character',x=0,y=0,w=1,h=1)]))


def test_identity_matching_contract_includes_appearance_updates():
    p=project()
    _,write=task_runtime.analysis_paths(p,'match',{})
    assert '/observations' in write
    assert '/annotations/@unnamed/description' in write
