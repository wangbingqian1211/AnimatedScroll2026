<script setup lang="ts">
defineProps<{projects:Record<string,any>[];busy:boolean;lastId:string}>()
defineEmits<{open:[id:string];create:[]}>()
function introduction(item:Record<string,any>){return ({zhekan:'从一场直言与劝谏开始，探索画中人物的选择。',chongping:'循着棋局、座次与重重屏风，读出画面中的层次。',bunian:'从人物的距离、服饰与仪仗，走近一场历史相见。'} as Record<string,string>)[item.libraryKey]||'从观察一个人物开始，结合画作与资料，慢慢写出你的故事。'}
function metadata(item:Record<string,any>){return [item.paintingInfo?.period?.split(/[；;]/)[0]?.replace('题材',''),item.paintingInfo?.artist].filter(Boolean).join(' · ')||'画中人物 · 叙事创作'}
</script>

<template>
 <main class="painting-home">
  <section class="painting-home-heading">
   <div><span class="home-eyebrow">画中有话 · 创作空间</span><h2>选择一幅画，开始你的叙事。</h2><p>从画中人物出发，读懂故事，再让故事拥有自己的声音。</p></div>
   <span class="home-step">选画 <i>→</i> 创作 <i>→</i> 入画对话</span>
  </section>
  <section class="painting-shelf" aria-label="选择画作" :aria-busy="busy">
   <button v-for="item in projects" :key="item.id" class="painting-cover-card" :disabled="busy" @click="$emit('open',item.id)">
    <div class="painting-cover"><img v-if="item.image" :src="item.image" :alt="item.title+'的画作封面'"><span v-else class="painting-cover-placeholder">卷</span><span v-if="item.id===lastId" class="last-opened">上次打开</span></div>
    <div class="painting-card-copy"><span class="painting-card-meta">{{metadata(item)}}</span><h3>{{item.title}}</h3><p>{{introduction(item)}}</p><span class="painting-card-enter">进入创作 <span aria-hidden="true">↗</span></span></div>
   </button>
   <button class="new-painting-card" :disabled="busy" @click="$emit('create')"><span aria-hidden="true">＋</span><h3>从另一幅画开始</h3><p>添加画作与资料<br>建立新的创作项目</p><span class="new-painting-link">新建项目 →</span></button>
  </section>
 </main>
</template>

<style scoped>
.painting-home{max-width:1440px;padding:42px 4% 60px}.painting-home-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:30px;margin-bottom:32px}.home-eyebrow{font-size:11px;letter-spacing:.18em;color:#7e8c77}.painting-home-heading h2{font:400 38px/1.45 serif;letter-spacing:.06em;margin:17px 0 14px}.painting-home-heading p{font-size:13px;color:#7d8878;margin:0}.home-step{font-size:11px;color:#7d8878;white-space:nowrap;padding-bottom:5px}.home-step i{font-style:normal;margin:0 16px;color:#b1b9a4}.painting-shelf{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}.painting-cover-card{display:flex;flex-direction:column;min-width:0;padding:0;overflow:hidden;text-align:left;background:#fffef9;border:1px solid #dde1d5;border-radius:12px;transition:transform .2s,box-shadow .2s}.painting-cover-card:hover{background:#fffef9;transform:translateY(-4px);box-shadow:0 14px 35px #30453612}.painting-cover{width:100%;aspect-ratio:1.65;display:flex;align-items:center;justify-content:center;padding:22px;background:#eae7db;position:relative;overflow:hidden}.painting-cover img{display:block;max-width:100%;max-height:100%;object-fit:contain;box-shadow:0 4px 15px #493e2720}.painting-cover-placeholder{font:48px serif;color:#a2ab95}.last-opened{position:absolute;left:14px;top:14px;font-size:10px;color:#486448;background:#fffef5e8;border:1px solid #dbe0cd;border-radius:4px;padding:5px 8px}.painting-card-copy{padding:23px 25px 20px;display:flex;flex-direction:column;flex:1;width:100%}.painting-card-meta{font-size:10px;letter-spacing:.05em;color:#8b927e;min-height:15px}.painting-card-copy h3{font:400 25px/1.4 serif;letter-spacing:.06em;margin:10px 0}.painting-card-copy p{font-size:12px;line-height:1.9;color:#7c8676;margin:0 0 24px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;min-height:46px}.painting-card-enter{display:flex;align-items:center;justify-content:space-between;font-size:12px;color:#31594b;border-top:1px solid #e9eadf;padding-top:16px;margin-top:auto}.painting-card-enter>span{font-size:18px}.new-painting-card{padding:28px;min-height:250px;display:flex;flex-direction:column;align-items:center;justify-content:center;background:transparent;border:1px dashed #cbd3c2;border-radius:12px;text-align:center}.new-painting-card>span:first-child{font:28px serif;color:#879d7e}.new-painting-card h3{font:400 20px serif;margin:15px 0 6px}.new-painting-card p{font-size:12px;line-height:1.9;color:#8a9380;margin:0 0 20px}.new-painting-link{font-size:12px}.painting-home button:focus-visible{outline:2px solid #64816b;outline-offset:5px}@media(max-width:1000px){.painting-home{padding-top:40px}.painting-shelf{grid-template-columns:repeat(2,minmax(0,1fr))}.painting-home-heading h2{font-size:36px}.home-step{display:none}}@media(max-width:600px){.painting-home{padding:32px 5% 45px}.painting-home-heading{margin-bottom:26px}.painting-home-heading h2{font-size:30px}.painting-home-heading p{font-size:12px;line-height:1.9}.painting-shelf{grid-template-columns:1fr;gap:20px}.painting-cover{aspect-ratio:1.8}.painting-card-copy p{min-height:0}.painting-card-copy{padding:20px}.new-painting-card{min-height:210px}}@media(prefers-reduced-motion:reduce){.painting-cover-card{transition:none}.painting-cover-card:hover{transform:none}}
</style>
