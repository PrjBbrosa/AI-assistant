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
        """铝壳体+钢螺栓、不同温度 → 有热损失。"""
        data = _base_input()
        data["options"] = {"check_level": "thermal"}
        data["loads"]["thermal_force_loss"] = 0
        data["operating"] = {
            "temp_bolt": 80.0,
            "temp_parts": 30.0,
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


class TestJointTypeThermalIntegration:
    def test_tapped_aluminum_thermal_full_chain(self):
        """螺纹孔连接 + 铝壳体，thermal 层级完整链路。"""
        data = _base_input()
        data["options"] = {
            "check_level": "thermal",
            "joint_type": "tapped",
        }
        data["loads"]["thermal_force_loss"] = 0  # trigger auto estimation
        data["operating"] = {
            "temp_bolt": 80.0,
            "temp_parts": 30.0,
            "alpha_bolt": 11.5e-6,
            "alpha_parts": 23.0e-6,
            "load_cycles": 100000,
        }
        data["clamped"] = {"total_thickness": 20.0}
        data["bearing"]["p_G_allow"] = 700.0
        result = calculate_vdi2230_core(data)
        # joint type
        assert result["joint_type"] == "tapped"
        assert "螺纹孔" in result["scope_note"]
        assert "螺栓头端" in result["r7_note"]
        # thermal auto estimation activated
        assert result["thermal"]["thermal_auto_estimated"] is True
        assert result["thermal"]["thermal_auto_value_N"] > 0
        assert result["thermal"]["alpha_bolt"] == 11.5e-6
        assert result["thermal"]["alpha_parts"] == 23.0e-6
        # R7 still works
        assert "bearing_pressure_ok" in result["checks"]
        # all standard checks present
        assert "assembly_von_mises_ok" in result["checks"]
        assert "operating_axial_ok" in result["checks"]
        assert "residual_clamp_ok" in result["checks"]
        assert "thermal_loss_ok" in result["checks"]

    def test_through_joint_steel_basic_level(self):
        """通孔连接 + 钢，basic 层级。"""
        data = _base_input()
        data["options"] = {"joint_type": "through"}
        data["bearing"]["p_G_allow"] = 700.0
        result = calculate_vdi2230_core(data)
        assert result["joint_type"] == "through"
        assert "通孔" in result["scope_note"]
        assert "螺母端" in result["r7_note"]
        assert result["overall_pass"] in (True, False)  # just check it runs


class TestEmbedEstimation:
    def test_embed_auto_when_zero_and_surface_class_provided(self):
        """embed_loss=0 + surface_class → 自动估算。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 0
        data["clamped"] = {"part_count": 1, "surface_class": "medium"}
        result = calculate_vdi2230_core(data)
        embed = result["embed_estimation"]
        assert embed["embed_auto_estimated"] is True
        assert embed["embed_auto_value_N"] > 0
        assert embed["embed_interfaces"] == 2  # tapped, 1 part → 1+1=2

    def test_embed_manual_value_preserved(self):
        """embed_loss > 0 → 不自动估算，保持用户值。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 800.0
        data["clamped"] = {"part_count": 1, "surface_class": "medium"}
        result = calculate_vdi2230_core(data)
        embed = result["embed_estimation"]
        assert embed["embed_auto_estimated"] is False
        assert embed["embed_auto_value_N"] == 0.0

    def test_embed_skipped_without_surface_class(self):
        """无 surface_class → 不估算。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 0
        result = calculate_vdi2230_core(data)
        embed = result["embed_estimation"]
        assert embed["embed_auto_estimated"] is False

    def test_embed_through_joint_more_interfaces(self):
        """通孔连接比螺纹孔连接多 1 个界面。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 0
        data["clamped"] = {"part_count": 2, "surface_class": "medium"}
        result_tapped = calculate_vdi2230_core(data)
        data["options"] = {"joint_type": "through"}
        result_through = calculate_vdi2230_core(data)
        assert result_tapped["embed_estimation"]["embed_interfaces"] == 3
        assert result_through["embed_estimation"]["embed_interfaces"] == 4
        assert result_through["embed_estimation"]["embed_auto_value_N"] > \
               result_tapped["embed_estimation"]["embed_auto_value_N"]

    def test_embed_rougher_surface_higher_loss(self):
        """粗糙表面嵌入损失更大。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 0
        data["clamped"] = {"part_count": 1, "surface_class": "rough"}
        result_rough = calculate_vdi2230_core(data)
        data["clamped"]["surface_class"] = "fine"
        result_fine = calculate_vdi2230_core(data)
        assert result_rough["embed_estimation"]["embed_auto_value_N"] > \
               result_fine["embed_estimation"]["embed_auto_value_N"]

    def test_embed_formula_correctness(self):
        """验证公式: F_Z = f_z_per_if × n_if × 1e-3 / (δs + δp)。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 0
        data["clamped"] = {"part_count": 1, "surface_class": "medium"}
        result = calculate_vdi2230_core(data)
        embed = result["embed_estimation"]
        delta_s = data["stiffness"]["bolt_compliance"]
        delta_p = data["stiffness"]["clamped_compliance"]
        expected = 2.5 * 2 * 1e-3 / (delta_s + delta_p)  # medium=2.5μm, 2 interfaces
        assert abs(embed["embed_auto_value_N"] - expected) < 0.1


class TestAdditionalLoadReference:
    def test_additional_load_not_in_checks(self):
        """additional_load_ok 不再出现在 checks 字典中。"""
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert "additional_load_ok" not in result["checks"]

    def test_additional_load_in_references(self):
        """附加载荷信息出现在 references 字典中。"""
        data = _base_input()
        result = calculate_vdi2230_core(data)
        ref = result["references"]
        assert "additional_load_ok" in ref
        assert "FA_perm_N" in ref
        assert ref["is_reference"] is True

    def test_overall_pass_ignores_additional_load(self):
        """overall_pass 不受附加载荷估算影响 — 正式校核全过即 overall_pass=True。"""
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert result["overall_pass"] is True
        assert "additional_load_ok" not in result["checks"]
        assert "additional_load_ok" in result["references"]

    def test_fa_perm_value_unchanged(self):
        """FA_perm 计算值不变。"""
        data = _base_input()
        result = calculate_vdi2230_core(data)
        ref = result["references"]
        phi_n = result["intermediate"]["phi_n"]
        rp02 = data["fastener"]["Rp02"]
        as_val = result["derived_geometry_mm"]["As"]
        expected = 0.1 * rp02 * as_val / phi_n
        assert abs(ref["FA_perm_N"] - expected) < 0.1


class TestBatch2Integration:
    def test_embed_estimation_with_thermal_full_chain(self):
        """嵌入损失估算 + 热估算 + R7 全链路。"""
        data = _base_input()
        data["options"] = {
            "check_level": "thermal",
            "joint_type": "tapped",
        }
        data["loads"]["embed_loss"] = 0
        data["loads"]["thermal_force_loss"] = 0
        data["clamped"] = {
            "part_count": 2,
            "surface_class": "medium",
            "total_thickness": 25.0,
        }
        data["operating"] = {
            "temp_bolt": 80.0,
            "temp_parts": 30.0,
            "alpha_bolt": 11.5e-6,
            "alpha_parts": 23.0e-6,
        }
        data["bearing"]["p_G_allow"] = 700.0
        result = calculate_vdi2230_core(data)
        # embed estimation activated
        embed = result["embed_estimation"]
        assert embed["embed_auto_estimated"] is True
        assert embed["embed_interfaces"] == 3  # tapped, 2 parts
        # thermal auto estimation activated
        assert result["thermal"]["thermal_auto_estimated"] is True
        # additional_load is reference, not in checks
        assert "additional_load_ok" not in result["checks"]
        assert "additional_load_ok" in result["references"]
        # overall_pass based only on formal checks
        assert isinstance(result["overall_pass"], bool)

    def test_manual_embed_overrides_estimation(self):
        """手动嵌入损失 > 0 时不使用自动估算。"""
        data = _base_input()
        data["loads"]["embed_loss"] = 1500.0
        data["clamped"] = {"part_count": 1, "surface_class": "rough"}
        result = calculate_vdi2230_core(data)
        assert result["embed_estimation"]["embed_auto_estimated"] is False
        # FM_min 中使用的是手动值 1500，而非估算值
        inter = result["intermediate"]
        phi_n = inter["phi_n"]
        fa = data["loads"]["FA_max"]
        # basic check_level (default) → thermal_effective = 0.0
        expected_fmmin = inter["F_K_required_N"] + (1 - phi_n) * fa + 1500.0 + 0.0
        assert abs(inter["FMmin_N"] - expected_fmmin) < 1.0


class TestTighteningMethodWarnings:
    def test_torque_method_alpha_in_range_no_warning(self):
        """扭矩法 αA=1.6 在建议范围 [1.4, 1.8] 内，无 warning。"""
        data = _base_input()
        data.setdefault("options", {})["tightening_method"] = "torque"
        data["tightening"]["alpha_A"] = 1.6
        result = calculate_vdi2230_core(data)
        assert not any("αA" in w for w in result["warnings"])

    def test_torque_method_alpha_out_of_range_warns(self):
        """扭矩法 αA=1.2 低于建议下限 1.4，触发 warning。"""
        data = _base_input()
        data.setdefault("options", {})["tightening_method"] = "torque"
        data["tightening"]["alpha_A"] = 1.2
        result = calculate_vdi2230_core(data)
        assert any("αA" in w for w in result["warnings"])

    def test_angle_method_alpha_in_range(self):
        """转角法 αA=1.2 在建议范围 [1.1, 1.3] 内，无 warning。"""
        data = _base_input()
        data.setdefault("options", {})["tightening_method"] = "angle"
        data["tightening"]["alpha_A"] = 1.2
        result = calculate_vdi2230_core(data)
        assert not any("αA" in w for w in result["warnings"])

    def test_hydraulic_method_alpha_out_of_range_warns(self):
        """液压拉伸法 αA=1.3 超出建议上限 1.15，触发 warning。"""
        data = _base_input()
        data.setdefault("options", {})["tightening_method"] = "hydraulic"
        data["tightening"]["alpha_A"] = 1.3
        result = calculate_vdi2230_core(data)
        assert any("αA" in w for w in result["warnings"])

    def test_unknown_method_no_warning(self):
        """默认 tightening_method=torque + αA=1.6 在范围内，无 warning。"""
        data = _base_input()
        result = calculate_vdi2230_core(data)
        assert not any("αA" in w for w in result["warnings"])

    def test_tightening_method_echoed_in_result(self):
        """tightening_method 回显在结果中。"""
        data = _base_input()
        data.setdefault("options", {})["tightening_method"] = "angle"
        result = calculate_vdi2230_core(data)
        assert result["tightening_method"] == "angle"


class TestR5TorsionResidual:
    def test_torque_method_includes_torsion_residual(self):
        """扭矩法 R5 使用 von Mises 含 k_tau=0.5 的扭转残余。"""
        data = _base_input()
        data.setdefault("options", {})["tightening_method"] = "torque"
        result = calculate_vdi2230_core(data)
        stresses = result["stresses_mpa"]
        assert stresses["sigma_vm_work"] > stresses["sigma_ax_work"]
        assert stresses["k_tau"] == 0.5

    def test_angle_method_no_torsion_residual(self):
        """转角法 R5 的 k_tau=0，σ_vm_work = σ_ax_work。"""
        data = _base_input()
        data.setdefault("options", {})["tightening_method"] = "angle"
        result = calculate_vdi2230_core(data)
        stresses = result["stresses_mpa"]
        assert stresses["k_tau"] == 0.0
        assert abs(stresses["sigma_vm_work"] - stresses["sigma_ax_work"]) < 0.01

    def test_r5_check_uses_vm_work(self):
        """R5 校核使用 σ_vm_work 而非 σ_ax_work。"""
        data = _base_input()
        data.setdefault("options", {})["tightening_method"] = "torque"
        result = calculate_vdi2230_core(data)
        stresses = result["stresses_mpa"]
        expected_pass = stresses["sigma_vm_work"] <= stresses["sigma_allow_work"]
        assert result["checks"]["operating_axial_ok"] == expected_pass

    def test_torsion_residual_formula(self):
        """验证公式: σ_vm_work = √(σ_ax² + 3·(k_τ·τ)²)。"""
        data = _base_input()
        data.setdefault("options", {})["tightening_method"] = "torque"
        result = calculate_vdi2230_core(data)
        s = result["stresses_mpa"]
        import math
        expected = math.sqrt(s["sigma_ax_work"]**2 + 3.0 * (0.5 * s["tau_assembly"])**2)
        assert abs(s["sigma_vm_work"] - expected) < 0.01


class TestFatigueModelImproved:
    def test_fatigue_uses_asv_table_not_018_rp02(self):
        """M10 螺栓疲劳极限应使用 σ_ASV 查表值，而非 0.18×Rp02。"""
        data = _base_input()
        data.setdefault("options", {})["check_level"] = "fatigue"
        result = calculate_vdi2230_core(data)
        fatigue = result["fatigue"]
        # M10, d=10, 轧制螺纹: σ_ASV ≈ 44 MPa
        assert fatigue["sigma_ASV"] > 0
        assert fatigue["sigma_ASV"] < 0.18 * 640  # 查表值远小于旧公式

    def test_larger_bolt_lower_asv(self):
        """M20 螺栓的 σ_ASV 应低于 M10。"""
        data10 = _base_input()
        data10.setdefault("options", {})["check_level"] = "fatigue"
        data20 = _base_input()
        data20["fastener"]["d"] = 20.0
        data20["fastener"]["p"] = 2.5
        data20.setdefault("options", {})["check_level"] = "fatigue"
        r10 = calculate_vdi2230_core(data10)
        r20 = calculate_vdi2230_core(data20)
        assert r10["fatigue"]["sigma_ASV"] > r20["fatigue"]["sigma_ASV"]

    def test_cut_thread_lower_asv(self):
        """切削螺纹 σ_ASV 约为轧制的 65%。"""
        data = _base_input()
        data.setdefault("options", {})["check_level"] = "fatigue"
        data["options"]["surface_treatment"] = "rolled"
        r_rolled = calculate_vdi2230_core(data)
        data["options"]["surface_treatment"] = "cut"
        r_cut = calculate_vdi2230_core(data)
        assert r_cut["fatigue"]["sigma_ASV"] < r_rolled["fatigue"]["sigma_ASV"]
        ratio = r_cut["fatigue"]["sigma_ASV"] / r_rolled["fatigue"]["sigma_ASV"]
        assert 0.55 < ratio < 0.75

    def test_goodman_still_applies(self):
        """Goodman 修正仍然应用于 σ_ASV 基础上。"""
        data = _base_input()
        data.setdefault("options", {})["check_level"] = "fatigue"
        result = calculate_vdi2230_core(data)
        fatigue = result["fatigue"]
        assert fatigue["sigma_a_allow"] <= fatigue["sigma_ASV"] * 1.01

    def test_asv_interpolation_non_standard_diameter(self):
        """非标准直径使用线性插值。"""
        data = _base_input()
        data["fastener"]["d"] = 15.0
        data["fastener"]["p"] = 2.0
        data.setdefault("options", {})["check_level"] = "fatigue"
        result = calculate_vdi2230_core(data)
        fatigue = result["fatigue"]
        # M14: 39, M16: 38 → M15 应介于之间
        assert 37.5 < fatigue["sigma_ASV"] < 39.5
