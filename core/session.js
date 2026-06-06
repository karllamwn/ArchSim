// core/session.js — Design session marker lifecycle
// ─────────────────────────────────────────────────────────────────────────
// When the user submits a new Client Brief, we call `startNewSession(brief)`
// which POSTs to the local dev server's /session endpoint (see serve.py).
// The server writes snapshots/.session.json with a fresh sessionId.
//
// On the next GH `export = True`, gh-params-export.py reads that file,
// compares the sessionId to what's in snapshots/manifest.json, and if
// they differ it archives the previous session and resets the round
// counter to R001.
//
// IMPORTANT: this requires running the app via `python serve.py` rather
// than `python -m http.server 3000` — the latter has no POST support.
// If the endpoint is unreachable, we warn to the console but don't block
// the UI. The user can continue; GH just won't reset automatically.
// ─────────────────────────────────────────────────────────────────────────

/**
 * Start a new design session. Writes snapshots/.session.json via the
 * local dev server (serve.py).
 * @param {string} brief  The raw Client Brief text
 * @returns {Promise<object|null>} session data, or null if the call failed
 */
export async function startNewSession(brief = '') {
  try {
    const res = await fetch('/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ brief }),
    });
    if (!res.ok) {
      console.warn('[session] marker write failed:', res.status, res.statusText);
      return null;
    }
    const data = await res.json();
    console.log('[session] started', data.sessionId);
    return data;
  } catch (e) {
    console.warn(
      '[session] marker write error — is serve.py running?\n' +
      '  Run: python serve.py   (instead of python -m http.server)',
      e
    );
    return null;
  }
}

/**
 * Get the current session marker, if one exists.
 * @returns {Promise<object|null>}
 */
export async function getCurrentSession() {
  try {
    const res = await fetch('/session');
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}
