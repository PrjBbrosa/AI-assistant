import json
import unittest
from pathlib import Path

from core.worm.calculator import calculate_worm_geometry


class WormExamplesTests(unittest.TestCase):
    """Task 2.C Step 3: examples/ 加载回归测试。

    对每个 worm_case_0*.json 文件执行 calculate_worm_geometry，
    断言返回结构存在 'geometry' 键且不抛出异常。
    若文件不存在（core-engineer 尚未生成）则 skipTest。
    """

    EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples"

    def test_worm_case_01_loads_and_runs(self) -> None:
        path = self.EXAMPLES_DIR / "worm_case_01.json"
        if not path.exists():
            self.skipTest(f"示例文件 {path} 不存在（Wave 2 core-engineer 未完成时）")
        with open(path) as f:
            data = json.load(f)
        result = calculate_worm_geometry(data)
        self.assertIn("geometry", result)
        if result.get("load_capacity", {}).get("enabled"):
            contact = result["load_capacity"].get("contact", {})
            allowable = (
                contact.get("allowable_contact_stress_mpa")
                or contact.get("allowable_stress_mpa")
            )
            # PA66+GF30 在 60 °C / 50 % RH 工况下 sigma_Hlim 降额后仍应 > 0
            if allowable is not None:
                self.assertGreater(allowable, 0)

    def test_worm_case_02_runs(self) -> None:
        path = self.EXAMPLES_DIR / "worm_case_02.json"
        if not path.exists():
            self.skipTest("worm_case_02.json 未创建")
        with open(path) as f:
            data = json.load(f)
        result = calculate_worm_geometry(data)
        self.assertIn("geometry", result)

    def test_worm_case_03_runs(self) -> None:
        path = self.EXAMPLES_DIR / "worm_case_03.json"
        if not path.exists():
            self.skipTest("worm_case_03.json 未创建")
        with open(path) as f:
            data = json.load(f)
        result = calculate_worm_geometry(data)
        self.assertIn("geometry", result)


if __name__ == "__main__":
    unittest.main()
