"""SQLite compatibility and pooled MySQL transactions for the existing storage API."""
import os
import sqlite3
from functools import lru_cache
from . import config


def backend():
    kind = os.getenv('CREATION_DB_BACKEND', 'sqlite').lower()
    if kind not in ('sqlite', 'mysql'):
        raise ValueError('CREATION_DB_BACKEND must be sqlite or mysql')
    return kind


@lru_cache(maxsize=4)
def mysql_engine(host, port, database, user, password):
    from sqlalchemy import create_engine, URL, MetaData, Table, Column, String, Integer, Index
    from sqlalchemy.dialects.mysql import LONGTEXT
    url = URL.create('mysql+pymysql', username=user, password=password,
                     host=host, port=int(port), database=database, query={'charset':'utf8mb4'})
    engine = create_engine(url, pool_pre_ping=True, pool_recycle=1800,
                           connect_args={'connect_timeout':10}, hide_parameters=True)
    meta = MetaData()
    def table(name, *columns):
        return Table(name, meta, *columns, mysql_engine='InnoDB', mysql_charset='utf8mb4')
    def text(name): return Column(name, LONGTEXT, nullable=False)
    def key(name='id'): return Column(name, String(128), primary_key=True)
    table('projects', key(), text('body'))
    table('events', key(), Column('project',String(128),index=True), Column('time',String(64)),
          Column('action',String(128)), text('before'),text('after'),text('meta'))
    table('tasks', key(), Column('project',String(128),index=True), text('body'))
    table('video_jobs', key(), Column('project',String(128),index=True), text('body'))
    table('artwork_catalog',key('project_id'),text('name'),text('body'))
    table('artwork_people',key('project_id'),key(),text('name'),text('body'))
    table('artwork_sources',key('project_id'),key(),text('title'),Column('version',Integer),text('body'))
    table('artwork_relations',key('project_id'),key(),Column('from_id',String(128)),Column('to_id',String(128)),Column('label',String(100)),text('body'))
    table('artwork_events',key('project_id'),key(),Column('title',String(200)),Column('time_label',String(512)),Column('position',Integer),text('body'))
    Index('artwork_relations_from',meta.tables['artwork_relations'].c.project_id,meta.tables['artwork_relations'].c.from_id)
    Index('artwork_relations_to',meta.tables['artwork_relations'].c.project_id,meta.tables['artwork_relations'].c.to_id)
    meta.create_all(engine)
    return engine


def engine():
    required = ('MYSQL_DATABASE','MYSQL_USER','MYSQL_PASSWORD')
    if not all(os.getenv(k) for k in required):
        raise RuntimeError('MySQL 配置不完整，请填写 .env.mysql。不会回退到 SQLite。')
    return mysql_engine(os.getenv('MYSQL_HOST','127.0.0.1'),os.getenv('MYSQL_PORT','3307'),
                        os.environ['MYSQL_DATABASE'],os.environ['MYSQL_USER'],os.environ['MYSQL_PASSWORD'])


class Rows:
    def __init__(self, rows): self.rows=rows
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return self.rows
    def __iter__(self): return iter(self.rows)


class MySQLConnection:
    dialect = 'mysql'
    def __init__(self): self.conn=engine().raw_connection();self.write=False
    def __enter__(self): return self
    def __exit__(self,kind,value,traceback):
        try:
            if kind: self.conn.rollback()
            else: self.conn.commit()
        finally: self.conn.close()
    def execute(self,sql,params=()):
        if sql=='BEGIN IMMEDIATE':
            self.conn.begin();self.write=True;return Rows([])
        if sql.startswith('INSERT OR REPLACE INTO projects'):
            sql='INSERT INTO projects (id,body) VALUES (?,?) ON DUPLICATE KEY UPDATE body=VALUES(body)'
        elif sql.startswith('INSERT OR REPLACE INTO tasks'):
            sql='INSERT INTO tasks (id,project,body) VALUES (?,?,?) ON DUPLICATE KEY UPDATE project=VALUES(project),body=VALUES(body)'
        if 'ORDER BY rowid DESC' in sql:
            sql=sql.replace('ORDER BY rowid DESC',"ORDER BY JSON_UNQUOTE(JSON_EXTRACT(body,'$.time')) DESC,id DESC")
        elif 'ORDER BY rowid' in sql:
            sql=sql.replace('ORDER BY rowid','ORDER BY time,id')
        if self.write and sql=='SELECT body FROM projects WHERE id=?': sql+=' FOR UPDATE'
        sql=sql.replace('action,before,after,meta','action,`before`,`after`,meta')
        # SQL is internal, with ? placeholders; values remain bound separately.
        sql=sql.replace('?', '%s')
        with self.conn.cursor() as cur:
            cur.execute(sql,params)
            return Rows(list(cur.fetchall()) if cur.description else [])


def connect(data):
    if backend()=='mysql':return MySQLConnection()
    return sqlite3.connect(data/'projects.sqlite')
