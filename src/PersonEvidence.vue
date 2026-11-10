<script setup lang="ts">
import {computed} from 'vue'
import {personEvidence} from './personEvidence'
const props=defineProps<{project:any;character:any;structured?:any}>()
const passages=computed(()=>personEvidence(props.project,props.character,props.structured))
</script>
<template><details class="person-evidence" open @click.stop><summary>原文依据<span v-if="passages.length"> · {{passages.length}} 处</span></summary><blockquote v-for="passage in passages" :key="passage.key"><p>{{passage.quote}}</p><cite>{{passage.title}}<template v-if="passage.page"> · 第 {{passage.page}} 页</template><template v-else-if="passage.location"> · {{passage.location}}</template></cite></blockquote><p v-if="!passages.length" class="empty-evidence">所选资料中暂无可定位的支持原文。</p></details></template>
<style scoped>
.person-evidence{margin:16px 0;font-size:12px;color:#637469}.person-evidence summary{cursor:pointer}.person-evidence summary span{color:#819086}.person-evidence blockquote{margin:12px 0;padding:10px 12px;border-left:2px solid #a8bd91;background:#f3f7ed}.person-evidence blockquote p{margin:0 0 8px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.9}.person-evidence cite{font-size:11px;font-style:normal;color:#7b8b80}.empty-evidence{font-size:12px;line-height:1.8;color:#819086}
</style>
