"""Local HTTP server for the Ant World dashboard and control API."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import Dict, Optional

import config


class DashboardState:
    """Thread-safe shared simulation state and one-shot start request."""

    def __init__(self):
        self.current_state: Optional[Dict] = None
        self.lock = threading.Lock()
        self.start_requested = threading.Event()

    def update(self, state: Dict) -> None:
        with self.lock:
            self.current_state = state

    def get(self) -> Optional[Dict]:
        with self.lock:
            return self.current_state

    def request_start(self) -> bool:
        with self.lock:
            if not self.current_state or self.current_state.get('status') != 'ready':
                return False
            self.current_state['status'] = 'starting'
            self.start_requested.set()
            return True


dashboard_state = DashboardState()


class DashboardHandler(SimpleHTTPRequestHandler):
    """Serve dashboard assets and its local REST endpoints."""

    def _send_json(self, status: int, payload: Dict) -> None:
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/state':
            state = dashboard_state.get()
            self._send_json(200, state or {
                'status': 'starting', 'message': 'Menunggu state simulasi'
            })
            return

        if self.path in ('/', '/index.html'):
            self._serve_file(Path('dashboard/index.html'), 'text/html; charset=utf-8')
            return

        if self.path.startswith('/dashboard/'):
            filepath = Path(self.path.lstrip('/'))
            content_types = {
                '.html': 'text/html; charset=utf-8',
                '.css': 'text/css; charset=utf-8',
                '.js': 'application/javascript; charset=utf-8',
                '.json': 'application/json; charset=utf-8',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
            }
            self._serve_file(filepath, content_types.get(filepath.suffix.lower(), 'application/octet-stream'))
            return

        if self.path == '/api/benchmark':
            self._serve_file(Path('results/benchmark_results.csv'), 'text/csv; charset=utf-8')
            return

        self.send_error(404)

    def do_POST(self):
        if self.path != '/api/control/start':
            self.send_error(404)
            return
        accepted = dashboard_state.request_start()
        self._send_json(202 if accepted else 409, {
            'accepted': accepted,
            'message': 'Simulasi dimulai' if accepted else 'Simulasi tidak sedang menunggu START',
        })

    def _serve_file(self, filepath: Path, content_type: str) -> None:
        if not filepath.exists() or not filepath.is_file():
            self.send_error(404)
            return
        body = filepath.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


class DashboardServer:
    """Manage dashboard HTTP server in a background thread."""

    def __init__(self, host: str | None = None, port: int | None = None):
        self.host = host or config.DASHBOARD_HOST
        self.port = port or config.DASHBOARD_PORT
        self.server: Optional[ThreadingHTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False

    def start(self):
        if self.running:
            return
        self.server = ThreadingHTTPServer((self.host, self.port), DashboardHandler)
        self.running = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"Dashboard server started at http://{self.host}:{self.port}")
        print(f"API endpoint: http://{self.host}:{self.port}/api/state")

    def stop(self):
        if self.server and self.running:
            self.running = False
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=2)

    def update_state(self, state: Dict):
        dashboard_state.update(state)

    def wait_for_start(self, timeout: float | None = None) -> bool:
        return dashboard_state.start_requested.wait(timeout)

    def clear_start_request(self) -> None:
        dashboard_state.start_requested.clear()


def update_dashboard(state: Dict):
    dashboard_state.update(state)
