from pathlib import Path

import pytest


def _sample_payload() -> dict:
    return {
        "fastener": {"d": 10.0, "p": 1.5, "Rp02": 640.0, "grade": "8.8"},
        "assembly": {
            "F_preload_min": 12000.0,
            "alpha_A": 1.6,
            "mu_thread": 0.12,
            "mu_bearing": 0.14,
            "bearing_d_inner": 11.0,
            "bearing_d_outer": 18.0,
            "prevailing_torque": 0.0,
            "thread_flank_angle_deg": 60.0,
            "tightening_method": "torque",
            "utilization": 0.9,
        },
        "service": {"FA_min": 0.0, "FA_max": 2000.0},
        "fatigue": {"load_cycles": 1_000_000.0, "surface_treatment": "rolled"},
        "thread_strip": {"safety_required": 1.5},
        "checks": {"yield_safety_operating": 1.15},
        "options": {"report_mode": "full"},
    }


def _sample_result() -> dict:
    return {
        "overall_pass": True,
        "model_type": "tapped_axial_threaded_joint",
        "scope_note": "仅适用于螺栓拧入螺纹对手件、中间无被夹件、纯轴向拉载荷工况。",
        "derived_geometry": {"As_mm2": 58.0, "d2_mm": 9.026, "d3_mm": 8.160},
        "assembly": {
            "F_preload_min_N": 12000.0,
            "F_preload_max_N": 19200.0,
            "MA_min_Nm": 31.2,
            "MA_max_Nm": 49.9,
            "k_thread_mm": 0.92,
            "k_bearing_mm": 1.68,
            "tightening_method": "torque",
        },
        "forces": {
            "F_service_min_N": 19200.0,
            "F_service_max_N": 21200.0,
            "F_mean_N": 20200.0,
            "F_amplitude_N": 1000.0,
        },
        "stresses_mpa": {
            "sigma_ax_assembly": 331.0,
            "tau_assembly": 114.0,
            "sigma_vm_assembly": 385.0,
            "sigma_ax_service_max": 365.5,
            "sigma_vm_service_max": 391.8,
            "sigma_m_fatigue": 348.2,
            "sigma_a_fatigue": 17.2,
        },
        "fatigue": {
            "sigma_ASV": 46.5,
            "goodman_factor": 0.39,
            "sigma_a_allow": 18.3,
            "load_cycles": 1_000_000.0,
            "surface_treatment": "rolled",
        },
        "thread_strip": {
            "active": False,
            "check_passed": True,
            "A_SB_mm2": 0.0,
            "A_SM_mm2": 0.0,
            "tau_BS_MPa": 0.0,
            "tau_BM_MPa": 0.0,
            "F_strip_bolt_N": 0.0,
            "F_strip_nut_N": 0.0,
            "F_bolt_max_N": 0.0,
            "critical_side": "",
            "strip_safety": 0.0,
            "strip_safety_required": 0.0,
            "note": "未提供 m_eff，未执行螺纹脱扣校核。",
        },
        "checks": {
            "assembly_von_mises_ok": True,
            "service_von_mises_ok": True,
            "fatigue_ok": True,
            "thread_strip_ok": True,
        },
        "trace": {
            "assumptions": [
                "仅适用于无被夹件、纯轴向拉载荷工况。",
                "外轴力全部进入螺栓主链，不建模 phi_n 或残余夹紧力。",
            ],
            "intermediate": {
                "lead_angle_rad": 0.0528,
                "friction_angle_rad": 0.1392,
                "cycle_factor": 1.0,
                "C1": 0.75,
                "C3": 0.58,
                "sigma_allow_assembly": 576.0,
                "sigma_allow_service": 556.5,
            },
        },
        "warnings": [],
        "recommendations": ["所有校核均通过。"],
        "references": {
            "geometry": "ISO metric thread approximation",
            "assembly_strength": "von Mises with assembly torsion",
            "fatigue": "sigma_ASV plus Goodman reduction",
            "thread_strip": "VDI 2230 style shear area comparison with service max force",
        },
    }


def _sample_result_incomplete() -> dict:
    """默认未填 m_eff 的真实 core 输出：overall_status=incomplete、thread_strip_ok=None."""
    from core.bolt.tapped_axial_joint import calculate_tapped_axial_joint

    data = _sample_payload()
    # 降 FA_max 让 assembly/service/fatigue 都过，隔离 thread_strip not_checked
    data["service"]["FA_max"] = 500.0
    result = calculate_tapped_axial_joint(data)
    assert result["overall_status"] == "incomplete"
    assert result["checks"]["thread_strip_ok"] is None
    return result


def test_generate_tapped_axial_pdf_report(tmp_path: Path) -> None:
    pytest.importorskip("reportlab")

    from app.ui.report_pdf_tapped_axial import generate_tapped_axial_report

    out = tmp_path / "tapped_axial_report.pdf"
    generate_tapped_axial_report(out, _sample_payload(), _sample_result())

    assert out.exists()
    assert out.stat().st_size > 1000


def test_pdf_verdict_receives_overall_status_string(tmp_path: Path, monkeypatch) -> None:
    """Codex follow-up 2026-04-16：incomplete 场景导出 PDF 时，_verdict_block 必须
    收到字符串 'incomplete'（否则退化到 bool(overall_pass) 会渲染为红色 FAIL）."""
    pytest.importorskip("reportlab")

    import app.ui.report_pdf_tapped_axial as mod
    from app.ui.report_pdf_common import _verdict_block as original

    captured: dict = {}

    def _spy(styles, overall, subtitle):
        captured["overall"] = overall
        return original(styles, overall, subtitle)

    monkeypatch.setattr(mod, "_verdict_block", _spy)

    data = _sample_payload()
    data["service"]["FA_max"] = 500.0
    from core.bolt.tapped_axial_joint import calculate_tapped_axial_joint
    result = calculate_tapped_axial_joint(data)

    out = tmp_path / "incomplete.pdf"
    mod.generate_tapped_axial_report(out, data, result)

    assert captured["overall"] == "incomplete", (
        f"incomplete 场景应把 'incomplete' 传给 _verdict_block，实际: {captured['overall']}"
    )
    assert out.exists()


def test_pdf_check_pills_render_none_as_unchecked(tmp_path: Path) -> None:
    """Codex follow-up 2026-04-16：checks[key] is None 的 pill 必须渲染为中性"未校核"，
    其背景颜色为 C_MUTED（灰色），而不是 C_FAIL（红色）."""
    pytest.importorskip("reportlab")

    from app.ui.report_pdf_common import (
        C_FAIL,
        C_MUTED,
        C_PASS,
        _build_styles,
        _check_pills,
        _register_fonts,
    )

    _register_fonts()
    styles = _build_styles()
    check_labels = {
        "assembly_von_mises_ok": "装配 von Mises 强度",
        "service_von_mises_ok": "服役最大 von Mises 强度",
        "fatigue_ok": "交变轴向疲劳",
        "thread_strip_ok": "螺纹脱扣",
    }
    checks = {
        "assembly_von_mises_ok": True,
        "service_von_mises_ok": True,
        "fatigue_ok": True,
        "thread_strip_ok": None,  # 未校核
    }

    table = _check_pills(styles, checks, check_labels, refs={})
    # 从 reportlab Table 内部的 _bkgrndcmds 读取每列的背景色
    backgrounds: dict[int, object] = {}
    for cmd in getattr(table, "_bkgrndcmds", []):
        if cmd[0] == "BACKGROUND" and isinstance(cmd[1], tuple):
            backgrounds[cmd[1][0]] = cmd[3]
    # 第 4 列（未校核）期望灰色；前三列期望绿色；不应有红色
    assert backgrounds.get(3) == C_MUTED, (
        f"未校核项必须渲染为 C_MUTED 灰色，实际 {backgrounds}"
    )
    for i in (0, 1, 2):
        assert backgrounds.get(i) == C_PASS, (
            f"通过项第 {i} 列应为 C_PASS，实际 {backgrounds.get(i)}"
        )
    assert C_FAIL not in backgrounds.values(), (
        f"incomplete 场景不应出现 C_FAIL 红色背景，实际 {backgrounds}"
    )
