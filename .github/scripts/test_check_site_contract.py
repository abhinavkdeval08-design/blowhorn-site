#!/usr/bin/env python3
"""Tests for check-site-contract.py's redirect check: the old legal URLs must
keep redirecting to the Trust Center pages that replaced them.

Run with `make test-scripts` (CI runs it too).
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("check-site-contract.py")
spec = importlib.util.spec_from_file_location("check_site_contract", SCRIPT)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def alias(target):
    return (
        "<!DOCTYPE html><html lang=\"en\"><head>"
        f"<title>{target}</title><link rel=\"canonical\" href=\"{target}\">"
        f"<meta charset=\"utf-8\"><meta http-equiv=\"refresh\" content=\"0; url={target}\">"
        "</head><body></body></html>"
    )


class RedirectCheckTest(unittest.TestCase):
    def check(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, text in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            return contract.check_redirects(root)

    def test_alias_pages_pass(self):
        self.assertEqual(self.check({page: alias(target) for page, target in contract.REDIRECTS.items()}), [])

    def test_missing_alias_fails(self):
        problems = self.check({})
        self.assertEqual(len(problems), len(contract.REDIRECTS))
        self.assertIn("is not published", problems[0])

    def test_wrong_target_fails(self):
        files = {page: alias(target) for page, target in contract.REDIRECTS.items()}
        files["privacy.html"] = alias("https://blowhorn.ai/")
        problems = self.check(files)
        self.assertEqual(len(problems), 2)
        self.assertTrue(all(p.startswith("/privacy.html") for p in problems))

    def test_old_legal_urls_are_listed(self):
        self.assertEqual(contract.REDIRECTS["privacy.html"], "https://blowhorn.ai/legal/privacy/")
        self.assertEqual(contract.REDIRECTS["terms.html"], "https://blowhorn.ai/legal/terms/")



    def test_action_matrix_url_is_a_contract(self):
        """HelpTips deep-link to /integrations/actions/ and its group and action anchors."""
        page = "integrations/actions/index.html"
        self.assertIn(page, contract.PAGES)
        ids = contract.PAGES[page]
        self.assertIn("main", ids)
        self.assertIn("matrix-title", ids)
        root = Path(__file__).resolve().parents[2]
        actions = json.loads((root / "data/actions.json").read_text(encoding="utf-8"))
        for group in actions["groups"]:
            self.assertIn(f"group-{group['id']}", ids)
        for action in actions["actions"]:
            self.assertIn(f"action-{action['id']}", ids)


if __name__ == "__main__":
    unittest.main()
