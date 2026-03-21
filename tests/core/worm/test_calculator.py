import unittest

from core.worm.calculator import InputError, calculate_worm_geometry


class WormCalculatorTests(unittest.TestCase):
    @staticmethod
    def _base_payload() -> dict:
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
            },
            "operating": {
                "power_kw": 3.0,
                "speed_rpm": 1450.0,
                "application_factor": 1.25,
                "torque_ripple_percent": 0.0,
            },
            "materials": {
                "worm_material": "20CrMnTi",
                "wheel_material": "ZCuSn12Ni2",
                "worm_e_mpa": 206000.0,
                "worm_nu": 0.30,
                "wheel_e_mpa": 110000.0,
                "wheel_nu": 0.34,
            },
            "advanced": {
                "friction_override": "",
                "normal_pressure_angle_deg": 20.0,
            },
            "load_capacity": {
                "enabled": True,
                "method": "DIN 3996 Method B",
                "allowable_contact_stress_mpa": 520.0,
                "allowable_root_stress_mpa": 90.0,
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
                    "center_distance_mm": 84.0,
                    "diameter_factor_q": 10.0,
                    "lead_angle_deg": 20.0,
                },
                "operating": {
                    "power_kw": 3.0,
                    "speed_rpm": 1450.0,
                },
                "materials": {
                    "worm_material": "20CrMnTi",
                    "wheel_material": "ZCuSn12Ni2",
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

        overridden = calculate_worm_geometry(payload)

        self.assertAlmostEqual(overridden["performance"]["friction_mu"], 0.09, places=9)
        self.assertLess(
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


if __name__ == "__main__":
    unittest.main()
