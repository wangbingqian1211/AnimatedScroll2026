"""Keep narrative clue drafts grounded in the current plot, without model calls."""
import copy
import re
from . import workspace as ws

def sync(before, project, force=False):
    w=ws.ensure(project)
    old=before.get('workspace',{}).get('entities',{}) if before else {}
    for plot in list(w['entities'].values()):
        if plot['kind']!='plot':continue
        children=[r for r in w['entities'].values() if r['kind']=='clue' and r['state']!='deleted' and r['draft'].get('type')=='narrative' and r['draft'].get('plotIds')==[plot['id']]]
        if plot['state']=='deleted':
            for child in children:child['state']='deleted'
            continue
        prior=old.get('plot:'+plot['id'],{}).get('draft',{})
        d=plot['draft']
        if not force and all(prior.get(k)==d.get(k) for k in ('title','body','characterIds')):continue
        # A generator that already updated children owns their segmentation.
        if not force and children and any(old.get('clue:'+r['id'],{}).get('draft')!=r['draft'] for r in children):continue
        body=d.get('body','').strip()
        if not body:continue
        sentences=[v.strip() for v in re.findall(r'.+?(?:[。！？](?:（[^）]*）)?|$)',body,re.S) if v.strip()]
        count=min(max(len(children),1),len(sentences))
        if not children:
            from .studio import add_clue
            cid=add_clue(w,dict(name=d.get('title','剧情'),content=body),'narrative',[plot['id']],source='plot:'+plot['id'])
            children=[w['entities']['clue:'+cid]]
        active=[]
        for i,child in enumerate(children):
            if i>=count:
                child['state']='deleted'
                continue
            text=''.join(sentences[len(sentences)*i//count:len(sentences)*(i+1)//count])
            value=copy.deepcopy(child['draft'])
            value.update(name=d.get('title','剧情')+(' · '+str(i+1) if count>1 else ''),content=text,summary='',characterIds=copy.deepcopy(d.get('characterIds',[])))
            child['draft']=ws.narrative_draft(value,copy.deepcopy(child['draft']))
            child['draftRefs']=ws.refs_for(w,child)
            child['generatedFrom']='plot:'+plot['id']
            active.append(child['id'])
        d['clueIds']=active
