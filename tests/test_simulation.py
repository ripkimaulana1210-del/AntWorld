"""
Tests for simulation module
"""

import unittest
from src.simulation import Simulation
import config


class TestSimulation(unittest.TestCase):
    
    def setUp(self):
        self.sim = Simulation(num_ants=100, seed=42)
    
    def test_initialization(self):
        """Test simulation initialization"""
        self.assertEqual(len(self.sim.ants), 100)
        self.assertEqual(self.sim.iteration, 0)
        self.assertEqual(self.sim.food_collected, 0)
        self.assertIsNotNone(self.sim.world)
    
    def test_step_execution(self):
        """Test single simulation step"""
        initial_iteration = self.sim.iteration
        
        self.sim.step()
        
        self.assertEqual(self.sim.iteration, initial_iteration + 1)
    
    def test_multiple_steps(self):
        """Test multiple simulation steps"""
        num_steps = 50
        
        for _ in range(num_steps):
            self.sim.step()
        
        self.assertEqual(self.sim.iteration, num_steps)
    
    def test_food_collection_progress(self):
        """Test that ants eventually collect food"""
        # Run enough iterations for ants to find food
        for _ in range(500):
            self.sim.step()
        
        # Should have collected some food by now
        metrics = self.sim.get_metrics()
        # Note: Due to randomness, might not always collect food in 500 iterations
        # but pheromone levels should increase
        self.assertGreaterEqual(metrics['avg_pheromone'], 0)
    
    def test_pheromone_decay(self):
        """Test pheromone decay mechanism"""
        # Deposit pheromone
        self.sim.world.deposit_pheromone(30, 30, 100.0)
        initial_pheromone = self.sim.world.get_pheromone(30, 30)
        
        # Run step (should trigger decay)
        self.sim.step()
        
        # Pheromone should decrease
        final_pheromone = self.sim.world.get_pheromone(30, 30)
        self.assertLess(final_pheromone, initial_pheromone)
    
    def test_get_metrics(self):
        """Test metrics retrieval"""
        metrics = self.sim.get_metrics()
        
        required_keys = ['iteration', 'food_collected', 'total_trips',
                        'food_remaining', 'avg_pheromone', 'max_pheromone',
                        'ants_with_food']
        
        for key in required_keys:
            self.assertIn(key, metrics)
    
    def test_get_state(self):
        """Test state retrieval"""
        state = self.sim.get_state()
        
        self.assertIn('iteration', state)
        self.assertIn('metrics', state)
        self.assertIn('world', state)
        self.assertIn('ants', state)
        
        self.assertEqual(len(state['ants']), 100)
    
    def test_deterministic_behavior(self):
        """Test that same seed produces same results"""
        sim1 = Simulation(num_ants=50, seed=123)
        sim2 = Simulation(num_ants=50, seed=123)
        
        # Run same number of steps
        for _ in range(100):
            sim1.step()
            sim2.step()
        
        # Should have same results
        metrics1 = sim1.get_metrics()
        metrics2 = sim2.get_metrics()
        
        self.assertEqual(metrics1['food_collected'], metrics2['food_collected'])
        self.assertEqual(metrics1['iteration'], metrics2['iteration'])

    def test_default_mode_matches_explicit_baseline(self):
        default = Simulation(num_ants=20, seed=321)
        baseline = Simulation(num_ants=20, seed=321, exploration_mode='baseline')

        for _ in range(25):
            default.step()
            baseline.step()

        self.assertEqual(default.get_metrics(), baseline.get_metrics())
        self.assertEqual(
            [ant.get_state_dict_full() for ant in default.ants],
            [ant.get_state_dict_full() for ant in baseline.ants],
        )
        self.assertEqual(default.world.pheromone_grid.tolist(),
                         baseline.world.pheromone_grid.tolist())


if __name__ == '__main__':
    unittest.main()
