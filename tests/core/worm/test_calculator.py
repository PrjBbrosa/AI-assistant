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
                "power_kw": 3.0,
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
                    "power_kw": 3.0,
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
                        "power_kw": 3.0,
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
                    "power_kw": 4.0,
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
        self.assertEqual(len(curve["load_factor"]), len(curve["thermal_capacity_kw"]))
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
                    "power_kw": 3.0,
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
        output_power_kw = performance["output_power_kw"]
        self.assertAlmostEqual(output_power_kw, payload["operating"]["power_kw"] * performance["efficiency_estimate"], places=9)
        self.assertAlmostEqual(
            performance["power_loss_kw"],
            payload["operating"]["power_kw"] - output_power_kw,
            places=9,
        )
        self.assertAlmostEqual(
            performance["output_torque_nm"],
            9550.0 * output_power_kw / result["geometry"]["wheel_speed_rpm"],
            places=9,
        )

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

    def test_thermal_capacity_equals_power_loss(self) -> None:
        payload = self._base_payload()
        result = calculate_worm_geometry(payload)
        perf = result["performance"]
        self.assertAlmostEqual(perf["thermal_capacity_kw"], perf["power_loss_kw"], places=9)

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


if __name__ == "__main__":
    unittest.main()
