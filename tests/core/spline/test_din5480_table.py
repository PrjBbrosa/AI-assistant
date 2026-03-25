import pytest
from core.spline.din5480_table import (
    DIN5480_CATALOG,
    all_designations,
    lookup_by_designation,
)

REQUIRED_KEYS = {
    "designation", "module_mm", "tooth_count", "reference_diameter_mm",
    "tip_diameter_shaft_mm", "root_diameter_shaft_mm", "tip_diameter_hub_mm",
}


class TestDin5480Table:
    def test_catalog_not_empty(self):
        assert len(DIN5480_CATALOG) >= 15

    def test_lookup_known_designation(self):
        result = lookup_by_designation("W 25x1.25x18")
        assert result is not None
        assert result["module_mm"] == 1.25
        assert result["tooth_count"] == 18
        assert result["reference_diameter_mm"] == 25.0

    def test_lookup_unknown_returns_none(self):
        assert lookup_by_designation("W 999x99x99") is None

    def test_all_designations_matches_catalog(self):
        assert len(all_designations()) == len(DIN5480_CATALOG)

    def test_catalog_entries_have_required_keys(self):
        for entry in DIN5480_CATALOG:
            missing = REQUIRED_KEYS - set(entry.keys())
            assert not missing, f"{entry.get('designation', '?')} missing keys: {missing}"

    def test_geometric_consistency(self):
        for entry in DIN5480_CATALOG:
            d = entry["designation"]
            assert entry["root_diameter_shaft_mm"] < entry["tip_diameter_hub_mm"], f"{d}: d_f1 >= d_a2"
            assert entry["tip_diameter_hub_mm"] < entry["tip_diameter_shaft_mm"], f"{d}: d_a2 >= d_a1"
            assert entry["tip_diameter_shaft_mm"] < entry["reference_diameter_mm"], f"{d}: d_a1 >= d_B"
