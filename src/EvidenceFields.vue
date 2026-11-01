<script setup lang="ts">
const props = defineProps<{ evidence: Record<string, any>; sources: Record<string, any>[] }>()
function choose() {
  props.evidence.sourceVersion = props.sources.find(s => s.id === props.evidence.sourceId)?.version || 1
  props.evidence.quote = ''
}
</script>
<template>
  <fieldset class="evidence-fields">
    <legend>关联史料（可稍后补充）</legend>
    <label>来源<select v-model="evidence.sourceId" @change="choose"><option value="">尚无关联来源</option><option v-for="s in sources" :key="s.id" :value="s.id">{{s.title}} · v{{s.version}}</option></select></label>
    <template v-if="evidence.sourceId">
      <label>逐字引文<textarea v-model="evidence.quote" rows="3" placeholder="从下方原文逐字摘录，留空时标为待补依据。" /></label>
      <details><summary>阅读所选来源</summary><p>{{sources.find(s=>s.id===evidence.sourceId)?.text}}</p></details>
    </template>
    <small>关联引文只表示可追溯到原文，不表示系统已验证史实。</small>
  </fieldset>
</template>
<style scoped>
.evidence-fields{border-top:1px solid #dce1d3;padding-top:15px;margin-top:20px}.evidence-fields legend{font-size:12px;padding-right:8px;color:#6d7e64}.evidence-fields details{font-size:12px;margin:15px 0}.evidence-fields p{white-space:pre-wrap;font-size:12px;line-height:1.9;max-height:220px;overflow:auto}
</style>
