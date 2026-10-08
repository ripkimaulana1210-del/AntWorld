"""
Tests for I/O tasks module
"""

import unittest
import os
import json
import tempfile
from pathlib import Path
from src.io_tasks import IOTaskManager


class TestIOTasks(unittest.TestCase):
    
    def setUp(self):
        self.io_manager = IOTaskManager(num_threads=2)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        self.io_manager.shutdown()
        # Cleanup temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_write_stats_async(self):
        """Test asynchronous stats writing"""
        stats = {'iteration': 100, 'food_collected': 50}
        filepath = os.path.join(self.temp_dir, 'stats.json')
        
        future = self.io_manager.write_stats_async(stats, filepath)
        result = future.result()
        
        self.assertEqual(result, filepath)
        self.assertTrue(os.path.exists(filepath))
        
        # Verify content
        with open(filepath, 'r') as f:
            loaded = json.load(f)
        self.assertEqual(loaded['iteration'], 100)
    
    def test_write_csv_async(self):
        """Test asynchronous CSV writing"""
        data = [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9]
        ]
        headers = ['A', 'B', 'C']
        filepath = os.path.join(self.temp_dir, 'data.csv')
        
        future = self.io_manager.write_csv_async(data, filepath, headers)
        result = future.result()
        
        self.assertEqual(result, filepath)
        self.assertTrue(os.path.exists(filepath))
        
        # Verify content
        with open(filepath, 'r') as f:
            lines = f.readlines()
        self.assertIn('A,B,C', lines[0])
        self.assertEqual(len(lines), 4)  # header + 3 rows
    
    def test_write_dashboard_snapshot_async(self):
        """Test asynchronous dashboard snapshot writing"""
        snapshot = {
            'iteration': 50,
            'ants': [{'id': 0, 'position': (10, 10)}]
        }
        filepath = os.path.join(self.temp_dir, 'snapshot.json')
        
        future = self.io_manager.write_dashboard_snapshot_async(snapshot, filepath)
        result = future.result()
        
        self.assertTrue(os.path.exists(filepath))
        
        with open(filepath, 'r') as f:
            loaded = json.load(f)
        self.assertEqual(loaded['iteration'], 50)
    
    def test_save_and_load_checkpoint(self):
        """Test checkpoint save and load with proper state structure"""
        # Create state with required structure
        state = {
            'iteration': 100,
            'metrics': {
                'food_collected': 10,
                'avg_pheromone': 5.5,
                'ants_with_food': 3,
                'food_remaining': 50,
                'max_pheromone': 12.0
            },
            'ants': [
                {'id': 0, 'path_length': 5},
                {'id': 1, 'path_length': 3},
                {'id': 2, 'path_length': 0}
            ]
        }
        filepath = os.path.join(self.temp_dir, 'checkpoint.json')
        
        # Save
        save_future = self.io_manager.save_checkpoint_async(state, filepath)
        save_future.result()
        
        self.assertTrue(os.path.exists(filepath))
        
        # Load
        load_future = self.io_manager.load_checkpoint_async(filepath)
        loaded_state = load_future.result()
        
        self.assertEqual(loaded_state['iteration'], 100)
        self.assertEqual(loaded_state['food_collected'], 10)
        self.assertIn('timestamp', loaded_state)
    
    def test_multiple_async_operations(self):
        """Test multiple concurrent I/O operations"""
        futures = []
        
        for i in range(5):
            stats = {'iteration': i * 10}
            filepath = os.path.join(self.temp_dir, f'stats_{i}.json')
            future = self.io_manager.write_stats_async(stats, filepath)
            futures.append((future, filepath))
        
        # Wait for all
        for future, filepath in futures:
            future.result()
            self.assertTrue(os.path.exists(filepath))


if __name__ == '__main__':
    unittest.main()
