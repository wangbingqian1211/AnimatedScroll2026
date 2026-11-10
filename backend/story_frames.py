"""Qwen story preview images, explicitly generated and selected by the author."""
import base64,io,json,uuid
from pathlib import Path
from urllib.parse import urlparse
import httpx
from PIL import Image
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .dashscope_video import WanAdapter

class Generate(BaseModel):
    prompt:str
class Select(BaseModel):
    first:str
    last:str=''

def reference_content(p,sid,data):
    from .video import shot_inputs,payload
    inputs,path=shot_inputs(p,sid,data)
    from .video_generation import request_config
    native=payload(dict(prompt='',referencePlan=inputs['references'],requestConfig=request_config()),path)
    images=native['input']['media']
    content=[dict(image=images[0]['url'])]
    names=[r['name'] for r in inputs['references'][1:]]
    # Qwen 3.0 accepts up to three images. Pack all selected character crops
    # into a separate reference sheet rather than silently dropping characters.
    if len(images)>1:
        sheet=Image.new('RGB',(384*min(4,len(names)),512*((len(names)+3)//4)),(240,237,227))
        for i,item in enumerate(images[1:]):
            crop=Image.open(io.BytesIO(base64.b64decode(item['url'].split(',',1)[1]))).convert('RGB')
            crop.thumbnail((360,480))
            sheet.paste(crop,((i%4)*384+(384-crop.width)//2,(i//4)*512+(512-crop.height)//2))
        out=io.BytesIO();sheet.save(out,format='PNG')
        content.append(dict(image='data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()))
    instruction='图1是原画，只参考画风、笔触、设色、建筑与器物，不照搬人物数量、动作或原画剧情。'
    if names:instruction+='图2是本镜人物截图参考板，按从左到右、从上到下依次为：'+ '、'.join(names)+'。只使用这些人物，保持其面貌与衣冠；忽略截图边缘混入的其他人物或手臂，不复制原有受控姿态。参考板不可出现在最终画面中。'
    instruction+='根据当前剧情重新构图，未选人物不得出镜。'
    return content,instruction,names

def install(app,get,save,data):
    def folder(pid,sid):
        get(pid)
        if not all(v and all(c.isalnum() or c in '-_' for c in v) for v in (pid,sid)):raise HTTPException(422,'分镜编号无效')
        root=Path(data())/'story-frames'/pid/sid
        root.mkdir(parents=True,exist_ok=True)
        return root
    @app.get('/api/projects/{pid}/storyboards/{sid}/frames')
    def listing(pid:str,sid:str):
        return [json.loads(f.read_text(encoding='utf-8')) for f in folder(pid,sid).glob('*.json')]
    @app.post('/api/projects/{pid}/storyboards/{sid}/frames')
    async def generate(pid:str,sid:str,req:Generate):
        root=folder(pid,sid)
        if not req.prompt.strip() or len(req.prompt)>18000:raise HTTPException(422,'请填写预览图描述，最多18000字')
        adapter=WanAdapter()
        try:references,instruction,names=reference_content(get(pid),sid,data())
        except (ValueError,KeyError) as exc:raise HTTPException(422,'请先确认本镜人物和画中身份：'+str(exc)) from exc
        submitted_prompt=instruction+'\n剧情要求：'+req.prompt
        body=dict(model='qwen-image-3.0',input=dict(messages=[dict(role='user',content=references+[dict(text=submitted_prompt)])]),parameters=dict(prompt_extend=True))
        try:
            async with httpx.AsyncClient(timeout=240,follow_redirects=False) as client:
                response=await client.post(adapter.base()+'/services/aigc/multimodal-generation/generation',headers=adapter.headers(),json=body)
                response.raise_for_status()
                result=response.json()
                content=result.get('output',{}).get('choices',[{}])[0].get('message',{}).get('content',[])
                url=next((v['image'] for v in content if v.get('image')),None)
                if not url:raise ValueError(result.get('message') or '图片接口未返回图片')
                parsed=urlparse(url)
                if parsed.scheme!='https' or not (parsed.hostname or '').endswith('.aliyuncs.com'):raise ValueError('图片下载地址无效')
                image=await client.get(url);image.raise_for_status()
                if len(image.content)>40*1024*1024:raise ValueError('图片过大')
            key=uuid.uuid4().hex
            with Image.open(io.BytesIO(image.content)) as im:im.convert('RGB').save(root/(key+'.png'))
            record=dict(id=key,prompt=submitted_prompt,referenceNames=names,referenceCount=len(references),url=f'/api/projects/{pid}/storyboards/{sid}/frames/{key}.png')
            (root/(key+'.json')).write_text(json.dumps(record,ensure_ascii=False),encoding='utf-8')
            return record
        except (httpx.HTTPError,ValueError) as exc:
            from .video_diagnostics import failure
            raise HTTPException(502,failure(exc).get('providerMessage') or '预览图生成失败；未自动重试') from exc
    @app.get('/api/projects/{pid}/storyboards/{sid}/frames/{key}.png')
    def image(pid:str,sid:str,key:str):
        if len(key)!=32 or not all(c in '0123456789abcdef' for c in key):raise HTTPException(404)
        path=folder(pid,sid)/(key+'.png')
        if not path.exists():raise HTTPException(404)
        return FileResponse(path)
    @app.put('/api/projects/{pid}/storyboards/{sid}/frames-selection')
    def select(pid:str,sid:str,req:Select):
        root=folder(pid,sid);frames=[]
        if req.last and not req.first:raise HTTPException(422,'请先选择首帧')
        for kind,key in [('first_frame',req.first),('last_frame',req.last)]:
            if not key:continue
            if len(key)!=32 or not all(c in '0123456789abcdef' for c in key):raise HTTPException(422,'图片编号无效')
            path=root/(key+'.png')
            if not path.exists():raise HTTPException(422,'预览图不存在')
            frames.append(dict(type=kind,url='data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()))
        p=get(pid);version=p['version']
        p['workspace'].setdefault('media',{}).setdefault(sid,{})['storyFrames']=frames
        return save(p,version,'studio:story-frames',dict(storyboardId=sid))
