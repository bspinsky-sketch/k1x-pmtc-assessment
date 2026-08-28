# CLAUDE_problems.md -- Failure Patterns and Mitigations (Tagged)

**Tags:** [GENERAL] = applies to all projects | [WEB] = Flask/Python web projects | [VBA] = Excel/VBA projects | [GIT] = git/version control

**Purpose:** RCA and context for known failure modes. Read when something goes wrong, when diagnosing unexpected behaviour, or when onboarding a new session phase. NOT required reading every session turn — that's `STANDING_RULES.md`.

**Actionable rules distilled from this file live in:** `STANDING_RULES.md` — read that every session.

**Last updated:** 2026-08-28 EDT (P047 added -- Peer Leaders score sourced from the wrong workbook table, plus a Python/Excel rounding mismatch)

---

## META-RULE -- Error Documentation Standing Order (2026-06-11)

**Standing order from Ben:** Whenever any error occurs during any session, Claude MUST:
1. Review CLAUDE_problems.md immediately for any related prior pattern
2. Document the new error with: error description, root cause, mitigation applied, and prevention steps
3. Write the entry to CLAUDE_problems.md before continuing work -- do not defer
4. Nothing should be lost to a compaction event -- document while the error is fresh

This applies to ALL error types: Python exceptions, Flask bugs, bash failures, tool failures, VBA errors, file corruption, subprocess issues, session bugs, and any unexpected behavior requiring a workaround.

---

## P001 [GENERAL] -- Context Compaction Corrupts Structured Data

**Severity:** High
**Pattern:** When a session runs long, conversation history is summarized (compacted). Structured data — especially tables with similar-looking values (numbered lists, matrices, codes) — is vulnerable to silent corruption. Values get transposed, substituted, or lost. Claude then uses the corrupted data confidently, with no awareness that an error occurred.

**Rule:**
- Never trust in-session memory for structured reference data after a long session.
- Always read source documents directly before any work that depends on structured data (mappings, formulas, named ranges, schema definitions, etc.).
- If a project has a reference file (e.g., CLAUDE.md), read it — but then verify its structured sections against the live source before relying on them.

---

## P002 [GENERAL] -- Reference Documents Written from Memory Inherit Compaction Errors

**Severity:** High
**Pattern:** A reference document (like CLAUDE.md) was created to survive compaction. But it was authored during an already-compacted session, so it encoded wrong data with false confidence. The document intended to prevent the problem became a vehicle for propagating it.

**Rule:**
- Never write or update a reference document from session memory alone.
- Always read the relevant source files directly before authoring or updating any reference document.
- After writing, read back the critical sections and verify them against the source before saving.

---

## P003 [GENERAL] -- Edit Tool Truncates End of Large Files

**Severity:** Medium
**Pattern:** The Edit tool drops trailing lines when editing large files — confirmed on JS scripts, Python scripts, and docx XML. The file appears intact when read from the middle, but the tail is silently missing. For scripts, the result is a silent syntax/runtime failure; for XML, a validation error on repack. The truncation recurs even after recovery if the Edit tool is used again on the same file.

**Primary workflow — PREVENTION (use this by default):**
- **Never use the Edit tool on large JS or Python scripts.** Use Python string replacement exclusively:
  ```python
  content = open('file.js').read()
  content = content.replace('old string', 'new string')
  open('file.js', 'w').write(content)
  ```
- For docx XML files (`word/document.xml` and similar), use the Edit tool only for small, isolated changes nowhere near the end of the file. For any change within the last ~20% of a large XML file, use Python string replacement instead.
- After any write — Python or otherwise — verify the tail before running: `tail -5 filename`

**Fallback — if truncation has already occurred:**
- Identify the last clean line with `tail -20 filename`
- Strip to the last clean point and reconstruct the tail in Python:
  ```python
  content = open('file.js').read()
  cut = content.rfind('\n[last known clean line]')
  open('file.js', 'w').write(content[:cut] + reconstructed_tail)
  ```
- For docx XML: find the last complete `>`, strip everything after it, then reconstruct the proper closing tags (`</w:rPr>`, `</w:r>`, `</w:p>`, `</w:tc>`, `</w:tr>`, `</w:tbl>`, `</w:body>`, `</w:document>`) based on context.

**Additional pattern — mixed-tool conflict (noted 2026-05-31):**
After Python rewrites a file, the Edit tool will refuse the next operation with "file modified since read." This is a secondary symptom of the same root cause: the Edit tool is not safe for large files that are also being modified by Python. The fix is the same — use Python for all edits on that file, not just some.

**Last updated:** 2026-06-11 18:46 EDT (P024-P026 added; meta-rule standing order added)

---

## P004 [GENERAL] -- soffice PDF Conversion Times Out in Long Sessions

**Severity:** Low-Medium
**Pattern:** The `python scripts/office/soffice.py` wrapper times out in long bash sessions, causing PDF conversion steps (needed for visual QA of .pptx files) to fail silently.

**Rule:**
- In long sessions, call soffice directly rather than through the Python wrapper:
  ```bash
  soffice --headless --convert-to pdf file.pptx --outdir /path/to/dir/ &
  sleep 20
  ```

---

## P005 [GENERAL] -- User Preference: No Multi-Select Questions

**Severity:** Medium (user experience)
**Pattern:** Claude used multiple-choice / multi-select question formats. User stated explicitly this is not acceptable: answers will always be given in free text.

**Rule:**
- Never use multi-select or multiple-choice question formats with this user.
- Ask clarifying questions in plain prose only.
- **Recurrence, 2026-08-26/27 (this session):** Used AskUserQuestion's multiple-choice picker twice on the workbook-scope-change question before Ben repeated the correction directly ("Stop using the multiple-choice question gadget, just ask a question and I'll answer"). STANDING_RULES.md already stated this rule in plain text at session start; it was not re-checked before reaching for the tool. Corrected immediately -- switched to plain-prose questions for the rest of the session (see P038 for the related pattern of not re-checking STANDING_RULES.md's exact wording before acting).

---

## P006 [GENERAL] -- Providing Unverified URLs / The URL Rule

**Core principle:** Research is useless unless it can be human verified.

**Severity:** Medium
**Pattern:** Claude cited a URL as a source without first fetching it to verify it was accessible and pointed to the expected content. The URL redirected to an unrelated page, making the citation useless and eroding trust in the research.

**Rule:**
- Never cite a URL as a source without first fetching it with `mcp__workspace__web_fetch` to confirm it (a) resolves without redirect to an unrelated page, and (b) contains the content being cited.
- If a URL cannot be fetched or redirects, do not cite it. Either find an alternative source or disclose that the source could not be verified.
- Receiving partial content from a fetch is not sufficient verification. Community forums, gated portals, and login-walled pages often return snippet content publicly before requiring authentication for the full page. Verify that the fetched content actually contains the specific claim being cited — not just that the fetch returned something.
- This applies to all URLs, including those returned by web search results.

---

## P007 [GENERAL] -- Claiming Prior Work Was Not Done Without Reading the Transcript

**Severity:** High
**Pattern:** When asked whether a prior task had been completed, Claude said it could not confirm and offered to redo the work — without first reading the session transcript. The transcript was accessible the entire time and contained the answer. The failure had two compounding causes: (1) Claude misread a compacted summary that noted gaps as meaning the work was not done, rather than substantially done with specific gaps remaining; (2) Claude did not apply the obvious fix — read the transcript — before responding.

**Rule:**
- Any time the question is "has X already been done?" or "was X researched/completed?", read the session transcript before answering. Do not rely on session summaries for work completion status.
- Session summaries are lossy. They note gaps and open items prominently. "Gaps exist" does not mean "work not done."
- The transcript is the primary source for what actually happened. It is accessible via the .jsonl file in the project outputs folder. Use it.
- Never offer to redo work before verifying whether it was already done.
- **Last added:** 2026-05-31

---

## P008 [GENERAL] -- Within-Session State Loss on Multi-Item Tracking Tasks

**Severity:** High
**Pattern:** During a long session involving a multi-item checklist (e.g., 15 benefits, each with 6 content slots), Claude reached a correct resolution for several items mid-session, then later reconstructed the open/closed list from scratch — contradicting earlier conclusions without noticing. Specifically: B6, B9, B10 Gain 2 were correctly marked resolved, then re-added to the open list in a subsequent turn. This is distinct from P001 (cross-session compaction) and P007 (transcript blindness before claiming work undone). The failure is within a single session: conclusions decay across turns when the context is large.

**Root cause:** Claude regenerates state summaries from the full context window rather than from a persistent record. In a long session, earlier conclusions are present in context but are weighted less than recent content, and are silently dropped when Claude reconstructs a list.

**Rule:**
- For any task involving a multi-item checklist or tracking structure with more than ~6 items, maintain a persistent session state file on disk (e.g., `SESSION_STATE.md` in the project folder).
- Update the file immediately after any item is resolved — do not rely on in-context memory across turns.
- Before stating any item's status (open, closed, resolved), read the session state file. Do not reconstruct from memory.
- When a session state file exists, reference it explicitly: "Per SESSION_STATE.md, the open items are..."
- **Last added:** 2026-06-01

---

## P009 [GENERAL] -- Compaction Cascade: Second-Generation Summaries Are Increasingly Lossy

**Severity:** High
**Pattern:** A session that has already been compacted once contains a lossy summary at the top. When that session is compacted again, the new summary is generated from context that is itself already a summary — a second-generation compression. Each generation loses more detail, and errors introduced early propagate forward with increasing confidence. This project has already experienced at least one compaction cycle.

**Rule:**
- Never rely on compaction summaries as a source of truth for any structured data, decision, or completion status.
- The antidote is files, not context. Every decision, completion, and standing rule must be written to a persistent file (CLAUDE.md, CLAUDE_problems.md, PROJECT_STATE.md) before the session ends or risks compaction.
- At the start of any session that shows a compaction summary header, treat ALL in-context facts as unverified until cross-checked against source files.
- **Last added:** 2026-06-01

---

## P010 [GENERAL] -- Document Section Drift: No Canonical Map for Multi-Section Files

**Severity:** Medium
**Pattern:** BVF_Benefit_Headers.docx has grown through multiple sessions into a layered document with 4+ appended sections (original headers, 2+2+2 rewrite, research pass 2, B11 supplement). The authoritative content for any given benefit is distributed across sections with no index. A future session — or a later turn in this one — cannot reliably determine which paragraph contains the current version of a specific stat without reading hundreds of paragraphs.

**Rule:**
- Any document that grows through appending across sessions must have a section map maintained in PROJECT_STATE.md.
- When a new section is appended to a document, update the section map immediately.
- When editing content that exists in multiple sections, update all instances or explicitly mark earlier instances as superseded.
- Current BVF_Benefit_Headers.docx section map is in PROJECT_STATE.md.
- **Last added:** 2026-06-01

---

## P011 [GENERAL] -- Decision Decay: Session Decisions Not Written to Persistent Files

**Severity:** High
**Pattern:** Decisions made mid-session (stat choices, source substitutions, framing directions, standing rules given by Ben) live only in the conversation context. When the session is compacted or ends, these decisions are either lost or encoded imprecisely in a summary. Future sessions then re-litigate or contradict them. This session produced multiple decisions not yet in CLAUDE.md: B8/B14 "industry benchmark" attribution, B1 Pain 2 calculation method, B8 Pain 2 McKinsey substitution, IBM 2025 update, B1/B5 Gain 2 direction.

**Rule:**
- Any time Ben gives a direction that constitutes a standing decision (source choice, calculation method, attribution standard, content direction), write it to CLAUDE.md Key Decisions Log before the next tool call.
- Any time a new standing behavioral rule is stated by Ben, write it to CLAUDE_problems.md Standing Rules immediately.
- Do not accumulate decisions in context with the intention of writing them "at the end" — they will be lost if compaction occurs first.
- **Last added:** 2026-06-01

---

## P012 [GENERAL] -- Workbook Unreadable: Root Cause Unknown

**Severity:** Medium
**Pattern:** `ITSM Business Value Framework.xlsx` was unreadable to both the sandbox and LibreOffice. Excel was confirmed not open; no active Excel processes. The workaround was renaming the file — the renamed copy (`v0.01.xlsx`) opened successfully. This is distinct from the earlier mount/BytesIO issue — that was a path problem; this is a file-state problem.

**Status:** Workaround only — root cause unresolved and undiagnosed. Candidates include: GeniusDrive cloud sync holding a lock mid-sync, corrupted file state from a prior write operation, or a Windows permissions artifact. None confirmed.

**Mitigation:**
- If a read fails with a file-unreadable error, ask Ben whether a sync process may be active, then retry. If still unreadable, rename as a last resort.
- Do not state a confident diagnosis without evidence — the Excel shadow-copy explanation was incorrect.
- **Last added:** 2026-06-01

---

## P013 [GENERAL] -- Confabulation from Compacted Memory Presented as Verified Fact

**Severity:** Critical
**Pattern:** After compaction, Claude reconstructs file contents (cell values, paragraph text, URLs, cell references) from the compaction summary and states them with the same confidence as directly-read content. The fabricated Discovery cell references during T-04 (B36, B42, B44, B45, B46 — none of which contained the flagged content) are the clearest example. Ben received an unusable list of corrections and had no way to distinguish verified claims from invented ones. This forced granular per-item prompting as the only error-catching mechanism, wasting significant time.

**Root cause:** Claude has no internal flag distinguishing "read in this session" from "reconstructed from memory." Both feel equally certain. Compaction summaries are particularly dangerous because they are written in declarative language that encodes reconstructions as facts.

**Rule:**
- Before stating the contents of any cell, paragraph, shape, formula, or file location, read it in the current session. No exceptions.
- If content has not been read in the current session, say so explicitly: "I need to read that first."
- Never present a reconstruction from a compaction summary as a verified fact.
- Diagnoses and root causes must be supported by evidence read in the current session. Inferences must be labeled as such.
- **Last added:** 2026-06-01

---

---

## P014 [VBA] -- VBA: Application.Range() Fails for Sheet Names with Spaces When PowerPoint Is Open

**Severity:** High — causes silent skips with no visible error until the summary dialog
**Discovered:** W3-03 ExportToReport QA, 2026-06-07. Produced 4 skipped rows every run.
**Pattern:** `Application.Range("'Sheet Name'!A1:B10")` fails silently under `On Error Resume Next` when PowerPoint is the foreground application and a sheet name contains spaces. The range object returns `Nothing` even though the address is syntactically correct. The error manifests as a range-resolution failure on any row referencing a multi-word sheet name (e.g., `Business Value Summary`).

**Additional finding (Ben's observation):** The sourceID string as stored in the Report sheet contained the sheet name in single-quotes with an extra trailing single quote — e.g. `'Business Value Summary'!O2:R16'` — which the original `ResolveRangeAddress` was not stripping, compounding the failure.

**Root cause:** Two compounding issues: (1) `Application.Range()` is unreliable for cross-sheet references when PPT holds focus; (2) the source string had an extra trailing quote that wasn't being cleaned.

**Fix applied in `Macro - ExportToReport (complete).txt`:**
Rewrote `ResolveRangeAddress` to:
1. Parse sheet name and range part separately using `InStr(addr, "!")` as the split point
2. Strip ALL leading and trailing single quotes from both parts using `Do While` loops (handles any number of quote characters, not just one)
3. Use `For Each ws In ThisWorkbook.Worksheets` + `StrComp` to locate the sheet (immune to focus/foreground issues under `On Error Resume Next`)
4. Fall back to `Application.Range("'" & sheetPart & "'!" & rangePart)` only as strategy 2

**Rule for next project:**
- Never use `Application.Range(addr)` for ranges that may include multi-word sheet names — use the `For Each ws` worksheet loop as the primary strategy from the start.
- Strip trailing/leading quotes from both the sheet name and the range part using `Do While` loops — not a single `Trim` or `Replace`, which misses doubled quotes.
- After building ExportToReport for a new project, run a full push with PPT open before declaring it functional. Sheet-name space issues will not surface in test runs where PPT is closed.

---

## P015 [VBA] -- VBA: Chart.Export Produces Empty PNG When PowerPoint Is Open

**Severity:** High — chart images push silently but render as blank shapes in the deck
**Discovered:** W3-03 ExportToReport QA, 2026-06-07. All chart images on slides 20–27 were blank/missing in the first test run.
**Pattern:** `ChartObject.Chart.Export "path.png"` silently produces an empty or zero-byte PNG file when PowerPoint is the foreground application and has taken rendering focus from Excel. The subsequent `AddPicture` call reads the empty file and creates a shape with no embedded image — no error is raised at any point.

**Root cause:** Excel's chart rendering engine cannot export to file when another Office application holds the rendering context. The failure is completely silent.

**Fix applied:**
Replaced `Chart.Export` + `AddPicture` with clipboard-based approach for ALL image pushes (both chart and range):
```vba
DoEvents   ' <-- only BEFORE CopyPicture
cht.CopyPicture Appearance:=xlScreen, Format:=xlPicture
' NO DoEvents here — go straight to Paste (see P016)
Dim pasted As Object
Set pasted = slide.Shapes.Paste()
```
After paste, resize and position the new shape, then delete the placeholder.

**Rule for next project:**
- Never use `Chart.Export` + `AddPicture` in any ExportToReport implementation where PowerPoint will be open during the macro run. Use `CopyPicture` + `Shapes.Paste()` exclusively.
- Apply the same clipboard approach to range images (`rng.CopyPicture`) — do not mix strategies between chart and range cases.
- The placeholder shape is deleted AFTER the paste and rename, not before — deleting it first removes the positioning target.

---

## P016 [VBA] -- VBA: DoEvents Between CopyPicture and Paste Clears the Clipboard

**Severity:** High — causes a runtime error: "Clipboard is empty or contains data which may not be pasted here"
**Discovered:** W3-03 ExportToReport QA, 2026-06-07. Affected Benefit 10 (B10) after the P015 chart fix was applied; all other benefits passed. Root cause took one full debug cycle to identify.
**Pattern:** A `DoEvents` call between `CopyPicture` and `Shapes.Paste()` yields control to Windows, which processes pending window messages. One of those messages clears the clipboard. The subsequent `Paste()` then fails with a runtime error because the clipboard is empty.

**Why B10 specifically:** The B10 benefit slide had an extra processing step between the CopyPicture and Paste calls compared to other slides, making the timing window wider. Once `DoEvents` was removed, B10 passed on the same run as all other slides.

**Root cause:** `DoEvents` is a yielding mechanism — it allows Windows message processing, which includes clipboard-clearing operations from background processes. Clipboard contents are not guaranteed to persist across a `DoEvents` call.

**Fix applied:**
Remove ALL `DoEvents` calls between `CopyPicture` and `Paste()`. Keep exactly one `DoEvents` immediately BEFORE `CopyPicture` (to let Excel finish rendering), and go straight to `Paste()` after. No intermediate `DoEvents`.

```vba
DoEvents                                              ' OK — before copy
cht.CopyPicture Appearance:=xlScreen, Format:=xlPicture
' ← NO DoEvents here ←
Set pasted = slide.Shapes.Paste()                    ' must be immediate
```

**Rule for next project:**
- Never place `DoEvents` between any `CopyPicture` call and the corresponding `Shapes.Paste()`.
- One `DoEvents` before `CopyPicture` is correct and necessary — it is the `DoEvents` AFTER that causes the failure.
- If B10 (or any specific slide) is the only one failing a clipboard paste, suspect a `DoEvents` or any other yielding call in the code path between the copy and paste.

---

## P017 [VBA] -- PPTX Template: Text Formatting Not Inherited Without Explicit endParaRPr Attributes

**Severity:** Medium — VBA push succeeds but text renders with wrong formatting (font, size, bold, color)
**Discovered:** W3-03 ExportToReport QA, 2026-06-07. `txt_annual` and `txt_3yr` shapes on all 15 benefit slides showed incorrect formatting (not Calibri 28pt White Bold) after text was pushed via ExportToReport.
**Pattern:** A PowerPoint shape's `endParaRPr` (end-of-paragraph run properties) defines the formatting of any text pushed into that paragraph by VBA. If `endParaRPr` omits explicit attributes (`b`, `solidFill`, `latin` typeface), VBA-pushed text inherits nothing and renders with default formatting — even if the shape visually appears correctly formatted when viewed in PowerPoint with placeholder text.

**Why it's hard to catch in design:** In PowerPoint's normal editing mode, placeholder text may display correctly because formatting is inherited from a theme or layout master. After a VBA text push, that inheritance chain is bypassed and only the explicit XML attributes in `endParaRPr` are applied.

**Root cause:** The template's benefit slide shapes had `<a:endParaRPr lang="en-US" sz="2800" dirty="0"/>` — correct size, but missing `b="1"` (bold), `<a:solidFill>` (white), and `<a:latin typeface="Calibri"/>`. VBA-pushed text therefore rendered as non-bold, black, default-font.

**Fix applied:**
Updated `endParaRPr` on all 15 benefit slides in the template via python-pptx:
```xml
<a:endParaRPr lang="en-US" sz="2800" b="1" dirty="0">
  <a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>
  <a:latin typeface="Calibri"/>
</a:endParaRPr>
```
Also updated existing `<a:r><a:rPr>` runs in the same shapes to carry the same explicit attributes.

**Rule for next project:**
- After building any slide template that will receive VBA-pushed text, inspect the raw XML of each target shape's `endParaRPr`. Verify it has ALL required formatting attributes explicitly — `b`, `sz`, `solidFill` with color, `latin` typeface.
- Do not trust the visual appearance of shapes in PowerPoint's editing view — placeholder text rendering does not reflect what VBA will produce.
- The fix is always at the template level (XML), not in the VBA push code. If text looks wrong after a push, open the PPTX, unpack it, find the shape's XML, and add the missing `endParaRPr` attributes.
- Script the template XML fix in python-pptx and run it against the template before any ExportToReport testing — doing it after the first failed run wastes a full test cycle.

---

## P019 [VBA] -- VBA: Worksheet_Calculate Event Causes Infinite Loop When Handler Modifies Sheet Structure

**Severity:** High — locks up Excel; requires Ctrl+Break or force-quit
**Discovered:** W3-05c QA, 2026-06-08. RunRowVisibility called from Data sheet Worksheet_Calculate; hiding/showing rows on Discovery and Framework sheets triggered recalculation, re-firing Worksheet_Calculate.
**Pattern:** Any `Worksheet_Calculate` handler that modifies row/column visibility, cell values, or any other property that can trigger recalculation will re-fire the event, creating an infinite loop.

**Fix:**
Wrap the entire handler body with `Application.EnableEvents = False` / `Application.EnableEvents = True`, including the `Failed` handler so events are always restored even on error.

```vba
Public Sub RunRowVisibility()
    On Error GoTo Failed
    Application.EnableEvents = False
    Application.ScreenUpdating = False
    ' ... all work here ...
    Application.EnableEvents = True
    Application.ScreenUpdating = True
    Exit Sub
Failed:
    Application.EnableEvents = True
    Application.ScreenUpdating = True
End Sub
```

**Rule for next project:**
- Any `Worksheet_Calculate` or `Worksheet_Change` handler that writes back to Excel (hides rows, sets values, changes formatting) must use `Application.EnableEvents = False` as its first substantive line, restored unconditionally in both the normal exit and the error handler.

---

## P020 [VBA] -- VBA: ChartObject.CopyPicture Produces Empty Clipboard When Chart Is Hidden

**Severity:** Medium — silent failure; clipboard empty at Shapes.Paste (error -2147188160)
**Discovered:** W3-05c + ExportToReport integration, 2026-06-08. RowVisibility had hidden charts for deselected benefits (`co.Visible = False`). ExportToReport then attempted CopyPicture on those hidden charts before the slideDelete pre-pass (W3-05e) eliminated the wasted pushes.
**Pattern:** `ChartObject.CopyPicture` on a chart where `Visible = False` completes without raising an error but leaves the clipboard empty. Same external symptom as P018 chart case (error -2147188160 at Shapes.Paste) but different cause.

**Fix (defensive, still present in code):**
Temporarily show the chart before copying, then restore its visibility:

```vba
Dim chtWasVisible As Boolean
chtWasVisible = cht.Visible
If Not chtWasVisible Then
    Application.ScreenUpdating = False
    cht.Visible = True
End If
' ... CopyPicture ...
If Not chtWasVisible Then
    cht.Visible = False
    Application.ScreenUpdating = True
End If
```

**Note:** With the slideDelete pre-pass (W3-05e) in place, ExportToReport never attempts to push a chart on a slide that will be deleted — so in practice this code path is rarely hit. The fix is retained as a defensive measure.

---

## P021 [VBA] -- VBA: Application.Goto Fails on Protected Sheets with xlUnlockedCells Selection

**Severity:** Medium — runtime error 1004; macro aborts
**Discovered:** W3-05b QA, 2026-06-08. Nav buttons on modNavigation used `Application.Goto ws.Cells(1,1), True` to scroll to the top of the target sheet after activating it. This fails when `ApplyUserMode` is active and sheets are protected with `EnableSelection = xlUnlockedCells` — row 1 contains the nav button shapes and title, which are locked cells.
**Pattern:** `Application.Goto` with `Scroll:=True` attempts to select the target cell. If the cell is locked and the sheet's `EnableSelection = xlUnlockedCells`, the select fails with error 1004.

**Fix:**
Replace `Application.Goto` with direct scroll — no cell selection required:

```vba
With ThisWorkbook.Worksheets(targetSheet)
    .Activate
    ActiveWindow.ScrollRow = 1
    ActiveWindow.ScrollColumn = 1
End With
```

**Rule for next project:**
- Never use `Application.Goto` for navigation in sheets that will be protected with `xlUnlockedCells`. Use `Activate` + `ScrollRow`/`ScrollColumn` instead.
- The same applies to `Workbook_Open` navigation stubs — remove any `.Cells(1,1).Select` after `ApplyUserMode` has run.

**Rule for next project:**
- Never call `CopyPicture` on a hidden ChartObject. Always check `cht.Visible` first and show temporarily if needed.
- The slideDelete pre-pass (standard architecture — see Key Decisions Log) eliminates most cases where this would occur; the explicit visibility check is belt-and-suspenders.

---

## P022 [VBA] -- VBA: ChartObject.CopyPicture Fails Silently Under DrawingObjects:=True Sheet Protection

**Severity:** High — silent failure; clipboard empty; Shapes.Paste error -2147188160
**Discovered:** W3-06b end-to-end test, 2026-06-08. ExportToReport ran successfully in dev mode but failed on img_comboChart (slide 18, ROI Analysis) once user mode was active. Same clipboard-empty symptom as P018/P020 but different cause.
**Pattern:** `ChartObject.CopyPicture` silently produces an empty clipboard when the chart's parent sheet is protected with `DrawingObjects:=True`. The protection call succeeds and the chart is visible — the failure is specific to the interaction between DrawingObjects protection and CopyPicture.

**Fix:**
Add `UnprotectAll` and `ReprotectAll` helpers to modDevMode. Call them at the start and end of ExportToReport:

```vba
' In ExportToReport, after PPT minimize:
modDevMode.UnprotectAll

' In ExportToReport, before PPT window restore:
modDevMode.ReprotectAll
```

`UnprotectAll` unprotects workbook structure and all sheets using DEV_PASSWORD.
`ReprotectAll` re-applies full user-mode protection (DrawingObjects:=True, Contents:=True, etc.) without touching app-level chrome.

**Rule for next project:**
- ExportToReport must always call `modDevMode.UnprotectAll` at the start of its run and `modDevMode.ReprotectAll` at the end when the workbook uses user-mode sheet protection.
- Do not assume VBA bypasses DrawingObjects protection for CopyPicture — it does not.

---

## P018 [VBA] -- VBA: CopyPicture Fails When PowerPoint Has Screen Rendering Focus

**Severity:** High — silent failure at runtime; error only surfaces in the summary dialog
**Discovered:** W3-05c QA, 2026-06-08. Manifested across three runs on rows 38, 46 (ranges), and 363 (chart).
**Pattern:** `CopyPicture Appearance:=xlScreen` fails when PowerPoint has screen rendering focus. For ranges, this produces error 1004 ("CopyPicture method of Range class failed"). For charts, it fails silently — no error raised, but the clipboard is left empty, causing `Shapes.Paste` to fail with error -2147188160 ("Clipboard is empty or contains data which may not be pasted here"). Both failure modes share the same root cause: `xlScreen` requires Excel to hold screen rendering focus, which PPT steals when open or being edited.

**Fix — ranges, iteration 1 (insufficient):**
Added `ThisWorkbook.Activate` + `rng.Parent.Activate` + `DoEvents` before `rng.CopyPicture Appearance:=xlScreen`. Resolved rows 38 and 46 but failed on row 40 when PowerPoint was actively being edited — more aggressive focus stealing than a passive open.

**Fix — ranges, iteration 2 (final):**
Replaced `Appearance:=xlScreen` with `Appearance:=xlPrinter`. The print pipeline has no screen focus dependency.

**Fix — charts, iteration 1 (insufficient):**
xlPrinter attempted for charts. Raises error 5 ("Invalid procedure call or argument") on every chart — `Appearance:=xlPrinter` is not a valid argument for `ChartObject.CopyPicture`. Only valid for `Range.CopyPicture`.

**Fix — charts, iteration 2 (discarded — functional but unacceptable UX):**
Minimized PPT window before each chart copy, restored after. Eliminated error but produced repeated minimize/restore animation on every chart push — unacceptable for end users.

**Fix — charts, iteration 3 (insufficient — PPT window restores mid-run):**
Minimize PPT once at the start of `ExportToReport`. Confirmed this resolves early chart copies. But in W3-06b testing: after UnprotectAll/ReprotectAll (P022) was added and early charts started succeeding, a later chart (B13/img_barChart, row 369) still failed intermittently. Exactly one chart fails per run; which chart fails changes across runs. Pattern: `Shapes.Paste` calls earlier in the run apparently restore the PPT window on some executions, returning screen rendering focus to PPT and causing the next `xlScreen CopyPicture` to silently produce an empty clipboard.

Added per-chart re-minimize (`pres.Windows(1).WindowState = 2` before every chart `CopyPicture`). This suppresses the failure for the early chart (B1) but the failure moves to a later chart (B13) — the root cause (PPT window restoration by Shapes.Paste) persists.

**Fix — charts, final (confirmed working 2026-06-08):**
Retry loop in PushImage chart case: up to 3 attempts, with 1-second wait between retries. Each attempt: re-minimize PPT, activate workbook+sheet, DoEvents, CopyPicture, then Paste with `On Error Resume Next` to catch -2147188160 without aborting. On success, position shape and exit function. On 3 consecutive failures, surface error with attempt count.

```vba
For chtTry = 1 To 3
    ' Show chart temporarily if hidden (P020)
    chtWasVisible = cht.Visible
    If Not chtWasVisible Then
        Application.ScreenUpdating = False
        cht.Visible = True
    End If

    ' Re-minimize PPT (P018)
    On Error Resume Next
    pres.Windows(1).WindowState = 2
    On Error GoTo Failed
    ThisWorkbook.Activate
    cht.Parent.Activate
    DoEvents
    cht.CopyPicture Appearance:=xlScreen, Format:=xlPicture
    ' No DoEvents here — P016

    If Not chtWasVisible Then
        cht.Visible = False
        Application.ScreenUpdating = True
    End If

    ' Catch clipboard-empty error to allow retry
    chtPasteErr = 0
    On Error Resume Next
    Set chtPasted = slide.Shapes.Paste()
    chtPasteErr = Err.Number
    On Error GoTo Failed

    If chtPasteErr = 0 And Not chtPasted Is Nothing And chtPasted.Count > 0 Then
        Exit For    ' success
    End If
    If chtTry < 3 Then Application.Wait Now + TimeValue("0:00:01")
Next chtTry
```

The chart case handles positioning and exits the function directly; the shared paste block after `End Select` handles Range only.

**Rule for next project:**
- For `Range.CopyPicture`: use `Appearance:=xlPrinter` — print pipeline, no screen focus dependency.
- For `ChartObject.CopyPicture`: `xlPrinter` is NOT valid (error 5). Use `xlScreen` with the full retry loop above.
- The retry loop is the final resolution — do not attempt to debug PPT window restoration order.
- `pptPres.Windows(1).WindowState = 2` minimizes the PPT window. Object model calls remain fully functional while minimized.
- Note: xlScreen failure mode differs by object type: Range → error 1004 (raised); Chart → silent empty clipboard (caught at Shapes.Paste as -2147188160).
- Do not confuse with P015 (Chart.Export) or P016 (DoEvents clipboard race).

---

## P023 [VBA] -- VBA: Or/And Operators Do Not Short-Circuit

**Severity:** High — causes error 91 (Object variable or With block variable not set) in compound conditions involving Object properties
**Discovered:** W3-06b end-to-end test, 2026-06-08. Retry loop's post-loop check raised error 91 instead of surfacing the actual paste failure message.
**Pattern:** VBA's `Or` and `And` operators **always evaluate all operands** — they never short-circuit. Compound conditions like `If obj Is Nothing Or obj.Count = 0` or `If err = 0 And Not obj Is Nothing And obj.Count > 0` evaluate `obj.Count` even when `obj Is Nothing`, raising error 91.

```vba
' ❌ WRONG — VBA evaluates chtPasted.Count even when chtPasted Is Nothing:
If chtPasteErr <> 0 Or chtPasted Is Nothing Or chtPasted.Count = 0 Then ...
If chtPasteErr = 0 And Not chtPasted Is Nothing And chtPasted.Count > 0 Then ...

' ✅ CORRECT — separate Ifs guarantee safe evaluation order:
If chtPasteErr <> 0 Then ...       ' check error first
If chtPasted Is Nothing Then ...   ' then nil check
If chtPasted.Count = 0 Then ...    ' only reached when not Nothing
```

**Rule for next project:**
- Never use compound `Or`/`And` conditions that mix `Is Nothing` checks with property access on the same object in VBA. Split into separate `If` statements.
- This applies to any Object variable whose validity is in question: ShapeRange, Range, Worksheet, etc.

---

## Standing Rules
See `STANDING_RULES.md` — that is the single authoritative list. Do not maintain a duplicate here.

---

## P024 [WEB] -- Flask: session.modified Not Always Set by Nested Dict Assignment

**Severity:** High -- causes session data to be silently dropped from the cookie; symptoms appear as 500 errors or redirect loops on the results page
**Discovered:** ITSMweb Phase 3, 2026-06-11. session['kpis'] = kpis executed without error and the 302 redirect was returned, but decoding the Set-Cookie header showed kpis absent from the cookie.
**Root cause:** Flask's session (SecureCookieSession, a subclass of CallbackDict) calls on_update (sets modified = True) via __setitem__. In practice -- particularly when a long-running subprocess (LibreOffice) runs between two session assignments -- the modification flag does not reliably propagate to the final serialized cookie. The CPython/Flask version interaction is not fully characterized; the mitigation is deterministic and free.

Symptom sequence:
1. POST handler sets session['priorities'] = priorities (mod flag set)
2. Subprocess runs (LibreOffice recalculation -- several seconds)
3. session['kpis'] = kpis executes without raising
4. Handler returns redirect(...) -- 302 with Set-Cookie
5. Decoding Set-Cookie: only 'profile' and 'priorities' present -- 'kpis' missing
6. Subsequent GET to /submitted: Jinja2 raises UndefinedError: 'kpis' is undefined

Fix:
    session['kpis'] = kpis
    session.modified = True   # explicit -- never rely on implicit detection after long-running work

Rule for all future Flask projects:
- After any session mutations that include a long-running operation (subprocess, network call, file I/O), always set session.modified = True explicitly after the last mutation.
- Treat implicit modification detection as unreliable whenever a subprocess runs mid-handler.
- When debugging "session key missing after redirect": decode the Set-Cookie header on the response directly -- session_transaction() reads/rewrites the cookie and can mask the bug.

---

## P025 [WEB] -- Bash: cat-append-heredoc Corrupts Existing Code Files

**Severity:** High -- silently mangles the target file, producing SyntaxError on next import
**Discovered:** ITSMweb Phase 3, 2026-06-11. Attempted to append a debug route to routes.py using cat >> routes.py with a heredoc. The heredoc body contained Python string literals whose quotes interacted with the shell, truncating routes.py mid-line.
**Root cause:** cat >> file << HEREDOC appends a heredoc to an existing file. If the heredoc body contains shell-significant characters (quotes, dollar signs, backslashes), the shell corrupts the boundary between existing and new content.

Fix: Restore from known-good content using Python write:
    with open('path/to/file.py', 'w') as f:
        f.write(full_correct_content)

Rule for all future projects:
- Never use cat >> file with heredoc to append to existing code files. Use Python writes or the Edit tool.
- After any file write or append, always verify syntax: python3 -c "import ast; ast.parse(open('file.py').read()); print('OK')"
- To append safely: read full file in Python, concatenate new content, write complete result.

---

## P026 [GENERAL] -- Write Tool: Truncates Long Files at ~50-60 Lines

**Severity:** High -- file appears written successfully (no error) but tail content is missing; discovered only at runtime via TemplateSyntaxError or ImportError
**Discovered:** ITSMweb Phase 3, 2026-06-11. Write tool used to create submitted.html (~120 lines). Tool reported success but file was truncated at line 53, ending mid-attribute. Jinja2 raised: TemplateSyntaxError: Unexpected end of template. Jinja was looking for 'endblock'.
**Root cause:** The Write tool has an undocumented line-length limit (~50-60 lines observed). Files exceeding this threshold are written partially with no error signal. Previously documented as P003 in the Accertify CLAUDE_problems.md for identical behavior.

Fix: Write long files via bash cat-heredoc with SINGLE-QUOTED delimiter (prevents variable expansion):
    cat > /path/to/file.html << 'ENDOFFILE'
    ...full content...
    ENDOFFILE
    echo "Lines: $(wc -l < /path/to/file.html)"
    tail -3 /path/to/file.html

Rule for all future projects:
- Never use the Write tool for files longer than ~40 lines. Use bash cat-heredoc with single-quoted delimiter.
- Always verify file length and tail after writing: wc -l and tail -3.
- For HTML templates: verify closing tag (e.g., endblock) is present. For Python: run ast.parse.
- The Edit tool is safe for targeted modifications to existing files -- it sends a diff, not a full rewrite.

---

## P027 [WEB] -- Flask: request.app Does Not Exist -- Use current_app

**Severity:** Medium -- raises AttributeError on every request, taking down all routes
**Discovered:** ITSMweb Phase 6, 2026-06-12. before_request_hook used request.app.config to read app config. Every request failed with: AttributeError: 'Request' object has no attribute 'app'.
**Root cause:** Flask's request context object does not expose the application as request.app. The correct accessor is current_app from flask, which is a context local proxy to the active Flask application during a request.

Fix:
    from flask import current_app
    # Wrong:  request.app.config.get(...)
    # Right:  current_app.config.get(...)

Rule for all future Flask projects:
- Never use request.app -- it does not exist.
- Always import and use current_app when accessing app config, extensions, or logger from within a request context (before_request hooks, view functions, etc.).
- request gives you: method, args, form, json, headers, endpoint, blueprint, url -- not the app.

---

## P028 [WEB] -- LibreOffice OOM on Render Free Tier

**Severity:** Critical -- calculation engine fails on every production request
**Discovered:** ITSMweb Phase 10 production testing, 2026-06-12 17:05 EDT

LibreOffice subprocess requires ~300MB RAM at startup. Render free tier provides 512MB total. With Flask/gunicorn using ~100-150MB, the container runs out of memory when LibreOffice launches, producing an empty stderr with return code 1 (SIGKILL -- no cleanup output).

Sequence of failures encountered:
1. javaldx launch failure (missing Java) -- stubbed javaldx
2. javaldx path read failure -- made stub echo /tmp
3. Empty stderr, return code 1 (OOM kill) -- fundamental resource limit

**Fix:** Replace LibreOffice formula recalculation with xlcalculator (pure Python, in-process). calculator.py rewritten to use ModelCompiler + Evaluator -- no subprocess, no memory spike, reads formulas directly from the xlsx workbook. xlcalculator added to requirements.txt.

LibreOffice remains in the Docker image for PDF conversion (emailer.py) but is no longer used for recalculation.

**Rule for all future projects on free-tier hosting:**
- Never use LibreOffice for formula recalculation on Render free tier (512MB RAM).
- Use xlcalculator for Python-based formula evaluation instead.
- If LibreOffice is needed for PDF conversion, budget RAM accordingly or upgrade to a paid plan.

---

## P029 [WEB] -- .dockerignore Excluded *.xlsx and *.pptx

**Severity:** High -- workbook and PPT template missing from Docker image; calculation and report generation both fail
**Discovered:** ITSMweb Phase 10 production testing, 2026-06-12

.dockerignore contained lines: `*.xlsx`, `*.xlsm`, `*.pptx`. These excluded the master workbook (ITSM Business Value Framework v1.xlsx) and PPT template (ITSM_BVF_Report_v1.pptx) from the Docker build, even though both were committed to git.

Error seen: `[Errno 2] No such file or directory: '/app/ITSM Business Value Framework v1.xlsx'`

**Fix:** Remove *.xlsx, *.xlsm, *.pptx lines from .dockerignore.

**Rule for all future projects:**
- Never add *.xlsx, *.xlsm, or *.pptx to .dockerignore unless those files are truly build artifacts.
- Reference data files that are committed to git must not be in .dockerignore.

---

## P030 [WEB] -- python-pptx: Writing to Pre-Baked Template Shapes Overwrites Formatted Content

**Severity:** High -- silently corrupts pre-filled slide content; formatting is lost even if text is the same
**Discovered:** ITSMweb Phase 9, 2026-06-15. First draft of report.py would have pushed Pain1_text, Pain1_callout, Whatif_text, Gain_text, Benefit_category, Benefit_name from BENEFIT_HEADERS and a catch-all `values` dict. These shapes are pre-filled in the 36-slide template with correctly formatted text. Caught by inspecting template content before executing the code.

**Pattern:** When working with a PPTX template that has 15+ per-benefit slides, it is easy to assume all benefit text must be pushed by the generator. In reality, static content (headers, callouts, citations) is baked into each slide at template build time; only dynamic values (callouts tied to user inputs, tbl_calc data cells, chart images) need runtime population. Pushing to pre-baked shapes replaces formatted runs with plain-text runs, stripping bold, color, size, and font.

**Root cause:** Generated code assumed all content was dynamic without inspecting the template's existing text content first.

**Detection:** `python3 -c "from pptx import Presentation; prs = Presentation('template.pptx'); [print(f'[{s.name}]: {s.text_frame.text[:80]}') for slide in prs.slides for s in slide.shapes if s.has_text_frame and s.text_frame.text.strip()]"` -- run this before writing any populate loop.

**Rule for all future python-pptx projects:**
- Before writing any shape-population code, inspect the template to identify which shapes are pre-filled vs. which are empty placeholders.
- Only push to shapes that are confirmed EMPTY (or whose content is intentionally replaced). Leave pre-filled shapes alone.
- The inspection command above is fast (~2 seconds) and should be run as the first step of any report generator build, not inferred from slide structure diagrams.
- For benefit/section slides that are duplicated across a template (e.g., 15 identical-structure slides), inspect ONE representative slide's shape content before assuming any shape is empty.

---

## Standing Rules
See `STANDING_RULES.md` -- that is the single authoritative list. Do not maintain a duplicate here.

---

## P031 [GENERAL] -- Write/Edit tools truncate headers.py silently (2026-06-15)

**Error:** Both the Write tool and Edit tool silently truncate `headers.py` at approximately line 79-80, always at the same byte boundary. The tool reports "file updated successfully" but the resulting file is incomplete. The `try/except` block assigning `BENEFIT_HEADERS` and `CALC_ROWS` is missing, so `CALC_ROWS` is never defined at module level.

**Symptom:** `ImportError: cannot import name 'CALC_ROWS' from 'app.itsmbvf.headers'` -- or worse, silent fallback to empty dicts if the except clause runs partially.

**Root cause:** Unknown -- appears to be a file size or content-triggered truncation in the Write/Edit tools for this specific file. The truncation point is consistent (~3KB) but the cause was not identified.

**Mitigation applied:** Write the file via bash `cat > /path/to/headers.py << 'ENDOFFILE' ... ENDOFFILE`. This writes the complete file correctly.

**Prevention:**
- **Never use Write or Edit tools to modify headers.py.** Always use bash cat-heredoc.
- After any write to headers.py, verify with: `wc -l /path/to/headers.py` (should be ~89 lines) and `tail -5` to confirm the try/except block is present.
- Verify import works: `python3 -B -c "import importlib.util; spec = importlib.util.spec_from_file_location('h', 'app/itsmbvf/headers.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('CALC_ROWS' in dir(m))"`

---

## P032 [GENERAL] -- Edit tool truncates routes.py at the same ~3KB boundary (2026-06-15)

**Error:** The Edit tool truncated `routes.py` mid-line at line 449 when inserting `_fmt_calc` near line 77. Same silent truncation as P031. The tool reported success; the resulting file had a partial line (`@itsmbvf_bp.route('/assumptions', methods=['GET', 'P`) that caused a SyntaxError.

**Additional impact:** The `cat >> heredoc` append landed AFTER the truncated line, so the file had a stray partial line followed by the correct content. Fixed with `sed -i '449d'` to remove the stray line.

**Affected files confirmed:** `headers.py`, `routes.py`. Treat ALL files in this project as vulnerable to Write/Edit tool truncation.

**Rule:** Use bash (`sed` for targeted replacements, `cat > file << 'EOF'` for full rewrites, `cat >> file << 'EOF'` only for clean appends to syntactically complete files). After any modification, always run `python3 -c "import ast; ast.parse(open('file.py').read()); print('OK')"`.

---

## P033 [GENERAL] -- Write/Edit tools truncate HTML templates silently (2026-06-15)

**Severity:** Critical -- same truncation pattern as P031/P032 but now confirmed to affect HTML files, not just Python files. Previously the standing rule only prohibited Write/Edit on Python files; HTML files were still being modified with those tools, causing two silent truncations in a single session.

**Affected files this session:**
- `app/templates/itsmbvf/base.html` -- truncated to 37 lines (was ~183). Truncated mid-CSS, ending at `background:var(--ltblue);color:var(`. Entire HTML body, nav, blocks, and most CSS rules were lost.
- `app/templates/itsmbvf/assumptions.html` -- truncated to 183 lines. Truncated mid-attribute inside a tooltip `title="..."` string, losing the input close tag, two closing divs, nav buttons, form close, and `{% endblock %}`.

**Discovered:** Session 10 post-compaction truncation audit, 2026-06-15 13:xx EDT.

**Impact:** Both files silently appeared "successfully updated" in tool output. The truncation of base.html caused 500 errors on all routes (Jinja2 could not compile the broken template). The truncation of assumptions.html caused the assumptions page to render a broken form with no submit button and no `{% endblock %}`.

**Root cause:** The Write and Edit tools in this environment silently truncate file output at approximately 3KB regardless of file size or type. This is a transport-layer or buffer limit -- it is NOT specific to Python files. Every file written by these tools is at risk. The truncation is always silent: the tool reports success.

**Pattern:** The 3KB limit applies across all file types: `.py`, `.html`, `.md`, `.js`, `.css`. Any file larger than approximately 40-50 lines is potentially at risk. The truncation point is consistent within a session but may vary between sessions.

**Mitigation applied:**
- `base.html`: Reconstructed full file via `cat > file << 'EOF'` heredoc (183 lines).
- `assumptions.html`: Removed truncated last line with `sed -i '{n}d'`, then appended tail via `cat >> file << 'EOF'`.

**Prevention -- STANDING RULE UPDATE (extends P031/P032 from Python-only to ALL files):**
- **Never use the Write or Edit tools on ANY file in this project.** The 3KB truncation applies to .py, .html, .md, .js, .css, and all other file types.
- For full file writes: `cat > /path/to/file << 'EOF' ... EOF` via bash.
- For targeted line replacements: `sed -i 's/old/new/g'` or `sed -i '{n}s/.*/new_content/'` via bash.
- For appends to syntactically complete files: `cat >> file << 'EOF' ... EOF` via bash.
- **After every write, run `check_files.sh`** (or at minimum: `wc -l filename && tail -5 filename`).
- For HTML templates, always verify the tail contains `{% endblock %}`.
- For Python files, always run `python3 -c "import ast; ast.parse(open('f').read()); print('OK')"`.

**Detection -- post-write checklist:**
```bash
wc -l filename          # Does line count match expectation?
tail -5 filename        # Does the file end where it should?
grep "endblock\|</html>" filename  # For HTML: closing structure present?
python3 -c "import ast; ast.parse(open('file.py').read()); print('OK')"  # For Python
```

---

## P034 [WEB] -- Missing JS function detection (check_js.py)

**Date:** 2026-06-15
**Symptom:** A JS function is called in an event handler (onclick, onchange) in a template but the function definition was deleted, truncated away, or never written -- resulting in a silent "function is not defined" error at runtime only.
**Root cause:** Static analysis was not previously applied to JS. Truncation events (see P033) could remove a `<script>` block without check_files.sh detecting it, because the HTML tail ({% endblock %}) would still be intact.
**Detection:**
- `check_js.py`: Extracts all function calls from event handler attributes across all templates. Extracts all function definitions from `<script>` blocks. Flags any call with no matching definition.
- Wired into `check_files.sh` as the "JS function coverage" layer.
**Prevention:** Run `check_files.sh` after every write. Any new JS function called in a template must also be defined in a `<script>` block in that template (or added to the GLOBAL_FUNS set in check_js.py for library functions).
**Note:** check_js.py uses static regex analysis only -- it does not evaluate JS. It will not catch logic errors inside functions, only missing definitions.

---

## P035 [WEB] -- Route smoke test / Python logic error detection (check_routes.py)

**Date:** 2026-06-15
**Symptom:** A Python route returns 500, 302-loops, or renders with missing content -- catching errors that syntax checking (check_structure.py) cannot detect. Examples: a template variable referenced in a template but not passed by `render_template()`; a session guard redirecting because the wrong key name is used; `run_calculation()` missing an output key that a template expects.
**Root cause:** Syntax checks (`ast.parse`) confirm the file is valid Python but cannot verify runtime behavior. Logic errors, missing context variables, and broken session flows are invisible to static analysis.
**Detection:**
- `check_routes.py`: Uses Flask's built-in test client (no server needed). Seeds a realistic session, hits every route, asserts HTTP 200 and presence of expected content strings.
- Also calls `run_calculation()` directly and verifies all required KPI output keys are present.
- Wired into `check_files.sh` as the "Route smoke test" layer.
**Known limitation:** KPI values (payback, benefit_3y, etc.) will show WARN "blank/zero" in the sandbox because openpyxl does not recalculate Excel formulas without the full engine. This is expected -- treat it as a WARN, not a FAIL.
**CRITICAL: `GET /` calls `session.clear()`** -- it must be tested with a separate test client from the seeded-session routes. Failing to do this causes all subsequent routes to see an empty session and redirect, making the test useless. check_routes.py handles this by using separate `with app.test_client()` blocks.
**Prevention:** Run `check_files.sh` after every write. When adding a new route, add it to ROUTES or FRESH_ROUTES in check_routes.py and add at least one expected content string.

---

## P036 [WEB] -- Session cleared on back-navigation (session persistence bug)

**Date:** 2026-06-15
**Symptom:** User advances to Summary or Challenges, then navigates back to Profile or Challenges. All previously entered inputs (company name, revenue, employees, challenge priorities) are blank -- session appears empty.
**Root cause:** `GET /` calls `session.clear()` -- this is intentional for fresh-start behavior. However, the Profile nav link in `base.html` and the "← Profile" back button in `step2_challenges.html` both pointed to `/`, so any mid-flow back-navigation wiped the session.
**Fix:**
1. `app/templates/itsmbvf/base.html` -- Profile nav link: change `href="/"` to `href="{% if step and step > 1 %}/edit_profile{% else %}/{% endif %}"`. Mid-flow (step > 1) routes to `/edit_profile` which pre-fills from session. Fresh start (step 1 or no step) still routes to `/` as intended.
2. `app/templates/itsmbvf/step2_challenges.html` -- back button: change `href="/"` to `href="/edit_profile"`.
**The `/edit_profile` route:** `GET /edit_profile` pre-fills the Profile form from `session['profile']` without clearing the session. All other session data (priorities, kpis, assumptions) is preserved.
**Prevention:** Any "back" or "edit" navigation link that appears after step 1 must point to `/edit_profile`, not `/`. Only the "Start over" or initial entry point should point to `/`.

---

## P037 [GENERAL] -- Edit tool used in violation of STANDING_RULES, caused routes.py truncation (Session 13)

**Date:** 2026-06-17
**Symptom:** After using the Edit tool to update the POST /assumptions handler in routes.py (a 4-line replacement around line 504), the file was truncated to 705 lines. Last readable line was `            sen` (mid-line). Syntax parse reported `SyntaxError: expected 'except' or 'finally' block` at line 706.
**Root cause:** STANDING_RULES explicitly prohibits the Write and Edit tools on ALL files in this project: "Never use the Write or Edit tools on ANY file in this project. Always use bash." The Edit tool silently truncates files at ~3KB. The Edit tool always reports success regardless.
**Contributing factor:** Compaction event at session start caused Claude to lose standing-rule memory. The truncation rule was re-read from STANDING_RULES.md only after the damage was done.
**Fix:**
1. Identified the truncated tail: `tail -3 file | cat -A` showed the line ending mid-word
2. Calculated missing lines from known git HEAD (698 lines) + prior edits
3. `head -n -1 routes.py > /tmp/routes_fixed.py` to remove the truncated line
4. `cat >> /tmp/routes_fixed.py << 'EOF'` to append the 8 missing lines
5. `cp /tmp/routes_fixed.py routes.py`
6. Verified: 713 lines, clean `ast.parse`, clean `check_files.sh`
**Prevention:**
- After every compaction event, read STANDING_RULES.md BEFORE touching any file
- Never use the Write or Edit tools on ANY file in this project under any circumstances
- If tempted to use Edit for a "small" change: use `sed -i` for single-line replacements, `sed -i 'Nr /dev/stdin'` with heredoc for block insertions, `cat >>` for appends
**Recurrence, 2026-08-27 (this session):** After a compaction event, responded to the compaction summary and then proceeded directly to substantive work (reviewing the uploaded zip, staging device files, editing `results.html` via `device_bash`, updating `SESSION_LOG.md`/`PROJECT_STATE.md`, giving Ben commit commands) without first re-reading `CLAUDE.md`, `PROJECT_STATE.md`, `STANDING_RULES.md`, or `CLAUDE_problems.md` -- exactly the failure this entry's own Prevention bullet names ("After every compaction event, read STANDING_RULES.md BEFORE touching any file"). Caught only when Ben asked directly ("there should be a defined protocol to follow when there [is a compaction event]"), which prompted reading `STANDING_RULES.md`'s COMPACTION RECOVERY PROTOCOL section (added since P037 was written) and all four mandated files. No file damage resulted this time -- every edit made before the check happened to already follow the sed-i/cat-heredoc rules from memory of the pre-compaction summary, and `bash check_files.sh` was run after the results.html edit -- but that is luck from a fresh memory of the prior session, not verification, and is exactly the "getting away with it was luck, not verification" pattern P038 also names. **Root cause:** the compaction summary itself is detailed enough to feel like sufficient context to act on, so the explicit MANDATORY re-read step gets silently skipped in favor of continuing the task at hand. **Prevention, reinforced:** treat the appearance of a compaction summary as a hard stop -- before any tool call other than reading the four mandated files, read them, even if (especially if) the summary feels complete and actionable on its own.

## P038 [GENERAL] -- Python heredoc `open().write()` used for markdown edits despite explicit STANDING_RULES ban (Session 2 continued, self-caught)

**Date:** 2026-08-26/27
**Symptom:** Across this session, `CLAUDE.md`, `PROJECT_STATE.md`, `SESSION_LOG.md`, and `check_css.py` were edited using `python3 << 'PYEOF' ... io.open(path, 'r'/'w').read()/.write(...) ... PYEOF` heredoc scripts -- a pattern STANDING_RULES.md's File Writing Rules section bans by name: "Never use `python3 - << 'EOF'` heredoc scripts that call open().write()." Not caught until Ben asked for a template-documentation update, which prompted a full re-read of STANDING_RULES.md that surfaced the conflict.
**Root cause:** STANDING_RULES.md was read at session start per protocol, but its exact wording wasn't re-checked before choosing a file-edit method mid-session. `cat > file << 'EOF'` (the mandated pattern) is more awkward for a surgical string-replacement edit (find exact old text, splice in new text, preserve everything else byte-for-byte) than a short Python `str.replace()` script, so the more convenient-but-banned pattern got reached for repeatedly without registering that it matched a named prohibition.
**Contributing factor:** No actual file damage resulted this time -- every edit was spot-checked with `tail`/`wc -l` along the way, and `bash check_files.sh`'s syntax/tail checks passed clean on `check_css.py`/`check_js.py`/etc. by the end of the session. But STANDING_RULES.md also mandates `bash check_files.sh` after *every* write and `python3 check_structure.py --update` after every verified-good write, and neither was run after the CLAUDE.md/PROJECT_STATE.md/SESSION_LOG.md edits specifically -- only once, near the end of the session, for unrelated reasons. The safety net that would have caught a silent truncation was itself being skipped, so getting away with it this time was luck, not verification.
**Also noted:** P025 (2026-06-11) explicitly recommends `with open(path, 'w') as f: f.write(...)` as the *fix* for a cat-heredoc corruption pattern. That recommendation now conflicts with STANDING_RULES.md's later, more absolute ban on the same open().write() technique. STANDING_RULES.md is authoritative per its own header ("if CLAUDE_problems.md conflicts with this file, CLAUDE_problems.md is primary -- update this file immediately"), but P025's fix text should be corrected so it stops pointing at a now-banned pattern -- flagging this rather than editing P025 unilaterally, since it means changing another RCA entry's stated fix, not just appending a new one.
**Fix going forward:** Use `sed -i` (targeted replacements/inserts, including the `sed -i 'Nr /dev/stdin'` heredoc-insert form used for this very entry) and `cat > file << 'EOF'` / `cat >> file << 'EOF'` (full rewrites / clean appends) for every markdown, doc, and code edit in this project from here on -- no exceptions for "just a small string replacement." Run `bash check_files.sh` after every write, not just at natural checkpoints.
**Prevention:**
- Before choosing a file-edit method, check STANDING_RULES.md's File Writing Rules section against the *specific technique* about to be used, not just its general spirit.
- Treat "the safety-net command wasn't run" as itself an error condition, not a shortcut -- if `bash check_files.sh` isn't run after a write, that write is unverified regardless of what wrote it.
- P025's fix recommendation needs a correction pass (see "Also noted" above) -- proposed, not yet done; needs Ben's go-ahead since it changes prior RCA guidance.

---

## P039 [GENERAL] -- Compaction trigger produced a generic narrative summary instead of the mandated file re-read, immediately after the same session's first protocol skip was caught (2026-08-27)

**Date:** 2026-08-27
**Severity:** High -- the same standing rule was violated twice, back-to-back, in a single session; catching and logging the first violation did not prevent the second.

**Symptom / sequence:**
1. This session opened already mid-compaction (its first message was a long structured summary of a prior conversation). Work proceeded directly into substantive changes -- reviewing an uploaded zip, porting Results-page updates into `results.html`, updating `SESSION_LOG.md`/`PROJECT_STATE.md`, handing Ben commit commands -- without first reading `CLAUDE.md`/`PROJECT_STATE.md`/`STANDING_RULES.md`/`CLAUDE_problems.md`. This is a direct recurrence of P037 and was logged as a recurrence note on that entry.
2. Mid-session, an explicit `"Compaction event, follow protocol"` instruction arrived, naming the exact protocol by its own section title (`STANDING_RULES.md`'s "COMPACTION RECOVERY PROTOCOL"). The response was to generate a long free-text narrative summary of the conversation from memory -- structurally identical to a generic session-compaction summary -- instead of reading the four mandated files. This is a second, distinct failure: a response that superficially resembles "handling a compaction event" while doing the opposite of what this project's protocol requires, and it also runs against P009/P013 (a compaction reconstruction is not fact; do not act on the summary alone) since that narrative was produced and left standing as if reliable.
3. Only Ben's direct, explicit correction ("review Claude.md & STANDING_RULES") triggered the actual protocol -- reading all four files -- at which point failure #1 was caught and logged. Failure #2 (this entry) was not recognized or logged until Ben flagged it separately, a second time.

**Root cause:** The concept "compaction event" maps to two different behaviors: (a) a generic, broadly-trained default -- when told a compaction occurred, produce a summary of the conversation so far; (b) this project's specific, mandatory rule -- when a compaction event is detected, stop and read four named files before doing anything else, and explicitly do not act on the summary alone. When the instruction "follow protocol" arrived, it was answered via default behavior (a) rather than grounded in the project's own documentation (b), even though "protocol" is the literal word `STANDING_RULES.md` uses for its own section header. The generic pattern-match fired before the specific rule -- already invoked once earlier in this very session -- was consulted.

**Contributing factors:**
- No re-read of `STANDING_RULES.md` had occurred between failure #1 and failure #2 -- the second failure happened precisely because the first one's fix (reading the files) had not yet happened at that point. The two are sequential instances of the identical gap, not independent bugs.
- The compaction-recovery protocol lives in one place in one file, with nothing that forces a check of it the moment a compaction-related trigger arrives -- there was general awareness such a rule existed, but no reflexive "see the word compaction -> open STANDING_RULES.md first" habit.
- A detailed, plausible-looking narrative summary is easy to mistake for competent handling of a compaction event, which makes this failure mode unusually hard to self-catch -- the response felt complete and accurate as far as it went, so nothing about it looked broken from the inside.

**Fix applied:** Read all four mandated files in full once Ben's direct correction arrived. Verified no retroactive content damage from either failure -- all file edits made in between had, by coincidence, already followed the `sed -i`/`cat`-heredoc rules, and `check_files.sh` had been run once. Failure #1 logged as a recurrence note on P037; this entry documents failure #2 and the compounding pattern of both happening in one session.

**Prevention, reinforced (extends the P037 recurrence note, which only covered failure #1):**
- Any message containing "compaction" or "compact" -- a system-generated session-start summary, an explicit mid-session notice, or a user message referencing one -- is a hard trigger to read `CLAUDE.md`, `PROJECT_STATE.md`, `STANDING_RULES.md`, and `CLAUDE_problems.md` in full BEFORE any other action, including before responding with any text, even a summary that seems ready to give.
- "I already have a detailed summary in context" is not equivalent to having read the files. A summary is a reconstruction (P009, P013); the protocol's entire point is that reconstructions do not substitute for source files, no matter how complete the reconstruction looks.
- A mid-session self-correction of a rule violation (like the P037 recurrence note) is a signal to re-verify compliance with that SAME rule for the rest of the session, not a closed incident -- the same gap recurred immediately after being caught once, in this very case.

**Cross-references:** P009, P013 (compaction reconstructions are not fact -- do not act on them alone), P037 (original instance and this session's first recurrence), P038 (self-caught rule violation, same "getting away with it was luck, not verification" pattern).

---

## P040 [GENERAL] -- No Detectable Signal When Compaction Occurs Before the Session-Start Protocol Ever Completes (2026-08-27)

**Date:** 2026-08-27
**Severity:** High -- this is the root-of-the-root-cause behind P037 and P039: both of those document failures to REACT to a compaction signal, but this entry covers the case where no reliable signal exists to react to in the first place.
**Pattern:** P037 and P039 both assume a compaction event presents some noticeable cue (a session-start summary, an explicit mid-session notice). But if compaction occurs mid-way through the very first session-start read-through -- before `CLAUDE.md`/`PROJECT_STATE.md`/`STANDING_RULES.md`/`CLAUDE_problems.md` have all been read even once -- there may be no clean narrative cue at all in the next turn. A compacted summary reads as detailed and complete regardless of whether the protocol behind it was ever actually finished, which biases toward treating work as already-underway-and-continuing rather than still-incomplete. This case was identified by Ben from this project's own history (the true session-start protocol run appears to have been interrupted by an early compaction event), not caught through an in-session error.
**Root cause:** Both this gap and P037/P039 share the same underlying issue -- relying on noticing something (a signal, a feeling of "this looks handled") rather than checking something concrete. Signal-recognition is not reliable enough to be the only gate on a MANDATORY protocol.
**Fix:** A disk-based, checkable verification marker replaces signal-recognition as the gate. See `STANDING_RULES.md`'s SESSION-START AND COMPACTION RECOVERY PROTOCOL section for the full mechanism: a small marker file (`.session_protocol_verified`, in the same folder as this file) gets a timestamped line the moment each of the four mandatory files is actually read via a tool call. Before any substantive work in any turn, the marker is checked -- and only counts as valid if its claims are backed by `Read` tool calls actually visible in the current context, not just the file's mere existence. A marker that can't be corroborated against currently-visible tool-call history is treated as stale, regardless of what it says or what a narrative summary implies.
**Prevention:**
- Do not treat a detailed, plausible compaction-recovery summary as proof the protocol ran to completion. Proof is the marker file cross-checked against visible tool-call history, nothing else.
- The marker check runs before ANY substantive work in ANY turn -- not gated on first recognizing a compaction-shaped signal, since this entry exists specifically because that signal can be entirely absent.
- If a marker is missing, incomplete (not all four files logged), or unverifiable, run the full protocol and write a fresh marker before proceeding, no exceptions.
**Cross-references:** P009, P013 (compaction reconstructions are not fact), P037 (skipped protocol after a recognized compaction), P039 (generic-summary habit overrode a recognized protocol trigger). This entry is the structural fix underneath all three.

---

## P041 [GIT] -- Sandbox Git Status Shows Unrelated Files as "Modified" Due to CRLF Mismatch and Missing git-lfs (2026-08-27)

**Date:** 2026-08-27
**Severity:** Low -- cosmetic/diagnostic noise only; confirmed no real content divergence in every case checked.
**Pattern:** `git status`/`git diff` run from the device-bridge Linux shell (not the user's own machine) reports a cluster of unrelated files as "modified" -- plain text files (README.md, .py modules, config files) and, separately, LFS-tracked binaries (`*.xlsx`, `*.png`, `*.pptx`, `*.pdf` per this repo's `.gitattributes`). Neither reflects a real problem.
**Root cause, part 1 (text files):** No `core.autocrlf` is set anywhere visible to this shell (global/system/local all empty). The repo's committed history is LF-only; the working tree, maintained by the user's own Windows git, is CRLF (confirmed byte-for-byte: `\r\n` in the working copy vs `\n` in `git show HEAD:<file>`). The user's Windows git almost certainly has `core.autocrlf=true` set (Git for Windows' standard default), which transparently reconciles this for their own status/diff -- confirmed by the literal warning their terminal shows during a real commit ("LF will be replaced by CRLF the next time Git touches it"). This bridge shell's git has no such setting and cannot do the same reconciliation, so it reports every CRLF-converted text file as changed.
**Root cause, part 2 (LFS binaries):** `git-lfs` is not installed in this bridge shell (`git: 'lfs' is not a git command`). The repo's actual stored content for an LFS-tracked file is a ~131-byte pointer stub (`version https://git-lfs.github.com/spec/v1 / oid sha256:... / size ...`); the working tree has the real, correctly-smudged file (smudged by the user's own git-lfs, on their machine). Without the filter available here, this shell's git can't reconcile pointer-vs-real content and reports a `Bin 131 -> <real size> bytes` diff.
**Verification:** Checked byte-for-byte on multiple files (a .md, a .py, and both LFS-tracked types) via `git show HEAD:<file>` against the working-tree file directly. Confirmed a real, intentional commit made from the user's own terminal shows clean from this shell immediately afterward -- proving this shell's git and the user's git agree on actual content; they just can't both correctly compare against the working tree the same way.
**Fix / mitigation:** None needed for correctness -- purely a this-shell diagnostic artifact, not a repo or content problem. Do not chase these files as if they contain real changes, and do not `git add -A` blindly from this shell without checking each flagged file's actual diff first (a targeted diff immediately reveals whether it's this artifact or a real change). STANDING_RULES.md's existing rule (never rely on sandbox git for commits, always commit from the user's own machine, read-only git commands only from this session) already routes around the underlying risk -- this entry exists so the noise itself doesn't have to be re-diagnosed from scratch every time it's noticed.
**Permanent fix, scoped to the START of a new project, not retrofitted onto an active one:** add explicit line-ending normalization to `.gitattributes` (e.g. `* text=auto eol=lf`, keeping `*.bat`/`*.ps1` as `eol=crlf` since those are genuinely Windows-native) immediately after cloning the starter repo and before the first push -- see README_first.md step 3. Retrofitting this onto an already-active repo needs a `git add --renormalize .` pass and risks one large line-ending-only commit, so it is deliberately NOT being done to an existing project's repo after the fact -- it is cheap and clean only when done before the first commit.
**Cross-references:** None prior -- new pattern.

---

## P042 [WEB] -- Python zoneinfo Fails on Windows Without the tzdata Package (2026-08-28)

**Date:** 2026-08-28
**Severity:** High -- crashes the app at import time on Windows (every route fails), zero-effort to reproduce, invisible in a Linux dev/sandbox environment
**Discovered:** K1x PMTC Assessment, Phase 10 local test run on Ben's Windows machine. `flask --app "app:create_app()" run --debug` failed immediately with `zoneinfo._common.ZoneInfoNotFoundError: 'No time zone found with key America/New_York'`, traced to `data_capture.py`'s module-level `EASTERN = ZoneInfo("America/New_York")`.
**Pattern:** Python's built-in `zoneinfo` module (stdlib since 3.9) does not ship its own copy of the IANA time zone database -- it looks for one already present on the OS. Linux and macOS both ship a system tz database, so `zoneinfo.ZoneInfo(...)` works out of the box there. Windows has no equivalent system database, so any `ZoneInfo(...)` call raises `ZoneInfoNotFoundError` unless the `tzdata` PyPI package (a pure-Python copy of the IANA database) is installed separately.
**Root cause of the miss:** `data_capture.py` was built, `ast.parse`-verified, and exercised via a mocked-Sheets test harness entirely inside this project's Linux bridge shell, which has a system tz database and never exposed the gap. The code was correct Python and correct logic -- it just depended on an OS capability that isn't universal, and nothing in the verification chain used a Windows interpreter (the actual deploy/dev target for this project, which runs entirely on Ben's Windows machine and, per CLAUDE.md's Key Decisions Log, has no auth/hosting dependency that would have forced an earlier Windows-side smoke test).
**Fix:** Added `tzdata==2024.1` to `requirements.txt`; Ben ran `pip install -r requirements.txt` in the shared venv to pick it up.
**Rule for all future projects using zoneinfo:**
- Any project that uses `from zoneinfo import ZoneInfo` and targets Windows (dev machine, hosting platform, or both) MUST include `tzdata` in `requirements.txt` -- do not rely on it being present.
- This is safe to include unconditionally even on Linux/Mac targets (it's a harmless, small, pure-Python package there too) -- no need to special-case it by platform.
- General lesson: any dependency on OS-provided data (tz database, locale data, certificate stores) verified only inside this project's Linux bridge shell should be treated as unverified for Ben's actual Windows runtime until smoke-tested there. `ast.parse` and mocked unit tests catch logic bugs, not environment-shape mismatches between the sandbox and the real target.
**Cross-references:** None prior -- new pattern.

---
## P043 [WEB] -- Placeholder Copy Wired In as a Real Default `value`, Both Client- and Server-Side (2026-08-28)

**Date:** 2026-08-28
**Severity:** Medium-high -- silent data corruption, not a crash: a visitor who left Company blank or never touched Industry would have had `'Company XYZ'` / `'Accounting'` written into the session, the calculated results, and the Google Sheet capture as if they'd been entered for real. Invisible during normal dev/QA because a developer testing the flow types a real company name out of habit.
**Discovered:** Ben's own review of the Profile page's input defaults (self-initiated, not triggered by a test failure) -- "Company name should be blank, Industry should be blank (just a hint: Select one), all goals should be not scored, all capabilities not scored."
**Pattern:** `profile.html`'s company `<input>` had `value="{{ profile.company if profile else 'Company XYZ' }}"` -- what was clearly meant as example/placeholder text got wired into the actual `value` attribute instead of a `placeholder` attribute, so it would submit unchanged if the visitor never touched the field. The industry `<select>` had no blank option at all, so with no profile the browser silently pre-selected the first `<option>` (`Accounting`) with zero visual indication a choice had been made. `routes.py`'s `profile_submit()` had the identical fallback baked in a second time server-side (`request.form.get('company') or 'Company XYZ'`, `industry or INDUSTRIES[0]`, plus a coercion of any unrecognized industry back to `INDUSTRIES[0]`) -- so even a client-side fix alone would not have closed the gap; a direct POST or JS-disabled visitor would still have gotten fabricated data silently written to the Sheet.
**Root cause of the miss:** the goal sliders and capability sliders in this same app already had the *correct* pattern (`value: null` → renders as an explicit "NOT SCORED"/"Not answered yet" unset state, gated by a required-before-continue JS check) -- the two plain-text/select fields on the same page just didn't get that same treatment when they were built, and nothing in `check_files.sh`'s structural/CSS/JS checks would ever catch a wrong *default value* (they check that classes/functions exist, not what a fresh page renders).
**Fix:** Company input's default `value` changed to `''`; industry `<select>` given a `<option value="" selected disabled>Select one</option>` placeholder (shown only when there's no existing `profile.industry`, so the `/edit_profile` prefill path is unaffected); both fields marked `required`; the existing `startBtn` click handler (already gating on all 6 goals being answered) extended to gate on company non-blank and industry selected, same validation-message pattern already in use. `routes.py` no longer fabricates `'Company XYZ'`/`INDUSTRIES[0]` for a blank submission -- stores whatever was actually submitted instead, matching the existing convention that this app's only validation gate is client-side (goals have no server-side "all answered" enforcement either). Confirmed `calculator.py`'s peer-lookup already degrades gracefully on an unrecognized/blank industry via `.get(industry, PEER_SCORES)` / `.get(industry, PEER_COUNTS["Accounting"])`, so blank industry reaching `run_calculation()` cannot crash it. Verified with a standalone Jinja2 render of the patched template (`flask` isn't importable in this sandbox -- see P042's own environment-gap note) comparing `profile=None` (blank input, "Select one" selected+disabled) against an existing-profile render (correct prefill preserved).
**Rule for all future projects with multi-field forms:** any field whose fallback is meant to be a UI hint (a placeholder) must use the `placeholder` attribute, never the `value` attribute -- a `value` fallback is what actually gets submitted if the visitor does nothing. When one field on a page already has a correct "unset by default, required before continuing" pattern (as the goal/capability sliders did here), audit every other field on the same page/form for the same treatment rather than assuming consistency -- a per-field default can drift independently of a well-designed neighbor. Check both layers: a client-side-only fix is incomplete if the server route has its own independent fallback baked in.
**Cross-references:** None prior -- new pattern. Related to P042 in that both were caught by real-world review outside this sandbox's own verification loop, not by `check_files.sh`.

---
## P044 [WEB] -- CDK Lambda Bundling Used Unix-Only `cp` and Would Have Shipped `.env`/`.git`/`.venv` Into the Deployed Function (2026-08-28)

**Date:** 2026-08-28
**Severity:** High -- two independent bugs found together on Ben's first real deploy attempt. One was a hard crash (`cdk synth` failed outright on Windows); the other was silent and would not have been caught by any check run so far -- a live Lambda function's deployment package would have contained the real Google service-account key and Flask secret key in plaintext (`.env`), readable by anyone able to export that function's code from the AWS console.
**Discovered:** Ben's own first attempt to run `npx cdk synth` from his Windows machine, walked through live in this session. `«FailedToBundleAsset» ... Error: spawnSync cp ENOENT`.
**Pattern:** `infra/lib/app-stack.ts`'s Lambda bundling step (both the local-bundling `tryBundle()` path and its Docker `command` fallback) copied the Lambda's code by shelling out to `cp -a`/`cp -au`, copying the *entire* `appDir` (`Application/app/`) into the deployment package. Two problems, only one of which Windows exposed:
1. `cp` does not exist on Windows -- the whole design point of local-bundling-first packaging was to deploy from Ben's Windows machine with no Docker, so this broke the one path the feature exists for. Worse, the failing `cp` call sat *outside* the function's own `try { ... } catch { return false }` block, so instead of the intended graceful fallback to Docker-based bundling, it threw an uncaught exception and crashed `cdk synth` entirely.
2. Independent of platform: a blanket copy of `appDir` sweeps in everything sitting next to the actual Flask package -- `.env` (real secrets), `.git` (full history), `.venv` (an entire virtualenv), `WORKBOOK.xlsx`, and various dev-only scripts (`check_*.py`, `deploy.ps1`). None of that belongs in a Lambda deployment package, and `.env` in particular would have put live credentials inside AWS infrastructure state (the function's own code, downloadable from the console) rather than only in the intended `environment:` variables. This would have been true on Linux too, and was never caught because the local sandbox verification in the two prior sessions used a scratch `appDir` that happened not to contain a `.env`.
**Root cause of the miss:** this code was written and `cdk synth`-verified entirely inside this session's own Linux cloud sandbox (see the P042-adjacent entry two sessions ago for `cdk synth` runs), never against Ben's actual Windows target machine, and never against a scratch `appDir` shaped like the real one (with `.env`/`.git`/`.venv` present) -- so neither bug had a chance to surface until the real first deploy attempt, on the real machine, against the real folder.
**Fix:** Replaced both `cp` shell-outs with Node's built-in `fs.cpSync` (cross-platform, no external command dependency), and changed what gets copied from "everything in `appDir`" to explicitly only `lambda_handler.py` and the `app/` subpackage, with a filter excluding `__pycache__`/`.pyc`. Applied to both the local-bundling path and the Docker fallback's `bash -c` command, for consistency even though only the local path is expected to run in practice. Verified before writing back to Ben's machine: rebuilt the cloud-sandbox scratch test project's `appDir` with fake `.env`/`.git`/`.venv`/`WORKBOOK.xlsx` files planted alongside the real `app/`/`lambda_handler.py`, ran `cdk synth` clean, and directly inspected the synthesized asset directory to confirm none of the four fake sensitive files were present while the real app package and all its dependencies were. Re-ran the same simulated Lambda Function URL invocation used for the original build to confirm nothing about the app's actual behavior changed.
**Rule for all future projects bundling a Lambda (or any deploy package) from a directory that also contains dev-only files:** never copy a whole "everything lives next to the app" directory into a deployment artifact -- name exactly what ships (entry point + the actual package), the same way you'd write a `.dockerignore`/`.gitignore`, and treat a blanket recursive copy as a bug even when it "works," not just when it crashes. Prefer a language-native cross-platform copy (`fs.cpSync` in Node, `shutil.copytree` in Python) over shelling out to a Unix-only command when the tool doing the shelling-out (`cdk synth`/`cdk deploy`) is explicitly meant to run on Windows. And per the general lesson under P042: any bundling/packaging logic verified only against a sandbox's own scratch directory shape should be treated as unverified until tried against the real target directory's real shape (real dotfiles and all), not just the real OS.
**Cross-references:** Same "verified only in this sandbox, not the real Windows target" root-cause family as P042. First entry in this file to catch a would-be credential-leak bug specifically.

---
## P045 [WEB] -- Google Sheets `append_row(table_range=...)` Did Not Honor the Range's Column Boundary, Wrote One Column Left of Intended (2026-08-28)

**Date:** 2026-08-28
**Severity:** Medium -- every "first capture" of a live assessment (the `append_row` path in `data_capture.py`'s `capture_result()`) landed one column to the left of its intended B:AG range, misaligning every field in the row against its header. First surfaced on the live tool's very first real post-deploy use.
**Discovered:** Ben ran a real assessment through the newly-deployed live tool and noticed the captured row's Timestamp value sitting in column A of the Google Sheet, not column B where `FIRST_DATA_COL`/the documented schema/the header both say it belongs. Initially misdiagnosed (by both Claude and, reasonably, Ben) as a header-alignment problem in the Sheet itself and "fixed" by shifting the header rows left by one column -- Ben caught and corrected this when he confirmed directly that the *data* itself, not just the visual impression, had landed in column A.
**Pattern:** `capture_result()`'s append path called `gspread`'s `Worksheet.append_row(row, table_range='B4:AG4', ...)`, expecting the Sheets API's "find the table within this range and append after it" behavior to anchor new values starting at column B (the range's own left edge) as documented. In practice, against Ben's real Sheet, the write landed starting at column A instead -- one column left of the range actually given. The exact mechanism inside the Sheets API/gspread's table-detection logic was not pinned down (no direct access to reproduce against the real Sheet from this environment), but the effect was consistent and confirmed directly by Ben, not just inferred from a code read.
**Root cause of the miss:** the original Phase 10 build was "live-verified end-to-end on Ben's own machine" per an earlier session's log entry, using a local dev server against real credentials -- but that verification evidently didn't catch this, or the Sheet's shape at verification time (fewer/no pre-existing header rows, or a different table state) happened not to trigger the same table-detection quirk that showed up on the live Lambda's first real write. A blanket "verified once" claim for a Sheets-API-dependent code path is fragile against under-documented server-side heuristics like `values.append`'s table auto-detection -- it isn't purely a function of the code, but also of the exact state of the target Sheet at write time.
**Fix:** Rather than chase the exact API mechanism, compensated for the observed behavior directly: `capture_result()`'s append path now prepends one blank string to the values array (for column A, which this module was never meant to write into anyway) and widens `table_range`'s left edge from B to A. Wherever the API's table-detection actually anchors the write, the real Timestamp value now lands in the *second* position of whatever range gets used, landing correctly in column B regardless. The update-in-place path (`sheet.update()`, used for revise-and-resubmit and for `update_lead_info()`'s lead-field backfill) was not touched -- it writes to an explicit range with no table-detection involved, and was never implicated in this bug. Verified only at the Python level so far (array padding and range-string construction checked with a standalone dry run, no real Sheets API call) -- **this fix has not yet been confirmed against a real live write**; that's the next step once Ben is free to redeploy and run one more real assessment through the live tool.
**Rule for future projects writing to Google Sheets (or any API with a "smart" append/table-detection feature) via a shared/central formula:** treat the exact anchor point of an "auto-detect and append" call as unverified until confirmed against the real target sheet/table in its real state, not just against a scratch copy or an isolated unit test -- these heuristics can behave differently depending on what's already in the sheet (header rows, adjacent columns with any content, an untouched-but-non-empty first column) in ways that are not fully documented. When in doubt, or when column alignment is important and can't be visually caught immediately, prefer an explicit target range over an auto-detecting append.
**Cross-references:** None prior -- new pattern, though it echoes the general lesson under P042/P044: verification done in one specific state/environment doesn't transfer automatically to another.

---
## P046 [GIT] -- `infra/` Had No `.gitignore`; Folding It Into the Repo Would Have Committed Real Secrets (2026-08-28)

**Date:** 2026-08-28
**Severity:** High (near-miss, caught before any git command ran) -- would have pushed a real Google service-account key and a real Flask secret key to GitHub.
**Discovered:** Self-caught, not user-reported. Ben's colleague asked him to update the repo for upcoming domain/email work, which surfaced that `infra/` (the CDK deploy code built and used earlier today) was never git-tracked at all -- only `app/` was, in its own separate repo. Ben authorized folding `infra/` into the same repo as `app/` by relocating `.git` up one directory level. Before running any git command, stopped to check whether `infra/` had anything that shouldn't be committed.
**Pattern:** Earlier the same session, `infra/cdk.json` had been filled in with real secret values (`googleCredentialsJson`, `googleSheetId` copied from `.env`; `flaskSecretKey` freshly generated) so `cdk deploy` could run non-interactively. That file was never meant to be committed, but `infra/` had no `.gitignore` of its own -- nothing was excluding `cdk.json`, `node_modules/`, or `cdk.out/`. A plain `git add -A` after merging `infra/` into the tracked repo would have staged all three, and a subsequent commit+push would have put live credentials in git history on what may be a public GitHub repo.
**Fix:** Created `infra/.gitignore` (excluding `cdk.json`, `node_modules/`, `cdk.out/`) *before* touching `.git` at all. Verified by relocating `.git`, staging everything with `git add -A`, and confirming via `git status --short` that `cdk.json`/`node_modules/`/`cdk.out/` do not appear anywhere in the staged output -- then ran `git reset` to unstage before handing off to Ben (per P033, commits happen from his machine, not this bridge).
**Rule for future projects:** whenever a new subdirectory that holds generated config, build output, or secrets-filled-in-for-deploy is about to be brought under version control for the first time (via `git init`, moving `.git`, or `git add` for the first time on that path), check for and create its `.gitignore` *before* any `git add`, not after -- don't assume a directory inherits protection from a `.gitignore` elsewhere in the tree (git's pattern matching is per-directory-tree-relative but a missing file simply excludes nothing). This is a variant of P044's lesson (secret/artifact leakage via an unguarded bulk operation) but at the git-tracking layer instead of the Lambda-bundling layer.
**Cross-references:** P044 (same failure family -- unguarded bulk copy/add operation risking a secret leak, caught before Ben's machine or GitHub ever saw it).

---
## P047 [WEB] -- "Peer Leaders" Score Ported From the Wrong Workbook Table, Plus a Python/Excel Rounding Mismatch It Exposed (2026-08-28)

**Date:** 2026-08-28
**Severity:** Medium -- the "Peer Leaders" number under the score ring, every per-capability comparison bar, the maturity-curve peer mark, and the top-3 "gaps" ranking were all built from the wrong source data since Phase 4. Visible on every single Results page, but not something a user could self-diagnose as wrong without independently knowing what the real peer benchmark should be -- Ben caught it purely by eye ("Peer Leaders score doesn't look right").
**Discovered:** Ben reported the number looked off and asked where it came from. Investigation (not a code-read alone -- direct inspection of the live workbook's actual formulas) found two separate, similarly-shaped peer-data tables on the `Data` sheet: `B27:G39` ("Peer Comparison Data," 5 industry columns, values 2.5/2.2/2.1/1.9/2.3/2.3/1.4/1.5/1.2/1.7, averaging to 1.9) and `D84:E96` (a single column literally headed "PEER LEADERS," values 3.5/3.2/3.3/2.3/2.1/2.8/2.2/2.1/1.8/2.2, averaging to 2.6). `calculator.py`'s `PEER_SCORES` had been ported from the first table. The live workbook's own `Results!F7` (`R_peerScore`, the actual number shown on the workbook's own dashboard) is `=Data!E97`, which averages the *second* table. Confirmed the first table's per-capability rows are never referenced by any formula anywhere in the workbook at all -- the only thing it's actually used for, live, is `Results!F9`'s HLOOKUP into its Peer Count row.
**Root cause of the miss:** an earlier session's Key Decisions Log entry ("Peer comparison data ... treated as final for now") referenced both `Data!B27:G40` and `Results!E85:E94` together, as if they were the same or related data. They aren't the same table, and `Results!E85:E94` doesn't even exist in the current workbook (the `Results` sheet's populated range stops at row 72) -- that citation looks like it was never actually opened and checked against the live file, just carried forward as an assumption. Once a wrong-but-plausible cross-reference like that lands in the decision log, it reads as settled and nothing forces a re-check against the real workbook later.
**Fix:** `calculator.py`'s `PEER_SCORES` now sourced from `Data!D84:E96` instead of `B27:G39`. `PEER_COUNTS` untouched (it was already correctly sourced from `B27:G40` row 40). Re-verified against Ben's own 2026-08-28 workbook refresh -- both tables are unchanged from the version this was originally (mis-)ported from, so the fix isn't chasing a moving target.
**A second, independent bug this fix exposed:** with the corrected values, `peer_score = round(mean(PEER_SCORES.values()), 1)` landed on `2.55` -- a genuine `.x5` rounding boundary. Python's built-in `round(2.55, 1)` returns `2.5` (2.55 isn't exactly representable in binary float; the nearest double is a hair under it, and Python's round-half-to-even then rounds down on that slightly-low value). Excel's `ROUND(2.55, 1)` -- which is literally what `Data!E97`'s formula uses (`=ROUND(AVERAGE(E85:E94),1)`), not a bare `AVERAGE()` -- returns `2.6`, rounding on the value's true decimal digits. The old `PEER_SCORES` never happened to sum to a boundary case, so this was latent and invisible until this fix changed the numbers being averaged.
**Fix (rounding):** added `_excel_round(value, digits=1)` to `calculator.py` -- routes the value through `str()` into `decimal.Decimal` (so it rounds on the value's printed base-10 digits, not Python's underlying binary float noise) with `ROUND_HALF_UP`. Replaced all three `round(..., 1)` call sites in `run_calculation()` (`your_score`, `peer_score`, and the per-capability gap `delta`) with it, even though only `peer_score` was actually observed hitting a boundary case -- `your_score` is currently safe by construction (always an integer sum divided by exactly 10, which can't produce a genuine .x5 ambiguity), but there's no guarantee that stays true if the model's shape changes again (see CLAUDE.md's standing reminder that it already has, twice), and there's no reason to leave two of three near-identical call sites still exposed to the same failure mode once it's been found once.
**While investigating, also corrected an unrelated stale claim in the same Key Decisions Log entry area:** a 2026-08-27 entry asserted `Assessment!N21` and `Data!E97` "both average across all 12 rows including the 2 retired ones." Checked directly against the live formulas for this investigation -- both are `ROUND(AVERAGE(...), 1)` over ranges that stop *before* the 2 retired capabilities' rows; neither actually includes them. This didn't require a code change (the Python port already independently averages only the 10 active capabilities, for the same correct result either way) but the decision log's stated *reason* was factually wrong and has been corrected in place.
**Rule for future workbook hand-ports:** when a workbook has two tables that could plausibly both be "the peer data" (or any other near-duplicate reference table), don't decide which one is authoritative by name/shape alone -- open the sheet that actually *displays* the number in question and read its live formula back to its real source range. A named-range or formula reference (`R_peerScore` → `Data!E97`) is ground truth in a way that a table's label or position on the sheet is not. Also: any time a workbook formula wraps a calculation in `ROUND(...)`, treat that as a signal to check whether Python's `round()` will actually agree with it for realistic inputs, not just copy the digit count and assume behavioral parity.
**Cross-references:** P045 (a different Sheets/Excel-API behavioral-parity surprise found on this project); the archetype-band-clamp decision (CLAUDE.md) for the general pattern of a workbook gaining structure the Python port already anticipated.

---
## P048 [GIT] -- Git LFS Not Installed in the Bridge Shell; Its `git status`/`git diff` Are Unreliable for LFS-Tracked Binaries, and a Commit From Here Would Corrupt LFS Pointers (2026-08-28)

**Date:** 2026-08-28
**Severity:** Medium -- no data was lost or corrupted (caught before any bridge-shell commit was attempted), but this is a standing trap: every future session that runs `git status`/`git diff` from the bridge shell will see the same false signal unless warned.
**Discovered:** While pre-verifying the six accumulated fixes (Open Item #10) before handing off to Ben for commit, `git status` from the bridge shell showed 20 modified files -- far more than the ~10 files actually touched this session. Ran `git diff --ignore-space-at-eol` on the 7 unexpected non-binary files (`.dockerignore`, `.gitattributes`, `.gitignore`, `Dockerfile`, `README.md`, `__init__.py`, `emailer.py`, `report.py`, `deploy.ps1`) and got zero diff lines -- pure CRLF/LF noise (the P041 pattern, confirmed again). The two binary files (`app/app/static/pmtc/picture1.png`, `app/WORKBOOK.xlsx`) both showed `Bin 131 -> <real size>` -- `git lfs version` in this shell returned "git: 'lfs' is not a git command", and `git cat-file -p HEAD:<path>` on both showed a raw LFS pointer file ("version https://git-lfs.github.com/spec/v1 ... size ..."), not the real binary. Comparing `sha256sum` of each working-tree file against the oid in its own HEAD pointer: `picture1.png`'s hash matched exactly (never actually changed -- pure false positive from the missing smudge filter) while `WORKBOOK.xlsx`'s hash differed (genuinely refreshed this session, as expected).
**Root cause:** the bridge shell's Linux VM has git but not git-lfs. Without the LFS clean/smudge filters, `git diff`/`git status` compare the real, smudged working-tree file against the raw pointer text stored at HEAD -- so *every* LFS-tracked binary shows as drastically "modified" (`Bin 131 -> X`) regardless of whether its actual content changed. 131 bytes is just the pointer-file size, not a real prior version.
**Why this matters beyond a confusing `git status`:** if a commit were ever made from this shell (already against P033/STANDING_RULES.md, but worth spelling out why), `git add` would run the (missing) clean filter -- with no git-lfs installed, git would fall back to storing the *raw binary bytes* directly in the object database instead of converting them to an LFS pointer, silently de-LFS-ing that path going forward. This is a strictly worse failure mode than the CRLF noise: CRLF false-positives are just misleading, but a bridge-shell commit on an LFS-tracked binary would actively corrupt the repo's LFS tracking.
**Fix / what was done:** no repo changes needed -- verified by hash comparison that `picture1.png` is unchanged and `WORKBOOK.xlsx`'s change is the intended one, then handed off the exact real-file list to Ben to review and commit from his own machine (per P033), rather than running `git add -A` from the bridge.
**Rule for future sessions:** never trust bridge-shell `git status`/`git diff` at face value for LFS-tracked file types (currently `*.xlsx`, `*.xlsm`, `*.pptx`, `*.png`, `*.pdf` per `app/.gitattributes`) -- treat any "modified" binary as unverified until either (a) `sha256sum`-compared against the oid in `git cat-file -p HEAD:<path>`'s pointer text, or (b) confirmed by Ben's own terminal (where git-lfs is actually installed). This is the binary-file counterpart to P041's CRLF-noise rule for text files -- both boil down to "the bridge's git view is not ground truth, verify before trusting it."
**Cross-references:** P033 (STANDING_RULES.md's git rule -- this is a second, more concrete reason it exists beyond lock files and reliability), P041 (the text-file CRLF-noise counterpart), P046 (another git-hygiene catch on this same repo).

---

---
## P049 [WEB] -- "Peer Leaders" Eyebrow's `white-space:nowrap` Overflowed Into the New Narrative Card for Long Industry Names (2026-08-28)

**Date:** 2026-08-28
**Severity:** Medium -- visible on the live Results page for the two longest of the five `INDUSTRIES` values ("Family Office / Wealth Management", "Tax Exempt / Non-Profit"), overlapping the eyebrow text into the narrative card's border/background. Cosmetic, not a data-correctness bug, but shipped to production for roughly 9 minutes before Ben caught it (deployed 17:47 EDT, reported ~17:56 EDT).
**Discovered:** Ben's own manual click-through of the freshly-deployed live site (exactly the verification step the deploy's own `NextStep` output asks for) -- screenshot showed "WHERE YOUR FAMILY OFFICE / WEALTH MANAGEMENT PEER LEADERS RANKED" running into the "What This Means" card.
**Root cause:** `.ysc-peer-eyebrow-row` (the "Where Your {industry} Peer Leaders Ranked" line) spans grid columns 1-2 of `.your-score-card`'s 3-column grid, with `white-space:nowrap` -- a deliberate choice from the original 3-row-grid redesign (see the CSS comment right above it) so the line wouldn't wrap awkwardly inside column 1's ~238px width alone. That was safe when written and tested against the default "Accounting" industry's short label. It stopped being safe today, for an unrelated reason: this same session's item (4) wrapped `.ysc-narrative` (column 3) in a new `.narrative-card` div with a real background and border (previously column 3 was plain/transparent in that row). A CSS grid item with `white-space:nowrap` doesn't get clipped or forced to wrap just because it's wider than its grid track -- it overflows past the track boundary with default `overflow:visible`. That overflow was always happening for the two long industry names; it just used to spill onto an empty transparent area (invisible) and now spills onto a card with a border (visible, and visually colliding).
**Why the redesign (item 4) didn't catch this itself:** the narrative-card verification that session covered content overflow *inside* the card (shortest vs. longest narrative band) at multiple viewport widths, but didn't specifically re-check every sibling grid item for old `nowrap`/fixed-width assumptions that predate the card gaining a visible boundary. A `nowrap` overflow onto a *transparent* neighboring area is invisible in a screenshot diff -- there was nothing to see before the neighbor had a background.
**Fix:** removed `white-space:nowrap` from `.ysc-peer-eyebrow-row`'s base (desktop) rule -- it now wraps normally within its grid-column-1/3 span, same as the mobile media query already did (that query's own `white-space:normal` override becomes redundant at that breakpoint but is harmless left in place). No other layout changes needed: `.your-score-card`'s overall row height is already governed by the taller neighbor (`.ysc-narrative`, `grid-row:1 / 4`), so a 2-line eyebrow on the left just uses existing headroom rather than growing the card.
**Verified:** rendered the real production template against all 5 `INDUSTRIES` values (`Accounting`, `Family Office / Wealth Management`, `Financial Institution`, `Fund`, `Tax Exempt / Non-Profit`) via the Jinja2+Playwright rig, at desktop widths 1100/900/780/761px (761 is the last pixel before the 760px mobile breakpoint) and mobile (400px). The two long names now wrap to 2 lines and stay entirely left of the narrative card's border at every width tested; the three short names still render on one line, unchanged from before the fix; mobile stacked layout unaffected (already had its own override).
**Rule for future card/layout redesigns:** when giving a previously-transparent grid/flex sibling a visible background or border, don't just verify that sibling's own content -- also re-check every *other* item in the same container for `white-space:nowrap`, negative margins, or fixed widths that assumed an empty/transparent neighbor. Those assumptions can be correct and invisible for years and then become visibly wrong the moment a neighboring area stops being blank, with no code change to the item that actually breaks.
**Cross-references:** the narrative-card redesign earlier this same session (item 4 of Open Item #10, `results.html`'s `.narrative-card`) -- this bug is a direct, delayed side effect of that change, not an independent defect. P047 (same day, same page, another "looked fine until you looked closely" catch by Ben).

---

## P050 [WEB] -- CloudFront Rejects Cookie/Header/QueryString and Compression Settings on a Zero-TTL Cache Policy (2026-08-28)

**Date:** 2026-08-28
**Severity:** Medium -- a `CREATE_FAILED` and full stack rollback on the first `cdk deploy PmtcDomain`. No live resource was affected (the stack was new, and the app's own `PmtcApp`/Lambda/Function URL were untouched throughout), but the deploy had to be re-run and the design had to change.
**Discovered:** First real `cdk deploy` of the PMTC custom-domain stack, run by Tristen from his own machine. `Resource handler returned message: "Invalid request provided: AWS::CloudFront::CachePolicy: The parameter CookieBehavior is invalid for policy with caching disabled."`
**Pattern:** `domain-stack.ts` defined a custom `CachePolicy` with `minTtl`/`defaultTtl`/`maxTtl` all zero (correct -- every page in this app is per-session and must never be cached) but *also* set `cookieBehavior: all()`, `queryStringBehavior: all()`, and `enableAcceptEncodingGzip/Brotli: true`. CloudFront treats all-TTLs-zero as "caching disabled" and then refuses any cache-key parameter at all. The cookie/query settings were redundant in the first place -- what actually forwards cookies and query strings to the origin is the *origin request policy* (`ALL_VIEWER_EXCEPT_HOST_HEADER`), an entirely separate mechanism from the cache policy, which only decides the cache key. The compression flags were not redundant, and that is where the real cost landed.
**Root cause of the miss:** `cdk synth` validates against the CDK's own TypeScript types and CloudFormation's schema, neither of which encodes this CloudFront service-side constraint. The stack synthesized perfectly clean, and the synthesized template was inspected field by field before deploying -- the combination is only rejected by the CloudFront API itself, at create time. Same lesson family as P044/P045: a check that runs entirely locally cannot confirm a constraint that only the real service enforces.
**Fix:** Dropped the custom policy for the managed `CachePolicy.CACHING_DISABLED`. Cookies and query strings still reach Flask, unchanged, via the origin request policy. Compression at the edge is lost: the origin sends no `Content-Encoding` of its own (measured -- `/profile` is 64,991 bytes with `Accept-Encoding: gzip, br` on the request), so pages are served uncompressed where gzip/brotli would have been roughly a 6x cut. The constraint was confirmed to extend to compression, not just cookies, by probing the `CreateCachePolicy` API directly with a throwaway policy rather than by re-running the deploy: `The parameter EnableAcceptEncodingGzip is invalid for policy with caching disabled`.
**Workaround considered and deliberately rejected:** a `maxTtl` of 1 second makes the policy legal and buys compression back. Rejected on a security ground, not a correctness one: `GET /` calls `session.clear()` and so returns a `Set-Cookie`, and a first-time visitor has no cookie for the cache key to distinguish them by -- so within that one-second window a second cookieless visitor could be served the cached response *including its `Set-Cookie`* and land inside the first visitor's Flask session. That is session fixation, on a tool that collects names and email addresses, in exchange for page weight. The correct way to recover the compression is at the origin (`flask-compress` in the app), which also benefits the bare Function URL and involves no caching at all.
**Rule for future projects putting CloudFront in front of a dynamic, session-bearing app:** use the managed `CACHING_DISABLED` policy rather than hand-rolling a zero-TTL one -- CloudFront forbids every cache-key and compression parameter on such a policy, so a custom one can only ever be equivalent or invalid. Keep the distinction between the *cache policy* (what forms the cache key) and the *origin request policy* (what is forwarded to the origin) firmly in mind: forwarding cookies to a dynamic origin is the origin request policy's job, and putting them in the cache policy is at best redundant. And treat any TTL above zero on a route that can emit `Set-Cookie` as a session-sharing bug rather than a caching tradeoff, however short the TTL.
**Cross-references:** P044, P045 (same root-cause family -- local/sandbox verification passing while the real service rejects the same input).

---
