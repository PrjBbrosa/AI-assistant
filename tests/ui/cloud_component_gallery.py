"""Offscreen Cloud Porcelain control gallery. Not a product page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.design_tokens import cloud_porcelain_controls, qcolor
from app.ui.widgets.app_combo_box import AppComboBox
from app.ui.widgets.help_button import HelpButton


def _field(text: str, *, read_only: bool = False, disabled: bool = False, error: bool = False) -> QLineEdit:
    edit = QLineEdit(text)
    edit.setObjectName("InputField")
    edit.setReadOnly(read_only)
    edit.setEnabled(not disabled)
    if error:
        edit.setProperty("fieldError", True)
    return edit


def _badge(object_name: str, text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def _card(object_name: str, title: str, body: str) -> QFrame:
    frame = QFrame()
    frame.setObjectName(object_name)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 12, 12, 12)
    heading = QLabel(title)
    heading.setObjectName("SubSectionTitle")
    hint = QLabel(body)
    hint.setObjectName("SectionHint")
    hint.setWordWrap(True)
    layout.addWidget(heading)
    layout.addWidget(hint)
    return frame


class CloudComponentGallery(QWidget):
    """Test-only widget covering CONTROL-01..03 surfaces."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("CloudComponentGallery")
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), qcolor("canvas_base"))
        self.setPalette(palette)
        controls = cloud_porcelain_controls()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setObjectName("GalleryScroll")
        scroll.setAutoFillBackground(True)
        scroll.setPalette(palette)
        host = QWidget()
        host.setObjectName("GalleryHost")
        host.setAutoFillBackground(True)
        host.setPalette(palette)
        layout = QVBoxLayout(host)
        layout.setSpacing(16)

        fields_box = QGroupBox("输入")
        fields_grid = QGridLayout(fields_box)
        self.field_normal = _field("normal")
        self.field_focus = _field("focus")
        self.field_error = _field("error", error=True)
        self.field_readonly = _field("read-only 可复制", read_only=True)
        self.field_disabled = _field("disabled", disabled=True)
        self.field_hover = _field("hover")
        labels = (
            ("normal", self.field_normal),
            ("hover", self.field_hover),
            ("focus", self.field_focus),
            ("error", self.field_error),
            ("read-only", self.field_readonly),
            ("disabled", self.field_disabled),
        )
        for index, (caption, widget) in enumerate(labels):
            fields_grid.addWidget(QLabel(caption), index, 0)
            fields_grid.addWidget(widget, index, 1)
        layout.addWidget(fields_box)

        combo_box = QGroupBox("AppComboBox")
        combo_row = QHBoxLayout(combo_box)
        self.combo_normal = AppComboBox()
        self.combo_normal.addItems(["短选项", "圆柱体夹紧件非常长的选项文字", "第三项"])
        self.combo_disabled = AppComboBox()
        self.combo_disabled.addItems(["禁用"])
        self.combo_disabled.setEnabled(False)
        self.combo_error = AppComboBox()
        self.combo_error.addItems(["错误态"])
        self.combo_error.setProperty("fieldError", True)
        combo_row.addWidget(self.combo_normal)
        combo_row.addWidget(self.combo_disabled)
        combo_row.addWidget(self.combo_error)
        layout.addWidget(combo_box)

        buttons = QGroupBox("按钮")
        button_row = QHBoxLayout(buttons)
        self.btn_primary = QPushButton("执行校核")
        self.btn_primary.setObjectName("PrimaryButton")
        self.btn_primary.setMinimumHeight(controls.primary_button_height)
        self.btn_secondary = QPushButton("次级")
        self.btn_secondary.setObjectName("SecondaryButton")
        self.btn_secondary.setMinimumHeight(controls.button_height)
        self.btn_link = QPushButton("链接")
        self.btn_link.setObjectName("LinkButton")
        self.btn_disabled = QPushButton("禁用")
        self.btn_disabled.setEnabled(False)
        self.btn_disabled.setMinimumHeight(controls.button_height)
        self.overflow_button = QPushButton("更多")
        self.overflow_button.setObjectName("OverflowButton")
        self.overflow_button.setMinimumHeight(controls.button_height)
        self.overflow_button.setMinimumWidth(controls.icon_hit_min)
        self.help_button = HelpButton("terms/_sample")
        button_row.addWidget(self.btn_primary)
        button_row.addWidget(self.btn_secondary)
        button_row.addWidget(self.btn_link)
        button_row.addWidget(self.btn_disabled)
        button_row.addWidget(self.overflow_button)
        button_row.addWidget(self.help_button)
        button_row.addStretch(1)
        layout.addWidget(buttons)

        badges = QGroupBox("状态")
        badge_row = QHBoxLayout(badges)
        self.badge_pass = _badge("PassBadge", "✓ 通过")
        self.badge_fail = _badge("FailBadge", "× 不通过")
        self.badge_incomplete = _badge("IncompleteBadge", "! 校核不完整")
        self.badge_wait = _badge("WaitBadge", "— 未校核")
        self.badge_ref = _badge("RefBadge", "i 仅参考")
        for badge in (
            self.badge_pass,
            self.badge_fail,
            self.badge_incomplete,
            self.badge_wait,
            self.badge_ref,
        ):
            badge_row.addWidget(badge)
        badge_row.addStretch(1)
        layout.addWidget(badges)

        cards = QGroupBox("卡片")
        cards_row = QHBoxLayout(cards)
        self.sub_card = _card("SubCard", "SubCard", "玻璃次级卡")
        self.auto_card = _card("AutoCalcCard", "AutoCalcCard", "自动派生")
        auto_field = _field("12.0", read_only=True)
        self.auto_card.layout().addWidget(auto_field)
        self.disabled_card = _card("DisabledSubCard", "DisabledSubCard", "当前 mode 无关")
        self.warning_card = _card("WarningCard", "WarningCard", "适用范围提示")
        cards_row.addWidget(self.sub_card)
        cards_row.addWidget(self.auto_card)
        cards_row.addWidget(self.disabled_card)
        cards_row.addWidget(self.warning_card)
        layout.addWidget(cards)

        self.plain = QPlainTextEdit()
        self.plain.setPlainText("\n".join(f"行 {index} 滚动内容" for index in range(1, 16)))
        self.plain.setMaximumHeight(120)
        layout.addWidget(self.plain)

        self.table = QTableWidget(8, 3)
        self.table.setHorizontalHeaderLabels(["项目", "值", "单位"])
        for row in range(8):
            self.table.setItem(row, 0, QTableWidgetItem(f"项 {row + 1}"))
            self.table.setItem(row, 1, QTableWidgetItem(str(row)))
            self.table.setItem(row, 2, QTableWidgetItem("mm"))
        self.table.setMaximumHeight(180)
        layout.addWidget(self.table)

        self.tabs = QTabWidget()
        self.tabs.addTab(QLabel("页签 A"), "几何")
        self.tabs.addTab(QLabel("页签 B"), "结果")
        layout.addWidget(self.tabs)

        self.menu = QMenu(self)
        self.menu.setObjectName("GalleryMenu")
        self.menu.addAction("复制")
        self.menu.addAction("粘贴")
        self.menu.addSeparator()
        disabled_action = self.menu.addAction("禁用项")
        disabled_action.setEnabled(False)

        layout.addStretch(1)
        scroll.setWidget(host)
        root.addWidget(scroll)


def build_cloud_component_gallery(parent: QWidget | None = None) -> CloudComponentGallery:
    return CloudComponentGallery(parent)
