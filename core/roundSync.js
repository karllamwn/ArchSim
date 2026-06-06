// core/roundSync.js — round-boundary orchestrator for app ↔ Grasshopper.
// ─────────────────────────────────────────────────────────────────────────
// Called once per round (after the planner commits a param delta) to:
//   1. Generate a fresh roundToken "R{n}_{timestamp}_{uuid6}"
//   2. POST full params (with roundToken) to serve.py /gh-inputs
//   3. Show a UI lock overlay with a 0→90s elapsed counter
//   4. Poll params.json until it contains our roundToken (GH solved)
//   5. Call window.syncFromGH() to pull the new results into the UI
//   6. Remove overlay, resolve the promise
//
// Timeout (90s) → modal with [RETRY] (restart the cycle, fresh 90s clock)
// and [CONTINUE OFFLINE] (set window._ghOfflineMode = true for THIS round,
// unlock, let callers fall back to api/hops.js estimators). Offline mode
// auto-clears at the start of the next round.
//
// A "progress narrator" slot is supported via options.onNarrate — if the
// caller provides a function, we invoke it once with the elapsed seconds
// + roundToken so the activity feed can show a 2-sentence "GH is solving
// X, Y, Z" line from the LLM while the user waits.
//
// Requires:
//   - serve.py running (for POST /gh-inputs + serving params.json)
//   - core/ghSync.js → pushGhInputs
//   - window.syncFromGH() defined in index.html (pulls params.json → UI)
// ─────────────────────────────────────────────────────────────────────────

import { pushGhInputs } from './ghSync.js';

const TIMEOUT_MS       = 180_000;   // 3 minutes — was 90s; allows slower GH solves
const POLL_INTERVAL_MS = 1_000;
const PARAMS_URL       = 'params.json';

// ── Overlay + modal DOM (injected lazily, once) ──────────────────────────

const OVERLAY_ID = 'roundSyncOverlay';
const MODAL_ID   = 'roundSyncTimeoutModal';

function _ensureOverlayStyles() {
  if (document.getElementById('roundSyncStyles')) return;
  const s = document.createElement('style');
  s.id = 'roundSyncStyles';
  s.textContent = `
    #${OVERLAY_ID} {
      position: fixed; inset: 0; z-index: 99998;
      background: rgba(13,23,22,0.72); backdrop-filter: blur(2px);
      display: flex; align-items: center; justify-content: center;
      font-family: 'Press Start 2P', monospace;
      color: #abdac9; pointer-events: all;
    }
    #${OVERLAY_ID} .rs-box {
      min-width: 420px; max-width: 560px;
      border: 1px solid rgba(171,218,201,0.5);
      background: #0d1716;
      padding: 24px 28px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.6);
      text-align: center;
    }
    #${OVERLAY_ID} .rs-title {
      font-size: 11px; letter-spacing: 2px; color: #45d1b3;
      margin-bottom: 14px;
    }
    #${OVERLAY_ID} .rs-spinner {
      font-size: 22px; margin: 8px 0 14px; color: #45d1b3;
    }
    #${OVERLAY_ID} .rs-sub {
      font-family: VT323, monospace;
      font-size: 16px; color: #abdac9; line-height: 1.4;
      margin-top: 6px;
    }
    #${OVERLAY_ID} .rs-token {
      font-family: VT323, monospace;
      font-size: 12px; color: rgba(171,218,201,0.5);
      margin-top: 10px;
    }
    #${MODAL_ID} {
      position: fixed; inset: 0; z-index: 99999;
      background: rgba(13,23,22,0.88);
      display: flex; align-items: center; justify-content: center;
      font-family: 'Press Start 2P', monospace;
      color: #abdac9;
    }
    #${MODAL_ID} .rs-modal {
      min-width: 440px; max-width: 580px;
      border: 1px solid #ff7f50;
      background: #0d1716;
      padding: 28px 32px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.8);
    }
    #${MODAL_ID} .rs-modal-title {
      font-size: 12px; letter-spacing: 2px; color: #ff7f50;
      margin-bottom: 16px; text-align: center;
    }
    #${MODAL_ID} .rs-modal-body {
      font-family: VT323, monospace;
      font-size: 16px; color: #abdac9;
      line-height: 1.5; margin-bottom: 20px; text-align: center;
    }
    #${MODAL_ID} .rs-btn-row {
      display: flex; gap: 10px; justify-content: center;
    }
    #${MODAL_ID} button {
      font-family: 'Press Start 2P', monospace;
      font-size: 10px; letter-spacing: 1px;
      background: transparent;
      color: #abdac9;
      border: 1px solid rgba(171,218,201,0.5);
      padding: 12px 18px;
      cursor: pointer;
    }
    #${MODAL_ID} button:hover { border-color: #45d1b3; color: #45d1b3; }
    #${MODAL_ID} button.rs-offline { border-color: #ff7f50; color: #ff7f50; }
    #${MODAL_ID} button.rs-offline:hover { background: rgba(255,127,80,0.1); }
    .rs-offline-banner {
      position: fixed; top: 0; left: 0; right: 0;
      background: #ff7f50; color: #0d1716;
      font-family: 'Press Start 2P', monospace;
      font-size: 9px; letter-spacing: 1px;
      padding: 6px 12px; text-align: center; z-index: 99997;
    }
  `;
  document.head.appendChild(s);
}

function _showOverlay(roundNumber, roundToken, title) {
  _ensureOverlayStyles();
  let ov = document.getElementById(OVERLAY_ID);
  if (!ov) {
    ov = document.createElement('div');
    ov.id = OVERLAY_ID;
    document.body.appendChild(ov);
  }
  const displayTitle = title || ('GRASSHOPPER SOLVING — ROUND ' + roundNumber);
  ov.innerHTML = `
    <div class="rs-box">
      <div class="rs-title">${displayTitle}</div>
      <div class="rs-spinner">◴</div>
      <div class="rs-sub" id="rsElapsed">0s / ${Math.round(TIMEOUT_MS / 1000)}s</div>
      <div class="rs-sub" id="rsNarrator" style="opacity:0.75;min-height:22px;"></div>
      <div class="rs-token">${roundToken}</div>
    </div>
  `;
  // Spinner rotation
  let spinFrame = 0;
  const spinChars = ['◴','◷','◶','◵'];
  const spinnerEl = ov.querySelector('.rs-spinner');
  ov._spinInterval = setInterval(() => {
    spinFrame = (spinFrame + 1) % spinChars.length;
    if (spinnerEl) spinnerEl.textContent = spinChars[spinFrame];
  }, 220);
  return ov;
}

function _updateOverlayElapsed(elapsedMs) {
  const el = document.getElementById('rsElapsed');
  if (el) el.textContent = Math.round(elapsedMs / 1000) + 's / ' + Math.round(TIMEOUT_MS / 1000) + 's';
}

function _updateOverlayNarrator(text) {
  const el = document.getElementById('rsNarrator');
  if (el && text) el.textContent = text;
}

function _hideOverlay() {
  const ov = document.getElementById(OVERLAY_ID);
  if (ov) {
    if (ov._spinInterval) clearInterval(ov._spinInterval);
    ov.remove();
  }
}

function _showTimeoutModal({ onRetry, onOffline, roundNumber }) {
  _ensureOverlayStyles();
  let m = document.getElementById(MODAL_ID);
  if (m) m.remove();
  m = document.createElement('div');
  m.id = MODAL_ID;
  m.innerHTML = `
    <div class="rs-modal">
      <div class="rs-modal-title">⚠ GRASSHOPPER TIMEOUT — ROUND ${roundNumber}</div>
      <div class="rs-modal-body">
        Grasshopper did not respond within ${Math.round(TIMEOUT_MS / 1000)} seconds.<br><br>
        Is Rhino / GH still running?<br>
        Is gh-inputs-read.py wired with a Timer?
      </div>
      <div class="rs-btn-row">
        <button id="rsRetryBtn" style="display:inline-flex;align-items:center;gap:4px;"><img src="assets/icon_sync.png" style="width:12px;height:12px;image-rendering:pixelated;"> RETRY</button>
        <button id="rsOfflineBtn" class="rs-offline" style="display:inline-flex;align-items:center;gap:4px;"><img src="assets/icon_play.png" style="width:12px;height:12px;image-rendering:pixelated;"> CONTINUE OFFLINE</button>
      </div>
    </div>
  `;
  document.body.appendChild(m);
  m.querySelector('#rsRetryBtn').onclick = () => {
    m.remove();
    onRetry();
  };
  m.querySelector('#rsOfflineBtn').onclick = () => {
    m.remove();
    onOffline();
  };
}

function _showOfflineBanner() {
  let b = document.getElementById('rsOfflineBanner');
  if (b) return;
  b = document.createElement('div');
  b.id = 'rsOfflineBanner';
  b.className = 'rs-offline-banner';
  b.textContent = '⚠ GH OFFLINE FOR THIS ROUND — USING ESTIMATED DATA';
  document.body.appendChild(b);
}
function _hideOfflineBanner() {
  const b = document.getElementById('rsOfflineBanner');
  if (b) b.remove();
}

// ── Polling for the matching roundToken in params.json ───────────────────

async function _fetchParams() {
  try {
    const res = await fetch(PARAMS_URL + '?t=' + Date.now(), { cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  } catch (_) {
    return null;
  }
}

async function _pollForToken(roundToken, startTime, onTick) {
  // Returns { matched: true, data } on success, or { matched: false } on timeout.
  while (true) {
    const elapsed = Date.now() - startTime;
    onTick(elapsed);
    if (elapsed >= TIMEOUT_MS) return { matched: false };
    const data = await _fetchParams();
    if (data && data.roundToken === roundToken) {
      return { matched: true, data };
    }
    await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
  }
}

// ── Public API ───────────────────────────────────────────────────────────

let _tokenCounter = 0;
function _makeToken(roundNumber) {
  _tokenCounter++;
  const ts = Date.now().toString(36);
  const uid = Math.random().toString(36).slice(2, 8);
  return 'R' + roundNumber + '_' + ts + '_' + uid;
}

/**
 * Run one round-end sync cycle.
 * @param {object} params       Full params object to push.
 * @param {object} opts
 * @param {number} opts.roundNumber        Round number for display + token.
 * @param {(roundToken:string)=>Promise<string>|string} [opts.onNarrate]
 *        Optional: called once shortly after lock; return a 1-2 sentence
 *        string to display as the "progress narrator" line.
 * @returns {Promise<{ status: 'ok'|'offline', data?: object }>}
 */
export async function runRoundSync(params, opts = {}) {
  console.log('[roundSync] runRoundSync ENTER — opts:', opts);
  const roundNumber = opts.roundNumber || 1;
  // Clear any prior offline flag — it applies to ONE round only
  if (window._ghOfflineMode) {
    window._ghOfflineMode = false;
    _hideOfflineBanner();
  }

  const attempt = async () => {
    const roundToken = _makeToken(roundNumber);
    const startTime  = Date.now();
    console.log('[roundSync] attempt starting — token:', roundToken);
    _showOverlay(roundNumber, roundToken, opts.title);
    console.log('[roundSync] overlay shown');

    // Pre-populate narrator with a default sentence immediately (no LLM wait)
    if (opts.defaultNarration) {
      _updateOverlayNarrator(opts.defaultNarration);
    }

    // Fire the narrator call in parallel — don't block on it
    if (typeof opts.onNarrate === 'function') {
      Promise.resolve()
        .then(() => opts.onNarrate(roundToken))
        .then(text => { if (text) _updateOverlayNarrator(text); })
        .catch(() => {});
    }

    // Push params + token to GH
    console.log('[roundSync] pushing gh-inputs...');
    try {
      await pushGhInputs({ ...params, roundToken });
      console.log('[roundSync] pushGhInputs succeeded');
    } catch (e) {
      console.warn('[roundSync] pushGhInputs failed:', e.message);
      // Fall through to poll anyway — serve.py might be down but GH might still solve
    }

    // Poll for matching token
    console.log('[roundSync] starting poll loop for token', roundToken);
    const result = await _pollForToken(roundToken, startTime, (elapsed) => {
      _updateOverlayElapsed(elapsed);
    });
    console.log('[roundSync] poll returned:', result.matched ? 'MATCHED' : 'TIMEOUT');

    if (result.matched) {
      _hideOverlay();
      // Pull new results into the UI via the existing syncFromGH function
      if (typeof window.syncFromGH === 'function') {
        try { await window.syncFromGH(); } catch (e) { console.warn('[roundSync] syncFromGH error:', e); }
      }
      return { status: 'ok', data: result.data };
    }

    // Timeout → retry or offline
    _hideOverlay();
    return new Promise((resolve) => {
      _showTimeoutModal({
        roundNumber,
        onRetry:   () => { attempt().then(resolve); },
        onOffline: () => {
          window._ghOfflineMode = true;
          _showOfflineBanner();
          resolve({ status: 'offline' });
        },
      });
    });
  };

  return attempt();
}

// Expose on window so inline scripts in index.html can call it without imports
if (typeof window !== 'undefined') {
  window.runRoundSync = runRoundSync;
}
