"""Validated artwork catalog and SQL read models, committed with each project revision."""
import json
from . import storage

TABLES = {
    'artwork_catalog': 'project_id TEXT PRIMARY KEY, name TEXT NOT NULL, body TEXT NOT NULL',
    'artwork_people': 'project_id TEXT NOT NULL, id TEXT NOT NULL, name TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(project_id,id)',
    'artwork_sources': 'project_id TEXT NOT NULL, id TEXT NOT NULL, title TEXT NOT NULL, version INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(project_id,id)',
    'artwork_relations': 'project_id TEXT NOT NULL, id TEXT NOT NULL, from_id TEXT NOT NULL, to_id TEXT NOT NULL, label TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(project_id,id)',
    'artwork_events': 'project_id TEXT NOT NULL, id TEXT NOT NULL, title TEXT NOT NULL, time_label TEXT NOT NULL, position INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(project_id,id)',
}

def schema(conn):
    for table, columns in TABLES.items():
        conn.execute(f'CREATE TABLE IF NOT EXISTS {table} ({columns})')
    conn.execute('CREATE INDEX IF NOT EXISTS artwork_people_name ON artwork_people(name)')
    conn.execute('CREATE INDEX IF NOT EXISTS artwork_relations_from ON artwork_relations(project_id,from_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS artwork_relations_to ON artwork_relations(project_id,to_id)')


def validate(project, old=None):
    people = {c['id'] for c in project['characters']}
    sources = {s['id']: s for s in project['sources']}
    ids = set()
    previous = {r['id']: r for r in (old or {}).get('personRelations', []) + (old or {}).get('historicalEvents', [])}
    for key in ('characters', 'sources'):
        keys = [r['id'] for r in project[key]]
        if len(keys) != len(set(keys)):
            raise ValueError('人物或来源编号重复')
    for row in project.get('personRelations', []) + project.get('historicalEvents', []):
        if row['id'] in ids:
            raise ValueError('资料库记录编号重复')
        ids.add(row['id'])
        linked = [row['fromId'], row['toId']] if 'fromId' in row else row.get('characterIds', [])
        if any(cid not in people for cid in linked):
            raise ValueError('关系或事件关联了不存在的人物')
        if 'fromId' in row and row['fromId'] == row['toId']:
            raise ValueError('关系两端需要选择不同人物')
        evidence = row.get('evidence', {})
        sid = evidence.get('sourceId', '')
        if sid and sid not in sources:
            raise ValueError('关系或事件关联了不存在的来源')
        unchanged = previous.get(row['id'], {}).get('evidence') == evidence
        if sid and evidence.get('quote') and not unchanged and evidence['quote'] not in sources[sid]['text']:
            raise ValueError('关系或事件的引文必须逐字来自所选来源')
        if not sid and evidence.get('quote'):
            raise ValueError('填写引文时需要选择来源')


def synchronize(conn, project):
    # The versioned project is authoritative. These searchable SQL rows are a
    # transactionally maintained projection, never an independently editable copy.
    pid = project['id']
    dump = lambda value: json.dumps(value, ensure_ascii=False)
    info = project.get('paintingInfo', {})
    name = info.get('name') or project['title']
    for table in TABLES:
        conn.execute(f'DELETE FROM {table} WHERE project_id=?', (pid,))
    conn.execute('INSERT INTO artwork_catalog VALUES (?,?,?)', (pid, name, dump(info)))
    for row in project['characters']:
        conn.execute('INSERT INTO artwork_people VALUES (?,?,?,?)', (pid, row['id'], row['name'], dump(row)))
    for row in project['sources']:
        conn.execute('INSERT INTO artwork_sources VALUES (?,?,?,?,?)', (pid, row['id'], row['title'], row['version'], dump(row)))
    for row in project.get('personRelations', []):
        conn.execute('INSERT INTO artwork_relations VALUES (?,?,?,?,?,?)', (pid, row['id'], row['fromId'], row['toId'], row['label'], dump(row)))
    for index, row in enumerate(project.get('historicalEvents', [])):
        conn.execute('INSERT INTO artwork_events VALUES (?,?,?,?,?,?)', (pid, row['id'], row['title'], row.get('time',''), index, dump(row)))


def install(app, get, db):
    @app.get('/api/projects/{pid}/catalog')
    def read_catalog(pid: str):
        p = get(pid)
        sources = {s['id']: s for s in p['sources']}
        def evidence_state(row):
            e = row.get('evidence', {})
            s = sources.get(e.get('sourceId'))
            if not s or not e.get('quote'):
                return 'unlinked'
            if s['version'] != e.get('sourceVersion') or e['quote'] not in s['text']:
                return 'stale'
            return 'linked'
        return dict(projectId=pid, version=p['version'], storage=storage.backend(),
            painting=p.get('paintingInfo', {}), characters=p['characters'], sources=p['sources'],
            relations=[dict(r, evidenceState=evidence_state(r)) for r in p.get('personRelations', [])],
            events=[dict(e, evidenceState=evidence_state(e)) for e in p.get('historicalEvents', [])])

    def backfill():
        with db() as conn:
            for body, in conn.execute('SELECT body FROM projects').fetchall():
                synchronize(conn, json.loads(body))
    app.router.add_event_handler('startup', backfill)
