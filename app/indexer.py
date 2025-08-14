import os
from .search import upsert_file, insert_symbol
from .parsers import parse_dump_blocks, parse_gdextension_manifest

def index_from_dump(con, dump_text: str) -> None:
    blocks = parse_dump_blocks(dump_text)
    for path, content in blocks:
        upsert_file(con, path, content)
        if path.endswith('.gdextension'):
            man = parse_gdextension_manifest(content)
            insert_symbol(con, {
                "kind": "manifest",
                "name": os.path.basename(path),
                "fq_name": "gdextension_manifest",
                "signature": "[configuration],[libraries]",
                "header": None,
                "impl": None,
                "includes": None,
                "inherits": None,
                "macros": None,
                "refs": None,
                "path": path,
                "line_start": 1,
                "line_end": content.count('\n') + 1
            })
            if 'entry_symbol' in man["configuration"]:
                insert_symbol(con, {
                    "kind": "manifest_item",
                    "name": "entry_symbol",
                    "fq_name": man["configuration"]["entry_symbol"],
                    "signature": man["configuration"]["entry_symbol"],
                    "header": None,
                    "impl": None,
                    "includes": None,
                    "inherits": None,
                    "macros": None,
                    "refs": None,
                    "path": path,
                    "line_start": 1,
                    "line_end": 1
                })
