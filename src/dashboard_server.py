"""Local HTTP server for the Ant World dashboard and control API."""

from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import config

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DashboardState:
    """Thread-safe shared simulation state and control request manager."""

    def __init__(self):
        self.current_state: Optional[Dict] = None
        self.lock = threading.Lock()
        self.start_requested = threading.Event()
        self.pause_requested = threading.Event()
        self.resume_requested = threading.Event()
        self.restart_requested = threading.Event()
        self.activities: List[Dict] = []
        self._activity_counter = 0

    def add_activity(self, message: str, event_type: str = 'info') -> None:
        with self.lock:
            self._activity_counter += 1
            now = datetime.now().strftime("%H:%M:%S")
            self.activities.append({
                'id': self._activity_counter,
                'time': now,
                'message': message,
                'type': event_type,
            })
            if len(self.activities) > 12:
                self.activities.pop(0)

    def update(self, state: Dict) -> None:
        with self.lock:
            state_copy = dict(state)
            state_copy['activities'] = list(self.activities)
            self.current_state = state_copy

    def get(self) -> Optional[Dict]:
        with self.lock:
            if self.current_state is not None:
                self.current_state['activities'] = list(self.activities)
            return self.current_state

    def get_status(self) -> str:
        with self.lock:
            if not self.current_state:
                return 'starting'
            return self.current_state.get('status', 'starting')

    def set_status(self, status: str) -> None:
        with self.lock:
            if self.current_state is not None:
                self.current_state['status'] = status

    def request_start(self) -> Tuple[bool, str]:
        with self.lock:
            status = self.current_state.get('status') if self.current_state else None
            if status != 'ready':
                return False, f"Simulasi tidak dalam status ready (status saat ini: {status})"
            if self.current_state is not None:
                self.current_state['status'] = 'starting'
            self.start_requested.set()
        self.add_activity("Simulation started (Hybrid mode)", "start")
        return True, "Simulasi dimulai"

    def request_pause(self) -> Tuple[bool, str]:
        with self.lock:
            status = self.current_state.get('status') if self.current_state else None
            if status != 'running':
                return False, f"Hanya simulasi yang sedang berjalan yang dapat dijeda (status: {status})"
            self.pause_requested.set()
            self.resume_requested.clear()
        return True, "Permintaan pause diterima"

    def request_resume(self) -> Tuple[bool, str]:
        with self.lock:
            status = self.current_state.get('status') if self.current_state else None
            if status != 'paused':
                return False, f"Hanya simulasi yang dijeda yang dapat dilanjutkan (status: {status})"
            self.resume_requested.set()
            self.pause_requested.clear()
        return True, "Permintaan resume diterima"

    def request_restart(self) -> Tuple[bool, str]:
        with self.lock:
            status = self.current_state.get('status') if self.current_state else None
            if status not in ('running', 'paused', 'completed', 'starting'):
                return False, f"Tidak dapat me-restart saat status {status}"
            if self.current_state is not None:
                self.current_state['status'] = 'restarting'
            self.restart_requested.set()
            # If paused or waiting for start, wake them up so restart can proceed
            self.resume_requested.set()
            self.start_requested.set()
        self.add_activity("Simulation restarted to initial conditions", "restart")
        return True, "Simulasi di-reset"


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
        clean_path = urlparse(self.path).path

        if clean_path == '/api/state':
            state = dashboard_state.get()
            self._send_json(200, state or {
                'status': 'starting', 'message': 'Menunggu state simulasi', 'activities': []
            })
            return

        if clean_path in ('/', '/index.html'):
            self._serve_file(PROJECT_ROOT / 'dashboard' / 'index.html', 'text/html; charset=utf-8')
            return

        if clean_path.startswith('/dashboard/'):
            filepath = PROJECT_ROOT / clean_path.lstrip('/')
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

        if clean_path == '/api/benchmark':
            self._serve_file(PROJECT_ROOT / 'results' / 'benchmark_results.csv', 'text/csv; charset=utf-8')
            return

        self.send_error(404)

    def do_POST(self):
        clean_path = urlparse(self.path).path

        if clean_path in ('/api/control/start', '/api/start'):
            accepted, msg = dashboard_state.request_start()
            self._send_json(202 if accepted else 409, {
                'accepted': accepted,
                'message': msg,
                'status': dashboard_state.get_status()
            })
            return

        if clean_path in ('/api/control/pause', '/api/pause'):
            accepted, msg = dashboard_state.request_pause()
            self._send_json(202 if accepted else 409, {
                'accepted': accepted,
                'message': msg,
                'status': dashboard_state.get_status()
            })
            return

        if clean_path in ('/api/control/resume', '/api/resume'):
            accepted, msg = dashboard_state.request_resume()
            self._send_json(202 if accepted else 409, {
                'accepted': accepted,
                'message': msg,
                'status': dashboard_state.get_status()
            })
            return

        if clean_path in ('/api/control/restart', '/api/restart'):
            accepted, msg = dashboard_state.request_restart()
            self._send_json(202 if accepted else 409, {
                'accepted': accepted,
                'message': msg,
                'status': dashboard_state.get_status()
            })
            return

        self.send_error(404)

    def _serve_file(self, filepath: Path, content_type: str) -> None:
        try:
            resolved = filepath.resolve()
            if not resolved.exists() or not resolved.is_file():
                self.send_error(404)
                return
            body = resolved.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            self.send_error(500)

    def log_message(self, format, *args):
        pass


class DashboardServer:
    """Manage dashboard HTTP server in a background thread."""

    def __init__(self, host: str | None = None, port: int | None = None):
        self.host = host if host is not None else config.DASHBOARD_HOST
        self.port = int(port) if port is not None else config.DASHBOARD_PORT
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

    def get_state(self) -> Optional[Dict]:
        return dashboard_state.get()

    def add_activity(self, message: str, event_type: str = 'info'):
        dashboard_state.add_activity(message, event_type)

    def wait_for_start(self, timeout: float | None = None) -> bool:
        return dashboard_state.start_requested.wait(timeout)

    def clear_start_request(self) -> None:
        dashboard_state.start_requested.clear()

    def is_pause_requested(self) -> bool:
        return dashboard_state.pause_requested.is_set()

    def clear_pause_request(self) -> None:
        dashboard_state.pause_requested.clear()

    def wait_for_resume_or_restart(self, timeout: float | None = None) -> Tuple[bool, bool]:
        """Wait until either resume or restart is signaled. Returns (resumed, restarted)."""
        deadline = time.time() + (timeout if timeout else 999999)
        while time.time() < deadline:
            if dashboard_state.restart_requested.is_set():
                return False, True
            if dashboard_state.resume_requested.is_set():
                dashboard_state.resume_requested.clear()
                return True, False
            time.sleep(0.05)
        return False, False

    def is_restart_requested(self) -> bool:
        return dashboard_state.restart_requested.is_set()

    def clear_restart_request(self) -> None:
        dashboard_state.restart_requested.clear()


def update_dashboard(state: Dict):
    dashboard_state.update(state)
