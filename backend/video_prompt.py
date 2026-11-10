"""Deterministic director brief and checks, based on the published Wan guides."""
import re

GUIDE_URL='https://help.aliyun.com/zh/model-studio/text-to-video-prompt'
POLICY='story-director-v6'


def compile(inputs,duration,style):
    shot=inputs['shot'];refs=inputs['references']
    dialogue=shot.get('dialogue','').strip()
    sound=('人物对白（逐句按角色说出，不添加其他台词）：'+dialogue+'。无旁白、无背景音乐。') if dialogue else '无台词、无旁白、无背景音乐。'
    cast=[]
    for person in inputs['people']:
        ref=next((r for r in refs if r.get('characterId')==person['id']),None)
        if ref:cast.append(f"{person['name']}：仅参考{ref['label']}中的面貌、衣冠与身份，姿态按本镜情节重新设计")
    clue=inputs['clue']
    story=clue.get('summary') or clue.get('name','')
    # Old drafts copied the painting's later events and fixed poses. Do not feed
    # those full prose prompts back into the new story-first brief.
    def direction(value):
        parts=re.split(r'[。；\n]',value or '')
        return '；'.join(part for part in parts if part.strip() and not re.search(r'原画|原图|原有|原位置|位置不变|数量不变|不换位|保持原|相对静止|依原|依照原',part))
    early_petition='朱云' in (story+clue.get('name','')) and '直谏' in clue.get('name','')
    boundary=('本镜是朱云当廷直谏，尚未发生押解和折槛：朱云双手自由，站立进言；不得出现侍卫、抓握手腕、反剪双手、捆绑、拖拽或折断栏杆。' if early_petition else '只表现本镜情节中已经发生的事件。未被本镜提及的押解、捆绑、冲突、破坏与后续人物不得从参考画复制进来。')
    action=direction(shot.get('action',''))
    start=direction(shot.get('startFrame',''))
    end=direction(shot.get('endFrame',''))
    if early_petition:
        action='朱云双手自由，面向皇帝自然抬手进言；其他出场人物倾听，不发生抓捕或肢体控制'
        start='朱云自由站立，面对在座的皇帝，栏杆完整，无侍卫入镜'
        end='朱云完成进言手势，双手保持自由，画面停留在听谏的时刻'
    mapping='；'.join(r['label']+'＝'+r['name'] for r in refs)
    return (style+f'\n生成单镜头，{duration}秒，一镜到底。按当前故事重新绘制场景、人物站位和动作。'
            '\n参考用途：所有图片仅为参考素材，均不是首帧或尾帧。图1只参考建筑、器物、笔触和设色，不复制其中的剧情、人物数量、人物姿态或构图。人物裁切仅参考外貌与服饰，不复制被控制的姿态、抓握人物的手或周边人物。'
            '\n参考索引：'+mapping+'\n允许出场的人物：'+('；'.join(cast) or '无人出镜，仅表现场景')+
            '\n未选人物不出镜；不得为填满原画构图而保留旁观者或侍卫。根据剧情重新安排景别、站位与空间，不拼贴参考图、不分屏、不加边框。'
            '\n本镜情节（决定画面内容的首要依据）：'+story+
            '\n事件边界：'+boundary+
            '\n动作：'+(action or '以本镜情节为依据设计一个明确的可见动作')+
            '\n运镜：'+(direction(shot.get('camera','')) or '固定镜头，聚焦本镜人物')+
            f"\n节奏：0–1秒，{start or '建立符合当前情节的起始画面'}；1–{max(2,duration-1)}秒，完成上述主要动作；末1秒，{end or '停留在当前事件结束的状态，不进入下一情节'}。"+
            '\n绘画与质感：保留古画笔触、设色和材质；构图按当前剧情重新安排。'+
            '\n声音：'+sound+'无字幕、无现代物件。人物形象与原画画风保持一致，剧情和动作以本镜为准。')


def audit(inputs,text,duration):
    shot=inputs['shot'];warnings=[];errors=[]
    if len(text)>19500:errors.append('完整提示词超过19500字符，请缩短后再提交')
    missing=[label for field,label in (('action','具体动作'),('camera','运镜'),('startFrame','起始画面'),('endFrame','结束画面')) if not shot.get(field,'').strip()]
    if missing:warnings.append('分镜尚缺少'+ '、'.join(missing)+'；建议补充后再生成')
    if not all(r['label'] in text for r in inputs['references']):warnings.append('最终文本未完整对应参考图编号，人物可能被模型重新设计')
    if inputs['people'] and any(not p.get('boxes') for p in inputs['people']):errors.append('出场人物缺少已确认的画中对应')
    if re.search(r'固定.{0,6}或|或.{0,6}(?:推近|平移)',shot.get('camera','')):warnings.append('运镜仍有备选方案，请在固定镜头和移动镜头之间明确一种')
    if re.search(r'固定机位',shot.get('camera','')) and re.search(r'平移|移动机位',shot.get('camera','')):warnings.append('运镜同时写了固定机位和平移，请统一镜头运动')
    if re.search(r'不换位|保持原画姿态|仅有.{0,8}衣纹',shot.get('prompt','')+shot.get('action','')) and re.search(r'前行|迈步|走向|起身|站起',shot.get('endFrame','')):warnings.append('主体要求保持姿态，结束画面却出现位移或起身，请统一起止动作')
    if re.search(r'仅有.{0,8}衣纹|仅作.{0,8}衣纹',shot.get('action','')):warnings.append('当前主要是衣纹微动，历史情节依靠外部讲解；若希望演出剧情，请明确一个可见的主要动作')
    durations={int(v) for v in re.findall(r'(?<![\d–—\-])(?<![\d])(?:独立|时长|共|总计|持续)?\s*(\d+)\s*秒(?:分镜|视频|短片|钟)?',shot.get('prompt',''))}
    if durations and any(v!=duration for v in durations):warnings.append(f'原分镜包含不同的时长，请与本次{duration}秒设置统一')
    if not re.search(r'单镜头|一镜到底|single shot',text,re.I):warnings.append('未明确单镜头，可能出现额外切镜')
    if not shot.get('dialogue','').strip() and not re.search(r'无台词|无对白|No dialogue',text,re.I):warnings.append('未明确禁止台词，模型可能自行配音')
    if not re.search(r'笔触|绘画|画风|水墨|设色',text):warnings.append('缺少原画风格与材质约束')
    positive=re.sub(r'(?:不|禁止|避免|不要|无)[^，。；\n]{0,25}','',text)
    if re.search(r'真人实拍|照片级真实|3D渲染|现代卡通',positive,re.I):warnings.append('提示词可能要求改变原画风格，请检查真人化或3D描述')
    if re.search(r'不[动移]|静止不动',shot.get('prompt','')) and re.search(r'抬手|起身|走向|行走|转身',shot.get('action','')):warnings.append('完整提示词与动作字段可能存在运动冲突')
    return dict(policyVersion=POLICY,guideUrl=GUIDE_URL,errors=errors,warnings=warnings,
                checks=[dict(label='参考图编号齐全',passed=all(r['label'] in text for r in inputs['references'])),
                        dict(label='动作、运镜与起止字段齐全',passed=not missing),
                        dict(label='已声明原画风格',passed=bool(re.search(r'笔触|绘画|画风|水墨|设色',text))),
                        dict(label='已声明单镜头与声音边界',passed=bool(re.search(r'单镜头|一镜到底',text) and re.search(r'无台词|无对白|人物对白',text)))],
                note='规则检查用于发现输入缺失与冲突；人物一致性和动作效果仍需生成后人工检查。')
