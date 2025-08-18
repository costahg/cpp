#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extapi_core.py — Núcleo simples para ler e consultar o extension_api.json (Godot 4.4)

v0.3.1 — robustez do roteador para Builtin (case-insensitive) e pequenos ajustes
- route("builtin Color") e route("builtin color") agora funcionam igualmente.
- Detecção de nome em "layout de X" tenta casar com nomes conhecidos de builtins.
- Mantém cobertura ampla de builtin_classes (membros, construtores, operadores, métodos, constantes) e layout.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import json
from pathlib import Path
import re


# -------------------------
# Estruturas de dados leves
# -------------------------

@dataclass
class Indexes:
    version: str
    classes_by_name: Dict[str, Dict[str, Any]]
    methods_by_name: Dict[str, List[Tuple[str, Dict[str, Any]]]]  # nome_do_metodo -> [(classe, metodo_dict)]
    methods_by_hash: Dict[str, List[Tuple[str, Dict[str, Any]]]]  # hash -> [(classe, metodo_dict)]
    global_enums_by_name: Dict[str, Dict[str, Any]]               # "Corner" -> enum_dict
    class_enums_qualname: Dict[str, Dict[str, Any]]               # "Control.Layout" -> enum_dict
    singletons_by_name: Dict[str, str]                             # "Engine" -> "Engine"
    builtin_sizes: Dict[str, Dict[str, int]]                       # config -> {BuiltinName: size}
    builtin_offsets: Dict[str, Dict[str, List[Dict[str, Any]]]]    # config -> {BuiltinName: [ {member, offset, meta}, ... ]}
    utility_by_name: Dict[str, Dict[str, Any]]                     # "rand_from_seed" -> ufunc_dict
    utility_by_cat: Dict[str, List[str]]                           # "Math" -> ["sin", "cos", ...]
    native_structs_by_name: Dict[str, Dict[str, Any]]              # "PlaceHolder" -> {...}
    builtin_classes_by_name: Dict[str, Dict[str, Any]]             # "Color" -> {...}
    global_constants_by_name: Dict[str, Dict[str, Any]]            # "OK" -> {...}


class ExtApi:
    def __init__(self, json_path: str | Path):
        self.path = Path(json_path)
        self.api = self._load_api(self.path)
        self.ix = self._build_indexes(self.api)

    # ------------
    # Carregamento
    # ------------
    @staticmethod
    def _load_api(path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    # -----------------------
    # Construção dos índices
    # -----------------------
    @staticmethod
    def _build_indexes(api: Dict[str, Any]) -> Indexes:
        header = api.get("header") or {}
        version = (
            header.get("version_full_name")
            or (api.get("version") or {}).get("string")
            or (api.get("version") or {}).get("full_name")
            or "unknown"
        )

        # Classes (com métodos/props/sinais/enums dentro)
        classes_by_name: Dict[str, Dict[str, Any]] = {}
        methods_by_name: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        methods_by_hash: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        class_enums_qualname: Dict[str, Dict[str, Any]] = {}

        for c in api.get("classes", []) or []:
            name = c.get("name")
            if not name:
                continue
            classes_by_name[name] = c
            # Métodos
            for m in c.get("methods", []) or []:
                mn = m.get("name")
                if not mn:
                    continue
                methods_by_name.setdefault(mn, []).append((name, m))
                # hash principal
                hv_main = m.get("hash")
                if hv_main is not None:
                    methods_by_hash.setdefault(str(hv_main), []).append((name, m))
                # hash_compatibility pode ser lista
                hv_compat = m.get("hash_compatibility")
                if isinstance(hv_compat, list):
                    for hcv in hv_compat:
                        methods_by_hash.setdefault(str(hcv), []).append((name, m))
                elif hv_compat is not None:
                    methods_by_hash.setdefault(str(hv_compat), []).append((name, m))
            # Enums da classe (qualificados: Classe.Enum)
            for e in c.get("enums", []) or []:
                en = e.get("name")
                if en:
                    class_enums_qualname[f"{name}.{en}"] = e

        # Enums globais
        global_enums_by_name: Dict[str, Dict[str, Any]] = {}
        for e in api.get("global_enums", []) or []:
            en = e.get("name")
            if en:
                global_enums_by_name[en] = e

        # Singletons
        singletons_by_name: Dict[str, str] = {}
        for s in api.get("singletons", []) or []:
            nm = s.get("name")
            tp = s.get("type")
            if nm and tp:
                singletons_by_name[nm] = tp

        # Utility
        utility_by_name: Dict[str, Dict[str, Any]] = {}
        utility_by_cat: Dict[str, List[str]] = {}
        for u in api.get("utility_functions", []) or []:
            nm = u.get("name")
            if nm:
                utility_by_name[nm] = u
                cat = u.get("category") or ""
                utility_by_cat.setdefault(cat, []).append(nm)

        # Builtins: tamanhos e offsets por configuração
        builtin_sizes: Dict[str, Dict[str, int]] = {}
        for conf in api.get("builtin_class_sizes", []) or []:
            conf_name = conf.get("build_configuration")
            sizes_map: Dict[str, int] = {}
            for item in conf.get("sizes", []) or []:
                bname = item.get("name")
                size = item.get("size")
                if bname is not None and size is not None:
                    sizes_map[bname] = size
            if conf_name:
                builtin_sizes[conf_name] = sizes_map

        builtin_offsets: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for conf in api.get("builtin_class_member_offsets", []) or []:
            conf_name = conf.get("build_configuration")
            cmap: Dict[str, List[Dict[str, Any]]] = {}
            for c in conf.get("classes", []) or []:
                bname = c.get("name")
                members = c.get("members", []) or []
                if bname:
                    cmap[bname] = members
            if conf_name:
                builtin_offsets[conf_name] = cmap

        # Native structures
        native_structs_by_name: Dict[str, Dict[str, Any]] = {}
        for n in api.get("native_structures", []) or []:
            nn = n.get("name")
            if nn:
                native_structs_by_name[nn] = n

        # Builtin classes (detalhes) e constantes globais
        builtin_classes_by_name: Dict[str, Dict[str, Any]] = {}
        for b in api.get("builtin_classes", []) or []:
            bn = b.get("name")
            if bn:
                builtin_classes_by_name[bn] = b

        global_constants_by_name: Dict[str, Dict[str, Any]] = {}
        for gc in api.get("global_constants", []) or []:
            nm = gc.get("name")
            if nm:
                global_constants_by_name[nm] = gc

        return Indexes(
            version=version,
            classes_by_name=classes_by_name,
            methods_by_name=methods_by_name,
            methods_by_hash=methods_by_hash,
            global_enums_by_name=global_enums_by_name,
            class_enums_qualname=class_enums_qualname,
            singletons_by_name=singletons_by_name,
            builtin_sizes=builtin_sizes,
            builtin_offsets=builtin_offsets,
            utility_by_name=utility_by_name,
            utility_by_cat=utility_by_cat,
            native_structs_by_name=native_structs_by_name,
            builtin_classes_by_name=builtin_classes_by_name,
            global_constants_by_name=global_constants_by_name,
        )

    # ------------------
    # Funções de consulta
    # ------------------
    def info(self) -> Dict[str, Any]:
        return {
            "version": self.ix.version,
            "classes": len(self.ix.classes_by_name),
            "methods": sum(len(v) for v in self.ix.methods_by_name.values()),
            "global_enums": len(self.ix.global_enums_by_name),
            "singletons": len(self.ix.singletons_by_name),
            "builtin_classes": len(self.ix.builtin_classes_by_name),
            "native_structures": len(self.ix.native_structs_by_name),
        }

    def get_class(self, name: str) -> Optional[Dict[str, Any]]:
        c = self.ix.classes_by_name.get(name)
        if c:
            return c
        for k in self.ix.classes_by_name.keys():
            if k.lower() == name.lower():
                return self.ix.classes_by_name[k]
        return None

    def list_class_items(self, name: str) -> Optional[Dict[str, Any]]:
        c = self.get_class(name)
        if not c:
            return None
        return {
            "name": c.get("name"),
            "api_type": c.get("api_type"),
            "inherits": c.get("inherits"),
            "is_instantiable": c.get("is_instantiable"),
            "is_refcounted": c.get("is_refcounted"),
            "methods": [self._fmt_method_sig(m, c.get("name")) for m in c.get("methods", []) or []],
            "properties": [self._fmt_property(p) for p in c.get("properties", []) or []],
            "signals": [self._fmt_signal(s) for s in c.get("signals", []) or []],
            "constants": [
                {"name": k.get("name"), "value": k.get("value")} for k in c.get("constants", []) or []
            ],
            "enums": [
                {
                    "name": e.get("name"),
                    "values": [v.get("name") for v in e.get("values", []) or []],
                } for e in c.get("enums", []) or []
            ],
        }

    def find_methods(self, name: str, cls: Optional[str] = None) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for cname, m in self.ix.methods_by_name.get(name, []) or []:
            if cls and cname.lower() != cls.lower():
                continue
            out.append(self._sig_dict(cname, m))
        return out

    def find_method_by_hash(self, h: str | int) -> List[Dict[str, Any]]:
        hs = str(h)
        return [self._sig_dict(cname, m) for cname, m in self.ix.methods_by_hash.get(hs, []) or []]

    def get_global_enum(self, name: str) -> Optional[Dict[str, Any]]:
        e = self.ix.global_enums_by_name.get(name)
        if e:
            return {"name": name, "values": [v.get("name") for v in e.get("values", []) or []]}
        for k, e in self.ix.global_enums_by_name.items():
            if k.lower() == name.lower():
                return {"name": k, "values": [v.get("name") for v in e.get("values", []) or []]}
        return None

    def get_class_enum(self, qualified: str) -> Optional[Dict[str, Any]]:
        e = self.ix.class_enums_qualname.get(qualified)
        if e:
            return {"name": qualified, "values": [v.get("name") for v in e.get("values", []) or []]}
        parts = qualified.split(".")
        if len(parts) == 2:
            cpart, enpart = parts
            cname_real = None
            for k in self.ix.classes_by_name.keys():
                if k.lower() == cpart.lower():
                    cname_real = k
                    break
            if cname_real:
                key = f"{cname_real}.{enpart}"
                e = self.ix.class_enums_qualname.get(key)
                if e:
                    return {"name": key, "values": [v.get("name") for v in e.get("values", []) or []]}
        return None

    def list_singletons(self) -> Dict[str, str]:
        return dict(self.ix.singletons_by_name)

    # ---------
    # Utility
    # ---------
    def find_utility(self, name: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        if name:
            u = self.ix.utility_by_name.get(name)
            if u:
                return {"name": name, "category": u.get("category"), "return_type": (u.get("return_type")), "args": [a.get("type") for a in u.get("arguments", []) or []]}
            # tenta insensitive
            for k, u in self.ix.utility_by_name.items():
                if k.lower() == name.lower():
                    return {"name": k, "category": u.get("category"), "return_type": (u.get("return_type")), "args": [a.get("type") for a in u.get("arguments", []) or []]}
            return {}
        if category is not None:
            return {"category": category, "functions": self.ix.utility_by_cat.get(category, [])}
        return {"functions": sorted(list(self.ix.utility_by_name.keys()))}

    # -------
    # Builtins
    # -------
    def list_builtin_names(self) -> List[str]:
        return sorted(list(self.ix.builtin_classes_by_name.keys()))

    def get_builtin(self, name: str) -> Optional[Dict[str, Any]]:
        b = self._resolve_builtin_name(name)
        if not b:
            return None
        out: Dict[str, Any] = {
            "name": b.get("name"),
            "is_keyed": b.get("is_keyed"),
            "has_destructor": b.get("has_destructor"),
        }
        if "indexing_return_type" in b:
            out["indexing_return_type"] = b.get("indexing_return_type")
        if b.get("members"):
            out["members"] = [
                {"name": m.get("name"), "type": (m.get("type") if not isinstance(m.get("type"), dict) else m.get("type", {}).get("type"))}
                for m in b.get("members", []) if isinstance(m, dict)
            ]
        if b.get("constants"):
            out["constants"] = [{"name": c.get("name"), "value": c.get("value")} for c in b.get("constants", [])]
        if b.get("constructors"):
            out["constructors"] = [
                {
                    "index": c.get("index"),
                    "args": [a.get("type") for a in c.get("arguments", []) or []]
                } for c in b.get("constructors", [])
            ]
        if b.get("operators"):
            out["operators"] = [
                {
                    "name": op.get("name"),
                    "right_type": op.get("right_type"),
                    "return_type": op.get("return_type"),
                } for op in b.get("operators", [])
            ]
        if b.get("methods"):
            out["methods"] = [
                {
                    "name": m.get("name"),
                    "return_type": m.get("return_type"),
                    "is_vararg": m.get("is_vararg", False),
                    "args": [a.get("type") for a in m.get("arguments", []) or []]
                } for m in b.get("methods", [])
            ]
        return out

    def get_builtin_layout(self, name: str, config: str = "float_32") -> Optional[Dict[str, Any]]:
        bn = self._resolve_builtin_key(name)
        size = (self.ix.builtin_sizes.get(config, {}) or {}).get(bn)
        members = (self.ix.builtin_offsets.get(config, {}) or {}).get(bn)
        if size is None and not members:
            return None
        return {"class": bn, "config": config, "size": size, "members": members or []}

    def get_builtin_member_offset(self, name: str, member: str, config: str = "float_32") -> Optional[int]:
        layout = self.get_builtin_layout(name, config)
        if not layout:
            return None
        for it in layout.get("members", []) or []:
            if it.get("member") == member:
                return it.get("offset")
        return None

    def _resolve_builtin_name(self, name: str) -> Optional[Dict[str, Any]]:
        b = self.ix.builtin_classes_by_name.get(name)
        if b:
            return b
        for k, v in self.ix.builtin_classes_by_name.items():
            if k.lower() == name.lower():
                return v
        return None

    def _resolve_builtin_key(self, name: str) -> Optional[str]:
        if name in self.ix.builtin_classes_by_name:
            return name
        for k in self.ix.builtin_classes_by_name.keys():
            if k.lower() == name.lower():
                return k
        return None

    # -------------------
    # Constantes globais
    # -------------------
    def get_global_constant(self, name: str) -> Optional[Dict[str, Any]]:
        gc = self.ix.global_constants_by_name.get(name)
        if gc:
            return gc
        for k, v in self.ix.global_constants_by_name.items():
            if k.lower() == name.lower():
                return v
        return None

    def list_global_constants(self) -> List[str]:
        return sorted(list(self.ix.global_constants_by_name.keys()))

    # ----------
    # Roteamento
    # ----------
    def _extract_known(self, q: str, names: List[str]) -> Optional[str]:
        """Tenta achar um nome conhecido (case-insensitive) presente na frase inteira."""
        for nm in sorted(names, key=len, reverse=True):  # nomes mais longos primeiro
            if re.search(rf"\b{re.escape(nm)}\b", q, flags=re.IGNORECASE):
                return nm
        return None

    
    def route(self, q: str) -> Dict[str, Any]:
        ql = q.lower()
        # 1) Builtin layout/offset/size FIRST (para não confundir "Color.a" com enum de classe)
        if ("layout" in ql or "tamanho" in ql or "size" in ql or "offset" in ql):
            bn = self._extract_known(q, list(self.ix.builtin_classes_by_name.keys()))
            if bn:
                if "offset" in ql and "." in q:
                    m3 = re.search(r"\b([A-Za-z][A-Za-z0-9_]*)\s*\.\s*([a-zA-Z_]\w*)\b", q)
                    if m3:
                        cls = self._extract_known(m3.group(1), list(self.ix.builtin_classes_by_name.keys())) or m3.group(1)
                        member = m3.group(2)
                        off = self.get_builtin_member_offset(cls, member)
                        if off is not None:
                            return {"action": "builtin_member_offset", "params": {"config": "float_32", "class": cls, "member": member}, "result": {"offset": off}}
                lay = self.get_builtin_layout(bn)
                if lay:
                    return {"action": "builtin_layout", "params": {"class": bn, "config": lay["config"]}, "result": lay}

        # 2) hash de método
        m = re.search(r"hash\s*[:=]?\s*(\d+)", ql)
        if m:
            h = m.group(1)
            return {"action": "method_by_hash", "params": {"hash": h}, "result": self.find_method_by_hash(h)}

        # 3) Detalhes de builtin (métodos/operadores/constructors/members)
        if "builtin" in ql:
            m4 = re.search(r"\bbuiltin\s+([A-Za-z][A-Za-z0-9_]*)\b", q, flags=re.IGNORECASE)
            if not m4:
                m4 = re.search(r"\b([A-Za-z][A-Za-z0-9_]*)\s+builtin\b", q, flags=re.IGNORECASE)
            nm = None
            if m4:
                nm = m4.group(1)
            else:
                nm = self._extract_known(q, list(self.ix.builtin_classes_by_name.keys()))
            if nm:
                data = self.get_builtin(nm)
                return {"action": "builtin", "params": {"class": nm}, "result": data}

        # 4) Classe.Enum (depois de tratar builtin Color.a)
        m2 = re.search(r"\b([A-Za-z][A-Za-z0-9_]*)\.([A-Za-z][A-Za-z0-9_]*)\b", q)
        if m2:
            qual = f"{m2.group(1)}.{m2.group(2)}"
            return {"action": "class_enum", "params": {"qualified": qual}, "result": self.get_class_enum(qual)}


        # 5) classe
        if "classe" in ql or "class" in ql:
            # tenta capturar explicitamente o nome após 'classe'/'class'
            m5 = re.search(r"\b(?:classe|class)\s+([A-Za-z][A-Za-z0-9_]*)\b", q, flags=re.IGNORECASE)
            cname = None
            if m5:
                cname = m5.group(1)
            else:
                # fallback: procurar um nome de classe conhecido na frase inteira (case-insensitive)
                cname = self._extract_known(q, list(self.ix.classes_by_name.keys()))
            if cname:
                return {"action": "class", "params": {"name": cname}, "result": self.list_class_items(cname)}
    

        # 6) método
        if "método" in ql or "metodo" in ql or "method" in ql:
            m6 = re.search(r"\b([A-Za-z_]\w*)\b", q)
            if m6:
                nm = m6.group(1)
                return {"action": "method_by_name", "params": {"name": nm}, "result": self.find_methods(nm)}

        return {
            "action": "help",
            "hints": [
                "Exemplos:",
                "builtin Color",
                "layout de Color",
                "offset de Color.a",
                "tamanho de Vector3",
                "classe Node",
                "método add_child",
                "Node.ProcessMode",
            ],
        }

    # -------------------
    # Utilitários de formatação
    # -------------------
    @staticmethod
    def _fmt_type(t: Optional[str | Dict[str, Any]]) -> str:
        if not t:
            return "void"
        if isinstance(t, dict):
            t = t.get("type") or "void"
        if t.startswith("typedarray::"):
            return f"Array<{t.split('::', 1)[1]}>"
        if t.startswith("enum::"):
            return t.split("::", 1)[1]
        return t

    def _fmt_method_sig(self, m: Dict[str, Any], cls: Optional[str] = None) -> str:
        ret = self._fmt_type((m.get("return_value") or {}).get("type"))
        args = ", ".join(self._fmt_arg(a) for a in m.get("arguments", []) or [])
        name = m.get("name", "<unnamed>")
        qual = f"{cls}::{name}" if cls else name
        flags = []
        if m.get("is_static"): flags.append("static")
        if m.get("is_const"): flags.append("const")
        if m.get("is_virtual"): flags.append("virtual")
        if m.get("is_vararg"): flags.append("vararg")
        flags_s = (" [" + ", ".join(flags) + "]") if flags else ""
        return f"{ret} {qual}({args}){flags_s}"

    def _fmt_arg(self, arg: Dict[str, Any]) -> str:
        t = self._fmt_type(arg.get("type"))
        name = arg.get("name", "")
        dv = arg.get("default_value")
        if dv is not None:
            return f"{t} {name}={dv}"
        return f"{t} {name}" if name else t

    def _fmt_property(self, p: Dict[str, Any]) -> str:
        t = self._fmt_type(p.get("type"))
        name = p.get("name", "<unnamed>")
        getter = p.get("getter")
        setter = p.get("setter")
        idx = p.get("index")
        extra = []
        if getter: extra.append(f"get={getter}")
        if setter: extra.append(f"set={setter}")
        if idx is not None: extra.append(f"index={idx}")
        return f"{t} {name}" + (" [" + ", ".join(extra) + "]" if extra else "")

    @staticmethod
    def _fmt_signal(s: Dict[str, Any]) -> str:
        name = s.get("name", "<unnamed>")
        args = s.get("arguments", []) or []
        def _atype(a):
            t = a.get('type')
            if isinstance(t, dict):
                t = t.get('type')
            return t or 'void'
        args_s = ", ".join(f"{_atype(a)} {a.get('name','')}".strip() for a in args)
        return f"signal {name}({args_s})"

    @staticmethod
    def _sig_dict(cls: str, m: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "class": cls,
            "name": m.get("name"),
            "ret": (m.get("return_value") or {}).get("type"),
            "args": [a.get("type") for a in m.get("arguments", []) or []],
            "hash": m.get("hash"),
            "hash_compatibility": m.get("hash_compatibility"),
            "is_static": m.get("is_static") or False,
            "is_const": m.get("is_const") or False,
            "is_virtual": m.get("is_virtual") or False,
            "is_vararg": m.get("is_vararg") or False,
        }