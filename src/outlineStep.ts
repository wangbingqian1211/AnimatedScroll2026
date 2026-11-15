import {ref} from 'vue'
/** Which half of 剧本大纲 is on screen. Direction and plot are separate pages, not one split view. */
export const outlineStep = ref<'direction' | 'plot'>('direction')
