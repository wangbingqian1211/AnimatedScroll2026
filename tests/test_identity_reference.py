import asyncio
import hashlib
from PIL import Image
from backend import vision


def painting(tmp_path):
    path=tmp_path/'painting.png';Image.new('RGB',(400,200)).save(path)
    boxes=[dict(id='left',kind='character',x=.1,y=.2,w=.15,h=.5,characterId='zhu'),dict(id='right',kind='character',x=.7,y=.2,w=.15,h=.5,characterId='emperor')]
    return path,dict(annotations=boxes,characters=[dict(id='zhu',name='朱云'),dict(id='emperor',name='汉成帝')],matches=[],identityReference=dict(imageSha256=hashlib.sha256(path.read_bytes()).hexdigest(),annotations=[dict(a) for a in boxes]))


def test_same_image_repeated_matching_follows_creator_reference(tmp_path,monkeypatch):
    path,p=painting(tmp_path)
    p['annotations'][0]['characterId']='emperor'  # Previous model mistake.
    async def forbidden(*args,**kwargs):raise AssertionError('reference needs no model guess')
    monkeypatch.setattr(vision,'ask',forbidden)
    for _ in range(2):
        matches=asyncio.run(vision.match_people(path,p))
        assert [(m['annotationId'],m['characterId']) for m in matches]==[('left','zhu'),('right','emperor')]
        assert all(m['origin']=='creator_reference' and not m['confirmed'] for m in matches)


def test_reference_respects_manual_correction_and_leaves_unmatched_unknown(tmp_path):
    path,p=painting(tmp_path)
    p['annotations'][0].update(characterId='emperor',identityConfirmed=True)
    p['annotations'].append(dict(id='new',kind='character',x=.4,y=.1,w=.1,h=.4))
    result=vision.reference_matches(path,p)
    assert result[0]['characterId']=='emperor' and result[0]['confirmed']
    assert result[-1]['characterId']==''


def test_reference_invalid_for_another_image_and_one_to_one_for_duplicates(tmp_path):
    path,p=painting(tmp_path)
    p['annotations'].append(dict(p['annotations'][0],id='duplicate'))
    assert sum(m['characterId']=='zhu' for m in vision.reference_matches(path,p))==1
    Image.new('RGB',(400,200),'white').save(path)
    assert vision.reference_matches(path,p) is None
