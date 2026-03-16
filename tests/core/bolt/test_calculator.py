"""VDI 2230 bolt calculator tests."""
import math
import pytest
from core.bolt.calculator import InputError, calculate_vdi2230_core


def _base_input() -> dict:
    """最小可用输入（基于 input_case_02.json，已知全部通过）。"""
    return {
        "fastener": {"d": 12.0, "p": 1.75, "Rp02": 940.0},
        "tightening": {
            "alpha_A": 1.5, "mu_thread": 0.1, "mu_bearing": 0.12,
            "utilization": 0.85, "thread_flank_angle_deg": 60.0,
        },
        "loads": {
            "FA_max": 6000.0, "FQ_max": 600.0, "embed_loss": 600.0,
            "thermal_force_loss": 300.0, "slip_friction_coefficient": 0.2,
            "friction_interfaces": 1.0,
        },
        "stiffness": {
            "bolt_compliance": 1.8e-06, "clamped_compliance": 2.4e-06,
            "load_introduction_factor_n": 1.0,
        },
        "bearing": {"bearing_d_inner": 13.0, "bearing_d_outer": 22.0},
        "checks": {"yield_safety_operating": 1.15},
    }


class TestPhiNHardBlock:
    def test_phi_n_ge_1_raises_input_error(self):
        data = _base_input()
        # n=2.0 使 phi_n = 2.0 * delta_p/(delta_s+delta_p) > 1
        data["stiffness"]["load_introduction_factor_n"] = 2.0
        with pytest.raises(InputError, match="phi_n"):
            calculate_vdi2230_core(data)

    def test_phi_n_below_1_passes(self):
        data = _base_input()
        data["stiffness"]["load_introduction_factor_n"] = 1.0
        result = calculate_vdi2230_core(data)
        assert result["intermediate"]["phi_n"] < 1.0

    def test_phi_n_warning_removed_from_output(self):
        data = _base_input()
        result = calculate_vdi2230_core(data)
        for w in result.get("warnings", []):
            assert "phi_n" not in w.lower()
