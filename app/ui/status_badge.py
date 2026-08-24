"""Map check/overall status values to Cloud Porcelain badge objectNames."""

from __future__ import annotations

PASS_BADGE = "PassBadge"
FAIL_BADGE = "FailBadge"
WAIT_BADGE = "WaitBadge"
REF_BADGE = "RefBadge"
INCOMPLETE_BADGE = "IncompleteBadge"


def badge_object_name(state: object) -> str:
    """Return the QLabel objectName for a status value.

    True / "pass" → PassBadge
    False / "fail" → FailBadge
    "incomplete" → IncompleteBadge
    "reference_only" / "reference" → RefBadge
    "not_checked" / "wait" / None / unknown → WaitBadge

    Unknown or fail-adjacent strings never map to PassBadge.
    """
    if isinstance(state, str):
        key: object = state.strip().lower()
    else:
        key = state
    if key is True or key == "pass":
        return PASS_BADGE
    if key is False or key == "fail":
        return FAIL_BADGE
    if key == "incomplete":
        return INCOMPLETE_BADGE
    if key in ("reference_only", "reference"):
        return REF_BADGE
    return WAIT_BADGE
