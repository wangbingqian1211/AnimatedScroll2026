<script setup lang="ts">
import {ref,computed,watch} from 'vue'
import {useStudio,state,states} from '../studioContext'
import EntityActions from '../EntityActions.vue'
import ReviewUnit from '../ReviewUnit.vue'
import ReviewBadge from '../ReviewBadge.vue'
import AppIcon from '../AppIcon.vue'
import SmartEditButton from '../SmartEditButton.vue'
import SmartEditBatch from '../SmartEditBatch.vue'
import RegionPicker from '../RegionPicker.vue'
import Portrait from '../Portrait.vue'
import VideoPanel from '../VideoPanel.vue'
import MediaPreviewPanel from '../MediaPreviewPanel.vue'
import VideoBudgetPanel from '../VideoBudgetPanel.vue'
const s=useStudio(),selected=ref(''),scope=ref('narrative'),checked=ref<string[]>([]),showLegacy=ref(false)
const clues=computed(()=>s.entries('clue').filter((c:any)=>scope.value==='all'||c.draft.type==='narrative'))
const visibleIds=computed<string[]>(()=>clues.value.map((c:any)=>c.id))
const shots=computed(()=>s.entries('storyboard').filter((shot:any)=>visibleIds.value.includes(shot.draft.clueId)).sort((a:any,b:any)=>visibleIds.value.indexOf(a.draft.clueId)-visibleIds.value.indexOf(b.draft.clueId)))
const r=computed(()=>shots.value.find((r:any)=>r.id===selected.value)||shots.value[0])
const mediaIds=computed(()=>checked.value.filter(id=>shots.value.some((shot:any)=>shot.id===id)))
watch(scope,()=>{checked.value=[]})
const dialogueSpeaker=ref(''),customSpeaker=ref(''),dialogueTiming=ref('镜头开始时'),customTiming=ref(''),dialogueText=ref('')
function appendDialogue(){
 const name=dialogueSpeaker.value==='custom'?customSpeaker.value.trim():dialogueSpeaker.value
 const timing=dialogueTiming.value==='custom'?customTiming.value.trim():dialogueTiming.value
 if(!r.value||!name||!timing||!dialogueText.value.trim())return
 const line=name+'（'+timing+'）：'+dialogueText.value.trim()
 r.value.draft.dialogue=[r.value.draft.dialogue?.trim(),line].filter(Boolean).join('\n')
 dialogueText.value='';s.scheduleAutosave()
}
watch(()=>r.value?.id,()=>{dialogueSpeaker.value='';customSpeaker.value='';dialogueTiming.value='镜头开始时';customTiming.value='';dialogueText.value=''})
function generate(regenerate=false,one=''){void s.generateStep('storyboards',one?[one]:checked.value.length?checked.value:visibleIds.value,regenerate,'storyboard',scope.value)}
watch(()=>s.focus.value,(v:string)=>{if(v.startsWith('storyboard:'))selected.value=v.split(':')[1]},{immediate:true})
</script>
<template><VideoBudgetPanel/><section class="shot-scope"><label>生成范围<select v-model="scope"><option value="narrative">仅叙事线索（默认）</option><option value="all">全部线索</option></select></label><div class="actions"><button :disabled="s.generating.value||!visibleIds.length" @click="generate()">{{checked.length?'生成所选线索的缺失提示词':'生成当前范围的缺失提示词'}}</button><button :disabled="s.generating.value||!checked.length" @click="generate(true)">重新生成所选提示词</button></div><SmartEditButton kind="storyboard" :item-ids="shots.filter((shot:any)=>checked.includes(shot.draft.clueId)).map((shot:any)=>shot.id)" label="所选分镜"/><p>当前 {{clues.length}} 条线索，已勾选 {{checked.length}} 条。勾选用于指定生成范围；内容和关联资料检查通过后才能生成提示词。</p><label v-for="c in clues" :key="c.id" class="shot-check"><input type="checkbox" :value="c.id" v-model="checked">{{c.draft.name}}</label></section><details class="legacy-media" @toggle="showLegacy=($event.target as HTMLDetailsElement).open"><summary>旧版媒体记录</summary><MediaPreviewPanel v-if="showLegacy" history-only :ids="mediaIds" :scope="scope" :visible-ids="visibleIds"/></details><div class="workspace-two"><aside class="entity-rail shot-rail"><h2>分镜管理</h2><small>每条线索一个分镜，独立制作。</small><button v-for="(shot,index) in shots" :key="shot.id" class="shot-rail-item" :aria-pressed="shot.id===r?.id" :class="{selected:shot.id===r?.id}" @click="s.selectEntity('storyboard',shot.id)"><span class="shot-number">{{Number(index)+1}}</span><span class="shot-label"><b>{{s.rec('clue',shot.draft.clueId)?.draft.name||shot.draft.name}}</b><ReviewBadge :unit="s.unit('storyboard:'+shot.id)"/></span></button></aside><article v-if="r" :data-entity-key="'storyboard:'+r.id"><fieldset :disabled="s.locked('storyboard',r.id)"><div class="rail-heading"><h2>{{s.rec('clue',r.draft.clueId)?.draft.name}}</h2><SmartEditButton kind="storyboard" :item-ids="[r.id]" label="当前分镜"/></div><button @click="s.navigate('clues','clue:'+r.draft.clueId)">查看对应线索</button><details class="shot-settings-panel"><summary><span class="shot-settings-title">参与人物与画面区域<small>选择出场人物，调整画面范围</small></span><span class="shot-settings-toggle" aria-hidden="true"></span></summary><fieldset><legend>参与人物</legend><label v-for="c in s.castEntries()"><input type="checkbox" :value="c.id" v-model="r.draft.characterIds" @change="r.draft.participantsConfirmed=false">{{c.draft.name}}</label><small>{{r.draft.characterIds.length?'已选择参与人物':'无人出镜'}}</small></fieldset><RegionPicker :image="s.p.value.image" v-model="r.draft.region"/><Portrait v-if="r.draft.region" :url="s.p.value.image" :box="r.draft.region"/></details><details class="shot-settings-panel"><summary><span class="shot-settings-title">人物台词<small>选择发言人物和时机，编写或自定义台词</small></span><span class="shot-settings-toggle" aria-hidden="true"></span></summary><div class="dialogue-editor"><div class="compact-grid"><label>发言人物<select v-model="dialogueSpeaker"><option disabled value="">请选择人物</option><option v-for="person in s.castEntries().filter((p:any)=>r.draft.characterIds.includes(p.id))" :key="person.id" :value="person.draft.name">{{person.draft.name}}</option><option value="custom">自定义人物</option></select><input v-if="dialogueSpeaker==='custom'" v-model="customSpeaker" placeholder="填写发言人名称"></label><label>发言时机<select v-model="dialogueTiming"><option>镜头开始时</option><option>主要动作进行时</option><option>主要动作结束后</option><option>镜头结束前</option><option value="custom">自定义时机</option></select><input v-if="dialogueTiming==='custom'" v-model="customTiming" placeholder="例如：朱云攀住栏杆时，或第 2 秒"></label></div><label>台词内容<textarea rows="2" v-model="dialogueText" placeholder="填写这次发言的内容"/></label><button type="button" :disabled="!dialogueText.trim()||!dialogueSpeaker||(dialogueSpeaker==='custom'&&!customSpeaker.trim())||(dialogueTiming==='custom'&&!customTiming.trim())" @click="appendDialogue">＋ 添加台词</button><label class="dialogue-script">本镜完整台词（可直接修改）<textarea rows="4" v-model="r.draft.dialogue" placeholder="暂无台词，留空则无对白。"/></label><small>添加后可在完整台词中修改或删除。发言时机将随台词一起传入视频提示词。</small></div></details><fieldset :disabled="s.locked('storyboard',r.id,'prompt')"><details class="shot-settings-panel"><summary><span class="shot-settings-title">动作与镜头设置<small>调整动作、运镜、画风及首尾画面</small></span><span class="shot-settings-toggle" aria-hidden="true"></span></summary><label>主体与动作<textarea v-model="r.draft.action"/></label><label>镜头运动<textarea v-model="r.draft.camera"/></label><label>风格与限制<textarea v-model="r.draft.style"/></label><div class="compact-grid"><label>起始画面<textarea rows="5" v-model="r.draft.startFrame"/></label><label>结束画面<textarea rows="5" v-model="r.draft.endFrame"/></label></div></details><div class="shot-generate-actions"><button :disabled="s.busy.value||s.generating.value" title="生成期间不能重复提交任务" class="primary" @click="generate(true,r.id)"><AppIcon name="ai" :size="14"/>{{r.draft.prompt?.trim()?'重新生成分镜提示词':'生成分镜提示词'}}</button><small>生成提示词和首尾画面描述；视频需在下方单独提交。</small></div></fieldset><ReviewUnit :unit-id="'storyboard:'+r.id" label="确认此分镜"/></fieldset><VideoPanel :storyboard-id="r.id"/></article><article v-else><div class="empty">生成线索后即可制作分镜。</div></article></div></template>

<style scoped>.legacy-media{margin:0 0 18px;color:#8a957f;font-size:11px}.shot-scope{padding:18px;border:1px solid var(--border);border-radius:10px;margin-bottom:18px}.shot-scope>label:first-child{max-width:280px}.shot-scope p{font-size:12px;color:#718177}.shot-check{display:inline-flex;align-items:center;gap:6px;margin:8px 18px 8px 0;font-size:12px}.shot-check input{width:auto}</style>

<style scoped>.shot-rail .shot-rail-item{display:flex;width:100%;align-items:flex-start;gap:10px;padding:12px;margin:8px 0;box-sizing:border-box;border:1px solid transparent;border-radius:9px;background:transparent;text-align:left}.shot-rail .shot-rail-item.selected{background:#edf4e9;border-color:#94ad89}.shot-rail .shot-rail-item:hover:not(.selected){background:#f5f7f2;border-color:transparent}.shot-number{flex:0 0 22px;color:#84917f;font-size:12px;padding-top:2px}.shot-label{display:flex;flex:1;min-width:0;flex-direction:column;gap:8px}.shot-label b{white-space:normal;overflow-wrap:anywhere;line-height:1.5}.shot-label :deep(.review-badge){white-space:normal;font-size:11px}.shot-rail-item:focus-visible{outline:2px solid #4f8a78;outline-offset:2px}</style>

<style scoped>.shot-generate-actions{display:flex;align-items:flex-start;flex-direction:column;gap:9px;margin:20px 0 24px}.shot-generate-actions small{color:#7e897a}.shot-dialogue{margin:20px 0;padding:18px;border:1px solid #dce5d7;border-radius:10px;background:#fafcf7}.shot-dialogue h3{margin:0 0 10px}.shot-dialogue p,.shot-dialogue small{font-size:12px;color:#778570}.shot-dialogue textarea{margin-top:10px}</style>

<style scoped>
.shot-settings-panel{margin:20px 0;border:1px solid #b9cdb8;border-radius:11px;background:#fffefa;overflow:hidden}
.shot-settings-panel>summary{display:flex;align-items:center;justify-content:space-between;gap:16px;list-style:none;padding:17px 18px;background:#edf3e7;cursor:pointer;color:#315c48;border-bottom:1px solid transparent}
.shot-settings-panel>summary::-webkit-details-marker{display:none}
.shot-settings-panel>summary:hover{background:#e3edda}
.shot-settings-panel>summary:focus-visible{outline:2px solid #416f56;outline-offset:-3px}
.shot-settings-title{font-size:15px;font-weight:600;line-height:1.5}
.shot-settings-title small{display:block;margin-top:4px;font-size:12px;font-weight:400;color:#687d63}
.shot-settings-toggle{flex-shrink:0;min-width:65px;padding:6px 10px;border:1px solid #a8c09f;border-radius:7px;background:#fffefa;text-align:center;font-size:12px;font-weight:500}
.shot-settings-toggle::before{content:'展开 ＋'}
.shot-settings-panel[open]>summary{border-bottom-color:#d1dfc9;margin-bottom:16px}
.shot-settings-panel[open]>summary .shot-settings-toggle::before{content:'收起 −'}
.shot-settings-panel> :not(summary){margin-left:18px;margin-right:18px}
.shot-settings-panel> :last-child:not(summary){margin-bottom:18px}
</style>

<style scoped>.shot-generate-actions{align-items:flex-end;text-align:right;margin:18px 0 24px}.dialogue-editor{padding:0 0 4px}.dialogue-script{margin-top:18px}.dialogue-editor>small{display:block;color:#788574;font-size:12px;line-height:1.6}@media(max-width:600px){.shot-generate-actions{align-items:stretch;text-align:left}}</style>
