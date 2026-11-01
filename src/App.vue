<script setup lang="ts">
import {ref,onMounted,computed,watch,nextTick} from 'vue'
import ScriptStudio from './ScriptStudio.vue'
import ImportPanel from './ImportPanel.vue'
import DialogueStage from './DialogueStage.vue'
import {profile} from './people'
import CharacterCards from './CharacterCards.vue'
import SceneOutline from './SceneOutline.vue'
import NarrativePackage from './NarrativePackage.vue'
import PaintingHome from './PaintingHome.vue'
type Row = Record<string,any>
const characterFocus=ref('')
const analysisRunning=ref(false)
const dialogueOpen=ref(false)
const home=ref(true),homeProjects=ref<Row[]>([]),lastProject=ref(localStorage.getItem('animatedscroll-project')||'')
const deleteProjectOpen=ref(false),deletedProject=ref<Row|null>(null)
const p=ref<Row|null>(null), projects=ref<Row[]>([]), step=ref(0), busy=ref(false), error=ref(''), notice=ref(''), selected=ref(''), selectedScene=ref(''), proposal=ref<Row|null>(null), history=ref<Row[]>([]), event=ref<Row|null>(null), zoom=ref(100)
const source=ref({title:'',citation:'',location:'',text:''})
const steps=['画作探索','人物与边界','故事大纲','剧本与分镜','检查与导出']
const labels:Row={supported:'有依据',inference:'解释／推测',fiction:'虚构补充'}
const scene=computed(()=>p.value?.scenes.find((s:Row)=>s.id===selectedScene.value)||p.value?.scenes[0])
const allUnits=computed(()=>p.value?.scenes.flatMap((s:Row)=>s.units)||[])
const unit=computed(()=>allUnits.value.find((u:Row)=>u.id===selected.value))
const id=()=>crypto.randomUUID().slice(0,12)
async function api(path:string,method='GET',body?:any){const r=await fetch('/api'+path,{method,headers:body instanceof FormData?{}:{'Content-Type':'application/json'},body:body instanceof FormData?body:body?JSON.stringify(body):undefined});if(!r.ok){let v=await r.json();throw Error(typeof v.detail==='string'?v.detail:(v.detail?.message||'请求失败')+(v.detail?.characters?.length?'：'+v.detail.characters.map((c:Row)=>c.name).join('、'):''))}return r.json()}
async function run(fn:()=>Promise<void>){busy.value=true;error.value='';notice.value='';try{await fn()}catch(e){error.value=String(e)}finally{busy.value=false}}
async function list(){projects.value=await api('/projects')}
async function refreshHome(){await list();homeProjects.value=await Promise.all(projects.value.map(async(item:Row)=>{const project=await api('/projects/'+item.id);return {...item,image:project.image,paintingInfo:project.paintingInfo}}))}
async function openHome(){await run(async()=>{if(p.value)await persist();await refreshHome();home.value=true;dialogueOpen.value=false;await nextTick();window.scrollTo(0,0)})}
async function load(pid:string){await run(async()=>{p.value=await api('/projects/'+pid);localStorage.setItem('animatedscroll-project',pid);lastProject.value=pid;proposal.value=null;selected.value='';selectedScene.value='';characterFocus.value='';step.value=0;await list();home.value=false;await nextTick();window.scrollTo(0,0)})}
async function sample(){const existing=projects.value.find((item:Row)=>item.libraryKey==='zhekan');if(existing){await load(existing.id);return}await run(async()=>{p.value=await api('/sample?example=zhekan','POST',{});localStorage.setItem('animatedscroll-project',p.value!.id);await list()})}
async function create(){await run(async()=>{p.value=await api('/projects','POST',{});localStorage.setItem('animatedscroll-project',p.value!.id);lastProject.value=p.value!.id;step.value=0;home.value=false;await list();await nextTick();window.scrollTo(0,0)})}
async function deleteProject(){await run(async()=>{await persist();deletedProject.value=await api('/projects/'+p.value!.id+'/archive','POST',{version:p.value!.version});deleteProjectOpen.value=false;dialogueOpen.value=false;proposal.value=null;selected.value='';selectedScene.value='';characterFocus.value='';p.value=null;home.value=true;lastProject.value='';localStorage.removeItem('animatedscroll-project');await refreshHome();step.value=0;notice.value='项目已删除，可撤销本次删除'})}
async function restoreProject(){if(!deletedProject.value)return;await run(async()=>{p.value=await api('/projects/'+deletedProject.value!.id+'/restore','POST',{version:deletedProject.value!.version});deletedProject.value=null;localStorage.setItem('animatedscroll-project',p.value!.id);lastProject.value=p.value!.id;if(home.value)await refreshHome();else await list();notice.value='项目已恢复'})}
async function removeCharacter(cid:string){await run(async()=>{await persist();p.value=await api('/projects/'+p.value!.id+'/characters/'+cid+'/remove','POST',{version:p.value!.version});characterFocus.value='';await list();notice.value='人物已删除，相关引用已更新；原有正文请重新核对'})}
async function persist(){p.value=await api('/projects/'+p.value!.id,'PUT',p.value);await list()}
async function generateIntent(title:string){await run(async()=>{const result=await api('/projects/'+p.value!.id+'/intent/draft','POST',{version:p.value!.version,title});p.value!.intent=result.intent;p.value!.intentTitle=result.title;p.value!.intentOrigin='llm_draft';notice.value='创作意图草稿已填入，请审查、修改后保存'})}
async function save(){await run(async()=>{await persist();notice.value='已保存到本地'})}
async function generate(task:string,unitId=''){
 await run(async()=>{await persist();if(task!=='extract'&&(!p.value!.characters.length||blockers.value.length)){error.value='请先核对并确认：'+(blockers.value.map((c:Row)=>c.name).join('、')||'尚未建立人物');return}const result=await api(`/projects/${p.value!.id}/generate`,'POST',{version:p.value!.version,task,sceneId:scene.value?.id||'',unitId,instruction:instruction.value});if(result.proposal)proposal.value=result;else p.value=result;notice.value='生成完成，请人工核查';instruction.value=''})
}
async function generateDraft(stage:string,regenerate=false){
 await run(async()=>{await persist();p.value=await api(`/projects/${p.value!.id}/workflow/draft`,'POST',{version:p.value!.version,stage,regenerate});if(stage==='scripts')selected.value=p.value!.scenes[0]?.units[0]?.id||'';notice.value='初稿已填好，可直接修改并保存'})
}
async function ensureDraft(){
 if(!p.value||busy.value||analysisRunning.value)return
 if(step.value===1&&!p.value.workflowPrepared)await generateDraft('prepare')
 if(step.value===2&&!p.value.scenes.length)await generateDraft('outline')
 if(step.value===3&&p.value.scenes.length===p.value.sceneCount&&p.value.scenes.some((s:Row)=>!s.units.length))await generateDraft('scripts')
}
watch(step,()=>{void ensureDraft()})
const instruction=ref('')
const blockers=computed(()=>p.value?.characters.filter((c:Row)=>!c.confirmed)||[])
async function confirmRole(c:Row){await run(async()=>{const cid=c.id;await persist();p.value=await api(`/projects/${p.value!.id}/characters/${cid}/confirm`,'POST',{version:p.value!.version,characterId:cid})})}
function locateRole(cid:string){characterFocus.value=cid;step.value=1;setTimeout(()=>document.getElementById('character-'+cid)?.scrollIntoView({block:'center',behavior:'smooth'}),0)}
async function apply(){await run(async()=>{p.value=await api(`/projects/${p.value!.id}/apply`,'POST',proposal.value);proposal.value=null;selected.value=''})}
async function addSource(){if(!source.value.text.trim()||!source.value.title.trim()){error.value='请填写资料标题及原文';return}p.value!.sources.push({...source.value,id:id(),version:1});source.value={title:'',citation:'',location:'',text:''};await save()}
async function importText(e:Event){const f=(e.target as HTMLInputElement).files?.[0];if(f){source.value.text=await f.text();source.value.title ||= f.name}}
async function upload(e:Event){const f=(e.target as HTMLInputElement).files?.[0];if(!f)return;await run(async()=>{await persist();const form=new FormData();form.append('file',f);p.value=await api(`/projects/${p.value!.id}/image?version=${p.value!.version}`,'POST',form)})}
let start:{x:number,y:number}|null=null
function point(e:PointerEvent){const r=(e.currentTarget as HTMLElement).getBoundingClientRect();return {x:Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),y:Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))}}
function down(e:PointerEvent){start=point(e);(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)}
function up(e:PointerEvent){if(!start)return;const end=point(e);if(Math.abs(end.x-start.x)>.01&&Math.abs(end.y-start.y)>.01)p.value!.annotations.push({id:id(),x:Math.min(start.x,end.x),y:Math.min(start.y,end.y),w:Math.abs(end.x-start.x),h:Math.abs(end.y-start.y),description:'',kind:'scene',characterId:'',confirmed:false});start=null}
function addCharacter(){p.value!.characters.push({id:id(),name:'新角色',identity:'',relationships:'',knowledge:'',evidence:'',confirmed:false})}
function showStoryboard(){document.getElementById('storyboard-script')?.scrollIntoView({block:'start',behavior:'smooth'})}
function addRef(){unit.value.references.push({sourceId:'',sourceVersion:1,annotationId:'',quote:''})}
function refChanged(r:Row){const s=p.value!.sources.find((s:Row)=>s.id===r.sourceId);r.sourceVersion=s?.version||1;r.annotationId=''}
async function audit(status:string){const selectedId=unit.value.id;await run(async()=>{await persist();const current=allUnits.value.find((u:Row)=>u.id===selectedId);current.status=status;await persist();notice.value='审核状态已保存'})}
async function confirmPackageSource(sid:string){await run(async()=>{await persist();p.value=await api('/projects/'+p.value!.id+'/sources/'+sid+'/confirm','POST',{version:p.value!.version});notice.value='来源核对状态已保存'})}
function navigatePackage(nextStep:number,sid=''){if(sid){selectedScene.value=sid;selected.value=''}step.value=nextStep}
async function downloadNarrative(req:{format:string;draft:boolean;reviewed:boolean}){await run(async()=>{await persist();const r=await fetch(`/api/projects/${p.value!.id}/narrative/export?format=${req.format}&draft=${req.draft}&reviewed=${req.reviewed}`);if(!r.ok){const value=await r.json();throw Error(typeof value.detail==='string'?value.detail:value.detail?.message||'导出失败')}const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download=`narrative-${req.draft?'draft':'approved'}.${req.format}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);notice.value='叙事包已导出'})}
async function logs(){await run(async()=>{history.value=await api(`/projects/${p.value!.id}/events`)})}
async function download(format:string,draft:boolean){await run(async()=>{await persist();const r=await fetch(`/api/projects/${p.value!.id}/export?format=${format}&draft=${draft}`);if(!r.ok)throw Error((await r.json()).detail);const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download=`${draft?'draft':'approved'}-story.${format}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)})}
onMounted(async()=>{await run(refreshHome)})
</script>

<template>
<header class="app-header">
 <h1>AnimatedScroll</h1>
 <div class="header-workspace">
  <div class="project-switcher">
   <button v-if="!home" class="back-to-paintings" :disabled="busy||analysisRunning" @click="openHome">← 选择画作</button>
   <select v-if="!home" aria-label="选择项目" :disabled="busy||analysisRunning" :value="p?.id||''" @change="load(($event.target as HTMLSelectElement).value)"><option disabled value="">选择项目</option><option v-for="item in projects" :key="item.id" :value="item.id">{{item.title}}</option></select>
   <button :disabled="busy||analysisRunning" @click="create">＋ 新项目</button>
   <button v-if="!home" class="project-delete" :disabled="busy||analysisRunning||!p" @click="deleteProjectOpen=true">删除项目</button>
  </div>
  <div v-if="!home" class="header-primary-actions"><button :disabled="busy||analysisRunning||!p" @click="dialogueOpen=true">入画对话 <span aria-hidden="true">↗</span></button><button class="primary" :disabled="busy||analysisRunning||!p" @click="save">保存版本</button></div>
 </div>
</header>
<div v-if="error" class="banner error" role="alert">{{error}} <button :disabled="busy||analysisRunning" @click="p&&load(p.id)">重新加载已保存版本</button></div><div v-if="notice||deletedProject" class="banner">{{notice}} <button v-if="deletedProject" :disabled="busy||analysisRunning" @click="restoreProject">撤销删除项目</button></div><div v-if="busy" class="banner" role="status">正在处理，请稍候……</div>
<PaintingHome v-if="home" :projects="homeProjects" :busy="busy||analysisRunning" :last-id="lastProject" @open="load" @create="create"/>
<main v-else-if="p"><nav><button :disabled="busy||analysisRunning" v-for="(s,i) in steps" :class="{active:step===i}" @click="step=i"><b>0{{Number(i)+1}}</b>{{s}}</button></nav>
<fieldset :disabled="busy||analysisRunning"><div v-if="step!==0" class="projectline"><input class="project-title" v-model="p.title"><span>本地项目 · v{{p.version}} · {{allUnits.filter((u:Row)=>u.status==='approved').length}} / {{allUnits.length}} 单元已批准</span></div>
<div v-if="step>1&&step<4&&p.reviewNotice" class="banner">{{p.reviewNotice}}</div>
<ImportPanel v-if="step===0" :key="p.id" :project="p" @replace="p=$event;list()" @running="analysisRunning=$event"/>
<CharacterCards v-if="step===1" :project="p" :focus-id="characterFocus" @confirm="confirmRole" @remove="removeCharacter" @add="addCharacter" @prepare="generateDraft('prepare',true)" @generate-intent="generateIntent" @save-intent="save"/>
<SceneOutline v-if="step===2" :key="p.id" :project="p" @generate="generateDraft('outline',true)" @save="save"/>
<ScriptStudio v-if="step===3" :key="p.id" :project="p" v-model:scene-id="selectedScene" v-model:unit-id="selected" v-model:instruction="instruction" @save="save" @generate="(task:string,uid?:string)=>generate(task,uid)" @draft="generateDraft('scripts')" @audit="audit" @replace="p=$event" @busy="analysisRunning=$event"/>
<NarrativePackage v-if="step===4" :key="p.id" :project="p" :history="history" @save="save" @navigate="navigatePackage" @preview="dialogueOpen=true" @download="downloadNarrative" @check="generate('check')" @logs="logs" @audit-export="download($event,true)" @confirm-source="confirmPackageSource"/>
<footer><button v-if="step<4" class="primary" @click="step++">下一步 →</button></footer></fieldset>
<div v-if="proposal" class="modal"><article><h2>修改提案 · 比较后采用</h2><p>本场锁定内容会保留。采用后需要重新审核。</p><div class="columns"><div><h3>当前内容</h3><p v-for="u in scene.units.filter((u:Row)=>!proposal?.unitId||u.id===proposal.unitId)">{{u.text}}</p></div><div><h3>建议内容</h3><div v-for="u in proposal.proposal.units" class="card"><span class="tag" :class="u.category">{{labels[u.category]}}</span><p>{{u.text}}</p><small>{{u.rationale}}</small></div></div></div><div class="actions"><button :disabled="busy||analysisRunning" class="primary" @click="apply">采用提案</button><button :disabled="busy||analysisRunning" @click="proposal=null">保留原稿</button></div></article></div>
</main><div v-else class="welcome"><small>HISTORICALLY GROUNDED NARRATIVE</small><h2>让故事生动，让依据可见。</h2><p>从一段古画、几份资料和一个创作意图开始。</p><button class="primary" :disabled="busy||analysisRunning" @click="create">创建第一个项目</button></div>
<div v-if="deleteProjectOpen&&p" class="modal" role="dialog" aria-modal="true" aria-labelledby="delete-project-title"><article><h2 id="delete-project-title">删除项目「{{p.title}}」？</h2><p>项目将从选择列表移除，可以撤销本次删除。删除前会保存当前修改。</p><div class="actions"><button :disabled="busy||analysisRunning" @click="deleteProjectOpen=false">取消</button><button :disabled="busy||analysisRunning" @click="deleteProject">确认删除项目</button></div></article></div>
<DialogueStage v-if="dialogueOpen&&p" :project="p" @close="dialogueOpen=false"/>
</template>
