<script setup lang="ts">
import {computed,ref,watch} from 'vue'
import {useStudio} from './studioContext'
import AppIcon from './AppIcon.vue'
const s=useStudio(),items=ref<any[]>([]),loading=ref(false),error=ref('')
const chosen=computed<string[]>(()=>s.p.value.authoringDrafts?.materialSources?.libraryIds||[])
function choose(id:string,checked:boolean){
 const ids=new Set(chosen.value);checked?ids.add(id):ids.delete(id)
 s.p.value.authoringDrafts||={};s.p.value.authoringDrafts.materialSources={libraryIds:[...ids]};s.scheduleAutosave()
}
const allSelected=computed(()=>items.value.length>0&&items.value.every(row=>chosen.value.includes(row.id)))
function toggleAll(){
 if(s.generating.value)return
 const ids=new Set(chosen.value),clear=allSelected.value
 for(const row of items.value)clear?ids.delete(row.id):ids.add(row.id)
 s.p.value.authoringDrafts||={};s.p.value.authoringDrafts.materialSources={libraryIds:[...ids]};s.scheduleAutosave()
}
let sequence=0
async function load(){
 const ticket=++sequence,pid=s.p.value.id;loading.value=true;error.value='';items.value=[]
 try{
  const response=await fetch(`/api/projects/${pid}/source-library?catalog=pdf-files-v2`,{cache:'no-store'})
  if(!response.ok)throw Error('PDF 资料暂未加载，请重试。')
  const result=await response.json()
  if(result.schemaVersion!=='pdf-library-2')throw Error('PDF 资料正在更新，请稍后重试。')
  if(ticket===sequence&&pid===s.p.value.id)items.value=result.items.filter((row:any)=>row.format==='pdf'&&typeof row.filename==='string'&&row.filename.toLowerCase().endsWith('.pdf')&&row.fileUrl&&row.summary?.trim())
 }catch(e:any){if(ticket===sequence)error.value=e.message}
 finally{if(ticket===sequence)loading.value=false}
}
watch(()=>s.p.value.id,()=>{void load()},{immediate:true})
</script>
<template><section class="source-library-picker" aria-label="PDF文献资料">
 <p v-if="error" role="alert" class="banner error">{{error}} <button :disabled="loading" @click="load">重新读取</button></p>
 <p v-else-if="loading" role="status" class="pdf-status">正在读取 PDF…</p>
 <div v-else-if="items.length"><div class="pdf-selection-toolbar"><button type="button" class="pdf-select-all" :disabled="s.generating.value" @click="toggleAll">{{allSelected?'取消全选':'全选'}}</button><p class="pdf-selection-note">可多选 · 已选 {{chosen.length}} 份，点击“整理资料”后统一整理。</p></div><div class="pdf-list" role="list"><div v-for="row in items" :key="row.id" class="pdf-entry" :class="{'is-selected':chosen.includes(row.id)}" role="listitem"><input class="pdf-checkbox" type="checkbox" :checked="chosen.includes(row.id)" :disabled="s.generating.value" :aria-label="'选择 PDF：'+row.filename" @change="choose(row.id,($event.target as HTMLInputElement).checked)"><span class="pdf-file-icon" aria-hidden="true"><AppIcon name="script" :size="23"/></span><div class="pdf-copy"><h3><a :href="row.fileUrl" target="_blank" rel="noopener">{{row.filename}}</a></h3><p>{{row.summary}}</p></div><a class="pdf-open" :href="row.fileUrl" target="_blank" rel="noopener" :aria-label="'查看 PDF：'+row.filename">查看 PDF <AppIcon name="arrow" :size="15"/></a></div></div></div>
 <p v-else class="pdf-status">暂无 PDF 文件。</p>
</section></template>
<style scoped>
.pdf-selection-toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px}.pdf-select-all{padding:7px 14px;border:1px solid #dce4d2;border-radius:6px;background:#f5f7ee;color:#46663d;font-size:12px;cursor:pointer}.pdf-select-all:disabled{opacity:.5;cursor:not-allowed}.pdf-select-all:focus-visible{outline:2px solid #315e50;outline-offset:3px}.pdf-selection-toolbar .pdf-selection-note{margin:0}.pdf-selection-note{font-size:12px;color:#718069;margin:0 0 12px}.pdf-checkbox{width:16px;height:16px;flex-shrink:0;accent-color:#315e50}.pdf-list .is-selected{background:#f0f5e9}.source-library-picker{margin:22px 0 26px}
.pdf-list{background:#fffefa;border:1px solid #e0e5d7;border-radius:12px;overflow:hidden}
.pdf-list .pdf-entry{display:flex;align-items:center;gap:20px;padding:26px 28px;transition:background .15s}
.pdf-entry+.pdf-entry{border-top:1px solid #e8ebdf}
.pdf-entry:hover{background:#f9faf4}
.pdf-file-icon{display:grid;place-items:center;align-self:flex-start;flex:0 0 44px;height:52px;border:1px solid #dce4d1;border-radius:7px;background:#f0f4e9;color:#6e8560}
.pdf-copy{flex:1;min-width:0}
.pdf-copy h3{margin:0 0 9px;font:500 16px/1.6 'Microsoft YaHei','PingFang SC',sans-serif;letter-spacing:.01em}
.pdf-copy h3 a{color:#2d5045;text-decoration:none;overflow-wrap:anywhere}
.pdf-copy h3 a:hover{text-decoration:underline;text-underline-offset:4px}
.pdf-copy p{margin:0;max-width:880px;color:#718069;font-size:13px;line-height:1.95}
.pdf-open{display:inline-flex;align-items:center;gap:12px;flex-shrink:0;padding:10px 15px;border:1px solid #dce4d2;border-radius:6px;background:#f5f7ee;color:#46663d;text-decoration:none;font-size:12px;white-space:nowrap}
.pdf-open:hover{background:#eaf0df;border-color:#b4c4a6}
.pdf-entry a:focus-visible{outline:2px solid #315e50;outline-offset:4px}
.pdf-status{font-size:13px;padding:16px 0;color:#718069}
@media(max-width:700px){.pdf-list .pdf-entry{gap:14px;padding:20px 18px;flex-wrap:wrap}.pdf-copy{flex-basis:calc(100% - 58px)}.pdf-open{margin-left:58px;padding:8px 12px}.pdf-copy h3{font-size:15px}.pdf-copy p{font-size:12px}}
</style>
