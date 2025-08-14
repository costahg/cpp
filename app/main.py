import os, json
from fastapi import FastAPI, HTTPException, Query
from typing import Optional
from .search import connect, bootstrap, search as db_search
from .parsers import parse_gdextension_manifest

DB_PATH = os.getenv("DB_PATH", "/data/index.db")

app = FastAPI(title="godot-cpp-index", version="1.0.0")

@app.on_event("startup")
def _startup():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = connect(DB_PATH)
    bootstrap(con)
    con.close()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/search")
def search(q: str = Query(..., min_length=1), kind: Optional[str] = None, limit: int = Query(20, ge=1, le=50)):
    con = connect(DB_PATH)
    try:
        hits = db_search(con, q, kind, limit)
        return {"hits": hits}
    finally:
        con.close()

@app.get("/symbol/{name}")
def get_symbol(name: str):
    con = connect(DB_PATH)
    try:
        cur = con.execute("SELECT * FROM symbols WHERE fq_name=? OR name=? ORDER BY CASE WHEN fq_name=? THEN 0 ELSE 1 END LIMIT 1", (name, name, name))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, detail="Symbol not found")
        return {
            "kind": row["kind"],
            "name": row["name"],
            "fq_name": row["fq_name"],
            "signature": row["signature"],
            "header": row["header"],
            "impl": row["impl"],
            "includes": None,
            "inherits": row["inherits"],
            "macros": None,
            "references": row.get("refs") if isinstance(row, dict) else row["refs"],
            "path": row["path"],
            "line_span": {"start": row["line_start"], "end": row["line_end"]}
        }
    finally:
        con.close()

@app.get("/file")
def get_file(path: str, start: int = 1, end: Optional[int] = None):
    con = connect(DB_PATH)
    try:
        cur = con.execute("SELECT content, line_count FROM files WHERE path=?", (path,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, detail="File not indexed")
        content = row["content"]
        lines = content.splitlines()
        if end is None:
            end = min(len(lines), start + 199)
        start = max(1, start)
        end = min(len(lines), end)
        if start > end:
            raise HTTPException(400, detail="Invalid range")
        slice_text = "\n".join(lines[start-1:end])
        return {"path": path, "start": start, "end": end, "text": slice_text}
    finally:
        con.close()

@app.get("/manifest")
def get_manifest(path: str):
    con = connect(DB_PATH)
    try:
        cur = con.execute("SELECT content FROM files WHERE path=?", (path,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, detail="Manifest not found")
        man = parse_gdextension_manifest(row["content"])
        man_obj = {"path": path, **man}
        return man_obj
    finally:
        con.close()

@app.get("/extension")
def get_extension(class_: Optional[str] = Query(None, alias="class"), method: Optional[str] = None, signal: Optional[str] = None, version: Optional[str] = None):
    con = connect(DB_PATH)
    try:
        cur = con.execute("SELECT content, path FROM files WHERE path LIKE '%extension_api.json%' LIMIT 1")
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, detail="extension_api.json not indexed")
        try:
            data = json.loads(row["content"])
        except Exception:
            raise HTTPException(500, detail="Invalid JSON in extension_api.json")
        items = []
        for cls in data.get("classes", []):
            if class_ and cls.get("name") != class_:
                continue
            items.append({"kind": "class", "class_": cls.get("name"), "name": cls.get("name")})
            for m in cls.get("methods", []):
                if method and m.get("name") != method:
                    continue
                items.append({"kind": "method", "class_": cls.get("name"), "name": m.get("name"), "signature": m.get("return_type", "void") + " " + m.get("name", "")})
            for s in cls.get("signals", []):
                if signal and s.get("name") != signal:
                    continue
                items.append({"kind": "signal", "class_": cls.get("name"), "name": s.get("name")})
        return {"items": items}
    finally:
        con.close()
