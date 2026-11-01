<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'
import EvidenceFields from './EvidenceFields.vue'
import { profile } from './people'
type Row = Record<string, any>
const props = defineProps<{project: Row; analysisRunning?: boolean; relationTask?: Row}>()
const emit = defineEmits(['replace', 'running', 'close', 'analyze-relations'])
const database = ref({backend:'',connected:false})
const storageLabel = computed(()=>database.value.connected?(database.value.backend==='mysql'?'MySQL 资料库':'SQLite 资料库'):'数据库连接待确认')
onMounted(async()=>{try{const r=await fetch('/api/database/status');if(r.ok)database.value=await r.json()}catch{}})
const tab = ref('overview'), query = ref(''), selectedPerson = ref('')
const editing = ref(''), draft = ref<Row>({}), busy = ref(false), error = ref(''), notice = ref('')
let baseVersion = 0
const tabs = [
  {id:'overview',name:'作品档案',mark:'卷'}, {id:'people',name:'人物档案',mark:'人'},
  {id:'relations',name:'人物关系',mark:'系'}, {id:'events',name:'历史事件',mark:'事'},
  {id:'sources',name:'史料来源',mark:'据'}, {id:'background',name:'背景原文',mark:'文'},
]
const info = computed(()=>props.project.paintingInfo || {})
const relations = computed<Row[]>(()=>props.project.personRelations || [])
const events = computed<Row[]>(()=>props.project.historicalEvents || [])
const person = computed(()=>props.project.characters.find((c:Row)=>c.id===selectedPerson.value))
const people = computed<Row[]>(()=>props.project.characters.filter((c:Row)=>(c.name+' '+c.identity).includes(query.value.trim())))
const sources = computed<Row[]>(()=>props.project.sources.filter((s:Row)=>(s.title+' '+s.citation+' '+s.text).includes(query.value.trim())))
const fields: Row = {name:'作品名称',artist:'作者',period:'绘画年代',storyPeriod:'故事时代',medium:'材质与技法',dimensions:'尺寸',collection:'收藏机构',accession:'馆藏编号'}
const rawFields: Row = {background:'历史背景',relationships:'人物与关系',narrative:'已有历史叙事'}
const newId = ()=>crypto.randomUUID().slice(0,12)
const evidence = ()=>({sourceId:'',sourceVersion:1,quote:''})
function name(id:string){return props.project.characters.find((c:Row)=>c.id===id)?.name || '未关联人物'}
function count(id:string){return ({people:props.project.characters.length,relations:relations.value.length,events:events.value.length,sources:props.project.sources.length} as Row)[id]}
function switchTab(id:string){tab.value=id;query.value=''}
function begin(kind:string,row?:Row){
  if(editing.value)return
  baseVersion=props.project.version;error.value='';notice.value='';editing.value=kind
  if(row){draft.value=structuredClone(JSON.parse(JSON.stringify(row)));return}
  if(kind==='overview')draft.value={...info.value,name:info.value.name||props.project.title}
  if(kind==='people')draft.value={id:newId(),name:'',identity:'',biography:'',summary:'',relationships:'',knowledge:'',evidence:'',mentions:[],namingOrigin:'catalog',confirmed:false}
  if(kind==='relations')draft.value={id:newId(),fromId:'',toId:'',label:'',description:'',evidence:evidence()}
  if(kind==='events')draft.value={id:newId(),title:'',time:'',description:'',characterIds:[],evidence:evidence()}
  if(kind==='sources')draft.value={id:newId(),title:'',citation:'',location:'',text:'',version:1,method:'catalog',sourceType:'historical_note',confirmed:false}
  if(kind==='background')draft.value={...props.project.materialInputs}
}
function cancel(){editing.value='';draft.value={};error.value=''}
function upsert(p:Row,key:string){p[key] ||= [];const i=p[key].findIndex((r:Row)=>r.id===draft.value.id);if(i<0)p[key].push({...draft.value});else p[key][i]={...draft.value}}
function validate(){
  const d=draft.value
  if(editing.value==='overview'&&!d.name?.trim())throw Error('请填写作品名称。')
  if(editing.value==='people'&&!d.name?.trim())throw Error('请填写人物姓名或称谓。')
  if(editing.value==='relations'&&(!d.fromId||!d.toId||d.fromId===d.toId||!d.label?.trim()))throw Error('请选择两个不同人物，并填写关系名称。')
  if(editing.value==='events'&&!d.title?.trim())throw Error('请填写事件名称。')
  if(editing.value==='sources'&&(!d.title?.trim()||!d.text?.trim()))throw Error('请填写来源标题和原文。')
}
async function save(remove=false){
  error.value='';notice.value=''
  try{
    if(!remove)validate()
    if(props.project.version!==baseVersion)throw Error('项目版本已变化。草稿仍保留，请取消后重新编辑最新资料。')
    const p=JSON.parse(JSON.stringify(props.project))
    if(editing.value==='overview')p.paintingInfo={...draft.value}
    if(editing.value==='background')p.materialInputs={...draft.value}
    if(editing.value==='people'){draft.value.summary=[draft.value.identity,draft.value.biography].filter(Boolean).join('；');draft.value.confirmed=false;upsert(p,'characters')}
    if(editing.value==='relations'){
      if(remove){
        p.personRelations=p.personRelations.filter((r:Row)=>r.id!==draft.value.id)
        p.dismissedRelationKeys ||= []
        const k=JSON.stringify([draft.value.fromId,draft.value.toId,draft.value.label.trim()])
        if(!p.dismissedRelationKeys.includes(k))p.dismissedRelationKeys.push(k)
      }else{
        draft.value.origin='manual';draft.value.confirmed=true
        upsert(p,'personRelations')
      }
    }
    if(editing.value==='events')upsert(p,'historicalEvents')
    if(editing.value==='sources')upsert(p,'sources')
    busy.value=true;emit('running',true)
    const r=await fetch('/api/projects/'+p.id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)})
    const value=await r.json()
    if(!r.ok)throw Error(typeof value.detail==='string'?value.detail:r.status===409?'保存冲突：数据库已有新版本，当前草稿已保留。':'保存失败，请核对字段后重试。')
    emit('replace',value);editing.value='';draft.value={};notice.value='已保存到资料库 · 项目版本 v'+value.version
  }catch(e){error.value=e instanceof Error?e.message:String(e)}finally{busy.value=false;emit('running',false)}
}
function sourceState(row:Row){
  const e=row.evidence,s=props.project.sources.find((s:Row)=>s.id===e?.sourceId)
  if(!s||!e?.quote)return '待补依据'
  return s.version===e.sourceVersion&&s.text.includes(e.quote)?'已关联引文':'来源已变化 · 待复核'
}
function sourceName(row:Row){return props.project.sources.find((s:Row)=>s.id===row.evidence?.sourceId)?.title || ''}
function openSource(row:Row){tab.value='sources';query.value=sourceName(row)}
const nodes=computed(()=>props.project.characters.map((c:Row,i:number,all:Row[])=>{
  const angle=2*Math.PI*i/all.length-Math.PI/2
  return {...c,x:250+(all.length===1?0:170*Math.cos(angle)),y:180+(all.length===1?0:120*Math.sin(angle))}
}))
const edges=computed<Row[]>(()=>relations.value.map((r:Row)=>{const from=nodes.value.find((c:Row)=>c.id===r.fromId),to=nodes.value.find((c:Row)=>c.id===r.toId);if(!from||!to)return null;const dx=to.x-from.x,dy=to.y-from.y,l=Math.hypot(dx,dy)||1;return {...r,from,to,x1:from.x+dx/l*30,y1:from.y+dy/l*30,x2:to.x-dx/l*32,y2:to.y-dy/l*32}}).filter((r:Row|null)=>r!==null) as Row[])
watch(()=>props.project.id,()=>{cancel();selectedPerson.value='';query.value=''})
</script>

<template>
<section class="catalog-panel">
  <div class="catalog-heading"><div><small>ARTWORK KNOWLEDGE LIBRARY</small><h2>画作资料库</h2><p>围绕当前画作，整理人物、关系、事件与出处。</p></div><div class="library-actions"><span class="storage-badge">● {{storageLabel}} · v{{project.version}}</span><button :disabled="!!editing" @click="emit('close')">收起资料库 ↑</button></div></div>
  <div v-if="notice" class="catalog-notice" role="status">{{notice}}</div>
  <div class="catalog-layout" :class="{'with-editor':editing}">
    <nav class="catalog-nav" aria-label="资料分类"><button v-for="item in tabs" :key="item.id" :class="{active:tab===item.id}" @click="switchTab(item.id)"><span class="nav-mark">{{item.mark}}</span>{{item.name}}<small v-if="count(item.id)!==undefined">{{count(item.id)}}</small></button><p>与当前画作关联<br>编辑后保存至资料库</p></nav>
    <div class="catalog-content">
      <div class="content-heading"><div><h3>{{tabs.find(t=>t.id===tab)?.name}}</h3><small>{{tab==='relations'?'从史料自动分析关系；虚线为待核对建议，实线为人工录入或已确认。':tab==='events'?'按创作者录入顺序展示；不自动补写史实和年份。':'已有资料直接展示，点击编辑后修改。'}}</small></div><button v-if="tab==='relations'" class="primary" :disabled="analysisRunning||!!editing||project.characters.length<2||!project.sources.length" @click="emit('analyze-relations')">{{analysisRunning?'分析中…':'从史料分析关系'}}</button><button v-if="tab==='overview'||tab==='background'" :disabled="!!editing" @click="begin(tab)">编辑{{tab==='overview'?'档案':'原文'}}</button><button v-else :disabled="!!editing" class="primary" @click="begin(tab)">＋ 新增{{({people:'人物',relations:'关系',events:'事件',sources:'来源'} as Row)[tab]}}</button></div>
      <input v-if="tab==='people'||tab==='sources'" v-model="query" class="catalog-search" :aria-label="tab==='people'?'搜索人物资料':'搜索史料来源'" :placeholder="tab==='people'?'搜索姓名或身份…':'搜索标题、出处或原文…'" />
      <template v-if="tab==='overview'">
        <div class="artwork-summary"><img v-if="project.image" :src="project.image" alt="当前画作预览"><div><span class="section-label">当前画作</span><h2>{{info.name||project.title}}</h2><p>{{info.description||project.materialAnalysis?.summary||'尚未填写作品简介，可点击“编辑档案”补充。'}}</p></div></div>
        <dl class="metadata-grid"><div v-for="(label,key) in fields" :key="key"><dt>{{label}}</dt><dd>{{info[key]||(key==='name'?project.title:'待补充')}}</dd></div></dl>
        <div class="catalog-stats"><button v-for="item in tabs.filter(t=>['people','relations','events','sources'].includes(t.id))" :key="item.id" @click="switchTab(item.id)"><b>{{count(item.id)}}</b><span>{{item.name}}</span><span>↗</span></button></div>
      </template>
      <template v-if="tab==='people'"><div class="people-grid"><section v-for="c in people" :key="c.id" class="catalog-card"><div class="card-top"><span class="name-seal">{{c.name.slice(0,1)}}</span><div><h4>{{c.name}}</h4><small>{{c.confirmed?'资料已确认':'资料待核对'}}</small></div><button :disabled="!!editing" @click="begin('people',c)">编辑</button></div><p>{{profile(c)}}</p><details v-if="c.relationships"><summary>人物关系笔记</summary><p>{{c.relationships}}</p></details><details v-if="c.evidence"><summary>依据与不确定性</summary><p>{{c.evidence}}</p></details></section></div><p v-if="!people.length" class="catalog-empty">{{query?'没有匹配的人物。':'尚无人物资料，点击“新增人物”建立档案。'}}</p></template>
      <template v-if="tab==='relations'"><p v-if="relationTask&&(['queued','running'].includes(relationTask.status)||!relations.length||relationTask.inputVersion>=project.version)" class="relation-progress" role="status" aria-live="polite">{{relationTask.progress}}</p>
        <div v-if="nodes.length" class="relation-graph"><svg viewBox="0 0 500 360" role="group" aria-label="当前画作人物关系图"><defs><marker id="catalog-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#95a58b" /></marker></defs><g v-for="r in edges" :key="r.id"><line :class="{suggested:r.origin==='model'&&!r.confirmed}" :x1="r.x1" :y1="r.y1" :x2="r.x2" :y2="r.y2" marker-end="url(#catalog-arrow)"/><rect :x="(r.from.x+r.to.x)/2-42" :y="(r.from.y+r.to.y)/2-10" width="84" height="20" rx="5"/><text :x="(r.from.x+r.to.x)/2" :y="(r.from.y+r.to.y)/2+4">{{r.label.length>7?r.label.slice(0,7)+'…':r.label}}</text></g><g v-for="c in nodes" :key="c.id" role="button" tabindex="0" :aria-label="'查看'+c.name+'的关系资料'" :class="{selected:selectedPerson===c.id}" @click="selectedPerson=c.id" @keydown.enter="selectedPerson=c.id" @keydown.space.prevent="selectedPerson=c.id"><circle :cx="c.x" :cy="c.y" r="28"/><text :x="c.x" :y="c.y+5">{{c.name.length>4?c.name.slice(0,4):c.name}}</text></g></svg></div>
        <div v-if="person" class="person-callout"><b>{{person.name}}</b><p>{{person.relationships||'还没有人物关系笔记。'}}</p><button :disabled="!!editing" @click="begin('people',person)">编辑人物档案</button></div>
        <p v-if="!relations.length" class="catalog-empty">点击“从史料分析关系”，系统会生成带原文依据的关系建议。已有关系可直接编辑。</p>
        <section v-for="r in relations" :key="r.id" class="catalog-card relation-card"><div class="card-top"><h4><small class="relation-review">{{r.origin==='model'&&!r.confirmed?'模型建议 · 待核对':'人工录入／已核对'}}</small>{{name(r.fromId)}} <span>→ {{r.label}} →</span> {{name(r.toId)}}</h4><button v-if="r.origin==='model'&&!r.confirmed" :disabled="!!editing||analysisRunning" @click="begin('relations',r);save()">确认关系</button><button :disabled="!!editing" @click="begin('relations',r)">编辑／删除</button></div><p>{{r.description}}</p><div class="evidence-line"><span>{{sourceState(r)}}</span><button v-if="r.evidence?.sourceId" @click="openSource(r)">{{sourceName(r)}} ↗</button></div><blockquote v-if="r.evidence?.quote">{{r.evidence.quote}}</blockquote></section>
      </template>
      <template v-if="tab==='events'"><div class="event-timeline"><section v-for="(event,i) in events" :key="event.id" class="event-item"><span class="event-dot">{{String(i+1).padStart(2,'0')}}</span><div class="catalog-card"><div class="card-top"><div><small>{{event.time||'具体时间未载明'}}</small><h4>{{event.title}}</h4></div><button :disabled="!!editing" @click="begin('events',event)">编辑</button></div><p>{{event.description}}</p><div class="event-people"><span v-for="cid in event.characterIds" :key="cid">{{name(cid)}}</span></div><div class="evidence-line"><span>{{sourceState(event)}}</span><button v-if="event.evidence?.sourceId" @click="openSource(event)">{{sourceName(event)}} ↗</button></div><blockquote v-if="event.evidence?.quote">{{event.evidence.quote}}</blockquote></div></section></div><div v-if="!events.length" class="catalog-empty"><p>尚未录入结构化历史事件。</p><p>已有叙事原文完整保留在“背景原文”中，可据此逐条建立事件并关联出处。</p><button @click="switchTab('background')">阅读已有叙事 →</button></div></template>
      <template v-if="tab==='sources'"><section v-for="s in sources" :key="s.id" class="catalog-card source-card"><div class="card-top"><div><small>{{s.sourceType==='creative_intent'?'创作设想 · 非史料':s.method==='material_input'?'背景原文记录':'资料来源'}} · v{{s.version}}</small><h4>{{s.title}}</h4></div><button :disabled="!!editing" @click="s.method==='material_input'?begin('background'):begin('sources',s)">编辑</button></div><p class="source-citation">{{s.citation||'尚未填写出处'}}<span v-if="s.location"> · {{s.location}}</span></p><p class="source-preview">{{s.text}}</p><details><summary>阅读完整原文</summary><p class="original-text">{{s.text}}</p></details></section><p v-if="!sources.length" class="catalog-empty">{{query?'没有匹配的来源。':'尚无来源，点击“新增来源”录入原文和出处。'}}</p></template>
      <template v-if="tab==='background'"><section v-for="(label,key) in rawFields" :key="key" class="catalog-card"><div class="card-top"><h4>{{label}}</h4><small>原文 v{{project.materialInputs.version}}</small></div><p class="original-text">{{project.materialInputs[key]||'尚未录入。'}}</p></section><small>原文修改后，相关人物和已有创作审核会按原流程标记为待复核；不会自动调用模型。</small></template>
    </div>
    <aside v-if="editing" class="catalog-editor" aria-label="资料编辑器"><div class="editor-heading"><div><small>CREATOR EDITOR</small><h3>编辑{{tabs.find(t=>t.id===editing)?.name}}</h3></div><button :disabled="busy" aria-label="取消编辑" @click="cancel">×</button></div><p class="editor-hint">修改后点击保存，才会写入资料库。取消将放弃当前草稿。</p>
      <form @submit.prevent="save()"><fieldset :disabled="busy">
        <template v-if="editing==='overview'"><label v-for="(label,key) in fields" :key="key">{{label}}<input v-model="draft[key]" :required="key==='name'" :placeholder="key==='storyPeriod'?'与画作年代分开记录':'未载明可留空'"></label><label>作品简介<textarea v-model="draft.description" rows="4" /></label></template>
        <template v-if="editing==='people'"><label>姓名或称谓<input v-model="draft.name" required maxlength="100"></label><label>身份<input v-model="draft.identity"></label><label>经历<textarea v-model="draft.biography" rows="4" /></label><label>人物关系笔记<textarea v-model="draft.relationships" rows="3" /></label><label>依据与不确定性<textarea v-model="draft.evidence" rows="3" /></label><small>修改人物资料后需重新核对确认，对应的画面姓名也会标记为待复核。</small></template>
        <template v-if="editing==='relations'"><label>起点人物<select v-model="draft.fromId" required><option value="">选择人物</option><option v-for="c in project.characters" :key="c.id" :value="c.id">{{c.name}}</option></select></label><label>关系名称<input v-model="draft.label" required maxlength="100" placeholder="例如：老师、劝谏、为其辩护"></label><label>终点人物<select v-model="draft.toId" required><option value="">选择人物</option><option v-for="c in project.characters" :key="c.id" :value="c.id">{{c.name}}</option></select></label><label>关系说明<textarea v-model="draft.description" rows="3" /></label><EvidenceFields :evidence="draft.evidence" :sources="project.sources"/></template>
        <template v-if="editing==='events'"><label>事件名称<input v-model="draft.title" required maxlength="200"></label><label>时间或阶段<input v-model="draft.time" placeholder="例如：当廷进谏；无具体年份可留空"></label><label>事件经过<textarea v-model="draft.description" rows="5" /></label><fieldset class="participant-fields"><legend>关联人物</legend><label v-for="c in project.characters" :key="c.id"><input type="checkbox" v-model="draft.characterIds" :value="c.id"> {{c.name}}</label></fieldset><EvidenceFields :evidence="draft.evidence" :sources="project.sources"/></template>
        <template v-if="editing==='sources'"><label>资料标题<input v-model="draft.title" required></label><label>出处（书名／机构／链接）<input v-model="draft.citation"></label><label>页码或原文位置<input v-model="draft.location"></label><label>资料类型<select v-model="draft.sourceType"><option value="historical_note">历史资料／整理笔记</option><option value="creative_intent">创作设想（非史料）</option></select></label><label>原文<textarea v-model="draft.text" rows="12" required /></label><small>保存会更新来源版本，原有引用将按已有流程要求复核。</small></template>
        <template v-if="editing==='background'"><label v-for="(label,key) in rawFields" :key="key">{{label}}<textarea v-model="draft[key]" rows="6" /></label></template>
        <p v-if="error" class="editor-error" role="alert">{{error}}</p><div class="editor-actions"><button v-if="editing==='relations'&&project.personRelations?.some((r:Row)=>r.id===draft.id)" type="button" class="delete-relation" @click="save(true)">删除关系</button><button type="button" @click="cancel">取消</button><button class="primary" type="submit">{{busy?'正在保存…':'保存到资料库'}}</button></div>
      </fieldset></form>
    </aside>
  </div>
</section>
</template>

<style scoped>
.catalog-panel{margin:24px 0 30px}.catalog-heading{display:flex;justify-content:space-between;gap:20px;align-items:center;margin:0 0 22px}.catalog-heading small{font-size:10px;letter-spacing:.16em}.catalog-heading h2{font-size:27px;font-weight:500;margin:8px 0}.catalog-heading p{margin:0;color:#87917e;font-size:12px}.storage-badge{font-size:11px;color:#7b896d;border:1px solid #d7dfcb;border-radius:20px;padding:8px 13px;white-space:nowrap}.catalog-layout{display:grid;grid-template-columns:164px minmax(0,1fr);border:1px solid #dbe0d1;border-radius:10px;overflow:clip;background:#fffef9;align-items:start}.catalog-layout.with-editor{grid-template-columns:150px minmax(260px,1fr) 340px}.catalog-nav{display:flex;flex-direction:column;gap:5px;background:#f0f2e8;align-self:stretch;padding:18px 10px;margin:0;border-right:1px solid #dfe4d6}.catalog-nav button{display:flex;gap:10px;align-items:center;flex:none;padding:13px 10px;border:0;border-radius:5px;background:transparent;font-size:12px;color:#78856e}.catalog-nav button.active{background:#e0e8d8;color:#31594b}.catalog-nav button small{margin-left:auto;font-size:10px}.nav-mark{font-family:serif;font-size:17px;color:#8f9f80}.catalog-nav p{font-size:10px;color:#9aa48f;line-height:1.9;padding:20px 12px;margin-top:auto}.catalog-content{padding:26px;min-width:0;min-height:470px}.content-heading{display:flex;justify-content:space-between;align-items:start;gap:15px;margin-bottom:25px}.content-heading h3{font:500 20px serif;margin:0 0 8px}.content-heading small{font-size:10px;line-height:1.7}.content-heading>button{white-space:nowrap;font-size:11px}.artwork-summary{display:flex;align-items:center;gap:24px;margin:10px 0 26px}.artwork-summary img{width:140px;height:120px;object-fit:cover;border-radius:6px}.artwork-summary h2{font:500 23px serif;margin:10px 0}.artwork-summary p{font-size:12px;color:#7f8975;line-height:1.9;margin-bottom:0;white-space:pre-wrap}.section-label{font-size:10px;letter-spacing:.08em;color:#9aa18d}.metadata-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));border-top:1px solid #e2e6da;margin:0}.metadata-grid>div{padding:17px 0;border-bottom:1px solid #e8ebdf;min-width:0}.metadata-grid dt{font-size:10px;color:#929d84;margin-bottom:8px}.metadata-grid dd{font-size:13px;margin:0;color:#4a5f46;overflow-wrap:anywhere}.catalog-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:24px}.catalog-stats button{display:flex;align-items:center;gap:9px;padding:15px 12px;text-align:left;background:#f5f6ee;border:1px solid #e2e6d7}.catalog-stats b{font:24px Georgia;color:#738564}.catalog-stats span{font-size:10px}.catalog-stats span:last-child{margin-left:auto;color:#97a28a}.catalog-card{border:1px solid #e0e4d7;padding:19px;border-radius:7px;background:#fffefb;margin-bottom:15px;overflow-wrap:anywhere}.catalog-card h4{font-size:15px;font-weight:500;margin:4px 0}.catalog-card p{font-size:12px;line-height:1.95;color:#738069}.catalog-card details{font-size:11px;border-top:1px solid #e8ecdf;padding-top:12px;margin-top:12px}.card-top{display:flex;gap:13px;align-items:center}.card-top button{margin-left:auto;font-size:11px;padding:5px 9px;border:0;background:#f1f4e9;flex-shrink:0}.card-top small{font-size:10px;line-height:1.7}.name-seal{font:22px serif;background:#e9eede;color:#788a64;border-radius:50%;height:42px;width:42px;text-align:center;line-height:42px;flex-shrink:0}.people-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.people-grid .catalog-card{margin:0}.with-editor .people-grid{grid-template-columns:1fr}.catalog-search{max-width:400px;margin-bottom:24px!important;background:#f8f9f1!important}.catalog-empty{text-align:center;color:#99a18d;padding:40px 15px;line-height:1.9;font-size:12px;background:#f7f8f0;border:1px dashed #dce2d0;border-radius:7px}.catalog-empty p{font-size:12px}.catalog-empty button{font-size:11px;background:transparent;border:0}.relation-graph{max-width:650px;margin:0 auto 15px;background:#f4f6ed;border:1px solid #e4e9da;border-radius:8px}.relation-graph svg{width:100%;display:block;max-height:400px}.relation-graph line{stroke:#9ead92;stroke-width:1.5}.relation-graph rect{fill:#f4f6ed}.relation-graph text{font-size:11px;text-anchor:middle;fill:#657a58;pointer-events:none}.relation-graph circle{fill:#fffef9;stroke:#c0ccb1;stroke-width:1.5}.relation-graph g[role=button]{cursor:pointer;outline:none}.relation-graph g[role=button]:hover circle,.relation-graph g[role=button]:focus-visible circle,.relation-graph .selected circle{fill:#e3ebd8;stroke:#31594b;stroke-width:2}.relation-graph g[role=button] text{font-size:12px;fill:#31594b}.person-callout{padding:14px 18px;background:#eef3e4;border-radius:6px;margin:15px 0;font-size:13px}.person-callout p{font-size:12px;margin:7px 0}.person-callout button{font-size:11px;padding:5px;background:transparent;border:0}.relation-card h4 span{font-size:11px;color:#94a187;font-weight:400;margin:0 8px}.evidence-line{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:13px}.evidence-line>span{font-size:10px;color:#967c43;background:#f4f0e2;padding:4px 7px;border-radius:3px}.evidence-line button{border:0;background:transparent;padding:0;font-size:10px;text-decoration:underline;color:#70865c}.catalog-card blockquote{font-size:12px;line-height:1.9;color:#7c856e;border-left:2px solid #c7d2b8;margin:15px 0 0;padding-left:12px}.event-timeline{padding-left:40px}.event-item{position:relative;padding:0 0 9px 15px;border-left:1px solid #ccd6be}.event-dot{position:absolute;left:-17px;top:20px;background:#eef2e6;border:1px solid #d3ddc7;border-radius:50%;width:33px;height:33px;line-height:32px;font:italic 12px/32px Georgia;text-align:center;color:#8c9c7b}.event-item .catalog-card{margin:0 0 8px 9px}.event-people{display:flex;gap:7px;flex-wrap:wrap}.event-people span{font-size:10px;color:#7d8d6c;background:#edf2e5;padding:4px 8px;border-radius:12px}.source-citation{font-size:11px!important;color:#929c85!important}.source-preview{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;white-space:pre-wrap}.original-text{white-space:pre-wrap;max-height:400px;overflow:auto}.catalog-editor{padding:22px;background:#f5f7ef;border-left:1px solid #dce3d1;position:sticky;top:10px;max-height:85vh;overflow:auto;min-width:0}.editor-heading{display:flex;justify-content:space-between;align-items:center}.editor-heading small{font-size:9px;letter-spacing:.14em}.editor-heading h3{font:500 18px serif;margin:8px 0 0}.editor-heading button{font-size:22px;padding:2px 6px;background:transparent;border:0;color:#87947a}.editor-hint{font-size:10px;color:#97a08a;line-height:1.8}.catalog-editor label{font-size:11px;margin-top:17px}.catalog-editor input,.catalog-editor textarea,.catalog-editor select{font-size:12px!important}.editor-actions{display:flex;justify-content:flex-end;gap:8px;position:sticky;bottom:-22px;background:#f5f7ef;padding:18px 0 7px;margin-top:14px}.editor-actions button{font-size:11px}.editor-error{font-size:12px;padding:12px;background:#f7e7df;border-radius:5px;color:#974c32}.catalog-notice{padding:12px 17px;background:#e6eddb;color:#5c774a;font-size:12px;border-radius:6px;margin-bottom:15px}.participant-fields{border-top:1px solid #dce2d2;margin-top:20px;padding-top:10px}.participant-fields legend{font-size:12px}.participant-fields label{display:inline-block;margin:8px 12px 0 0}button:focus-visible{outline:2px solid #31594b;outline-offset:3px}@media(max-width:1200px){.catalog-layout.with-editor{grid-template-columns:145px minmax(0,1fr)}.catalog-editor{grid-column:2;position:static;max-height:none;border-top:1px solid #dce3d1}.catalog-stats{grid-template-columns:repeat(2,1fr)}}@media(max-width:700px){.catalog-layout,.catalog-layout.with-editor{grid-template-columns:1fr}.catalog-nav{flex-direction:row;flex-wrap:wrap;padding:10px;border-right:0;border-bottom:1px solid #dce3d1}.catalog-nav button{padding:9px;font-size:11px}.catalog-nav p{display:none}.catalog-content{padding:18px;min-height:0}.catalog-editor{grid-column:1;border-left:0}.people-grid{grid-template-columns:1fr}.artwork-summary{align-items:start;gap:15px}.artwork-summary img{width:80px;height:100px}.artwork-summary h2{font-size:20px}.catalog-heading{flex-wrap:wrap}.catalog-stats{gap:8px}.event-timeline{padding-left:22px}.metadata-grid{gap:0 15px}}
.library-actions{display:flex;gap:12px;align-items:center}.library-actions button{font-size:11px;background:transparent;padding:7px 10px}@media(max-width:700px){.library-actions{width:100%;justify-content:space-between}}
.relation-graph line.suggested{stroke-dasharray:5 4}.relation-review{display:block!important;margin-bottom:8px;color:#967c43!important;font-size:10px!important}.relation-progress{padding:11px 14px;background:#edf3e4;color:#70855a;font-size:12px;border-radius:5px;margin-bottom:18px}.editor-actions .delete-relation{color:#9d634e;margin-right:auto}.content-heading{flex-wrap:wrap}.content-heading>div{flex:1;min-width:180px}
</style>
