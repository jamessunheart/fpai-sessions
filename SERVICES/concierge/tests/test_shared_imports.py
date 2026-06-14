"""Smoke test — make sure every package imports cleanly."""


def test_shared_modules_import():
    from shared import app_factory, auth, config, db, events, features, logging, tenant_context  # noqa: F401


def test_service_mains_import():
    from tenant_api import main as tm  # noqa: F401
    from compliance_gate import main as cm  # noqa: F401
    from handoff_broker import main as hm  # noqa: F401
    from skills_mesh import main as sm  # noqa: F401
    from voice_router import main as vm  # noqa: F401
    from outbound_engine import main as om  # noqa: F401
    from workers import auto_training, ai_qa  # noqa: F401
    from knowledge_ingest import worker  # noqa: F401


def test_feature_keys_declared():
    from shared.features import FEATURES, PLAN_DEFAULTS

    assert "inbound_voice" in FEATURES
    assert "realtime_voice" in FEATURES
    for plan, defs in PLAN_DEFAULTS.items():
        for k in defs:
            assert k in FEATURES, f"{plan} references unknown feature {k}"
