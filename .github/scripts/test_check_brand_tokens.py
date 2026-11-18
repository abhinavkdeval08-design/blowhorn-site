#!/usr/bin/env python3
"""Tests for check_brand_tokens.py: the product-to-site token comparison, the
CSS size check, and the --write regeneration.

Run with `make test-scripts` (CI runs it too).
"""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).with_name("check_brand_tokens.py")
spec = importlib.util.spec_from_file_location("check_brand_tokens", SCRIPT)
tokens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tokens)


def product_tokens():
    return {
        "name": "Blowhorn",
        "version": 1,
        "color": {
            "themes": [{"id": "light", "name": "Light"}],
            "tokens": [
                {"name": "teal", "value": "#00B39F",
                 "usage": "Layer5 teal, the primary brand fill."},
                {"name": "ink", "value": {"light": "#1E2117", "dark": "#FFFFFF"},
                 "usage": "Body text."},
            ],
        },
        "type": {
            "fonts": [{"family": "Instrument Sans", "file": "fonts/InstrumentSans-Regular.woff2"}],
            "families": {"sans": "Instrument Sans, system-ui, sans-serif"},
            "groups": [
                {"name": "Display", "styles": [
                    {"name": "h1", "fontSize": "40px", "lineHeight": "46px",
                     "fontWeight": 700, "sample": "Product sample", "usage": "Product usage"},
                    {"name": "label", "fontSize": "11px", "lineHeight": "16px",
                     "fontWeight": 600, "sample": "Product label"},
                ]},
                {"name": "Text", "styles": [
                    {"name": "ui", "fontSize": "15px", "lineHeight": "22px", "fontWeight": 500},
                    {"name": "caption", "fontSize": "13px", "lineHeight": "18px", "fontWeight": 500},
                ]},
                {"name": "Mono", "styles": [
                    {"name": "code", "fontSize": "13px", "lineHeight": "20px", "fontWeight": 400},
                ]},
            ],
        },
        "spacing": {"space-1": "4px"},
        "radius": {"radius-1": "4px"},
        "shadow": {"shadow-1": "0 1px 2px rgba(0,0,0,0.1)"},
        "stroke": {"stroke-1": "1px"},
    }


def site_tokens():
    """The same tokens as the site keeps them: reworded usage prose, the ui and
    caption sizes the product moved to, and the site-only mono label."""
    site = product_tokens()
    site["color"]["tokens"][0]["usage"] = "Blowhorn teal, the primary brand fill."
    site["type"]["groups"][0]["styles"] = [
        {"name": "h1", "fontSize": "40px", "lineHeight": "46px",
         "fontWeight": 700, "sample": "Site sample", "usage": "Site usage"},
    ]
    site["type"]["groups"][2]["styles"].append(
        {"name": "label", "fontSize": "11px", "lineHeight": "16px",
         "fontWeight": 500, "sample": "FOLLOWERS"})
    return site


def stale_site_tokens():
    """The site file before the #436 fix: ui 14/20 and caption 12/16."""
    site = site_tokens()
    for group in site["type"]["groups"]:
        for style in group["styles"]:
            if style["name"] == "ui":
                style.update(fontSize="14px", lineHeight="20px")
            if style["name"] == "caption":
                style.update(fontSize="12px", lineHeight="16px")
    return site


CSS = (
    ".ui { font-size: 15px; line-height: 22px; font-weight: 500; }\n"
    ".caption { font-size: 13px; line-height: 18px; font-weight: 500; }\n"
    ".label {\n"
    "  font-family: var(--font-mono);\n"
    "  font-size: 11px;\n"
    "  line-height: 16px;\n"
    "  font-weight: 500;\n"
    "}\n"
)


class CheckTokensTest(unittest.TestCase):
    def test_in_sync_passes(self):
        self.assertEqual(tokens.check_tokens(product_tokens(), site_tokens()), [])

    def test_usage_prose_is_not_compared(self):
        # The site rewords usage notes (Layer5 becomes Blowhorn); only name and
        # value are compared, so a reworded token still passes.
        site = site_tokens()
        site["color"]["tokens"][0]["usage"] = "Something else entirely."
        self.assertEqual(tokens.check_tokens(product_tokens(), site), [])

    def test_stale_type_size_fails(self):
        problems = tokens.check_tokens(product_tokens(), stale_site_tokens())
        self.assertTrue(any("ui" in p and "15px" in p for p in problems), problems)
        self.assertTrue(any("caption" in p and "13px" in p for p in problems), problems)

    def test_changed_colour_value_fails(self):
        site = site_tokens()
        site["color"]["tokens"][0]["value"] = "#00B39E"
        problems = tokens.check_tokens(product_tokens(), site)
        self.assertEqual(len(problems), 1)
        self.assertIn("teal", problems[0])

    def test_missing_product_token_fails(self):
        site = site_tokens()
        del site["color"]["tokens"][1]
        problems = tokens.check_tokens(product_tokens(), site)
        self.assertTrue(any("ink" in p for p in problems), problems)

    def test_reordered_tokens_fail(self):
        site = site_tokens()
        site["color"]["tokens"] = list(reversed(site["color"]["tokens"]))
        problems = tokens.check_tokens(product_tokens(), site)
        self.assertTrue(any("in order" in p for p in problems), problems)

    def test_unlisted_site_only_colour_fails(self):
        site = site_tokens()
        site["color"]["tokens"].append(
            {"name": "surprise", "value": "#123456", "usage": "Nowhere in the list."})
        problems = tokens.check_tokens(product_tokens(), site)
        self.assertTrue(any("surprise" in p for p in problems), problems)

    def test_listed_site_only_colour_passes(self):
        site = site_tokens()
        site["color"]["tokens"].append(
            {"name": "video-matte", "value": "#111111", "usage": "Video ground."})
        self.assertEqual(tokens.check_tokens(product_tokens(), site), [])

    def test_unlisted_site_only_style_fails(self):
        site = site_tokens()
        site["type"]["groups"][2]["styles"].append(
            {"name": "footnote", "fontSize": "10px", "lineHeight": "14px", "fontWeight": 400})
        problems = tokens.check_tokens(product_tokens(), site)
        self.assertTrue(any("footnote" in p for p in problems), problems)

    def test_product_label_is_not_compared(self):
        # The product's Display label (weight 600) and the site's mono label
        # (weight 500) share a name but are different styles.
        site = site_tokens()
        site["type"]["groups"][2]["styles"][1]["fontWeight"] = 400
        self.assertEqual(tokens.check_tokens(product_tokens(), site), [])

    def test_whole_group_drift_fails(self):
        site = site_tokens()
        site["spacing"] = {"space-1": "5px"}
        problems = tokens.check_tokens(product_tokens(), site)
        self.assertTrue(any(p.startswith("spacing:") for p in problems), problems)


class CheckCssTest(unittest.TestCase):
    def test_matching_css_passes(self):
        self.assertEqual(tokens.check_css(CSS, site_tokens()), [])

    def test_stale_css_fails(self):
        css = CSS.replace("15px", "14px").replace("22px", "20px")
        problems = tokens.check_css(css, site_tokens())
        self.assertTrue(any(".ui" in p and "15px" in p for p in problems), problems)

    def test_missing_rule_fails(self):
        problems = tokens.check_css("", site_tokens())
        self.assertEqual(len(problems), 3)
        self.assertTrue(all("no .ui rule" in p or "no .caption rule" in p or "no .label rule" in p
                            for p in problems), problems)


class MergeTokensTest(unittest.TestCase):
    def test_write_regenerates_stale_file(self):
        merged = tokens.merge_tokens(product_tokens(), stale_site_tokens())
        self.assertEqual(tokens.check_tokens(product_tokens(), merged), [])
        self.assertEqual(tokens.check_css(CSS, merged), [])
        styles = tokens.styles_by_name(merged)
        self.assertEqual(styles["ui"]["fontSize"], "15px")
        self.assertEqual(styles["caption"]["lineHeight"], "18px")

    def test_write_keeps_site_prose_and_site_only_entries(self):
        merged = tokens.merge_tokens(product_tokens(), site_tokens())
        self.assertEqual(merged["color"]["tokens"][0]["usage"],
                         "Blowhorn teal, the primary brand fill.")
        self.assertEqual(tokens.styles_by_name(merged)["h1"]["sample"], "Site sample")
        self.assertEqual(tokens.styles_by_name(merged)["label"]["fontWeight"], 500)
        self.assertEqual(merged["color"]["tokens"][0]["value"], "#00B39F")

    def test_write_is_idempotent_on_an_in_sync_file(self):
        site = site_tokens()
        self.assertEqual(tokens.merge_tokens(product_tokens(), site), site)

    def test_write_roundtrip_only_changes_drifted_lines(self):
        # Regenerating a stale file must only change the drifted lines, and the
        # result must pass the check.
        merged = tokens.merge_tokens(product_tokens(), stale_site_tokens())
        self.assertEqual(tokens.check_tokens(product_tokens(), merged), [])
        before = tokens.dump_tokens(stale_site_tokens()).splitlines()
        after = tokens.dump_tokens(merged).splitlines()
        self.assertEqual(len(before), len(after))
        changed = [line for a, b in zip(before, after) if a != b for line in (b,)]
        self.assertEqual(len(changed), 4)
        self.assertTrue(all("15px" in line or "22px" in line or "13px" in line or "18px" in line
                            for line in changed), changed)


class MainTest(unittest.TestCase):
    def run_main(self, product, site, css, extra=()):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            product_path = root / "product.json"
            site_path = root / "site.json"
            css_path = root / "site.css"
            product_path.write_text(json.dumps(product), encoding="utf-8")
            site_path.write_text(json.dumps(site), encoding="utf-8")
            css_path.write_text(css, encoding="utf-8")
            return tokens.main(["--product", str(product_path), "--site", str(site_path),
                                "--css", str(css_path), *extra])

    def test_main_passes_when_in_sync(self):
        self.assertEqual(self.run_main(product_tokens(), site_tokens(), CSS), 0)

    def test_main_fails_when_stale(self):
        self.assertEqual(self.run_main(product_tokens(), stale_site_tokens(), CSS), 1)

    def test_main_write_fixes_a_stale_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            product_path = root / "product.json"
            site_path = root / "site.json"
            css_path = root / "site.css"
            product_path.write_text(json.dumps(product_tokens()), encoding="utf-8")
            site_path.write_text(json.dumps(stale_site_tokens()), encoding="utf-8")
            css_path.write_text(CSS, encoding="utf-8")
            self.assertEqual(tokens.main(["--product", str(product_path), "--site", str(site_path),
                                         "--css", str(css_path), "--write"]), 0)
            fixed = json.loads(site_path.read_text(encoding="utf-8"))
            self.assertEqual(tokens.check_tokens(product_tokens(), fixed), [])

    def test_main_skips_without_a_product_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site_path = root / "site.json"
            css_path = root / "site.css"
            site_path.write_text(json.dumps(site_tokens()), encoding="utf-8")
            css_path.write_text(CSS, encoding="utf-8")
            env = {"BLOWHORN_DIR": str(root / "no-blowhorn"),
                   "SOURCE_DIR": str(root / "no-product")}
            with mock.patch.dict(os.environ, env):
                self.assertEqual(tokens.main(["--site", str(site_path),
                                             "--css", str(css_path)]), 0)

    def test_main_write_fails_without_a_product_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site_path = root / "site.json"
            site_path.write_text(json.dumps(site_tokens()), encoding="utf-8")
            env = {"BLOWHORN_DIR": str(root / "no-blowhorn"),
                   "SOURCE_DIR": str(root / "no-product")}
            with mock.patch.dict(os.environ, env):
                self.assertEqual(tokens.main(["--site", str(site_path),
                                             "--css", str(root / "site.css"),
                                             "--write"]), 2)


if __name__ == "__main__":
    unittest.main()
