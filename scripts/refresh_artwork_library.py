"""Idempotent, backed-up refresh of the three user-requested local artworks."""
import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image
from backend import main
from backend.models import Project
from backend.domain import reconcile,uid
from backend.artwork_library import build_project,rectangle,ZHEKAN_BOXES,REVISION

KEEP='08f73b736ebc'
ARCHIVE=('2eebe628a14c','f417cabb0972')
ASSETS=Path(__file__).resolve().parents[1]/'examples'/'assets'
FILES={'zhekan':'宋人折槛图_部分.jpg','chongping':'重屏会棋图.jpg','bunian':'步辇图.jpg'}
DESCRIPTIONS={
 '汉成帝':'右侧坐椅上的宽袍须髯者，身后有两位侍立人物。',
 '宫人：德福':'右侧坐者左侧偏后站立的人物，身体略向坐者侧倾。',
 '辛弃疾':'下方中央身体前倾的人物，着深色长衣、戴帽，朝向右上方人物群。',
 '张禹':'右侧最外站立人物，着深色外衣，有长须，袖前持物。',
 '朱云':'左侧偏后着深色长衣、浅色衣领的人物，手臂伸向栏边。',
 '宫女：春桃':'右侧坐者身后偏左的侍立人物，头部高于坐者。',
 '宫女：春萍':'右侧坐者身后偏右的侍立人物，身前可见红色衣物。',
 '侍卫乙':'左侧前方戴帽、着彩色甲衣的人物，身体略向右转。',
 '侍卫甲':'左侧甲衣人物后方露出的戴盔头部；身体大部被遮挡。',
}


def run(apply=False):
    active=main.projects();current=main.get(KEEP)
    plan=dict(keep=KEEP,archive=[r['id'] for r in active if r['id'] in ARCHIVE],assets={k:str(ASSETS/v) for k,v in FILES.items()})
    for filename in FILES.values():
        with Image.open(ASSETS/filename) as im:im.verify()
    if not apply:return dict(dryRun=True,plan=plan)
    backup=main.DATA/'backups'/('artwork-library-20261030-'+uid());backup.mkdir(parents=True)
    def snapshot(p):
        (backup/(p['id']+'.json')).write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')
    def image(key):
        path=ASSETS/FILES[key];sha=hashlib.sha256(path.read_bytes()).hexdigest()
        name='library-'+key+'-'+sha[:12]+'.jpg';target=main.DATA/name
        if not target.exists():shutil.copyfile(path,target)
        return '/api/images/'+name,sha
    result=dict(backup=str(backup),archived=[],created=[],updated=[])
    # Preserve all existing story/character/annotation IDs; only image geometry is refreshed.
    url,sha=image('zhekan')
    if current['image']!=url or current.get('datasetRevision')!=REVISION:
        snapshot(current);p=copy.deepcopy(current)
        p.update(title='宋人折槛图',libraryKey='zhekan',datasetRevision=REVISION,image=url,imageVersion=p.get('imageVersion',0)+1)
        p['paintingInfo'].update(name='宋人折槛图（部分）',description='用户提供的局部 JPG；保留既有角色命名，已按当前图像重新定位。人物身份与画面对应仍待人工核对。')
        if 'painting' in p:p['painting']['imageNote']='已换用用户提供的无浏览器控件 JPG 局部图像，并重新定位人物。'
        names={c['id']:c['name'] for c in p['characters']}
        with Image.open(ASSETS/FILES['zhekan']) as im:size=im.size
        if size!=(1232,828):raise ValueError('折槛图尺寸与本次手工校准依据不一致，请重新核对')
        for a in p['annotations']:
            name=names.get(a.get('characterId'))
            if name in ZHEKAN_BOXES:a.update(**rectangle(ZHEKAN_BOXES[name],size),description=DESCRIPTIONS[name],confirmed=False,identityConfirmed=False,needsReview=True,origin='manual_relocated')
        p['observations']=[dict(id=uid(),annotationId=a['id'],description=a['description'],inference='',confirmed=False,stale=False,imageVersion=p['imageVersion']) for a in p['annotations'] if a.get('kind')=='character']
        p['matches']=[];p['checks']=[];p['sceneVideoApprovals']={};p.pop('scriptApproval',None)
        p['identityReference']=dict(imageSha256=sha,sourceProjectId=p['id'],basis='沿用用户已指定的角色对应，按2026-10-30新图手工重定位；不构成史料身份鉴定。',annotations=[{k:a[k] for k in ('id','x','y','w','h','characterId')} for a in p['annotations'] if a.get('kind')=='character'])
        for c in p['characters']:c['confirmed']=False
        p=reconcile(current,Project.model_validate(p).model_dump())
        saved=main.save(p,current['version'],'replace_painting_and_relocate',dict(imageSha256=sha,sourceFile=FILES['zhekan']))
        result['updated'].append(dict(id=saved['id'],version=saved['version'],characters=len(saved['characters'])))
    for pid in ARCHIVE:
        if any(r['id']==pid for r in active):
            p=main.get(pid);snapshot(p);p['archived']=True
            main.save(p,p['version'],'archive_project',dict(reason='用户要求移除空白／重复项目',recoverable=True))
            result['archived'].append(pid)
    active=main.projects()
    for key in ('chongping','bunian'):
        if any(r.get('libraryKey')==key for r in active):continue
        url,sha=image(key);p=build_project(key,url)
        p['identityReference']=dict(imageSha256=sha,basis='按用户提供的本地图片手工定位；命名依据与争议见各资料来源。',annotations=[{k:a[k] for k in ('id','x','y','w','h','characterId')} for a in p['annotations']])
        saved=main.save(p,0,'import_artwork_library',dict(libraryKey=key,sourceFile=FILES[key],imageSha256=sha,humanApproved=False))
        result['created'].append(dict(id=saved['id'],title=saved['title'],characters=len(saved['characters']),scenes=len(saved['scenes'])))
    (backup/'refresh-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true')
    print(json.dumps(run(parser.parse_args().apply),ensure_ascii=False,indent=2))
