import unittest
import httpx
from backend.video_diagnostics import failure, clean

class VideoDiagnosticsTests(unittest.TestCase):
    def test_rejection_details(self):
        request=httpx.Request('POST','https://aihubmix.com/ai/v1/videos',headers={'Authorization':'Bearer secret'})
        response=httpx.Response(403,request=request,json={'error':{'code':'forbidden','message':'model unavailable'},'request_id':'trace-123'})
        result=failure(httpx.HTTPStatusError('failed',request=request,response=response))
        self.assertEqual(result['httpStatus'],403)
        self.assertEqual(result['providerCode'],'forbidden')
        self.assertEqual(result['providerMessage'],'model unavailable')
        self.assertEqual(result['traceId'],'trace-123')
        self.assertNotIn('secret',str(result))

    def test_unexpected_error_body(self):
        for body in ([], '<html>forbidden</html>'):
            request=httpx.Request('POST','https://aihubmix.com/ai/v1/videos')
            response=httpx.Response(403,request=request,json=body) if isinstance(body,list) else httpx.Response(403,request=request,text=body)
            self.assertEqual(failure(httpx.HTTPStatusError('failed',request=request,response=response))['httpStatus'],403)

    def test_redaction(self):
        result=clean('Bearer private-key sk-secret data:image/png;base64,ABCDEF')
        for secret in ('private-key','sk-secret','ABCDEF'):
            self.assertNotIn(secret,result)

if __name__=='__main__':unittest.main()
