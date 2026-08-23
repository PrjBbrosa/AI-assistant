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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKAGE_CANDIDATES = ("ai-assistant", "codex-ai-assistant", "local-engineering-assistant")


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


def _git_short_hash() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
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


def software_version() -> str:
    packaged = _package_version()
    if packaged:
        return packaged
    git_hash = _git_short_hash()
    if git_hash:
        return f"git:{git_hash}"
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
