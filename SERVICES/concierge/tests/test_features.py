"""Unit tests for feature flag resolution logic (no DB required)."""
from shared.features import FEATURES, PLAN_DEFAULTS


def test_starter_plan_has_core_features():
    d = PLAN_DEFAULTS["starter"]
    assert d["inbound_voice"] is True
    assert d["human_escalation"] is True
    assert d.get("outbound_campaigns", False) is False


def test_scale_plan_enables_everything():
    d = PLAN_DEFAULTS["scale"]
    for k in FEATURES:
        assert d.get(k) is True


def test_plan_defaults_only_reference_known_features():
    for plan, defs in PLAN_DEFAULTS.items():
        for k in defs:
            assert k in FEATURES, f"{plan} -> unknown feature {k}"
