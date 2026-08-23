"""Shared report export helpers for engineering module pages."""

from __future__ import annotations

import os
import uuid
import zipfile
from collections.abc import Callable, Sequence
from pathlib import Path
from xml.sax.saxutils import escape

from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument
from PySide6.QtWidgets import QFileDialog, QWidget

from app.ui.fonts import make_ui_font


EXPORT_FILTER = "PDF Files (*.pdf);;Word Files (*.docx);;Text Files (*.txt);;All Files (*)"


class ReportExportError(RuntimeError):
    """Raised when a report cannot be written safely."""


def _wrap_export_error(exc: OSError) -> ReportExportError:
    return ReportExportError(f"导出失败：目标文件可能被其他程序占用或无写入权限。{exc}")


def _remove_if_exists(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _assert_complete_report(path: Path, suffix: str) -> None:
    if not path.exists() or path.stat().st_size <= 0:
        raise ReportExportError("导出失败：目标文件可能被其他程序占用或无写入权限。")
    if suffix == ".pdf":
        with path.open("rb") as handle:
            magic = handle.read(4)
        if magic != b"%PDF":
            raise ReportExportError("导出失败：生成的 PDF 文件无效。")
    elif suffix == ".docx":
        if not zipfile.is_zipfile(path):
            raise ReportExportError("导出失败：生成的 Word 文件无效。")
        with zipfile.ZipFile(path, "r") as archive:
            archive.namelist()


def write_report_atomically(out_path: Path, writer: Callable[[Path], None]) -> None:
    """Write via a same-directory temp file, then os.replace onto out_path.

    ``writer`` must write a closed, complete file at the given temp path.
    The destination is not touched until that file exists, is non-empty, and
    passes format checks. On failure the temp file is deleted and any existing
    destination is left intact.
    """
    out_path = Path(out_path)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise _wrap_export_error(exc) from exc

    tmp_path = out_path.with_name(out_path.name + ".tmp" + uuid.uuid4().hex)
    try:
        writer(tmp_path)
        _assert_complete_report(tmp_path, out_path.suffix.lower())
        os.replace(tmp_path, out_path)
    except ReportExportError:
        _remove_if_exists(tmp_path)
        raise
    except OSError as exc:
        _remove_if_exists(tmp_path)
        raise _wrap_export_error(exc) from exc
    except Exception:
        _remove_if_exists(tmp_path)
        raise


def write_text_report(out_path: Path, text: str) -> None:
    """Atomically write a UTF-8 text report."""

    def _write(tmp_path: Path) -> None:
        tmp_path.write_text(text, encoding="utf-8")

    write_report_atomically(out_path, _write)


def export_report_lines(
    parent: QWidget,
    dialog_title: str,
    default_path: Path,
    lines: Sequence[str],
) -> Path | None:
    """Export plain report lines as PDF/DOCX/TXT according to selected suffix."""
    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        dialog_title,
        str(default_path),
        EXPORT_FILTER,
    )
    if not file_path:
        return None

    out_path = Path(file_path)
    suffix = out_path.suffix.lower()
    if suffix == ".pdf":
        _export_pdf(out_path, lines)
    elif suffix == ".docx":
        _export_docx(out_path, lines)
    else:
        write_text_report(out_path, "\n".join(lines))
    return out_path


def _export_pdf(out_path: Path, lines: Sequence[str]) -> None:
    def _write(tmp_path: Path) -> None:
        writer = QPdfWriter(str(tmp_path))
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        document = QTextDocument()
        document.setDefaultFont(make_ui_font(10))
        document.setPlainText("\n".join(lines))
        document.print_(writer)
        del writer

    write_report_atomically(out_path, _write)


def _export_docx(out_path: Path, lines: Sequence[str]) -> None:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
        'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        'xmlns:o="urn:schemas-microsoft-com:office:office" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:w10="urn:schemas-microsoft-com:office:word" '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
        'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" '
        'xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" '
        'xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" '
        'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
        'mc:Ignorable="w14 wp14"><w:body>'
    )
    for line in lines:
        safe = escape(line)
        if safe:
            document_xml += f"<w:p><w:r><w:t>{safe}</w:t></w:r></w:p>"
        else:
            document_xml += "<w:p/>"
    document_xml += (
        "<w:sectPr><w:pgSz w:w=\"11906\" w:h=\"16838\"/>"
        "<w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" "
        "w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/></w:sectPr></w:body></w:document>"
    )

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""
    package_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    document_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>
"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
  </w:style>
</w:styles>
"""

    def _write(tmp_path: Path) -> None:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as docx:
            docx.writestr("[Content_Types].xml", content_types)
            docx.writestr("_rels/.rels", package_rels)
            docx.writestr("word/_rels/document.xml.rels", document_rels)
            docx.writestr("word/styles.xml", styles_xml)
            docx.writestr("word/document.xml", document_xml)

    write_report_atomically(out_path, _write)
