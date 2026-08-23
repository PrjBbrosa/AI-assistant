"""Independent reference checks against documented example/comment values.

Expected numbers come from repo comments and examples, not from re-running a
calculator and asserting its own PASS/FAIL. Hertz/spline published catalog
numbers are not recorded independently in this repo, so they are not invented
here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.bolt._common import derive_thread_section
from core.bolt.grades import BOLT_GRADE_TABLE
from core.bolt.tapped_axial_joint import _ASV_TABLE_ROLLED, _fatigue_limit_asv

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
TAPPED_CASE_01 = EXAMPLES_DIR / "tapped_axial_joint_case_01.json"


def _tapped_case_01() -> dict:
    return json.loads(TAPPED_CASE_01.read_text(encoding="utf-8"))


def test_m8x125_thread_section_matches_iso724_example_comment() -> None:
    """derive_thread_section vs ISO 724 / example comment values.

    Source, examples/tapped_axial_joint_case_01.json _comment:
        "M8 x 1.25, grade 8.8 — light-duty tapped steel-to-steel joint.
         Values from ISO 898-1 (Rp0.2 min 640 MPa for 8.8, d<=16),
         ISO 724 (thread geometry), ..."

    The same file records the documented M8x1.25 section as
    As=36.6 mm2, d2=7.188 mm, d3=6.466 mm.
    """
    case = _tapped_case_01()
    comment = str(case.get("_comment", ""))
    fastener = case["fastener"]

    assert "ISO 724" in comment
    assert fastener["d"] == 8.0
    assert fastener["p"] == 1.25
    assert fastener["As"] == 36.6
    assert fastener["d2"] == 7.188
    assert fastener["d3"] == 6.466

    derived = derive_thread_section(fastener["d"], fastener["p"])
    # As is commonly tabulated to 1 decimal (36.6 mm2); d2/d3 to 0.001 mm.
    assert derived["As"] == pytest.approx(fastener["As"], abs=0.05)
    assert derived["d2"] == pytest.approx(fastener["d2"], abs=1e-3)
    assert derived["d3"] == pytest.approx(fastener["d3"], abs=1e-3)


def test_grade_88_rp02_matches_iso898_1_example_comment() -> None:
    """BOLT_GRADE_TABLE 8.8 -> 640 matches the ISO 898-1 example comment.

    Source, examples/tapped_axial_joint_case_01.json _comment:
        "Values from ISO 898-1 (Rp0.2 min 640 MPa for 8.8, d<=16), ..."

    grades.py documents the 8.8 preset as 640 MPa (GB/T 3098.1 style, matching
    ISO 898-1 for 8.8 with d<=16).
    """
    case = _tapped_case_01()
    comment = str(case.get("_comment", ""))

    assert "ISO 898-1" in comment
    assert "640" in comment
    assert case["fastener"]["grade"] == "8.8"
    assert case["fastener"]["Rp02"] == 640.0
    assert BOLT_GRADE_TABLE["8.8"] == 640
    assert BOLT_GRADE_TABLE["8.8"] == case["fastener"]["Rp02"]


def test_asv_d8_rolled_matches_vdi_table_a4_example_comment() -> None:
    """VDI 2230-1 Table A4 ASV for d=8 rolled is 47 MPa in comment and table.

    Source, examples/tapped_axial_joint_case_01.json _comment:
        "VDI 2230-1:2015 Table A4 (sigma_ASV=47 MPa at d=8, rolled)"

    _ASV_TABLE_ROLLED in core/bolt/tapped_axial_joint.py is annotated
    "VDI 2230-1:2015, Table A4" and contains (8, 47). Lookup is
    _fatigue_limit_asv, not the overall joint PASS/FAIL.
    """
    case = _tapped_case_01()
    comment = str(case.get("_comment", ""))

    assert "Table A4" in comment
    assert "sigma_ASV=47" in comment
    assert "d=8" in comment
    assert (8, 47) in _ASV_TABLE_ROLLED
    assert _fatigue_limit_asv(8.0, "rolled") == pytest.approx(47.0)
