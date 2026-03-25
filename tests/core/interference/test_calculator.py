import unittest

from core.interference.calculator import InputError, calculate_interference_fit


def make_case() -> dict:
    return {
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
            "mu_torque": 0.14,
            "mu_axial": 0.14,
            "mu_assembly": 0.12,
        },
        "loads": {
            "torque_required_nm": 350.0,
            "axial_force_required_n": 0.0,
            "radial_force_required_n": 0.0,
            "bending_moment_required_nm": 0.0,
            "application_factor_ka": 1.0,
        },
    }


class InterferenceFitCalculatorTests(unittest.TestCase):
    def test_nominal_case_outputs_pressure_torque_and_curve(self) -> None:
        result = calculate_interference_fit(make_case())

        self.assertGreater(result["pressure_mpa"]["p_min"], 0.0)
        self.assertGreater(result["pressure_mpa"]["p_mean"], result["pressure_mpa"]["p_min"])
        self.assertGreater(result["pressure_mpa"]["p_max"], result["pressure_mpa"]["p_min"])
        self.assertGreater(result["capacity"]["torque_min_nm"], 0.0)
        self.assertGreater(result["capacity"]["torque_mean_nm"], result["capacity"]["torque_min_nm"])
        self.assertGreater(result["capacity"]["torque_max_nm"], result["capacity"]["torque_min_nm"])
        self.assertGreater(result["assembly"]["press_force_max_n"], result["assembly"]["press_force_min_n"])
        self.assertTrue(result["checks"]["torque_ok"])
        self.assertTrue(result["checks"]["gaping_ok"])
        self.assertTrue(result["overall_pass"])

        curve = result["press_force_curve"]
        self.assertEqual(len(curve["interference_um"]), 41)
        self.assertEqual(len(curve["force_n"]), 41)
        self.assertGreater(curve["force_n"][-1], curve["force_n"][0])
        self.assertIn("additional_pressure_mpa", result)

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

    def test_invalid_hollow_shaft_geometry_is_rejected(self) -> None:
        data = make_case()
        data["geometry"]["shaft_inner_d_mm"] = 40.0

        with self.assertRaises(InputError):
            calculate_interference_fit(data)

    def test_required_interference_is_reported(self) -> None:
        data = make_case()
        data["geometry"] = {
            "shaft_d_mm": 35.0,
            "hub_outer_d_mm": 75.0,
            "fit_length_mm": 40.0,
        }
        data["materials"] = {
            "shaft_e_mpa": 210000.0,
            "shaft_nu": 0.30,
            "shaft_yield_mpa": 560.0,
            "hub_e_mpa": 205000.0,
            "hub_nu": 0.29,
            "hub_yield_mpa": 300.0,
        }
        data["fit"] = {
            "delta_min_um": 16.0,
            "delta_max_um": 36.0,
        }
        data["friction"] = {
            "mu_torque": 0.13,
            "mu_axial": 0.13,
            "mu_assembly": 0.11,
        }
        data["loads"] = {
            "torque_required_nm": 260.0,
            "axial_force_required_n": 4200.0,
            "radial_force_required_n": 0.0,
            "bending_moment_required_nm": 0.0,
            "application_factor_ka": 1.0,
        }
        result = calculate_interference_fit(data)

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

    def test_application_factor_increases_required_interference(self) -> None:
        base = make_case()
        result_base = calculate_interference_fit(base)

        factored = make_case()
        factored["loads"]["application_factor_ka"] = 1.5
        result_factored = calculate_interference_fit(factored)

        self.assertGreater(
            result_factored["required"]["delta_required_um"],
            result_base["required"]["delta_required_um"],
        )

    def test_hollow_shaft_reduces_pressure_and_capacity_and_updates_model_type(self) -> None:
        solid = make_case()
        solid_result = calculate_interference_fit(solid)

        hollow = make_case()
        hollow["geometry"]["shaft_inner_d_mm"] = 20.0
        hollow_result = calculate_interference_fit(hollow)

        self.assertEqual(hollow_result["model"]["type"], "cylindrical_interference_hollow_shaft")
        self.assertGreater(
            hollow_result["derived"]["radial_compliance_shaft_mm_per_mpa"],
            solid_result["derived"]["radial_compliance_shaft_mm_per_mpa"],
        )
        self.assertLess(hollow_result["pressure_mpa"]["p_min"], solid_result["pressure_mpa"]["p_min"])
        self.assertLess(
            hollow_result["capacity"]["torque_min_nm"],
            solid_result["capacity"]["torque_min_nm"],
        )

    def test_slip_safety_factor_increases_required_interference_and_can_exhaust_fit_window(self) -> None:
        base = make_case()
        base["loads"]["torque_required_nm"] = 870.0
        base["checks"] = {
            "slip_safety_min": 1.0,
            "stress_safety_min": 1.2,
        }

        result_low = calculate_interference_fit(base)

        stricter = make_case()
        stricter["loads"]["torque_required_nm"] = 1000.0
        stricter["checks"] = {
            "slip_safety_min": 1.5,
            "stress_safety_min": 1.2,
        }
        result_high = calculate_interference_fit(stricter)

        self.assertGreater(
            result_high["required"]["p_required_mpa"],
            result_low["required"]["p_required_mpa"],
        )
        self.assertGreater(
            result_high["required"]["delta_required_um"],
            result_low["required"]["delta_required_um"],
        )
        self.assertTrue(result_low["checks"]["fit_range_ok"])
        self.assertFalse(result_high["checks"]["fit_range_ok"])

    def test_combined_torque_and_axial_usage_can_fail_overall_even_if_single_checks_pass(self) -> None:
        data = make_case()
        data["loads"]["torque_required_nm"] = 300.0
        data["loads"]["axial_force_required_n"] = 22000.0
        data["checks"] = {
            "slip_safety_min": 1.2,
            "stress_safety_min": 1.2,
        }

        result = calculate_interference_fit(data)

        self.assertTrue(result["checks"]["torque_ok"])
        self.assertTrue(result["checks"]["axial_ok"])
        self.assertFalse(result["checks"]["combined_ok"])
        self.assertFalse(result["overall_pass"])

    def test_force_fit_mode_is_exposed_in_assembly_detail(self) -> None:
        data = make_case()
        data["assembly"] = {
            "method": "force_fit",
            "mu_press_in": 0.08,
            "mu_press_out": 0.06,
        }

        result = calculate_interference_fit(data)

        self.assertEqual(result["assembly_detail"]["method"], "force_fit")
        self.assertIn("force_fit", result["assembly_detail"])
        self.assertGreater(result["assembly_detail"]["force_fit"]["press_in_force_n"], 0.0)

    def test_force_fit_mode_uses_press_in_friction_for_main_press_force_summary(self) -> None:
        data = make_case()
        data["assembly"] = {
            "method": "force_fit",
            "mu_press_in": 0.08,
            "mu_press_out": 0.06,
        }

        result = calculate_interference_fit(data)

        area = result["derived"]["contact_area_mm2"]
        p_min = result["pressure_mpa"]["p_min"]
        p_mean = result["pressure_mpa"]["p_mean"]
        p_max = result["pressure_mpa"]["p_max"]

        self.assertAlmostEqual(result["assembly"]["press_force_min_n"], 0.08 * p_min * area, places=6)
        self.assertAlmostEqual(result["assembly"]["press_force_mean_n"], 0.08 * p_mean * area, places=6)
        self.assertAlmostEqual(result["assembly"]["press_force_max_n"], 0.08 * p_max * area, places=6)
        self.assertAlmostEqual(
            result["assembly"]["press_force_max_n"],
            result["assembly_detail"]["force_fit"]["press_in_force_n"],
            places=6,
        )

    def test_repeated_load_block_reports_applicable_case(self) -> None:
        data = make_case()
        data["advanced"] = {
            "repeated_load_mode": "on",
        }
        data["loads"]["torque_required_nm"] = 120.0

        result = calculate_interference_fit(data)

        self.assertTrue(result["repeated_load"]["enabled"])
        self.assertTrue(result["repeated_load"]["applicable"])
        self.assertGreater(result["repeated_load"]["max_transferable_torque_nm"], 0.0)
        self.assertFalse(result["repeated_load"]["fretting_risk"])

    def test_repeated_load_block_is_not_applicable_for_hollow_shaft(self) -> None:
        data = make_case()
        data["geometry"]["shaft_inner_d_mm"] = 20.0
        data["advanced"] = {
            "repeated_load_mode": "on",
        }

        result = calculate_interference_fit(data)

        self.assertTrue(result["repeated_load"]["enabled"])
        self.assertFalse(result["repeated_load"]["applicable"])
        self.assertIn("hollow shaft", " ".join(result["repeated_load"]["notes"]).lower())

    def test_repeated_load_block_reports_not_applicable_case(self) -> None:
        data = make_case()
        data["geometry"]["fit_length_mm"] = 8.0
        data["advanced"] = {
            "repeated_load_mode": "on",
        }

        result = calculate_interference_fit(data)

        self.assertTrue(result["repeated_load"]["enabled"])
        self.assertFalse(result["repeated_load"]["applicable"])
        self.assertIn("not applicable", " ".join(result["repeated_load"]["notes"]).lower())

    def test_fretting_block_is_exposed_when_new_mode_is_enabled(self) -> None:
        data = make_case()
        data["fretting"] = {
            "mode": "on",
            "load_spectrum": "pulsating",
            "duty_severity": "medium",
            "surface_condition": "dry",
            "importance_level": "important",
        }

        result = calculate_interference_fit(data)

        self.assertIn("fretting", result)
        self.assertTrue(result["fretting"]["enabled"])
        self.assertIn(result["fretting"]["risk_level"], {"low", "medium", "high", "not_applicable"})

    def test_fretting_can_be_high_risk_without_changing_base_overall_pass(self) -> None:
        data = make_case()
        data["loads"]["axial_force_required_n"] = 12000.0
        data["checks"] = {
            "slip_safety_min": 1.2,
            "stress_safety_min": 1.2,
        }
        data["fretting"] = {
            "mode": "on",
            "load_spectrum": "reversing",
            "duty_severity": "heavy",
            "surface_condition": "dry",
            "importance_level": "critical",
        }

        result = calculate_interference_fit(data)

        self.assertTrue(result["overall_pass"])
        self.assertEqual(result["fretting"]["risk_level"], "high")

    def test_legacy_repeated_load_switch_still_enables_fretting_assessment(self) -> None:
        data = make_case()
        data["advanced"] = {
            "repeated_load_mode": "on",
        }

        result = calculate_interference_fit(data)

        self.assertIn("fretting", result)
        self.assertTrue(result["fretting"]["enabled"])

    def test_gaping_check_fails_when_radial_and_bending_loads_are_high(self) -> None:
        data = make_case()
        data["loads"]["radial_force_required_n"] = 36000.0
        data["loads"]["bending_moment_required_nm"] = 900.0

        result = calculate_interference_fit(data)

        self.assertFalse(result["checks"]["gaping_ok"])
        self.assertGreater(
            result["additional_pressure_mpa"]["p_gap"],
            result["pressure_mpa"]["p_min"],
        )

    def test_legacy_mu_static_is_still_supported(self) -> None:
        data = make_case()
        data["friction"] = {
            "mu_static": 0.14,
            "mu_assembly": 0.12,
        }

        result = calculate_interference_fit(data)

        self.assertGreater(result["capacity"]["torque_min_nm"], 0.0)
        self.assertGreater(result["capacity"]["axial_min_n"], 0.0)


if __name__ == "__main__":
    unittest.main()
