# PPT_CONVENTIONS.md -- PowerPoint Template Design and Audit Guide

**Two-part reference:**
- **Part 1:** Conventions for PPT templates you design from scratch
- **Part 2:** Audit checklist for PPT templates handed to you

---

# Part 1: Design Conventions (Templates Built from Scratch)

## Shape Naming Convention

Every shape that python-pptx will interact with must have a unique, consistent name.

| Prefix | Used for | Example |
|--------|---------|---------|
| `txt_` | Text frames with dynamic values | `txt_ROI`, `txt_companyName` |
| `lbl_` | Static label text (rarely pushed; document if so) | `lbl_paybackLabel` |
| `img_` | Image placeholders for chart/range inserts | `img_barChart`, `img_doughnut` |
| `tbl_` | Table shapes for structured data | `tbl_calc`, `tbl_investment` |
| `marker_` | Invisible marker triangles identifying slides | `marker_B1`, `marker_overview` |
| `tile_` | KPI tile groups (prefix + group + part) | `tile_roiValue`, `tile_roiLabel` |
| `icon_` | Icon shapes | `icon_ch1`, `icon_revenue` |

**Rules:**
- Name every shape you will push to. Unnamed shapes cannot be reliably targeted by python-pptx.
- Use exact, stable names -- they are hardcoded in report.py.
- Document the full shape-to-named-range mapping in CLAUDE.md under "Output Report Slide Map."

## Slide Markers

For slides that may be deleted (e.g., inactive benefit slides):
- Add an invisible isosceles triangle shape at (-0.1 inches, -0.1 inches)
- Name it `marker_{benefit_id}` (e.g., `marker_B1`)
- python-pptx finds markers to identify which slides correspond to which benefits
- Size: any small size; color: transparent or white; no visible impact

## Pre-Filled vs. Empty Shapes

- **Pre-filled shapes:** Text baked into the template at design time. python-pptx must NOT push to these -- overwriting strips all formatting runs, losing bold, color, size, and font.
- **Empty shapes:** Placeholders for dynamic content. python-pptx pushes values here at report generation time.
- Document which shapes are pre-filled and which are empty in the slide map.

## endParaRPr Requirements [P017]

For any empty shape that will receive VBA-pushed text (or python-pptx text with specific formatting requirements):
- Open the PPTX, unpack the XML, inspect `endParaRPr` on every target shape
- All required attributes must be explicit: `b`, `sz`, `solidFill` (with color value), `latin` (typeface)
- Visual appearance in PowerPoint's editor does NOT reflect what python-pptx will produce
- Fix at the template level before first test run

## Font and Color Guidelines

- Use standard Windows/Office fonts (Georgia, Calibri, Arial, Times New Roman) -- guaranteed present on all machines
- Define a small set of brand colors in the design questionnaire; apply consistently across all slides
- Use the slide master for repeating elements (footer, logo placeholder) -- reduces per-slide maintenance

---

# Part 2: Audit Checklist (Templates Handed to You)

Run this audit **before Phase 4** (PPT generation build) and again **before Phase 9** (full report push). Issues caught here prevent silent failures in report generation.

## Step 1: List All Shapes and Their Text Content

```python
from pptx import Presentation

prs = Presentation('template.pptx')
print(f'Total slides: {len(prs.slides)}')
for i, slide in enumerate(prs.slides):
    print(f'\n--- Slide {i+1} ---')
    for shape in slide.shapes:
        text = ''
        if shape.has_text_frame:
            text = shape.text_frame.text[:60]
        print(f'  [{shape.name}] type={shape.shape_type} text={text!r}')
```

**Check:**
- Every dynamic shape has a name matching the `txt_`, `img_`, `tbl_`, `marker_` convention
- Pre-filled shapes (text present) are identified and excluded from push logic
- All expected shapes are present on every slide that uses them

## Step 2: Identify Marker Shapes

```python
for i, slide in enumerate(prs.slides):
    for shape in slide.shapes:
        if shape.name.startswith('marker_'):
            print(f'Slide {i+1}: {shape.name}')
```

**Check:** Every benefit/section slide has exactly one marker. No marker = slide cannot be found by name at runtime.

## Step 3: Inspect endParaRPr on Target Shapes

```python
from pptx.oxml.ns import qn
from lxml import etree

prs = Presentation('template.pptx')
for i, slide in enumerate(prs.slides):
    for shape in slide.shapes:
        if shape.name.startswith('txt_') and shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                end_rpr = para._p.find(qn('a:endParaRPr'))
                if end_rpr is not None:
                    print(f'Slide {i+1} [{shape.name}]: {etree.tostring(end_rpr, pretty_print=True).decode()}')
```

**Check:** `endParaRPr` has explicit `b`, `sz`, `solidFill` (with `srgbClr val`), and `latin typeface` attributes. If any are missing, add them via python-pptx before first test run.

## Step 4: Count Slides and Verify Structure

```python
prs = Presentation('template.pptx')
for i, slide in enumerate(prs.slides):
    layout = slide.slide_layout.name if slide.slide_layout else 'unknown'
    title = ''
    for shape in slide.shapes:
        if shape.has_text_frame and shape.name.lower().startswith('title'):
            title = shape.text_frame.text[:40]
    print(f'Slide {i+1}: layout={layout!r} title={title!r}')
```

**Check:** Total slide count matches expected. Every slide has the expected layout and title shape.

## Audit Sign-Off Checklist

- [ ] All dynamic shapes named with correct prefix convention
- [ ] Pre-filled shapes identified and listed; excluded from push logic in report.py
- [ ] All marker shapes present on deletable slides
- [ ] endParaRPr explicit attributes verified on all txt_ target shapes
- [ ] Slide count and layout confirmed
- [ ] Font choices confirmed: standard Windows/Office fonts only
- [ ] Shape name mapping documented in CLAUDE.md slide map

