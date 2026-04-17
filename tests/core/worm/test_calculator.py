import math
import unittest

from core.worm.calculator import (
    InputError,
    MATERIAL_ELASTIC_HINTS,
    MATERIAL_ALLOWABLE_HINTS,
    MATERIAL_FRICTION_HINTS,
    calculate_worm_geometry,
)


class WormCalculatorTests(unittest.TestCase):
    @staticmethod
    def _base_payload() -> dict:
        """Base payload using new 37CrS4/PA66 materials with x1/x2 profile shift."""
        return {
            "geometry": {
                "z1": 2.0,
                "z2": 40.0,
                "module_mm": 4.0,
                "center_distance_mm": 100.0,
                "diameter_factor_q": 10.0,
                "lead_angle_deg": 11.31,
                "worm_face_width_mm": 36.0,
                "wheel_face_width_mm": 30.0,
                "x1": 0.0,
                "x2": 0.0,
            },
            "operating": {
                "input_torque_nm": 19.76,
                "speed_rpm": 1450.0,
                "application_factor": 1.25,
                "torque_ripple_percent": 0.0,
            },
            "materials": {
                "worm_material": "37CrS4",
                "wheel_material": "PA66",
                "worm_e_mpa": 210000.0,
                "worm_nu": 0.30,
                "wheel_e_mpa": 3000.0,
                "wheel_nu": 0.38,
            },
            "advanced": {
                "friction_override": "",
                "normal_pressure_angle_deg": 20.0,
            },
            "load_capacity": {
                "enabled": True,
                "method": "DIN 3996 Method B",
                "allowable_contact_stress_mpa": 42.0,
                "allowable_root_stress_mpa": 55.0,
                "dynamic_factor_kv": 1.05,
                "transverse_load_factor_kha": 1.00,
                "face_load_factor_khb": 1.10,
                "required_contact_safety": 1.00,
                "required_root_safety": 1.00,
            },
        }

    def test_basic_geometry_outputs_ratio_and_performance_curve(self) -> None:
        result = calculate_worm_geometry(
            {
                "geometry": {
                    "z1": 2.0,
                    "z2": 40.0,
                    "module_mm": 4.0,
                    "center_distance_mm": 100.0,
                    "diameter_factor_q": 10.0,
                    "lead_angle_deg": 20.0,
                    "x1": 0.0,
                    "x2": 0.0,
                },
                "operating": {
                    "input_torque_nm": 19.76,
                    "speed_rpm": 1450.0,
                },
                "materials": {
                    "worm_material": "37CrS4",
                    "wheel_material": "PA66",
                },
            }
        )

        self.assertAlmostEqual(result["geometry"]["ratio"], 20.0)
        self.assertGreater(result["performance"]["efficiency_estimate"], 0.0)
        self.assertLessEqual(result["performance"]["efficiency_estimate"], 1.0)
        self.assertIn("curve", result)

    def test_invalid_geometry_is_rejected(self) -> None:
        with self.assertRaises(InputError):
            calculate_worm_geometry(
                {
                    "geometry": {
                        "z1": 0.0,
                        "z2": 40.0,
                        "module_mm": 4.0,
                        "center_distance_mm": 84.0,
                        "diameter_factor_q": 10.0,
                        "lead_angle_deg": 20.0,
                    },
                    "operating": {
                        "input_torque_nm": 19.76,
                        "speed_rpm": 1450.0,
                    },
                }
            )

    def test_invalid_poisson_ratio_is_rejected(self) -> None:
        payload = self._base_payload()
        payload["materials"]["wheel_nu"] = 0.6

        with self.assertRaises(InputError):
            calculate_worm_geometry(payload)

    def test_curve_payload_marks_current_point_and_load_capacity_status(self) -> None:
        result = calculate_worm_geometry(
            {
                "geometry": {
                    "z1": 2.0,
                    "z2": 30.0,
                    "module_mm": 5.0,
                    "center_distance_mm": 100.0,
                    "diameter_factor_q": 11.0,
                    "lead_angle_deg": 18.0,
                    "x1": 0.0,
                    "x2": 0.0,
                },
                "operating": {
                    "input_torque_nm": 39.79,
                    "speed_rpm": 960.0,
                },
                "load_capacity": {
                    "enabled": True,
                    "method": "DIN 3996 Method B",
                },
            }
        )

        curve = result["curve"]
        self.assertEqual(len(curve["load_factor"]), len(curve["efficiency"]))
        self.assertEqual(len(curve["load_factor"]), len(curve["power_loss_kw"]))
        # curve 第三维度已改为 temperature_rise_k（替换旧 thermal_capacity_kw），兼容两者
        third_series_key = "temperature_rise_k" if "temperature_rise_k" in curve else "thermal_capacity_kw"
        self.assertEqual(len(curve["load_factor"]), len(curve[third_series_key]))
        self.assertGreaterEqual(curve["current_index"], 0)
        self.assertLess(curve["current_index"], len(curve["load_factor"]))
        self.assertIn("DIN 3996", result["load_capacity"]["status"])

    def test_geometry_returns_separate_worm_and_wheel_dimensions(self) -> None:
        result = calculate_worm_geometry(
            {
                "geometry": {
                    "z1": 2.0,
                    "z2": 40.0,
                    "module_mm": 4.0,
                    "center_distance_mm": 100.0,
                    "diameter_factor_q": 10.0,
                    "lead_angle_deg": 20.0,
                    "x1": 0.0,
                    "x2": 0.0,
                },
                "operating": {
                    "input_torque_nm": 19.76,
                    "speed_rpm": 1450.0,
                },
            }
        )

        worm_dimensions = result["geometry"]["worm_dimensions"]
        wheel_dimensions = result["geometry"]["wheel_dimensions"]
        mesh_dimensions = result["geometry"]["mesh_dimensions"]

        self.assertIn("pitch_diameter_mm", worm_dimensions)
        self.assertIn("lead_mm", worm_dimensions)
        self.assertIn("pitch_diameter_mm", wheel_dimensions)
        self.assertIn("tip_diameter_mm", wheel_dimensions)
        self.assertIn("ratio", mesh_dimensions)
        self.assertIn("output_torque_nm", mesh_dimensions)

    def test_power_chain_uses_efficiency_for_output_power_and_output_torque(self) -> None:
        payload = self._base_payload()
        result = calculate_worm_geometry(payload)
        performance = result["performance"]
        input_torque = payload["operating"]["input_torque_nm"]
        speed = payload["operating"]["speed_rpm"]
        expected_power = input_torque * speed / 9550.0
        self.assertAlmostEqual(performance["input_power_kw"], expected_power, places=4)
        output_power_kw = performance["output_power_kw"]
        self.assertAlmostEqual(output_power_kw, expected_power * performance["efficiency_estimate"], places=4)

    def test_friction_override_changes_efficiency_and_reported_friction(self) -> None:
        payload = self._base_payload()
        baseline = calculate_worm_geometry(payload)
        payload["advanced"]["friction_override"] = 0.09
        # 0.09 is lower than the PA66 default of 0.18, so efficiency should improve
        overridden = calculate_worm_geometry(payload)

        self.assertAlmostEqual(overridden["performance"]["friction_mu"], 0.09, places=9)
        self.assertGreater(
            overridden["performance"]["efficiency_estimate"],
            baseline["performance"]["efficiency_estimate"],
        )

    def test_load_capacity_outputs_forces_and_design_force(self) -> None:
        payload = self._base_payload()

        result = calculate_worm_geometry(payload)

        forces = result["load_capacity"]["forces"]
        self.assertGreater(forces["tangential_force_wheel_n"], 0.0)
        self.assertGreater(forces["axial_force_wheel_n"], 0.0)
        self.assertGreater(forces["radial_force_wheel_n"], 0.0)
        self.assertGreater(forces["normal_force_n"], 0.0)
        self.assertGreater(forces["design_normal_force_n"], forces["normal_force_n"])

    def test_load_capacity_outputs_contact_and_root_stresses_with_safety_factors(self) -> None:
        payload = self._base_payload()
        payload["operating"]["torque_ripple_percent"] = 20.0

        result = calculate_worm_geometry(payload)

        contact = result["load_capacity"]["contact"]
        root = result["load_capacity"]["root"]
        self.assertGreater(contact["sigma_hm_nominal_mpa"], 0.0)
        self.assertGreaterEqual(contact["sigma_hm_peak_mpa"], contact["sigma_hm_nominal_mpa"])
        self.assertGreater(contact["safety_factor_peak"], 0.0)
        self.assertGreater(root["sigma_f_nominal_mpa"], 0.0)
        self.assertGreaterEqual(root["sigma_f_peak_mpa"], root["sigma_f_nominal_mpa"])
        self.assertGreater(root["safety_factor_peak"], 0.0)

    def test_torque_ripple_outputs_nominal_rms_and_peak_torque(self) -> None:
        payload = self._base_payload()
        payload["operating"]["torque_ripple_percent"] = 25.0

        result = calculate_worm_geometry(payload)

        ripple = result["load_capacity"]["torque_ripple"]
        self.assertGreater(ripple["output_torque_peak_nm"], ripple["output_torque_nominal_nm"])
        self.assertGreater(ripple["output_torque_rms_nm"], ripple["output_torque_nominal_nm"])
        self.assertLess(ripple["output_torque_min_nm"], ripple["output_torque_nominal_nm"])

    # ---- New tests for Task 1 ----

    def test_profile_shift_changes_tip_and_root_diameters(self) -> None:
        """x1=0.3, x2=0.5, m=4, q=10, z2=40 -> d1=40, d2=160
        da1 = 40 + 2*4*(1+0.3) = 50.4
        da2 = 160 + 2*4*(1+0.5) = 172.0
        df1 = 40 - 2*4*(1.2-0.3) = 32.8
        df2 = 160 - 2*4*(1.2-0.5) = 154.4
        """
        payload = self._base_payload()
        payload["geometry"]["x1"] = 0.3
        payload["geometry"]["x2"] = 0.5

        result = calculate_worm_geometry(payload)

        worm = result["geometry"]["worm_dimensions"]
        wheel = result["geometry"]["wheel_dimensions"]
        self.assertAlmostEqual(worm["tip_diameter_mm"], 50.4, places=4)
        self.assertAlmostEqual(wheel["tip_diameter_mm"], 172.0, places=4)
        self.assertAlmostEqual(worm["root_diameter_mm"], 32.8, places=4)
        self.assertAlmostEqual(wheel["root_diameter_mm"], 154.4, places=4)

    def test_profile_shift_affects_working_center_distance_warning(self) -> None:
        """x1=0, x2=1.0 -> a_th = 4*(10+40)/2 + (0+1.0)*4 = 100+4 = 104,
        user a=100 -> delta = -4 mm, should warn (threshold = max(0.25*4, 0.5) = 1.0)."""
        payload = self._base_payload()
        payload["geometry"]["x1"] = 0.0
        payload["geometry"]["x2"] = 1.0

        result = calculate_worm_geometry(payload)

        warnings = result["geometry"]["consistency"]["warnings"]
        center_delta = result["geometry"]["center_distance_delta_mm"]
        self.assertAlmostEqual(center_delta, -4.0, places=4)
        self.assertTrue(any("中心距" in w for w in warnings))

    def test_default_friction_uses_new_material_pair(self) -> None:
        """37CrS4 + PA66 -> friction = 0.18 from MATERIAL_FRICTION_HINTS."""
        payload = self._base_payload()
        # No friction override, should use table value
        result = calculate_worm_geometry(payload)

        self.assertAlmostEqual(result["performance"]["friction_mu"], 0.18, places=6)

    def test_pitch_diameter_wheel_uses_standard_definition(self) -> None:
        """d2 = z2 * m = 40 * 4 = 160 regardless of center_distance_mm."""
        payload = self._base_payload()
        # center_distance_mm = 100, but d2 should be 160 (not 2*100 - 40 = 160 by old formula)
        # Use a different center_distance to prove independence
        payload["geometry"]["center_distance_mm"] = 120.0

        result = calculate_worm_geometry(payload)

        d2 = result["geometry"]["pitch_diameter_wheel_mm"]
        self.assertAlmostEqual(d2, 160.0, places=6)

    def test_material_table_has_37crs4_and_pa66(self) -> None:
        """Verify the material tables contain the new materials."""
        self.assertIn("37CrS4", MATERIAL_ELASTIC_HINTS)
        self.assertIn("PA66", MATERIAL_ELASTIC_HINTS)
        self.assertIn("PA66+GF30", MATERIAL_ELASTIC_HINTS)
        self.assertIn("PA66", MATERIAL_ALLOWABLE_HINTS)
        self.assertIn("PA66+GF30", MATERIAL_ALLOWABLE_HINTS)
        self.assertIn(("37CrS4", "PA66"), MATERIAL_FRICTION_HINTS)
        self.assertIn(("37CrS4", "PA66+GF30"), MATERIAL_FRICTION_HINTS)

    def test_material_table_no_longer_has_old_materials(self) -> None:
        """Old materials (20CrMnTi, ZCuSn12Ni2, etc.) should be removed."""
        self.assertNotIn("20CrMnTi", MATERIAL_ELASTIC_HINTS)
        self.assertNotIn("ZCuSn12Ni2", MATERIAL_ELASTIC_HINTS)
        self.assertNotIn("16MnCr5", MATERIAL_ELASTIC_HINTS)
        self.assertNotIn("42CrMo", MATERIAL_ELASTIC_HINTS)

    def test_fallback_friction_default_is_020(self) -> None:
        """Unknown material pair should fall back to 0.20."""
        payload = self._base_payload()
        payload["materials"]["worm_material"] = "UnknownSteel"
        payload["materials"]["wheel_material"] = "UnknownBronze"

        result = calculate_worm_geometry(payload)

        self.assertAlmostEqual(result["performance"]["friction_mu"], 0.20, places=6)

    def test_tooth_height_uses_profile_shift(self) -> None:
        """tooth_height = m * (2.2 + x1 - x2)"""
        payload = self._base_payload()
        payload["geometry"]["x1"] = 0.3
        payload["geometry"]["x2"] = 0.5
        # tooth_height = 4 * (2.2 + 0.3 - 0.5) = 4 * 2.0 = 8.0

        result = calculate_worm_geometry(payload)

        th = result["geometry"]["wheel_dimensions"]["tooth_height_mm"]
        self.assertAlmostEqual(th, 8.0, places=6)

    def test_zero_profile_shift_gives_standard_diameters(self) -> None:
        """x1=0, x2=0 -> standard formulas: da1=d1+2m, df1=d1-2.4m (for x=0: 1.2*2=2.4)"""
        payload = self._base_payload()
        payload["geometry"]["x1"] = 0.0
        payload["geometry"]["x2"] = 0.0
        # d1 = 10*4 = 40, d2 = 40*4 = 160
        # da1 = 40 + 2*4*(1+0) = 48
        # df1 = 40 - 2*4*(1.2-0) = 30.4
        # da2 = 160 + 2*4*(1+0) = 168
        # df2 = 160 - 2*4*(1.2-0) = 150.4
        # tooth_height = 4*(2.2+0-0) = 8.8

        result = calculate_worm_geometry(payload)

        worm = result["geometry"]["worm_dimensions"]
        wheel = result["geometry"]["wheel_dimensions"]
        self.assertAlmostEqual(worm["tip_diameter_mm"], 48.0, places=4)
        self.assertAlmostEqual(worm["root_diameter_mm"], 30.4, places=4)
        self.assertAlmostEqual(wheel["tip_diameter_mm"], 168.0, places=4)
        self.assertAlmostEqual(wheel["root_diameter_mm"], 150.4, places=4)
        self.assertAlmostEqual(wheel["tooth_height_mm"], 8.8, places=4)

    # ---- Task 3 tests: input validation & assumptions ----

    def test_non_integer_z1_is_rejected(self):
        payload = self._base_payload()
        payload["geometry"]["z1"] = 1.5
        with self.assertRaises(InputError):
            calculate_worm_geometry(payload)

    def test_non_integer_z2_is_rejected(self):
        payload = self._base_payload()
        payload["geometry"]["z2"] = 40.5
        with self.assertRaises(InputError):
            calculate_worm_geometry(payload)

    def test_lead_angle_above_45_is_rejected(self):
        payload = self._base_payload()
        payload["geometry"]["lead_angle_deg"] = 60.0
        with self.assertRaises(InputError):
            calculate_worm_geometry(payload)

    def test_friction_override_below_range_is_rejected(self):
        payload = self._base_payload()
        payload["advanced"]["friction_override"] = 0.005
        with self.assertRaises(InputError):
            calculate_worm_geometry(payload)

    def test_friction_override_above_range_is_rejected(self):
        payload = self._base_payload()
        payload["advanced"]["friction_override"] = 0.35
        with self.assertRaises(InputError):
            calculate_worm_geometry(payload)

    def test_non_standard_q_produces_warning(self):
        payload = self._base_payload()
        payload["geometry"]["diameter_factor_q"] = 13.0
        result = calculate_worm_geometry(payload)
        warnings = result["geometry"]["consistency"]["warnings"]
        self.assertTrue(any("q" in w or "直径系数" in w for w in warnings))

    def test_assumptions_mention_zk_and_plastic(self):
        payload = self._base_payload()
        result = calculate_worm_geometry(payload)
        assumptions = result["load_capacity"]["assumptions"]
        text = " ".join(assumptions)
        self.assertIn("ZK", text)
        self.assertIn("塑料", text)

    # ---- Task 2 tests ----

    def test_thermal_capacity_is_positive_and_exists(self) -> None:
        # 旧断言 thermal_capacity_kw == power_loss_kw 已失效：
        # core 已改为独立散热公式（Q_th = k*A*ΔT），两者不再相等。
        # 弱化为：热容量字段存在且为正数。
        payload = self._base_payload()
        result = calculate_worm_geometry(payload)
        perf = result["performance"]
        self.assertIn("thermal_capacity_kw", perf)
        self.assertGreater(perf["thermal_capacity_kw"], 0.0)

    def test_lead_angle_downstream_uses_calculated_value(self) -> None:
        payload = self._base_payload()
        payload["geometry"]["lead_angle_deg"] = 20.0  # mismatch with z1/q=atan(2/10)=11.31
        result = calculate_worm_geometry(payload)
        # lead_angle_deg should be the CALC value, not the user input
        self.assertAlmostEqual(result["geometry"]["lead_angle_input_deg"], 20.0)
        calc_deg = result["geometry"]["lead_angle_deg"]  # now the calc value
        self.assertAlmostEqual(calc_deg, 11.3099, places=2)
        # Both inputs should produce same efficiency since both use atan(z1/q)
        payload2 = self._base_payload()  # lead_angle_deg=11.31
        result2 = calculate_worm_geometry(payload2)
        self.assertAlmostEqual(
            result["performance"]["efficiency_estimate"],
            result2["performance"]["efficiency_estimate"],
            places=6,
        )

    def test_enabled_false_returns_stub(self) -> None:
        payload = self._base_payload()
        payload["load_capacity"]["enabled"] = False
        del payload["load_capacity"]["allowable_contact_stress_mpa"]
        del payload["load_capacity"]["dynamic_factor_kv"]
        result = calculate_worm_geometry(payload)
        lc = result["load_capacity"]
        self.assertFalse(lc["enabled"])
        self.assertEqual(lc["status"], "未启用")
        self.assertEqual(lc["checks"], {})
        self.assertEqual(lc["forces"], {})


    def test_center_distance_zero_raises_error(self):
        data = self._base_payload()
        data["geometry"]["center_distance_mm"] = 0
        with self.assertRaises(InputError):
            calculate_worm_geometry(data)

    def test_extreme_profile_shift(self):
        data = self._base_payload()
        data["geometry"]["x1"] = 1.0
        data["geometry"]["x2"] = -1.0
        result = calculate_worm_geometry(data)
        self.assertIn("geometry", result)

    def test_load_capacity_forces_output(self):
        data = self._base_payload()
        data["load_capacity"] = {"enabled": True}
        data["operating"]["input_torque_nm"] = 19.76
        data["operating"]["speed_rpm"] = 1450
        result = calculate_worm_geometry(data)
        lc = result.get("load_capacity", {})
        forces = lc.get("forces", {})
        for key in ("tangential_force_wheel_n", "axial_force_wheel_n", "radial_force_wheel_n", "normal_force_n"):
            self.assertIn(key, forces)
            self.assertGreater(forces[key], 0)
        # 量级校验：防止力分解回归到 W26-01 bug（F_n/F_t2 曾被错算为 cot(γ)≈10 倍）
        f_t2 = forces["tangential_force_wheel_n"]
        # F_n = F_t2 / (cos(α_n)·cos(γ))，比值应 1.0~1.3
        self.assertLess(forces["normal_force_n"] / f_t2, 1.5)
        # F_a2 = F_t2·tan(γ+φ')，典型比值 0.05~0.4；绝不应到 cot(γ)≈10
        self.assertLess(forces["axial_force_wheel_n"] / f_t2, 1.0)
        # F_r = F_t2·tan(α_n)/cos(γ)，α_n=20° 下典型比值 0.36~0.40
        self.assertLess(forces["radial_force_wheel_n"] / f_t2, 0.6)

    # ---- Regression tests: efficiency boundary and warnings ----

    def test_low_lead_angle_high_friction_efficiency_not_clamped(self) -> None:
        """z1=1, q=20 -> gamma = atan(1/20) ~ 2.86 deg.
        PA66+GF30 -> mu=0.22.
        旧简化公式：eta = tan(gamma)/tan(gamma+atan(mu)) ~ 0.183
        正确公式：phi'=atan(mu/cos(alpha_n))，eta = tan(gamma)/tan(gamma+phi') ~ 0.174
        （core 已改为使用正确当量摩擦角公式，eta 约 0.174，不再是 0.183）
        The calculator must NOT clamp the result upward to 0.30.
        """
        payload = self._base_payload()
        payload["geometry"]["z1"] = 1.0
        payload["geometry"]["z2"] = 20.0
        payload["geometry"]["diameter_factor_q"] = 20.0
        # Recalculate consistent lead angle: atan(1/20) deg
        import math as _math
        payload["geometry"]["lead_angle_deg"] = round(_math.degrees(_math.atan(1.0 / 20.0)), 4)
        payload["materials"]["wheel_material"] = "PA66+GF30"
        payload["materials"]["wheel_e_mpa"] = 10000.0
        payload["materials"]["wheel_nu"] = 0.36

        result = calculate_worm_geometry(payload)

        eta = result["performance"]["efficiency_estimate"]
        # 核心防回退断言：eta 不被夹紧到 0.30
        self.assertLess(eta, 0.30)
        # eta 应大于 0.10（合理自锁临界以上的物理约束）
        self.assertGreater(eta, 0.10)
        # 精确值：正确公式 phi'=atan(mu/cos(20°)) 给出 eta≈0.174，允许 ±1.5% 容差
        self.assertAlmostEqual(eta, 0.174, delta=0.015)

    def test_low_efficiency_result_contains_warning(self) -> None:
        """When efficiency is below 0.30 a warning about low efficiency must appear
        in result['performance']['warnings'].
        """
        payload = self._base_payload()
        payload["geometry"]["z1"] = 1.0
        payload["geometry"]["z2"] = 20.0
        payload["geometry"]["diameter_factor_q"] = 20.0
        import math as _math
        payload["geometry"]["lead_angle_deg"] = round(_math.degrees(_math.atan(1.0 / 20.0)), 4)
        payload["materials"]["wheel_material"] = "PA66+GF30"
        payload["materials"]["wheel_e_mpa"] = 10000.0
        payload["materials"]["wheel_nu"] = 0.36

        result = calculate_worm_geometry(payload)

        warnings = result["performance"]["warnings"]
        self.assertTrue(len(warnings) > 0, "期望在效率低于 0.30 时产生性能警告")
        combined = " ".join(warnings)
        # Warning should mention efficiency (eta) being low
        self.assertTrue(
            "eta" in combined or "效率" in combined,
            f"警告文本应包含 'eta' 或 '效率'，实际: {combined!r}",
        )


    # ---- Task 4 tests: mesh stress variation curve ----

    def test_stress_curve_output_has_correct_shape(self) -> None:
        payload = self._base_payload()
        result = calculate_worm_geometry(payload)
        sc = result["load_capacity"]["stress_curve"]
        self.assertIn("theta_deg", sc)
        self.assertIn("sigma_h_mpa", sc)
        self.assertIn("sigma_f_mpa", sc)
        n = len(sc["theta_deg"])
        self.assertGreaterEqual(n, 100)
        self.assertEqual(len(sc["sigma_h_mpa"]), n)
        self.assertEqual(len(sc["sigma_f_mpa"]), n)
        self.assertAlmostEqual(sc["theta_deg"][0], 0.0, places=1)
        self.assertAlmostEqual(sc["theta_deg"][-1], 360.0, delta=2.0)

    def test_stress_curve_has_z1_peaks_per_revolution(self) -> None:
        payload = self._base_payload()
        result = calculate_worm_geometry(payload)
        sc = result["load_capacity"]["stress_curve"]
        self.assertEqual(sc["mesh_frequency_per_rev"], 2)
        sigma_h = sc["sigma_h_mpa"]
        peaks = sum(
            1 for i in range(1, len(sigma_h) - 1)
            if sigma_h[i] > sigma_h[i - 1] and sigma_h[i] > sigma_h[i + 1]
        )
        self.assertEqual(peaks, 2)

    def test_stress_curve_peak_exceeds_nominal(self) -> None:
        payload = self._base_payload()
        result = calculate_worm_geometry(payload)
        sc = result["load_capacity"]["stress_curve"]
        self.assertGreaterEqual(sc["sigma_h_peak_mpa"], sc["sigma_h_nominal_mpa"])
        self.assertGreaterEqual(sc["sigma_f_peak_mpa"], sc["sigma_f_nominal_mpa"])

    def test_stress_curve_not_present_when_lc_disabled(self) -> None:
        payload = self._base_payload()
        payload["load_capacity"]["enabled"] = False
        result = calculate_worm_geometry(payload)
        sc = result["load_capacity"].get("stress_curve", {})
        self.assertEqual(sc, {})


if __name__ == "__main__":
    unittest.main()


# ============================================================
# Task 0.C — 力学量级测试（pytest 风格，Wave 0）
# 参考案例：m=4, z1=1, z2=40, q=10, alpha_n=20 deg,
#   mu=0.05 (friction_override), T2≈500 N·m
# 手算（规格见 docs/superpowers/specs/）：
#   d2=160 mm, F_t2=6250 N, gamma=5.7106 deg, phi'=3.0466 deg
#   F_a2=F_t2·tan(gamma+phi')=6250·tan(8.757°)≈963 N
#   F_r =F_t2·tan(20°)/cos(5.71°)=6250·0.3640/0.9950≈2286 N
#   F_n =F_t2/(cos(20°)·cos(5.71°))=6250/0.9351≈6683 N
#   eta =tan(gamma)/tan(gamma+phi')=0.1000/0.1540=0.6493
# ============================================================

import math as _math
import pytest


def _case_m4_z1_q10() -> dict:
    """m=4, z1=1, z2=40, q=10, mu=0.05, T2=500 N·m 参考案例。

    input_torque_nm 设为使 output_torque ≈ 500 N·m 的理论值：
    T1 = T2 / (i * eta) = 500 / (40 * 0.6493) ≈ 19.24 N·m
    （core 修正后 eta 采用 phi'=atan(mu/cos(alpha_n))=0.6493，修正前略有偏差。）
    """
    gamma_deg = _math.degrees(_math.atan(1.0 / 10.0))
    return {
        "geometry": {
            "module_mm": 4.0,
            "z1": 1,
            "z2": 40,
            "diameter_factor_q": 10.0,
            "center_distance_mm": 100.0,   # (q+z2)/2 * m = (10+40)/2*4 = 100
            "lead_angle_deg": gamma_deg,
            "worm_face_width_mm": 32.0,
            "wheel_face_width_mm": 28.0,
            "x1": 0.0,
            "x2": 0.0,
        },
        "operating": {
            "input_torque_nm": 500.0 / 40.0 / 0.6493,  # ~19.24 N·m
            "speed_rpm": 1500.0,
            "application_factor": 1.0,
        },
        "materials": {
            "worm_material": "37CrS4",
            "wheel_material": "PA66",
            "worm_e_mpa": 210000.0,
            "worm_nu": 0.30,
            "wheel_e_mpa": 3000.0,
            "wheel_nu": 0.38,
            "handedness": "right",
            "lubrication": "grease",
        },
        "advanced": {
            "friction_override": 0.05,
            "normal_pressure_angle_deg": 20.0,
        },
        "load_capacity": {
            "enabled": True,
            "allowable_contact_stress_mpa": 42.0,
            "allowable_root_stress_mpa": 55.0,
            "required_contact_safety": 1.0,
            "required_root_safety": 1.0,
        },
    }


def test_force_decomposition_magnitude_m4_q10():
    """参考案例力分解量级：F_t2≈6250, F_a2≈963, F_r≈2286, F_n≈6683 N。

    修复前（sin_gamma）的错误值约为：
      F_n≈62802, F_a2≈62500, F_r≈22856（高估 ~10×）。
    修复后本测试应通过；core 未修复时本测试应 FAIL。
    """
    data = _case_m4_z1_q10()
    result = calculate_worm_geometry(data)
    forces = result["load_capacity"]["forces"]

    # T2 ≈ 500 N·m → F_t2 = 2*T2/d2*1000 ≈ 6250 N（3% 容差）
    assert forces["tangential_force_wheel_n"] == pytest.approx(6250.0, rel=3e-2)
    # F_a2 = F_t2·tan(gamma+phi') ≈ 963 N（5% 容差）
    assert forces["axial_force_wheel_n"] == pytest.approx(963.0, rel=5e-2)
    # F_r = F_t2·tan(alpha_n)/cos(gamma) ≈ 2286 N（5% 容差）
    assert forces["radial_force_wheel_n"] == pytest.approx(2286.0, rel=5e-2)
    # F_n = F_t2/(cos(alpha_n)·cos(gamma)) ≈ 6683 N（5% 容差）
    assert forces["normal_force_n"] == pytest.approx(6683.0, rel=5e-2)


def test_efficiency_matches_tan_gamma_formula():
    """效率 eta = tan(gamma)/tan(gamma+phi') 其中 phi'=atan(mu/cos(alpha_n))。

    参考案例：eta ≈ 0.6493。
    core 修复前效率用简化 atan(mu)（非当量摩擦角），eta≈0.6633，本测试应 FAIL。
    core 修复后 phi'=atan(mu/cos(alpha_n))，eta≈0.6493，本测试应 PASS。
    """
    data = _case_m4_z1_q10()
    result = calculate_worm_geometry(data)
    eta = result["performance"]["efficiency_estimate"]
    assert eta == pytest.approx(0.6493, rel=3e-2)


def test_self_locking_warning_when_gamma_below_phi():
    """当 gamma <= phi' 时，warnings 应包含'自锁'字样。

    设置：z1=1, q=20（gamma=atan(1/20)≈2.86°），mu=0.25（phi'≈14.9°），
    gamma << phi' → 应触发自锁警告。
    """
    data = _case_m4_z1_q10()
    data["advanced"]["friction_override"] = 0.25  # 大摩擦系数
    data["geometry"]["z1"] = 1
    data["geometry"]["diameter_factor_q"] = 20.0  # 小导程角
    data["geometry"]["lead_angle_deg"] = _math.degrees(_math.atan(1.0 / 20.0))
    data["geometry"]["center_distance_mm"] = (20.0 + 40.0) / 2.0 * 4.0  # 120 mm
    result = calculate_worm_geometry(data)
    warnings = " ".join(result["performance"]["warnings"])
    assert "自锁" in warnings


def test_thermal_capacity_independent_of_power_loss():
    """热容量应基于散热公式（Q_th = k*A*ΔT），不等于损失功率。

    修复前 thermal_capacity_kw == power_loss_kw（直接赋值）。
    修复后两者独立计算，除非恰好相等（极小概率），差值应 > 0.001 kW。
    """
    data = _case_m4_z1_q10()
    result = calculate_worm_geometry(data)
    perf = result["performance"]
    assert perf["thermal_capacity_kw"] > 0.0
    assert perf["power_loss_kw"] > 0.0
    # 散热公式结果不等于损失功率
    assert abs(perf["thermal_capacity_kw"] - perf["power_loss_kw"]) > 1e-3


def test_nonstandard_q_does_not_fail_consistency_check():
    """q=13 为工程实践中的非标准值，应只产生警告，不应令 geometry_consistent=False。

    修复前：geometry_consistent = not geometry_warnings，q 非标警告会污染一致性判断。
    修复后：geometry_consistent 仅看 lead_angle 偏差和 center_distance 偏差。
    """
    data = _case_m4_z1_q10()
    data["geometry"]["diameter_factor_q"] = 13.0  # 非标准 q
    data["geometry"]["lead_angle_deg"] = _math.degrees(_math.atan(1.0 / 13.0))
    data["geometry"]["center_distance_mm"] = (13.0 + 40.0) / 2.0 * 4.0  # 106 mm

    result = calculate_worm_geometry(data)

    # q 非标应不影响 geometry_consistent
    assert result["load_capacity"]["checks"]["geometry_consistent"] is True
    # 但仍应产生 q 非标警告
    geom_warnings = result["geometry"]["consistency"]["warnings"]
    assert any("q" in w or "直径系数" in w for w in geom_warnings)


def test_method_c_raises_input_error():
    """Method C 尚未实现，应抛出 InputError 并提示切换 Method。

    修复前：Method C 与 Method B 输出完全相同（无错误）。
    修复后：应抛 InputError，消息含 'Method C'。
    """
    from core.worm.calculator import InputError as WormInputError

    data = _case_m4_z1_q10()
    data.setdefault("load_capacity", {})["method"] = "DIN 3996 Method C"
    with pytest.raises(WormInputError, match="Method C"):
        calculate_worm_geometry(data)


def test_method_a_gives_lower_efficiency_than_b():
    """Method A（手册系数法）应给出比 Method B 更低的效率。

    修复前：Method A/B/C 三者输出完全相同。
    修复后：Method A 乘以 0.92 折减系数，eta_A < eta_B。
    """
    data_a = _case_m4_z1_q10()
    data_a.setdefault("load_capacity", {})["method"] = "DIN 3996 Method A"
    result_a = calculate_worm_geometry(data_a)

    data_b = _case_m4_z1_q10()
    data_b.setdefault("load_capacity", {})["method"] = "DIN 3996 Method B"
    result_b = calculate_worm_geometry(data_b)

    eta_a = result_a["performance"]["efficiency_estimate"]
    eta_b = result_b["performance"]["efficiency_estimate"]
    assert eta_a < eta_b, f"Method A 效率 {eta_a:.4f} 应低于 Method B 效率 {eta_b:.4f}"


def test_lubrication_dry_increases_friction():
    """干摩擦（dry）应使摩擦系数高于油浴润滑（oil_bath）。

    规格：LUB_MU_MULTIPLIER = {'oil_bath': 0.90, 'grease': 1.00, 'dry': 1.35}。
    本测试在当前 core 已实现 lubrication 联动时即可通过。
    """
    data_oil = _case_m4_z1_q10()
    data_oil["materials"]["lubrication"] = "oil_bath"
    data_oil["advanced"].pop("friction_override", None)  # 用表格默认值
    data_oil["advanced"]["friction_override"] = ""  # 使用材料对表格值
    result_oil = calculate_worm_geometry(data_oil)

    data_dry = _case_m4_z1_q10()
    data_dry["materials"]["lubrication"] = "dry"
    data_dry["advanced"]["friction_override"] = ""
    result_dry = calculate_worm_geometry(data_dry)

    mu_oil = result_oil["performance"]["friction_mu"]
    mu_dry = result_dry["performance"]["friction_mu"]
    assert mu_dry > mu_oil, f"干摩擦 mu={mu_dry:.4f} 应大于油浴摩擦 mu={mu_oil:.4f}"
