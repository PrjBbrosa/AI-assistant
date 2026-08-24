"""Shared report provenance metadata for TXT/PDF exports.

EXPORT-S02: every exported report should record software version,
timezone-aware generation time, module id, optional model level, and a
stable sha256 of the canonical JSON payload.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_CANDIDATES = ("ai-assistant", "codex-ai-assistant", "local-engineering-assistant")
_BUILD_INFO_NAME = "build-info.json"


@dataclass(frozen=True)
class ReportTrace:
    software_version: str
    generated_at: str
    module_id: str
    input_hash: str
    model_level: str | None = None


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, (set, tuple)):
        return list(value)
    return str(value)


def canonical_payload_json(payload: Any) -> str:
    """Return a key-sorted, compact JSON string for hashing."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )


def payload_sha256(payload: Any) -> str:
    digest = hashlib.sha256(canonical_payload_json(payload).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _package_version() -> str | None:
    try:
        from app import __version__
    except Exception:
        __version__ = None
    if __version__:
        return str(__version__)
    for name in _PACKAGE_CANDIDATES:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return None


def _build_info_paths() -> tuple[Path, ...]:
    """Return release metadata locations in trust/order preference.

    PyInstaller exposes bundled data under ``_MEIPASS``. The sidecar next to
    the executable is retained for operators and as a fallback for builds that
    do not bundle the file.
    """
    paths: list[Path] = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        paths.append(Path(bundle_root) / _BUILD_INFO_NAME)
    if getattr(sys, "frozen", False):
        paths.append(Path(sys.executable).resolve().parent / _BUILD_INFO_NAME)
    return tuple(dict.fromkeys(paths))


def _load_build_info() -> dict[str, Any] | None:
    for path in _build_info_paths():
        try:
            raw = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict) and _valid_build_info(raw):
            return raw
    return None


def _valid_build_info(info: dict[str, Any]) -> bool:
    """Accept only the release metadata schema emitted by build_exe.ps1."""
    if info.get("schema_version") != 1:
        return False
    for key in ("version", "build_id", "built_at", "build_mode"):
        if not isinstance(info.get(key), str) or not info[key].strip():
            return False
    if info["build_mode"] not in ("onedir", "onefile"):
        return False
    if not isinstance(info.get("git_dirty"), bool):
        return False
    git_commit = info.get("git_commit", "")
    return isinstance(git_commit, str)


def _format_build_info(info: dict[str, Any]) -> str:
    version = str(info["version"]).strip()
    parts = [version]
    git_commit = str(info.get("git_commit", "")).strip()
    if git_commit:
        dirty_suffix = "-dirty" if info.get("git_dirty") is True else ""
        parts.append(f"git:{git_commit}{dirty_suffix}")
    build_id = str(info.get("build_id", "")).strip()
    if build_id:
        parts.append(f"build:{build_id}")
    return " | ".join(parts)


def _git_text(*arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=_REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _git_version() -> str | None:
    git_hash = _git_text("rev-parse", "--short", "HEAD")
    if not git_hash:
        return None
    dirty = bool(_git_text("status", "--porcelain"))
    return f"git:{git_hash}{'-dirty' if dirty else ''}"


def software_version() -> str:
    build_info = _load_build_info()
    if build_info:
        return _format_build_info(build_info)
    # A frozen artifact must carry build-info.json. Falling back to the
    # source-tree package marker would make a broken release look traceable as
    # "0+source". Keep the failure explicit so CI and exported reports expose
    # the packaging defect.
    if getattr(sys, "frozen", False):
        return "unknown-packaged-build"
    git_version = _git_version()
    if git_version:
        return git_version
    packaged = _package_version()
    if packaged:
        return packaged
    return "unknown"


def format_generated_at(moment: datetime | None = None) -> str:
    aware = (moment or datetime.now()).astimezone()
    return aware.strftime("%Y-%m-%d %H:%M:%S %z")


def build_report_trace(
    module_id: str,
    payload: Any,
    *,
    model_level: str | None = None,
    generated_at: datetime | None = None,
) -> ReportTrace:
    return ReportTrace(
        software_version=software_version(),
        generated_at=format_generated_at(generated_at),
        module_id=module_id,
        input_hash=payload_sha256(payload),
        model_level=model_level or None,
    )


def trace_report_lines(trace: ReportTrace) -> list[str]:
    lines = [
        f"软件版本: {trace.software_version}",
        f"生成时间: {trace.generated_at}",
        f"模块: {trace.module_id}",
    ]
    if trace.model_level:
        lines.append(f"模型等级: {trace.model_level}")
    lines.append(f"输入摘要哈希: {trace.input_hash}")
    return lines


def trace_kv_rows(trace: ReportTrace) -> list[tuple[str, str]]:
    rows = [
        ("软件版本", trace.software_version),
        ("生成时间", trace.generated_at),
        ("模块", trace.module_id),
    ]
    if trace.model_level:
        rows.append(("模型等级", trace.model_level))
    rows.append(("输入摘要哈希", trace.input_hash))
    return rows
