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


import pytest


def _base_line_input():
    return {
        "geometry": {"contact_mode": "line", "r1_mm": 50.0, "r2_mm": 100.0, "length_mm": 20.0},
        "materials": {"e1_mpa": 210000, "nu1": 0.30, "e2_mpa": 210000, "nu2": 0.30},
        "loads": {"normal_force_n": 5000.0},
        "checks": {"allowable_p0_mpa": 1500.0},
    }


def _base_point_input():
    return {
        "geometry": {"contact_mode": "point", "r1_mm": 25.0, "r2_mm": 50.0},
        "materials": {"e1_mpa": 210000, "nu1": 0.30, "e2_mpa": 210000, "nu2": 0.30},
        "loads": {"normal_force_n": 1000.0},
        "checks": {"allowable_p0_mpa": 3000.0},
    }


def test_nu_zero_rejected():
    data = _base_line_input()
    data["materials"]["nu1"] = 0.0
    with pytest.raises(InputError):
        calculate_hertz_contact(data)


def test_nu_half_rejected():
    data = _base_line_input()
    data["materials"]["nu1"] = 0.5
    with pytest.raises(InputError):
        calculate_hertz_contact(data)


def test_nu_valid_boundaries():
    for nu in (0.01, 0.49):
        data = _base_line_input()
        data["materials"]["nu1"] = nu
        data["materials"]["nu2"] = nu
        result = calculate_hertz_contact(data)
        assert result["contact"]["p0_mpa"] > 0.0


def test_single_plane_line_contact():
    data = _base_line_input()
    data["geometry"]["r2_mm"] = 0.0  # r2=0 表示平面
    result = calculate_hertz_contact(data)
    assert result["contact"]["semi_width_mm"] > 0.0
    assert result["contact"]["p0_mpa"] > 0.0


def test_single_plane_point_contact():
    data = _base_point_input()
    data["geometry"]["r2_mm"] = 0.0  # r2=0 表示平面
    result = calculate_hertz_contact(data)
    assert result["contact"]["contact_radius_mm"] > 0.0
    assert result["contact"]["p0_mpa"] > 0.0


def test_safety_factor_value():
    data = _base_line_input()
    result = calculate_hertz_contact(data)
    p0 = result["contact"]["p0_mpa"]
    allowable = result["check"]["allowable_p0_mpa"]
    sf = result["check"]["safety_factor"]
    assert sf == pytest.approx(allowable / p0, rel=1e-3)


def test_warning_short_length():
    data = _base_line_input()
    data["geometry"]["length_mm"] = 3.0
    result = calculate_hertz_contact(data)
    assert any("边缘效应" in w or "长度" in w for w in result["warnings"])


def test_warning_low_safety():
    data = _base_line_input()
    data["checks"]["allowable_p0_mpa"] = 10.0  # 极低许用值，必然 SF < 1.2
    result = calculate_hertz_contact(data)
    assert any("安全系数" in w for w in result["warnings"])


def test_curve_generation_point_count():
    data = _base_line_input()
    data["options"] = {"curve_points": 51}
    result = calculate_hertz_contact(data)
    assert len(result["curve"]["force_n"]) == 51
    assert len(result["curve"]["p0_mpa"]) == 51


def test_contact_area_line():
    data = _base_line_input()
    result = calculate_hertz_contact(data)
    b = result["contact"]["semi_width_mm"]
    L = result["contact"]["length_mm"]
    area = result["contact"]["contact_area_mm2"]
    assert area == pytest.approx(2.0 * b * L, rel=1e-3)


def test_contact_area_point():
    import math as _math
    data = _base_point_input()
    result = calculate_hertz_contact(data)
    a = result["contact"]["contact_radius_mm"]
    area = result["contact"]["contact_area_mm2"]
    assert area == pytest.approx(_math.pi * a * a, rel=1e-3)
