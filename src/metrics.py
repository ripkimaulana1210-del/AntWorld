"""
Metrics module: Performance and simulation metrics collection

Throughput definition: ants / execution_time (per project specification)
"""

import time
from typing import Dict, List
import numpy as np
import config


class MetricsCollector:
    """
    Collects and computes simulation metrics.
    
    Metrics tracked:
    - food_collected: Total food items collected
    - total_trips: Number of successful foraging trips
    - avg_pheromone: Average pheromone level across grid
    - best_path_length: Shortest successful path to food
    - avg_path_length: Average path length for successful trips
    
    Performance metrics:
    - execution_time: Wall clock time
    - throughput: ants / execution_time
    - speedup: T_serial / T_parallel (requires baseline)
    - efficiency: (speedup / num_processes) * 100%
    """
    
    def __init__(self):
        self.metrics_history: List[Dict] = []
        self.start_time = None
        self.end_time = None
        self.best_path_length = float('inf')
        self.total_path_length = 0
        self.path_count = 0
    
    def start_timer(self):
        """Start timing execution"""
        self.start_time = time.time()
    
    def stop_timer(self):
        """Stop timing execution"""
        self.end_time = time.time()
    
    def record_metrics(self, metrics: Dict):
        """Record snapshot of simulation metrics"""
        timestamped = metrics.copy()
        timestamped['timestamp'] = time.time()
        self.metrics_history.append(timestamped)
    
    def record_path(self, path_length: int):
        """Record a successful path"""
        if path_length > 0:
            self.best_path_length = min(self.best_path_length, path_length)
            self.total_path_length += path_length
            self.path_count += 1
    
    def get_execution_time(self) -> float:
        """Get total execution time in seconds"""
        if self.start_time:
            return (self.end_time or time.time()) - self.start_time
        return 0.0
    
    def compute_summary(self, num_ants: int | None = None, 
                       num_iterations: int | None = None,
                       baseline_time: float | None = None,
                       num_processes: int | None = None) -> Dict:
        """
        Compute summary statistics from collected metrics.
        
        Args:
            num_ants: Number of ants in simulation
            num_iterations: Total iterations run
            baseline_time: Serial baseline time for speedup calculation
            num_processes: Number of processes (for efficiency calculation)
        """
        food_collected = [m.get('food_collected', 0) for m in self.metrics_history]
        iterations = [m.get('iteration', 0) for m in self.metrics_history]
        avg_pheromones = [m.get('avg_pheromone', 0) for m in self.metrics_history]
        
        execution_time = self.get_execution_time()
        total_iterations = num_iterations or (iterations[-1] if iterations else 0)
        
        summary = {
            'total_food_collected': food_collected[-1] if food_collected else 0,
            'total_iterations': total_iterations,
            'execution_time_seconds': execution_time,
            'final_avg_pheromone': avg_pheromones[-1] if avg_pheromones else 0,
        }
        
        # Throughput is the number of ants processed per second.
        if num_ants and execution_time > 0:
            summary['throughput'] = num_ants / execution_time
        else:
            summary['throughput'] = 0.0
        
        # Path metrics
        if self.path_count > 0:
            summary['best_path_length'] = self.best_path_length
            summary['avg_path_length'] = self.total_path_length / self.path_count
        else:
            summary['best_path_length'] = None
            summary['avg_path_length'] = None
        
        # Speedup and efficiency (only if baseline provided)
        if baseline_time is not None and baseline_time > 0 and execution_time > 0:
            speedup = baseline_time / execution_time
            summary['speedup'] = speedup
            if num_processes:
                summary['efficiency_percent'] = (speedup / num_processes) * 100
        
        return summary
