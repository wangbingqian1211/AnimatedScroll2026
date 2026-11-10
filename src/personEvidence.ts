export type PersonEvidence={key:string;quote:string;title:string;page?:number;location:string}

// Only linked, exact passages from the project's sources qualify as evidence.
// Generated summaries and visual observations are not original source text.
export function personEvidence(project:any,character:any,structured?:any):PersonEvidence[]{
 if(!character)return []
 const sources=[...(project.sources||[]),...(structured?.sources||[])]
 const refs=[...(character.mentions||[]),...(character.depictionReferences||[])]
 const person=structured?.people?.find((p:any)=>p.characterId===character.id||p.id===character.id)
 const ids=new Set(person?.referenceIds||[])
 for(const line of structured?.statements||[])if(person&&line.personId===person.id&&line.origin!=='observation')for(const id of line.referenceIds||[])ids.add(id)
 refs.push(...(structured?.evidence||[]).filter((e:any)=>ids.has(e.id)))
 const result=new Map<string,PersonEvidence>()
 function add(ref:any,resolveSummary=true){
  if(typeof ref.quote!=='string'||!ref.quote.trim())return
  const source=sources.find((s:any)=>s.id===ref.sourceId&&(ref.sourceVersion==null||s.version===ref.sourceVersion))
  if(!source||source.sourceType==='visual_observation')return
  // Prefer the current project version; an old snapshot must not revive removed text.
  const current=(project.sources||[]).find((s:any)=>s.id===source.id)
  if(current&&current.version!==source.version)return
  const text=source.text||''
  // Stored offsets may count Unicode code points rather than JavaScript code units.
  const start=Number.isInteger(ref.start)&&text.slice(ref.start,ref.start+ref.quote.length)===ref.quote?ref.start:text.indexOf(ref.quote)
  if(start<0||text.slice(start,start+ref.quote.length)!==ref.quote)return
  if(source.sourceType==='derived_summary'){
   if(!resolveSummary)return
   const origin=project.materialInputOrigins?.[source.materialKind]
   if(!origin||origin.stale||source.originStale)return
   for(const paragraph of origin.paragraphs||[]){
    // Resolve only the paragraph containing this mention, never all summary citations.
    if(paragraph.text?.includes(ref.quote))for(const original of paragraph.references||[])add(original,false)
   }
   return
  }
  const document=(project.documents||[]).find((d:any)=>d.id===source.documentId)
  const key=`${source.id}:${source.version}:${start}:${ref.quote.length}`
  result.set(key,{key,quote:ref.quote,title:document?.title||source.title||'所选资料',page:source.page||ref.page,location:source.location||ref.locator||''})
 }
 for(const ref of refs)add(ref)
 return [...result.values()]
}
