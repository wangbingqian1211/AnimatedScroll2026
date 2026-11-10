<script setup lang="ts">
import {computed} from 'vue'
import {zhekanContext} from './fixedArtworkContext'
const props=defineProps<{project:Record<string,any>}>()
const context=computed(()=>/折[槛檻]/.test(props.project.artworkName||props.project.title||'')?zhekanContext:null)
const columns=[{key:'background',title:'历史背景'},{key:'relationships',title:'人物与关系'},{key:'narrative',title:'已有历史叙事'}]
</script>
<template>
 <section v-if="context" class="fixed-artwork-context" aria-label="画作固定背景资料">
  <div v-for="column in columns" :key="column.key" class="context-column">
   <h3>{{column.title}}</h3>
   <p>{{context[column.key]}}</p>
  </div>
 </section>
</template>
<style scoped>
.fixed-artwork-context{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:28px;padding:28px;margin:24px 0;background:#fffefa;border:1px solid #e0e5d7;border-radius:11px}
.context-column{min-width:0}.context-column h3{font-size:15px;font-weight:600;color:#293f3b;margin:0 0 18px}.context-column p{font-size:13px;line-height:2;color:#77836d;white-space:pre-wrap;margin:0;overflow-wrap:anywhere}
@media(max-width:1000px){.fixed-artwork-context{grid-template-columns:1fr;gap:24px;padding:22px}.context-column+.context-column{border-top:1px solid #e6eadf;padding-top:24px}}
</style>
