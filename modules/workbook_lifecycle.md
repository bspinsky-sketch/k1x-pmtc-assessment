# modules/workbook_lifecycle.md -- Refreshing a Live Workbook Without a Redeploy

**When to read:** Phase 11, and again whenever a client sends an updated workbook post-launch.

**Purpose:** The client never has backend access -- they update their own copy of the spreadsheet and hand it to Ben. This module is the reusable mechanism for getting that update live without a code deploy, and without ever pushing a broken workbook to production.

---

## Why this exists

Before this module, reference data (Tier 1 constants, or the Tier 2 xlcalculator model) got hydrated once at module import time and baked into whatever container was deployed. The only way to pick up a new workbook was a full redeploy. There was also no documented process at all for what happens when a client sends an updated file -- see CLAUDE.md's Key Decisions Log for the project this was first identified on. This module closes both gaps.

---

## Storage

- Provision one cloud storage bucket per project (same GCP project as the Cloud Run service -- see modules/hosting_cloudrun.md).
- The live workbook lives in the bucket, not in the Docker image and not in the git-tracked reference data path. `.dockerignore` should exclude the workbook entirely for this pattern (the opposite of P029's rule, which is about workbooks still baked into the image under the old model -- if the workbook lives in the bucket, it was never meant to be in the image).
- Keep prior versions with a timestamp suffix: `workbook_2026-08-14T1400.xlsx`. Never overwrite in place -- a bad refresh needs a rollback target.

```
gs://[project]-workbooks/
  workbook_2026-06-01T0900.xlsx
  workbook_2026-08-14T1400.xlsx   <- current
```

## Loader as a callable

Whatever tier the calc engine uses (see modules/calc_engine.md), the reference-data load must be a function that can be re-invoked, not code that only runs at import time:

```python
# workbook_loader.py
import threading
from google.cloud import storage

_lock = threading.Lock()
_state = {'reference': None, 'model': None, 'version': None}

def load_from_bucket(bucket_name, blob_name):
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(blob_name)
    local_path = f"/tmp/{blob_name}"
    blob.download_to_filename(local_path)
    return local_path

def reload_workbook(bucket_name, blob_name):
    """Called at startup, and again by /admin/reload-workbook."""
    local_path = load_from_bucket(bucket_name, blob_name)
    audit_result = run_structure_audit(local_path)   # WORKBOOK_CONVENTIONS.md Part 2, Steps 1-3
    if not audit_result.passed:
        return {'ok': False, 'errors': audit_result.errors, 'version': _state['version']}

    new_reference = load_reference_data(local_path)   # Tier 1, or _load_model() for Tier 2
    with _lock:
        _state['reference'] = new_reference
        _state['version'] = blob_name
    return {'ok': True, 'version': blob_name}

def current_reference():
    with _lock:
        return _state['reference']
```

## Admin reload route

```python
# routes.py
import os
from flask import request, jsonify, abort

@bp.route('/admin/reload-workbook', methods=['POST'])
def admin_reload_workbook():
    if request.headers.get('X-Reload-Secret') != os.environ['RELOAD_SECRET']:
        abort(403)
    blob_name = request.json.get('blob_name')
    result = reload_workbook(os.environ['WORKBOOK_BUCKET'], blob_name)
    status = 200 if result['ok'] else 409
    return jsonify(result), status
```

**Rules:**
- `RELOAD_SECRET` is a separate shared secret, not Auth0 -- this route is an operational lever for Ben, not a user-facing feature.
- The audit (WORKBOOK_CONVENTIONS.md Part 2, Steps 1-3) always runs before the swap. A failed audit returns errors and leaves `_state['reference']` untouched -- the app keeps serving the last good version. Never swap first and validate after.
- The swap itself is a single dict/lock update, not a restart -- existing in-flight requests finish against whichever version they started with; new requests see the new version immediately after the lock releases.

## The actual handoff, since the client has no backend access

1. Client emails Ben the updated workbook (or drops it in a shared drive folder -- however they already send files today, no new process needed on their end).
2. Ben uploads it to the bucket: `gsutil cp updated.xlsx gs://[project]-workbooks/workbook_$(date +%Y-%m-%dT%H%M).xlsx`
3. Ben calls the reload route: `curl -X POST https://[project-url]/admin/reload-workbook -H "X-Reload-Secret: ..." -d '{"blob_name": "workbook_2026-08-14T1400.xlsx"}'`
4. If the response is `{"ok": true, ...}`, spot-check a few KPI values on the live site against the new workbook. If `{"ok": false, ...}`, the old version is still live -- fix the flagged issue in the workbook (or in the app, if the workbook's structure legitimately changed) before retrying.
5. Log the reload -- timestamp, blob name, outcome -- in PROJECT_STATE.md's Authoritative Source Registry.

## What this does not cover

- A change to the model's *logic* (not just its reference data/defaults) still requires a code change and a normal deploy -- this mechanism only covers data refreshes within the workbook's existing structure.
- If a refresh needs to change named ranges or sheet structure, that is a Phase 4-style change, not a Phase 11 reload -- treat it as a mini re-audit and possibly a calc-engine tier change, not a routine refresh.
