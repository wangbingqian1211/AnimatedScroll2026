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
import {outlineStep} from '../outlineStep'
const s=useStudio(),selected=ref('');const intent=computed(()=>s.rec('intent','main')),plots=computed(()=>[...s.entries('plot')].sort((a:any,b:any)=>(a.draft.order??9999)-(b.draft.order??9999))),plot=computed(()=>plots.value.find((r:any)=>r.id===selected.value)||plots.value[0])
const directionComposer=ref<InstanceType<typeof FeedbackComposer>>(),directionRunning=ref(false)
async function improveDirection(){
 if(directionRunning.value||s.generating.value)return
 const instruction=intent.value.draft.brief?.trim()
 ?'仅润色创作方向 brief：保留用户原有叙事意图、事件先后和人物立场，使表达清晰流畅，突出戏剧冲突；结合已有资料，不编造史实，不生成剧情。'
 :'仅生成创作方向 brief：根据当前画作、已整理的文献、人物和历史背景，提出一段具体且连贯的故事创作方向，说明叙事起点、主要冲突和收束，区分史实与创作设想；不生成剧情。'
 await directionComposer.value?.sendInstruction(instruction+' 同时根据最终brief更新theme、goal、audience、tone、framework、fiction、forbidden，所有修改属于intent/main。theme是具体主题短语；goal说明哪个人物经历什么变化、观众理解什么；audience和tone用易懂短语。framework逐条列出本故事有资料支持的关键事件；fiction逐条列出本故事准备补写的具体动作、对白或情节，并明确是创作设想；forbidden只列本故事不能改动的具体事实，不确定则留空。禁止空泛规则，例如“过渡动作均标虚构”“背景线索不得混入当天事件”“保留不确定性”。framework、fiction、forbidden的value使用JSON字符串数组，如["具体事件一","具体事件二"]，无内容用[]。保留可靠历史依据，不把虚构写进历史框架。')
}
function movePlot(offset:number){const list=[...plots.value],index=list.findIndex((r:any)=>r.id===plot.value?.id),next=index+offset;if(index<0||next<0||next>=list.length)return;[list[index],list[next]]=[list[next],list[index]];list.forEach((r:any,i:number)=>r.draft.order=i);s.scheduleAutosave()}
function add(){const r=s.add('plot',{order:plots.value.length,title:'新剧情',goal:'',body:'',connection:'',characterIds:[],clueIds:[],region:null});selected.value=r.id}
function addClue(){if(!plot.value)return;const r=s.add('clue',{name:'新叙事线索',summary:'',content:'',type:'narrative',parentId:'narrative',plotIds:[plot.value.id],characterIds:plot.value.draft.characterIds,units:[{id:id(),text:'',kind:'event',category:'fiction',rationale:'',speakerId:'',references:[]}]});plot.value.draft.clueIds.push(r.id);s.navigate('clues','clue:'+r.id)}
watch(()=>s.focus.value,(v:string)=>{if(v.startsWith('plot:')){selected.value=v.split(':')[1];outlineStep.value='plot'}},{immediate:true})
function openPlots(){outlineStep.value='plot';window.scrollTo(0,0)}
</script>
<template>
 <ReviewUnit unit-id="outline:main" label="确认整个大纲"/>
 <nav class="outline-steps" aria-label="大纲的两页">
  <button type="button" :class="{active:outlineStep==='direction'}" :aria-current="outlineStep==='direction'?'page':undefined" @click="outlineStep='direction'">创作方向</button>
  <button type="button" :class="{active:outlineStep==='plot'}" :aria-current="outlineStep==='plot'?'page':undefined" @click="openPlots">剧情</button>
 </nav>
 <article v-if="outlineStep==='direction'" id="story-direction" class="outline-sheet intent-panel" data-entity-key="intent:main">
  <div class="sheet-heading"><h2>你想怎样讲这幅画的故事？</h2><button class="smart-edit-button" type="button" :disabled="directionRunning||s.busy.value||s.generating.value" @click="improveDirection">{{directionRunning?'处理中…':intent.draft.brief?.trim()?'润色这段':'生成这段'}}</button></div>
  <textarea class="story-body" rows="8" v-model="intent.draft.brief" aria-label="你想怎样讲这幅画的故事？" placeholder="可留空，生成时根据资料给出默认方向。"/>
  <FeedbackComposer ref="directionComposer" direct @running="directionRunning=$event" storage-scope="intent-inline" :target="{kind:'intent',section:'content',itemIds:['main'],fields:['brief','theme','goal','audience','tone','framework','fiction','forbidden'],unitIds:[]}" label="创作方向"/>
  <EntityActions :record="intent"/>
  <div class="sheet-next"><button class="primary" type="button" @click="openPlots">下一步：编写剧情</button></div>
 </article>
 <article v-else class="outline-sheet" :data-entity-key="plot?'plot:'+plot.id:undefined">
  <div class="sheet-heading"><h2>编写剧情</h2><button type="button" @click="add">＋ 剧情</button></div>
  <div v-if="plots.length" class="plot-list">
   <button v-for="r in plots" :key="r.id" type="button" :class="{selected:r.id===plot?.id}" @click="s.selectEntity('plot',r.id)"><b>{{plots.indexOf(r)+1}}</b><span>{{r.draft.title}}</span></button>
  </div>
  <template v-if="plot">
   <fieldset :disabled="s.locked('plot',plot.id)">
    <label>剧情标题<input v-model="plot.draft.title"></label>
    <label>这则剧情要达成什么<textarea rows="3" v-model="plot.draft.goal"/></label>
    <label>具体怎么发展<textarea rows="8" v-model="plot.draft.body"/></label>
    <div class="plot-move"><button type="button" :disabled="plots[0]?.id===plot.id" @click="movePlot(-1)">前移</button><button type="button" :disabled="plots[plots.length-1]?.id===plot.id" @click="movePlot(1)">后移</button></div>
    <details class="more-plot">
     <summary>人物、画面和线索</summary>
     <SmartEditBatch kind="plot" :rows="plots" label="剧情"/>
     <div class="detail-title"><h3>{{plot.draft.title}}</h3><SmartEditButton kind="plot" :item-ids="[plot.id]" :label="plot.draft.title"/></div>
     <label>前后关联<textarea v-model="plot.draft.connection"/></label>
     <div class="chip-choices"><label v-for="c in s.castEntries()" :key="c.id"><input type="checkbox" :value="c.id" v-model="plot.draft.characterIds">{{c.draft.name}}</label></div>
     <RegionPicker :image="s.p.value.image" v-model="plot.draft.region"/>
     <Portrait v-if="plot.draft.region" :url="s.p.value.image" :box="plot.draft.region"/>
     <fieldset :disabled="s.locked('plot',plot.id,'clueIds')">
      <h3>子叙事线索</h3>
      <div class="plot-child-clue" v-for="c in s.entries('clue').filter((r:any)=>r.draft.type==='narrative'&&r.draft.plotIds?.length===1&&r.draft.plotIds[0]===plot.id)" :key="c.id"><div><b>{{c.draft.name}}</b><p>{{narrativeText(c.draft)}}</p></div><button type="button" @click="s.navigate('clues','clue:'+c.id)">编辑</button></div>
      <div class="actions"><button type="button" :disabled="s.busy.value||s.generating.value" @click="s.generate('plot_clues',plot.id)"><AppIcon name="ai" :size="14"/>生成子叙事线索</button><button type="button" @click="addClue">＋ 手动添加</button></div>
     </fieldset>
     <EntityActions :record="plot"/>
     <div class="actions"><button type="button" :disabled="s.busy.value||s.generating.value" @click="s.generate('plot',plot.id)"><AppIcon name="ai" :size="14"/>重生成本剧情及线索</button><button type="button" @click="s.remove(plot)">删除剧情</button></div>
    </details>
   </fieldset>
   <details class="more-plot"><summary>体验设置</summary><ExperienceSettings/></details>
  </template>
  <div v-else class="empty">还没有剧情。点右上角「生成剧本大纲」，或先添加一则。</div>
 </article>
</template>

<style scoped>
.outline-steps{display:flex;gap:8px;margin:0 0 18px}
.outline-steps button{border:0;border-radius:12px;background:transparent;color:#6a786c;font-size:18px;font-weight:600;padding:8px 16px}
.outline-steps button.active{background:#fffefa;color:#24382c;font-size:20px;box-shadow:inset 0 0 0 1px #d7e0d4}
.outline-sheet{max-width:860px;background:#fffefa;border:1px solid #e1e6da;border-radius:12px;padding:28px 32px 32px}
.sheet-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}
.sheet-heading h2{margin:0;font-size:22px;line-height:1.35;font-weight:640;color:#24382c}
.sheet-heading .smart-edit-button,.sheet-heading>button{font-size:15px;border-radius:12px;padding:8px 14px}
.story-body,.outline-sheet input,.outline-sheet textarea,.outline-sheet select{font-size:16px;line-height:1.7;border-radius:12px}
.story-body{display:block;width:100%;min-height:200px}
.sheet-next{display:flex;justify-content:flex-end;margin-top:18px}
.sheet-next .primary{font-size:16px;border-radius:12px;padding:10px 18px}
.plot-list{display:flex;flex-direction:column;gap:8px;margin-bottom:22px}
.plot-list button{display:flex;align-items:center;gap:12px;width:100%;text-align:left;border-radius:12px;background:#f7f8f2;font-size:16px;padding:12px 14px}
.plot-list button.selected{background:#eef4ea;box-shadow:inset 0 0 0 1.5px #8eaa86}
.plot-list b{font-size:14px;color:#6a786c;font-weight:600}
.plot-move{display:flex;gap:8px;margin:8px 0 4px}
.more-plot{margin-top:22px;border-top:1px solid #e1e6da;padding-top:14px}
.more-plot>summary{cursor:pointer;font-size:16px;font-weight:600;color:#3f5949}
.more-plot[open]>summary{margin-bottom:16px}
</style>
