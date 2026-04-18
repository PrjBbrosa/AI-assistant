"""Markdown 帮助内容的索引与加载。"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class HelpEntry:
    title: str
    body_md: str


def _default_root() -> Path:
    # PyInstaller 兼容：打包后 docs 随 _MEIPASS
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "docs" / "help"
    return Path(__file__).resolve().parents[2] / "docs" / "help"


def _parse(md_text: str, ref: str) -> HelpEntry:
    lines = md_text.splitlines()
    title = ""
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:]).strip()
    if not title:
        title = f"(无标题) {ref}"
    return HelpEntry(title=title, body_md=body)


class HelpProvider:
    """单例：按 ref 懒加载 Markdown 帮助内容。"""

    _instance: Optional["HelpProvider"] = None

    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = root or _default_root()
        self._index: Dict[str, Path] = {}
        self._cache: Dict[str, HelpEntry] = {}
        self._build_index()

    @classmethod
    def instance(cls) -> "HelpProvider":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _build_index(self) -> None:
        if not self._root.exists():
            return
        for md_path in self._root.rglob("*.md"):
            rel = md_path.relative_to(self._root).with_suffix("")
            ref = str(rel).replace("\\", "/")
            # GUIDELINES.md 等顶层文件不纳入 ref 索引
            if "/" not in ref:
                continue
            self._index[ref] = md_path

    def get(self, ref: str) -> HelpEntry:
        if ref in self._cache:
            return self._cache[ref]
        path = self._index.get(ref)
        if path is None:
            entry = HelpEntry(
                title=f"帮助内容缺失：{ref}",
                body_md=f"未找到 ref=`{ref}` 对应的帮助文件。",
            )
        else:
            text = path.read_text(encoding="utf-8")
            entry = _parse(text, ref)
        self._cache[ref] = entry
        return entry
