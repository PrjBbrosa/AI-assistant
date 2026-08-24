"""Regression guards for module-level beginner guide actions."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from app.ui.pages.bolt_tapped_axial_page import BoltTappedAxialPage
from app.ui.pages.bolt_page import BoltPage
from app.ui.pages.buffer_energy_page import BufferEnergyPage
from app.ui.pages.hertz_contact_page import HertzContactPage
from app.ui.pages.interference_fit_page import InterferenceFitPage
from app.ui.pages.spline_fit_page import SplineFitPage
from app.ui.pages.worm_gear_page import WormGearPage
from app.ui.widgets.beginner_guide_dialog import BeginnerGuideDialog


@dataclass(frozen=True)
class GuideCase:
    page_cls: type
    button_text: str
    help_ref: str


GUIDE_CASES = (
    GuideCase(
        BoltTappedAxialPage,
        "校核指南",
        "modules/bolt_tapped_axial/beginner_guide",
    ),
    GuideCase(
        InterferenceFitPage,
        "校核指南",
        "modules/interference/beginner_guide",
    ),
    GuideCase(SplineFitPage, "校核指南", "modules/spline/beginner_guide"),
    GuideCase(WormGearPage, "校核指南", "modules/worm/beginner_guide"),
    GuideCase(HertzContactPage, "校核指南", "modules/hertz/beginner_guide"),
    GuideCase(BufferEnergyPage, "仿真指南", "modules/buffer/beginner_guide"),
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize("case", GUIDE_CASES, ids=lambda case: case.page_cls.__name__)
def test_guide_action_opens_expected_vdi_style_dialog(qapp, monkeypatch, case):
    opened: list[BeginnerGuideDialog] = []

    def fake_exec(dialog):
        opened.append(dialog)
        return 0

    monkeypatch.setattr(BeginnerGuideDialog, "exec", fake_exec)
    page = case.page_cls()

    button = page.btn_help_guide
    assert button.text() == case.button_text
    assert button.isEnabled()
    assert not button.isHidden()
    assert button.property("helpRef") == case.help_ref

    right_actions = [
        page.right_actions_layout.itemAt(index).widget()
        for index in range(page.right_actions_layout.count())
    ]
    assert right_actions[:3] == [button, page.btn_load_1, page.btn_load_2]

    button.click()
    assert len(opened) == 1
    dialog = opened[0]
    assert dialog.objectName() == "BeginnerGuideDialog"
    assert dialog.size().width() == 720
    assert dialog.size().height() == 780
    assert dialog.close_button.text() == "我明白了"
    assert dialog.intro_label.isVisibleTo(dialog)
    assert dialog.intro_label.text()
    assert len(dialog.section_cards) >= 5
    page.deleteLater()


def test_vdi_guide_uses_the_same_shared_modal_dialog(qapp, monkeypatch):
    opened: list[BeginnerGuideDialog] = []

    def fake_exec(dialog):
        opened.append(dialog)
        return 0

    monkeypatch.setattr(BeginnerGuideDialog, "exec", fake_exec)
    page = BoltPage()
    page.btn_help_guide.click()

    assert len(opened) == 1
    dialog = opened[0]
    assert dialog.objectName() == "BeginnerGuideDialog"
    assert dialog.windowTitle() == "VDI 2230 螺栓校核指南"
    assert dialog.size().width() == 720
    assert dialog.size().height() == 780
    assert dialog.close_button.text() == "我明白了"
    page.deleteLater()


def test_shared_guide_dialog_centers_on_parent_window(qapp):
    host = QWidget()
    host.resize(1180, 720)
    host.move(100, 80)
    host.show()
    qapp.processEvents()

    dialog = BeginnerGuideDialog(
        window_title="测试指南",
        guide_title="测试指南",
        intro="用于验证弹窗位置。",
        sections=(("第一步", "正文"),),
        parent=host,
    )
    dialog.show()
    qapp.processEvents()
    dialog._center_on_parent()

    parent_center = host.frameGeometry().center()
    dialog_center = dialog.frameGeometry().center()
    assert abs(parent_center.x() - dialog_center.x()) <= 1
    assert abs(parent_center.y() - dialog_center.y()) <= 1
    dialog.close()
    host.close()
