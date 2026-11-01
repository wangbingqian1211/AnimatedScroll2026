import assert from 'node:assert/strict'
import fs from 'node:fs'
import ts from 'typescript'

const file=new URL('../src/dialogueStory.ts',import.meta.url)
const code=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText
const {buildChapters,guideCandidates,complete,shortName,selectSceneVideo}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'))
const names=['朱云','汉成帝','张禹','辛弃疾','宫女：春桃','宫人：德福']
const sources=[
 '他请求赐尚方斩马剑，处死佞臣，皇帝追问时点名安昌侯张禹。',
 '汉成帝是张禹的学生，长期信任张禹；事件中先震怒，后接受劝说。',
 '朱云被带离时攀住殿前栏杆，栏杆折断，并非主动砸毁宫殿或折断门槛。',
 '左将军辛弃疾免冠解印绶，叩头流血，请求容纳逆耳之言：“使其言是，不可诛；其言非，固当容之。”',
 '成帝息怒，朱云得以保全。',
 '后来修栏时皇帝要求不要换掉，而应修补旧栏，用来表彰直臣。'
]
const project={characters:names.map((name,id)=>({id:String(id),name,namingOrigin:id>=4?'creator':'legacy'})),annotations:[{id:'guide',kind:'character',characterId:'4'},{id:'emperor',kind:'character',characterId:'1'}],sources:sources.map((text,id)=>({id:String(id),text,title:'已有材料'})),scenes:['廷前直谏','攀槛折栏','以古自比与死争','成帝息怒','修栏勿易'].map((title,id)=>({id:'scene'+id,title,characterIds:['0','1','2','3'],units:[]}))}
const chapters=buildChapters(project)
assert.equal(chapters.length,5)
assert.deepEqual(chapters.map(c=>c.questions.length),[2,1,1,1,1])
assert.equal(guideCandidates(project).length,1,'A named guide without an image annotation cannot supply a portrait')
assert.equal(shortName('宫女：春桃'),'春桃')
for(const chapter of chapters){
 assert(!complete(chapter,[]))
 assert(complete(chapter,chapter.questions.map(q=>q.id)))
 assert(!complete(chapter,['another-scene:0']))
 for(const q of chapter.questions){assert(project.characters.some(c=>c.id===q.personId));assert(project.sources.some(s=>s.text.includes(q.quote)))}
}
assert(chapters.every(c=>!/(去问|问问|你来问|先问)/.test(c.lead)),'Guides introduce the scene instead of giving interaction instructions')
assert(!chapters[0].lead.includes('保全'))
assert(!chapters[0].questions.some(q=>q.answer.includes('朱云得以保全')))
assert(chapters[0].lead.includes('准备'))
assert(!chapters[0].questions.some(q=>q.answer.includes('张禹')||q.answer.includes('带离')))
assert(!chapters[0].lead.includes('方才'))
const pinnedProject={interaction:{sceneVideos:{scene0:'chosen'}}}
const clip=(id,sceneId='scene0',extra={})=>({id,sceneId,status:'succeeded',videoUrl:'/'+id,matchesCurrentScript:false,...extra})
assert.equal(selectSceneVideo(pinnedProject,[clip('other'),clip('chosen')],'scene0')?.id,'chosen')
assert.equal(selectSceneVideo(pinnedProject,[clip('chosen','wrong')],'scene0'),undefined)
assert.equal(selectSceneVideo(pinnedProject,[clip('chosen','scene0',{test:true})],'scene0'),undefined)
const unrelated={...project,sources:[],scenes:[{id:'other',title:'另一幅画',characterIds:['0'],units:[]}]}
const fallback=buildChapters(unrelated)
assert(!fallback[0].questions[0].answer.includes('斩马剑'),'Unrelated projects must not inherit this painting’s plot')
assert.equal(fallback[0].questions[0].quote,'')
console.log('Dialogue checks passed: guide eligibility, sourced questions, per-scene gates, no early ending, unrelated-project fallback.')

const authored={...project,interaction:{guideAnnotationIds:['guide'],chapters:[{id:'custom',title:'自定义一幕',lead:'引路词',outro:'收束',questions:[{id:'custom:0',personId:'0',question:'自定义提问',answer:'自定义回答',clue:'自定义线索',quote:'',sourceTitle:''}]}]}}
assert.equal(buildChapters(authored)[0].questions[0].answer,'自定义回答')
assert.equal(guideCandidates({...authored,interaction:{...authored.interaction,guideAnnotationIds:[]}}).length,0)
