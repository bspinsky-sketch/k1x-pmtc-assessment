# Output Report -- Design Notes

Working reference for finishing the remaining pages. Captures what was learned
building and revising page 5 (Scaled. Trusted. Proven.) so the same ground
doesn't get re-covered from scratch. Last updated 2026-08-29.

---

## 1. Check the real K1x product before inventing a design

The single biggest lesson from this round: when a page reads flat or needs a
real redesign (not just production from an approved layout), go look at the
live site -- **k1x.io** -- before reaching for general design instinct or the
sales deck alone. The site has already solved several of the exact problems
this report runs into, and citing its own precedent is more persuasive (and
more genuinely on-brand) than a plausible-sounding original composition.

Patterns confirmed live on k1x.io, worth reusing across the rest of this deck:

- **Solid-black stat tiles with oversized colored numerals.** Their homepage
  stat block (44 / 20 / 45+ / 40K+) is black tiles, no gray fill, big bold
  numeral in their brand cyan, small uppercase caption underneath in
  low-opacity white. This is the direct precedent for page 5's "variantD"
  black-tile treatment (gold numeral instead of their cyan, to stay inside
  this report's own established palette).
- **Open, rule-divided stat grids with no tile fill at all.** Their "Proven
  Results" section drops panel backgrounds entirely: pure white space, thin
  1px rule dividers (vertical between columns, horizontal between rows), a
  small line-icon next to each number, big colored numeral, small caption.
  Color and whitespace do the work instead of boxes. This is the precedent
  for page 5's "variantC" open-rule treatment.
- **Dark rounded "alliance" cards.** Their Accounting Alliances & Associations
  block is a dark navy/near-black rounded-corner card holding white logos --
  a reusable pattern if a future page needs to group partner/certification
  logos without a plain white background.
- **The wave-line graphic is a real, recurring site element, not a one-off.**
  It shows up across multiple sections (hero, section transitions) always as
  a background texture, always confined to open/calm areas, and never placed
  directly under dense body text or headlines. That placement discipline
  matters more than the graphic itself -- copy the *rule*, not just the
  asset.
- Their hero uses a dark near-black panel with a blue gradient blob and a
  large rounded "quarter-pill" white cutout transitioning into the light
  content below -- a possible reference if a future page wants a dark-to-light
  transition moment.

General checklist for any future page that needs a real design decision
(not just production): open k1x.io, look for an existing section that solves
a similar layout problem (stat wall, comparison, testimonial, CTA band,
section transition), and adapt that structure with this report's own palette
rather than starting from a blank instinct.

---

## 2. The wave-line background graphic

Source file (Ben pulled this from the K1x site/assets directly):
`K1x_Asset-10-1920x1063.png`, kept at the Application root.

**Technical detail that matters:** this file is a real RGBA image -- the
lines have genuine alpha-channel transparency (0-128 out of 255, i.e. never
fully opaque even at its densest), not a flat image sitting on a white
background. Confirmed via:

```python
from PIL import Image
import numpy as np
im = Image.open('K1x_Asset-10-1920x1063.png').convert('RGBA')
arr = np.array(im)
print(arr[...,3].min(), arr[...,3].max())  # 0, 128
```

Because the alpha channel is real, it can be recolored to any accent by
overwriting only the RGB channels and leaving alpha untouched -- the same
technique already used earlier in this project for the white-on-transparent
partner logos (Aprio, AICPA & CIMA, agn International):

```python
arr[...,0] = 245   # R
arr[...,1] = 208   # G
arr[...,2] = 0     # B  -- e.g. gold; swap for any brand color
# arr[...,3] unchanged, or scale it: arr[...,3] = np.clip(arr[...,3]*0.55, 0, 255)
```

**Aspect ratio / cropping math:** source is 1920x1063 (1.807 aspect), pages
are 1280x720 (1.778 aspect) -- close but not identical. To cover a full page
without distortion: scale by height (`720/1063`), giving a resized width of
~1301px, then center-crop 21px total off the width. For a *partial-page*
placement (a strip behind just one section, e.g. a footer band), crop a
fixed-pixel-size slice directly from an already-page-sized render rather than
fighting CSS `background-size: cover` percentage math against a differently-
shaped source -- it's more predictable and easier to verify.

**Derived files built this round** (`wave-gold.png` is now live in
`assets/bg/` and used on page 4 -- see below; the rest are still only in the
cloud scratch workspace):

| File | Tint | Purpose |
|---|---|---|
| `wave-gold.png` | gold, ~55% of source alpha | general-purpose subtle gold wash, full page |
| `wave-gold-strong.png` | gold, ~90% of source alpha | same crop, higher intensity for confined/small areas |
| `wave-gold-strip.png` | gold, cropped from `wave-gold-strong.png` | exact 1280x208 slice used behind page 5's bottom whitespace band |
| `wave-ink.png` | charcoal (#1E1E1E-ish), ~35% of source alpha | neutral monochrome option, no color commitment |
| `wave-panel.png` | panel-gray (`--panel` token), full source alpha (~50% max) | ties the texture to the report's existing panel-gray token instead of gold |

**Placement discipline (again, because it's the part that actually makes it
look intentional rather than decorative):** put it behind whitespace/negative
space, never behind a headline or body copy block. On page 5 it was used to
fill a previously-dead 130px band at the bottom of the page (below the trust
logo rows, above the footer) -- turning a flagged empty-space problem into a
branded flourish rather than adding a new element that competes with content.

---

## 3. Two structural patterns built for page 5 (reusable elsewhere)

**Open-rule grid** (no tile fill): CSS grid, no `background` on the cells,
`border-left` on every cell except the first in each row for vertical
dividers, `border-top` on the second row for the horizontal divider, big bold
numeral, small caption, and a small decorative accent (a short gold "tick"
bar, 22x3px rounded) above the numeral standing in for a per-stat icon
without needing a bespoke icon set. Reads as airy/editorial. Good default
whenever a stat wall feels flat but a full icon set isn't worth building.

**Black tile block**: solid `#0A0A0A` tile background, `border-radius:10px`,
gold numeral (`var(--gold)`, `font-weight:800`), caption in
`rgba(255,255,255,.72)`. Highest-contrast option, matches this report's own
page-4 dark card-header treatment as well as k1x.io's homepage stat block --
so it's doubly on-precedent (this report's own established language, and the
live product's).

Both are genuine alternatives to "gray panel + black text," which was the
flat/beige default this round moved away from. Consider one of these two
(or the earlier single-hero-tile idea: one stat gets a full accent-color
fill while the rest stay neutral, mirroring how the June sales deck itself
gave its $175M stat a unique yellow box) for any future stat-wall page,
rather than defaulting back to uniform gray tiles.

---

## 4. CSS gotcha: negative z-index background layers can vanish

If a background texture/image is added as an absolutely-positioned child with
`z-index: -1` (to sit behind the page's other content), and the parent
element (`.page`) only has `position: relative` with **no explicit
`z-index`**, the negative-z child can escape to the *parent's own* stacking
context instead of staying inside `.page`'s -- meaning it can paint **behind
`.page`'s own opaque background**, effectively becoming invisible, even
though DevTools/computed-style checks show it positioned correctly.

**Fix:** give the container an explicit `z-index` (e.g. `.page { z-index: 0;
}`) so it establishes its own stacking context. That forces correct paint
order: the container's own background paints first, then its negative-z
children paint on top of that (but still below its normal, non-negative-z
children).

Symptom to watch for: a background image/color that "isn't showing" despite
correct `background-image`, correct bounding-rect coordinates, and no
console errors when checked directly. If all of those check out and it's
still not visible, suspect stacking context before suspecting the image path
or CSS syntax.

---

## 5. Verify renders with pixel sampling, not just eyeballing

The z-index bug above was caught by sampling actual pixel colors in the
rendered PNG (via PIL/numpy) rather than concluding "looks right" from a
screenshot glance. A quick pattern worth reusing whenever a subtle visual
effect (faint texture, low-opacity overlay, thin rule line) needs
confirmation:

```python
from PIL import Image
import numpy as np
im = Image.open('render.png').convert('RGB')
arr = np.array(im)
band = arr[y0:y1, x0:x1, :]
uniq, counts = np.unique(band.reshape(-1,3), axis=0, return_counts=True)
# inspect the most common colors in the region -- pure white/expected-bg-only
# means the effect isn't actually rendering
```

Same discipline already used elsewhere on this project: computed-style checks
for font loading, `getBoundingClientRect()` checks for layout, and now pixel
sampling for subtle visual effects. Cheap to run, catches real bugs a
screenshot glance alone can miss.

---

## 6. Open flag: page 5's stat numbers may be stale

Page 5's current stat set was pulled from the June 30 sales deck
(`K1x Sales Enablement Deck v5 June 30.pptx`, slide 26), per the original
brief. The live k1x.io site (current as of this crawl) shows some
overlapping but not identical numbers:

| Page 5 draft says | k1x.io currently shows |
|---|---|
| 151 Top Accounting Firms | not found on the live site's stat sections visited |
| 20 Of the Top 25 Accounting Firms | matches -- "20 of the top 25 accounting firms" |
| 2 Of the Big Four Accounting Firms | not found on the live site's stat sections visited |
| 79 Leading Universities & Endowments | live site says "45 of the top 100 university endowments" -- different number, different framing |
| 85 Top Institutional Investors | live site doesn't show this as a separate stat |
| 44 Of Largest 100 Institutional Investors | matches -- "44 of the top 100 institutional investors" |
| 40K+ Organizations Trust K1x | matches -- "40K+ organizations worldwide" / "40,000 organizations" |
| $175M Growth Investment by Sumeru Equity Partners, April 2026 | point-in-time funding fact, not expected on an evergreen site -- no conflict |

Not resolved, not changed -- flagging only. Worth a quick check with Ben (or
K1x directly) on whether page 5 should track the live site's current numbers
instead of the June sales deck's, before this page locks in.

---

## 7. Status as of this note

**Page 4 update (2026-08-29):** the recolored wave graphic (`assets/bg/wave-gold.png`)
was added underneath the testimonial card grid -- an absolutely positioned
background layer starting just below the lede (`top:130px`, well clear of the
h1/lede text) running to the bottom of the page, `z-index:-1` with `.page`
given an explicit `z-index:0` (see Section 4's stacking-context gotcha -- this
page was built with that fix baked in from the start rather than discovered
the hard way again). Since the cards have opaque backgrounds, the texture
only shows through the row/column gaps and the small sliver below the grid --
same placement discipline as page 5 (calm/empty space only), just applied to
gaps in a grid instead of one open band. Verified visible via pixel sampling
before considering it done, same as the page-5 fix. Locked page 4 was updated
in place at Ben's direct request rather than proposed as a variant first --
this is a subtler addition (no layout, copy, or card changes), not a
redesign.

Page 5 is **not locked in**. Four visual variants exist only in the cloud
scratch workspace (not yet committed to this project folder):

- `05-trust-variantA.html` -- single hero gold tile ($175M), thin gold top-
  accent on all tiles
- `05-trust-variantB.html` -- all-gold numerals, gray tiles unchanged
- `05-trust-variantC.html` -- open-rule grid, no tile fill (Section 3 above)
- `05-trust-variantD.html` -- black tiles + gold numerals + wave-graphic
  texture in the bottom whitespace (Section 3 above)

Once Ben picks a direction (or a mix), the winning version becomes
`output_report/05-trust.html`, built from `assets/base.css` like pages 2-4,
and the logo/wave assets it depends on get copied into `assets/trust-logos/`
and `assets/bg/` respectively.

---

## 8. Object-alignment ("PowerPoint nudge") method for pixel-perfect layout

Recurring need: two visual elements sit in different structures (a number inside
a ring graphic vs. a plain number in a different column; a headline vs. a
caption several elements away) and need to land on the exact same line, or be
centered on their own region's centerline -- the kind of thing you'd do in
PowerPoint by just dragging shapes until the alignment guides snap. Normal CSS
flow can't do this on its own: a sibling's position depends on whatever
precedes it, so if one column has a 108px ring graphic and the neighboring
column just has a text label, nothing forces their contents onto a shared
line. Ben named this directly (2026-08-29, page 6 build): "if this was
PowerPoint, I could just move the objects around to the correct visual
alignment." The fix is the direct software equivalent of that.

**Method:**

1. Take every element that needs precise placement out of document flow --
   `position:absolute` inside a `position:relative` container ("box") that
   represents one region of the slide (usually one grid column).
2. Give each element an explicit `top` (and, to center it on its own box's
   centerline, `left:50%; transform:translateX(-50%)`). This is the "nudge" --
   each element now has its own independent coordinate, like a shape on a
   slide canvas, rather than a position inherited from its neighbors.
3. Decide the shared reference lines across boxes (e.g. "these two numbers
   sit on one line," "these two text blocks start at the same height"), and
   give the boxes themselves the same height/top so their internal
   coordinate systems line up.
4. Assign matching `top` values to whichever elements should land on each
   shared line.
5. Render with Playwright and measure the *actual* result --
   `getBoundingClientRect()` on both elements, comparing `top`/`bottom` or
   the vertical center `(top+bottom)/2`.
6. Adjust the `top` values by the measured gap, re-render, re-measure.
   Usually converges in 1-2 iterations since the boxes already share a
   coordinate system by construction (step 3).

**Reusable pattern:**

```css
.obj-box { position:relative; height:200px; }  /* one region per "column" of objects */
.obj     { position:absolute; left:50%; transform:translateX(-50%); top:Npx; }  /* one shape */
```

```python
# measure two elements that should align
a = await page.eval_on_selector('.thing-a', 'el => el.getBoundingClientRect()')
b = await page.eval_on_selector('.thing-b', 'el => el.getBoundingClientRect()')
# compare a['top']/a['bottom'] (or the midpoint) to b's; adjust CSS `top`, re-render, re-check
```

**Worked example:** page 6 ("Where You Stand Today") -- the "Your Score" ring's
number needed to sit on the same line as the "Peer" donut's number, and the
band text ("Transforming the Workflow") needed to align with the peer note
text, even though the ring is a 108px graphic and the peer content started
out as plain stacked text. Converged in one pass: both boxes given
`height:186px` (later `216px` once both got card treatment), matching `top`
offsets assigned to the two number elements and the two text elements, then
verified with `getBoundingClientRect()` -- landed within 1px on the first
render. See SESSION_LOG.md 2026-08-29 for the full back-and-forth.

**When to reach for this:** any time a request describes *moving or aligning
specific visual elements* relative to each other -- "align X with Y," "put
these on the same line," "center this on that box" -- rather than changing
copy, color, or which element appears at all. Very likely to recur on the
remaining Output Report pages, since several of them (like page 6) mix a
graphic element (rings, icons) with plain text across parallel columns.

### 8a. How an alignment request is best handed off

Asked and answered directly (2026-08-29, after the page 6 alignment work): an
annotated screenshot -- red boxes around the elements that should group
together, straight lines drawn through the exact points that should share a
coordinate -- communicated the target far better than prose alone would have.
"Align the numbers" in words could mean a lot of things; a line drawn through
both numbers in an actual screenshot can't be misread. Worth treating as the
default way to hand off this kind of request going forward, not just a
one-off for page 6.

Two things that kind of annotation does *not* resolve on its own, and are
worth a quick text exchange rather than guessing:

- **The trade-off in how to reach that end state**, when the elements being
  aligned have different natural sizes (here: a 108px ring graphic vs. a
  plain text label). The image shows the target line-up, not which side
  gives -- shrink the graphic, or add space above the shorter content? That
  still needs a question and an answer before implementing.
- **Box edges are approximate**, not a literal pixel spec. A hand-drawn
  rectangle means "roughly this region" -- reasonable judgment on the exact
  column width/boundary is expected, not a demand to match it pixel-for-
  pixel.

So the effective combination is: annotated screenshot for the geometric
target, short text exchange for the "how do we get there" trade-off. Ask for
(or expect) both next time an alignment request comes in.

**Standing instruction from Ben (2026-08-29): if an alignment/positioning
request comes in without an annotated screenshot and it's not already
unambiguous, ask for one before implementing rather than guessing.** Don't
silently proceed on a best-effort interpretation of a prose-only alignment
request -- the annotated-screenshot pattern above is good enough, and cheap
enough for Ben to produce, that it's worth the one extra round-trip rather
than risking a wrong guess and a redo.
