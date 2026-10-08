"""
Main CLI: Run ant colony simulation in serial or hybrid mode

Usage:
    python main.py --mode serial --iterations 1000
    python main.py --mode hybrid --iterations 1000 --dashboard
    python main.py --mode hybrid --iterations 1000 --processes 4 --threads 8
"""

import argparse
import sys
from pathlib import Path
import config
from src.simulation import Simulation
from src.parallel import HybridSimulation
from src.metrics import MetricsCollector
from src.io_tasks import IOTaskManager
from src.dashboard_server import DashboardServer
import time


def print_banner(mode: str, name: str, nim: int, threads: int, processes: int, ants: int, seed: int, iterations: int):
    """Print formatted banner with configuration"""
    print(f"{'='*60}")
    print(f"  ANT WORLD - HYBRID COMPUTING ({mode.upper()})")
    print(f"{'='*60}")
    print(f"  Student Name  : {name}")
    print(f"  NIM           : {nim}")
    print(f"  Threads (I/O) : {threads}")
    print(f"  Processes (CPU): {processes}")
    print(f"  Ants          : {ants}")
    print(f"  Seed          : {seed}")
    print(f"  Iterations    : {iterations}")
    print(f"{'='*60}")
    print()


def run_serial(args, baseline_for_hybrid: bool = False):
    """Run simulation in serial mode"""
    name = config.NAMA_MAHASISWA
    threads = args.threads or config.THREADS
    ants = args.ants or config.ANTS
    
    if not baseline_for_hybrid:
        print_banner("Serial", name, config.NIM, threads, 
                    config.PROCESSES, ants, config.SEED, args.iterations)
    
    # Initialize
    sim = Simulation(ants, config.SEED)
    metrics_collector = MetricsCollector()
    io_manager = IOTaskManager(threads)
    
    # Setup dashboard if requested
    dashboard = None
    if args.dashboard and not baseline_for_hybrid:
        dashboard = DashboardServer()
        dashboard.start()
    
    # Run simulation
    metrics_collector.start_timer()
    
    for i in range(args.iterations):
        sim.step()
        
        # Track completed paths from this iteration
        completed_paths = sim.get_and_clear_completed_paths()
        for path_length in completed_paths:
            metrics_collector.record_path(path_length)
        
        # Collect metrics
        if i % config.STATS_INTERVAL == 0 or i == 0:
            metrics = sim.get_metrics()
            metrics_collector.record_metrics(metrics)
            if not baseline_for_hybrid:
                print(f"Iteration {i:4d}: Food={metrics['food_collected']:3d}, "
                      f"Trips={metrics['total_trips']:3d}, "
                      f"AvgPheromone={metrics['avg_pheromone']:6.2f}")
        
        # Update dashboard via ThreadPool
        if dashboard and i % config.DASHBOARD_UPDATE_INTERVAL == 0:
            state = sim.get_state()
            elapsed = metrics_collector.get_execution_time()
            state['performance'] = {
                'execution_time_seconds': elapsed,
                'throughput': ants / elapsed if elapsed > 0 else 0.0,
                'speedup': None,
                'efficiency_percent': None,
                'threads': threads,
                'processes': 0,
            }
            io_manager.executor.submit(dashboard.update_state, state)
        
        # Save checkpoint via ThreadPool
        if args.checkpoint and i > 0 and i % args.checkpoint_interval == 0:
            checkpoint_dir = "results/checkpoints"
            Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
            checkpoint_path = f"{checkpoint_dir}/iteration_{i:05d}.json"
            checkpoint_state = sim.get_state()
            elapsed = metrics_collector.get_execution_time()
            checkpoint_state['performance'] = {
                'execution_time_seconds': elapsed,
                'throughput': ants / elapsed if elapsed > 0 else 0.0,
            }
            io_manager.save_checkpoint_async(checkpoint_state, checkpoint_path)
    
    metrics_collector.stop_timer()
    
    # Final results
    final_metrics = sim.get_metrics()
    execution_time = metrics_collector.get_execution_time()
    summary = metrics_collector.compute_summary(
        num_ants=ants,
        num_iterations=args.iterations
    )

    if dashboard:
        state = sim.get_state()
        state['performance'] = {
            'execution_time_seconds': execution_time,
            'throughput': ants / execution_time if execution_time > 0 else 0.0,
            'speedup': None,
            'efficiency_percent': None,
            'threads': threads,
            'processes': 0,
        }
        io_manager.executor.submit(dashboard.update_state, state).result()
    
    if not baseline_for_hybrid:
        print(f"\n{'='*60}")
        print(f"  PERFORMANCE RESULT")
        print(f"{'='*60}")
        print(f"  Execution Time    : {execution_time:.4f} seconds")
        print(f"  Throughput        : {summary.get('throughput', 0):.2f} ants/second")
        print(f"  Food Collected    : {final_metrics['food_collected']}")
        print(f"  Total Trips       : {final_metrics['total_trips']}")
        best_path = summary.get('best_path_length')
        avg_path = summary.get('avg_path_length')
        print(f"  Best Path Length  : {best_path if best_path is not None else 'N/A'}")
        if avg_path is not None:
            print(f"  Avg Path Length   : {avg_path:.2f}")
        else:
            print(f"  Avg Path Length   : N/A")
        print(f"{'='*60}")
    
    # Save final stats
    if args.output:
        summary['mode'] = 'serial'
        summary['final_metrics'] = final_metrics
        io_manager.write_stats_async(summary, args.output)
        if not baseline_for_hybrid:
            print(f"\nStats saved to {args.output}")
    
    # Cleanup
    io_manager.shutdown()
    if dashboard:
        input("\nPress Enter to stop dashboard...")
        dashboard.stop()
    
    return execution_time, summary


def run_hybrid(args):
    """Run simulation in hybrid mode (ProcessPool + ThreadPool)"""
    name = config.NAMA_MAHASISWA
    processes = args.processes or config.PROCESSES
    threads = args.threads or config.THREADS
    ants = args.ants or config.ANTS
    
    print_banner("Hybrid Parallel", name, config.NIM, threads, 
                processes, ants, config.SEED, args.iterations)
    
    # Measure serial baseline by default (identical workload)
    baseline_time = None
    if not args.no_baseline:
        print("Measuring serial baseline (same ants, iterations, threads)...")
        print("-" * 60)
        baseline_args = argparse.Namespace(
            ants=ants, iterations=args.iterations, dashboard=False,
            checkpoint=False, output=None, threads=threads,
            checkpoint_interval=args.checkpoint_interval
        )
        baseline_time, _ = run_serial(baseline_args, baseline_for_hybrid=True)
        print(f"Serial baseline: {baseline_time:.2f}s")
        print("-" * 60)
        print()
    
    # Initialize simulation and hybrid wrapper with persistent pool
    sim = Simulation(ants, config.SEED)
    hybrid_sim = HybridSimulation(sim, processes)
    metrics_collector = MetricsCollector()
    io_manager = IOTaskManager(threads)
    
    # Setup dashboard if requested
    dashboard = None
    if args.dashboard:
        dashboard = DashboardServer()
        dashboard.start()
    
    # Run simulation
    metrics_collector.start_timer()
    
    for i in range(args.iterations):
        hybrid_sim.step_parallel()
        
        # Track completed paths from this iteration
        completed_paths = sim.get_and_clear_completed_paths()
        for path_length in completed_paths:
            metrics_collector.record_path(path_length)
        
        # Collect metrics
        if i % config.STATS_INTERVAL == 0 or i == 0:
            metrics = sim.get_metrics()
            metrics_collector.record_metrics(metrics)
            print(f"Iteration {i:4d}: Food={metrics['food_collected']:3d}, "
                  f"Trips={metrics['total_trips']:3d}, "
                  f"AvgPheromone={metrics['avg_pheromone']:6.2f}")
        
        # Update dashboard via ThreadPool
        if dashboard and i % config.DASHBOARD_UPDATE_INTERVAL == 0:
            state = sim.get_state()
            elapsed = metrics_collector.get_execution_time()
            speedup = baseline_time / elapsed if baseline_time and elapsed > 0 else None
            state['performance'] = {
                'execution_time_seconds': elapsed,
                'throughput': ants / elapsed if elapsed > 0 else 0.0,
                'speedup': None,
                'efficiency_percent': None,
                'threads': threads,
                'processes': processes,
            }
            io_manager.executor.submit(dashboard.update_state, state)
        
        # Save checkpoint via ThreadPool
        if args.checkpoint and i > 0 and i % args.checkpoint_interval == 0:
            checkpoint_dir = "results/checkpoints"
            Path(checkpoint_dir).mkdir(parents=True, exist_ok=True)
            checkpoint_path = f"{checkpoint_dir}/iteration_{i:05d}_hybrid.json"
            checkpoint_state = sim.get_state()
            elapsed = metrics_collector.get_execution_time()
            checkpoint_state['performance'] = {
                'execution_time_seconds': elapsed,
                'throughput': ants / elapsed if elapsed > 0 else 0.0,
                'speedup': baseline_time / elapsed if baseline_time and elapsed > 0 else None,
                'efficiency_percent': (baseline_time / elapsed / processes * 100)
                    if baseline_time and elapsed > 0 else None,
            }
            io_manager.save_checkpoint_async(checkpoint_state, checkpoint_path)
    
    metrics_collector.stop_timer()
    
    # Cleanup persistent pool
    hybrid_sim.shutdown()
    
    # Final results
    final_metrics = sim.get_metrics()
    execution_time = metrics_collector.get_execution_time()
    summary = metrics_collector.compute_summary(
        num_ants=ants,
        num_iterations=args.iterations,
        baseline_time=baseline_time,
        num_processes=processes
    )

    if dashboard:
        state = sim.get_state()
        state['performance'] = {
            'execution_time_seconds': execution_time,
            'throughput': ants / execution_time if execution_time > 0 else 0.0,
            'speedup': summary.get('speedup'),
            'efficiency_percent': summary.get('efficiency_percent'),
            'threads': threads,
            'processes': processes,
        }
        io_manager.executor.submit(dashboard.update_state, state).result()
    
    print(f"\n{'='*60}")
    print(f"  PERFORMANCE RESULT")
    print(f"{'='*60}")
    print(f"  Execution Time    : {execution_time:.4f} seconds")
    print(f"  Throughput        : {summary.get('throughput', 0):.2f} ants/second")
    print(f"  Food Collected    : {final_metrics['food_collected']}")
    print(f"  Total Trips       : {final_metrics['total_trips']}")
    best_path = summary.get('best_path_length')
    avg_path = summary.get('avg_path_length')
    print(f"  Best Path Length  : {best_path if best_path is not None else 'N/A'}")
    if avg_path is not None:
        print(f"  Avg Path Length   : {avg_path:.2f}")
    else:
        print(f"  Avg Path Length   : N/A")
    
    if baseline_time:
        speedup = summary.get('speedup', 0)
        efficiency = summary.get('efficiency_percent', 0)
        print(f"  Speedup           : {speedup:.4f}x (T_serial / T_parallel)")
        print(f"  Efficiency        : {efficiency:.2f}% (speedup / {processes} * 100%)")
        print(f"  Baseline measured : {baseline_time:.4f}s (serial, same workload)")
    else:
        print(f"  Speedup           : Not measured (use default or omit --no-baseline)")
    
    print(f"{'='*60}")
    
    # Save final stats
    if args.output:
        summary['mode'] = 'hybrid'
        summary['num_processes'] = processes
        summary['num_threads'] = threads
        summary['final_metrics'] = final_metrics
        if baseline_time:
            summary['baseline_time_seconds'] = baseline_time
        io_manager.write_stats_async(summary, args.output)
        print(f"\nStats saved to {args.output}")
    
    # Cleanup
    io_manager.shutdown()
    if dashboard:
        input("\nPress Enter to stop dashboard...")
        dashboard.stop()
    
    return execution_time, summary


def main():
    parser = argparse.ArgumentParser(description='Ant Colony Simulation')
    parser.add_argument('--mode', choices=['serial', 'hybrid'], default='serial',
                       help='Execution mode')
    parser.add_argument('--iterations', type=int, default=1000,
                       help='Number of iterations')
    parser.add_argument('--ants', type=int, default=None,
                       help=f'Number of ants (default: {config.ANTS})')
    parser.add_argument('--processes', type=int, default=None,
                       help=f'Number of processes for hybrid mode (default: {config.PROCESSES})')
    parser.add_argument('--threads', type=int, default=None,
                       help=f'Number of I/O threads (default: {config.THREADS})')
    parser.add_argument('--dashboard', action='store_true',
                       help='Enable dashboard server')
    parser.add_argument('--checkpoint', action='store_true',
                       help='Enable checkpointing')
    parser.add_argument('--checkpoint-interval', type=int, default=config.CHECKPOINT_INTERVAL,
                       help=f'Checkpoint interval (default: {config.CHECKPOINT_INTERVAL})')
    parser.add_argument('--no-baseline', action='store_true',
                       help='Skip baseline measurement in hybrid mode (not recommended)')
    parser.add_argument('--output', type=str, default='results/run_stats.json',
                       help='Output stats file')
    
    args = parser.parse_args()
    
    # Create results directory
    Path('results').mkdir(exist_ok=True)
    
    if args.mode == 'serial':
        run_serial(args)
    elif args.mode == 'hybrid':
        run_hybrid(args)


if __name__ == '__main__':
    main()
