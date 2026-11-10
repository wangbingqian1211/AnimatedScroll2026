import copy
from backend import main, source_library, documents, structured


def create(client, title='折槛图'):
    return client.post('/api/projects', json={'title': title}).json()


def available(client, project):
    response = client.get(f"/api/projects/{project['id']}/source-library")
    assert response.status_code == 200, response.text
    return response.json()


def add(client, project, ids):
    return client.post(f"/api/projects/{project['id']}/source-library/import", json={'version': project['version'], 'sourceIds': ids})


def test_catalog_lists_original_pdfs_with_summaries(client):
    p = create(client)
    result = available(client, p)
    assert result['matched'] and len(result['items']) == len(list(source_library.PDF_LIBRARY.glob('*.pdf')))
    assert result['schemaVersion'] == 'pdf-library-2'
    assert all(row['title'] == row['filename'] for row in result['items'])
    assert all(row['recommended'] and not row['imported'] for row in result['items'])
    assert all(row['format'] == 'pdf' and row['summary'] and row['pageCount'] > 0 for row in result['items'])
    assert {row['filename'] for row in result['items']} == {path.name for path in source_library.PDF_LIBRARY.glob('*.pdf')}
    for row in result['items']:
        response = client.get(row['fileUrl'])
        assert response.status_code == 200
        assert response.headers['content-type'] == 'application/pdf'
        assert response.headers['content-disposition'].startswith('inline;')
        assert response.content == source_library.pdf_path(row).read_bytes()
    assert client.get(f"/api/projects/{p['id']}/source-library/missing/file").status_code == 404
    assert client.get('/api/projects/missing/source-library/hanshu-zhuyun-pdf/file').status_code == 404
    assert main.get(p['id'])['version'] == p['version']
    other = create(client, '步辇图')
    assert not available(client, other)['matched']
    assert not any(row['recommended'] for row in available(client, other)['items'])


def test_missing_pdf_is_not_listed(client, monkeypatch, tmp_path):
    import json
    folder = tmp_path / 'pdf-library'
    folder.mkdir()
    source = source_library.entries()[0]
    (folder / source['filename']).write_bytes(source_library.pdf_path(source).read_bytes())
    missing = dict(source, id='missing', filename='不存在.pdf')
    (folder / 'catalog.json').write_text(json.dumps({'items': [source, missing]}), encoding='utf-8')
    monkeypatch.setattr(source_library, 'PDF_LIBRARY', folder)
    rows = available(client, create(client))['items']
    assert [row['filename'] for row in rows] == [source['filename']]


def test_selected_sources_join_the_existing_literature_flow_without_ai_or_overwriting(client, monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError('import must not invoke a model')
    monkeypatch.setattr(documents, 'ask', forbidden)
    monkeypatch.setattr(structured, 'ask', forbidden)
    p = client.post('/api/sample?example=zhekan').json()
    p = main.get(p['id'])
    before = copy.deepcopy(p)
    rows = available(client, p)['items']
    response = add(client, p, [row['id'] for row in rows[:2]])
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['added'] == 2 and result['reused'] == 0
    saved = result['project']
    assert len(saved['documents']) == len(before['documents']) + 2
    for key in ('characters', 'intent', 'scenes'):
        assert saved[key] == before[key]
    assert [{k: a.get(k) for k in ('id', 'x', 'y', 'w', 'h', 'characterId')} for a in saved['annotations']] == [{k: a.get(k) for k in ('id', 'x', 'y', 'w', 'h', 'characterId')} for a in before['annotations']]
    selected = documents.selected_sources(saved, {'documents': [{'documentId': did, 'pages': []} for did in result['documentIds']]})
    assert len(selected) == sum(row['pageCount'] for row in rows[:2])
    for doc, original in zip(saved['documents'][-2:], rows[:2]):
        assert doc['format'] == 'pdf' and doc['parseStatus'] == 'ready'
        assert (main.DATA / doc['filename']).read_bytes() == source_library.pdf_path(original).read_bytes()
        sources = [row['source'] for row in selected if row['source']['documentId'] == doc['id']]
        assert len(sources) == original['pageCount']
        assert all(row['text'].strip() and not row['confirmed'] for row in sources)
        assert all(row['libraryProvenance']['origin']['filename'] == original['filename'] for row in sources)
    assert sum(row['imported'] for row in available(client, saved)['items']) == 2


def test_duplicates_retry_and_edited_imports_never_overwrite_notes(client):
    p = create(client)
    entry = available(client, p)['items'][0]
    first = add(client, p, [entry['id'], entry['id']]).json()
    p = first['project']
    assert first['added'] == 1
    repeat = add(client, p, [entry['id']]).json()
    assert repeat['added'] == 0 and repeat['reused'] == 1
    assert repeat['project']['version'] == p['version']
    source = next(s for s in p['sources'] if s.get('documentId') == first['documentIds'][0])
    updated_text = '用户补充后的文字，必须保留'
    edited_project = copy.deepcopy(p)
    edited_source = next(s for s in edited_project['sources'] if s['id'] == source['id'])
    edited_source['text'] = updated_text
    p = main.save(edited_project, p['version'], 'test:edit_source')
    result = add(client, p, [entry['id']]).json()
    assert result['added'] == 0
    assert len(result['project']['documents']) == 1
    assert result['project']['sources'][0]['text'] == updated_text
    assert result['project']['sources'][0]['libraryProvenance']['origin'] == {'system': 'PDF资料库', 'filename': entry['filename']}
    other = create(client)
    assert add(client, other, [entry['id']]).json()['added'] == 1


def test_invalid_batch_and_stale_version_leave_no_partial_documents_or_files(client):
    p = create(client)
    entry = available(client, p)['items'][0]
    files = set(main.DATA.iterdir())
    assert add(client, p, [entry['id'], 'missing']).status_code == 422
    assert add(client, p, []).status_code == 422
    assert set(main.DATA.iterdir()) == files
    main.save(copy.deepcopy(p), p['version'], 'test:concurrent_change')
    assert add(client, p, [entry['id']]).status_code == 409
    assert not main.get(p['id'])['documents']
    assert set(main.DATA.iterdir()) == files


def test_failed_save_removes_only_new_library_files(client, monkeypatch):
    p = create(client)
    entry = available(client, p)['items'][0]
    keep = main.DATA / 'existing.txt'
    keep.write_text('existing data', encoding='utf-8')
    files = set(main.DATA.iterdir())
    original = source_library.reconcile
    def concurrent(old, new):
        current = main.get(p['id'])
        main.save(current, current['version'], 'test:concurrent_change')
        return original(old, new)
    monkeypatch.setattr(source_library, 'reconcile', concurrent)
    assert add(client, p, [entry['id']]).status_code == 409
    assert set(main.DATA.iterdir()) == files
    assert keep.read_text(encoding='utf-8') == 'existing data'
    assert not main.get(p['id'])['documents']
