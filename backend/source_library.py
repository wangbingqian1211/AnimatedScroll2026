"""Bundled PDF literature: browse originals and import page-level text locally."""
import copy
import hashlib
import json
from pathlib import Path
from fastapi import HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from . import config, documents
from .domain import uid, reconcile

PDF_LIBRARY = config.ROOT / 'examples' / 'assets' / 'pdf资料'


def entries():
    catalog = PDF_LIBRARY / 'catalog.json'
    rows = json.loads(catalog.read_text(encoding='utf-8'))['items'] if catalog.exists() else []
    known = {row['filename'] for row in rows}
    for path in sorted(PDF_LIBRARY.glob('*.pdf')):
        if path.name in known:
            continue
        import pypdfium2 as pdfium
        with documents._pdf_lock:
            with pdfium.PdfDocument(path) as pdf:
                page = pdf[0]
                textpage = page.get_textpage()
                try:
                    excerpt = ' '.join(textpage.get_text_range().split())[:150]
                finally:
                    textpage.close()
                    page.close()
                rows.append(dict(id='pdf-'+hashlib.sha256(path.name.encode()).hexdigest()[:16],
                                 filename=path.name, pageCount=len(pdf),
                                 summary='内容节选：'+excerpt if excerpt else 'PDF文献，可打开阅读原文。'))
    result = []
    for row in rows:
        try:
            pdf_path(row)
        except HTTPException:
            continue
        result.append(dict(row, title=row['filename'], format='pdf',
                           citation=Path(row['filename']).stem))
    return result


def pdf_path(entry):
    path = (PDF_LIBRARY / entry['filename']).resolve()
    if path.parent != PDF_LIBRARY.resolve() or not path.is_file() or path.suffix.lower() != '.pdf':
        raise HTTPException(404, 'PDF文件不存在')
    return path


def existing_document(project, entry):
    return next((doc for doc in project['documents']
                 if doc.get('librarySourceId') == entry['id']), None)


class ImportSources(BaseModel):
    version: int
    sourceIds: list[str] = Field(min_length=1, max_length=100)


def install(app, get, save, data):
    @app.get('/api/projects/{pid}/source-library')
    def available(pid: str, response: Response):
        response.headers['Cache-Control'] = 'no-store'
        project = get(pid)
        name = project.get('artworkName') or project['title']
        matched = '折槛' in name or '折檻' in name
        rows = []
        for entry in entries():
            doc = existing_document(project, entry)
            rows.append(dict(entry, recommended=matched, imported=bool(doc),
                             documentId=doc['id'] if doc else None,
                             fileUrl=f"/api/projects/{pid}/source-library/{entry['id']}/file"))
        return dict(schemaVersion='pdf-library-2', items=rows, artworkTitle='折槛图', matched=matched)

    @app.get('/api/projects/{pid}/source-library/{sid}/file')
    def original_pdf(pid: str, sid: str):
        get(pid)
        entry = next((row for row in entries() if row['id'] == sid), None)
        if not entry:
            raise HTTPException(404, 'PDF文件不存在')
        return FileResponse(pdf_path(entry), media_type='application/pdf',
                            filename=entry['filename'], content_disposition_type='inline')

    @app.post('/api/projects/{pid}/source-library/import')
    def import_selected(pid: str, req: ImportSources):
        project = get(pid)
        if project['version'] != req.version:
            raise HTTPException(409, '项目已变化，请刷新后加入资料；已选资料不会覆盖当前内容')
        catalog = {entry['id']: entry for entry in entries()}
        selected = list(dict.fromkeys(req.sourceIds))
        if any(key not in catalog for key in selected):
            raise HTTPException(422, '所选资料不存在，请重新选择')
        project = copy.deepcopy(project)
        created, files, reused = [], [], []
        try:
            for key in selected:
                entry = catalog[key]
                old = existing_document(project, entry)
                if old:
                    reused.append(old['id'])
                    continue
                did, name = uid(), uid() + '.pdf'
                content = pdf_path(entry).read_bytes()
                path = Path(data()) / name
                with path.open('xb') as output:
                    files.append(path)
                    output.write(content)
                provenance = dict(librarySourceId=key, kind='pdf',
                                  origin=dict(system='PDF资料库', filename=entry['filename']))
                doc = dict(id=did, filename=name, title=entry['title'], citation=entry['citation'],
                           format='pdf', inputMode='file', parseStatus='ready',
                           parseVersion=documents.PARSE_VERSION,
                           contentHash=hashlib.sha256(content).hexdigest(), sizeBytes=len(content),
                           librarySourceId=key, libraryProvenance=provenance)
                doc['pages'] = documents.parse_pdf(path, doc)
                doc['pageCount'] = len(doc['pages'])
                project['documents'].append(doc)
                sources = documents.parsed_sources(doc, [])
                for source in sources:
                    source['libraryProvenance'] = provenance
                project['sources'].extend(sources)
                created.append(did)
            if created:
                project = reconcile(get(pid), project)
                project = save(project, req.version, 'import_source_library',
                               dict(sourceIds=selected, documentIds=created, trigger='user_button'))
            return dict(project=project, added=len(created), reused=len(reused), documentIds=created + reused)
        except Exception:
            for path in files:
                path.unlink(missing_ok=True)
            raise
