import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.widgets.latex_label import LatexLabel


class LatexLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_set_latex_renders_pixmap(self) -> None:
        label = LatexLabel()
        label.set_latex(r"$\sigma_H = \sqrt{\frac{F_n \cdot E^*}{\pi \cdot L \cdot \rho}}$")
        pixmap = label.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertGreater(pixmap.width(), 0)
        self.assertGreater(pixmap.height(), 0)

    def test_set_latex_with_custom_fontsize(self) -> None:
        label = LatexLabel()
        label.set_latex(r"$T_1$", fontsize=20)
        pixmap = label.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertGreater(pixmap.width(), 0)

    def test_same_formula_uses_cache(self) -> None:
        label = LatexLabel()
        label.set_latex(r"$\alpha$")
        pixmap1 = label.pixmap()
        label.set_latex(r"$\alpha$")
        pixmap2 = label.pixmap()
        # PySide6 wraps the same QPixmap in different Python objects,
        # so compare the underlying Qt cache key instead of identity.
        self.assertEqual(pixmap1.cacheKey(), pixmap2.cacheKey())

    def test_empty_latex_clears_pixmap(self) -> None:
        label = LatexLabel()
        label.set_latex(r"$x$")
        label.set_latex("")
        self.assertTrue(label.pixmap() is None or label.pixmap().isNull())


if __name__ == "__main__":
    unittest.main()
