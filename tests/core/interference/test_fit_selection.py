import unittest

from core.interference import InputError
from core.interference.fit_selection import (
    derive_interference_from_deviations,
    derive_interference_from_preferred_fit,
)


class FitSelectionTests(unittest.TestCase):
    def test_preferred_fit_h7_s6_at_50mm_matches_curated_iso286_window(self) -> None:
        result = derive_interference_from_preferred_fit(
            fit_name="H7/s6",
            nominal_diameter_mm=50.0,
        )

        self.assertEqual(result["mode"], "preferred_fit")
        self.assertEqual(result["fit_name"], "H7/s6")
        self.assertEqual(result["delta_min_um"], 18.0)
        self.assertEqual(result["delta_max_um"], 59.0)

    def test_preferred_fit_rejects_nominal_diameter_outside_curated_range(self) -> None:
        with self.assertRaises(InputError):
            derive_interference_from_preferred_fit(
                fit_name="H7/s6",
                nominal_diameter_mm=55.0,
            )

    def test_preferred_fit_band_edges_select_expected_h7_s6_windows(self) -> None:
        result_10 = derive_interference_from_preferred_fit(
            fit_name="H7/s6",
            nominal_diameter_mm=10.0,
        )
        result_18 = derive_interference_from_preferred_fit(
            fit_name="H7/s6",
            nominal_diameter_mm=18.0,
        )

        self.assertEqual(result_10["delta_min_um"], 4.0)
        self.assertEqual(result_10["delta_max_um"], 20.0)
        self.assertEqual(result_18["delta_min_um"], 7.0)
        self.assertEqual(result_18["delta_max_um"], 27.0)

    def test_preferred_fit_h7_u6_mid_band_matches_curated_window(self) -> None:
        result = derive_interference_from_preferred_fit(
            fit_name="H7/u6",
            nominal_diameter_mm=35.0,
        )

        self.assertEqual(result["delta_min_um"], 27.0)
        self.assertEqual(result["delta_max_um"], 61.0)

    def test_user_defined_deviations_can_be_converted_to_interference_window(self) -> None:
        result = derive_interference_from_deviations(
            shaft_upper_um=35.0,
            shaft_lower_um=20.0,
            hub_upper_um=-10.0,
            hub_lower_um=-20.0,
        )

        self.assertEqual(result["mode"], "user_defined_deviations")
        self.assertEqual(result["delta_min_um"], 30.0)
        self.assertEqual(result["delta_max_um"], 55.0)

    def test_invalid_deviation_order_is_rejected(self) -> None:
        with self.assertRaises(InputError):
            derive_interference_from_deviations(
                shaft_upper_um=10.0,
                shaft_lower_um=20.0,
                hub_upper_um=-10.0,
                hub_lower_um=-20.0,
            )

    def test_transition_or_clearance_fit_is_rejected_for_interference_module(self) -> None:
        with self.assertRaises(InputError):
            derive_interference_from_deviations(
                shaft_upper_um=10.0,
                shaft_lower_um=-5.0,
                hub_upper_um=5.0,
                hub_lower_um=-5.0,
            )


if __name__ == "__main__":
    unittest.main()
