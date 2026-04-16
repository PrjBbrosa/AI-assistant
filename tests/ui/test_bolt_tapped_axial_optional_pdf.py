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


def test_generate_tapped_axial_pdf_report(tmp_path: Path) -> None:
    pytest.importorskip("reportlab")

    from app.ui.report_pdf_tapped_axial import generate_tapped_axial_report

    out = tmp_path / "tapped_axial_report.pdf"
    generate_tapped_axial_report(out, _sample_payload(), _sample_result())

    assert out.exists()
    assert out.stat().st_size > 1000
