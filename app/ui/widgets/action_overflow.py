"""Action-bar overflow: QAction proxies for existing QPushButton instances.

Priority is classified from button text, not page class lists:

- P0 always visible: 执行校核 / 执行仿真 / 导入曲线*
- P1 shown when space allows: 保存/加载输入条件, 指南
- P2 overflow first: 清空, 测试案例, secondary 导出
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QPushButton, QWidget

from app.ui.design_tokens import cloud_porcelain_controls


def widget_is_alive(widget: QObject | None) -> bool:
    """Return False when the C++ wrapper has already been deleted."""
    if widget is None:
        return False
    try:
        from shiboken6 import isValid

        if not bool(isValid(widget)):
            return False
    except Exception:
        pass
    try:
        widget.objectName()
    except RuntimeError:
        return False
    return True


def classify_action_priority(text: str) -> int:
    """Return 0 (always shown), 1 (preferred), or 2 (overflow first)."""
    label = (text or "").strip()
    if label in {"执行校核", "执行仿真"} or label.startswith("导入曲线"):
        return 0
    if label in {"保存输入条件", "加载输入条件", "校核指南", "仿真指南"}:
        return 1
    if "指南" in label and "导出" not in label:
        return 1
    return 2


def _button_width(button: QWidget) -> int:
    if not widget_is_alive(button):
        return 0
    button.ensurePolished()
    return max(button.sizeHint().width(), button.minimumSizeHint().width(), 32)


class ChapterActionButton(QPushButton):
    """QPushButton that notifies the overflow controller of Python-side state changes.

    ``setEnabled`` is not a C++ virtual, so page code such as
    ``btn_save.setEnabled(False)`` must go through this override to keep the
    menu QAction in sync while the menu is closed.
    """

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._overflow_controller: ActionOverflowController | None = None

    def setEnabled(self, aflag: bool) -> None:  # noqa: N802
        super().setEnabled(aflag)
        self._notify_overflow()

    def setText(self, text: str) -> None:  # noqa: N802
        super().setText(text)
        self._notify_overflow()

    def setToolTip(self, tip: str) -> None:  # noqa: N802
        super().setToolTip(tip)
        self._notify_overflow()

    def _notify_overflow(self) -> None:
        controller = self._overflow_controller
        if controller is None or not widget_is_alive(controller):
            return
        try:
            controller.sync_button(self)
        except RuntimeError:
            return


class ChapterActionsWidget(QWidget):
    """Action row whose contents do not become a hard page-width constraint.

    The toolbar still reports its natural ``sizeHint`` so a roomy header keeps
    all actions visible.  Its horizontal minimum is deliberately zero: the
    overflow controller owns the responsive packing and must be allowed to
    hide lower-priority buttons before the containing page pushes an outer
    splitter past its requested sidebar width.
    """

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        return QSize(0, hint.height())


@dataclass
class ActionProxy:
    button: QPushButton
    action: QAction
    priority: int
    logical_visible: bool = True
    overflowed: bool = False


class ActionOverflowController(QObject):
    """Hide lower-priority toolbar buttons and proxy them through a 更多 menu."""

    def __init__(
        self,
        header: QWidget,
        overflow_button: QPushButton,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._header = header
        self.overflow_button = overflow_button
        self._actions = overflow_button.parentWidget()
        self._menu = QMenu(overflow_button)
        self._proxies: list[ActionProxy] = []
        self._applying = False
        self._relayouting = False
        self._spacing = 8

        overflow_button.setObjectName("OverflowButton")
        overflow_button.setText("更多")
        overflow_button.setAccessibleName("更多操作")
        overflow_button.setToolTip("更多操作")
        overflow_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        overflow_button.setAutoDefault(False)
        overflow_button.setDefault(False)
        overflow_button.setMinimumHeight(cloud_porcelain_controls().button_height)
        overflow_button.setMenu(self._menu)
        overflow_button.hide()

        self._menu.aboutToShow.connect(self._sync_all)
        header.installEventFilter(self)
        if widget_is_alive(self._actions):
            self._actions.installEventFilter(self)

    def register(self, button: QPushButton) -> QAction:
        action = QAction(button.text(), self)
        action.setToolTip(button.toolTip())
        action.setEnabled(button.isEnabled())
        action.setVisible(False)
        action.triggered.connect(lambda _checked=False, source=button: self._click_source(source))
        self._menu.addAction(action)

        proxy = ActionProxy(
            button=button,
            action=action,
            priority=classify_action_priority(button.text()),
            logical_visible=True,
        )
        if isinstance(button, ChapterActionButton):
            button._overflow_controller = self
        self._proxies.append(proxy)
        self.sync_button(button)
        return action

    def action_for(self, button: QPushButton) -> QAction | None:
        for proxy in self._proxies:
            if proxy.button is button:
                return proxy.action
        return None

    def overflowed_buttons(self) -> list[QPushButton]:
        return [
            proxy.button
            for proxy in self._proxies
            if proxy.overflowed and widget_is_alive(proxy.button)
        ]

    def sync_button(self, button: QPushButton) -> None:
        proxy = self._proxy_for(button)
        if proxy is not None:
            self._sync_proxy(proxy)

    def relayout(self) -> None:
        if self._relayouting or not widget_is_alive(self) or not widget_is_alive(self._header):
            return
        if self._header.width() <= 1:
            return
        self._relayouting = True
        try:
            self._proxies = [
                proxy for proxy in self._proxies if widget_is_alive(proxy.button)
            ]
            available = self._available_actions_width()
            shown, overflowed = self._pack(available)
            shown_ids = {id(proxy) for proxy in shown}
            overflowed_ids = {id(proxy) for proxy in overflowed}
            for proxy in self._proxies:
                if not widget_is_alive(proxy.button):
                    continue
                proxy.overflowed = id(proxy) in overflowed_ids
            self._apply_toolbar_visibility(shown_ids)
        except RuntimeError:
            return
        finally:
            self._relayouting = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if not widget_is_alive(self):
            return False
        if obj in {self._header, self._actions} and event.type() == QEvent.Type.Resize:
            self.relayout()
        return False

    def _available_actions_width(self) -> int:
        layout = self._header.layout()
        margins = layout.contentsMargins() if layout is not None else None
        inset = (margins.left() + margins.right()) if margins is not None else 32
        gap = layout.spacing() if layout is not None else 12
        inner = max(0, self._header.width() - inset)
        title_reserve = min(max(168, inner // 4), 280)
        if layout is not None:
            for index in range(layout.count()):
                widget = layout.itemAt(index).widget()
                if widget is None or widget is self._actions:
                    continue
                title_reserve = max(title_reserve, widget.minimumSizeHint().width())
                break
        return max(0, inner - title_reserve - gap)

    def _pack(self, available: int) -> tuple[list[ActionProxy], list[ActionProxy]]:
        alive = [proxy for proxy in self._proxies if widget_is_alive(proxy.button)]
        logical = [proxy for proxy in alive if proxy.logical_visible]
        p0 = [proxy for proxy in logical if proxy.priority == 0]
        p1 = [proxy for proxy in logical if proxy.priority == 1]
        p2 = [proxy for proxy in logical if proxy.priority == 2]
        remaining = p1 + p2

        if not remaining:
            return list(p0), []
        if self._width_of(p0 + remaining, overflow=False) <= available:
            return list(p0 + remaining), []

        shown = list(p0)
        for candidate in remaining:
            trial = shown + [candidate]
            if self._width_of(trial, overflow=True) <= available:
                shown = trial

        overflowed = [proxy for proxy in remaining if id(proxy) not in {id(item) for item in shown}]
        if not overflowed:
            return shown, []
        return shown, overflowed

    def _width_of(self, proxies: list[ActionProxy], *, overflow: bool) -> int:
        widgets = [proxy.button for proxy in proxies]
        extra = 1 if overflow else 0
        count = len(widgets) + extra
        if count == 0:
            return 0
        total = sum(_button_width(widget) for widget in widgets)
        if overflow and widget_is_alive(self.overflow_button):
            total += _button_width(self.overflow_button)
        total += self._spacing * max(0, count - 1)
        return total

    def _apply_toolbar_visibility(self, shown_ids: set[int]) -> None:
        if not widget_is_alive(self):
            return
        self._applying = True
        try:
            any_overflow = False
            for proxy in self._proxies:
                if not widget_is_alive(proxy.button):
                    continue
                in_toolbar = proxy.logical_visible and id(proxy) in shown_ids
                proxy.button.setVisible(in_toolbar)
                in_menu = proxy.logical_visible and proxy.overflowed
                if widget_is_alive(proxy.action):
                    proxy.action.setVisible(in_menu)
                if in_menu:
                    any_overflow = True
                self._sync_proxy(proxy)
            if widget_is_alive(self.overflow_button):
                self.overflow_button.setVisible(any_overflow)
        except RuntimeError:
            return
        finally:
            self._applying = False

    def _sync_all(self) -> None:
        if not widget_is_alive(self):
            return
        for proxy in list(self._proxies):
            self._sync_proxy(proxy)

    def _sync_proxy(self, proxy: ActionProxy) -> None:
        if not widget_is_alive(proxy.action):
            return
        if not widget_is_alive(proxy.button):
            try:
                proxy.action.setEnabled(False)
                proxy.action.setVisible(False)
            except RuntimeError:
                pass
            return
        try:
            proxy.priority = classify_action_priority(proxy.button.text())
            proxy.action.setText(proxy.button.text())
            tooltip = proxy.button.toolTip() or proxy.button.text()
            proxy.action.setToolTip(tooltip)
            proxy.action.setEnabled(proxy.button.isEnabled())
            proxy.action.setVisible(proxy.logical_visible and proxy.overflowed)
        except RuntimeError:
            return

    def _click_source(self, button: QPushButton) -> None:
        if not widget_is_alive(button):
            return
        try:
            if not button.isEnabled():
                return
            button.click()
        except RuntimeError:
            return

    def _proxy_for(self, obj: QObject) -> ActionProxy | None:
        for proxy in self._proxies:
            if proxy.button is obj:
                return proxy
        return None
