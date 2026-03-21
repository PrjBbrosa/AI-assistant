import math
import pytest
from core.spline.geometry import derive_involute_geometry, GeometryError


class TestDeriveInvoluteGeometry:
    def test_basic_m2_z20(self):
        """m=2, z=20, alpha=30 deg -> d=40, d_a=42, d_f=37.5"""
        r = derive_involute_geometry(module_mm=2.0, tooth_count=20)
        assert r["reference_diameter_mm"] == pytest.approx(40.0)
        assert r["tip_diameter_shaft_mm"] == pytest.approx(42.0)
        assert r["root_diameter_shaft_mm"] == pytest.approx(37.5)
        assert r["tip_diameter_hub_mm"] == pytest.approx(38.0)
        assert r["effective_tooth_height_mm"] == pytest.approx(2.0)
        assert r["mean_diameter_mm"] == pytest.approx(39.75)
        assert r["pressure_angle_deg"] == pytest.approx(30.0)

    def test_m1_25_z22(self):
        """DIN 5480 - 30x1.25x22 typical spec"""
        r = derive_involute_geometry(module_mm=1.25, tooth_count=22)
        assert r["reference_diameter_mm"] == pytest.approx(27.5)
        assert r["tip_diameter_shaft_mm"] == pytest.approx(28.75)

    def test_invalid_module_zero(self):
        with pytest.raises(GeometryError, match="模数"):
            derive_involute_geometry(module_mm=0.0, tooth_count=20)

    def test_invalid_tooth_count_too_small(self):
        with pytest.raises(GeometryError, match="齿数"):
            derive_involute_geometry(module_mm=2.0, tooth_count=5)

    def test_output_keys(self):
        r = derive_involute_geometry(module_mm=2.0, tooth_count=20)
        expected_keys = {
            "module_mm", "tooth_count", "pressure_angle_deg",
            "reference_diameter_mm", "tip_diameter_shaft_mm",
            "root_diameter_shaft_mm", "tip_diameter_hub_mm",
            "effective_tooth_height_mm", "mean_diameter_mm",
        }
        assert expected_keys.issubset(set(r.keys()))
