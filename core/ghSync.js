// core/ghSync.js — one-shot app → GH push at round boundaries.
// ─────────────────────────────────────────────────────────────────────────
// Round-sync flow (see core/roundSync.js for the full orchestrator):
//   1. Agents synthesise a param delta
//   2. App applies it to local params
//   3. pushGhInputs(params) posts the whole payload to /gh-inputs
//   4. serve.py atomically writes snapshots/.gh-inputs.json
//   5. gh-inputs-read.py reads it on the next GH timer tick
//   6. GH solves, gh-params-export.py writes snapshots/latest/params.json
//      (echoing the roundToken the app embedded in the payload)
//   7. roundSync polls that file and resumes when roundToken matches
//
// No polling, no debounce, no live per-slider sync. Call this exactly
// once per round, from roundSync.js, with the full params object.
// ─────────────────────────────────────────────────────────────────────────

/**
 * Post the full params snapshot to serve.py, which writes .gh-inputs.json
 * atomically. Returns the parsed JSON response on success, or throws.
 * @param {object} params  Full params object (will be shallow-cloned).
 */
export async function pushGhInputs(params) {
  const payload = { ...params, _ts: Date.now() };
  const res = await fetch('/gh-inputs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error('pushGhInputs failed: ' + res.status);
  }
  return res.json();
}
