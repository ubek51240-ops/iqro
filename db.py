import os
import sqlite3
import json

DATABASE_URL = os.environ.get('DATABASE_URL', '')
USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg2
    import psycopg2.extras

DB_FILE = os.path.join(os.path.dirname(__file__), 'database.db')


class DB:
    def __init__(self):
        if USE_PG:
            self.conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            self.conn.autocommit = False
        else:
            self.conn = sqlite3.connect(DB_FILE, timeout=30)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute('PRAGMA journal_mode=WAL')
            self.conn.execute('PRAGMA busy_timeout=30000')

    def _convert(self, query):
        if not USE_PG:
            return query
        query = query.replace('?', '%s')
        if 'INSERT OR REPLACE INTO settings' in query:
            query = query.replace(
                'INSERT OR REPLACE INTO settings',
                'INSERT INTO settings'
            )
            query += ' ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value'
        elif 'INSERT OR IGNORE INTO settings' in query:
            query = query.replace(
                'INSERT OR IGNORE INTO settings',
                'INSERT INTO settings'
            )
            query += ' ON CONFLICT (key) DO NOTHING'
        return query

    def execute(self, query, params=None):
        pg_query = self._convert(query)
        if USE_PG:
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(pg_query, params or ())
        else:
            cur = self.conn.cursor()
            cur.execute(pg_query, params or ())
        return cur

    def executemany(self, query, params_list):
        pg_query = self._convert(query)
        if USE_PG:
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.executemany(pg_query, params_list)
        else:
            cur = self.conn.cursor()
            cur.executemany(pg_query, params_list)
        return cur

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def lastrowid(self, cur):
        if USE_PG:
            cur2 = self.conn.cursor()
            cur2.execute("SELECT LASTVAL()")
            row = cur2.fetchone()
            return row[0] if row else None
        else:
            return cur.lastrowid

    def insert_and_get_id(self, query, params=None, id_column='id'):
        if USE_PG:
            pg_query = self._convert(query)
            pg_query += f' RETURNING {id_column}'
            cur = self.execute(pg_query, params)
            row = cur.fetchone()
            self.commit()
            return row[id_column] if row else None
        else:
            cur = self.execute(query, params)
            self.commit()
            return cur.lastrowid

    def table_exists(self, table_name):
        if USE_PG:
            cur = self.execute(
                "SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name = %s)",
                (table_name,)
            )
            return cur.fetchone()['exists']
        else:
            cur = self.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,)
            )
            return cur.fetchone() is not None

    def column_names(self, table_name):
        if USE_PG:
            cur = self.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
                (table_name,)
            )
            return [r['column_name'] for r in cur.fetchall()]
        else:
            cur = self.execute(f"PRAGMA table_info({table_name})")
            return [r['name'] for r in cur.fetchall()]

    def add_column(self, table_name, column_def):
        if USE_PG:
            self.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
        else:
            self.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")