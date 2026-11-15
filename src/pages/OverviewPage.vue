<script setup lang="ts">
import ProjectGallery from '../ProjectGallery.vue'
import ProjectArchive from '../ProjectArchive.vue'
import {useStudio} from '../studioContext'
const s=useStudio()
</script>
<template><section class="overview-page">
 <ol class="how-to" aria-label="开始创作的四步">
  <li><button type="button" @click="s.navigate('library')"><b>1 看画</b><span>核对人物和故事，再整理文献</span></button></li>
  <li><button type="button" @click="s.navigate('outline')"><b>2 写故事</b><span>说明想讲什么，生成剧情</span></button></li>
  <li><button type="button" @click="s.navigate('characters')"><b>3 人物开口</b><span>写小传，设定怎么说话</span></button></li>
  <li><button type="button" @click="s.navigate('experience')"><b>4 欣赏</b><span>进入画里，和人物对话</span></button></li>
 </ol>
 <ProjectGallery/>
 <details class="overview-details project-management"><summary>项目与示例管理 <span>导入示例、归档与恢复</span></summary><ProjectArchive/></details>
</section></template>
<style scoped>.how-to{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:8px 0 28px;padding:0;list-style:none}.how-to button{display:flex;flex-direction:column;align-items:flex-start;gap:6px;width:100%;height:100%;padding:16px 16px 18px;text-align:left;background:#fffefa;border:1px solid #dce3d2;border-radius:10px;color:#3f5949}.how-to li:first-child button{border-color:#8eaa86;background:#f7faf3}.how-to button:hover{background:#f4f7ee;border-color:#b7c7a8}.how-to b{font-size:14px;font-weight:650}.how-to span{font-size:12px;line-height:1.6;color:#6d7b70}@media(max-width:900px){.how-to{grid-template-columns:1fr 1fr}}@media(max-width:560px){.how-to{grid-template-columns:1fr}}.overview-flow{margin-bottom:28px}.overview-subflow{border:1px solid #dce6de;background:#f7faf5;border-radius:14px;padding:24px;margin:28px 0 36px;scroll-margin-top:110px}.overview-subflow:focus{outline:2px solid #7ba48c;outline-offset:4px}.overview-subflow .workflow-heading h3{margin-top:9px;font-size:16px}.subflow-tag{font-size:9px;color:#7d9684;letter-spacing:.08em}.flow-caption{font-size:12px;color:#809087;line-height:1.9}.workflow-heading button{font-size:11px;white-space:nowrap}</style>
