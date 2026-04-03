import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.widgets.worm_stress_curve import WormStressCurveWidget


class WormStressCurveWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_stress_curve_widget_accepts_data_and_renders(self) -> None:
        widget = WormStressCurveWidget()
        widget.set_curves(
            theta_deg=[0, 90, 180, 270, 360],
            sigma_h_mpa=[30, 45, 30, 45, 30],
            sigma_f_mpa=[20, 35, 20, 35, 20],
            sigma_h_nominal_mpa=35.0,
            sigma_f_nominal_mpa=25.0,
        )
        widget.resize(800, 400)
        widget.show()
        self.app.processEvents()
        pixmap = widget.grab()
        self.assertGreater(pixmap.size().width(), 0)

    def test_stress_curve_widget_clears_on_empty(self) -> None:
        widget = WormStressCurveWidget()
        widget.set_curves(
            theta_deg=[],
            sigma_h_mpa=[],
            sigma_f_mpa=[],
            sigma_h_nominal_mpa=0.0,
            sigma_f_nominal_mpa=0.0,
        )
        self.assertEqual(widget._theta_deg, [])


if __name__ == "__main__":
    unittest.main()
