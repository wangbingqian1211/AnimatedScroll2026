<script setup lang="ts">
import {ref,computed,watch} from 'vue'
import {useStudio,id,state,states} from '../studioContext'
import FeedbackComposer from '../FeedbackComposer.vue'
import EntityActions from '../EntityActions.vue'
import ReviewUnit from '../ReviewUnit.vue'
import ReviewBadge from '../ReviewBadge.vue'
import AppIcon from '../AppIcon.vue'
import SmartEditButton from '../SmartEditButton.vue'
import SmartEditBatch from '../SmartEditBatch.vue'
import RegionPicker from '../RegionPicker.vue'
import Portrait from '../Portrait.vue'
import ExperienceSettings from '../ExperienceSettings.vue'
import {narrativeText} from '../narrative'
const s=useStudio(),selected=ref('');const intent=computed(()=>s.rec('intent','main')),plots=computed(()=>[...s.entries('plot')].sort((a:any,b:any)=>(a.draft.order??9999)-(b.draft.order??9999))),plot=computed(()=>plots.value.find((r:any)=>r.id===selected.value)||plots.value[0])
const directionComposer=ref<InstanceType<typeof FeedbackComposer>>(),directionRunning=ref(false)
async function improveDirection(){
 if(directionRunning.value||s.generating.value)return
 const instruction=intent.value.draft.brief?.trim()
 ?'仅润色创作方向 brief：保留用户原有叙事意图、事件先后和人物立场，使表达清晰流畅，突出戏剧冲突；结合已有资料，不编造史实，不生成右侧剧情。'
 :'仅生成创作方向 brief：根据当前画作、已整理的文献、人物和历史背景，提出一段具体且连贯的故事创作方向，说明叙事起点、主要冲突和收束，区分史实与创作设想；不生成右侧剧情。'
 await directionComposer.value?.sendInstruction(instruction+' 同时根据最终brief更新theme、goal、audience、tone、framework、fiction、forbidden，所有修改属于intent/main。theme是具体主题短语；goal说明哪个人物经历什么变化、观众理解什么；audience和tone用易懂短语。framework逐条列出本故事有资料支持的关键事件；fiction逐条列出本故事准备补写的具体动作、对白或情节，并明确是创作设想；forbidden只列本故事不能改动的具体事实，不确定则留空。禁止空泛规则，例如“过渡动作均标虚构”“背景线索不得混入当天事件”“保留不确定性”。framework、fiction、forbidden的value使用JSON字符串数组，如["具体事件一","具体事件二"]，无内容用[]。保留可靠历史依据，不把虚构写进历史框架。')
}
function movePlot(offset:number){const list=[...plots.value],index=list.findIndex((r:any)=>r.id===plot.value?.id),next=index+offset;if(index<0||next<0||next>=list.length)return;[list[index],list[next]]=[list[next],list[index]];list.forEach((r:any,i:number)=>r.draft.order=i);s.scheduleAutosave()}
function add(){const r=s.add('plot',{order:plots.value.length,title:'新剧情',goal:'',body:'',connection:'',characterIds:[],clueIds:[],region:null});selected.value=r.id}
function addClue(){if(!plot.value)return;const r=s.add('clue',{name:'新叙事线索',summary:'',content:'',type:'narrative',parentId:'narrative',plotIds:[plot.value.id],characterIds:plot.value.draft.characterIds,units:[{id:id(),text:'',kind:'event',category:'fiction',rationale:'',speakerId:'',references:[]}]});plot.value.draft.clueIds.push(r.id);s.navigate('clues','clue:'+r.id)}
watch(()=>s.focus.value,(v:string)=>{if(v.startsWith('plot:'))selected.value=v.split(':')[1]},{immediate:true})
</script>
<template><ReviewUnit unit-id="outline:main" label="确认整个大纲"/><div class="outline-layout"><article id="story-direction" class="intent-panel" data-entity-key="intent:main"><div class="rail-heading"><h2>创作方向</h2><button class="smart-edit-button" type="button"  :disabled="directionRunning||s.busy.value||s.generating.value" @click="improveDirection">{{directionRunning?'处理中…':intent.draft.brief?.trim()?'润色创作方向':'生成创作方向'}}</button></div><label>你想怎样讲这幅画的故事？<textarea rows="5" v-model="intent.draft.brief" placeholder="可直接编辑正文，也可让 AI 根据资料生成方向或润色已有内容；留空则根据资料给出默认方向。"/></label><FeedbackComposer ref="directionComposer" direct @running="directionRunning=$event" storage-scope="intent-inline" :target="{kind:'intent',section:'content',itemIds:['main'],fields:['brief','theme','goal','audience','tone','framework','fiction','forbidden'],unitIds:[]}" label="创作方向"/><EntityActions :record="intent"/><ExperienceSettings/></article>
<div><article :data-entity-key="plot?'plot:'+plot.id:undefined"><div class="rail-heading"><h2>剧情</h2><button @click="add">＋ 剧情</button></div><div class="plot-strip"><button v-for="r in plots" :class="{selected:r.id===plot?.id}" @click="s.selectEntity('plot',r.id)"><b>{{plots.indexOf(r)+1}}. {{r.draft.title}}</b></button></div><SmartEditBatch kind="plot" :rows="plots" label="剧情"/><template v-if="plot"><fieldset :disabled="s.locked('plot',plot.id)"><div class="detail-title"><h3>{{plot.draft.title}}</h3><SmartEditButton kind="plot" :item-ids="[plot.id]" :label="plot.draft.title"/></div><div class="actions"><button :disabled="plots[0]?.id===plot.id" @click="movePlot(-1)">前移</button><button :disabled="plots[plots.length-1]?.id===plot.id" @click="movePlot(1)">后移</button></div><label>剧情标题<input v-model="plot.draft.title"></label><label>剧情目标<textarea v-model="plot.draft.goal"/></label><label>具体发展<textarea rows="6" v-model="plot.draft.body"/></label><label>前后关联<textarea v-model="plot.draft.connection"/></label><div class="chip-choices"><label v-for="c in s.castEntries()"><input type="checkbox" :value="c.id" v-model="plot.draft.characterIds">{{c.draft.name}}</label></div><RegionPicker :image="s.p.value.image" v-model="plot.draft.region"/><Portrait v-if="plot.draft.region" :url="s.p.value.image" :box="plot.draft.region"/><fieldset :disabled="s.locked('plot',plot.id,'clueIds')"><h3>子叙事线索</h3><small>每条是一小段情节，只属于当前剧情。</small><div class="plot-child-clue" v-for="c in s.entries('clue').filter((r:any)=>r.draft.type==='narrative'&&r.draft.plotIds?.length===1&&r.draft.plotIds[0]===plot.id)"><div><b>{{c.draft.name}}</b><p>{{narrativeText(c.draft)}}</p></div><button @click="s.navigate('clues','clue:'+c.id)">编辑</button></div><div class="actions"><button :disabled="s.busy.value||s.generating.value" title="生成期间不能重复提交任务" @click="s.generate('plot_clues',plot.id)"><AppIcon name="ai" :size="14"/>生成子叙事线索</button><button @click="addClue">＋ 手动添加</button></div><small>生成结果追加为草稿，不改写剧情，不覆盖已有线索。</small></fieldset><EntityActions :record="plot"/><div class="actions"><button :disabled="s.busy.value||s.generating.value" title="生成期间不能重复提交任务" @click="s.generate('plot',plot.id)"><AppIcon name="ai" :size="14"/>重生成本剧情及线索</button><button @click="s.remove(plot)">删除剧情</button></div></fieldset></template><div v-else class="empty">写下左边的创作方向，再点右上角「生成剧本大纲」。</div></article></div></div></template>

<style scoped>
.rail-heading .smart-edit-button{padding:8px 14px;border-radius:8px;color:#426450;background:#f4f7ef;border:1px solid #d6e0cf}.intent-panel>label>small{display:block;margin:5px 0 10px;color:#7b877c}
</style>
