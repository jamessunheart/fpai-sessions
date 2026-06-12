import json
import unittest

from curator.tgbot import _is_low_risk_row, _proposal_type


class TestProposalTypeFallback(unittest.TestCase):
    def test_uses_explicit_type_field_when_present(self) -> None:
        cells = {"Type": "create-task", "Diff": "{}"}
        self.assertEqual(_proposal_type(cells), "create-task")

    def test_falls_back_to_diff_payload_proposal_type(self) -> None:
        cells = {"Diff": json.dumps({"proposal_type": "add-tag", "diff": {"params": {}}})}
        self.assertEqual(_proposal_type(cells), "add-tag")

    def test_falls_back_to_nested_diff_type(self) -> None:
        cells = {"Diff": json.dumps({"diff": {"type": "create-task", "params": {}}})}
        self.assertEqual(_proposal_type(cells), "create-task")

    def test_low_risk_works_when_type_column_blank(self) -> None:
        cells = {
            "Type": "",
            "Confidence": "🟢 High (>0.9)",
            "Diff": json.dumps({"proposal_type": "create-task", "diff": {"params": {}}}),
        }
        self.assertTrue(_is_low_risk_row(cells))


if __name__ == "__main__":
    unittest.main()
