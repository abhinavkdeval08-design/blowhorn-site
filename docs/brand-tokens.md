# Brand tokens on blowhorn.ai

The site keeps a hand-made copy of the product's `marketing/brand/tokens.json`
at `static/assets/brand/tokens.json`, and `assets/css/site.css` implements
those tokens (README: "The site follows the brand kit exactly"). The copy
drifted once already: it missed blowhorn-ai/blowhorn#1865 (caption 13/18, ui
15/22) and five colour usage notes, and was only fixed by hand in #435. The
check below stops that happening again.

## Where it lives

| What | File |
| --- | --- |
| Product tokens | `marketing/brand/tokens.json` in a blowhorn checkout (`BLOWHORN_DIR`, default `../blowhorn`; `SOURCE_DIR`, default `product`, is the sync-docs.yml checkout) |
| Site tokens | `static/assets/brand/tokens.json` |
| Stylesheet | `assets/css/site.css` (`.ui`, `.caption`, `.label`) |
| Contract check | `.github/scripts/check_brand_tokens.py` (`make check-tokens`, part of `site-check`) |

## What the check asserts

- Name, version, colour themes, type fonts and families, and the spacing,
  radius, shadow and stroke groups are equal.
- Colour tokens: the site list starts with the product list in order,
  comparing name and value only. Usage prose is the site's own wording
  (Layer5 becomes Blowhorn, blowhorn.layer5.io becomes blowhorn.ai, and
  `check-naming.py` would fail the product wording), so it is not compared.
  Extra site colours must be in `SITE_ONLY_COLORS` in the script.
- Type styles: every product style, by name across groups, has a site style
  with the same font size, line height, weight and letter spacing, except
  `label`. The product's Display `label` and the site's mono `.label` are
  different styles sharing a name (different group, weight and font), so
  `label` is a site-only style and is not compared against the product. Extra
  site styles must be in `SITE_ONLY_STYLES` in the script.
- CSS: `.ui`, `.caption` and `.label` in `site.css` match the font size and
  line height of the ui, caption and label styles in the site tokens file.

## No product checkout

`make check-tokens` passes and checks nothing when no product checkout is
present: plain CI has none, and the product repository is private. Run it
where a checkout exists, e.g. `make check-tokens BLOWHORN_DIR=../blowhorn`.

## Fixing drift

Regenerate the site file from the product file:

```sh
python3 .github/scripts/check_brand_tokens.py --write
```

Product values and sizes win; the site's usage and sample prose and its
site-only entries are kept in place, so a regeneration never rewords the site
copy or drops a site-only colour or style. `--write` never touches the
stylesheet: fix a CSS drift the check reports by hand, then re-run the check.

## Follow-up

Generating the site file in the docs sync PR (issue #436, preferred outcome)
is not wired yet: the sync flow would run the `--write` mode above and commit
`static/assets/brand/tokens.json` alongside the synced docs. Until then the
check is the guard, and it runs wherever a product checkout is present.
