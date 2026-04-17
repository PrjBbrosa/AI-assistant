"""Task 1.C Step 1 — 塑料材料库单元测试。

覆盖：
- 材料库完整性（PA66 / PA66+GF30 / POM / PA46 / PEEK）
- 温度降额（高温下强度显著下降）
- 湿度降额（PA 系列显著降额，PEEK 几乎不降）
"""
import pytest
from core.worm.materials import PLASTIC_MATERIALS, apply_derate


def test_all_plastic_materials_loaded():
    """材料库应包含 5 种塑料：PA66、PA66+GF30、POM、PA46、PEEK。"""
    for name in ("PA66", "PA66+GF30", "POM", "PA46", "PEEK"):
        assert name in PLASTIC_MATERIALS, f"材料 {name} 未在 PLASTIC_MATERIALS 中"


def test_temperature_derate_reduces_allowables():
    """PA66 在 80℃ 下接触疲劳极限应低于常温的 70%。

    PA66 的 temp_derate_per_10c = 0.92，基准温度 23℃，
    80℃ 时 steps = (80-23)/10 = 5.7，降额系数 = 0.92^5.7 ≈ 0.618 < 0.70。
    """
    mat = PLASTIC_MATERIALS["PA66"]

    # 常温、零湿度（消除湿度影响，仅测温度降额）
    sigma_h_23, _ = apply_derate(mat, operating_temp_c=23.0, humidity_rh=0.0)
    # 高温、零湿度
    sigma_h_80, _ = apply_derate(mat, operating_temp_c=80.0, humidity_rh=0.0)

    # 常温干态时湿度因子=1.0，所以 sigma_h_23 = sigma_hlim_mpa
    assert sigma_h_23 == pytest.approx(mat.sigma_hlim_mpa, rel=1e-6)
    # 80℃ 下应低于常温的 70%
    assert sigma_h_80 < sigma_h_23 * 0.70, (
        f"PA66 在 80℃ 下 sigma_Hlim={sigma_h_80:.2f} MPa 应 < {sigma_h_23 * 0.70:.2f} MPa"
    )


def test_humidity_derate_hits_pa_only():
    """PA66 在 50%RH 下强度显著降额（< 75% 干态），PEEK 几乎不降（≈ 1.0×）。

    PA66 的 humidity_derate_at_50rh = 0.70，
    所以 50%RH 时湿度因子 = 0.70，即降到干态的 70%（< 75%）。

    PEEK 的 humidity_derate_at_50rh = 0.99，
    所以 50%RH 时湿度因子 = 0.99，与干态几乎相同（在 5% 容差内）。
    """
    pa = PLASTIC_MATERIALS["PA66"]
    peek = PLASTIC_MATERIALS["PEEK"]

    # 常温下比较（消除温度降额），对比 0%RH vs 50%RH
    sigma_pa_0rh, _ = apply_derate(pa, operating_temp_c=23.0, humidity_rh=0.0)
    sigma_pa_50rh, _ = apply_derate(pa, operating_temp_c=23.0, humidity_rh=50.0)

    sigma_peek_0rh, _ = apply_derate(peek, operating_temp_c=23.0, humidity_rh=0.0)
    sigma_peek_50rh, _ = apply_derate(peek, operating_temp_c=23.0, humidity_rh=50.0)

    # PA66：50%RH 下应 < 75% 干态
    assert sigma_pa_50rh < sigma_pa_0rh * 0.75, (
        f"PA66 50%RH={sigma_pa_50rh:.2f} MPa 应 < {sigma_pa_0rh * 0.75:.2f} MPa（干态 75%）"
    )

    # PEEK：50%RH 下应与干态接近（5% 容差内）
    assert sigma_peek_50rh == pytest.approx(sigma_peek_0rh, rel=5e-2), (
        f"PEEK 湿度降额不应显著：50%RH={sigma_peek_50rh:.2f} vs 干态={sigma_peek_0rh:.2f} MPa"
    )


def test_derate_base_temp_no_change():
    """在基准温度 23℃、零湿度下，降额后值等于原始材料参数。"""
    for name, mat in PLASTIC_MATERIALS.items():
        sigma_h, sigma_f = apply_derate(mat, operating_temp_c=23.0, humidity_rh=0.0)
        assert sigma_h == pytest.approx(mat.sigma_hlim_mpa, rel=1e-6), (
            f"{name}: 常温干态下 sigma_Hlim 不应降额"
        )
        assert sigma_f == pytest.approx(mat.sigma_flim_mpa, rel=1e-6), (
            f"{name}: 常温干态下 sigma_Flim 不应降额"
        )


def test_all_materials_have_positive_allowables():
    """所有材料的许用应力和弹性参数必须大于零。"""
    for name, mat in PLASTIC_MATERIALS.items():
        assert mat.sigma_hlim_mpa > 0, f"{name}: sigma_hlim_mpa 必须 > 0"
        assert mat.sigma_flim_mpa > 0, f"{name}: sigma_flim_mpa 必须 > 0"
        assert mat.e_mpa > 0, f"{name}: e_mpa 必须 > 0"
        assert 0.0 < mat.nu < 0.5, f"{name}: nu 必须在 (0, 0.5) 范围内"
        assert mat.allowable_surface_temp_c > 23.0, (
            f"{name}: allowable_surface_temp_c 应高于基准温度 23℃"
        )


def test_peek_highest_allowable_contact_stress():
    """PEEK 应有最高的接触疲劳极限（工程实践：PEEK 热强度最优）。"""
    peek_sigma = PLASTIC_MATERIALS["PEEK"].sigma_hlim_mpa
    for name, mat in PLASTIC_MATERIALS.items():
        if name != "PEEK":
            assert peek_sigma > mat.sigma_hlim_mpa, (
                f"PEEK sigma_Hlim={peek_sigma} 应高于 {name} sigma_Hlim={mat.sigma_hlim_mpa}"
            )
