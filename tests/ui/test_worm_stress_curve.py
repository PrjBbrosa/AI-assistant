import os
import unittest
from unittest.mock import patch

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

    def test_stress_curve_widget_configures_matplotlib_fonts_on_construct(self) -> None:
        with patch("app.ui.widgets.worm_stress_curve.configure_matplotlib_fonts") as mock_config:
            WormStressCurveWidget()

        mock_config.assert_called_once()

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

    def test_stress_curve_data_survives_redraw(self) -> None:
        widget = WormStressCurveWidget()
        theta = [0.0, 90.0, 180.0, 270.0, 360.0]
        sigma_h = [30.0, 45.0, 30.0, 45.0, 30.0]
        sigma_f = [20.0, 35.0, 20.0, 35.0, 20.0]
        widget.set_curves(
            theta_deg=theta,
            sigma_h_mpa=sigma_h,
            sigma_f_mpa=sigma_f,
            sigma_h_nominal_mpa=35.0,
            sigma_f_nominal_mpa=25.0,
        )
        stored = widget.curve_data()
        self.assertEqual(stored[0], theta)
        self.assertEqual(stored[1], sigma_h)
        self.assertEqual(stored[2], sigma_f)
        self.assertEqual(stored[3], 35.0)
        self.assertEqual(stored[4], 25.0)
        widget.resize(800, 400)
        widget.show()
        self.app.processEvents()
        widget.grab()
        self.assertEqual(widget.curve_data(), stored)
        self.assertIn("accent", widget._palette)
        self.assertNotEqual(widget._palette["accent"], "#D97757")


if __name__ == "__main__":
    unittest.main()
