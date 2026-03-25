import math
import unittest

from core.interference.assembly import calculate_assembly_detail


def make_context() -> dict[str, float]:
    return {
        "shaft_d_mm": 50.0,
        "fit_length_mm": 20.0,
        "delta_min_um": 18.0,
        "delta_mean_um": 35.0,
        "delta_max_um": 59.0,
        "p_min_mpa": 46.0,
        "p_mean_mpa": 72.0,
        "p_max_mpa": 118.0,
        "contact_area_mm2": math.pi * 50.0 * 20.0,
        "mu_assembly": 0.12,
        "mu_torque": 0.15,
        "mu_axial": 0.15,
    }


class AssemblyDetailTests(unittest.TestCase):
    def test_shrink_fit_required_hub_temperature_rises_with_required_clearance(self) -> None:
        context = make_context()

        low = calculate_assembly_detail(
            {
                "method": "shrink_fit",
                "room_temperature_c": 20.0,
                "shaft_temperature_c": 20.0,
                "clearance_mode": "direct_value",
                "clearance_um": 20.0,
                "alpha_hub_1e6_per_c": 11.0,
                "alpha_shaft_1e6_per_c": 11.0,
                "hub_temp_limit_c": 250.0,
            },
            context,
        )
        high = calculate_assembly_detail(
            {
                "method": "shrink_fit",
                "room_temperature_c": 20.0,
                "shaft_temperature_c": 20.0,
                "clearance_mode": "direct_value",
                "clearance_um": 40.0,
                "alpha_hub_1e6_per_c": 11.0,
                "alpha_shaft_1e6_per_c": 11.0,
                "hub_temp_limit_c": 250.0,
            },
            context,
        )

        self.assertEqual(low["method"], "shrink_fit")
        self.assertGreater(
            high["shrink_fit"]["required_hub_temperature_c"],
            low["shrink_fit"]["required_hub_temperature_c"],
        )

    def test_shrink_fit_required_expansion_uses_max_interference_side(self) -> None:
        context = make_context()

        result = calculate_assembly_detail(
            {
                "method": "shrink_fit",
                "room_temperature_c": 20.0,
                "shaft_temperature_c": 20.0,
                "clearance_mode": "direct_value",
                "clearance_um": 20.0,
                "alpha_hub_1e6_per_c": 11.0,
                "alpha_shaft_1e6_per_c": 11.0,
            },
            context,
        )

        self.assertAlmostEqual(
            result["shrink_fit"]["required_expansion_um"],
            context["delta_max_um"] + 20.0,
            places=6,
        )

    def test_force_fit_pressing_force_uses_max_pressure_side(self) -> None:
        context = make_context()

        result = calculate_assembly_detail(
            {
                "method": "force_fit",
                "mu_press_in": 0.08,
                "mu_press_out": 0.06,
            },
            context,
        )

        expected_press_in = math.pi * 50.0 * 20.0 * 0.08 * 118.0
        expected_press_out = math.pi * 50.0 * 20.0 * 0.06 * 118.0

        self.assertEqual(result["method"], "force_fit")
        self.assertAlmostEqual(result["force_fit"]["press_in_force_n"], expected_press_in, places=6)
        self.assertAlmostEqual(result["force_fit"]["press_out_force_n"], expected_press_out, places=6)

    def test_manual_only_mode_keeps_generic_press_force_trace(self) -> None:
        context = make_context()

        result = calculate_assembly_detail({"method": "manual_only"}, context)

        self.assertEqual(result["method"], "manual_only")
        self.assertIn("generic_press_force", result)
        self.assertIn("service_friction", result)


if __name__ == "__main__":
    unittest.main()
