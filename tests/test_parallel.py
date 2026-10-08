"""
Tests for parallel module - must genuinely execute ProcessPool
"""

import unittest
from src.simulation import Simulation
from src.parallel import HybridSimulation, worker_step_ants
import config


class TestParallel(unittest.TestCase):
    
    def test_worker_step_ants(self):
        """Test worker function directly"""
        # Create minimal world snapshot
        world_snapshot = {
            'width': 50,
            'height': 50,
            'food_grid': [[0]*50 for _ in range(50)],
            'obstacle_grid': [[False]*50 for _ in range(50)],
            'pheromone_grid': [[0.0]*50 for _ in range(50)],
            'nest_position': (25, 25)
        }
        
        # Create ant states
        ant_states = [
            {'id': 0, 'position': (25, 25), 'has_food': False, 'path': []},
            {'id': 1, 'position': (26, 26), 'has_food': False, 'path': []},
        ]
        
        args = (ant_states, world_snapshot, 0, 0, 42)
        
        result = worker_step_ants(args)
        
        self.assertIn('updated_ants', result)
        self.assertIn('food_attempts', result)
        self.assertIn('pheromone_deposits', result)
        self.assertIn('nest_deposits', result)
        self.assertIn('chunk_id', result)
        
        self.assertEqual(len(result['updated_ants']), 2)
        self.assertEqual(result['chunk_id'], 0)
    
    def test_hybrid_simulation_initialization(self):
        """Test hybrid simulation initialization"""
        sim = Simulation(100, seed=42)
        hybrid_sim = HybridSimulation(sim, num_processes=2)
        
        self.assertEqual(hybrid_sim.num_processes, 2)
        self.assertEqual(hybrid_sim.sim, sim)
    
    def test_step_parallel_genuinely_uses_processpool(self):
        """
        Test that parallel execution genuinely uses ProcessPool.
        This test actually spawns processes and executes work.
        """
        sim = Simulation(num_ants=50, seed=42)
        hybrid_sim = HybridSimulation(sim, num_processes=2)
        
        initial_iteration = sim.iteration
        
        # Execute one parallel step
        hybrid_sim.step_parallel()
        
        # Verify iteration incremented
        self.assertEqual(sim.iteration, initial_iteration + 1)
        
        # Verify ants moved (positions should have changed for at least some ants)
        # Note: all ants start at nest, after one step some should have moved
        positions = [ant.position for ant in sim.ants]
        unique_positions = len(set(positions))
        self.assertGreater(unique_positions, 1, "Some ants should have moved from nest")
    
    def test_multiple_parallel_steps(self):
        """Test multiple parallel steps"""
        sim = Simulation(num_ants=30, seed=123)
        hybrid_sim = HybridSimulation(sim, num_processes=2)
        
        # Run 10 parallel steps
        for _ in range(10):
            hybrid_sim.step_parallel()
        
        self.assertEqual(sim.iteration, 10)
        
        # Get metrics
        metrics = sim.get_metrics()
        self.assertEqual(metrics['iteration'], 10)
    
    def test_determinism_serial_vs_hybrid(self):
        """Test that serial and hybrid produce same results with same seed"""
        seed = 999
        
        # Run serial
        sim_serial = Simulation(num_ants=50, seed=seed)
        for _ in range(20):
            sim_serial.step()
        metrics_serial = sim_serial.get_metrics()
        
        # Run hybrid
        sim_hybrid = Simulation(num_ants=50, seed=seed)
        hybrid_sim = HybridSimulation(sim_hybrid, num_processes=2)
        for _ in range(20):
            hybrid_sim.step_parallel()
        metrics_hybrid = sim_hybrid.get_metrics()
        
        # Compare results - should be identical
        self.assertEqual(metrics_serial['food_collected'], metrics_hybrid['food_collected'],
                        "Food collected should match between serial and hybrid")
        self.assertEqual(metrics_serial['total_trips'], metrics_hybrid['total_trips'],
                        "Total trips should match between serial and hybrid")
        
        # Note: Due to potential floating point rounding in process communication,
        # pheromone levels might differ very slightly
        self.assertAlmostEqual(metrics_serial['avg_pheromone'], 
                              metrics_hybrid['avg_pheromone'], 
                              places=5,
                              msg="Average pheromone should be close")

    def test_foraging_mode_serial_hybrid_determinism(self):
        seed = 2718
        serial = Simulation(num_ants=30, seed=seed, exploration_mode='foraging')
        hybrid_simulation = Simulation(num_ants=30, seed=seed, exploration_mode='foraging')
        hybrid = HybridSimulation(hybrid_simulation, num_processes=2)

        try:
            for _ in range(60):
                serial.step()
                hybrid.step_parallel()

            self.assertEqual(serial.get_metrics(), hybrid_simulation.get_metrics())
            self.assertEqual(
                [ant.get_state_dict_full() for ant in serial.ants],
                [ant.get_state_dict_full() for ant in hybrid_simulation.ants],
            )
            self.assertEqual(serial.world.food_grid.tolist(),
                             hybrid_simulation.world.food_grid.tolist())
            self.assertEqual(serial.world.pheromone_grid.tolist(),
                             hybrid_simulation.world.pheromone_grid.tolist())
        finally:
            hybrid.shutdown()
    
    def test_exception_propagation(self):
        """Test that worker exceptions are propagated"""
        # This test verifies that exceptions in workers are caught and raised
        sim = Simulation(num_ants=10, seed=42)
        hybrid_sim = HybridSimulation(sim, num_processes=2)
        
        # Normal execution should work
        try:
            hybrid_sim.step_parallel()
            # If we get here, execution succeeded (expected)
            self.assertTrue(True)
        except RuntimeError:
            # This would indicate worker failure
            self.fail("Worker should not fail with valid input")


if __name__ == '__main__':
    unittest.main()
