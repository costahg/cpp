import re
import json
from typing import Tuple, Dict, Any, List

DUMP_BEGIN = re.compile(r"^===== BEGIN FILE =====\s*$")
PATH_LINE = re.compile(r"^PATH:\s*(.+?)\s*$")
CONTENT_BEGIN = re.compile(r"^----- CONTENT -----\s*$")
DUMP_END = re.compile(r"^===== END FILE =====\s*$")

INI_SECTION_RE = re.compile(r"^\[(.+?)\]\s*$")
INI_KV_RE = re.compile(r"^([A-Za-z0-9_\.]+)\s*=\s*\"?(.*?)\"?\s*$")

def parse_dump_blocks(text: str) -> List[Tuple[str, str]]:
    blocks: List[Tuple[str,str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if DUMP_BEGIN.match(lines[i]):
            i += 1
            path = None
            while i < len(lines) and not CONTENT_BEGIN.match(lines[i]):
                m_path = PATH_LINE.match(lines[i])
                if m_path:
                    path = m_path.group(1).strip().replace('\\', '/')
                i += 1
            if i < len(lines) and CONTENT_BEGIN.match(lines[i]):
                i += 1
                content_lines = []
                while i < len(lines) and not DUMP_END.match(lines[i]):
                    content_lines.append(lines[i])
                    i += 1
                blocks.append((path or "unknown", "\n".join(content_lines)))
        i += 1
    return blocks

def parse_gdextension_manifest(content: str) -> Dict[str, Any]:
    current = None
    config: Dict[str, Any] = {}
    libraries: List[Dict[str, str]] = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        msec = INI_SECTION_RE.match(line)
        if msec:
            current = msec.group(1)
            continue
        mkv = INI_KV_RE.match(line)
        if mkv and current:
            k, v = mkv.group(1), mkv.group(2)
            if current == 'configuration':
                if v.lower() in {'true','false'}:
                    vv: Any = True if v.lower()=='true' else False
                else:
                    vv = v
                config[k] = vv
            elif current == 'libraries':
                parts = k.split('.')
                lib = {
                    'platform': parts[0] if len(parts) > 0 else 'unknown',
                    'build': parts[1] if len(parts) > 1 else 'unknown',
                    'arch': parts[2] if len(parts) > 2 else 'unknown',
                    'resource': v
                }
                libraries.append(lib)
    return {"configuration": config, "libraries": libraries}
