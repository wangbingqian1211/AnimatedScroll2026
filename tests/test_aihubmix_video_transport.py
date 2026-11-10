import unittest,os,json
from unittest.mock import patch
import httpx
from backend.aihubmix_video import WanAdapter

class TransportTests(unittest.IsolatedAsyncioTestCase):
 async def test_submit_poll_download(self):
  calls=[]
  def handle(req):
   calls.append(req)
   self.assertEqual(req.headers.get('authorization'),'Bearer test-only')
   if req.method=='POST':
    self.assertEqual(str(req.url),'https://aihubmix.com/ai/v1/videos')
    self.assertEqual(json.loads(req.content),{'model':'wan3.0-video','prompt':'test'})
    return httpx.Response(200,json={'id':'job1','status':'pending'})
   if req.url.path.endswith('/job1'):return httpx.Response(200,json={'id':'job1','status':'completed','output':[{'content_url':'https://aihubmix.com/ai/v1/content/file1'}]})
   return httpx.Response(200,content=b'video')
  real=httpx.AsyncClient
  with patch.dict(os.environ,{'AIHUBMIX_API_KEY':'test-only'}),patch('backend.aihubmix_video.httpx.AsyncClient',side_effect=lambda **kw:real(transport=httpx.MockTransport(handle),**kw)):
   adapter=WanAdapter();job={'prompt':'test'}
   job['remoteId']=await adapter.submit(job,dict(model='wan3.0-video',prompt='test'))
   result=await adapter.inspect(job)
   self.assertEqual(result['status'],'succeeded')
   self.assertEqual(await adapter.download(job,result),b'video')
  self.assertEqual(len(calls),3)
 async def test_no_key_sent_to_unknown_download_host(self):
  with self.assertRaises(ValueError):await WanAdapter().download({},dict(url='https://untrusted.example/video'))

class RequestMappingTests(unittest.TestCase):
 def test_official_gateway_schema(self):
  native=dict(input=dict(media=[dict(type='reference_image',url='data:image/png;base64,YQ==')]),parameters=dict(resolution='480P',duration=5,ratio='adaptive',audio=True,prompt_extend=False))
  with patch.dict(os.environ,{'AIHUBMIX_API_KEY':'test-only'}),patch('backend.video.payload',return_value=native):
   body=WanAdapter().build_request({'prompt':'test'},None)
  self.assertEqual(body['resolution'],'480p')
  self.assertEqual(body['duration'],5)
  self.assertEqual(body['aspect_ratio'],'adaptive')
  self.assertEqual(body['input_references'][0]['type'],'image_url')
  self.assertTrue(body['generate_audio'])
  self.assertNotIn('input',body)
  self.assertNotIn('parameters',body)
