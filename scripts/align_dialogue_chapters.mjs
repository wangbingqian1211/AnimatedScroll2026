import fs from 'node:fs'
import ts from 'typescript'
const [input,output]=process.argv.slice(2)
if(!input||!output)throw Error('Provide project snapshot and output paths')
const code=ts.transpileModule(fs.readFileSync(new URL('../src/dialogueStory.ts',import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText
const {makeInteractionDraft}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'))
const project=JSON.parse(fs.readFileSync(input,'utf8'))
fs.writeFileSync(output,JSON.stringify(makeInteractionDraft(project),null,2),'utf8')
