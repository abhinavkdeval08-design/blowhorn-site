#!/usr/bin/env python3
"""Fail if the site's copy of the product brand tokens drifted, or the CSS drifted from them.

The site keeps a hand-made copy of the product's `marketing/brand/tokens.json`
at `static/assets/brand/tokens.json`. The copy drifted once already: it missed
blowhorn-ai/blowhorn#1865 (caption 13/18, ui 15/22) and five colour usage notes,
and was only fixed by hand in #435. `check-site-contract.py` only checks that
the file exists, so this script compares it against a product checkout instead.

Usage: check_brand_tokens.py [--product PATH] [--site PATH] [--css PATH] [--write]

  --product  product tokens file; default BLOWHORN_DIR/marketing/brand/tokens.json
             (BLOWHORN_DIR defaults to ../blowhorn), falling back to
             SOURCE_DIR/marketing/brand/tokens.json (SOURCE_DIR defaults to
             product, the sync-docs.yml checkout). When no product file exists
             the check prints a skip note and exits 0: plain CI has no product
             checkout, and the product repository is private.
  --site     site tokens file; default static/assets/brand/tokens.json
  --css      site stylesheet; default assets/css/site.css
  --write    regenerate the site tokens file from the product file instead of
             checking it: product values and sizes win, the site's own
             usage/sample prose and its site-only entries are kept. Exits 2
             when there is no product file to generate from. Never touches the
             stylesheet: fix a CSS drift the check reports by hand.

What the check asserts:

  - name, version, color themes, type fonts and families, and the spacing,
    radius, shadow and stroke groups are equal.
  - color tokens: the site list starts with the product list in order,
    comparing name and value only. Usage prose is the site's own wording
    (Layer5 becomes Blowhorn, blowhorn.layer5.io becomes blowhorn.ai, and
    check-naming.py would fail the product wording), so it is not compared.
    Extra site colours must be in SITE_ONLY_COLORS.
  - type styles: every product style, by name across groups, has a site style
    with the same fontSize, lineHeight, fontWeight and letterSpacing, except
    SITE_ONLY_STYLES. The product's Display `label` and the site's mono
    `.label` are different styles sharing a name (different group, weight and
    font), so `label` is a site-only style and is not compared against the
    product. Extra site styles must be in SITE_ONLY_STYLES.
  - CSS: `.ui`, `.caption` and `.label` in site.css match the font-size and
    line-height of the ui, caption and label styles in the site tokens file.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SITE_TOKENS = ROOT / "static" / "assets" / "brand" / "tokens.json"
SITE_CSS = ROOT / "assets" / "css" / "site.css"

# Colours the site may add after the product list (issue #436). None of them is
# in the site file today: they live as literals in site.css, and this list only
# allows them if a later tokens edit promotes one into the file.
SITE_ONLY_COLORS = {
    "video-matte", "on-matte", "on-teal-deep", "teal-glow",
    "status-bg", "status-ink",
    "mark-claude", "mark-deepseek", "mark-openai",
    "proof-flag-bg", "proof-flag-ink", "print-ink", "ai-soon-ink",
}

# Type styles the site may add, by name. `label` is the only one today: the
# site's mono uppercase .label, not the product's Display label.
SITE_ONLY_STYLES = {"label"}

# Compared on every type style: the size and weight. letterSpacing is compared
# only when the product style sets it.
STYLE_FIELDS = ("fontSize", "lineHeight", "fontWeight", "letterSpacing")

# Groups compared whole: the site keeps no local additions in them.
WHOLE_GROUPS = ("spacing", "radius", "shadow", "stroke")

CSS_CLASSES = ("ui", "caption", "label")


def find_product_tokens(explicit=None):
    """The product tokens file, or None when no product checkout is present."""
    if explicit:
        return Path(explicit)
    for base in (os.environ.get("BLOWHORN_DIR", "../blowhorn"),
                 os.environ.get("SOURCE_DIR", "product")):
        candidate = (ROOT / base / "marketing" / "brand" / "tokens.json").resolve() \
            if not os.path.isabs(base) else Path(base) / "marketing" / "brand" / "tokens.json"
        if candidate.is_file():
            return candidate
    return None


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def dump_tokens(tokens):
    """The site file's own formatting: one-space indent, raw non-ASCII, no trailing newline."""
    return json.dumps(tokens, indent=1, ensure_ascii=False)


def styles_by_name(tokens):
    """type styles keyed by name, across groups."""
    found = {}
    for group in tokens.get("type", {}).get("groups", []):
        for style in group.get("styles", []):
            found.setdefault(style["name"], style)
    return found


def check_tokens(product, site):
    """Every drift between the product and site token files, as error strings."""
    errors = []
    if product.get("name") != site.get("name"):
        errors.append(f"name: product is {product.get('name')!r}, site is {site.get('name')!r}")
    if product.get("version") != site.get("version"):
        errors.append(f"version: product is {product.get('version')!r}, site is {site.get('version')!r}")
    if product.get("color", {}).get("themes") != site.get("color", {}).get("themes"):
        errors.append("color.themes: product and site differ")
    product_tokens = product.get("color", {}).get("tokens", [])
    site_tokens = site.get("color", {}).get("tokens", [])
    for index, token in enumerate(product_tokens):
        if index >= len(site_tokens):
            errors.append(f"color.tokens: site is missing {token['name']!r} (and the rest of the product list)")
            break
        site_token = site_tokens[index]
        if site_token.get("name") != token["name"]:
            errors.append(
                f"color.tokens[{index}]: product has {token['name']!r}, site has "
                f"{site_token.get('name')!r}; the site list must start with the product list in order")
            break
        if site_token.get("value") != token.get("value"):
            errors.append(
                f"color.tokens {token['name']!r}: product value is {token.get('value')!r}, "
                f"site value is {site_token.get('value')!r}")
    for token in site_tokens[len(product_tokens):]:
        if token["name"] not in SITE_ONLY_COLORS:
            errors.append(
                f"color.tokens: site-only colour {token['name']!r} is not in the allowed "
                f"site-only list; add it to SITE_ONLY_COLORS in check_brand_tokens.py or remove it")
    for key in ("fonts", "families"):
        if product.get("type", {}).get(key) != site.get("type", {}).get(key):
            errors.append(f"type.{key}: product and site differ")
    product_styles = styles_by_name(product)
    site_styles = styles_by_name(site)
    for name, style in product_styles.items():
        if name in SITE_ONLY_STYLES:
            continue
        site_style = site_styles.get(name)
        if site_style is None:
            errors.append(f"type styles: site is missing {name!r}")
            continue
        for field in STYLE_FIELDS:
            if field in style and style[field] != site_style.get(field):
                errors.append(
                    f"type style {name!r}: product {field} is {style[field]!r}, "
                    f"site {field} is {site_style.get(field)!r}")
    for name in site_styles:
        if name not in product_styles and name not in SITE_ONLY_STYLES:
            errors.append(
                f"type styles: site-only style {name!r} is not in the allowed "
                f"site-only list; add it to SITE_ONLY_STYLES in check_brand_tokens.py or remove it")
    for key in WHOLE_GROUPS:
        if product.get(key) != site.get(key):
            errors.append(f"{key}: product and site differ")
    for key in product:
        if key not in site:
            errors.append(f"site tokens file is missing the {key!r} group")
    for key in site:
        if key not in product:
            errors.append(f"site tokens file has an extra top-level group {key!r}")
    return errors


def css_rule(css, name):
    """The declaration block of `.name { ... }`, or None."""
    match = re.search(r"\." + re.escape(name) + r"\s*\{([^}]*)\}", css, re.S)
    return match.group(1) if match else None


def check_css(css, site):
    """Every .ui/.caption/.label size in the stylesheet that differs from the site tokens."""
    errors = []
    site_styles = styles_by_name(site)
    for name in CSS_CLASSES:
        style = site_styles.get(name)
        if style is None:
            errors.append(f"type styles: site tokens have no {name!r} style for the CSS check")
            continue
        block = css_rule(css, name)
        if block is None:
            errors.append(f"assets/css/site.css: no .{name} rule")
            continue
        for prop, field in (("font-size", "fontSize"), ("line-height", "lineHeight")):
            match = re.search(re.escape(prop) + r"\s*:\s*([^;]+);", block)
            if match is None:
                errors.append(f"assets/css/site.css: .{name} sets no {prop}")
            elif match.group(1).strip() != style[field]:
                errors.append(
                    f"assets/css/site.css: .{name} {prop} is {match.group(1).strip()}, "
                    f"the {name} token says {style[field]}")
    return errors


def merge_tokens(product, site):
    """The site file regenerated from the product file.

    Product values and sizes win; the site's usage/sample prose and its
    site-only entries are kept, in place, so a regeneration never rewords the
    site copy or drops a site-only colour or style.
    """
    merged = {}
    for key, value in product.items():
        merged[key] = value
    merged["color"] = dict(product.get("color", {}))
    merged["color"]["tokens"] = []
    site_tokens = {token["name"]: token for token in site.get("color", {}).get("tokens", [])}
    for token in product.get("color", {}).get("tokens", []):
        merged_token = dict(token)
        if token["name"] in site_tokens:
            merged_token["usage"] = site_tokens[token["name"]].get("usage", token.get("usage"))
        merged["color"]["tokens"].append(merged_token)
    product_names = {token["name"] for token in product.get("color", {}).get("tokens", [])}
    for token in site.get("color", {}).get("tokens", []):
        if token["name"] not in product_names:
            merged["color"]["tokens"].append(token)
    merged["type"] = dict(product.get("type", {}))
    merged["type"]["groups"] = []
    site_styles = styles_by_name(site)
    for group in product.get("type", {}).get("groups", []):
        merged_group = dict(group)
        merged_group["styles"] = []
        for style in group.get("styles", []):
            if style["name"] in SITE_ONLY_STYLES:
                # The site keeps its own version of this style (its label lives
                # in Mono, not in the product's Display group); never copy the
                # product's version into the site file.
                continue
            merged_style = dict(style)
            if style["name"] in site_styles:
                for prose in ("sample", "usage"):
                    if prose in site_styles[style["name"]]:
                        merged_style[prose] = site_styles[style["name"]][prose]
            merged_group["styles"].append(merged_style)
        product_style_names = {style["name"] for style in group.get("styles", [])}
        for site_group in site.get("type", {}).get("groups", []):
            if site_group.get("name") != group.get("name"):
                continue
            for style in site_group.get("styles", []):
                if style["name"] not in product_style_names:
                    merged_group["styles"].append(style)
        merged["type"]["groups"].append(merged_group)
    site_group_names = {group.get("name") for group in product.get("type", {}).get("groups", [])}
    for group in site.get("type", {}).get("groups", []):
        if group.get("name") not in site_group_names:
            merged["type"]["groups"].append(group)
    return merged


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--product", help="product tokens file (default: found from BLOWHORN_DIR/SOURCE_DIR)")
    parser.add_argument("--site", default=str(SITE_TOKENS), help="site tokens file")
    parser.add_argument("--css", default=str(SITE_CSS), help="site stylesheet")
    parser.add_argument("--write", action="store_true", help="regenerate the site tokens file instead of checking it")
    args = parser.parse_args(argv)

    product_path = find_product_tokens(args.product)
    if product_path is None:
        if args.write:
            print("check-brand-tokens: no product tokens file found; pass --product or set BLOWHORN_DIR",
                  file=sys.stderr)
            return 2
        print("check-brand-tokens: no product checkout found (looked for "
              "BLOWHORN_DIR/marketing/brand/tokens.json and SOURCE_DIR/marketing/brand/tokens.json); skipped")
        return 0
    if not product_path.is_file():
        print(f"check-brand-tokens: {product_path} is not a file", file=sys.stderr)
        return 2
    product = load_json(product_path)
    site = load_json(args.site)
    if args.write:
        merged = merge_tokens(product, site)
        Path(args.site).write_text(dump_tokens(merged), encoding="utf-8")
        print(f"check-brand-tokens: regenerated {args.site} from {product_path}")
        errors = check_tokens(product, merged)
        if errors:
            print("check-brand-tokens: the regenerated file still has problems:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1
        return 0
    css = Path(args.css).read_text(encoding="utf-8")
    errors = check_tokens(product, site) + check_css(css, site)
    if errors:
        print(f"check-brand-tokens: {args.site} drifted from {product_path}:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"check-brand-tokens: {args.site} matches {product_path}, and .ui/.caption/.label match the tokens")
    return 0


if __name__ == "__main__":
    sys.exit(main())
