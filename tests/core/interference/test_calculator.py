import unittest

from core.interference.calculator import InputError, calculate_interference_fit


class InterferenceFitCalculatorTests(unittest.TestCase):
    def test_nominal_case_outputs_pressure_torque_and_curve(self) -> None:
        result = calculate_interference_fit(
            {
                "geometry": {
                    "shaft_d_mm": 40.0,
                    "hub_outer_d_mm": 80.0,
                    "fit_length_mm": 45.0,
                },
                "materials": {
                    "shaft_e_mpa": 210000.0,
                    "shaft_nu": 0.30,
                    "shaft_yield_mpa": 600.0,
                    "hub_e_mpa": 210000.0,
                    "hub_nu": 0.30,
                    "hub_yield_mpa": 320.0,
                },
                "fit": {
                    "delta_min_um": 20.0,
                    "delta_max_um": 45.0,
                },
                "friction": {
                    "mu_static": 0.14,
                    "mu_assembly": 0.12,
                },
                "loads": {
                    "torque_required_nm": 350.0,
                    "axial_force_required_n": 0.0,
                },
            }
        )

        self.assertGreater(result["pressure_mpa"]["p_min"], 0.0)
        self.assertGreater(result["pressure_mpa"]["p_max"], result["pressure_mpa"]["p_min"])
        self.assertGreater(result["capacity"]["torque_min_nm"], 0.0)
        self.assertGreater(result["capacity"]["torque_max_nm"], result["capacity"]["torque_min_nm"])
        self.assertGreater(result["assembly"]["press_force_max_n"], result["assembly"]["press_force_min_n"])
        self.assertTrue(result["checks"]["torque_ok"])
        self.assertTrue(result["overall_pass"])

        curve = result["press_force_curve"]
        self.assertEqual(len(curve["interference_um"]), 41)
        self.assertEqual(len(curve["force_n"]), 41)
        self.assertGreater(curve["force_n"][-1], curve["force_n"][0])

    def test_invalid_geometry_is_rejected(self) -> None:
        with self.assertRaises(InputError):
            calculate_interference_fit(
                {
                    "geometry": {
                        "shaft_d_mm": 70.0,
                        "hub_outer_d_mm": 60.0,
                        "fit_length_mm": 30.0,
                    },
                    "materials": {
                        "shaft_e_mpa": 210000.0,
                        "shaft_nu": 0.30,
                        "shaft_yield_mpa": 600.0,
                        "hub_e_mpa": 210000.0,
                        "hub_nu": 0.30,
                        "hub_yield_mpa": 320.0,
                    },
                    "fit": {
                        "delta_min_um": 10.0,
                        "delta_max_um": 20.0,
                    },
                    "friction": {
                        "mu_static": 0.12,
                        "mu_assembly": 0.10,
                    },
                    "loads": {
                        "torque_required_nm": 100.0,
                        "axial_force_required_n": 0.0,
                    },
                }
            )

    def test_required_interference_is_reported(self) -> None:
        result = calculate_interference_fit(
            {
                "geometry": {
                    "shaft_d_mm": 35.0,
                    "hub_outer_d_mm": 75.0,
                    "fit_length_mm": 40.0,
                },
                "materials": {
                    "shaft_e_mpa": 210000.0,
                    "shaft_nu": 0.30,
                    "shaft_yield_mpa": 560.0,
                    "hub_e_mpa": 205000.0,
                    "hub_nu": 0.29,
                    "hub_yield_mpa": 300.0,
                },
                "fit": {
                    "delta_min_um": 16.0,
                    "delta_max_um": 36.0,
                },
                "friction": {
                    "mu_static": 0.13,
                    "mu_assembly": 0.11,
                },
                "loads": {
                    "torque_required_nm": 260.0,
                    "axial_force_required_n": 4200.0,
                },
            }
        )

        self.assertGreater(result["required"]["delta_required_um"], 0.0)
        self.assertGreaterEqual(result["required"]["delta_required_um"], 0.0)
        self.assertIn("messages", result)

    def test_roughness_reduces_effective_capacity(self) -> None:
        base_input = {
            "geometry": {
                "shaft_d_mm": 40.0,
                "hub_outer_d_mm": 80.0,
                "fit_length_mm": 45.0,
            },
            "materials": {
                "shaft_e_mpa": 210000.0,
                "shaft_nu": 0.30,
                "shaft_yield_mpa": 600.0,
                "hub_e_mpa": 210000.0,
                "hub_nu": 0.30,
                "hub_yield_mpa": 320.0,
            },
            "fit": {
                "delta_min_um": 30.0,
                "delta_max_um": 50.0,
            },
            "friction": {
                "mu_static": 0.14,
                "mu_assembly": 0.12,
            },
            "loads": {
                "torque_required_nm": 250.0,
                "axial_force_required_n": 0.0,
            },
        }

        result_no_rough = calculate_interference_fit(base_input)
        input_with_rough = dict(base_input)
        input_with_rough["roughness"] = {
            "shaft_rz_um": 10.0,
            "hub_rz_um": 10.0,
            "smoothing_factor": 0.4,
        }
        result_rough = calculate_interference_fit(input_with_rough)

        self.assertLess(result_rough["pressure_mpa"]["p_min"], result_no_rough["pressure_mpa"]["p_min"])
        self.assertLess(result_rough["capacity"]["torque_min_nm"], result_no_rough["capacity"]["torque_min_nm"])
        self.assertGreater(result_rough["roughness"]["subsidence_um"], 0.0)


if __name__ == "__main__":
    unittest.main()
