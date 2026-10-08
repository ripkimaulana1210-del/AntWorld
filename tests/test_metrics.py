"""
Tests for metrics module
"""

import unittest
import time
from src.metrics import MetricsCollector


class TestMetrics(unittest.TestCase):
    
    def setUp(self):
        self.collector = MetricsCollector()
    
    def test_timer(self):
        """Test execution timer"""
        self.collector.start_timer()
        time.sleep(0.1)
        self.collector.stop_timer()
        
        execution_time = self.collector.get_execution_time()
        self.assertGreater(execution_time, 0.09)
        self.assertLess(execution_time, 0.2)
    
    def test_record_metrics(self):
        """Test recording metrics"""
        metrics1 = {'iteration': 100, 'food_collected': 50}
        metrics2 = {'iteration': 200, 'food_collected': 75}
        
        self.collector.record_metrics(metrics1)
        self.collector.record_metrics(metrics2)
        
        self.assertEqual(len(self.collector.metrics_history), 2)
        self.assertEqual(self.collector.metrics_history[0]['iteration'], 100)
        self.assertEqual(self.collector.metrics_history[1]['food_collected'], 75)
    
    def test_compute_summary(self):
        """Test summary computation"""
        # Record some metrics
        for i in range(10):
            metrics = {
                'iteration': i * 10,
                'food_collected': i * 5,
                'avg_pheromone': 2.0 + i * 0.1
            }
            self.collector.record_metrics(metrics)
        
        self.collector.start_timer()
        time.sleep(0.1)
        self.collector.stop_timer()
        
        summary = self.collector.compute_summary(num_ants=100, num_iterations=90)
        
        self.assertIn('total_food_collected', summary)
        self.assertIn('total_iterations', summary)
        self.assertIn('execution_time_seconds', summary)
        
        self.assertEqual(summary['total_food_collected'], 45)
        self.assertEqual(summary['total_iterations'], 90)
        self.assertGreater(summary['execution_time_seconds'], 0)
    
    def test_record_path(self):
        """Test path recording"""
        self.collector.record_path(10)
        self.collector.record_path(5)
        self.collector.record_path(8)
        
        self.assertEqual(self.collector.best_path_length, 5)
        self.assertEqual(self.collector.path_count, 3)
        self.assertEqual(self.collector.total_path_length, 23)
    
    def test_speedup_calculation(self):
        """Test speedup calculation with baseline"""
        self.collector.start_timer()
        time.sleep(0.1)
        self.collector.stop_timer()
        
        # Add dummy metrics
        self.collector.record_metrics({'iteration': 100, 'food_collected': 50})
        
        # Compute with baseline
        baseline_time = 1.0
        summary = self.collector.compute_summary(
            num_ants=100,
            num_iterations=100,
            baseline_time=baseline_time,
            num_processes=3
        )
        
        self.assertIn('speedup', summary)
        self.assertIn('efficiency_percent', summary)
        self.assertGreater(summary['speedup'], 1.0)


if __name__ == '__main__':
    unittest.main()
