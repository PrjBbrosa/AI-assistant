"""Helpers for deriving interference windows from fit selections."""

from __future__ import annotations

from .calculator import InputError

PREFERRED_FIT_OPTIONS: tuple[str, ...] = ("H7/p6", "H7/s6", "H7/u6")

# Curated ISO 286 preferred-fit subset for common hole-basis interference fits.
# The current implementation intentionally covers a narrow range (6~50 mm) so the
# UI can offer a traceable, testable starter workflow before a full tolerance
# system/search dialog is introduced.
_PREFERRED_FIT_TABLE: dict[str, dict[str, object]] = {
    "H7/p6": {
        "standard": "ISO 286 curated preferred-fit subset",
        "hole_tolerance": "H7",
        "shaft_tolerance": "p6",
        "bands": (
            {"lower_mm": 6.0, "upper_mm": 10.0, "hole_upper_um": 10.0, "hole_lower_um": 0.0, "shaft_upper_um": 12.0, "shaft_lower_um": 6.0},
            {"lower_mm": 10.0, "upper_mm": 18.0, "hole_upper_um": 12.0, "hole_lower_um": 0.0, "shaft_upper_um": 20.0, "shaft_lower_um": 12.0},
            {"lower_mm": 18.0, "upper_mm": 24.0, "hole_upper_um": 15.0, "hole_lower_um": 0.0, "shaft_upper_um": 24.0, "shaft_lower_um": 15.0},
            {"lower_mm": 24.0, "upper_mm": 30.0, "hole_upper_um": 18.0, "hole_lower_um": 0.0, "shaft_upper_um": 29.0, "shaft_lower_um": 18.0},
            {"lower_mm": 30.0, "upper_mm": 40.0, "hole_upper_um": 21.0, "hole_lower_um": 0.0, "shaft_upper_um": 35.0, "shaft_lower_um": 22.0},
            {"lower_mm": 40.0, "upper_mm": 50.0, "hole_upper_um": 25.0, "hole_lower_um": 0.0, "shaft_upper_um": 42.0, "shaft_lower_um": 26.0},
        ),
    },
    "H7/s6": {
        "standard": "ISO 286 curated preferred-fit subset",
        "hole_tolerance": "H7",
        "shaft_tolerance": "s6",
        "bands": (
            {"lower_mm": 6.0, "upper_mm": 10.0, "hole_upper_um": 10.0, "hole_lower_um": 0.0, "shaft_upper_um": 20.0, "shaft_lower_um": 14.0},
            {"lower_mm": 10.0, "upper_mm": 18.0, "hole_upper_um": 12.0, "hole_lower_um": 0.0, "shaft_upper_um": 27.0, "shaft_lower_um": 19.0},
            {"lower_mm": 18.0, "upper_mm": 24.0, "hole_upper_um": 15.0, "hole_lower_um": 0.0, "shaft_upper_um": 32.0, "shaft_lower_um": 23.0},
            {"lower_mm": 24.0, "upper_mm": 30.0, "hole_upper_um": 18.0, "hole_lower_um": 0.0, "shaft_upper_um": 39.0, "shaft_lower_um": 28.0},
            {"lower_mm": 30.0, "upper_mm": 40.0, "hole_upper_um": 21.0, "hole_lower_um": 0.0, "shaft_upper_um": 48.0, "shaft_lower_um": 35.0},
            {"lower_mm": 40.0, "upper_mm": 50.0, "hole_upper_um": 25.0, "hole_lower_um": 0.0, "shaft_upper_um": 59.0, "shaft_lower_um": 43.0},
        ),
    },
    "H7/u6": {
        "standard": "ISO 286 curated preferred-fit subset",
        "hole_tolerance": "H7",
        "shaft_tolerance": "u6",
        "bands": (
            {"lower_mm": 6.0, "upper_mm": 10.0, "hole_upper_um": 10.0, "hole_lower_um": 0.0, "shaft_upper_um": 26.0, "shaft_lower_um": 20.0},
            {"lower_mm": 10.0, "upper_mm": 18.0, "hole_upper_um": 12.0, "hole_lower_um": 0.0, "shaft_upper_um": 34.0, "shaft_lower_um": 26.0},
            {"lower_mm": 18.0, "upper_mm": 24.0, "hole_upper_um": 15.0, "hole_lower_um": 0.0, "shaft_upper_um": 41.0, "shaft_lower_um": 32.0},
            {"lower_mm": 24.0, "upper_mm": 30.0, "hole_upper_um": 18.0, "hole_lower_um": 0.0, "shaft_upper_um": 49.0, "shaft_lower_um": 38.0},
            {"lower_mm": 30.0, "upper_mm": 40.0, "hole_upper_um": 21.0, "hole_lower_um": 0.0, "shaft_upper_um": 61.0, "shaft_lower_um": 48.0},
            {"lower_mm": 40.0, "upper_mm": 50.0, "hole_upper_um": 25.0, "hole_lower_um": 0.0, "shaft_upper_um": 73.0, "shaft_lower_um": 57.0},
        ),
    },
}


def derive_interference_from_deviations(
    *,
    shaft_upper_um: float,
    shaft_lower_um: float,
    hub_upper_um: float,
    hub_lower_um: float,
) -> dict[str, object]:
    """Convert user-defined shaft/hub deviations into an interference window."""
    shaft_upper_um = float(shaft_upper_um)
    shaft_lower_um = float(shaft_lower_um)
    hub_upper_um = float(hub_upper_um)
    hub_lower_um = float(hub_lower_um)

    if shaft_upper_um < shaft_lower_um:
        raise InputError("轴偏差上下限无效：上偏差必须 >= 下偏差。")
    if hub_upper_um < hub_lower_um:
        raise InputError("轮毂偏差上下限无效：上偏差必须 >= 下偏差。")

    delta_min_um = shaft_lower_um - hub_upper_um
    delta_max_um = shaft_upper_um - hub_lower_um
    if delta_max_um <= 0:
        raise InputError("当前偏差组合不会形成过盈配合。")
    if delta_min_um < 0:
        raise InputError("当前偏差组合包含间隙或过渡配合，不适用于本过盈配合模块。")

    return {
        "mode": "user_defined_deviations",
        "delta_min_um": delta_min_um,
        "delta_max_um": delta_max_um,
        "deviations_um": {
            "shaft_upper_um": shaft_upper_um,
            "shaft_lower_um": shaft_lower_um,
            "hub_upper_um": hub_upper_um,
            "hub_lower_um": hub_lower_um,
        },
    }


def derive_interference_from_preferred_fit(
    *,
    fit_name: str,
    nominal_diameter_mm: float,
) -> dict[str, object]:
    """Convert a curated preferred fit into an interference window."""
    fit_name = str(fit_name).strip()
    nominal_diameter_mm = float(nominal_diameter_mm)
    if nominal_diameter_mm <= 0.0:
        raise InputError("名义配合直径必须 > 0。")

    fit_def = _PREFERRED_FIT_TABLE.get(fit_name)
    if fit_def is None:
        options = ", ".join(PREFERRED_FIT_OPTIONS)
        raise InputError(f"当前仅支持以下优选配合: {options}")

    band = None
    for candidate in fit_def["bands"]:  # type: ignore[index]
        lower = float(candidate["lower_mm"])
        upper = float(candidate["upper_mm"])
        if nominal_diameter_mm >= lower and nominal_diameter_mm <= upper:
            band = candidate
            break
    if band is None:
        lower = float(fit_def["bands"][0]["lower_mm"])  # type: ignore[index]
        upper = float(fit_def["bands"][-1]["upper_mm"])  # type: ignore[index]
        raise InputError(
            f"优选配合 {fit_name} 当前仅支持 {lower:.0f}~{upper:.0f} mm 名义直径的受限预设。"
        )

    derived = derive_interference_from_deviations(
        shaft_upper_um=float(band["shaft_upper_um"]),
        shaft_lower_um=float(band["shaft_lower_um"]),
        hub_upper_um=float(band["hole_upper_um"]),
        hub_lower_um=float(band["hole_lower_um"]),
    )
    derived.update(
        {
            "mode": "preferred_fit",
            "fit_name": fit_name,
            "standard": str(fit_def["standard"]),
            "hole_tolerance": str(fit_def["hole_tolerance"]),
            "shaft_tolerance": str(fit_def["shaft_tolerance"]),
            "nominal_diameter_mm": nominal_diameter_mm,
            "diameter_band_mm": {
                "lower_mm": float(band["lower_mm"]),
                "upper_mm": float(band["upper_mm"]),
            },
            "warnings": [
                "Current preferred-fit support is a curated ISO 286 subset for common hole-basis interference fits.",
            ],
        }
    )
    return derived
