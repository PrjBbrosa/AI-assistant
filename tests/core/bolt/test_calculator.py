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


class TestBearingPressureR7:
    def test_r7_pass_when_pressure_below_limit(self):
        data = _base_input()
        data["bearing"]["p_G_allow"] = 700.0
        result = calculate_vdi2230_core(data)
        assert "bearing_pressure_ok" in result["checks"]
        assert result["checks"]["bearing_pressure_ok"] is True
        assert result["stresses_mpa"]["p_bearing"] > 0
        assert result["stresses_mpa"]["A_bearing_mm2"] > 0

    def test_r7_fail_when_pressure_above_limit(self):
        data = _base_input()
        data["bearing"]["p_G_allow"] = 1.0  # 极低许用值
        result = calculate_vdi2230_core(data)
        assert result["checks"]["bearing_pressure_ok"] is False
        assert result["overall_pass"] is False

    def test_r7_skipped_when_p_g_allow_missing(self):
        data = _base_input()
        # 不设置 p_G_allow
        result = calculate_vdi2230_core(data)
        assert "bearing_pressure_ok" not in result["checks"]

    def test_r7_skipped_when_p_g_allow_zero(self):
        data = _base_input()
        data["bearing"]["p_G_allow"] = 0.0
        result = calculate_vdi2230_core(data)
        assert "bearing_pressure_ok" not in result["checks"]

    def test_r7_formula_correctness(self):
        data = _base_input()
        data["bearing"]["p_G_allow"] = 700.0
        result = calculate_vdi2230_core(data)
        d_inner = data["bearing"]["bearing_d_inner"]
        d_outer = data["bearing"]["bearing_d_outer"]
        a_expected = math.pi / 4.0 * (d_outer**2 - d_inner**2)
        fm_max = result["intermediate"]["FMmax_N"]
        p_expected = fm_max / a_expected
        assert abs(result["stresses_mpa"]["A_bearing_mm2"] - a_expected) < 0.1
        assert abs(result["stresses_mpa"]["p_bearing"] - p_expected) < 0.1

    def test_r7_tapped_note_says_head_side(self):
        data = _base_input()
        data["bearing"]["p_G_allow"] = 700.0
        result = calculate_vdi2230_core(data)
        assert "螺栓头端" in result["r7_note"]
        assert "螺母端" not in result["r7_note"]

    def test_r7_through_note_says_both_sides(self):
        data = _base_input()
        data["bearing"]["p_G_allow"] = 700.0
        data.setdefault("options", {})["joint_type"] = "through"
        result = calculate_vdi2230_core(data)
        assert "螺母端" in result["r7_note"]

    def test_r7_note_absent_when_r7_inactive(self):
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert result["r7_note"] == ""


class TestCalculationMode:
    def test_default_mode_is_design(self):
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert result["calculation_mode"] == "design"
        assert result["r3_note"] is not None

    def test_design_mode_r3_always_true(self):
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert result["checks"]["residual_clamp_ok"] is True

    def test_verify_mode_with_sufficient_preload(self):
        data = _base_input()
        data["options"] = {"calculation_mode": "verify"}
        # 先用设计模式计算出 FM_min，然后用更大的值做校核
        design_result = calculate_vdi2230_core(_base_input())
        fm_min_design = design_result["intermediate"]["FMmin_N"]
        data["loads"]["FM_min_input"] = fm_min_design * 1.2  # 120% 裕量
        result = calculate_vdi2230_core(data)
        assert result["calculation_mode"] == "verify"
        assert result["checks"]["residual_clamp_ok"] is True

    def test_verify_mode_with_insufficient_preload(self):
        data = _base_input()
        data["options"] = {"calculation_mode": "verify"}
        data["loads"]["FM_min_input"] = 100.0  # 远低于需求
        result = calculate_vdi2230_core(data)
        assert result["checks"]["residual_clamp_ok"] is False
        assert result["overall_pass"] is False

    def test_verify_mode_requires_fm_min_input(self):
        data = _base_input()
        data["options"] = {"calculation_mode": "verify"}
        # 不提供 FM_min_input
        with pytest.raises(InputError, match="FM_min_input"):
            calculate_vdi2230_core(data)

    def test_verify_mode_fm_min_used_for_torque_and_stress(self):
        data = _base_input()
        data["options"] = {"calculation_mode": "verify"}
        fm_input = 20000.0
        data["loads"]["FM_min_input"] = fm_input
        result = calculate_vdi2230_core(data)
        assert abs(result["intermediate"]["FMmin_N"] - fm_input) < 1e-6
        assert abs(result["intermediate"]["FMmax_N"] - fm_input * data["tightening"]["alpha_A"]) < 1.0


class TestJointType:
    def test_default_joint_type_is_tapped(self):
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert result["joint_type"] == "tapped"

    def test_through_joint_type_echoed(self):
        data = _base_input()
        data.setdefault("options", {})["joint_type"] = "through"
        result = calculate_vdi2230_core(data)
        assert result["joint_type"] == "through"

    def test_invalid_joint_type_raises(self):
        data = _base_input()
        data.setdefault("options", {})["joint_type"] = "invalid"
        with pytest.raises(InputError, match="joint_type"):
            calculate_vdi2230_core(data)

    def test_scope_note_mentions_joint_type(self):
        data = _base_input()
        data.setdefault("options", {})["joint_type"] = "through"
        result = calculate_vdi2230_core(data)
        assert "通孔" in result["scope_note"]

    def test_scope_note_tapped(self):
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert "螺纹孔" in result["scope_note"]


class TestThermalMaterial:
    def test_steel_bolt_aluminum_clamped_thermal_loss(self):
        """铝壳体+钢螺栓的热损失应显著大于钢+钢。"""
        data = _base_input()
        data["options"] = {"check_level": "thermal"}
        data["loads"]["thermal_force_loss"] = 0
        data["operating"] = {
            "temp_bolt": 80.0,
            "temp_parts": 80.0,
            "alpha_bolt": 11.5e-6,
            "alpha_parts": 23.0e-6,
        }
        data["clamped"] = {"total_thickness": 20.0}
        result = calculate_vdi2230_core(data)
        thermal = result["thermal"]
        assert thermal["thermal_auto_estimated"] is True
        assert thermal["thermal_auto_value_N"] > 0

    def test_same_material_no_thermal_loss(self):
        """相同材料、相同温度 → 无热损失。"""
        data = _base_input()
        data["options"] = {"check_level": "thermal"}
        data["loads"]["thermal_force_loss"] = 0
        data["operating"] = {
            "temp_bolt": 80.0,
            "temp_parts": 80.0,
            "alpha_bolt": 11.5e-6,
            "alpha_parts": 11.5e-6,
        }
        data["clamped"] = {"total_thickness": 20.0}
        result = calculate_vdi2230_core(data)
        assert result["thermal"]["thermal_auto_value_N"] == 0.0
        assert result["thermal"]["thermal_auto_estimated"] is False

    def test_different_temps_same_alpha_no_loss(self):
        """相同材料但不同温度 → 无热损失（Δα=0 使热力为零）。"""
        data = _base_input()
        data["options"] = {"check_level": "thermal"}
        data["loads"]["thermal_force_loss"] = 0
        data["operating"] = {
            "temp_bolt": 100.0,
            "temp_parts": 20.0,
            "alpha_bolt": 11.5e-6,
            "alpha_parts": 11.5e-6,
        }
        data["clamped"] = {"total_thickness": 20.0}
        result = calculate_vdi2230_core(data)
        assert result["thermal"]["thermal_auto_value_N"] == 0.0

    def test_alpha_values_echoed_in_thermal_output(self):
        data = _base_input()
        data["options"] = {"check_level": "thermal"}
        data["loads"]["thermal_force_loss"] = 0
        data["operating"] = {
            "temp_bolt": 80.0, "temp_parts": 30.0,
            "alpha_bolt": 11.5e-6, "alpha_parts": 23.0e-6,
        }
        data["clamped"] = {"total_thickness": 20.0}
        result = calculate_vdi2230_core(data)
        assert "alpha_bolt" in result["thermal"]
        assert "alpha_parts" in result["thermal"]
        assert result["thermal"]["alpha_bolt"] == 11.5e-6
        assert result["thermal"]["alpha_parts"] == 23.0e-6
