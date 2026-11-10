import json
import unittest
from unittest.mock import patch
import httpx
from backend.dashscope_video import WanAdapter

class OfficialTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_submit_poll_download(self):
        adapter=WanAdapter()
        calls=[]
        def handler(request):
            calls.append(request)
            if request.method=='POST':
                self.assertEqual(request.headers['X-DashScope-Async'],'enable')
                self.assertTrue(request.url.path.endswith('/video-generation/video-synthesis'))
                self.assertEqual(json.loads(request.content)['parameters']['resolution'],'480P')
                return httpx.Response(200,json={'output':{'task_id':'task-1'}})
            if '/tasks/' in request.url.path:
                return httpx.Response(200,json={'output':{'task_status':'SUCCEEDED','video_url':'https://result.oss-cn-beijing.aliyuncs.com/video.mp4'}})
            self.assertNotIn('authorization',request.headers)
            return httpx.Response(200,content=b'video')
        real=httpx.AsyncClient
        with patch.dict('os.environ',{'DASHSCOPE_API_KEY':'test-key','DASHSCOPE_WORKSPACE_ID':'test-space','DASHSCOPE_REGION':'cn-beijing'}), patch('backend.dashscope_video.httpx.AsyncClient',side_effect=lambda **kw:real(transport=httpx.MockTransport(handler),**kw)):
            self.assertEqual(await adapter.submit({}, {'parameters':{'resolution':'480P'}}),'task-1')
            result=await adapter.inspect({'remoteId':'task-1'})
            self.assertEqual(result['status'],'succeeded')
            self.assertEqual(await adapter.download({},result),b'video')
            self.assertEqual(calls[0].url.host,'test-space.cn-beijing.maas.aliyuncs.com')

    async def test_failed_task_details(self):
        real=httpx.AsyncClient
        def handler(request):
            return httpx.Response(200,json={'request_id':'trace-1','output':{'task_status':'FAILED','code':'InvalidParameter','message':'invalid input'}})
        with patch.dict('os.environ',{'DASHSCOPE_API_KEY':'test','DASHSCOPE_WORKSPACE_ID':'test-space'}), patch('backend.dashscope_video.httpx.AsyncClient',side_effect=lambda **kw:real(transport=httpx.MockTransport(handler),**kw)):
            result=await WanAdapter().inspect({'remoteId':'task-1'})
            self.assertEqual(result['status'],'failed')
            self.assertEqual(result['providerCode'],'InvalidParameter')
            self.assertEqual(result['traceId'],'trace-1')

    def test_native_reference_payload(self):
        from pathlib import Path
        import tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ',{'DASHSCOPE_API_KEY':'test','DASHSCOPE_WORKSPACE_ID':'test-space'}):
            path=Path(folder)/'painting.png'
            Image.new('RGB',(240,240)).save(path)
            job=dict(prompt='图1古画',requestConfig=dict(model='wan3.0-video',mediaMode='reference_images',parameters=dict(resolution='480P',duration=5,audio=True,ratio='adaptive')))
            body=WanAdapter().build_request(job,path)
            self.assertEqual(body['input']['media'][0]['type'],'reference_image')
            self.assertEqual(body['parameters']['resolution'],'480P')
            self.assertTrue(body['parameters']['audio'])

if __name__=='__main__':unittest.main()
