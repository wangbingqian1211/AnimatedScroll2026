/** Navigation and deterministic local checklist presentation. No network or model calls. */
export const creationPages = [
 {id:'overview',number:'0',name:'概览',short:'概览',icon:'overview',description:'当前进度与下一步',guide:'选一幅画。之后按左边从上到下做。'},
 {id:'library',number:'1',name:'资料与基础人物',short:'看画',icon:'image',description:'文献、作品资料与画中人物',guide:'先看画和右侧的故事。要补充依据，再去添加文献。'},
 {id:'outline',number:'2',name:'剧本大纲',short:'写故事',icon:'script',description:'创作方向和剧情',guide:'先写创作方向，再单独编写剧情。'},
 {id:'clues',number:'3',name:'线索库',short:'线索',icon:'clues',description:'文化、关系及叙事线索',guide:'把文化背景、人物关系和情节收成可以回查的线索。'},
 {id:'characters',number:'4',name:'人物档案',short:'人物',icon:'people',description:'完整人物设定、知识与引导',guide:'左边点一个人，改他的小传，再设定怎么说话。'},
 {id:'storyboards',number:'5',name:'分镜管理',short:'分镜',icon:'film',description:'人物、画面与完整提示词',guide:'勾选线索，生成镜头提示词。视频还不能生成。'},
]
export const routeNames: Record<string, string> = Object.fromEntries([
  ...creationPages.map(p => [p.id, p.name]), ['checks', '检查与发布'], ['experience', '欣赏作品'],
])
export function resolveRoute(hash: string) {
  const requested = hash.replace(/^#\/?/, '')
  if (requested === 'checks') return { page: 'overview', checks: true }
  return { page: routeNames[requested] ? requested : 'overview', checks: false }
}
export interface CheckItem {
  id?: string; page: string; name: string; state: string; target?: string; reason?: string
  action?: {task:string; target:string; label:string}; kind?: string; jobId?: string; dependency?: { page: string; target: string; name: string }
}
const statePriority: Record<string, number> = { failed: 0, interrupted: 0, stale: 1, changed: 2, review: 2, missing: 3, incomplete: 3, draft: 3 }
export function itemKey(item: CheckItem) { return item.id || `${item.page}:${item.target || item.name}:${item.state}` }
export function pendingItems(items: CheckItem[]) {
  const unique = new Map<string, CheckItem>()
  for (const item of items) if (item.kind!=='suggestion' && item.state in statePriority && !unique.has(itemKey(item))) unique.set(itemKey(item), item)
  const pageOrder = (page: string) => { const n = creationPages.findIndex(p => p.id === page); return n < 0 ? 99 : n }
  return [...unique.values()].sort((a, b) => statePriority[a.state]! - statePriority[b.state]! || pageOrder(a.page) - pageOrder(b.page) || itemKey(a).localeCompare(itemKey(b), 'zh-CN'))
}
export function runningItems(items: CheckItem[]) { return items.filter(i => i.state === 'queued' || i.state === 'running') }
export function shortReason(item: CheckItem) {
  const fallback: Record<string, string> = {failed:'生成未完成，请查看详情后重试',interrupted:'任务已中断，可手动重试',stale:'相关依据有变化，内容仍可使用',changed:'内容已修改，将自动保存',review:'请复核相关内容',missing:'需要补充内容',incomplete:'请补齐必要信息',draft:'可生成本步骤内容或直接填写'}
  const value = (item.reason || fallback[item.state] || '').replace(/\s+/g, ' ')
  return value.length > 68 ? value.slice(0, 68) + '…' : value
}
