import unittest

from core.worm.calculator import InputError, calculate_worm_geometry


class WormCalculatorTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
