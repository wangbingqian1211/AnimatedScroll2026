"""Wan image-to-video jobs with durable IDs and explicit prompt approval."""
import asyncio
import base64
import hashlib
import io
import json
import os
import re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
import httpx
from PIL import Image,ImageOps
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

LIMIT=None  # No local generation-count cap; provider limits still apply.
PROMPT_POLICY_VERSION='painting-reference-cast-v4'
MEDIA_MODE='reference_images'
STYLE='画风与人物延续是最高优先级：与所附古画保持完全相同的绘画风格，延续其笔触、线条、设色、材质和人物造型，不真人化、不3D化、不改成现代卡通。优先使用画作中已有的人物，保持每位人物的面貌、发式、衣冠、服饰纹样及身份特征；人物姓名仅用于识别，不能凭姓名重新设计人物或生成替身。'
VIDEO_MODEL='wan3.0-video'
VIDEO_PARAMETERS=dict(resolution='480P',ratio='adaptive',duration=5,audio=True,prompt_extend=False,seed=20261026)

def reference_plan(p,scene,board):
    """Image 1 is the painting; following images identify the actual cast."""
    people={c['id']:c for c in p['characters']};ids=[]
    for shot in board.get('shots',[]):
        ids.extend(d.get('speakerId') for d in shot.get('dialogue',[]) if d.get('text','').strip())
        ids.extend(shot.get('characterIds',[]))
    if not ids:ids.extend(scene.get('characterIds',[]))
    plan=[dict(label='图1',kind='painting',name='原画画风与场景参考')]
    used=set()
    for cid in ids:
        if cid in used or cid not in people:continue
        used.add(cid)
        box=next((a for a in p['annotations'] if a.get('kind','character')=='character' and a.get('characterId')==cid),None)
        if not box:continue
        bounds={k:box[k] for k in ('x','y','w','h')}
        if not (bounds['w']>0 and bounds['h']>0 and bounds['x']>=0 and bounds['y']>=0 and bounds['x']+bounds['w']<=1.000001 and bounds['y']+bounds['h']<=1.000001):continue
        plan.append(dict(label='图'+str(len(plan)+1),kind='character',characterId=cid,name=people[cid]['name'],box=bounds))
        if len(plan)==10:break
    return plan

def video_prompt(p,scene,board):
    cast={c['id']:c['name'] for c in p['characters']}
    positions=[];visible=set();refs={r.get('characterId'):r for r in reference_plan(p,scene,board) if r['kind']=='character'}
    for a in p['annotations']:
        if a.get('characterId') in cast:
            visible.add(a['characterId'])
            ref=refs.get(a['characterId'])
            if ref:
                positions.append(f"{ref['label']}＝{cast[a['characterId']]}的原画裁切。请使用这张人物参考的脸、发式和衣冠，不与其他人物互换。原画位置约横向{round((a['x']+a['w']/2)*100)}%、纵向{round((a['y']+a['h']/2)*100)}%，仅用于辨认，不固定生成后的站位。")
                if cast[a['characterId']]=='朱云' and '辛弃疾' in cast.values():positions.append(f"尤其注意：{ref['label']}对应朱云，朱云与辛弃疾是两个不同人物，不得互换面貌、衣冠或说话身份。")
    lines=[];start=0
    for shot in board['shots']:
        end=start+shot['duration'];actors='、'.join(cast[c] for c in shot.get('characterIds',[]) if c in visible) or '按本镜动作选择参考画中已有的人物'
        spoken='；'.join(cast.get(d['speakerId'],'未指定人物')+('说' if d['speakerId'] in visible else '以画外声音说')+'：“'+d['text']+'”' for d in shot.get('dialogue',[]) if isinstance(d.get('text'),str) and d['text'].strip()) or '无人物对白'
        lines.append(f"{start:g}–{end:g}秒：景别与构图：{shot.get('framing','按剧情安排')}。运镜：{shot.get('camera','按剧情安排')}。出场人物：{actors}。动作：{shot['action']}。对白：{spoken}。旁白：{shot.get('narration') or '无'}。音效与环境声：{shot.get('sound') or '安静'}。")
        start=end
    composition='图1仅提供古画画风与场景参考，不是首帧或尾帧；后续参考图分别指定人物外貌。本段是独立的5秒剧情分镜，不要求与前后视频在机位、人物站位或首尾构图上连续，也不要求回到原画布局。可以直接以剧本要求的景别开场，按故事情节改变人物位置、姿态与场景构图，允许中景、近景、特写、切镜及相应运镜；无需先展示完整原画。环境可随镜头视角重构，但必须延续同一古画画风。'
    cast_rule='按分镜选择出场者，特写中可只出现一个人物；优先复用原画已有角色。不把静止的原画人物留作背景又叠加会动的同一人物分身。未在原画定位的角色默认仅作画外声音，若剧情确需新增可见人物，应先由用户补充人物设定并审核。只朗读分镜列出的对白和旁白，不新增字幕、文字、标识或现代物件。'
    return STYLE+'\n'+composition+'\n'+cast_rule+'\n人物外貌参考索引：\n'+'\n'.join(positions)+'\n场景：'+scene['title']+'\n本场整体创作描述（具体时序、对白及景别以逐镜安排为准）：\n'+board.get('prompt','')+'\n逐镜安排：\n'+'\n'.join(lines)

def prompt_base(p,sid):
    return hashlib.sha256((scene_fingerprint(p,sid)+PROMPT_POLICY_VERSION+json.dumps(VIDEO_PARAMETERS,sort_keys=True)+VIDEO_MODEL).encode()).hexdigest()

def prompt_preview(p,scene,board):
    base=prompt_base(p,scene['id']);saved=p.get('sceneVideoPrompts',{}).get(scene['id'],{})
    compiled=video_prompt(p,scene,board)
    text=saved.get('text') or compiled
    legacy_layout=any(phrase in text for phrase in ('全幅固定','固定全幅','不改变面容位置服饰','保持全幅古画构图','原位不动'))
    refs=reference_plan(p,scene,board)
    return dict(prompt=text,compiledPrompt=compiled,customized=bool(saved.get('text')),stale=bool(saved.get('text')) and saved.get('baseFingerprint')!=base,baseFingerprint=base,requestFingerprint=request_fingerprint(text,refs),model=VIDEO_MODEL,parameters=dict(VIDEO_PARAMETERS),mediaMode=MEDIA_MODE,references=refs,hasLegacyLayoutInstructions=legacy_layout)

def request_fingerprint(text,references=None):
    return hashlib.sha256(json.dumps(dict(prompt=text,model=VIDEO_MODEL,parameters=VIDEO_PARAMETERS,mediaMode=MEDIA_MODE,references=references,policy=PROMPT_POLICY_VERSION),ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def scene_request_fingerprint(p,scene,board,text):
    return request_fingerprint(text,reference_plan(p,scene,board))

def reviewed_prompt(p,scene,board):
    preview=prompt_preview(p,scene,board)
    if not preview['customized'] or preview['stale']:raise ValueError('请先查看、编辑并保存当前分镜的最终视频提示词，再审核生成')
    return preview['prompt']

def image_path(p,data):
    path=Path(data)/Path(p.get('image','')).name
    if not p.get('image') or not path.is_file():raise ValueError('请先上传当前古画')
    return path

def script_fingerprint(p):
    value={k:p.get(k) for k in ('image','imageVersion','sceneCount','intent')}
    value['characters']=[{k:c.get(k) for k in ('id','name','identity')} for c in p['characters']]
    value['annotations']=[{k:a.get(k) for k in ('id','x','y','w','h','characterId')} for a in p['annotations']]
    value['scenes']=[{k:s.get(k) for k in ('id','title','goal','connection','characterIds')}|{'units':[{k:u.get(k) for k in ('text','kind','category','rationale','speakerId','references')} for u in s['units']]} for s in p['scenes']]
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def board_fingerprint(p):
    return hashlib.sha256(json.dumps(p.get('storyboards',[]),ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def scene_fingerprint(p,sid):
    scene=next((s for s in p['scenes'] if s['id']==sid),None)
    board=next((b for b in p.get('storyboards',[]) if b['sceneId']==sid),None)
    if not scene or not board:return ''
    subset=dict(p,sceneCount=1,scenes=[scene],storyboards=[board])
    return hashlib.sha256((script_fingerprint(subset)+board_fingerprint(subset)).encode()).hexdigest()

def endpoint():return os.getenv('DASHSCOPE_VIDEO_BASE_URL','https://cn-beijing.maas.qianwenaiapi.com/api/v1').rstrip('/')
def headers(async_mode=False):
    key=os.getenv('DASHSCOPE_API_KEY','')
    if not key:raise ValueError('未配置 DASHSCOPE_API_KEY')
    result={'Authorization':'Bearer '+key}
    if async_mode:result['X-DashScope-Async']='enable'
    return result

def reserve(data,jobid):
    """Keep submission records without enforcing or resetting a quota."""
    folder=Path(data)/'video-budget';folder.mkdir(exist_ok=True)
    try:
        with (folder/f'{jobid}.ticket').open('x',encoding='utf-8') as f:f.write(jobid)
    except FileExistsError:pass
    return jobid

def remaining(data):return None

def payload(job,path):
    image=ImageOps.exif_transpose(Image.open(path)).convert('RGB')
    if min(image.size)<240 or max(image.size)>8000 or max(image.size)/min(image.size)>8:raise ValueError('古画需每边240–8000像素，长宽比不超过8:1；不会自动裁切原画')
    buf=io.BytesIO();image.save(buf,format='PNG')
    if len(buf.getvalue())>20*1024*1024:raise ValueError('古画图片超过20MB')
    url='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
    if job.get('requestConfig'):
        config=job['requestConfig']
        if config.get('mediaMode')=='reference_images':
            media=[]
            for ref in job.get('referencePlan',[dict(kind='painting')]):
                target=image
                if ref['kind']=='character':
                    b=ref['box'];w,h=image.size
                    target=image.crop((round(b['x']*w),round(b['y']*h),round((b['x']+b['w'])*w),round((b['y']+b['h'])*h)))
                    if min(target.size)<=0:raise ValueError('人物参考裁切范围无效')
                    scale=max(1,240/min(target.size));target=target.resize((round(target.width*scale),round(target.height*scale)),Image.Resampling.LANCZOS)
                    if max(target.size)>8000 or max(target.size)/min(target.size)>8:raise ValueError('人物参考裁切过窄，请调整标注范围')
                blob=io.BytesIO();target.save(blob,format='PNG')
                if len(blob.getvalue())>20*1024*1024:raise ValueError('参考图超过20MB')
                media.append(dict(type='reference_image',url='data:image/png;base64,'+base64.b64encode(blob.getvalue()).decode()))
        else:media=[dict(type='first_frame',url=url)]
    elif job.get('promptPolicyVersion')!=PROMPT_POLICY_VERSION:
        # Preserve exact legacy behavior when resuming an old queued job.
        config=dict(model=VIDEO_MODEL,parameters=dict(VIDEO_PARAMETERS));media=[dict(type='first_frame',url=url),dict(type='last_frame',url=url)]
    else:config=dict(model=VIDEO_MODEL,parameters=dict(VIDEO_PARAMETERS));media=[dict(type='first_frame',url=url)]
    return dict(model=config['model'],input=dict(prompt=job['prompt'],media=media),parameters=dict(config['parameters']))

class Version(BaseModel):version:int
class VideoRequest(Version):
    sceneId:str
    test:bool=False

class PromptDraft(Version):
    text:str=Field(min_length=1,max_length=19500)
    baseFingerprint:str

class DialogueVideoRequest(Version):
    jobId:str


def install(app,get,save,db,data):
    workers=set();inflight=set();creation_lock=asyncio.Lock()
    def store(job):
        with db() as conn:conn.execute('UPDATE video_jobs SET body=? WHERE id=?',(json.dumps(job,ensure_ascii=False),job['id']))
    def read(jid):
        with db() as conn:row=conn.execute('SELECT body FROM video_jobs WHERE id=?',(jid,)).fetchone()
        if not row:raise HTTPException(404,'视频任务不存在')
        return json.loads(row[0])
    async def download(job,url):
        parsed=urlparse(url)
        if parsed.scheme!='https' or not (parsed.hostname or '').endswith('.aliyuncs.com'):raise ValueError('视频地址不是受支持的阿里云结果地址')
        folder=Path(data())/'videos';folder.mkdir(exist_ok=True)
        final=folder/(job['id']+'.mp4');partial=final.with_suffix('.part')
        # Never forward the model credential to an object-storage download.
        async with httpx.AsyncClient(timeout=120,follow_redirects=False) as client:
            async with client.stream('GET',url) as response:
                response.raise_for_status();size=0
                with partial.open('wb') as out:
                    async for chunk in response.aiter_bytes():
                        size+=len(chunk)
                        if size>150*1024*1024:raise ValueError('视频下载超过大小限制')
                        out.write(chunk)
        if partial.stat().st_size<100:raise ValueError('视频文件为空')
        partial.replace(final);job['videoUrl']=f"/api/projects/{job['projectId']}/videos/{job['id']}/file"
    async def work(job):
        jid=job['id']
        if jid in inflight:return
        inflight.add(jid)
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                if not job.get('remoteId'):
                    job.update(status='submitting',message='正在提交古画与分镜');store(job)
                    body=payload(job,Path(data())/'video-inputs'/(jid+'.png'))
                    try:
                        response=await client.post(endpoint()+'/services/aigc/video-generation/video-synthesis',headers=headers(async_mode=True),json=body)
                        response.raise_for_status();result=response.json()
                    except httpx.TimeoutException:
                        job.update(status='submission_unknown',message='提交响应超时，可能已创建远端任务；不会自动重复提交，请核对服务端记录');store(job);return
                    out=result.get('output',{})
                    if not out.get('task_id'):raise ValueError(str(result.get('code','提交失败'))+'：'+str(result.get('message','未返回任务编号'))[:250])
                    job.update(remoteId=out['task_id'],status='pending',message='已提交，等待视频生成');store(job)
                # Bounded polling; a restart resumes this same remote ID, never creates a duplicate.
                for _ in range(240):
                    try:
                        response=await client.get(endpoint()+'/tasks/'+job['remoteId'],headers=headers());response.raise_for_status();result=response.json()
                    except (httpx.TransportError,httpx.HTTPStatusError):
                        job.update(message='查询暂时失败，将继续查询原任务');store(job);await asyncio.sleep(15);continue
                    out=result.get('output',{});state=out.get('task_status','UNKNOWN')
                    if state=='SUCCEEDED':
                        job.update(status='downloading',message='生成完成，正在保存视频',remoteVideoUrl=out.get('video_url',''));store(job)
                        await download(job,job['remoteVideoUrl'])
                        job.update(status='succeeded',message='视频已保存',usage=result.get('usage',{}));store(job);return
                    if state in ('FAILED','CANCELED','UNKNOWN'):
                        job.update(status='failed',message=str(out.get('code',state))+'：'+str(out.get('message','远端任务未成功'))[:300]);store(job);return
                    job.update(status='running' if state=='RUNNING' else 'pending',message='正在生成古画动画' if state=='RUNNING' else '等待视频生成');store(job)
                    await asyncio.sleep(15)
                job.update(status='paused',message='等待时间较长，稍后可继续查询原任务');store(job)
        except Exception as exc:
            if isinstance(exc,httpx.HTTPStatusError):
                try:body=exc.response.json();message=str(body.get('code',exc.response.status_code))+'：'+str(body.get('message','请求失败'))[:250]
                except ValueError:message='视频接口返回 '+str(exc.response.status_code)
            else:message=str(exc)[:300] if isinstance(exc,ValueError) else type(exc).__name__+'：视频处理未完成'
            job.update(status='download_failed' if job.get('remoteVideoUrl') else 'failed',message=message);store(job)
        finally:inflight.discard(jid)
    def launch(job):
        task=asyncio.create_task(work(job));workers.add(task);task.add_done_callback(workers.discard)
    def valid_approval(p):
        approval=p.get('scriptApproval',{})
        try:return approval.get('fingerprint')==script_fingerprint(p) and approval.get('boardFingerprint')==board_fingerprint(p) and approval.get('promptFingerprints')==all_prompt_fingerprints(p) and approval.get('imageSha256')==hashlib.sha256(image_path(p,data()).read_bytes()).hexdigest()
        except (ValueError,StopIteration):return False
    def all_prompt_fingerprints(p):
        return {s['id']:scene_request_fingerprint(p,s,b,reviewed_prompt(p,s,b)) for s in p['scenes'] for b in p.get('storyboards',[]) if b['sceneId']==s['id']}
    def valid_scene_approval(p,sid):
        approval=p.get('sceneVideoApprovals',{}).get(sid,{})
        try:
            scene,board=selected_scene(p,sid)
            return bool(approval) and approval.get('fingerprint')==scene_fingerprint(p,sid) and approval.get('promptFingerprint')==scene_request_fingerprint(p,scene,board,reviewed_prompt(p,scene,board)) and approval.get('imageSha256')==hashlib.sha256(image_path(p,data()).read_bytes()).hexdigest()
        except (ValueError,HTTPException):return False
    def selected_scene(p,sid):
        scene=next((s for s in p['scenes'] if s['id']==sid),None)
        board=next((s for s in p.get('storyboards',[]) if s['sceneId']==sid),None)
        if not scene or not scene['units'] or not board:raise HTTPException(422,'本场剧本或分镜尚未完成')
        from .workflow import validate_boards
        try:validate_boards([board],dict(p,scenes=[scene],sceneCount=1))
        except ValueError as exc:raise HTTPException(422,str(exc)) from exc
        return scene,board
    @app.post('/api/projects/{pid}/scenes/{sid}/dialogue-video')
    def choose_dialogue_video(pid:str,sid:str,req:DialogueVideoRequest):
        p=get(pid)
        if p['version']!=req.version:raise HTTPException(409,'项目已变化，请重新载入')
        job=read(req.jobId)
        if not any(s['id']==sid for s in p['scenes']) or job['projectId']!=pid or job['sceneId']!=sid:raise HTTPException(422,'只能选择当前项目、本场景的视频')
        if job.get('status')!='succeeded' or job.get('test') or job.get('reviewStatus')=='needs_revision':raise HTTPException(422,'请选择已成功保存且可用的正式视频')
        if not (Path(data())/'videos'/(job['id']+'.mp4')).is_file():raise HTTPException(422,'视频文件不存在')
        p.setdefault('interaction',{}).setdefault('sceneVideos',{})[sid]=job['id']
        return save(p,req.version,'select_dialogue_video',dict(sceneId=sid,jobId=job['id'],selection='user'))
    @app.get('/api/projects/{pid}/scenes/{sid}/video-prompt')
    def preview_prompt(pid:str,sid:str):
        p=get(pid)
        scene=next((s for s in p['scenes'] if s['id']==sid),None)
        board=next((b for b in p.get('storyboards',[]) if b['sceneId']==sid),None)
        if not scene or not board:raise HTTPException(422,'请先完成本场分镜')
        return prompt_preview(p,scene,board)
    @app.post('/api/projects/{pid}/scenes/{sid}/video-prompt')
    def save_prompt(pid:str,sid:str,req:PromptDraft):
        p=get(pid)
        if p['version']!=req.version:raise HTTPException(409,'版本已变化，请重新查看提示词')
        if not scene_fingerprint(p,sid):raise HTTPException(422,'请先完成本场分镜')
        if req.baseFingerprint!=prompt_base(p,sid):raise HTTPException(409,'剧本、分镜或生成设置已变化，请重新整理提示词')
        if not req.text.strip():raise HTTPException(422,'最终视频提示词不能为空')
        p.setdefault('sceneVideoPrompts',{})[sid]=dict(text=req.text,baseFingerprint=req.baseFingerprint)
        p.get('sceneVideoApprovals',{}).pop(sid,None);p.pop('scriptApproval',None)
        return save(p,req.version,'save_video_prompt',dict(sceneId=sid,promptFingerprint=request_fingerprint(req.text)))
    @app.post('/api/projects/{pid}/scenes/{sid}/confirm-video')
    def confirm_scene(pid:str,sid:str,req:Version):
        p=get(pid)
        if p['version']!=req.version:raise HTTPException(409,'版本已变化，请重新载入本场')
        scene,board=selected_scene(p,sid)
        try:
            text=reviewed_prompt(p,scene,board)
            sha=hashlib.sha256(image_path(p,data()).read_bytes()).hexdigest()
        except ValueError as exc:raise HTTPException(422,str(exc)) from exc
        p.setdefault('sceneVideoApprovals',{})[sid]=dict(fingerprint=scene_fingerprint(p,sid),promptFingerprint=scene_request_fingerprint(p,scene,board,text),imageSha256=sha,time=datetime.now(timezone.utc).isoformat())
        return save(p,req.version,'confirm_scene_video',dict(sceneId=sid,trigger='user_button'))
    @app.post('/api/projects/{pid}/script/confirm')
    def confirm(pid:str,req:Version):
        p=get(pid)
        if p['version']!=req.version:raise HTTPException(409,'版本已变化')
        if len(p['scenes'])!=p['sceneCount'] or not p['scenes'] or any(not s['units'] for s in p['scenes']):raise HTTPException(422,'请先完成所有场景剧本')
        try:sha=hashlib.sha256(image_path(p,data()).read_bytes()).hexdigest()
        except ValueError as exc:raise HTTPException(422,str(exc)) from exc
        if p.get('storyboardFingerprint')!=script_fingerprint(p):raise HTTPException(422,'请先完成当前剧本的分镜')
        from .workflow import validate_boards
        try:validate_boards(p.get('storyboards',[]),p)
        except ValueError as exc:raise HTTPException(422,str(exc)) from exc
        try:prompt_fingerprints=all_prompt_fingerprints(p)
        except (ValueError,StopIteration) as exc:raise HTTPException(422,'请先逐场保存最终视频提示词') from exc
        p['scriptApproval']=dict(fingerprint=script_fingerprint(p),boardFingerprint=board_fingerprint(p),promptFingerprints=prompt_fingerprints,imageSha256=sha,time=datetime.now(timezone.utc).isoformat())
        return save(p,req.version,'confirm_video_script',dict(trigger='user_button'))
    @app.get('/api/projects/{pid}/videos')
    def videos(pid:str):
        p=get(pid)
        with db() as conn:jobs=[json.loads(row[0]) for row in conn.execute('SELECT body FROM video_jobs WHERE project=?',(pid,))]
        for job in jobs:
            job['matchesCurrentScript']=job['scopeFingerprint']==scene_fingerprint(p,job['sceneId']) if job.get('scopeFingerprint') else job['scriptFingerprint']==script_fingerprint(p) and job.get('boardFingerprint')==board_fingerprint(p)
            try:
                scene,board=selected_scene(p,job['sceneId'])
                job['matchesCurrentScript']=job['matchesCurrentScript'] and job.get('requestFingerprint')==scene_request_fingerprint(p,scene,board,reviewed_prompt(p,scene,board))
            except (ValueError,HTTPException):job['matchesCurrentScript']=False
            job['selectedForDialogue']=p.get('interaction',{}).get('sceneVideos',{}).get(job.get('sceneId'))==job['id']
            job.pop('remoteVideoUrl',None)
        return dict(jobs=sorted(jobs,key=lambda j:j['time'],reverse=True),remaining=remaining(data()),limit=LIMIT,scriptConfirmed=valid_approval(p),storyboardCurrent=p.get('storyboardFingerprint')==script_fingerprint(p))
    @app.post('/api/projects/{pid}/videos')
    async def create(pid:str,req:VideoRequest):
        async with creation_lock:
            p=get(pid)
            if p['version']!=req.version:raise HTTPException(409,'版本已变化')
            local_approved=valid_scene_approval(p,req.sceneId)
            if not (local_approved or valid_approval(p)):raise HTTPException(422,'请先保存并审核本场最终视频提示词，再确认生成')
            if not local_approved and p.get('storyboardFingerprint')!=script_fingerprint(p):raise HTTPException(422,'请先为当前剧本生成分镜')
            scene,board=selected_scene(p,req.sceneId)
            try:prompt=reviewed_prompt(p,scene,board)
            except ValueError as exc:raise HTTPException(422,str(exc)) from exc
            if len(prompt)>19500:raise HTTPException(422,'剧本与分镜过长，请精简后再生成，避免接口截断')
            image=image_path(p,data());image_hash=hashlib.sha256(image.read_bytes()).hexdigest()
            request_hash=scene_request_fingerprint(p,scene,board,prompt)
            jid=hashlib.sha256((pid+req.sceneId+scene_fingerprint(p,req.sceneId)+request_hash+image_hash+str(req.test)).encode()).hexdigest()[:24]
            with db() as conn:row=conn.execute('SELECT body FROM video_jobs WHERE id=?',(jid,)).fetchone()
            if row:return json.loads(row[0])
            headers()  # Validate configuration before reserving a paid attempt.
            job=dict(id=jid,projectId=pid,sceneId=req.sceneId,title=scene['title'],test=req.test,status='queued',message='准备提交',time=datetime.now(timezone.utc).isoformat(),prompt=prompt,duration=VIDEO_PARAMETERS['duration'],resolution=VIDEO_PARAMETERS['resolution'],model=VIDEO_MODEL,scriptFingerprint=script_fingerprint(p),boardFingerprint=board_fingerprint(p),imageSha256=image_hash,sourceVersion=p['version'])
            job['scriptSnapshot']=scene
            job['storyboardSnapshot']=board
            job['promptPolicyVersion']=PROMPT_POLICY_VERSION
            job['requestFingerprint']=request_hash
            job['requestConfig']=dict(model=VIDEO_MODEL,parameters=dict(VIDEO_PARAMETERS),mediaMode=MEDIA_MODE)
            job['referencePlan']=reference_plan(p,scene,board)
            job['scopeFingerprint']=scene_fingerprint(p,req.sceneId)
            payload(job,image)  # Validate the full painting before reserving quota.
            folder=Path(data())/'video-inputs';folder.mkdir(exist_ok=True)
            with Image.open(image) as im:ImageOps.exif_transpose(im).convert('RGB').save(folder/(jid+'.png'))
            job['slot']=reserve(data(),jid)
            with db() as conn:conn.execute('INSERT INTO video_jobs VALUES (?,?,?)',(jid,pid,json.dumps(job,ensure_ascii=False)))
            launch(job);return job
    @app.post('/api/projects/{pid}/videos/{jid}/refresh')
    async def refresh(pid:str,jid:str):
        job=read(jid)
        if job['projectId']!=pid:raise HTTPException(404,'视频不存在')
        if job.get('remoteId') and job['status']!='succeeded':launch(job)
        return job
    @app.get('/api/projects/{pid}/videos/{jid}/file')
    def file(pid:str,jid:str):
        job=read(jid)
        if job['projectId']!=pid or job['status']!='succeeded':raise HTTPException(404,'视频尚未生成')
        path=Path(data())/'videos'/(job['id']+'.mp4')
        if not path.is_file():raise HTTPException(404,'视频文件不存在')
        return FileResponse(path,media_type='video/mp4',filename=job['id']+'.mp4',content_disposition_type='inline')
    async def recover():
        with db() as conn:jobs=[json.loads(r[0]) for r in conn.execute('SELECT body FROM video_jobs')]
        for job in jobs:
            if job['status'] in ('queued','submitting') and not job.get('remoteId'):
                job.update(status='submission_unknown',message='服务重启，提交状态待核对；未重复提交');store(job)
            elif job.get('remoteId') and job['status'] in ('pending','running','downloading'):launch(job)
    async def shutdown():
        for task in workers:task.cancel()
        if workers:await asyncio.gather(*workers,return_exceptions=True)
    app.router.add_event_handler('startup',recover)
    app.router.add_event_handler('shutdown',shutdown)
