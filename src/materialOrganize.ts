/** The sole submission path for selected PDFs, uploaded documents and text. */
export async function organizeMaterials(s:any,selections?:{documentId:string;pages:number[]}[]){
 const pid=s.p.value.id
 const libraryIds=[...new Set<string>(s.p.value.authoringDrafts?.materialSources?.libraryIds||[])]
 const input={...s.rec('material','main').draft.literatureInput}
 const documents=selections?[...selections]:s.p.value.documents.filter((d:any)=>!d.librarySourceId).map((d:any)=>({documentId:d.id,pages:[]}))
 if(!libraryIds.length&&!documents.length&&!input.text?.trim())throw Error('请勾选 PDF、上传资料或补充文本后，再点击整理资料')
 function stillCurrent(){if(s.p.value.id!==pid)throw Error('已切换项目，请在当前项目重新点击整理资料')}
 await s.saveAll();stillCurrent()
 if(libraryIds.length){
  const result=await s.api(`/projects/${pid}/source-library/import`,'POST',{version:s.p.value.version,sourceIds:libraryIds})
  stillCurrent();await s.legacy(result.project)
  for(const documentId of result.documentIds)documents.push({documentId,pages:[]})
 }
 if(input.text?.trim()){
  const result=await s.api(`/projects/${pid}/documents/text`,'POST',{version:s.p.value.version,...input})
  stillCurrent();await s.legacy(result.project)
  s.rec('material','main').draft.literatureInput={...input,documentId:result.documentId,sourceVersion:result.sourceVersion}
  documents.push({documentId:result.documentId,pages:[]})
  await s.saveAll();stillCurrent()
 }
 const unique=[...new Map<string,{documentId:string;pages:number[]}>(documents.map((d:any)=>[d.documentId,d])).values()]
 await s.api(`/projects/${pid}/tasks`,'POST',{version:s.p.value.version,kind:'document_analysis',targetArtwork:s.p.value.targetArtwork||s.p.value.artworkName||s.p.value.title,documents:unique,trigger:'user_button',autoEnable:true})
 stillCurrent();await s.syncLatest()
}
