"""Copy a consistent SQLite snapshot into an empty MySQL database; never overwrite."""
import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from backend import config, storage, catalog


def snapshot(source, destination):
    with sqlite3.connect(source.as_uri()+'?mode=ro', uri=True) as src, sqlite3.connect(destination) as dest:
        src.backup(dest)


def migrate(source, verify_only=False):
    if storage.backend()!='mysql':
        raise ValueError('请先配置 .env.mysql 并选择 mysql；迁移不会使用 SQLite 作为目标。')
    if not source.is_file():raise ValueError('源数据库不存在。')
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
    backup=config.ROOT/'data'/'backups'/f'before-mysql-{stamp}.sqlite'
    backup.parent.mkdir(exist_ok=True,parents=True)
    snapshot(source,backup)
    with sqlite3.connect(backup) as src:
        data={table:src.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall() for table in ('projects','events','tasks')}
    expected={table:{row[0]:tuple(row) for row in rows} for table,rows in data.items()}
    with storage.connect(config.ROOT/'data') as dest:
        dest.execute('BEGIN IMMEDIATE')
        if not verify_only:
            if any(dest.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in data):
                raise ValueError('目标 MySQL 已有项目、日志或任务，已停止，未覆盖任何资料。可使用 --verify-only 校验。')
            for table,rows in data.items():
                for row in rows:
                    marks=','.join('?' for _ in row)
                    dest.execute(f'INSERT INTO {table} VALUES ({marks})',row)
            for pid,body in data['projects']:
                catalog.synchronize(dest,json.loads(body))
        for table,rows in expected.items():
            actual={r[0]:tuple(r) for r in dest.execute(f'SELECT * FROM {table}').fetchall()}
            if actual!=rows:raise ValueError(f'{table} 的迁移内容校验未通过，事务已取消。')
        counts={table:len(rows) for table,rows in data.items()}
        for table,key in [('artwork_people','characters'),('artwork_sources','sources'),('artwork_relations','personRelations'),('artwork_events','historicalEvents')]:
            wanted=sum(len(json.loads(body).get(key,[])) for _,body in data['projects'])
            actual=dest.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            if actual!=wanted:raise ValueError(f'{table} 的记录数量不一致，事务已取消。')
            counts[table]=actual
    report=dict(sourceBackup=str(backup),target='mysql',verified=True,counts=counts)
    report_path=config.ROOT/'data'/f'mysql-migration-{stamp}.json'
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=config.ROOT/'data'/'projects.sqlite')
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    try:migrate(args.source.resolve(),args.verify_only)
    except Exception as exc:
        # Do not echo database URLs or connection exception arguments with credentials.
        print(str(exc) if isinstance(exc,ValueError) else 'MySQL 连接或迁移失败，事务已回滚。请检查容器状态与本机配置。')
        raise SystemExit(1)
