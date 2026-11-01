"""Portable narrative packages, using the same authored interaction as the reader."""
import copy
import io
import json
import re
import hashlib
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Literal
from fastapi import HTTPException
from fastapi.responses import Response
from PIL import Image, ImageOps
from .models import Project
from pydantic import BaseModel
from .domain import citation_errors
from .video import scene_fingerprint, script_fingerprint, board_fingerprint


def local_file(root, name):
    # Package only known local assets, never a client-supplied absolute path or URL.
    if not name or '\\' in name or '/' in name or Path(name).name != name:return None
    root=Path(root).resolve();path=(root/name).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def painting_file(root,name):
    path=local_file(root,name)
    if not path or path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):return None
    try:
        with Image.open(path) as im:im.verify()
    except (OSError,ValueError):return None
    return path


def inspect(p, data, jobs=()):
    problems=[]
    def issue(section,code,message,step,scene_id='',severity='error',source_id=''):
        problems.append(dict(section=section,code=code,message=message,step=step,sceneId=scene_id,sourceId=source_id,severity=severity))
    people={c['id']:c for c in p['characters']};sources={s['id']:s for s in p['sources']}
    used_sources={r.get('sourceId') for s in p['scenes'] for u in s['units'] for r in u.get('references',[])}
    used_sources.update(q.get('sourceId') for c in p.get('interaction',{}).get('chapters',[]) for q in c['questions'])
    for sid in used_sources:
        source=sources.get(sid)
        if source and source.get('confirmed') is False:issue('sources','source_pending','来源「'+source['title']+'」尚待人工核对。',0,source_id=sid)
    entity_ids=[item['id'] for group in (p['characters'],p['sources'],p['annotations'],p['scenes'],[u for s in p['scenes'] for u in s['units']]) for item in group]
    if len(set(entity_ids))!=len(entity_ids):issue('story','duplicate_id','项目中存在重复编号，请修复后导出。',3)
    boxes={a['id']:a for a in p['annotations'] if a.get('kind')=='character'}
    mapped={a.get('characterId') for a in boxes.values()}
    confirmed_mapped={a.get('characterId') for a in boxes.values() if a.get('identityConfirmed')}
    painting=painting_file(data,Path(p.get('image','')).name) if p.get('image','').startswith('/api/images/') else None
    if not painting:issue('artwork','painting_missing','请补充可读取的原画文件。',0)
    if not people:issue('characters','characters_missing','请建立人物档案。',1)
    if any(not c.get('confirmed') for c in people.values()):issue('characters','characters_pending','人物资料有更新，请在人物页核对。',1)
    scenes=p['scenes'];scene_ids=[s['id'] for s in scenes]
    if not scenes or len(scenes)!=p['sceneCount']:issue('story','scene_count','故事场数与大纲不一致。',2)
    if len(set(scene_ids))!=len(scene_ids):issue('story','scene_duplicate','场景编号存在重复。',2)
    if not p['outlineConfirmed']:issue('story','outline_pending','请确认故事大纲。',2)
    for scene in scenes:
        sid=scene['id']
        if not scene['title'].strip():issue('story','scene_title','有场景尚未填写标题。',2,sid)
        if any(cid not in people for cid in scene['characterIds']):issue('story','scene_character','场景关联了已不存在的人物。',2,sid)
        if not scene['units']:issue('story','script_missing','本场尚无剧本。',3,sid)
        elif any(u['status']!='approved' for u in scene['units']):issue('story','script_pending','本场仍有剧本段落待核对。',3,sid)
        errors=[]
        for unit in scene['units']:
            if not unit['text'].strip():errors.append('存在空白剧本段落')
            errors.extend(e for e in citation_errors(unit,p) if e!='资料提取结果尚未人工确认')
            if unit.get('speakerId') and unit['speakerId'] not in people:errors.append('存在失效的说话人物')
        if errors:issue('sources','citation_invalid','本场引用需处理：'+'；'.join(dict.fromkeys(errors)),3,sid)
    interaction=p.get('interaction',{});chapters=interaction.get('chapters',[])
    guides=interaction.get('guideAnnotationIds',[])
    valid_guides=[]
    for aid in guides:
        a=boxes.get(aid);c=people.get(a.get('characterId')) if a else None
        if c and re.search('宫女|宫人|侍女|内侍|侍从|童子',c['name']+' '+c.get('identity','')):valid_guides.append(aid)
        else:issue('interaction','guide_invalid','引路人已失效或不符合宫人类角色条件，请重新选择。',4)
        if c and not a.get('identityConfirmed'):issue('artwork','guide_pending','请在画作探索中核对引路人「'+c['name']+'」的姓名与位置。',0)
    if not valid_guides:issue('interaction','guide_missing','请为入画对话选择至少一位有原画立绘的引路人。',4)
    if [c['id'] for c in chapters]!=scene_ids:issue('interaction','chapters_mismatch','请按大纲顺序补齐每一幕的对话配置。',4)
    seen=set();pending_speakers=set()
    for chapter in chapters:
        sid=chapter['id']
        if not chapter['title'].strip() or not chapter['lead'].strip() or not chapter['outro'].strip():issue('interaction','chapter_copy','本幕的标题、引路词或收束语尚未完成。',4,sid)
        if not chapter['questions']:issue('interaction','questions_missing','本幕至少需要一个问答，才能通过线索解锁。',4,sid)
        for q in chapter['questions']:
            if not q['id'] or q['id'] in seen:issue('interaction','question_id','问答编号缺失或重复。',4,sid)
            seen.add(q['id'])
            if q['personId'] not in people or q['personId'] not in mapped:issue('interaction','speaker_missing','本幕的回答人物需要有效档案与原画立绘。',4,sid)
            elif q['personId'] not in confirmed_mapped and q['personId'] not in pending_speakers:
                pending_speakers.add(q['personId'])
                issue('artwork','speaker_pending','请核对「'+people[q['personId']]['name']+'」的画中位置。',0,sid)
            if any(not q.get(k,'').strip() for k in ('question','answer','clue')):issue('interaction','question_copy','请补齐提问、回答和获得的线索。',4,sid)
            source=sources.get(q.get('sourceId'));quote=q.get('quote','')
            if (q.get('sourceId') and (not source or q.get('sourceVersion')!=source['version'])) or quote and (not source or quote not in source['text'] or source.get('sourceType')=='creative_intent'):issue('interaction','question_citation','对话引文不存在、已过期或误用了创作设想。',4,sid)
            if q.get('category')=='inference' and not quote:issue('interaction','inference_source','解释与推测需要关联原文依据。',4,sid)
            if q.get('category')=='supported' and (not quote or not source or q['answer'] not in quote):issue('interaction','supported_answer','标为原文作答的回答须逐字对应所引原文。',4,sid)
    if any(not check.get('resolved') for check in p.get('checks',[])):issue('review','findings_open','有一致性检查建议尚未处理。',4)
    if not p.get('checks'):issue('review','ai_optional','尚未运行 AI 一致性检查；该检查可选，不代替人工核对。',4,severity='warning')
    media=[]
    for scene in scenes:
        board=next((b for b in p.get('storyboards',[]) if b.get('sceneId')==scene['id']),None)
        if board:
            from .workflow import validate_boards
            try:validate_boards([board],dict(p,scenes=[scene]))
            except (ValueError,KeyError,TypeError):
                board=None
                issue('media','board_invalid','本场分镜未通过完整性检查，将回退为原画。',3,scene['id'],severity='warning')
        candidates=[j for j in jobs if j.get('sceneId')==scene['id'] and j.get('status')=='succeeded' and j.get('reviewStatus')!='needs_revision' and not j.get('test')]
        usable=[]
        for job in candidates:
            matches=(job['scopeFingerprint']==scene_fingerprint(p,scene['id'])) if job.get('scopeFingerprint') else job.get('scriptFingerprint')==script_fingerprint(p) and job.get('boardFingerprint')==board_fingerprint(p)
            pinned=p.get('interaction',{}).get('sceneVideos',{}).get(scene['id'])==job['id']
            if (matches or pinned) and local_file(Path(data)/'videos',job['id']+'.mp4'):usable.append(job)
        pinned_id=p.get('interaction',{}).get('sceneVideos',{}).get(scene['id'])
        chosen=next((j for j in usable if j['id']==pinned_id),None) or max(usable,key=lambda j:j.get('time',''),default=None)
        media.append(dict(sceneId=scene['id'],kind='video' if chosen else 'storyboard' if board and board.get('shots') else 'painting',jobId=chosen['id'] if chosen else '',path='assets/videos/'+chosen['id']+'.mp4' if chosen else '',board=board))
        if not chosen:issue('media','video_optional','本场无可用的当前版动画，将用分镜或原画呈现。',3,scene['id'],severity='warning')
    sections=[]
    for key,title,step in [('artwork','原画与立绘',0),('characters','人物与创作设想',1),('story','逐场故事与剧本',3),('sources','依据与出处',3),('interaction','入画对话与线索',4),('media','场景媒体',3),('review','检查与版本',4)]:
        group=[x for x in problems if x['section']==key]
        sections.append(dict(id=key,title=title,step=step,status='blocked' if any(x['severity']=='error' for x in group) else 'optional' if group else 'ready',issues=len(group)))
    return dict(ready=not any(x['severity']=='error' for x in problems),issues=problems,sections=sections,media=media,counts=dict(characters=len(people),scenes=len(scenes),questions=sum(len(c['questions']) for c in chapters),guides=len(valid_guides),videos=sum(m['kind']=='video' for m in media)))


def package(p,data,jobs,draft=True):
    status=inspect(p,data,jobs)
    if not draft and not status['ready']:raise HTTPException(422,dict(message='请先处理叙事包的必需项目。',issues=[x for x in status['issues'] if x['severity']=='error']))
    picture=Path(p.get('image','')).name if p.get('image','').startswith('/api/images/') else ''
    people={c['id']:c for c in p['characters']}
    portraits=[dict(annotationId=a['id'],characterId=a['characterId'],box={k:a[k] for k in ('x','y','w','h')},path='assets/portraits/'+hashlib.sha256(a['id'].encode()).hexdigest()[:24]+'.png') for a in p['annotations'] if a.get('kind')=='character' and a.get('characterId') in people]
    chapters=copy.deepcopy(p.get('interaction',{}).get('chapters',[]))
    for i,c in enumerate(chapters):c['unlock']=dict(requiresQuestionIds=[q['id'] for q in c['questions']],sceneId=c['id'],nextSceneId=chapters[i+1]['id'] if i+1<len(chapters) else '',mediaPolicy='exact-current-scene')
    documents=[dict(id=d['id'],title=d['title'],citation=d.get('citation',''),path='assets/documents/'+d['filename'] if local_file(data,d.get('filename','')) else '') for d in p.get('documents',[])]
    return dict(schemaVersion='2.0',kind='animatedscroll-narrative',state='draft' if draft else 'approved',exportedAt=datetime.now(timezone.utc).isoformat(),projectId=p['id'],projectVersion=p['version'],title=p['title'],readiness=status,artwork=dict(info=p.get('paintingInfo',{}),image='assets/painting/'+picture if picture else '',portraits=portraits),documents=documents,characters=p['characters'],intent=p['intent'],sources=p['sources'],scenes=p['scenes'],interaction=dict(guideAnnotationIds=p.get('interaction',{}).get('guideAnnotationIds',[]),sceneVideos=p.get('interaction',{}).get('sceneVideos',{}),presentation=p.get('interaction',{}).get('presentation',{}),chapters=chapters,progressStorage='reader-local; excluded from package',answerPolicy='authored; no automatic model calls'),media=status['media'],project=p)


def markdown(bundle):
    lines=['# '+bundle['title'], '', '状态：'+('草稿' if bundle['state']=='draft' else '已确认叙事包'),'', '## 人物与创作设想']
    for c in bundle['characters']:lines+=['- '+c['name']+'：'+c.get('identity','')]
    for k,v in bundle['intent'].items():
        if v:lines+=['- '+k+'：'+v]
    for s in bundle['scenes']:
        lines+=['','## '+s['title'],'',s['goal'],'',s['connection']]
        for u in s['units']:lines+=['',f"[{u['category']} / {u['status']}] {u['text']}"]
        chapter=next((c for c in bundle['interaction']['chapters'] if c['id']==s['id']),None)
        if chapter:
            lines+=['','### 入画对话','',chapter['lead']]
            for q in chapter['questions']:lines+=['','问：'+q['question'],'','答：'+q['answer'],'','线索：'+q['clue'],'','依据：'+q['quote']]
            lines+=['',chapter['outro']]
    lines+=['','## 资料与出处']
    for s in bundle['sources']:lines+=['','### '+s['title'],s.get('citation',''),s.get('editorialNote',''),s['text']]
    return '\n'.join(lines)


def archive(bundle,data):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps({k:v for k,v in bundle.items() if k!='project'},ensure_ascii=False,indent=2))
        z.writestr('project.json',json.dumps(bundle['project'],ensure_ascii=False,indent=2))
        z.writestr('story.md',markdown(bundle))
        z.writestr('README.md','# AnimatedScroll 叙事包\n\nmanifest.json 为体验契约，project.json 为创作快照；story.md 可直接阅读。素材均使用包内相对路径。\n按场景顺序阅读引路词与问答，读完本幕所有问题才解锁对应场景。没有视频时展示本幕分镜或原画。\n本包不包含播放器程序、用户阅读进度、API 密钥、历史日志或外部网页缓存。JSON 单文件不含素材文件，ZIP 才包含可用的本地素材。\n')
        painting=painting_file(data,Path(bundle['artwork']['image']).name)
        if painting:
            z.write(painting,bundle['artwork']['image'])
            with Image.open(painting) as raw:
                im=ImageOps.exif_transpose(raw).convert('RGB');w,h=im.size
                for portrait in bundle['artwork']['portraits']:
                    b=portrait['box'];x=min(w-1,max(0,int(b['x']*w)));y=min(h-1,max(0,int(b['y']*h)))
                    crop=im.crop((x,y,max(x+1,min(w,int((b['x']+b['w'])*w))),max(y+1,min(h,int((b['y']+b['h'])*h)))))
                    output=io.BytesIO();crop.save(output,format='PNG');z.writestr(portrait['path'],output.getvalue())
        for item in bundle['media']:
            if item['kind']=='video':
                path=local_file(Path(data)/'videos',item['jobId']+'.mp4')
                if path:z.write(path,item['path'])
        for doc in bundle['project'].get('documents',[]):
            path=local_file(data,doc.get('filename',''))
            if path:z.write(path,'assets/documents/'+path.name)
    return stream.getvalue()


class SourceConfirmation(BaseModel):
    version:int


def install(app,get,db,data,save):
    def jobs(pid):
        with db() as conn:return [json.loads(r[0]) for r in conn.execute('SELECT body FROM video_jobs WHERE project=?',(pid,))]
    @app.post('/api/projects/{pid}/sources/{sid}/confirm')
    def confirm_source(pid:str,sid:str,req:SourceConfirmation):
        p=get(pid)
        if p['version']!=req.version:raise HTTPException(409,'项目已变化，请重新载入后核对')
        source=next((s for s in p['sources'] if s['id']==sid),None)
        if not source:raise HTTPException(404,'来源不存在')
        if source.get('sourceType')=='creative_intent':raise HTTPException(422,'创作设想不能确认为史料来源')
        source['confirmed']=True
        return save(p,req.version,'confirm_source',dict(sourceId=sid,humanApproved=True))
    @app.post('/api/projects/{pid}/narrative/inspect')
    def inspect_draft(pid:str,project:Project):
        current=get(pid)
        if project.id!=pid:raise HTTPException(400,'项目ID不匹配')
        if current['version']!=project.version:raise HTTPException(409,'项目已变化，请重新载入')
        return inspect(project.model_dump(),data(),jobs(pid))
    @app.get('/api/projects/{pid}/narrative/export')
    def export(pid:str,format:Literal['zip','json','md']='zip',draft:bool=True,reviewed:bool=False):
        if not draft and not reviewed:raise HTTPException(422,'请先确认已审查当前叙事包的问答、线索与解锁顺序。')
        bundle=package(get(pid),data(),jobs(pid),draft)
        bundle['review']=dict(humanConfirmed=reviewed and not draft,projectVersion=bundle['projectVersion'])
        if format=='zip':body=archive(bundle,data());media='application/zip'
        elif format=='json':body=json.dumps(bundle,ensure_ascii=False,indent=2);media='application/json'
        else:body=markdown(bundle);media='text/markdown; charset=utf-8'
        return Response(body,media_type=media,headers={'Content-Disposition':f'attachment; filename="narrative-{pid}.{format}"'})
