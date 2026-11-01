"""Remove a visible person and clear structured references, retaining authored text."""
import copy


def remove_person(project, character_id='', annotation_id=''):
    p=copy.deepcopy(project)
    removed={a['id'] for a in p['annotations'] if (character_id and a.get('characterId')==character_id) or a['id']==annotation_id}
    if annotation_id and not character_id:
        a=next(a for a in p['annotations'] if a['id']==annotation_id)
        candidate=a.get('characterId','')
        if candidate and not any(x.get('characterId')==candidate and x['id'] not in removed for x in p['annotations']):
            character_id=candidate
    p['annotations']=[a for a in p['annotations'] if a['id'] not in removed]
    p['characters']=[c for c in p['characters'] if c['id']!=character_id]
    for key in ('observations','matches'):
        p[key]=[v for v in p.get(key,[]) if v.get('annotationId') not in removed and (not character_id or v.get('characterId')!=character_id)]
    p['personRelations']=[r for r in p.get('personRelations',[]) if character_id not in (r['fromId'],r['toId'])]
    for event in p.get('historicalEvents',[]):
        event['characterIds']=[c for c in event.get('characterIds',[]) if c!=character_id]
    for scene in p['scenes']:
        scene['characterIds']=[c for c in scene.get('characterIds',[]) if c!=character_id]
        for unit in scene.get('units',[]):
            if character_id and unit.get('speakerId')==character_id:unit['speakerId']=''
            for ref in unit.get('references',[]):
                if ref.get('annotationId') in removed:ref['annotationId']=''
    for board in p.get('storyboards',[]):
        for shot in board.get('shots',[]):
            shot['characterIds']=[c for c in shot.get('characterIds',[]) if c!=character_id]
            for line in shot.get('dialogue',[]):
                if character_id and line.get('speakerId')==character_id:line['speakerId']=''
    interaction=p.get('interaction',{})
    interaction['guideAnnotationIds']=[a for a in interaction.get('guideAnnotationIds',[]) if a not in removed]
    for chapter in interaction.get('chapters',[]):
        chapter['questions']=[q for q in chapter.get('questions',[]) if q.get('personId')!=character_id]
    reference=p.get('identityReference',{})
    reference['annotations']=[a for a in reference.get('annotations',[]) if a['id'] not in removed]
    return p
