"""Markdown 帮助内容的索引与加载。"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class HelpEntry:
    title: str
    body_md: str
    category: Optional[str] = None
    source: Optional[str] = None


def _default_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "docs" / "help"
    return Path(__file__).resolve().parents[2] / "docs" / "help"


# 用于 category 推断的两级映射
_MODULE_CATEGORY: Dict[str, str] = {
    "bolt_vdi": "螺栓 · 章节",
    "bolt_tapped_axial": "螺纹连接 · 章节",
    "hertz": "赫兹 · 章节",
    "interference": "过盈 · 章节",
    "spline": "花键 · 章节",
    "worm": "蜗轮 · 章节",
}

_TERM_PREFIX_CATEGORY: Dict[str, str] = {
    "bolt_": "螺栓 · 术语",
    "interference_": "过盈 · 术语",
    "hertz_": "赫兹 · 术语",
    "spline_": "花键 · 术语",
    "worm_": "蜗轮 · 术语",
}


def infer_category(ref: str) -> Optional[str]:
    """按 ref 路径推断所属模块/类别。"""
    parts = ref.split("/")
    if len(parts) >= 2 and parts[0] == "modules":
        return _MODULE_CATEGORY.get(parts[1])
    if len(parts) == 2 and parts[0] == "terms":
        name = parts[1]
        for prefix, cat in _TERM_PREFIX_CATEGORY.items():
            if name.startswith(prefix):
                return cat
        return "通用 · 术语"
    return None


# 匹配 "**出处**：...", "出处：...", "**Source**: ...", "Source: ..."
_SOURCE_RE = re.compile(
    r"^\s*(?:\*\*)?(?:出处|Source)(?:\*\*)?\s*[:：]\s*(.+?)\s*$"
)


def _extract_source(lines: list[str]) -> tuple[list[str], Optional[str]]:
    """从 body 末尾剥离出处行；返回 (剩余行, 出处文本或 None)。"""
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if not stripped:
            continue
        m = _SOURCE_RE.match(stripped)
        if m:
            return lines[:i], m.group(1).strip()
        break
    return lines, None


def _parse(md_text: str, ref: str) -> HelpEntry:
    lines = md_text.splitlines()
    title = ""
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body_start = i + 1
            break
    body_lines = lines[body_start:]
    body_lines, source = _extract_source(body_lines)
    body = "\n".join(body_lines).strip()
    if not title:
        title = f"(无标题) {ref}"
    return HelpEntry(
        title=title,
        body_md=body,
        category=infer_category(ref),
        source=source,
    )


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
                category=infer_category(ref),
                source=None,
            )
        else:
            text = path.read_text(encoding="utf-8")
            entry = _parse(text, ref)
        self._cache[ref] = entry
        return entry
