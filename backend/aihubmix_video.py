"""AIHubMix /ai/v1/videos asynchronous text-to-video contract."""
import os
from urllib.parse import urljoin,urlparse,quote
import httpx

class WanAdapter:
    def profile(self):return dict(model='wan3.0-video',resolution='480P',duration=5,audio=True,estimatedCny=5)
    def validate_configuration(self):
        if not os.getenv('AIHUBMIX_API_KEY'):raise ValueError('未配置 AIHubMix 密钥')
    def base(self):return os.getenv('AIHUBMIX_VIDEO_BASE_URL','https://aihubmix.com/ai/v1').rstrip('/')
    def headers(self):
        self.validate_configuration()
        return {'Authorization':'Bearer '+os.environ['AIHUBMIX_API_KEY']}
    def build_request(self,job,image_path):
        self.validate_configuration()
        from .video import payload
        native=payload(job,image_path)
        params=native['parameters']
        references=[dict(type='image_url',url=item['url']) for item in native['input']['media']]
        if len(references)>10:raise ValueError('Wan 3.0 最多支持10张参考图，请减少参与人物')
        body=dict(model='wan3.0-video',prompt=job['prompt'],resolution=str(params.get('resolution','480P')).lower(),duration=params.get('duration',5),aspect_ratio=params.get('ratio','adaptive'),generate_audio=params.get('audio',True),extra=dict(prompt_extend=params.get('prompt_extend',False),watermark=False))
        if references:body['input_references']=references
        if 'seed' in params:body['seed']=params['seed']
        return body
    async def submit(self,job,body):
        async with httpx.AsyncClient(timeout=120) as client:
            r=await client.post(self.base()+'/videos',headers=self.headers(),json=body);r.raise_for_status();value=r.json()
        remote=value.get('id')
        if not isinstance(remote,str) or not remote:raise ValueError('视频接口未返回任务编号，不能自动重试')
        return remote
    async def inspect(self,job):
        async with httpx.AsyncClient(timeout=60) as client:
            r=await client.get(self.base()+'/videos/'+quote(job['remoteId'],safe=''),headers=self.headers());r.raise_for_status();v=r.json()
        state=str(v.get('status','')).lower()
        outputs=v.get('output') or []
        url=next((item.get('content_url') for item in outputs if isinstance(item,dict) and item.get('content_url')),None) if isinstance(outputs,list) else None
        error=v.get('error')
        message=error.get('message','视频生成失败') if isinstance(error,dict) else str(error or '正在生成视频')
        if state=='completed' and not url:raise ValueError('任务完成但未返回视频下载地址')
        return dict(status='succeeded' if state=='completed' else 'failed' if state in ('failed','cancelled') else 'running',url=url,remoteId=job['remoteId'],message=message,providerCode=error.get('code') if isinstance(error,dict) else None)
    async def download(self,job,result):
        url=urljoin(self.base()+'/',result.get('url') or '')
        if not result.get('url'):raise ValueError('缺少视频下载地址')
        parsed=urlparse(url);base=urlparse(self.base())
        if parsed.scheme!='https' or parsed.netloc!=base.netloc:raise ValueError('下载地址不属于视频服务，未向未知主机发送密钥')
        async with httpx.AsyncClient(timeout=180,follow_redirects=False) as client:
            r=await client.get(url,headers=self.headers())
            if r.is_redirect:
                target=urljoin(url,r.headers['location'])
                if urlparse(target).scheme!='https':raise ValueError('下载跳转地址无效')
                headers=self.headers() if urlparse(target).netloc==base.netloc else {}
                r=await client.get(target,headers=headers)
            r.raise_for_status();return r.content
