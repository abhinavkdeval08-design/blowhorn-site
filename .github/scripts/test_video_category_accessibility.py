#!/usr/bin/env python3
"""Video category filter accessibility tests.

Ensures video category filters use accessible button group semantics with
aria-pressed rather than inappropriate tab roles. Run with `make test-scripts`.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIDEOS_HTML = ROOT / "layouts" / "videos.html"
RESOURCES_JS = ROOT / "assets" / "js" / "resources.js"
RESOURCES_CSS = ROOT / "assets" / "css" / "resources.css"


class VideoCategoryAccessibilityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = VIDEOS_HTML.read_text(encoding="utf-8")
        cls.js = RESOURCES_JS.read_text(encoding="utf-8")
        cls.css = RESOURCES_CSS.read_text(encoding="utf-8")

    def test_no_tab_roles_in_videos_layout(self):
        self.assertNotIn('role="tablist"', self.html)
        self.assertNotIn("role='tablist'", self.html)
        self.assertNotIn('role="tab"', self.html)
        self.assertNotIn("role='tab'", self.html)
        self.assertNotIn("aria-selected", self.html)

    def test_category_filters_use_group_and_aria_pressed(self):
        self.assertRegex(
            self.html,
            r'role="group"\s+aria-label="Filter by category"',
            "Category filters must be wrapped in a group labeled 'Filter by category'",
        )
        self.assertIn('data-category-tab="all"', self.html)
        self.assertIn('aria-pressed="true"', self.html)
        self.assertIn('aria-pressed="false"', self.html)

    def test_js_updates_aria_pressed_not_aria_selected(self):
        self.assertIn('setAttribute("aria-pressed"', self.js)
        self.assertNotIn('setAttribute("aria-selected"', self.js)

    def test_css_styles_aria_pressed_active_state(self):
        self.assertRegex(
            self.css,
            r'\.category-tab\[aria-pressed="true"\]',
            "CSS must define styles for .category-tab[aria-pressed='true']",
        )
        self.assertNotIn('.category-tab[aria-selected="true"]', self.css)


if __name__ == "__main__":
    unittest.main()
