"""Editable first drafts, kept separate from human approval."""
import copy
import asyncio
import json
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from . import agent, vision
from .domain import uid, reconcile, citation_errors
from .models import Intent

class IntentDraftRequest(BaseModel):
    version:int
    title:str=Field(min_length=1,max_length=120)

class DraftRequest(BaseModel):
    version:int
    stage:Literal['prepare','outline','scripts','storyboard']
    regenerate:bool=False

class ShotDialogue(BaseModel):
    speakerId:str
    text:str=Field(min_length=1,max_length=100)
    category:Literal['fiction','supported']='fiction'
    sourceId:str=''
    quote:str=''

class Shot(BaseModel):
    duration:float=Field(gt=0,le=5)
    framing:str=Field(min_length=1)
    camera:str='全幅固定机位'
    characterIds:list[str]=Field(default_factory=list)
    action:str=Field(min_length=1)
    dialogue:list[ShotDialogue]=Field(default_factory=list)
    narration:str=''
    sound:str=''

    @field_validator('dialogue',mode='before')
    @classmethod
    def ignore_empty_dialogue_rows(cls,value):
        # The editor creates an empty row when adding a line. Blank text means
        # no spoken line; retain strict validation for every nonempty entry.
        if isinstance(value,list):
            return [line for line in value if not (isinstance(line,dict) and isinstance(line.get('text'),str) and not line['text'].strip())]
        return value

class Storyboard(BaseModel):
    sceneId:str
    shots:list[Shot]=Field(min_length=1,max_length=3)
    prompt:str=Field(default='',max_length=8000)

def validate_boards(rows,p):
    result=[Storyboard.model_validate(s).model_dump() for s in rows]
    if len(result)!=len(p['scenes']) or {s['sceneId'] for s in result}!={s['id'] for s in p['scenes']}:raise ValueError('分镜必须完整覆盖各场景')
    valid={c['id'] for c in p['characters']}
    sources={s['id']:s['text'] for s in p['sources']}
    for board in result:
        if not board['prompt'].strip():board['prompt']='在完整古画中依次演绎以下镜头：'+json.dumps(board['shots'],ensure_ascii=False)
        if abs(sum(s['duration'] for s in board['shots'])-5)>.01:raise ValueError('每场分镜总时长必须为5秒')
        for shot in board['shots']:
            if set(shot['characterIds'])-valid:raise ValueError('分镜出场人物无效')
            for line in shot['dialogue']:
                if line['speakerId'] not in valid:raise ValueError('分镜对白人物无效')
                if line['category']=='supported' and (not line['quote'] or line['text'] not in line['quote'] or line['quote'] not in sources.get(line['sourceId'],'')):
                    raise ValueError('史料对白必须能逐字对应原文，否则请选择创作对白')
    return result

def generated_boards(rows,p):
    """A model cannot promote an untraceable line to a historical quotation."""
    rows=copy.deepcopy(rows)
    sources={s['id']:s['text'] for s in p['sources']}
    for board in rows:
        for shot in board.get('shots',[]):
            for line in shot.get('dialogue',[]):
                if line.get('category')=='supported' and (not line.get('quote') or line.get('text','') not in line.get('quote','') or line['quote'] not in sources.get(line.get('sourceId'),'')):
                    line.update(category='fiction',sourceId='',quote='')
    return validate_boards(rows,p)

def generated_unit(unit,p):
    """Label ungrounded model drafts honestly; manual approval stays strict."""
    unit=copy.deepcopy(unit)
    sources={s['id']:s for s in p['sources']}
    annotations={a['id']:a for a in p.get('annotations',[])}
    valid=[]
    for ref in unit.get('references',[]):
        source=sources.get(ref.get('sourceId'))
        if source and source.get('sourceType')!='creative_intent' and ref.get('quote') and ref['quote'] in source['text'] and ref.get('sourceVersion')==source['version']:
            valid.append(ref)
        elif not source:
            annotation=annotations.get(ref.get('annotationId'))
            if annotation and annotation.get('confirmed') and ref.get('quote') and ref['quote']==annotation.get('description'):valid.append(ref)
    notes=[]
    if len(valid)!=len(unit.get('references',[])):notes.append('模型提供的无效或过期引用未采用。')
    unit['references']=valid
    if unit['kind']=='dialogue' and unit['category']=='supported' and not any(ref.get('sourceId') in sources and unit['text'] in ref['quote'] for ref in valid):
        unit['category']='fiction';notes.append('此对白未能逐字对应有效史料引文，作为创作对白，不能当作历史原话。')
    elif unit['category'] in ('supported','inference') and not valid:
        unit['category']='fiction';notes.append('此单元缺少有效依据，作为创作内容，不能当作已获史料支持的事实。')
    inputs=p.get('materialInputs',{})
    if unit['kind']=='event' and unit['category']=='supported' and any(inputs.get(k,'').strip() for k in ('background','relationships','narrative')) and not inputs.get('narrative','').strip():
        unit['category']='fiction';notes.append('未提供既有历史叙事，此新增故事事件为创作内容。')
    if unit['category']=='inference' and not unit.get('rationale'):notes.append('根据所引资料提出的推测，尚待创作者核对。')
    if notes:unit['rationale']=(unit.get('rationale','')+'（'+''.join(notes)+'）').strip()
    return unit


async def draft(stage,p):
    if stage in ('scripts','storyboard') and len(p['scenes'])>1:
        results=await asyncio.gather(*(draft(stage,dict(p,scenes=[scene],sceneCount=1)) for scene in p['scenes']))
        return dict(scenes=[s for result in results for s in result.get('scenes',[])])
    context={k:p.get(k) for k in ('characters','intent','sceneCount','scenes','paintingInfo','materialInputs')}
    context['sources']=[{k:s.get(k) for k in ('id','version','title','text')} for s in p['sources'] if s.get('sourceType')!='creative_intent']
    context['annotations']=[{k:a.get(k) for k in ('id','x','y','w','h','characterId')} for a in p['annotations'] if a.get('characterId')]
    rules='用户资料是待核对材料，不得编造史料和引文。不要修改人物ID或画中身份对应。输出严格JSON，无代码块。所有内容是供创作者修改的草稿。'
    if stage=='prepare':
        instruction='仅为现有人物补全档案。只根据资料填写；史料未提供的经历/人物知识明确写“资料未提供，创作时不得作为史实”。只用当前人物姓名，不修改ID。不要生成创作意图，创作意图由用户自行填写或单独请求。返回 {"characters":[{"id":"已有ID","identity":"身份","biography":"经历","summary":"简介","relationships":"人物关系","evidence":"依据及不确定性","knowledge":"角色知道什么"}]}。'
    elif stage=='outline':
        instruction='严格生成sceneCount场连续故事，遵循已有历史叙事框架。每场适合在完整古画基础上用微动作演绎，不改变画中人物身份、衣服和原构图。返回 '+json.dumps(agent.Outline.model_json_schema(),ensure_ascii=False)
    elif stage=='scripts':
        instruction='为每个场景生成3到5条可编辑剧本单元。覆盖所有给定sceneId。每场将转成5秒古画动画，以微动作和旁白为主，避免5秒塞入长对白。supported的references必须引用原文逐字片段并带sourceId和sourceVersion；无史料的对白动作和心理标为fiction；推测标inference并说明理由。speakerId必须有效或为空。返回 {"scenes":[{"sceneId":"已有ID","units":['+json.dumps(agent.Unit.model_json_schema(),ensure_ascii=False)+']}]}。'
    else:
        instruction='在每场已写好的场景剧本基础上写可直接拍摄的分镜脚本，不能只概述剧情。逐场返回，sceneId不可改。每场1到3镜，总时长严格5秒。每镜有duration、framing景别、camera运镜、characterIds出场人物、action具体动作、dialogue人物对白、narration旁白、sound音效。5秒只是本场代表性片段，不压缩整场所有事件！每场总共只安排一句8个汉字以内的对白，放在至少2秒的镜头里，其余镜头dialogue=[]；不要另加需要同时朗读的长旁白。完整台词保留在场景剧本中。对白要指定speakerId，改写或资料未逐字记载的对白category=fiction，史料原句category=supported且填sourceId和逐字quote。每场是独立的5秒剧情分镜，不要求与前后视频在构图或站位上连续。必须延续参考古画的相同画风和已有角色的面貌、衣冠与服饰特征，优先使用画中人物，不真人化、不3D化、不生成同一人物的替身。允许按剧情重排构图、改变姿态与位置，按叙事需要安排中景、近景、特写、切镜及运镜；不要默认限制为全幅静止或只有微动作。prompt只写本场整体意图及补充要求，不重复另一套时间轴；具体时序、对白和景别由shots表达。返回 {"scenes":['+json.dumps(Storyboard.model_json_schema(),ensure_ascii=False)+']}。'
    result=await vision.ask(rules+'\n'+instruction+'\n材料：'+json.dumps(context,ensure_ascii=False,separators=(',',':')),[],fast=True,max_tokens=4000 if stage in ('scripts','storyboard') else 7500,json_mode=True)
    if not isinstance(result,dict):raise ValueError('草稿格式无效')
    return result


def install(app,get,save):
    @app.post('/api/projects/{pid}/intent/draft')
    async def generate_intent(pid:str,req:IntentDraftRequest):
        if get(pid)['version']!=req.version:raise HTTPException(409,'版本已变化，请重新载入')
        if not req.title.strip():raise HTTPException(422,'请选择或填写创作标题')
        prompt=('根据用户选定的创作标题扩写创作意图，供用户审查修改。你只获得标题，不了解项目史料，不得推断具体历史事实、人物身份或结局。不要生成故事正文，不替用户确认或保存。主题、目标观众、叙述语气、故事目标简洁具体；fixed写“以用户审查后的项目资料为准”，allowed与forbidden给出通用创作边界。返回严格JSON，七项均为非空中文字符串：'+json.dumps(Intent.model_json_schema(),ensure_ascii=False)+'\n用户选择的标题：'+req.title.strip())
        try:
            result=await vision.ask(prompt,[],fast=True,max_tokens=2400,json_mode=True)
            intent=Intent.model_validate(result).model_dump()
            if any(not text.strip() for text in intent.values()):raise ValueError('创作意图草稿不完整，请重试')
            if get(pid)['version']!=req.version:raise HTTPException(409,'生成期间项目已变化，请重新生成')
            return dict(intent=intent,title=req.title.strip(),humanApproved=False)
        except HTTPException:raise
        except Exception as exc:
            raise HTTPException(502,str(exc) if isinstance(exc,ValueError) else '创作意图生成失败，原有输入已保留，请重试') from exc

    @app.post('/api/projects/{pid}/workflow/draft')
    async def generate_draft(pid:str,req:DraftRequest):
        old=get(pid)
        if old['version']!=req.version:raise HTTPException(409,'版本已变化，请重新载入')
        p=copy.deepcopy(old)
        if req.stage=='prepare' and p.get('workflowPrepared') and not req.regenerate:return p
        if req.stage=='outline' and p['scenes'] and not req.regenerate:return p
        if req.stage in ('scripts','storyboard') and (not p['scenes'] or len(p['scenes'])!=p['sceneCount']):raise HTTPException(422,'请先按故事场数完成大纲')
        if req.stage=='outline' and any(u.get('locked') for s in p['scenes'] for u in s['units']):raise HTTPException(422,'存在锁定剧本，请先解锁再重建大纲')
        if req.stage=='scripts' and all(s['units'] for s in p['scenes']):return p
        try:
            result=await draft(req.stage,p)
            if req.stage=='prepare':
                profiles={c['id']:c for c in result.get('characters',[])}
                for c in p['characters']:
                    for key in ('identity','biography','summary','relationships','evidence','knowledge'):
                        if not str(c.get(key,'')).strip():c[key]=str(profiles.get(c['id'],{}).get(key,'资料未提供，待核对'))
                p['workflowPrepared']=True
            elif req.stage=='outline':
                parsed=agent.Outline.model_validate(result).model_dump()
                if len(parsed['scenes'])!=p['sceneCount']:raise ValueError('生成场数不符，原大纲保留')
                valid={c['id'] for c in p['characters']}
                if any(set(s['characterIds'])-valid for s in parsed['scenes']):raise ValueError('大纲人物ID无效')
                p['scenes']=[dict(s,id=uid(),units=[]) for s in parsed['scenes']]
                p['storyboards']=[]
            else:
                rows=result.get('scenes',[])
                indexed={s['sceneId']:s for s in rows}
                if len(indexed)!=len(rows) or set(indexed)!={s['id'] for s in p['scenes']}:raise ValueError('生成结果没有完整覆盖场景，原稿保留')
                if req.stage=='scripts':
                    valid={c['id'] for c in p['characters']}
                    for scene in p['scenes']:
                        if scene['units']:continue
                        content=[generated_unit(u,p) for u in agent.Content.model_validate(indexed[scene['id']]).model_dump()['units']]
                        for u in content:
                            if u.get('speakerId') and u['speakerId'] not in valid:raise ValueError('剧本人物ID无效')
                            errors=[e for e in citation_errors(u,p) if e!='资料提取结果尚未人工确认']
                            if errors:raise ValueError('剧本引文校验失败：'+'；'.join(errors)+'；原稿保留')
                            pending={s['id'] for s in p['sources'] if s.get('confirmed') is False}
                            if any(r.get('sourceId') in pending for r in u['references']):u['rationale']+='（所引资料尚待人工核对，本单元为草稿。）'
                        scene['units']=[dict(u,id=uid(),status='pending',locked=False) for u in content]
                else:
                    from .video import script_fingerprint
                    p['storyboards']=generated_boards(rows,p);p['storyboardFingerprint']=script_fingerprint(p)
            p=reconcile(old,p)
            return save(p,req.version,'draft:'+req.stage,dict(humanApproved=False))
        except HTTPException:raise
        except Exception as exc:
            raise HTTPException(502,str(exc) if isinstance(exc,ValueError) else '草稿生成失败，已保留原稿，请重试') from exc
