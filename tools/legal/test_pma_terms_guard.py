from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.legal import pma_terms_guard


class PMATermsGuardTest(unittest.TestCase):
    def test_patron_engine_terms_pass_repo_guard(self) -> None:
        result = pma_terms_guard.validate_terms()
        self.assertTrue(result.ok, result.errors)

    def test_positive_return_claim_is_rejected(self) -> None:
        terms = pma_terms_guard.TERMS_PATH.read_text(encoding="utf-8")
        review = pma_terms_guard.COUNCIL_REVIEW_PATH.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            terms_path = root / "terms.md"
            review_path = root / "review.md"
            terms_path.write_text(terms + "\nMembers will receive profits from the Patron Engine.\n", encoding="utf-8")
            review_path.write_text(review, encoding="utf-8")

            result = pma_terms_guard.validate_terms(terms_path, review_path)

        self.assertFalse(result.ok)
        self.assertTrue(any("prohibited positive economic claim" in error for error in result.errors))

    def test_missing_council_lens_is_rejected(self) -> None:
        terms = pma_terms_guard.TERMS_PATH.read_text(encoding="utf-8")
        review = pma_terms_guard.COUNCIL_REVIEW_PATH.read_text(encoding="utf-8").replace("Member Advocate", "Member Lens")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            terms_path = root / "terms.md"
            review_path = root / "review.md"
            terms_path.write_text(terms, encoding="utf-8")
            review_path.write_text(review, encoding="utf-8")

            result = pma_terms_guard.validate_terms(terms_path, review_path)

        self.assertFalse(result.ok)
        self.assertTrue(any("Member Advocate" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
