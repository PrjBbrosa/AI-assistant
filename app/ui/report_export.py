"""Shared report export helpers for engineering module pages."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Sequence
from xml.sax.saxutils import escape

from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument
from PySide6.QtWidgets import QFileDialog, QWidget

from app.ui.fonts import make_ui_font


EXPORT_FILTER = "PDF Files (*.pdf);;Word Files (*.docx);;Text Files (*.txt);;All Files (*)"


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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = out_path.suffix.lower()
    if suffix == ".pdf":
        _export_pdf(out_path, lines)
    elif suffix == ".docx":
        _export_docx(out_path, lines)
    else:
        out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _export_pdf(out_path: Path, lines: Sequence[str]) -> None:
    writer = QPdfWriter(str(out_path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    document = QTextDocument()
    document.setDefaultFont(make_ui_font(10))
    document.setPlainText("\n".join(lines))
    document.print_(writer)


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

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", package_rels)
        docx.writestr("word/_rels/document.xml.rels", document_rels)
        docx.writestr("word/styles.xml", styles_xml)
        docx.writestr("word/document.xml", document_xml)
