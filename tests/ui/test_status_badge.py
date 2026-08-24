"""Unit tests for shared status-badge objectName mapping."""

from app.ui.status_badge import (
    FAIL_BADGE,
    INCOMPLETE_BADGE,
    PASS_BADGE,
    REF_BADGE,
    WAIT_BADGE,
    badge_object_name,
)


def test_badge_object_name_maps_known_states() -> None:
    assert badge_object_name(True) == PASS_BADGE
    assert badge_object_name("pass") == PASS_BADGE
    assert badge_object_name("PASS") == PASS_BADGE
    assert badge_object_name(False) == FAIL_BADGE
    assert badge_object_name("fail") == FAIL_BADGE
    assert badge_object_name("incomplete") == INCOMPLETE_BADGE
    assert badge_object_name("reference_only") == REF_BADGE
    assert badge_object_name("reference") == REF_BADGE
    assert badge_object_name("not_checked") == WAIT_BADGE
    assert badge_object_name("wait") == WAIT_BADGE
    assert badge_object_name(None) == WAIT_BADGE


def test_badge_object_name_unknown_never_pass() -> None:
    for state in ("unknown", "failed", "error", "ok", "", 1, 0, "True"):
        assert badge_object_name(state) == WAIT_BADGE
        assert badge_object_name(state) != PASS_BADGE
