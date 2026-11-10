<script setup lang="ts">
import {computed} from 'vue'
import ImportPanel from '../ImportPanel.vue'
import DocumentLibrary from '../DocumentLibrary.vue'
import ArtworkContext from '../ArtworkContext.vue'
import {useStudio} from '../studioContext'
const s=useStudio(),emit=defineEmits(['replace','running'])
const hasData=computed(()=>!!s.rec('material','main')?.draft.structured||!!s.p.value.characters.length&&!!s.p.value.sources.length)
</script>
<template><div data-entity-key="material:main" class="library-page">
 <section class="painting-tools"><ImportPanel :project="s.p.value" studio hide-documents @replace="emit('replace',$event)" @running="emit('running',$event)" @confirm-materials="s.confirm(s.rec('material','main'),false)"/></section>
 <h2 class="library-section-label">文献与作品资料</h2><p class="library-section-note">添加来源，整理依据，再为画中人物补充身份与故事。</p>
 <details class="source-tools" :open="!hasData||!s.p.value.documents.length"><summary>资料来源 · {{s.p.value.documents.length}} 份文献 <span>选择已有史料或添加文件、文本</span></summary><DocumentLibrary compact/></details>
 <ArtworkContext :project="s.p.value"/>

 <div class="library-next"><button class="primary" @click="s.navigate('outline')">下一步：剧本大纲 →</button></div>
</div></template>
<style scoped>.source-tools{margin-bottom:24px;border:1px solid #e1e6da;background:#fbfcf7;border-radius:11px;padding:16px 20px}.source-tools>summary{cursor:pointer;font-size:13px;color:#5b7450;font-weight:600}.source-tools>summary span{font-size:11px;font-weight:400;color:#95a08b;margin-left:12px}.source-tools[open]>summary{margin-bottom:20px}.painting-tools{margin-bottom:32px}</style>
