"""VDI 2230 柔度模型单元测试。"""
import math

import pytest

from core.bolt.compliance_model import (
    calculate_bolt_compliance,
    calculate_clamped_compliance,
)


class TestBoltCompliance:
    def test_basic_bolt_compliance(self):
        """螺栓柔度基础计算。"""
        result = calculate_bolt_compliance(
            d=10.0, p=1.5, l_K=30.0, E_bolt=210_000.0
        )
        assert result["delta_s"] > 0
        assert "l_eff" in result

    def test_longer_bolt_higher_compliance(self):
        """更长的夹紧长度 → 更大的螺栓柔度。"""
        short = calculate_bolt_compliance(d=10, p=1.5, l_K=20, E_bolt=210_000)
        long = calculate_bolt_compliance(d=10, p=1.5, l_K=40, E_bolt=210_000)
        assert long["delta_s"] > short["delta_s"]


class TestClampedCompliance:
    def test_cylinder_model(self):
        """圆柱体模型基础计算。"""
        result = calculate_clamped_compliance(
            model="cylinder",
            d_h=11.0, D_A=24.0, l_K=30.0, E_clamped=210_000.0,
        )
        assert result["delta_p"] > 0
        A_p = math.pi / 4 * (24**2 - 11**2)
        expected = 30.0 / (210_000 * A_p)
        assert abs(result["delta_p"] - expected) / expected < 0.01

    def test_cone_model(self):
        """锥台模型基础计算。"""
        result = calculate_clamped_compliance(
            model="cone",
            d_h=11.0, D_w=16.0, D_A=24.0, l_K=30.0, E_clamped=210_000.0,
        )
        assert result["delta_p"] > 0
        assert "cone_angle_deg" in result

    def test_cone_positive_result(self):
        """锥台模型柔度为正值。"""
        result = calculate_clamped_compliance(
            model="cone", d_h=11, D_w=16, D_A=24, l_K=30, E_clamped=210_000)
        assert result["delta_p"] > 0

    def test_sleeve_model(self):
        """套筒模型。"""
        result = calculate_clamped_compliance(
            model="sleeve",
            d_h=11.0, D_outer=24.0, D_inner=14.0, l_K=30.0,
            E_clamped=210_000.0,
        )
        assert result["delta_p"] > 0

    def test_invalid_model_raises(self):
        """无效模型类型抛出异常。"""
        with pytest.raises(Exception):
            calculate_clamped_compliance(
                model="invalid", d_h=11, D_A=24, l_K=30, E_clamped=210_000)

    def test_multi_layer(self):
        """多层被夹件：δp = Σ δp_i。"""
        layers = [
            {"model": "cylinder", "d_h": 11, "D_A": 24, "l_K": 15, "E_clamped": 210_000},
            {"model": "cylinder", "d_h": 11, "D_A": 24, "l_K": 15, "E_clamped": 70_000},
        ]
        result = calculate_clamped_compliance(layers=layers)
        single_steel = calculate_clamped_compliance(
            model="cylinder", d_h=11, D_A=24, l_K=15, E_clamped=210_000)
        single_alu = calculate_clamped_compliance(
            model="cylinder", d_h=11, D_A=24, l_K=15, E_clamped=70_000)
        expected = single_steel["delta_p"] + single_alu["delta_p"]
        assert abs(result["delta_p"] - expected) / expected < 0.01
