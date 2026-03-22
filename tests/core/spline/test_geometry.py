import math
import pytest
from core.spline.geometry import derive_involute_geometry, GeometryError


class TestDeriveInvoluteGeometry:
    def test_basic_m2_z20(self):
        """m=2, z=20, alpha=30 deg -> d=40, d_a=42, d_f=37.5"""
        r = derive_involute_geometry(
            module_mm=2.0,
            tooth_count=20,
            allow_approximation=True,
        )
        assert r["reference_diameter_mm"] == pytest.approx(40.0)
        assert r["tip_diameter_shaft_mm"] == pytest.approx(42.0)
        assert r["root_diameter_shaft_mm"] == pytest.approx(37.5)
        assert r["tip_diameter_hub_mm"] == pytest.approx(38.0)
        assert r["effective_tooth_height_mm"] == pytest.approx(2.0)
        assert r["mean_diameter_mm"] == pytest.approx(39.75)
        assert r["pressure_angle_deg"] == pytest.approx(30.0)
        assert r["geometry_source"] == "approximation_from_module_and_tooth_count"
        assert r["approximation_used"] is True

    def test_public_catalog_w15_x_1_25_x_10_geometry(self):
        """Public DIN 5480 small-size catalog sample: W/N 15 x 1.25 x 10."""
        r = derive_involute_geometry(
            module_mm=1.25,
            tooth_count=10,
            reference_diameter_mm=15.0,
            tip_diameter_shaft_mm=14.75,
            root_diameter_shaft_mm=12.1,
            tip_diameter_hub_mm=12.5,
        )
        assert r["reference_diameter_mm"] == pytest.approx(15.0)
        assert r["tip_diameter_shaft_mm"] == pytest.approx(14.75)
        assert r["root_diameter_shaft_mm"] == pytest.approx(12.1)
        assert r["tip_diameter_hub_mm"] == pytest.approx(12.5)
        assert r["effective_tooth_height_mm"] == pytest.approx(1.125)
        assert r["mean_diameter_mm"] == pytest.approx(13.425)
        assert r["geometry_source"] == "explicit_reference_dimensions"
        assert r["approximation_used"] is False

    def test_requires_reference_dimensions_without_approximation(self):
        with pytest.raises(GeometryError, match="reference_diameter_mm"):
            derive_involute_geometry(module_mm=1.25, tooth_count=10)

    def test_approximation_mode_is_explicit_and_flagged(self):
        r = derive_involute_geometry(
            module_mm=1.25,
            tooth_count=10,
            allow_approximation=True,
        )
        assert r["geometry_source"] == "approximation_from_module_and_tooth_count"
        assert r["approximation_used"] is True
        assert any("近似" in msg for msg in r["messages"])

    def test_invalid_module_zero(self):
        with pytest.raises(GeometryError, match="模数"):
            derive_involute_geometry(module_mm=0.0, tooth_count=20)

    def test_invalid_tooth_count_too_small(self):
        with pytest.raises(GeometryError, match="齿数"):
            derive_involute_geometry(module_mm=2.0, tooth_count=5)

    def test_output_keys(self):
        r = derive_involute_geometry(module_mm=2.0, tooth_count=20, allow_approximation=True)
        expected_keys = {
            "module_mm", "tooth_count", "pressure_angle_deg",
            "reference_diameter_mm", "tip_diameter_shaft_mm",
            "root_diameter_shaft_mm", "tip_diameter_hub_mm",
            "effective_tooth_height_mm", "mean_diameter_mm",
            "geometry_source", "approximation_used", "messages",
        }
        assert expected_keys.issubset(set(r.keys()))
