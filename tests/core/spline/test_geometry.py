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
        assert r["mean_diameter_mm"] == pytest.approx(40.0)
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
        assert r["mean_diameter_mm"] == pytest.approx(13.625)
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

    def test_partial_explicit_geometry_raises(self):
        """Providing only some explicit dimensions should raise GeometryError."""
        with pytest.raises(GeometryError, match="显式花键几何输入不完整"):
            derive_involute_geometry(
                module_mm=1.25,
                tooth_count=10,
                reference_diameter_mm=15.0,
                # missing tip_diameter_shaft_mm, root_diameter_shaft_mm, tip_diameter_hub_mm
            )

    def test_pressure_angle_out_of_range_raises(self):
        with pytest.raises(GeometryError, match="压力角"):
            derive_involute_geometry(
                module_mm=2.0,
                tooth_count=20,
                allow_approximation=True,
                pressure_angle_deg=60.0,
            )

    def test_explicit_geometry_consistency_warning(self):
        """When explicit d deviates >5% from m*z, a warning message is produced."""
        # m=1.25, z=10 -> m*z=12.5, but we provide d=15.0 -> deviation=20%
        r = derive_involute_geometry(
            module_mm=1.25,
            tooth_count=10,
            reference_diameter_mm=15.0,
            tip_diameter_shaft_mm=14.75,
            root_diameter_shaft_mm=12.1,
            tip_diameter_hub_mm=12.5,
        )
        assert any("偏差" in msg for msg in r["messages"])
        assert any("5%" in msg for msg in r["messages"])

    def test_explicit_geometry_no_warning_when_consistent(self):
        """When explicit d matches m*z within 5%, no consistency warning."""
        # m=1.25, z=12 -> m*z=15.0, provide d=15.0 -> deviation=0%
        # Must satisfy d_f1 < d_a2 < d_a1 < d
        r = derive_involute_geometry(
            module_mm=1.25,
            tooth_count=12,
            reference_diameter_mm=15.0,
            tip_diameter_shaft_mm=14.75,
            root_diameter_shaft_mm=12.1,
            tip_diameter_hub_mm=12.5,
        )
        assert not any("偏差" in msg for msg in r["messages"])
