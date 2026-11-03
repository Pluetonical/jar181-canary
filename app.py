import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STARTED = time.time()
HEALTH_FAIL = True
BUILD = "v2-bad-health"


def read_cgroup(name, v1path):
    candidates = [f"/sys/fs/cgroup/{name}", f"/sys/fs/cgroup/{v1path}"]
    for path in candidates:
        try:
            with open(path) as handle:
                return handle.read().strip()
        except OSError:
            continue
    return None


def limits():
    return {
        "memory_max": read_cgroup("memory.max", "memory/memory.limit_in_bytes"),
        "cpu_max": read_cgroup("cpu.max", "cpu/cpu.cfs_quota_us"),
        "pids_max": read_cgroup("pids.max", "pids/pids.max"),
    }


def redacted_env():
    secret_markers = ("TOKEN", "SECRET", "PASSWORD", "KEY", "DATABASE_URL", "CREDENTIAL")
    out = {}
    for key in sorted(os.environ):
        value = os.environ[key]
        out[key] = "[redacted]" if any(marker in key.upper() for marker in secret_markers) else value
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload, content_type="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            if HEALTH_FAIL:
                self._send(503, {"status": "unhealthy", "build": BUILD})
            else:
                self._send(200, {"status": "ok", "build": BUILD, "uptime_s": round(time.time() - STARTED, 1)})
        elif path == "/version":
            self._send(200, {
                "build": BUILD,
                "sha_env": os.environ.get("GIT_COMMIT") or os.environ.get("PLUE_COMMIT") or os.environ.get("CANARY_SHA"),
            })
        elif path == "/limits":
            self._send(200, limits())
        elif path == "/env":
            self._send(200, {"keys": redacted_env()})
        elif path == "/crash":
            self._send(200, {"crashing": True})
            os._exit(1)
        elif path in ("/", "/index.html"):
            self._send(200, {"service": "jar181-canary", "build": BUILD}, "application/json")
        else:
            self._send(404, {"error": "not_found"})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
