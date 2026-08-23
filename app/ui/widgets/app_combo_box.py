"""Application combo box with content sizing and a frameless rounded popup."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QComboBox, QWidget


class AppComboBox(QComboBox):
    """QComboBox sized to contents, with a frameless rounded popup.

    macOS (and Windows to a lesser degree) wraps the combo popup in a
    top-level window (``QComboBoxPrivateContainer``) whose native chrome
    ignores the Qt stylesheet ``border-radius``. The popup therefore
    renders as a sharp rectangle even though the styled QFrame inside has
    rounded corners. Flipping that container into frameless + translucent
    mode on first show lets the QSS-painted frame become the only visible
    surface.

    Qt also tends to clip the combobox's own text area instead of widening
    the popup. On each show, the view's minimum width is set to the longest
    item plus padding.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

    def showPopup(self) -> None:  # noqa: N802 - matches Qt API
        # Apply window flags BEFORE the container becomes visible so the
        # first show already paints with a frameless + translucent chrome
        # (otherwise Qt has to hide/re-show on flag change -> visible flash).
        self._polish_container()
        super().showPopup()
        self._widen_view()

    def _polish_container(self) -> None:
        view = self.view()
        if view is None:
            return
        container = view.window()
        if container is None or container is self.window():
            return
        if container.property("themePolishApplied"):
            return
        container.setWindowFlag(Qt.FramelessWindowHint, True)
        container.setWindowFlag(Qt.NoDropShadowWindowHint, True)
        container.setAttribute(Qt.WA_TranslucentBackground, True)
        container.setProperty("themePolishApplied", True)

    def _widen_view(self) -> None:
        view = self.view()
        if view is None or self.count() == 0:
            return
        metrics: QFontMetrics = view.fontMetrics()
        longest = max(
            metrics.horizontalAdvance(self.itemText(i)) for i in range(self.count())
        )
        # padding (item 10px each side) + checkmark column + margin
        view.setMinimumWidth(max(self.width(), longest + 56))
