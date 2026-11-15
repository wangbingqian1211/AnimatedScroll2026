<script setup lang="ts">
import {computed,ref,watch} from 'vue'
import {useStudio} from './studioContext'
const s=useStudio(),previews=ref<Record<string,any>>({}),previewError=ref('')
const projects=computed(()=>s.projects.value||[])
watch(()=>projects.value.map((p:any)=>p.id).join(','),async()=>{
 previewError.value=''
 await Promise.all(projects.value.map(async(p:any)=>{
  if(p.id===s.p.value?.id){previews.value[p.id]=s.p.value;return}
  if(previews.value[p.id])return
  try{previews.value[p.id]=await s.api(`/projects/${p.id}/studio/editor`)}catch{previewError.value='部分画作预览暂未加载，仍可点击进入项目。'}
 }))
},{immediate:true})
function preview(p:any){return p.id===s.p.value?.id?s.p.value:previews.value[p.id]}
async function enter(p:any){await s.run(async()=>{await s.openProject(p.id);await s.navigate('library')})}
</script>
<template>
 <section class="project-gallery" aria-label="作品与创作项目">
  <p v-if="previewError" role="status">{{previewError}}</p>
  <div class="artwork-gallery">
   <button v-for="project in projects" :key="project.id" class="artwork-card" :disabled="s.busy.value" @click="enter(project)">
    <div class="artwork-cover"><span v-if="project.id===s.p.value?.id" class="last-opened">当前项目</span><img v-if="preview(project)?.image" :src="preview(project).image" :alt="project.title" loading="lazy"><span v-else class="artwork-placeholder">画</span></div>
    <div class="artwork-caption"><span class="gallery-eyebrow">画中人物 · 叙事创作</span><h2>{{project.title}}</h2><p>{{preview(project)?.annotations?.filter((a:any)=>a.kind==='character').length||0}} 个画中身影 · 资料、故事与人物设定</p><div class="artwork-enter">进入创作 <span>↗</span></div></div>
   </button>
   <button class="new-artwork-card" :disabled="s.busy.value" @click="s.beginName('create')"><span>＋</span><h2>开启新的画中故事</h2><p>新建项目，导入你的画作与资料</p></button>
  </div>
  <div class="gallery-footnote"><span>你的创作保存在本机，修改自动保存。</span></div>
 </section>
</template>
