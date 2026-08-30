# Standing Rules -- Web Project Template

**Purpose:** Authoritative behavioral rules for all xlsx+pptx-to-web projects. Read at session start AND before any build operation. If CLAUDE_problems.md conflicts with this file, CLAUDE_problems.md is primary -- update this file immediately.

---

## Session Protocol

1. Read CLAUDE.md
2. Read PROJECT_STATE.md
3. Read STANDING_RULES.md (this file) -- required before any build operation
4. Read CLAUDE_problems.md for full RCA context on any relevant pattern
5. Read PLATFORM.md before any build operation
6. Write/update the session-start verification marker (`.session_protocol_verified`, same folder as this file) once steps 1-4 are confirmed done via actual tool calls this turn -- see SESSION-START AND COMPACTION RECOVERY PROTOCOL below.

---

## Shared Documentation Sync Rule

`STANDING_RULES.md` and `CLAUDE_problems.md` are shared across every project built from this template -- unlike `CLAUDE.md`/`PROJECT_STATE.md`/`SESSION_LOG.md`, which stay project-specific and one-way (the template's blank shell feeds a new project at kickoff; a project's filled-in narrative never flows back).

When either shared file gains a genuinely general-purpose addition during project work (a new behavioral rule, a new CLAUDE_problems.md pattern), propagate it to `WEB PROJECT template`'s copy of the same file in the same session, not as a deferred separate ask:
- Check the template's current state first (e.g., its highest CLAUDE_problems.md P-number) before assigning a new entry number in this project's own copy, to avoid a numbering collision if more than one project is drawing from the template at once.
- Confirm the addition is actually general -- behavioral or process, not tangled up with this project's own client data -- before copying it over. Rewrite or trim project-specific framing first if needed.
- Log the sync in SESSION_LOG.md, since neither copy is under git version control.

This exists so a lesson learned on one project doesn't have to be rediscovered on the next one.

---

## Core Behavioral Rules

- **No em dashes.** Use en dashes (--) or restructure.
- **No multiple-choice question pickers.** Ask in plain prose. Ben's answers are always free text.
- **Explicit confirmation required before proceeding on any plan.** Firm standing rule.
- **Calibrate confidence.** Flag uncertainty explicitly. Never state compaction reconstructions as facts.
- **Timestamp all SESSION_LOG.md entries** using the eastern-time skill.
- **Document errors immediately** before continuing work. See CLAUDE_problems.md META-RULE.
- **"Discuss", "ask questions", or similar does NOT authorize file action.** These mean respond with text only.

---

## File Writing Rules [P003, P025, P026, P031, P032, P033]

**The Write and Edit tools silently truncate ALL file types at ~3KB. The tools always report success.**

- **Never use the Write or Edit tools on any project file.** Always use bash.
- **Never use `python3 -c "open(...).write(...)"` or any Python one-liner rewriting via open().write().**
- **Never use `python3 - << 'EOF'` heredoc scripts that call open().write().**
- Full file write: `cat > /path/to/file << 'EOF' ... EOF`
- Targeted replacement: `sed -i 's/old/new/g'` or `sed -i '{n}s/.*/new/'`
- Append to syntactically complete file: `cat >> file << 'EOF' ... EOF`
- Remove stray truncated line: `sed -i '{n}d' file`
- **After every write, run `bash check_files.sh`**
- **After every verified-good write, run `python3 check_structure.py --update`**
- Manual spot-check: `wc -l filename && tail -5 filename`
- For Python: `python3 -c "import ast; ast.parse(open('file.py').read()); print('OK')"`
- For HTML: confirm `{% endblock %}` or `</html>` in tail

---

## Research and Citation Rules [P006]

- **Never cite a URL without fetching it first** to verify it resolves and contains the cited claim.
- If a URL cannot be fetched or redirects to an unrelated page, do not cite it.
- Invoke the `verified-research` skill whenever any stat, benchmark, or external source appears in output.

---

## Compaction and Memory Rules [P001, P002, P007, P008, P009, P013]

- **Never trust in-session memory for structured data** (tables, matrices, cell references) after a long session.
- **Never write a reference document from session memory alone.** Read source files first.
- **Before stating any cell, file, or shape content, read it in the current session.** No exceptions.
- When a session shows a compaction summary, treat ALL in-context facts as unverified.
- For multi-item checklists (>6 items), maintain a persistent state file on disk.

---

## Flask Rules [P024, P027]

- After any session mutations following a long-running subprocess, set `session.modified = True` explicitly.
- Never use `request.app` -- it does not exist. Use `current_app` from flask.
- `GET /` always clears session (fresh start). `GET /edit_profile` pre-fills from session.
- All mid-flow back links must route to `/edit_profile`, not `/` (P036).

---

## python-pptx Rules [P030]

- **Before writing any shape-population code, inspect the template's existing shape content.**
- Only push to shapes confirmed EMPTY. Pre-filled shapes retain formatting -- overwriting strips it.
- For slides with duplicated structure (e.g., 15 benefit slides), inspect one representative slide.

---

## Hosting and Docker Rules [P028, P029]

- Never add `*.xlsx`, `*.xlsm`, or `*.pptx` to `.dockerignore` -- they are reference data, not build artifacts.
- LibreOffice requires ~300MB RAM. Render free tier (512MB) is insufficient -- use Cloud Run (2Gi) or xlcalculator.

---

## Git Rules [P033]

**The sandbox cannot reliably run git commands** -- stale lock files accumulate, permissions issues occur.

- **Never rely on sandbox git for commits.** Always commit from your local machine.
- After any session where files were modified:
  ```powershell
  bash check_files.sh     # verify integrity first
  git add -A
  git commit -m "Session N: brief description"
  git push
  ```
- **Every git push and Cloud Run deploy must be timestamped in the Authoritative Source Registry** in PROJECT_STATE.md.
- If a bad commit lands from a sandbox git attempt: `git reset HEAD~1` from local machine before pushing.
- **2026-08-30 update:** the LFS half of this rule's rationale is resolved -- git-lfs is now installed in the bridge shell (`~/bin/git-lfs`, confirmed resolving pointers correctly), so a commit from here no longer risks silently de-LFS-ing binaries (the P033/P048 failure mode). A real commit (`51410a0`) was made from the bridge shell this session with Ben's explicit go-ahead and verified clean. **Push still cannot happen from here** -- this shell has no GitHub credentials/credential-helper configured, and none will be entered on Ben's behalf (entering credentials/tokens is off-limits regardless of instruction). So: commits from the bridge shell are no longer a rule violation when Ben explicitly asks for one, but push is still always from Ben's own machine. Whether the installed `git-lfs` binary survives to a future session is unconfirmed -- may need reinstalling; check `git lfs version` before relying on it again.
- **Don't propose a commit after every individual page/section of a multi-part deliverable** (a multi-page report, a multi-file build). Keep building and saving to the working directory across the whole batch; only bring up committing at a natural checkpoint (a batch done, a session ending) or when Ben asks for it. Asking after each small unit is exactly the kind of thing that stops being helpful and starts being noise on a 12-20 page job.

---

## SESSION-START AND COMPACTION RECOVERY PROTOCOL -- MANDATORY

When a compaction event is detected, Claude MUST immediately read ALL of the following before responding to anything else:

1. `CLAUDE.md` -- project reference; challenge-benefit matrix; decisions
2. `PROJECT_STATE.md` -- current open/closed status; pending items
3. `STANDING_RULES.md` (this file) -- all behavioral rules
4. `CLAUDE_problems.md` -- all known failure patterns

**Verification marker (closes the "no signal at all" case -- see CLAUDE_problems.md P040):** Noticing a compaction-shaped signal is not sufficient by itself. If compaction occurs before this protocol has ever completed -- e.g., mid-way through the very first session-start read-through -- there may be no narrative cue to notice at all. To make this checkable rather than a matter of memory or feel:

- Immediately after each of the four files above is read via an actual tool call, append a timestamped line to `.session_protocol_verified` (a small local marker file in the same folder as this file, outside git, not part of check_files.sh's checked set).
- Before any substantive work in any turn (research, coding, content, file edits -- not a quick clarifying reply), check this marker. It only counts as valid if BOTH (a) it shows all four files logged with a completion line, AND (b) the corresponding `Read` tool calls are actually visible in the current context -- a marker whose timestamp cannot be backed up with visible tool-call history is stale and does not count, regardless of what it says or what a summary implies.
- If the marker is missing, incomplete, or unverifiable against current context, treat the protocol as not yet done -- run it in full and write a fresh marker before proceeding.

**A "compaction event" includes:** a session opening with an already-compacted summary as its first message, a mid-session notice referencing compaction, or any instruction to "follow protocol." All of these trigger this section -- not only an explicit system compaction marker. Read the four files before any other action, including before responding with any text, even a summary that seems ready to give.

Do not act on the compaction summary alone. The summary is a lossy reconstruction. A detailed, plausible-looking narrative summary is NOT a substitute for reading these files, no matter how complete it looks -- writing one in place of the actual read is itself a protocol violation (see CLAUDE_problems.md P039).

If this protocol was skipped once already this session and then corrected, treat that as a reason to actively re-verify compliance for the rest of the session -- not as a closed incident. The same gap can recur immediately after being caught once (see CLAUDE_problems.md P039).

---

## Rollback Rule

Always restore from the most recent authoritative source -- never rewrite from memory.

Authoritative sources in order of preference:
1. **Git** -- `git checkout <commit> -- <file(s)>`
2. **Cloud Run** -- currently deployed container is a known-good snapshot
3. **Local sandbox files** -- only if git and Cloud Run are both unavailable

---

## Questions vs. Actions

**When Ben asks a question, respond with information only. Never edit, write, or act on files.**

"Discuss", "ask questions", or similar phrasing means text response only. File writes require explicit direction to proceed.

---

## Pre-Build Checklist

Before any coding or file-writing operation:

1. Read STANDING_RULES.md (this file)
2. Read CLAUDE_problems.md -- scan for patterns relevant to the current task
3. Read PLATFORM.md -- confirm patterns to follow
4. If touching the workbook: verify named ranges against the live file
5. Writing any file: use bash cat-heredoc -- never Write or Edit tool
6. After every file write: `wc -l && tail -5 && syntax check`
7. After any meaningful changes: `bash check_files.sh` then commit from local machine

