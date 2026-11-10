import {test} from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import ts from 'typescript'
const js=ts.transpileModule(readFileSync(new URL('../src/materialOrganize.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText
const {organizeMaterials}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'))
function studio({libraryIds=[],docs=[],input={}}={}){
 const calls=[],draft={literatureInput:input}
 const s={p:{value:{id:'p',version:1,title:'画作',documents:docs,materialInputs:{background:'固定背景'},authoringDrafts:{materialSources:{libraryIds}}}},rec:()=>({draft}),saveAll:async()=>{},syncLatest:async()=>{},legacy:async p=>{s.p.value=p},api:async(path,method,body)=>{
 calls.push({path,body})
 if(path.endsWith('/source-library/import'))return {project:{...s.p.value,version:2},documentIds:body.sourceIds.map(id=>'doc-'+id)}
 if(path.endsWith('/documents/text'))return {project:{...s.p.value,version:3},documentId:'text-doc',sourceVersion:1}
 return {}
 }};return {s,calls,draft}
}
test('chosen PDFs, uploaded files and pending text are combined only on explicit organize',async()=>{
 const {s,calls}=studio({libraryIds:['a','b'],docs:[{id:'upload'},{id:'old-library',librarySourceId:'unselected'}],input:{text:'补充原文'}})
 assert.equal(calls.length,0)
 await organizeMaterials(s)
 assert.deepEqual(calls[0].body.sourceIds,['a','b'])
 const task=calls.find(c=>c.path.endsWith('/tasks'))
 assert.deepEqual(task.body.documents.map(d=>d.documentId),['upload','doc-a','doc-b','text-doc'])
 assert.equal(task.body.version,3)
 assert.equal(task.body.kind,'document_analysis')
 assert.equal(calls.filter(c=>c.path.endsWith('/tasks')).length,1)
})
test('empty selection does not silently analyze fixed artwork background',async()=>{
 const {s,calls}=studio();await assert.rejects(()=>organizeMaterials(s),/请勾选 PDF/);assert.equal(calls.length,0)
})
test('text is included even when an explicit file selection is empty',async()=>{
 const {s,calls}=studio({input:{text:'新文本'}});await organizeMaterials(s,[])
 assert.deepEqual(calls.at(-1).body.documents,[{documentId:'text-doc',pages:[]}])
})
test('a saved text document is submitted once with the selected page range',async()=>{
 const {s,calls}=studio({docs:[{id:'text-doc'}],input:{text:'更新'}});await organizeMaterials(s)
 assert.equal(calls.at(-1).body.documents.length,1)
})
test('switching projects during save cannot submit a task to the previous project',async()=>{
 const {s,calls}=studio({libraryIds:['a']});s.saveAll=async()=>{s.p.value={...s.p.value,id:'other'}}
 await assert.rejects(()=>organizeMaterials(s),/已切换项目/);assert.equal(calls.length,0)
})
