from __future__ import annotations
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel

Kind = Literal["class", "method", "enum", "signal", "typedef", "macro", "file", "manifest", "manifest_item"]

class SearchHit(BaseModel):
    kind: Kind
    name: str
    path: Optional[str] = None
    signature: Optional[str] = None
    score: Optional[float] = None

class Symbol(BaseModel):
    kind: Literal["class", "method", "enum", "signal", "typedef", "macro", "manifest", "manifest_item"]
    name: str
    fq_name: Optional[str] = None
    signature: Optional[str] = None
    header: Optional[str] = None
    impl: Optional[str] = None
    includes: Optional[List[str]] = None
    inherits: Optional[str] = None
    macros: Optional[List[str]] = None
    references: Optional[List[str]] = None
    line_span: Optional[Dict[str, int]] = None

class FileSlice(BaseModel):
    path: str
    start: int
    end: int
    text: str

class ExtensionAPIItem(BaseModel):
    class_: Optional[str] = None
    kind: Literal["class", "method", "signal", "property", "enum"]
    name: str
    signature: Optional[str] = None
    since: Optional[str] = None
    deprecated: Optional[bool] = None
    doc: Optional[str] = None

class GDExtensionManifestLibItem(BaseModel):
    platform: str
    build: str
    arch: str
    resource: str

class GDExtensionManifest(BaseModel):
    path: str
    configuration: Dict[str, Any]
    libraries: List[GDExtensionManifestLibItem]
