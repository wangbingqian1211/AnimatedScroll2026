"""Official Bailian Wan asynchronous video transport."""
import os
import re
from urllib.parse import quote, urlparse
import httpx

class WanAdapter:
    def profile(self):
        return dict(model='wan3.0-video',resolution='480P',duration=5,audio=True,estimatedCny=5)

    def base(self):
        workspace=os.getenv('DASHSCOPE_WORKSPACE_ID','')
        region=os.getenv('DASHSCOPE_REGION','cn-beijing')
        if not re.fullmatch(r'[A-Za-z0-9-]+',workspace):
            raise ValueError('请配置百炼业务空间 ID')
        if region not in ('cn-beijing','ap-southeast-1','ap-northeast-1','eu-central-1','us-east-1','cn-hongkong'):
            raise ValueError('百炼地域配置无效')
        return f'https://{workspace}.{region}.maas.aliyuncs.com/api/v1'

    def validate_configuration(self):
        if not os.getenv('DASHSCOPE_API_KEY'):
            raise ValueError('未配置 DASHSCOPE_API_KEY')
        self.base()

    def headers(self,async_mode=False):
        self.validate_configuration()
        result={'Authorization':'Bearer '+os.environ['DASHSCOPE_API_KEY']}
        if async_mode:result['X-DashScope-Async']='enable'
        return result

    def build_request(self,job,image_path):
        self.validate_configuration()
        from .video import payload
        body=payload(job,image_path)
        if len(body['input']['media'])>10:raise ValueError('最多支持10张参考图')
        body['parameters']['watermark']=False
        return body

    async def submit(self,job,body):
        async with httpx.AsyncClient(timeout=120) as client:
            response=await client.post(self.base()+'/services/aigc/video-generation/video-synthesis',headers=self.headers(True),json=body)
            response.raise_for_status()
            value=response.json()
        remote=value.get('output',{}).get('task_id')
        if not isinstance(remote,str) or not remote:
            from .video_diagnostics import clean
            raise ValueError(clean(value.get('message') or '官方接口未返回任务编号，提交结果待核实'))
        return remote

    async def inspect(self,job):
        async with httpx.AsyncClient(timeout=60) as client:
            response=await client.get(self.base()+'/tasks/'+quote(job['remoteId'],safe=''),headers=self.headers())
            response.raise_for_status()
            value=response.json()
        output=value.get('output',{})
        state=output.get('task_status','UNKNOWN')
        if state not in ('PENDING','RUNNING','SUCCEEDED','FAILED','CANCELED'):
            raise ValueError('官方任务状态未知，请继续查询原任务')
        url=output.get('video_url')
        if state=='SUCCEEDED' and not url:raise ValueError('任务完成但未返回视频地址')
        return dict(status='succeeded' if state=='SUCCEEDED' else 'failed' if state in ('FAILED','CANCELED') else 'running',url=url,remoteId=job['remoteId'],message=output.get('message') or value.get('message') or ('视频生成失败' if state in ('FAILED','CANCELED') else '正在生成视频'),providerCode=output.get('code') or value.get('code'),traceId=value.get('request_id'))

    async def download(self,job,result):
        url=result.get('url') or ''
        parsed=urlparse(url)
        if parsed.scheme!='https' or not (parsed.hostname or '').endswith('.aliyuncs.com'):
            raise ValueError('视频下载地址不是受支持的阿里云地址')
        # Signed object-storage URLs do not need the model API key.
        async with httpx.AsyncClient(timeout=180,follow_redirects=False) as client:
            response=await client.get(url)
            response.raise_for_status()
            return response.content
