<script setup lang="ts">
import {computed,nextTick,onMounted,onUnmounted,onActivated,onDeactivated,ref,watch} from 'vue'
import StoryFrames from './StoryFrames.vue'
import ReviewUnit from './ReviewUnit.vue'
import {useStudio} from './studioContext'
import {savedVideoReady} from './experienceRuntime'
const props=defineProps<{storyboardId:string}>(),s=useStudio()
const jobs=ref<any[]>([]),generation=ref<any>(null),budget=ref<any>(null),busy=ref(false),error=ref(''),forms=ref<Record<string,any>>({})
const submission=ref<{sid:string;message:string}|null>(null)
const submittingHere=computed(()=>submission.value?.sid===props.storyboardId)
const storageKey='animatedscroll-video-drafts:'+s.p.value.id
try{forms.value=JSON.parse(sessionStorage.getItem(storageKey)||'{}')}catch{}
const form=computed(()=>forms.value[props.storyboardId]||(forms.value[props.storyboardId]={text:'',saved:'',preview:null,accepted:false}))
const storyboardJobs=computed(()=>jobs.value.filter(j=>j.storyboardId===props.storyboardId))
const currentJobs=computed(()=>storyboardJobs.value.filter(j=>!j.archivedAt).sort((a,b)=>Date.parse(b.time)-Date.parse(a.time)))
const jobGroups=computed(()=>[{key:'latest',jobs:currentJobs.value.slice(0,1)},{key:'history',jobs:currentJobs.value.slice(1)}].filter(group=>group.jobs.length))
const failedCount=computed(()=>currentJobs.value.filter(j=>['failed','cancelled','canceled'].includes(j.status)).length)
async function clearFailed(){await run(async()=>{await s.api(base()+`/storyboards/${props.storyboardId}/videos/clear-failed`,'POST',{});await poll(true)})}
const ready=computed(()=>form.value.preview?.customized&&form.value.text===form.value.saved)
const submitBlocker=computed(()=>{
 if(!generation.value||!budget.value)return '正在读取视频服务和额度…'
 if(!generation.value.ready)return generation.value.message||'视频服务尚未配置'
 if(budget.value.blocked)return '有一笔视频任务状态待核实，请先查询原任务'
 if(budget.value.remainingCount<1||budget.value.remainingCny<5)return '本项目视频额度不足'
 if(!ready.value)return '请先保存当前最终提示词'
 if(!form.value.accepted)return '请勾选上方审核确认'
 return ''
})
watch(forms,()=>{try{sessionStorage.setItem(storageKey,JSON.stringify(forms.value))}catch{}},{deep:true})
const base=()=>`/projects/${s.p.value.id}`
async function run(fn:()=>Promise<void>){busy.value=true;error.value='';try{await fn()}catch(e:any){error.value=e.message||String(e)}finally{busy.value=false}}
async function poll(force=false){if(!force&&(document.hidden||s.page.value!=='storyboards'))return;const pid=s.p.value.id,result=await s.api(base()+'/videos');if(s.p.value?.id===pid){const changed=JSON.stringify(jobs.value)!==JSON.stringify(result.jobs);jobs.value=result.jobs;generation.value=result.generation;budget.value=result.budget;if(changed)await s.updateChecklist()}}
async function prepare(){await run(async()=>{await s.saveAll();const sid=props.storyboardId;const preview=await s.api(base()+`/storyboards/${sid}/video-prompt`);forms.value[sid]={preview,text:preview.prompt,saved:preview.customized?preview.prompt:'',accepted:false}})}
let previewSequence=0
let savingPrompt=false
async function refreshFinal(){
 const sid=props.storyboardId,pid=s.p.value.id,ticket=++previewSequence
 if(savingPrompt)return
 if(!s.rec('storyboard',sid)?.draft.prompt?.trim()||s.generating.value)return
 await run(async()=>{
  const preview=await s.api(base()+`/storyboards/${sid}/video-prompt`)
  if(ticket!==previewSequence||pid!==s.p.value.id||sid!==props.storyboardId)return
  const previous=forms.value[sid]
  if(previous){previous.preview=preview;return}
  forms.value[sid]={preview,text:preview.prompt,saved:preview.customized?preview.prompt:'',accepted:false}
  if(!preview.customized)await savePrompt()
 })
}
watch(()=>[props.storyboardId,s.rec('storyboard',props.storyboardId)?.revision,s.generating.value],()=>{void refreshFinal()},{immediate:true})
async function savePrompt(){
 if(savingPrompt)return
 const sid=props.storyboardId,f=forms.value[sid],text=f.text
 savingPrompt=true;++previewSequence
 try{await run(async()=>{
  await s.saveAll()
  const latest=await s.api(base()+`/storyboards/${sid}/video-prompt`)
  const p=await s.api(base()+`/storyboards/${sid}/video-prompt`,'PUT',{version:s.p.value.version,text,baseFingerprint:latest.baseFingerprint})
  await s.legacy(p)
  f.saved=text;f.text=text;f.accepted=false
  f.preview=await s.api(base()+`/storyboards/${sid}/video-prompt`)
 })}finally{savingPrompt=false}
}

async function submitVideo(previous?:any){
 if(busy.value||submission.value||submitBlocker.value)return
 const sid=props.storyboardId,f=form.value
 submission.value={sid,message:'正在保存并检查当前分镜…'}
 try{await run(async()=>{
  await nextTick()
  await s.saveAll()
  submission.value={sid,message:'正在确认提示词与人物参考…'}
  await s.legacy(await s.api(base()+`/storyboards/${sid}/confirm-video`,'POST',{version:s.p.value.version}))
  const request:any={version:s.p.value.version,storyboardId:sid}
  if(previous){const keys=f.retryIds||={};keys[previous.id]||=crypto.randomUUID();request.retryOf=previous.id;request.requestId=keys[previous.id]}
  submission.value={sid,message:'正在提交视频任务，请稍候…'}
  const job=await s.api(base()+'/videos','POST',request)
  if(job?.id)jobs.value=[job,...jobs.value.filter(item=>item.id!==job.id)]
  f.accepted=false
  submission.value={sid,message:'任务已提交，正在读取生成进度…'}
  await poll(true)
 })}finally{submission.value=null}
}
async function generate(){await submitVideo(storyboardJobs.value.find(j=>['failed','submission_unknown','cost_unknown','cancelled','canceled'].includes(j.status)))}
async function copySubmittedPrompt(job:any){await run(async()=>{await navigator.clipboard.writeText(job.prompt)})}
async function select(job:any){await run(async()=>{await s.saveAll();await s.legacy(await s.api(base()+`/storyboards/${props.storyboardId}/experience-video`,'POST',{version:s.p.value.version,jobId:job.id}));await poll()})}
async function refresh(job:any){await run(async()=>{await s.api(base()+`/videos/${job.id}/refresh`,'POST',{});await poll()})}
async function retry(job:any){await submitVideo(job)}
let timer:ReturnType<typeof setInterval>|undefined
function pause(){clearInterval(timer);timer=undefined}
function startPolling(){if(timer)return;void run(()=>poll(true));timer=setInterval(()=>{poll().catch(()=>{error.value='暂时无法查询视频进度，请重试'})},8000)}
onMounted(startPolling);onActivated(startPolling)
onDeactivated(pause);onUnmounted(pause)
</script>
<template>
<section class="extension-panel video-panel" aria-label="独立分镜视频制作">
 <h3>分镜视频制作</h3><p class="muted">审核本镜的情节、人物参考与最终导演稿。按当前剧情重新安排画面，原画仅参考人物、场景元素和画风。</p>
 <StoryFrames :storyboard-id="storyboardId" @selected="refreshFinal"/>
 <p v-if="error" class="extension-error" role="alert">{{error}}</p>
 <fieldset :disabled="busy"><div class="actions"><button v-if="error" @click="refreshFinal">重新读取最终提示词</button><span v-if="busy" role="status">正在处理…</span></div>
 <template v-if="form.preview"><p class="muted">{{form.preview.generation.ready?form.preview.model+' · '+form.preview.parameters.resolution+' · '+form.preview.parameters.duration+' 秒':'视频模型待接入，可先保存和审核导演稿'}}</p><p>{{form.preview.references.map((r:any)=>r.label+'：'+r.name).join('；')}}</p>
 <div class="prompt-audit" v-if="form.preview.audit"><h4>提示词检查 <a :href="form.preview.audit.guideUrl" target="_blank" rel="noopener noreferrer">官方写作指南 ↗</a></h4><div class="audit-checks"><span v-for="check in form.preview.audit.checks">{{check.passed?'✓':'○'}} {{check.label}}</span></div><p v-for="warning in form.preview.audit.warnings" class="audit-warning">{{warning}}</p><p v-for="issue in form.preview.audit.errors" class="extension-error">{{issue}}</p><small>{{form.text!==form.saved?'修改后保存导演稿即可更新检查。 ':''}}{{form.preview.audit.note}}</small></div>
 <label>实际发送给视频模型的完整文本<textarea rows="10" v-model="form.text" @input="form.accepted=false"/></label>
 <div class="actions"><button @click="savePrompt" :disabled="!form.text.trim()">保存最终提示词</button></div>
 <label class="extension-check"><input type="checkbox" v-model="form.accepted" :disabled="!ready">我已审核已保存的导演稿与人物参考，同意本次占用 ¥5 额度</label>
 <button class="primary" @click="generate" :disabled="busy||!!submitBlocker">{{submittingHere?'正在提交…':!generation?'正在读取视频服务…':generation.ready?'生成此分镜视频 · ¥5 额度':'视频服务未就绪'}}</button><p v-if="submitBlocker&&!submittingHere" class="muted" role="status">{{submitBlocker}} <button v-if="!generation||!budget||!generation.ready" @click="run(()=>poll(true))">刷新服务状态</button></p></template></fieldset>
 <div class="actions" v-if="failedCount"><button :disabled="busy" @click="clearFailed">清理失败记录（{{failedCount}}）</button></div>
 <div v-if="submittingHere" class="video-submit-feedback" role="status" aria-live="polite"><span class="submit-spinner" aria-hidden="true"/><div><strong>正在准备视频生成</strong><p>{{submission?.message}}</p><small>请勿重复点击，任务提交后会自动显示生成进度。</small></div></div>
 <div v-if="!currentJobs.length&&!submittingHere" class="muted">暂无视频任务记录。</div>
 <component v-for="group in jobGroups" :key="storyboardId+group.key" :is="group.key==='history'?'details':'div'" :class="group.key==='history'?'video-history':'video-latest'">
 <summary v-if="group.key==='history'">历史记录 <span>{{group.jobs.length}} 条</span><small>展开查看之前的视频与生成任务</small></summary>
 <article v-for="job in group.jobs" :key="job.id" class="video-job"><div class="video-result-heading"><b>{{job.title}}</b><ReviewUnit v-if="job.status==='succeeded'" :unit-id="'video:'+job.id" label="确认此视频"/><span>{{({submission_unknown:'提交结果待核实',queued:'等待提交',submitting:'正在提交',pending:'等待生成',running:'生成中',succeeded:'已完成',failed:'失败',paused:'已暂停',download_failed:'下载未完成'} as Record<string,string>)[job.status]||job.status}}</span></div><p>{{job.message}}</p><details v-if="job.diagnostics" class="video-failure-details"><summary>失败详情</summary><p v-if="job.diagnostics.stage">失败环节：{{job.diagnostics.stage}}</p><p v-if="job.diagnostics.timestamp">记录时间：{{new Date(job.diagnostics.timestamp).toLocaleString()}}</p><p>本地任务：{{job.id}}</p><p v-if="job.diagnostics.httpStatus">HTTP 状态：{{job.diagnostics.httpStatus}}</p><p v-if="job.diagnostics.providerCode">错误代码：{{job.diagnostics.providerCode}}</p><p v-if="job.diagnostics.providerMessage">{{job.diagnostics.providerMessage}}</p><p v-if="job.diagnostics.traceId">请求追踪号：{{job.diagnostics.traceId}}</p><p v-if="job.remoteId">远端任务：{{job.remoteId}}</p></details><p v-if="!job.matchesCurrentScript" class="muted">相关制作内容有更新，视频仍可播放</p>
 <details v-if="job.prompt" class="submitted-prompt" open><summary>本次实际提交给 API 的提示词</summary><p class="muted">这是生成此视频时保存的原文，不随上方编辑内容变化。</p><p class="muted">{{job.model}} · {{job.resolution}} · {{job.duration}} 秒 · {{job.adapter==='dashscope'?'阿里百炼':job.adapter||'历史接口'}}</p><p v-if="job.referencePlan?.length" class="muted">提交的参考图：{{job.referencePlan.map((r:any)=>r.label+'：'+r.name).join('；')}}</p><textarea readonly rows="12" :value="job.prompt" aria-label="本次实际提交的视频提示词"/><button @click="copySubmittedPrompt(job)">复制提示词</button></details>
 <video v-if="job.status==='succeeded'&&job.videoUrl" controls preload="metadata" :src="job.videoUrl"/>
 <div class="actions"><a class="video-download" v-if="job.videoUrl" :href="job.videoUrl" :download="job.id+'.mp4'">下载视频</a><button v-if="job.status==='succeeded'&&job.availableForExperience" :disabled="busy" @click="select(job)">{{job.selectedForExperience?'已用于欣赏作品':'选为体验视频'}}</button><button v-if="['paused','download_failed','pending','running'].includes(job.status)" :disabled="busy" @click="refresh(job)">继续查询／下载原任务</button><button v-if="['failed','submission_unknown','cost_unknown','cancelled','canceled'].includes(job.status)" :disabled="busy||!ready||!form.accepted||!generation?.ready||budget?.blocked||!budget?.remainingCount||budget?.remainingCny<5" @click="retry(job)">审核提示词后重试（调用视频服务）</button></div></article>
 </component>
</section>
</template>

<style scoped>
.video-history{margin-top:20px;border:1px solid #d4dfca;border-radius:12px;background:#f5f8f0;padding:16px}
.video-history>summary{cursor:pointer;font-weight:600;color:#315e50;line-height:1.8}
.video-history>summary span{margin-left:10px;font-size:12px;font-weight:400}
.video-history>summary small{margin-left:16px;font-size:12px;font-weight:400;color:#718071}

.submitted-prompt{margin:16px 0;padding:16px;background:#f4f7ef;border:1px solid #d4dfca;border-radius:10px}.submitted-prompt summary{cursor:pointer;font-weight:600;color:#315e50}.submitted-prompt textarea{width:100%;box-sizing:border-box;margin:8px 0 12px;font-size:13px;line-height:1.8;background:#fffefa}.submitted-prompt .muted{font-size:12px;line-height:1.7}

.video-submit-feedback{display:flex;align-items:flex-start;gap:14px;padding:20px;margin-top:20px;border:1px solid #bfd2bc;border-radius:12px;background:#f0f6eb;color:#315e50}
.video-submit-feedback p{margin:7px 0;font-size:14px}.video-submit-feedback small{color:#718071}
.submit-spinner{width:20px;height:20px;flex-shrink:0;border:2px solid #ccdbca;border-top-color:#315e50;border-radius:50%;animation:submit-spin .8s linear infinite}
@keyframes submit-spin{to{transform:rotate(360deg)}}
@media(prefers-reduced-motion:reduce){.submit-spinner{animation:none}}

.video-job{padding:22px;margin-top:24px;border:1px solid #dce5d5;border-radius:14px;background:#fffefa;scroll-margin-top:100px;overflow:hidden}
.video-result-heading{display:flex;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:14px}
.video-result-heading>b{flex:1;min-width:180px;font-size:17px;color:#315e50}
.video-result-heading>span{padding:5px 10px;border-radius:20px;background:#edf3e7;font-size:12px;color:#42644d}
.video-job>p{font-size:13px;line-height:1.7;margin:12px 0;color:#718071}
.video-job video{display:block;width:100%;height:auto;max-height:520px;object-fit:contain;border-radius:10px;background:#171f1b;margin:16px auto}
.video-job>.actions{display:flex;justify-content:flex-end;align-items:center;gap:12px;padding-top:16px;margin-top:0;border-top:1px solid #e6eadf}
.video-job .video-download{display:inline-flex;align-items:center;min-height:38px;padding:0 14px;border:1px solid #cbd7c1;border-radius:7px;text-decoration:none;background:#fff;color:#315e50;box-sizing:border-box}
.video-failure-details{padding:12px;background:#f7f8f2;border-radius:8px;overflow-wrap:anywhere}
@media(max-width:600px){.video-job{padding:14px}.video-job>.actions{justify-content:flex-start}}
.prompt-audit{border:1px solid #dce5d5;border-radius:8px;padding:14px;margin:16px 0;background:#f9fbf5}.prompt-audit h4{font-size:12px;margin:0 0 10px}.prompt-audit h4 a{float:right;font-size:10px;font-weight:400;color:#809374}.audit-checks{display:flex;gap:12px;flex-wrap:wrap;font-size:11px;color:#728968}.prompt-audit small{font-size:10px;color:#94a087;line-height:1.8}.prompt-audit .audit-warning{font-size:11px;color:#a5814a;margin:9px 0}</style>
