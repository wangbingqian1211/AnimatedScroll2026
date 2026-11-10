import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
const code=ts.transpileModule(readFileSync(new URL('../src/personEvidence.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText
const {personEvidence}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'))
const source={id:'s',version:1,title:'资料原文',documentId:'doc',page:3,text:'汉成帝，张禹的学生。朱云上书。'}
const ref={sourceId:'s',sourceVersion:1,quote:'汉成帝，张禹的学生。',start:0}
const project={sources:[source],documents:[{id:'doc',title:'用户选择的文献'}]}
test('shows linked original passages with document and page, deduplicating repeated references',()=>{
 const rows=personEvidence(project,{id:'c',mentions:[ref,ref],evidence:'需对照某书'})
 assert.equal(rows.length,1);assert.equal(rows[0].quote,ref.quote);assert.equal(rows[0].title,'用户选择的文献');assert.equal(rows[0].page,3)
})
test('never substitutes notes, invented quotes, unrelated passages, or stale versions for evidence',()=>{
 assert.deepEqual(personEvidence(project,{id:'c',evidence:'需对照某书'}),[])
 assert.deepEqual(personEvidence(project,{id:'c',mentions:[{...ref,quote:'汉成帝是朱云的学生'}]}),[])
 assert.deepEqual(personEvidence({...project,sources:[{...source,version:2}]},{id:'c',mentions:[ref]},{sources:[source]}),[])
})
test('resolves derived summaries to their own original paragraph references',()=>{
 const summary={id:'summary',version:1,sourceType:'derived_summary',materialKind:'background',text:'成帝为张禹弟子。'}
 const p={...project,sources:[source,summary],materialInputOrigins:{background:{paragraphs:[{text:summary.text,references:[ref]},{text:'朱云上书。',references:[{...ref,quote:'朱云上书。',start:12}]}]}}}
 const rows=personEvidence(p,{id:'c',mentions:[{sourceId:'summary',sourceVersion:1,quote:summary.text}]})
 assert.equal(rows.length,1);assert.equal(rows[0].quote,ref.quote)
 p.materialInputOrigins.background.stale=true
 assert.deepEqual(personEvidence(p,{mentions:[{sourceId:'summary',quote:summary.text}]}),[])
})
test('uses structured person citations while excluding observations and other people',()=>{
 const structured={sources:[source],people:[{id:'p',characterId:'c',referenceIds:['e']}],evidence:[{id:'e',...ref},{id:'unrelated',...ref,quote:'朱云上书。',start:12}]}
 assert.equal(personEvidence(project,{id:'c'},structured)[0].quote,ref.quote)
 assert.deepEqual(personEvidence(project,{id:'other'},structured),[])
 const observation={id:'visual',version:1,sourceType:'visual_observation',text:'黄袍'}
 assert.deepEqual(personEvidence({sources:[observation]},{mentions:[{sourceId:'visual',quote:'黄袍'}]}),[])
})
