import unittest

from core.hertz.calculator import InputError, calculate_hertz_contact


class HertzContactCalculatorTests(unittest.TestCase):
    def test_line_contact_case_outputs_pressure_and_check(self) -> None:
        result = calculate_hertz_contact(
            {
                "geometry": {
                    "contact_mode": "line",
                    "r1_mm": 30.0,
                    "r2_mm": 0.0,
                    "length_mm": 20.0,
                },
                "materials": {
                    "e1_mpa": 210000.0,
                    "nu1": 0.30,
                    "e2_mpa": 210000.0,
                    "nu2": 0.30,
                },
                "loads": {
                    "normal_force_n": 12000.0,
                },
                "checks": {
                    "allowable_p0_mpa": 1500.0,
                },
            }
        )

        self.assertGreater(result["contact"]["p0_mpa"], 0.0)
        self.assertGreater(result["contact"]["semi_width_mm"], 0.0)
        self.assertTrue(result["checks"]["contact_stress_ok"])

    def test_point_contact_case_outputs_contact_radius(self) -> None:
        result = calculate_hertz_contact(
            {
                "geometry": {
                    "contact_mode": "point",
                    "r1_mm": 15.0,
                    "r2_mm": 0.0,
                    "length_mm": 10.0,
                },
                "materials": {
                    "e1_mpa": 206000.0,
                    "nu1": 0.30,
                    "e2_mpa": 206000.0,
                    "nu2": 0.30,
                },
                "loads": {
                    "normal_force_n": 2500.0,
                },
                "checks": {
                    "allowable_p0_mpa": 1800.0,
                },
            }
        )

        self.assertGreater(result["contact"]["p0_mpa"], 0.0)
        self.assertGreater(result["contact"]["contact_radius_mm"], 0.0)

    def test_invalid_radius_is_rejected(self) -> None:
        with self.assertRaises(InputError):
            calculate_hertz_contact(
                {
                    "geometry": {
                        "contact_mode": "line",
                        "r1_mm": 0.0,
                        "r2_mm": 0.0,
                        "length_mm": 20.0,
                    },
                    "materials": {
                        "e1_mpa": 210000.0,
                        "nu1": 0.30,
                        "e2_mpa": 210000.0,
                        "nu2": 0.30,
                    },
                    "loads": {
                        "normal_force_n": 10000.0,
                    },
                    "checks": {
                        "allowable_p0_mpa": 1000.0,
                    },
                }
            )


if __name__ == "__main__":
    unittest.main()
