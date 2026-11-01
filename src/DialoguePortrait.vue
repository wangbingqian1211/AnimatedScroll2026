<script setup lang="ts">
import {ref,watch,onMounted} from 'vue'
const props=defineProps<{url:string;box:Record<string,any>;label:string;soft?:boolean}>()
const canvas=ref<HTMLCanvasElement|null>(null);let revision=0
async function draw(){const n=++revision,im=new Image();im.src=props.url;try{await im.decode()}catch{return}if(n!==revision||!canvas.value)return
 const b=props.box,x=Math.max(0,b.x*im.naturalWidth),y=Math.max(0,b.y*im.naturalHeight),w=Math.max(1,Math.min(b.w*im.naturalWidth,im.naturalWidth-x)),h=Math.max(1,Math.min(b.h*im.naturalHeight,im.naturalHeight-y)),scale=Math.min(3,440/w,640/h),c=canvas.value;c.width=Math.round(w*scale);c.height=Math.round(h*scale)
 const ctx=c.getContext('2d');if(!ctx)return;ctx.drawImage(im,x,y,w,h,0,0,c.width,c.height)
 if(props.soft){ctx.globalCompositeOperation='destination-in';const g=ctx.createLinearGradient(0,0,0,c.height);g.addColorStop(0,'rgba(0,0,0,0)');g.addColorStop(.06,'#000');g.addColorStop(.78,'#000');g.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=g;ctx.fillRect(0,0,c.width,c.height);ctx.globalCompositeOperation='source-over'}
}
watch(()=>[props.url,props.box,props.soft],draw,{deep:true});onMounted(draw)
</script>
<template><canvas ref="canvas" role="img" :aria-label="label"/></template>
<style scoped>canvas{display:block;max-width:100%;max-height:100%;object-fit:contain}</style>
