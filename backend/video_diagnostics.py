"""Small, credential-free video failure diagnostics."""
import re
import httpx

def clean(value):
    text=str(value or '')
    text=re.sub(r'data:[^\s"\']+', '[image omitted]', text)
    text=re.sub(r'(?i)bearer\s+\S+|sk-[A-Za-z0-9_-]+','[credential omitted]',text)
    return text[:1600]

def failure(exc):
    result=dict(errorType=type(exc).__name__)
    if isinstance(exc,httpx.HTTPStatusError):
        response=exc.response;result['httpStatus']=response.status_code
        result['endpoint']=response.request.url.path
        try:
            data=response.json()
            data=data if isinstance(data,dict) else {}
            error=data.get('error',{})
            if isinstance(error,dict):
                result['providerCode']=clean(error.get('code') or data.get('code'))
                result['providerMessage']=clean(error.get('message') or data.get('message'))
            else:result['providerMessage']=clean(error)
            if isinstance(data,dict):result['traceId']=clean(data.get('tid') or data.get('request_id') or response.headers.get('x-request-id'))
        except ValueError:result['providerMessage']='接口返回非 JSON 错误响应'
    else:result['providerMessage']='网络请求未完成' if isinstance(exc,httpx.TransportError) else clean(str(exc))
    return result


def record(job, details):
    import logging
    import json
    from datetime import datetime, timezone
    details=dict(details, timestamp=datetime.now(timezone.utc).isoformat())
    job['diagnostics']=details
    logging.getLogger('uvicorn.error').error('video_failure job=%s details=%s', job['id'], json.dumps(details, ensure_ascii=True))
