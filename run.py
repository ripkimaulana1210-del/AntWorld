"""Single-command launcher for the Ant World hybrid demo."""

import argparse
from datetime import datetime
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

import config
from src.dashboard_server import DashboardServer
from src.io_tasks import IOTaskManager
from src.metrics import MetricsCollector
from src.parallel import HybridSimulation
from src.simulation import Simulation


def _run_serial_baseline(ants: int, iterations: int) -> float:
    simulation = Simulation(ants, config.SEED)
    started = time.perf_counter()
    for _ in range(iterations):
        simulation.step()
    return time.perf_counter() - started


def run_demo(iterations: int, open_browser: bool = True) -> None:
    ants = config.ANTS
    threads = config.THREADS
    processes = config.PROCESSES
    bind_host = config.DASHBOARD_HOST
    port = config.DASHBOARD_PORT
    display_host = "localhost" if bind_host in ("0.0.0.0", "") else bind_host
    url = f"http://{display_host}:{port}"
    dashboard = DashboardServer(host=bind_host, port=port)
    io_manager = IOTaskManager(threads)
    hybrid = None

    print("=" * 46)
    print("       ANT WORLD - HYBRID COMPUTING")
    print("=" * 46)
    print(f"Name       : {config.NAMA_MAHASISWA}")
    print(f"NIM        : {config.NIM}")
    print(f"Threads    : {threads}")
    print(f"Processes  : {processes}")
    print(f"Ants       : {ants}")
    print(f"Seed       : {config.SEED}")
    print("Mode       : HYBRID")
    print(f"Host       : {bind_host}")
    print(f"Port       : {port}")
    print(f"Dashboard  : {url}")
    print("Status     : READY - menunggu START dari dashboard")
    print("=" * 46)

    try:
        # Serve the dashboard before expensive initialization/baseline work.
        try:
            dashboard.start()
        except OSError as error:
            if getattr(error, 'winerror', None) == 10048 or 'address already in use' in str(error).lower():
                raise RuntimeError(
                    f"Port {port} sedang digunakan. Tutup server ANT WORLD "
                    f"yang lama, atau gunakan PORT lain: set PORT=xxxx"
                ) from error
            raise
        simulation = Simulation(ants, config.SEED)
        simulation.total_iterations = iterations
        initial = simulation.get_state()
        initial['performance'] = {
            'execution_time_seconds': 0.0,
            'throughput': 0.0,
            'speedup': None,
            'efficiency_percent': None,
            'threads': threads,
            'processes': processes,
            'started_at': None,
            'iteration_time_seconds': None,
        }
        initial['status'] = 'ready'
        dashboard.update_state(initial)
        if open_browser:
            try:
                webbrowser.open(url)
            except Exception:
                pass

        print("Dashboard siap. Tekan tombol START pada HUD untuk memulai simulasi.")
        while not dashboard.wait_for_start(timeout=0.25):
            pass
        dashboard.clear_start_request()
        print("START diterima dari HUD.")

        print("Measuring serial baseline for runtime speedup...")
        serial_time = _run_serial_baseline(ants, iterations)
        simulation = Simulation(ants, config.SEED)
        simulation.total_iterations = iterations
        hybrid = HybridSimulation(simulation, processes)

        timer = MetricsCollector()
        timer.start_timer()
        started_at = datetime.now().astimezone().isoformat(timespec='seconds')
        active_state = simulation.get_state()
        active_state['status'] = 'running'
        active_state['performance'] = {
            'execution_time_seconds': 0.0,
            'throughput': 0.0,
            'speedup': None,
            'efficiency_percent': None,
            'threads': threads,
            'processes': processes,
            'started_at': started_at,
            'iteration_time_seconds': None,
        }
        io_manager.executor.submit(dashboard.update_state, active_state).result()
        last_progress = time.perf_counter()
        last_step_duration = None
        for index in range(iterations):
            step_started = time.perf_counter()
            hybrid.step_parallel()
            last_step_duration = time.perf_counter() - step_started
            elapsed = timer.get_execution_time()
            serial_elapsed_per_iteration = serial_time / iterations if iterations else 0.0
            hybrid_elapsed_per_iteration = elapsed / (index + 1)
            speedup = (serial_elapsed_per_iteration / hybrid_elapsed_per_iteration
                       if hybrid_elapsed_per_iteration > 0 else None)
            state = simulation.get_state()
            state['performance'] = {
                'execution_time_seconds': elapsed,
                'throughput': ants / elapsed if elapsed > 0 else 0.0,
                'speedup': speedup,
                'efficiency_percent': speedup / processes * 100 if speedup is not None else None,
                'threads': threads,
                'processes': processes,
                'started_at': started_at,
                'iteration_time_seconds': last_step_duration,
            }
            state['status'] = 'running'

            if index % config.DASHBOARD_UPDATE_INTERVAL == 0 or index == iterations - 1:
                # Wait for the I/O task so the submitted state is safely consumed before next mutation.
                io_manager.executor.submit(dashboard.update_state, state).result()
            if index > 0 and index % config.CHECKPOINT_INTERVAL == 0:
                io_manager.save_checkpoint_async(
                    state, f"results/checkpoints/iteration_{index:05d}_hybrid.json")

            now = time.perf_counter()
            if now - last_progress >= 1.0 or index == iterations - 1:
                print(f"Iteration {index + 1}/{iterations} | "
                      f"Food: {state['metrics']['food_collected']} | "
                      f"Elapsed: {elapsed:.1f}s")
                last_progress = now

        timer.stop_timer()
        elapsed = timer.get_execution_time()
        speedup = serial_time / elapsed if elapsed > 0 else 0.0
        summary = {
            'mode': 'hybrid',
            'num_threads': threads,
            'num_processes': processes,
            'num_ants': ants,
            'total_iterations': simulation.iteration,
            'execution_time_seconds': elapsed,
            'baseline_time_seconds': serial_time,
            'throughput': ants / elapsed if elapsed > 0 else 0.0,
            'speedup': speedup,
            'efficiency_percent': speedup / processes * 100,
            'final_metrics': simulation.get_metrics(),
        }
        state = simulation.get_state()
        state['performance'] = {
            'execution_time_seconds': elapsed,
            'throughput': summary['throughput'],
            'speedup': speedup,
            'efficiency_percent': summary['efficiency_percent'],
            'threads': threads,
            'processes': processes,
            'started_at': started_at,
            'completed_at': datetime.now().astimezone().isoformat(timespec='seconds'),
            'iteration_time_seconds': last_step_duration,
        }
        state['status'] = 'completed'
        io_manager.executor.submit(dashboard.update_state, state).result()
        io_manager.write_stats_async(summary, 'results/run_stats.json').result()

        print(f"Complete | Time: {elapsed:.2f}s | Throughput: {summary['throughput']:.2f} ants/s | "
              f"Speedup: {speedup:.3f}x | Efficiency: {summary['efficiency_percent']:.2f}%")
        print("Dashboard tetap aktif. Tekan Ctrl+C untuk menutup semua komponen.")
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nMenghentikan simulasi dan layanan dengan aman...")
    except RuntimeError as error:
        print(f"\nTidak dapat memulai dashboard: {error}")
    finally:
        if hybrid is not None:
            hybrid.shutdown()
        io_manager.shutdown(wait=True)
        dashboard.stop()
        print("ANT WORLD berhenti.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Jalankan demo ANT WORLD hybrid")
    parser.add_argument('--iterations', type=int, default=config.MAX_ITERATIONS,
                        help=f"Jumlah iterasi (default: {config.MAX_ITERATIONS})")
    parser.add_argument('--no-browser', action='store_true', help='Jangan membuka browser otomatis')
    args = parser.parse_args()
    Path('results/checkpoints').mkdir(parents=True, exist_ok=True)

    # Deteksi lingkungan headless / cloud (misal Railway atau Linux container)
    is_headless = bool(
        args.no_browser or
        os.environ.get('RAILWAY_ENVIRONMENT') or
        os.environ.get('RAILWAY_SERVICE_ID') or
        (not sys.platform.startswith('win') and not os.environ.get('DISPLAY'))
    )
    run_demo(args.iterations, open_browser=not is_headless)


if __name__ == '__main__':
    main()
