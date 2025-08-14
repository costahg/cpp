import sqlite3
from typing import Optional

def connect(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con

SCHEMA_SQL = r"""
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS files(
  path TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  line_count INTEGER NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(content, path UNINDEXED, content_rowid);
CREATE TABLE IF NOT EXISTS symbols(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  fq_name TEXT,
  signature TEXT,
  header TEXT,
  impl TEXT,
  includes TEXT,
  inherits TEXT,
  macros TEXT,
  refs TEXT,
  path TEXT,
  line_start INTEGER,
  line_end INTEGER
);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(kind);
"""

def bootstrap(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA_SQL)
    con.commit()

def upsert_file(con: sqlite3.Connection, path: str, content: str) -> None:
    line_count = content.count("\n") + 1 if content else 0
    con.execute("INSERT OR REPLACE INTO files(path, content, line_count) VALUES(?,?,?)", (path, content, line_count))
    # keep FTS table in sync
    cur = con.execute("SELECT rowid FROM files WHERE path=?", (path,))
    row = cur.fetchone()
    if row:
        rid = row["rowid"]
        con.execute("DELETE FROM files_fts WHERE rowid=?", (rid,))
        con.execute("INSERT INTO files_fts(rowid, content, path) VALUES(?, ?, ?)", (rid, content, path))

def insert_symbol(con: sqlite3.Connection, row: dict) -> None:
    cols = [
        "kind","name","fq_name","signature","header","impl","includes","inherits","macros","refs","path","line_start","line_end"
    ]
    con.execute(
        f"INSERT INTO symbols({','.join(cols)}) VALUES({','.join(['?']*len(cols))})",
        [row.get(k) for k in cols]
    )

def search(con: sqlite3.Connection, q: str, kind: Optional[str], limit: int = 20):
    hits = []
    if kind in {"class","method","enum","signal","typedef","macro","manifest","manifest_item"}:
        cur = con.execute(
            "SELECT kind,name,COALESCE(fq_name, name) as fq_name, path, signature FROM symbols WHERE kind=? AND (name LIKE ? OR COALESCE(fq_name,'') LIKE ?) LIMIT ?",
            (kind, f"%{q}%", f"%{q}%", limit)
        )
        for r in cur.fetchall():
            hits.append({"kind": r["kind"], "name": r["fq_name"], "path": r["path"], "signature": r["signature"], "score": 0.9})
    else:
        cur = con.execute(
            "SELECT kind,name,COALESCE(fq_name, name) as fq_name, path, signature FROM symbols WHERE name LIKE ? OR COALESCE(fq_name,'') LIKE ? LIMIT ?",
            (f"%{q}%", f"%{q}%", limit)
        )
        for r in cur.fetchall():
            hits.append({"kind": r["kind"], "name": r["fq_name"], "path": r["path"], "signature": r["signature"], "score": 0.85})
        cur = con.execute(
            "SELECT path, snippet(files_fts, 0, '', '', ' … ', 8) AS snip FROM files_fts WHERE files_fts MATCH ? LIMIT ?",
            (q, max(0, limit - len(hits)))
        )
        for r in cur.fetchall():
            hits.append({"kind": "file", "name": r["path"], "path": r["path"], "signature": r["snip"], "score": 0.7})
    return hits[:limit]
