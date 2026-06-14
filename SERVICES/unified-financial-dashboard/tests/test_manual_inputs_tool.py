import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "manual_inputs.py"
SPEC = importlib.util.spec_from_file_location("manual_inputs_tool", SCRIPT_PATH)
tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tool
SPEC.loader.exec_module(tool)


def test_default_payload_valid_with_expected_warnings():
    result = tool.validate_payload(tool.default_payload())

    assert result["valid"] is True
    assert "cash_on_hand_usd is not set." in result["warnings"]
    assert "monthly_burn_usd is not set." in result["warnings"]


def test_validate_payload_rejects_secret_like_keys_and_values():
    result = tool.validate_payload(
        {
            "schema": "manual_financial_inputs.v1",
            "updated_at": "2026-06-12T00:00:00Z",
            "cash_on_hand_usd": 120000,
            "monthly_burn_usd": 30000,
            "api_key": "sk-thisShouldNotBeHere12345",
        }
    )

    assert result["valid"] is False
    assert any("Suspicious key" in error for error in result["errors"])
    assert any("Suspicious secret-like value" in error for error in result["errors"])


def test_init_creates_local_manual_input_file(tmp_path):
    target = tmp_path / "manual_financial_inputs.json"
    exit_code = tool.main(["--path", str(target), "--init"])

    assert exit_code == 0
    assert target.exists()
    result = tool.validate_file(target)
    assert result["valid"] is True


def test_setters_update_manual_input_file(tmp_path):
    target = tmp_path / "manual_financial_inputs.json"
    exit_code = tool.main(
        [
            "--path",
            str(target),
            "--cash-on-hand-usd",
            "120000",
            "--monthly-burn-usd",
            "30000",
            "--updated-by",
            "test",
            "--notes",
            "Redacted operating estimate.",
        ]
    )

    assert exit_code == 0
    payload = tool.load_json(target)
    assert payload["cash_on_hand_usd"] == 120000
    assert payload["monthly_burn_usd"] == 30000
    assert payload["updated_by"] == "test"
    assert tool.validate_file(target)["valid"] is True
