"""
Benchmark script: Compare serial vs hybrid with thread/process/data variation

Workload: ants * iterations (total ant-steps simulated)
Throughput: ants / execution_time (semut per detik)

Usage:
    python benchmark.py  # Default 4 configs varying threads/processes/data
"""

import argparse
from collections import defaultdict
from datetime import datetime
from itertools import product
from pathlib import Path
import config
from src.simulation import Simulation
from src.parallel import HybridSimulation
from src.metrics import MetricsCollector
from src.io_tasks import IOTaskManager


def benchmark_config(config_num: int, threads: int, processes: int, ants: int, 
                    iterations: int, seed: int) -> tuple:
    """
    Benchmark a single configuration: serial baseline + hybrid.
    Returns (serial_result, hybrid_result) with measured data.
    """
    print(f"\n[Configuration {config_num}]")
    print(f"  Threads={threads}, Processes={processes}, Ants={ants}, Iterations={iterations}")
    print("-" * 70)
    
    # Run serial baseline
    print(f"  Running serial baseline...")
    sim_serial = Simulation(ants, seed)
    metrics_serial = MetricsCollector()
    io_serial = IOTaskManager(threads)
    
    metrics_serial.start_timer()
    for i in range(iterations):
        sim_serial.step()
        
        # Track completed paths
        completed_paths = sim_serial.get_and_clear_completed_paths()
        for path_length in completed_paths:
            metrics_serial.record_path(path_length)
        
        if i % 50 == 0:
            m = sim_serial.get_metrics()
            metrics_serial.record_metrics(m)
            io_serial.write_dashboard_snapshot_async(
                m, f'results/benchmark_io/serial_{config_num}_{i:05d}.json')
    metrics_serial.stop_timer()
    io_serial.shutdown()
    
    serial_time = metrics_serial.get_execution_time()
    serial_metrics = sim_serial.get_metrics()
    serial_summary = metrics_serial.compute_summary(ants, iterations)
    
    print(f"  Serial: {serial_time:.6f}s, Food={serial_metrics['food_collected']}")
    
    # Run hybrid
    print(f"  Running hybrid...")
    sim_hybrid = Simulation(ants, seed)
    hybrid_sim = HybridSimulation(sim_hybrid, processes)
    metrics_hybrid = MetricsCollector()
    io_hybrid = IOTaskManager(threads)
    
    metrics_hybrid.start_timer()
    for i in range(iterations):
        hybrid_sim.step_parallel()
        
        # Track completed paths
        completed_paths = sim_hybrid.get_and_clear_completed_paths()
        for path_length in completed_paths:
            metrics_hybrid.record_path(path_length)
        
        if i % 50 == 0:
            m = sim_hybrid.get_metrics()
            metrics_hybrid.record_metrics(m)
            io_hybrid.write_dashboard_snapshot_async(
                m, f'results/benchmark_io/hybrid_{config_num}_{i:05d}.json')
    metrics_hybrid.stop_timer()
    
    hybrid_sim.shutdown()
    io_hybrid.shutdown()
    
    hybrid_time = metrics_hybrid.get_execution_time()
    hybrid_metrics = sim_hybrid.get_metrics()
    hybrid_summary = metrics_hybrid.compute_summary(ants, iterations, serial_time, processes)
    
    speedup = serial_time / hybrid_time if hybrid_time > 0 else 0
    efficiency = (speedup / processes) * 100 if processes > 0 else 0
    
    print(f"  Hybrid: {hybrid_time:.6f}s, Food={hybrid_metrics['food_collected']}")
    print(f"  Speedup: {speedup:.4f}x, Efficiency: {efficiency:.2f}%")
    
    # Verify determinism
    if serial_metrics['food_collected'] == hybrid_metrics['food_collected']:
        print(f"  [OK] Determinism verified")
    else:
        print(f"  [WARNING] Determinism mismatch!")
    
    serial_result = {
        'No': config_num,
        'Threads': threads,
        'Processes': 1,
        'Data': ants,
        'Time': serial_time,
        'Speedup': 1.0,
        'Efficiency': 100.0,
        'Throughput': serial_summary.get('throughput', 0),
        'FoodCollected': serial_metrics['food_collected'],
        'AveragePath': serial_summary.get('avg_path_length', '')
    }
    
    hybrid_result = {
        'No': config_num,
        'Threads': threads,
        'Processes': processes,
        'Data': ants,
        'Time': hybrid_time,
        'Speedup': speedup,
        'Efficiency': efficiency,
        'Throughput': hybrid_summary.get('throughput', 0),
        'FoodCollected': hybrid_metrics['food_collected'],
        'AveragePath': hybrid_summary.get('avg_path_length', '')
    }
    
    return serial_result, hybrid_result


def _build_configurations(threads, processes, ants, iterations):
    return [
        {'threads': thread_count, 'processes': process_count, 'ants': ant_count,
         'iterations': iterations}
        for thread_count, process_count, ant_count in product(threads, processes, ants)
    ]


def run_benchmark(configurations=None):
    """Run benchmark configurations with a serial baseline per workload."""
    run_id = datetime.now().astimezone().strftime('%Y%m%d-%H%M%S-%f')
    print("=" * 70)
    print(f"  ANT COLONY SIMULATION BENCHMARK - {config.NAMA_MAHASISWA}")
    print("=" * 70)
    print(f"  NIM: {config.NIM}, Seed: {config.SEED}, Run ID: {run_id}")
    print(f"  Workload: ants * iterations (total ant-steps)")
    print(f"  Throughput: ants / execution_time (ants/second)")
    print("=" * 70)
    
    if configurations is None:
        configurations = _build_configurations((3, 5, 7), (2, 3), (500, 1000, config.ANTS), 100)
    
    all_results = []
    
    for i, cfg in enumerate(configurations, 1):
        serial_res, hybrid_res = benchmark_config(
            config_num=i,
            threads=cfg['threads'],
            processes=cfg['processes'],
            ants=cfg['ants'],
            iterations=cfg['iterations'],
            seed=config.SEED
        )
        for result in (serial_res, hybrid_res):
            result.update({
                'Iterations': cfg['iterations'],
                'Seed': config.SEED,
                'Run ID': run_id,
            })
        all_results.append(serial_res)
        all_results.append(hybrid_res)
    
    # Keep run and workload metadata beside every measurement for reproducibility.
    io_manager = IOTaskManager()
    csv_headers = ['Threads', 'Processes', 'Data', 'Time', 'Speedup',
                   'Efficiency', 'Throughput', 'Iterations', 'Seed', 'Run ID']
    csv_data = []
    
    for result in all_results:
        row = [
            result['Threads'],
            result['Processes'],
            result['Data'],
            f"{result['Time']:.8f}",
            f"{result['Speedup']:.4f}",
            f"{result['Efficiency']:.2f}",
            f"{result['Throughput']:.2f}",
            result['Iterations'],
            result['Seed'],
            result['Run ID'],
        ]
        csv_data.append(row)
    
    output_path = 'results/benchmark_results.csv'
    io_manager.write_csv_async(csv_data, output_path, csv_headers).result()
    
    print(f"\n{'='*70}")
    print(f"  BENCHMARK COMPLETE")
    print(f"{'='*70}")
    print(f"  Results: {output_path}")
    print(f"  Run ID: {run_id}")
    
    io_manager.shutdown()
    
    return all_results


def _comparison_series(results: list, varying_field: str):
    """Return only hybrid measurements that can be compared pairwise."""
    fixed_fields = {
        'Threads': ('Processes', 'Data', 'Iterations', 'Seed', 'Run ID'),
        'Processes': ('Threads', 'Data', 'Iterations', 'Seed', 'Run ID'),
    }
    if varying_field not in fixed_fields:
        raise ValueError(f"Unsupported comparison field: {varying_field}")

    grouped = defaultdict(lambda: defaultdict(list))
    for result in results:
        if result['Processes'] <= 1:
            continue
        key = tuple(result[field] for field in fixed_fields[varying_field])
        grouped[key][result[varying_field]].append(result['Time'])

    return [
        (key, {
            value: sum(times) / len(times)
            for value, times in sorted(values.items())
        })
        for key, values in sorted(grouped.items())
        if len(values) > 1
    ]


def generate_charts(results: list, run_id: str | None = None):
    """Generate three required charts"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available, skipping charts")
        return
    
    # Separate hybrid results only (for charts)
    hybrid_results = [r for r in results if r['Processes'] > 1]
    run_id = run_id or (results[0].get('Run ID', 'untracked') if results else 'untracked')
    
    # Chart 1: compare threads only within identical process/data/workload groups.
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    thread_groups = _comparison_series(hybrid_results, 'Threads')
    for key, values in thread_groups:
        processes, ants, iterations = key[:3]
        ax1.plot(
            list(values), list(values.values()), marker='o', linewidth=2, markersize=6,
            label=f'P={processes}, ants={ants}, iter={iterations}',
        )
    ax1.set_xlabel('Number of Threads (I/O Workers)', fontsize=12)
    ax1.set_ylabel('Execution Time (seconds)', fontsize=12)
    ax1.set_title(f'Execution Time vs Thread Count\nNIM: {config.NIM} | Run: {run_id}', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    if thread_groups:
        ax1.legend(fontsize=7, ncol=2)
    else:
        ax1.text(0.5, 0.5, 'No matched configurations to compare',
                 ha='center', va='center', transform=ax1.transAxes)
    plt.tight_layout()
    plt.savefig('results/time_vs_threads.png', dpi=150)
    plt.close()
    print(f"  Chart 1: results/time_vs_threads.png")
    
    # Chart 2: compare processes only within identical thread/data/workload groups.
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    process_groups = _comparison_series(hybrid_results, 'Processes')
    for key, values in process_groups:
        threads, ants, iterations = key[:3]
        ax2.plot(
            list(values), list(values.values()), marker='s', linewidth=2, markersize=6,
            label=f'T={threads}, ants={ants}, iter={iterations}',
        )
    ax2.set_xlabel('Number of Processes (CPU Workers)', fontsize=12)
    ax2.set_ylabel('Execution Time (seconds)', fontsize=12)
    ax2.set_title(f'Execution Time vs Process Count\nNIM: {config.NIM} | Run: {run_id}', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    if process_groups:
        ax2.legend(fontsize=7, ncol=2)
    else:
        ax2.text(0.5, 0.5, 'No matched configurations to compare',
                 ha='center', va='center', transform=ax2.transAxes)
    plt.tight_layout()
    plt.savefig('results/time_vs_processes.png', dpi=150)
    plt.close()
    print(f"  Chart 2: results/time_vs_processes.png")
    
    # Chart 3: Speedup vs Configuration
    fig3, ax3 = plt.subplots(figsize=(14, 7))
    config_labels = [
        f"T{r['Threads']}P{r['Processes']}D{r['Data']}I{r['Iterations']}"
        for r in hybrid_results
    ]
    speedups = [r['Speedup'] for r in hybrid_results]
    efficiencies = [r['Efficiency'] for r in hybrid_results]
    
    x = range(len(config_labels))
    width = 0.35
    
    ax3.bar([i - width/2 for i in x], speedups, width, label='Speedup', color='green', alpha=0.7)
    ax3_twin = ax3.twinx()
    ax3_twin.bar([i + width/2 for i in x], efficiencies, width, label='Efficiency %', color='orange', alpha=0.7)
    
    ax3.set_xlabel('Configuration', fontsize=12)
    ax3.set_ylabel('Speedup (T_serial / T_parallel)', fontsize=12, color='green')
    ax3_twin.set_ylabel('Efficiency (%)', fontsize=12, color='orange')
    ax3.set_title(f'Speedup and Efficiency vs Configuration\nNIM: {config.NIM} | Run: {run_id}', fontsize=14, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(config_labels, rotation=45, ha='right', fontsize=8)
    ax3.tick_params(axis='y', labelcolor='green')
    ax3_twin.tick_params(axis='y', labelcolor='orange')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.legend(loc='upper left')
    ax3_twin.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig('results/speedup_vs_configuration.png', dpi=150)
    plt.close()
    print(f"  Chart 3: results/speedup_vs_configuration.png")


def main():
    parser = argparse.ArgumentParser(description='Benchmark ant colony simulation')
    parser.add_argument('--no-charts', action='store_true',
                       help='Skip chart generation')
    parser.add_argument('--threads', type=int, nargs='+', default=[3, 5, 7],
                       help='I/O thread counts to benchmark')
    parser.add_argument('--processes', type=int, nargs='+', default=[2, 3],
                       help='CPU process counts to benchmark')
    parser.add_argument('--ants', type=int, nargs='+', default=[500, 1000, config.ANTS],
                       help='Ant counts to benchmark')
    parser.add_argument('--iterations', type=int, default=100,
                       help='Iterations per benchmark run')
    
    args = parser.parse_args()
    
    # Create results directory
    Path('results').mkdir(exist_ok=True)
    
    # Sweep every requested parameter combination so each comparison has a matched partner.
    configurations = _build_configurations(args.threads, args.processes, args.ants, args.iterations)
    results = run_benchmark(configurations)
    
    # Generate charts
    if not args.no_charts:
        generate_charts(results, results[0]['Run ID'] if results else None)


if __name__ == '__main__':
    main()
