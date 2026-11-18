# Site audit eradication: design plan for #414

Second attempt at the 45 audit findings (7 S1, 28 S2, 10 S3) in the audit
doc linked from #414. Parent issue: blowhorn-ai/blowhorn#1808.

## Where things stand

The first attempt (slices #417 to #422, PRs #427 to #439) implemented the
Signal theme unification and the fixes, then Yi called it the wrong
direction and Lee reverted it in #444, tracked in #443. Issues #416 to
#422 stay closed. Current master is the pre-#427 state, verified
2026-11-17 in this worktree:

- Site default is Reveille; the public home page sets front matter
  `theme: signal`. Docs, legal, pricing and download stay Reveille.
- The dead home variants are all still present: `home-figma` v1 to v4 and
  `home-oil`, in `content/en/`, `layouts/_partials/home/` and
  `assets/css/` (`home-figma.css`, `home-oil.css`, `home-signal.css`).
- The findings are still live on master: hard-coded `#6AE3B6` and
  `#E8B04A` in `home-signal.css`, `Safety` wording in layouts, sub-13px
  text in `assets/css/site.css`.

Yi's standing rule (2026-11-02): consistency discrepancies need no
approval from him and should be eradicated promptly. The one open call
from the first attempt is the theme: Yi chose Signal on Nov 2, but the
revert brought Reveille back, so the theme call needs re-confirming
before anything is deleted.

## Slices

Theme-independent slices go first. Nothing theme-dependent starts until
slice 0 is answered.

### Slice 0: re-confirm the theme call

Ask Yi on #414: Signal or Reveille? Until he confirms in writing, no
theme and no home variant is deleted. If Signal stands, slice 7 deletes
Reveille and the dead variants. If Reveille stands, slice 7 deletes
Signal instead and the home rebuild targets Reveille.

### Slice 1: vocabulary (fix 5)

One vocabulary everywhere: New activity (not New order or new post),
Posture (not Safety), one set of safety level names. Layouts, data
files and content. No theme dependency.

### Slice 2: header, menus, footer (fixes 8 and 9)

One Pricing link, one Download link, one Am I a Bot? link. Compare
becomes one link, and All comparisons points straight at its page
instead of through the `/versus/` redirect. Footer stops repeating the
header. Menu panels lose their intro paragraphs. Trust Center links to
its real page instead of `/legal` (the `/trust-center/` 404 goes away).
The AI native heading and the link with the same name become one.

### Slice 3: buttons (fix 4)

One install label, `Download`, from the shared template, and one
primary button per view. The home page stays skipped until its rebuild,
per the `check-install-cta` note in AGENTS.md.

### Slice 4: type floor and docs sidebar (fix 10)

Raise text below 13px to 13px (video badges and tags, action-matrix
group names, the home mockup). Remove the teal left stripe from the docs
sidebar's active link.

### Slice 5: colors to tokens (fix 6)

Replace the hard-coded colors in `home-signal.css` with brand tokens
from `static/assets/brand/tokens.json`. No new colors.

### Slice 6: home rebuild (fixes 1, 2 and 3)

Replace the home and Product-menu app mockup with the real shell (rail:
Dashboard, Activity, Profiles, Performance, Posture; New activity and
FAB lower right, Cmd-K upper right, non-link logo). One character per
section on home, with Major once; remove the characters that have no
site placement. Cut home to 6 or 7 sections, dropping the ones that
repeat the Product and Solutions menus, pricing and integrations. Each
testimonial appears in one place only. Depends on slice 0 and on the
Figma Signal design, which is the source of truth for layout and copy.

### Slice 7: theme unification and dead-variant deletion (fix 7)

Unify every page on the confirmed theme and delete the dead home
variants (`home-figma` v1 to v4, `home-oil`) with their layouts and CSS
(about 870 lines). `home-reveille` stays or goes with the slice 0 call.
Last slice, one PR, only after slices 1 to 6 are merged.

## Guardrails (what went wrong last time)

- One small PR per slice, merged separately. Never one big theme-plus-
  content PR that has to be reverted wholesale.
- No deletion of a theme or a home variant until Yi confirms the theme
  in writing on #414.
- Every slice is verified against the audit doc, passes `make check`,
  and follows the screenshot checklist in `docs/deploy.md` (390, 820 and
  1440 px, light and dark, no horizontal scroll from 320 px).
- Load the `ux-audit` skill before any change to `layouts/`,
  `assets/css/site.css` or a page's data file, and run the
  `brand-identity-review` skill at final review for brand pages, copy
  or tokens, per AGENTS.md.
- Docs copy is synced from the product repository's `docs/`: change it
  there, then sync. Never edit synced docs here.
- The #439 question: #443 listed #439 for revert while the #414 comment
  said it stays as a CI check fix the later docs syncs depend on.
  Verify on master whether its change is live before touching CI.

## Open questions for Lee and Yi

1. Theme: Signal or Reveille?
2. Is the Figma Signal design still the target for the home rebuild
   (slice 6), or does home stay as it is until the theme call?
3. Order: slices 1 to 5 first (no theme dependency), slices 6 and 7
   after the theme call. Agreed?
4. Who reviews and merges each slice: Lee, or a site maintainer?

## Out of scope

- #416 (empty states) stays closed as its own issue.
- #428 (bookmarklet card) stays, as decided in the revert.
- Docs syncs and unrelated work merged in between the revert.
