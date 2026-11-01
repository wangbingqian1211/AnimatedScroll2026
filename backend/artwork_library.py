"""Curated local artwork seeds. Notes, interpretations and authored dialogue stay distinct."""
from .domain import blank,uid

REVISION='2026-10-30'
MING='https://minghuaji.dpm.org.cn/article/detail?id='
CATALOG_CHONGPING='https://www.dpm.org.cn/collection/paint/230460.html'
CATALOG_BUNIAN='https://intl.dpm.org.cn/Ceramics/64087.html'
LECTURE='https://www.dpm.org.cn/learing_detail/251957.html'

# Pixel rectangles inspected against the supplied local files, not detector output.
ZHEKAN_BOXES={
    '汉成帝':(824,223,1065,551),'宫人：德福':(775,176,903,508),
    '辛弃疾':(404,465,626,754),'张禹':(1036,178,1187,549),
    '朱云':(153,212,278,491),'宫女：春萍':(947,143,1039,302),
    '宫女：春桃':(868,141,955,247),'侍卫乙':(22,218,216,523),
    '侍卫甲':(79,190,146,274),
}

ARTICLES={
 'chongping':[
  (1096,'重屏会棋图','/article/2019/03/28/201903280951505'),
  (1095,'周文矩《重屏会棋图》图示与内涵阐释','/article/2019/03/28/201903280951508'),
  (1094,'兴替自古一枰棋——周文矩《重屏会棋图》欣赏','/article/2019/03/28/201903280951506'),
  (1091,'周文矩《重屏会棋图》','/article/2019/03/28/201903280951490'),
 ],
 'bunian':[
  (19016,'以“图像学”解读初唐绘画《步辇图》','/article/2019/07/15/21e387b470de42a98f8e67d968a2dac0.pdf'),
  (19015,'图像背后的历史——从《步辇图》看文成公主入藏后初唐王朝与吐蕃的关系','/article/2019/07/15/aef518c1520143489fc31eafb03f0eec.pdf'),
  (19014,'《步辇图》概念的历史生成','/article/2019/07/15/6f20eedb21c84e0abd78ce256e93b9dd.pdf'),
  (19010,'阎立本与《步辇图》','/article/2019/07/15/dad584069a824b32ae316472f96578c2.pdf'),
 ],
}

SPECS={
 'chongping':dict(
  title='重屏会棋图',size=(1458,786),
  info=dict(name='重屏会棋图卷',artist='传周文矩',period='五代南唐题材；现存本有宋摹本说',storyPeriod='南唐',material='绢本设色',dimensions='40.3 × 70.5 厘米',collection='故宫博物院',description='用户提供的本地图片。四位主角的位置对应暂采李凇讲座报道，保留学术争议；屏内人物属于画中画，不与外层人物混作同一空间。'),
  notes=[
   ('catalog','会棋与重屏 · 馆藏说明整理','画面以李璟与三位兄弟会棋为主体；有棋具、坐榻和屏风。屏风所绘居室内还出现另一面屏风，形成画中画的层次。现存本无作者款印，馆方说明提及宋人摹本的鉴定意见。',CATALOG_CHONGPING+'\nhttps://www.dpm.org.cn/vr/stone-moat/wyd_6.html','historical_material'),
   ('people','四位人物的对应 · 有争议的研究释读','李凇讲座报道将四人自左至右辨为李景逷、李景遂、李璟、李景达。本项目暂采此对应。人物位置、作品年代和主题存在不同解读，不能把这一对应当作无争议鉴定。',LECTURE,'scholarly_interpretation'),
   ('screen','屏中诗意 · 解释笔记','有研究联系白居易《偶眠》理解屏中卧者及隐逸意趣；这是解释路径，不能据此确认屏中人物就是白居易，也不能把屏内外人物视为同处一室。',LECTURE,'scholarly_interpretation'),
   ('reading','观看边界 · 编辑说明','会棋、人物视线与室内陈设可供观察；关于继位和政治寓意的阐释应另列为研究观点。具体输赢、对话、内心活动与会棋当天的安排，现有整理材料不能直接证明。',LECTURE,'editorial_boundary'),
  ],
  # key, name, identity, visible description, pixel rectangle, source key, scope
  roles=[
   ('jingti','李景逷','南唐宗室，李璟之弟；画中对应待核对','外层前排左侧坐者，头巾系结，面向棋具。',(447,376,644,753),'people','outer'),
   ('jingsui','李景遂','南唐宗室，李璟之弟；画中对应待核对','外层偏左后排坐者，戴高巾，浅色长衣。',(532,309,676,578),'people','outer'),
   ('lijing','李璟','南唐中主；红带坐者对应待核对','外层居中偏后坐者，戴高帽，腰间有红色带。',(649,255,820,581),'people','outer'),
   ('jingda','李景达','南唐宗室，李璟之弟；画中对应待核对','外层前排右侧坐者，面向左侧，衣袖宽大。',(779,346,1001,752),'people','outer'),
   ('attendant','侍从：童子','画中未具名侍从；称谓按位置与形象整理','外层最右站立童子，双手在身前，腰系红带。',(1110,362,1227,696),'catalog','outer'),
   ('screen-elder','屏中高士','屏风内卧者；有联系白居易诗意的释读','屏风所绘室内的斜卧人物，属于画中画。',(422,175,654,333),'screen','screen'),
   ('screen-left','屏中侍者甲','屏内未具名人物；采用描述性称谓','屏风内左侧站立人物，与卧者处于内层画面。',(239,215,365,382),'screen','screen'),
   ('screen-right','屏中侍者乙','屏内未具名人物；采用描述性称谓','屏风内右侧站立人物，与外层童子分开标注。',(675,211,734,294),'screen','screen'),
  ],
  guide='attendant',
  presentation=dict(kicker='重屏之内 · 入画对话',headline='借一双画中人的眼睛，\n走近这一局会棋。',description='先看席间的人，再看屏中的画。\n随侍从听线索，向画中人物提问。',caption='一局会棋 · 层层重屏',closing='棋局仍在画中，几重屏风也还在。再看一遍人物的座次与目光，或许会发现新的问题。'),
  scenes=[
   ('会棋之席：辨认画中人',['jingti','jingsui','lijing','jingda','attendant'],'观察四位坐者、棋具与侍从。人物姓名采用注明出处的暂定对应，不补写未获支持的个人经历。','从整体画面进入人物关系，再引向屏风。','catalog',
    [('attendant','先看席间几位。'),('lijing','兄弟同坐，目光未必只在棋子上。')],
    [('lijing','席间都是哪些人？','画外的人将我们认作李璟兄弟四人；你也可以先看清各自坐在哪里，再回头比较这些说法。','人物身份对应需结合资料核对。','people'),('attendant','你站在棋局旁做什么？','我侍立在这里，看着席间的动静。至于我的名字，画上并没有留下。','未具名侍者不补写真实姓名。','catalog')]),
   ('屏中之屏：看见另一重空间',['lijing','attendant','screen-elder','screen-left','screen-right'],'区分外层会棋与内层居室；把诗意联系作为解释呈现，不声称屏内外是同一时刻的真实会面。','由外层坐席转向屏风内部，再返回整体观看。','screen',
    [('attendant','请再看屏风里面。'),('screen-elder','卧看屏前，也自有一番天地。')],
    [('attendant','屏风里怎么还有一面屏风？','目光往里走，居室中又有屏风。这样一层接一层看，才不容易把几重画面混在一起。','区分外层空间与屏内画面。','catalog'),('screen-elder','这里一定是在画白居易吗？','你可以循着《偶眠》的诗意来读我，却不必急着只用一个名字把这幅画说尽。','白居易的联系属于研究释读。','screen')]),
   ('一局多解：座次与目光',['lijing','jingda','jingsui','jingti','attendant'],'回看人物座次和视线，区分画面观察与政治寓意解释；不编造具体传位仪式或棋局结果。','汇总前两幕线索，留下可比较的观看路径。','reading',
    [('jingda','席间的话，未必尽在棋盘上。'),('attendant','带着方才的线索，再看一眼。')],
    [('jingda','这一局棋能直接证明传位安排吗？','棋局与座次可以引人思量，画面却没有把席间所有事情都说出来。留些未尽处，也好再看。','政治寓意应与确证事件分开。','reading'),('lijing','为什么你看向身旁的兄弟？','兄弟都在席间，我的目光也会落在他们身上。此刻，不必只盯着棋子。','视线方向可观察，动机对白为演绎。','people')]),
  ]),
 'bunian':dict(
  title='步辇图',size=(1571,788),
  info=dict(name='步辇图卷',artist='传阎立本',period='唐代题材；传世版本问题另需核对',storyPeriod='贞观十五年（641年）接见禄东赞的题材',material='绢本设色',dimensions='38.5 × 129 厘米',collection='故宫博物院',description='用户提供的本地 JPG。依可见头部逐个标注；本图可见宫女形象数量与馆方文字记述存在差异，保留版本核对提示，不擅自删除或补画人物。'),
  notes=[
   ('catalog','接见与人物 · 馆藏说明整理','画面题材是唐太宗李世民接见吐蕃使臣禄东赞。皇帝坐在步辇上，前方红袍者为引见官，最左白袍者馆藏说明释为内官；不据此补写两位官员姓名。',CATALOG_BUNIAN,'historical_material'),
   ('background','画外背景 · 馆藏说明整理','馆方说明把题材联系到贞观十五年（641年）禄东赞赴长安迎接文成公主。文成公主、松赞干布没有出现在所给画面中，不把画外背景改写成画中已发生的对白和动作。',CATALOG_BUNIAN,'historical_material'),
   ('image','用户图像的版本与人数 · 观察笔记','馆藏说明提及九名宫女；当前用户 JPG 中可辨出十处宫女头部形象，暂按实际可见位置标注，并将最右等形象保留为待核对。此差异不能据此判定原作人数、版本真伪或图像成因。','用户提供图片：步辇图.jpg；对照 '+CATALOG_BUNIAN,'image_observation'),
   ('boundary','观看边界 · 编辑说明','人物称谓、官员具体职任及作品版本需结合不同材料核对。未具名人物仅用服饰与位置区分；仪式具体话语、人物心理和细微动作作为创作补充，不能当作史料原话。',CATALOG_BUNIAN,'editorial_boundary'),
  ],
  roles=[
   ('white','白袍内官','最左白袍官员；通译等释读另待核对','左侧最外白袍人物，双手置于身前，面朝右侧。',(126,335,257,767),'catalog','outer'),
   ('ludongzan','禄东赞','吐蕃使臣；图中对应按馆方说明整理','左侧中间着纹样衣袍、拱手站立的使臣。',(307,329,456,769),'catalog','outer'),
   ('official','红袍引见官','仪式引见官员，姓名未据所给材料确认','三位立者中最右红袍人物，面向皇帝。',(500,278,648,726),'catalog','outer'),
   ('emperor','唐太宗李世民','唐朝皇帝，步辇上的坐者','右侧人物群中央戴冠坐者，周围有侍女。',(1121,277,1228,409),'catalog','outer'),
   ('fan-front','宫女：前侧掌扇者','持扇宫女，姓名未载','宫女群最左后方，持长柄扇，面向左。',(852,281,975,668),'image','outer'),
   ('maid-front-left','宫女：前列左侍者','辇前宫女，采用位置称谓','前排偏左、头向左转的宫女。',(944,369,1054,750),'image','outer'),
   ('maid-back-left','宫女：辇侧左侍者','辇侧宫女，采用位置称谓','皇帝左后方、身体部分遮挡的宫女。',(1024,301,1113,405),'image','outer'),
   ('maid-front-center','宫女：辇前侍者','辇前宫女，采用位置称谓','皇帝左前方、头偏向左侧的宫女。',(1090,383,1161,753),'image','outer'),
   ('maid-low','宫女：俯身侍者','较低处宫女，采用姿态称谓','辇前较低处露出头部，身体被遮挡。',(1046,520,1170,759),'image','outer'),
   ('maid-back-right','宫女：辇侧右侍者','辇侧宫女，采用位置称谓','皇帝右后方、头部较高的宫女。',(1204,299,1277,387),'image','outer'),
   ('maid-front-right','宫女：前列右侍者','辇前宫女，采用位置称谓','皇帝右前方、头略向左转的宫女。',(1218,371,1324,741),'image','outer'),
   ('canopy','宫女：后侧持盖者','持盖宫女，姓名未载','右后方最高处宫女，邻近华盖长柄。',(1305,241,1395,350),'image','outer'),
   ('maid-canopy','宫女：持盖者前侍者','右侧宫女，采用位置称谓','持盖者前方露出头部的宫女。',(1301,346,1402,741),'image','outer'),
   ('maid-far-right','宫女：最右侍者（待核对）','用户图像最右人物，需核对版本与人数差异','最右侧朝左的宫女形象，衣摆向下延伸。',(1384,337,1478,721),'image','outer'),
  ],
  guide='fan-front',
  presentation=dict(kicker='辇前相见 · 入画对话',headline='随一位画中侍者，\n走近这场辇前相见。',description='从人物位置和服饰开始。\n听引路人的介绍，再向相关人物提问。',caption='一次相见 · 几种视角',closing='使臣与皇帝的相见留在画中。再回望人物的距离、服饰与仪仗，也记住画面没有讲出的部分。'),
  scenes=[
   ('使臣入见：辨认三位立者',['white','ludongzan','official','emperor','fan-front'],'从左右人物关系进入接见场面，区分使臣、引见官与白袍官员，不为未具名官员添加姓名。','先辨认立者，再转向皇帝与步辇。','catalog',
    [('official','使臣已至。'),('ludongzan','奉使前来，敬候相见。')],
    [('ludongzan','你在这幅画中以什么身份出现？','我是从吐蕃前来的使臣。此刻站在殿前，等候这次相见。','使臣禄东赞与引见官分开辨认。','catalog'),('official','为什么你站在使臣前面？','我在这里引见来使。相见有相见的仪节，各人也有自己的位置。','红袍人物采用引见官称谓，不补姓名。','catalog')]),
   ('步辇与仪仗：由站立到端坐',['emperor','fan-front','maid-front-left','maid-back-left','maid-front-center','maid-low','maid-back-right','maid-front-right','canopy','maid-canopy','maid-far-right'],'观察步辇、扇与华盖，区分皇帝与侍女位置；人数差异保留为图像版本核对事项。','由使臣的朝向转向步辇周围的人物与器具。','image',
    [('fan-front','请看步辇周围。'),('emperor','来使已在辇前。')],
    [('fan-front','你手边的长柄器物是什么？','我在辇前持扇侍立。再往后看，还有持盖与扶侍的人，画面把我们安排在不同位置。','从可见器物与位置辨认侍者，不补真实姓名。','image'),('emperor','这次相见在画中如何呈现？','我坐在辇上，来使立在前方。人与人之间的朝向和距离，都是你可以细看的地方。','区分画面可见姿态与创作对白。','catalog')]),
   ('画外的历史：迎亲题材与观看边界',['ludongzan','emperor','white','fan-front'],'把题材与641年迎接文成公主的背景联系起来；不把未入画的人物加进当前画面，不扩写未经资料支持的会谈细节。','收束人物、器具与背景三组线索。','background',
    [('ludongzan','为远道而来的相见，谨致问候。'),('fan-front','再看一眼画中与画外。')],
    [('ludongzan','这次出使与什么背景有关？','我为迎亲之事来到长安。至于此行以后许多地方发生的事情，不能只凭眼前这一幅画说尽。','馆方题材说明联系禄东赞迎接文成公主。','background'),('fan-front','为什么没有在画里看到文成公主？','眼前画的是辇前接见，公主并没有出现在这一段画面里。看画时，先把画中的人与画外的事分开。','文成公主与松赞干布不作为画中可见角色。','background')]),
  ]),
}


def rectangle(box,size):
    x1,y1,x2,y2=box;w,h=size
    if not (0<=x1<x2<=w and 0<=y1<y2<=h):raise ValueError('人物框超出所给图像')
    return dict(x=x1/w,y=y1/h,w=(x2-x1)/w,h=(y2-y1)/h)


def build_project(key,image):
    spec=SPECS[key];p=blank();p.update(title=spec['title'],libraryKey=key,datasetRevision=REVISION,image=image,imageVersion=1,paintingInfo=spec['info'],workflowPrepared=True,intentOrigin='unstarted',personRelations=[],historicalEvents=[])
    sources={}
    for skey,title,text,citation,kind in spec['notes']:
        s=dict(id=uid(),title=title,text=text,citation=citation,location='编辑整理笔记，非馆方原文逐字转录',version=1,confirmed=False,method='curated_notes',sourceType=kind)
        p['sources'].append(s);sources[skey]=s
    for number,title,pdf in ARTICLES[key]:
        p['sources'].append(dict(id=uid(),title=title,text='已核对馆方文章标题与所列 PDF 元数据。PDF 地址本次请求返回404，未取得正文；仅收录出处，未据此补写结论。',citation=MING+str(number),location='馆方文章索引；正文待核对',version=1,confirmed=False,method='bibliography',sourceType='bibliographic_reference',articleId=number,pdfUrl='https://minghuaji.dpm.org.cn'+pdf,accessStatus='pdf_unavailable'))
    if key=='chongping':p['sources'].append(dict(id=uid(),title='周文矩重屏会棋图卷 · 用户提供馆藏链接',text='用户提供的故宫馆藏页已收录；本次直接访问超时，画作基础信息另对照故宫展览页与讲座报道整理。',citation=CATALOG_CHONGPING,location='馆方链接',version=1,confirmed=False,method='bibliography',sourceType='bibliographic_reference'))
    position_source=dict(id=uid(),title='画中人物位置 · 本地图片观察',text='\n'.join(name+'：'+description for _,name,_,description,_,_,_ in spec['roles']),citation='用户提供的本地图片：'+spec['title']+'.jpg',location='编辑观察；角色名称是暂定辨识标签，不构成史料身份鉴定',version=1,confirmed=False,method='image_observation',sourceType='image_observation')
    p['sources'].append(position_source)
    people={};annotations={}
    for rkey,name,identity,description,box,skey,scope in spec['roles']:
        c=dict(id=uid(),name=name,identity=identity,biography='',summary=identity,relationships='',knowledge='仅使用已提供资料与当前画面；未记言行不作为史实。',evidence='对应依据：'+sources[skey]['title']+'。人物位置与身份均待核对。',mentions=[],namingOrigin='descriptive' if scope=='screen' or any(v in name for v in ('侍','宫女')) else 'curated',confirmed=False)
        quote=name+'：'+description
        c['mentions']=[dict(kind='background',quote=quote,sourceId=position_source['id'],sourceVersion=1,start=position_source['text'].index(quote),end=position_source['text'].index(quote)+len(quote))]
        p['characters'].append(c);people[rkey]=c
        a=dict(id=uid(),kind='character',characterId=c['id'],description=description,confirmed=False,identityConfirmed=False,needsReview=True,origin='curated_manual',scope=scope,**rectangle(box,spec['size']))
        p['annotations'].append(a);annotations[rkey]=a
        p['observations'].append(dict(id=uid(),annotationId=a['id'],description=description,inference='',confirmed=False,stale=False,imageVersion=1))
    p['materialInputs']=dict(background=sources['catalog']['text']+'\n\n'+sources.get('screen',sources.get('background'))['text'],relationships=sources.get('people',sources['catalog'])['text'],narrative='',version=1)
    chapters=[];p['storyboards']=[]
    for i,(title,cast,goal,connection,skey,lines,questions) in enumerate(spec['scenes']):
        sid=uid();source=sources[skey];units=[]
        units.append(dict(id=uid(),text=source['text'],kind='clue',category='supported',speakerId='',rationale='引用编辑整理笔记，原文可靠性及解释仍待核对。',references=[dict(sourceId=source['id'],sourceVersion=1,annotationId='',quote=source['text'])],status='pending',locked=False))
        units.append(dict(id=uid(),text='保留整幅画面的布局，人物仅有轻微目光或衣袖变化。',kind='action',category='fiction',speakerId=people[spec['guide']]['id'],rationale='动画演绎草稿，不把微动作当作已记载事实。',references=[],status='pending',locked=False))
        for actor,text in lines:units.append(dict(id=uid(),text=text,kind='dialogue',category='fiction',speakerId=people[actor]['id'],rationale='为入画体验编写的演绎对白，不是历史原话。',references=[],status='pending',locked=False))
        p['scenes'].append(dict(id=sid,title=title,goal=goal,connection=connection,characterIds=[people[r]['id'] for r in cast],units=units))
        qs=[]
        for n,(actor,question,answer,clue,qsource) in enumerate(questions):
            src=sources[qsource]
            qs.append(dict(id=sid+':'+str(n),personId=people[actor]['id'],question=question,answer=answer,clue=clue,sourceId=src['id'],sourceVersion=1,sourceTitle=src['title'],quote=src['text'],category='fiction'))
        chapters.append(dict(id=sid,title=title.split('：')[0],lead='我是画中引路人。这一幕，先从「'+title+'」看起。',outro='这一幕的线索已经留下。让我们再看画中的下一处。',questions=qs))
        p['storyboards'].append(dict(sceneId=sid,prompt='保持所给古画全幅构图与原有形象，只演绎本场微动作。',shots=[dict(duration=5,framing='原画全幅',camera='固定机位',characterIds=[people[r]['id'] for r in cast if annotations[r].get('scope')=='outer'],action='保留原画；仅以轻微眼神、衣袖变化呈现本幕，不增减人物。',dialogue=[dict(speakerId=people[lines[0][0]]['id'],text=lines[0][1][:8],category='fiction',sourceId='',quote='')],narration='',sound='轻微衣料声')]))
    p['sceneCount']=len(p['scenes']);p['interaction']=dict(guideAnnotationIds=[annotations[spec['guide']]['id']],chapters=chapters,presentation=spec['presentation'])
    if key=='chongping':
        for brother in ('jingsui','jingda','jingti'):p['personRelations'].append(dict(id=uid(),fromId=people['lijing']['id'],toId=people[brother]['id'],label='兄弟',description='按馆方说明及所列人物释读整理；人物在画中的具体对应待核对。',origin='manual',confirmed=False,evidence=dict(sourceId=sources['people']['id'],sourceVersion=1,quote=sources['people']['text'])))
    else:p['personRelations'].append(dict(id=uid(),fromId=people['emperor']['id'],toId=people['ludongzan']['id'],label='接见／出使',description='画面表现皇帝与使臣的相见；具体对白另列为创作。',origin='manual',confirmed=False,evidence=dict(sourceId=sources['catalog']['id'],sourceVersion=1,quote=sources['catalog']['text'])))
    for scene in p['scenes']:p['historicalEvents'].append(dict(id=uid(),title=scene['title'],time='观看段落；不指定新的史实日期',description=scene['goal'],characterIds=scene['characterIds'],evidence=dict(sourceId=sources['catalog']['id'],sourceVersion=1,quote=sources['catalog']['text'])))
    if key=='bunian':p['imageAudit']=dict(status='needs_review',observedFigures=14,catalogFigures=13,note=sources['image']['text'])
    return p
