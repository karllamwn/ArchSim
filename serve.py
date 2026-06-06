#!/usr/bin/env python3
"""ArchSim V2 — local dev server.

Replacement for `python -m http.server 3000`. Serves the static app and
adds a single endpoint:

    POST /session
        body: {"brief": "…"}
        Writes snapshots/.session.json with a fresh sessionId. The GH
        gh-params-export.py script reads this on each export and, if the
        sessionId differs from what's in snapshots/manifest.json, archives
        the previous session and resets the round counter to R001.

Run with:
    python serve.py
or
    python serve.py 3001        # custom port
"""
import http.server
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

PORT = 3000
PROJECT_ROOT = Path(__file__).resolve().parent
SNAPSHOT_DIR   = PROJECT_ROOT / "snapshots"
SESSION_FILE   = SNAPSHOT_DIR / ".session.json"
GH_INPUTS_FILE = SNAPSHOT_DIR / ".gh-inputs.json"  # app → GH  (app writes, GH reads)
GH_LIVE_FILE   = SNAPSHOT_DIR / ".gh-live.json"    # GH → app  (GH writes, app polls)


def _write_session(brief: str) -> dict:
    now = datetime.now()
    session_id = "{}-{}".format(
        now.strftime("%Y%m%dT%H%M%S"),
        uuid.uuid4().hex[:6],
    )
    data = {
        "sessionId": session_id,
        "startedAt": now.strftime("%Y-%m-%d %H:%M:%S"),
        "brief": (brief or "")[:1000],  # cap length for disk/log
    }
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("[session] new session written: {}".format(session_id))
    return data


class Handler(http.server.SimpleHTTPRequestHandler):
    # Add CORS headers to every response so the browser can POST to /session
    # even though it's technically same-origin (kept for safety if the app
    # ever gets served from a different port).
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        # Disable caching so dev reloads pick up file changes immediately
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        if self.path == "/session":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length else ""
                payload = json.loads(raw) if raw.strip() else {}
            except Exception as e:
                self._json(400, {"error": "invalid json: " + str(e)})
                return

            brief = str(payload.get("brief", ""))
            try:
                data = _write_session(brief)
                self._json(200, data)
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if self.path == "/gh-inputs":
            # App pushes live slider values here. Atomic write so GH never
            # reads a half-written file.
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length else ""
                payload = json.loads(raw) if raw.strip() else {}
            except Exception as e:
                self._json(400, {"error": "invalid json: " + str(e)})
                return
            try:
                SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
                tmp = GH_INPUTS_FILE.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                tmp.replace(GH_INPUTS_FILE)
                self._json(200, {"ok": True, "count": len(payload)})
            except Exception as e:
                self._json(500, {"error": str(e)})
            return

        if self.path == "/copy-snapshot":
            # Copy snapshots/latest/Parallel_*.jpg → picker/<stepId>/<value>_<view>.jpg
            # Body: { stepId, value, viewMap: { "NE": "Parallel_NE", ... } }
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length else ""
                payload = json.loads(raw) if raw.strip() else {}
            except Exception as e:
                self._json(400, {"error": "invalid json: " + str(e)})
                return

            step_id = payload.get("stepId", "")
            value = payload.get("value", "")
            view_map = payload.get("viewMap", {
                "NE": "Parallel_NE",
                "NW": "Parallel_NW",
                "SE": "Parallel_SE",
                "SW": "Parallel_SW",
            })

            if not step_id or value == "":
                self._json(400, {"error": "stepId and value required"})
                return

            picker_dir = PROJECT_ROOT / "picker" / step_id
            picker_dir.mkdir(parents=True, exist_ok=True)

            copied = []
            errors = []
            latest = SNAPSHOT_DIR / "latest"
            for view_suffix, src_name in view_map.items():
                src = latest / (src_name + ".jpg")
                dst = picker_dir / ("{}_{}.jpg".format(value, view_suffix))
                if src.exists():
                    import shutil
                    shutil.copyfile(str(src), str(dst))
                    copied.append(str(dst.relative_to(PROJECT_ROOT)))
                else:
                    errors.append("{} not found".format(src_name))

            self._json(200, {"copied": copied, "errors": errors})
            return

        self._json(404, {"error": "unknown endpoint: " + self.path})

    def do_GET(self):
        if self.path == "/session":
            if SESSION_FILE.exists():
                try:
                    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
                    self._json(200, data)
                    return
                except Exception as e:
                    self._json(500, {"error": "corrupt session file: " + str(e)})
                    return
            self._json(404, {"error": "no session yet"})
            return

        if self.path == "/gh-live":
            # App polls this — returns last snapshot GH wrote to .gh-live.json.
            # 204 No Content when the file doesn't exist yet (GH not running).
            if GH_LIVE_FILE.exists():
                try:
                    data = json.loads(GH_LIVE_FILE.read_text(encoding="utf-8"))
                    self._json(200, data)
                    return
                except Exception as e:
                    self._json(500, {"error": "corrupt gh-live file: " + str(e)})
                    return
            self.send_response(204)
            self.end_headers()
            return

        if self.path == "/gh-inputs":
            # Debug read-back of what was last pushed.
            if GH_INPUTS_FILE.exists():
                try:
                    data = json.loads(GH_INPUTS_FILE.read_text(encoding="utf-8"))
                    self._json(200, data)
                    return
                except Exception as e:
                    self._json(500, {"error": "corrupt gh-inputs file: " + str(e)})
                    return
            self.send_response(204)
            self.end_headers()
            return

        # Fall through to static file serving
        return super().do_GET()

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Quieter, cleaner logging: one-line format
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


def main():
    port = PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("usage: python serve.py [port]")
            sys.exit(1)

    os.chdir(PROJECT_ROOT)
    print("ArchSim V2 dev server")
    print("  project root: {}".format(PROJECT_ROOT))
    print("  session file: {}".format(SESSION_FILE))
    print("  serving at:   http://localhost:{}".format(port))
    print("  (Ctrl+C to stop)")
    print()

    with http.server.ThreadingHTTPServer(("", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopping…")


if __name__ == "__main__":
    main()
