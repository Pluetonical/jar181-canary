import json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STARTED = time.time()
SHA = os.environ.get("WORKLOAD_COMMIT", os.environ.get("GIT_COMMIT", "unknown"))
VERSION = os.environ.get("CANARY_VERSION", "good")
FAIL = os.environ.get("CANARY_HEALTH_FAIL", "0") == "1"

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path == "/health":
            if FAIL:
                self._send(503, {"status": "unhealthy", "version": VERSION, "sha": SHA})
            else:
                self._send(200, {"status": "ok", "version": VERSION, "sha": SHA, "uptime_s": round(time.time()-STARTED,1)})
        elif self.path == "/":
            self._send(200, {"service": "jar181-canary", "version": VERSION, "sha": SHA})
        else:
            self._send(404, {"error": "not_found"})
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
