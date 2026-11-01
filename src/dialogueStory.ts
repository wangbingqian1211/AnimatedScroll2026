export type Row=Record<string,any>
export type Question={id:string;personId:string;question:string;answer:string;clue:string;quote:string;sourceTitle:string;sourceId?:string;sourceVersion?:number;category?:string}
export type Chapter={id:string;title:string;lead:string;outro:string;questions:Question[]}
export function shortName(name:string){return name.replace(/^(宫女|宫人|侍女|内侍|侍从|童子)[：:]\s*/,'')}
export function guideCandidates(p:Row){return (p.annotations||[]).filter((a:Row)=>!p.interaction?.chapters?.length||p.interaction.guideAnnotationIds.includes(a.id)).filter((a:Row)=>a.kind==='character'&&(p.characters||[]).some((c:Row)=>c.id===a.characterId&&/宫女|宫人|侍女|内侍|侍从|童子/.test(c.name+' '+c.identity)))}
export function complete(chapter:Chapter,read:string[]){return chapter.questions.length>0&&chapter.questions.every(q=>read.includes(q.id))}
export function selectSceneVideo(p:Row,jobs:Row[],sid:string){
 const usable=jobs.filter(j=>j.sceneId===sid&&j.status==='succeeded'&&!j.test&&j.videoUrl&&j.reviewStatus!=='needs_revision')
 const chosen=p.interaction?.sceneVideos?.[sid]
 return usable.find(j=>j.id===chosen)||usable.find(j=>j.selectedForDialogue)||usable.find(j=>j.matchesCurrentScript!==false)
}
export function buildChapters(p:Row):Chapter[]{
 if(p.interaction?.chapters?.length)return p.interaction.chapters
 const people:Row[]=p.characters||[],sources:Row[]=(p.sources||[]).filter((s:Row)=>s.sourceType!=='creative_intent')
 const find=(name:string)=>people.find(c=>c.name===name)
 function question(scene:Row,index:number,name:string,text:string,answer:string,clue:string,quote:string):Question|null{
  const person=find(name),source=sources.find(s=>quote&&s.text.includes(quote))
  if(!person||!source)return null
  return {id:scene.id+':'+index,personId:person.id,question:text,answer,clue,quote,sourceTitle:source.title}
 }
 const raw:Row[]=p.scenes?.length?p.scenes:[{id:'painting',title:p.paintingInfo?.name||p.title,units:[],characterIds:people.filter(c=>c.namingOrigin!=='creator').map(c=>c.id)}]
 return raw.map((s:Row)=>{
  let title=s.title,lead='画中人物各有位置，这段画面的来由，可以从他们的讲述慢慢了解。',outro='这一段画面已经看过，让我们带着线索继续往下走。',qs:(Question|null)[]=[]
  const q=(n:number,name:string,text:string,answer:string,clue:string,quote:string)=>question(s,n,name,text,answer,clue,quote)
  if(/修栏|勿易|旧槛|旌/.test(s.title)){
   title='旧栏，为什么留下';lead='此事暂告一段落。到了修栏的时候，殿前这段旧木，又让人想起那场直言。'
   qs=[q(0,'汉成帝','栏杆既已折断，为何不换新的？','旧栏可以修补，不必换去。留下它，是为了表彰直臣。','旧栏修补，并非原样弃置不修。','后来修栏时皇帝要求不要换掉，而应修补旧栏，用来表彰直臣。')]
   outro='一段旧栏，也能留下直言的分量。看看这场故事怎样收束。'
  }else if(/息怒|获救|获全|纳谏|保全/.test(s.title)){
   title='谏言之后，等待回应';lead='辛将军的话说完，殿里静了下来。天子尚未开口，阶前的人都在等候。'
   qs=[q(0,'汉成帝','面对这番劝谏，您如何看待直言？','话虽逆耳，也要听过其中的道理。朕正在想，该如何处置眼前这件事。','听取劝谏，等待天子回应。','成帝息怒，朱云得以保全。')]
   outro='劝谏已经说到这里，看看天子接下来怎样回应。'
  }else if(/自比|死争|辛弃疾|以古/.test(s.title)){
   title='有人，准备为直言争辩';lead='朱云攀栏之后，殿中的气氛愈发紧张。辛将军正望着御座，似乎也准备进言。'
   qs=[q(0,'辛弃疾','您为什么准备为朱云说话？','若他说得对，便不可诛；即使说得不对，也应当容纳。我想请天子听听这层道理。','辛将军准备请求容纳逆耳之言。','左将军辛弃疾免冠解印绶，叩头流血，请求容纳逆耳之言：“使其言是，不可诛；其言非，固当容之。”')]
   outro='他准备如何把这番道理说出口？让我们接着看。'
  }else if(/攀槛|折栏|攀栏|带离/.test(s.title)){
   title='请剑之后，御前追问';lead='请剑之言刚落，天子便要问清究竟所指何人。朱云仍立在阶前，这番话还没有说完。'
   qs=[q(0,'朱云','天子若问所指何人，你准备怎样回答？','安昌侯张禹。我既走到这里，便不打算回避这个名字。','朱云准备在天子追问时指名张禹。','他请求赐尚方斩马剑，处死佞臣，皇帝追问时点名安昌侯张禹。')]
   outro='一个名字，将把这场对话推向何处？看看接下来发生的事。'
  }else if(/直谏|廷前|请剑|张禹/.test(s.title)){
   title='殿前，请剑';lead='阶前那位是朱云。他正面向御座，准备向陛下进言。殿里渐渐安静下来，先听听他为何走到这里。'
   qs=[q(0,'朱云','你为什么准备向天子进言？','为臣者应当匡正君主、造福百姓，怎能只是尸位素餐？这些话，我想当面向陛下说。','朱云准备直言，所求在于匡正君主。','他请求赐尚方斩马剑，处死佞臣'),q(1,'朱云','你打算向陛下请求什么？','我准备请求尚方斩马剑，以斩佞臣。此刻剑还没有赐下，我先把这句话说出口。','朱云准备请剑，尚未点名或被带离。','他请求赐尚方斩马剑，处死佞臣')]
   outro='来意已经听明白。现在，看看朱云如何向天子说出这句请求。'
  }
  let questions=qs.filter((q):q is Question=>!!q)
  if(!questions.length){
   const cast=(s.characterIds||[]).map((id:string)=>people.find(c=>c.id===id)).filter((c:Row|undefined)=>c&&c.namingOrigin!=='creator') as Row[]
   questions=cast.slice(0,3).map((c:Row,i:number)=>{
    const spoken=(s.units||[]).filter((u:Row)=>u.speakerId===c.id)
    const refs=spoken.flatMap((u:Row)=>u.references||[]),reference=refs.find((r:Row)=>sources.some(src=>src.id===r.sourceId&&r.quote&&src.text.includes(r.quote)))
    return {id:s.id+':'+i,personId:c.id,question:`${shortName(c.name)}，这一段你能告诉我什么？`,answer:spoken.length?spoken.map((u:Row)=>u.text).slice(0,2).join(' '):c.identity?`我是${c.name}，${c.identity}。这场事件中我的具体言行，现有材料尚未交代。`:'现有材料没有记下我在这一刻的具体言行。',clue:`听过${c.name}对这一段的说明。`,quote:reference?.quote||'',sourceTitle:sources.find(src=>src.id===reference?.sourceId)?.title||'现有剧本与人物档案'}
   })
  }
  return {id:s.id,title,lead,outro,questions}
 })
}

export function makeInteractionDraft(p:Row){
 const chapters=buildChapters({...p,interaction:undefined}).map(c=>({...c,questions:c.questions.map(q=>{const s=(p.sources||[]).find((s:Row)=>s.sourceType!=='creative_intent'&&q.quote&&s.text.includes(q.quote));return {...q,sourceId:s?.id||'',sourceVersion:s?.version||1,sourceTitle:s?.title||q.sourceTitle,category:'fiction'}})}))
 return {guideAnnotationIds:guideCandidates({...p,interaction:undefined}).map((a:Row)=>a.id),chapters,sceneVideos:p.interaction?.sceneVideos||{},presentation:p.interaction?.presentation||{}}
}
