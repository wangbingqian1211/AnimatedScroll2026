<script setup lang="ts">
import {ref} from 'vue'
import ImportPanel from '../ImportPanel.vue'
import DocumentLibrary from '../DocumentLibrary.vue'
import ArtworkContext from '../ArtworkContext.vue'
import {useStudio} from '../studioContext'
const s=useStudio(),emit=defineEmits(['replace','running'])
const sourcesOpen=ref(!s.rec('material','main')?.draft.structured)
function onSourcesToggle(event:Event){if(event.target!==event.currentTarget)return;sourcesOpen.value=(event.target as HTMLDetailsElement).open}
</script>
<template><div data-entity-key="material:main" class="library-page">
 <section class="painting-tools"><ImportPanel :project="s.p.value" studio hide-documents @replace="emit('replace',$event)" @running="emit('running',$event)" @confirm-materials="s.confirm(s.rec('material','main'),false)"/></section>
 <h2 class="library-section-label">文献与作品资料</h2>
 <details id="source-library" class="source-tools" :open="sourcesOpen" @toggle="onSourcesToggle"><summary>{{s.p.value.documents.length?`已加入 ${s.p.value.documents.length} 份文献`:'还没有加入文献'}} <span>可以勾选 PDF，也可以上传或粘贴</span></summary><DocumentLibrary compact/></details>
 <ArtworkContext :project="s.p.value"/>
</div></template>
<style scoped>.library-section-label{margin:0 0 12px;font-size:18px}.source-tools{margin-bottom:24px;border:1px solid #e1e6da;background:#fbfcf7;border-radius:11px;padding:16px 20px}.source-tools>summary{cursor:pointer;font-size:13px;color:#5b7450;font-weight:600}.source-tools>summary span{font-size:11px;font-weight:400;color:#95a08b;margin-left:12px}.source-tools[open]>summary{margin-bottom:20px}.painting-tools{margin-bottom:32px}</style>
