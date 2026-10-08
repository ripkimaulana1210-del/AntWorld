"""
I/O Tasks module: Asynchronous I/O operations using ThreadPoolExecutor
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
import json
import pickle
import os
import time
from pathlib import Path
import config


class IOTaskManager:
    """Manages I/O operations using thread pool for non-blocking execution"""
    
    def __init__(self, num_threads: int | None = None):
        self.num_threads = num_threads or config.THREADS
        self.executor = ThreadPoolExecutor(max_workers=self.num_threads)
    
    def save_checkpoint_async(self, state: Dict, filepath: str):
        """Save simulation checkpoint asynchronously"""
        return self.executor.submit(self._save_checkpoint, state, filepath)
    
    def _save_checkpoint(self, state: Dict, filepath: str):
        """Internal checkpoint save function"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Create checkpoint with required fields
        checkpoint = {
            'iteration': state.get('iteration', 0),
            'timestamp': time.time(),
            'food_collected': state['metrics']['food_collected'],
            'avg_pheromone': state['metrics']['avg_pheromone'],
            'ants_with_food': state['metrics']['ants_with_food'],
            'ants_count': len(state['ants']),
            'execution_statistics': state.get('performance', {}),
            'world_summary': {
                'food_remaining': state['metrics']['food_remaining'],
                'pheromone_max': state['metrics']['max_pheromone']
            }
        }
        
        # Calculate average path length from ants with food
        paths = [ant['path_length'] for ant in state['ants'] if ant.get('path_length', 0) > 0]
        if paths:
            checkpoint['avg_path_length'] = sum(paths) / len(paths)
        else:
            checkpoint['avg_path_length'] = 0
        
        # Save as JSON (human-readable)
        with open(filepath, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        
        return filepath
    
    def load_checkpoint_async(self, filepath: str):
        """Load simulation checkpoint asynchronously"""
        return self.executor.submit(self._load_checkpoint, filepath)
    
    def _load_checkpoint(self, filepath: str) -> Dict:
        """Internal checkpoint load function"""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def write_stats_async(self, stats: Dict, filepath: str):
        """Write statistics to JSON file asynchronously"""
        return self.executor.submit(self._write_stats, stats, filepath)
    
    def _write_stats(self, stats: Dict, filepath: str):
        """Internal stats write function"""
        parent = os.path.dirname(filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)
        return filepath
    
    def read_world_data_async(self, filepath: str):
        """Read world data asynchronously"""
        return self.executor.submit(self._read_world_data, filepath)
    
    def _read_world_data(self, filepath: str) -> Dict:
        """Internal world data read function"""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def write_dashboard_snapshot_async(self, snapshot: Dict, filepath: str):
        """Write dashboard snapshot asynchronously"""
        return self.executor.submit(self._write_dashboard_snapshot, snapshot, filepath)
    
    def _write_dashboard_snapshot(self, snapshot: Dict, filepath: str):
        """Internal dashboard snapshot write function"""
        parent = os.path.dirname(filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(snapshot, f)
        return filepath
    
    def write_csv_async(self, data: list, filepath: str, headers: list | None = None):
        """Write CSV data asynchronously"""
        return self.executor.submit(self._write_csv, data, filepath, headers)
    
    def _write_csv(self, data: list, filepath: str, headers: list | None = None):
        """Internal CSV write function"""
        import csv
        parent = os.path.dirname(filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            if headers:
                writer.writerow(headers)
            writer.writerows(data)
        return filepath
    
    def shutdown(self, wait: bool = True):
        """Shutdown thread pool executor"""
        self.executor.shutdown(wait=wait)
