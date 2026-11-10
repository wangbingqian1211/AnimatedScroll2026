<script setup lang="ts">
import {ref,computed} from 'vue'
const props=defineProps<{image:string,modelValue:any}>(),emit=defineEmits(['update:modelValue'])
const surface=ref<HTMLElement>(),drag=ref<any>(null),preview=ref<any>(null),box=computed(()=>preview.value||props.modelValue)
const handles=['nw','n','ne','e','se','s','sw','w']
const clamp=(v:number,min=0,max=1)=>Math.max(min,Math.min(max,v))
function pos(e:PointerEvent){const r=surface.value!.getBoundingClientRect();return {x:clamp((e.clientX-r.left)/r.width),y:clamp((e.clientY-r.top)/r.height)}}
function down(e:PointerEvent){if(e.button!==0)return;const target=e.target as HTMLElement;drag.value={start:pos(e),mode:target.dataset.handle||(target.closest('.selection')?'move':'new'),box:props.modelValue?{...props.modelValue}:null};surface.value!.setPointerCapture(e.pointerId);e.preventDefault()}
function move(e:PointerEvent){const d=drag.value;if(!d)return;const p=pos(e),dx=p.x-d.start.x,dy=p.y-d.start.y,b=d.box
 if(d.mode==='new'){preview.value={x:Math.min(p.x,d.start.x),y:Math.min(p.y,d.start.y),w:Math.abs(dx),h:Math.abs(dy)};return}
 if(d.mode==='move'){preview.value={...b,x:clamp(b.x+dx,0,1-b.w),y:clamp(b.y+dy,0,1-b.h)};return}
 let l=b.x,t=b.y,r=b.x+b.w,bottom=b.y+b.h
 if(d.mode.includes('w'))l=clamp(l+dx,0,r-.005)
 if(d.mode.includes('e'))r=clamp(r+dx,l+.005,1)
 if(d.mode.includes('n'))t=clamp(t+dy,0,bottom-.005)
 if(d.mode.includes('s'))bottom=clamp(bottom+dy,t+.005,1)
 preview.value={x:l,y:t,w:r-l,h:bottom-t}
}
function up(e:PointerEvent){if(!drag.value)return;move(e);if(preview.value?.w>=.005&&preview.value?.h>=.005)emit('update:modelValue',preview.value);cancel()}
function cancel(){drag.value=null;preview.value=null}
</script>
<template><div><small>拖动画作空白处新建选框；拖动框内移动，拖动边缘或角点调整大小。</small><div v-if="image" ref="surface" class="region-picker" @pointerdown="down" @pointermove="move" @pointerup="up" @pointercancel="cancel" @lostpointercapture="cancel"><img :src="image" draggable="false"><span v-if="box" class="selection" :style="{left:box.x*100+'%',top:box.y*100+'%',width:box.w*100+'%',height:box.h*100+'%'}"><i v-for="h in handles" :key="h" :data-handle="h" :class="h"/></span></div><div v-else class="empty">请先上传画作</div><button v-if="modelValue" type="button" @click="emit('update:modelValue',null)">清除区域</button></div></template>
<style scoped>
.region-picker .selection{pointer-events:auto;cursor:move;box-sizing:border-box}.selection i{position:absolute;width:12px;height:12px;background:white;border:2px solid #b27a27;transform:translate(-50%,-50%);box-sizing:border-box}.nw,.w,.sw{left:0}.n,.s{left:50%}.ne,.e,.se{left:100%}.nw,.n,.ne{top:0}.w,.e{top:50%}.sw,.s,.se{top:100%}.nw,.se{cursor:nwse-resize}.ne,.sw{cursor:nesw-resize}.n,.s{cursor:ns-resize}.e,.w{cursor:ew-resize}
</style>
