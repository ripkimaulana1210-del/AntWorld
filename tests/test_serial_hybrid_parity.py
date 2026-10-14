"""Regression tests for serial/hybrid collection-semantics parity.

Verifies the observations the task requires:
- serial and hybrid have identical per-iteration state (position, has_food,
  path, visit_history, food_grid, pheromone_grid) for the same seed/config;
- food balance (remaining + collected + carried) is always conserved;
- no double collection or double deposit;
- ants respect grid bounds and obstacles;
- pheromone deposit/decay are consistent.

IMPORTANT: parameters are read from config.py (the production path). This test
must NOT mutate config.ALPHA/BETA/... at runtime: ProcessPoolExecutor children
re-import config, so a parent-only override would desync serial vs hybrid workers
and produce a false failure. That desync was the root cause of a prior false alarm.
"""
import unittest
import numpy as np
import config
from src.simulation import Simulation
from src.parallel import HybridSimulation

SEEDS = [config.SEED, 7, 42, 123, 2024]


def _snapshot(sim):
    return {
        'iteration': sim.iteration,
        'food_grid': np.array(sim.world.food_grid).tolist(),
        'pheromone_grid': np.round(sim.world.pheromone_grid, 9).tolist(),
        'food_collected': sim.food_collected,
        'total_trips': sim.total_trips,
        'ants': [(a.position, a.has_food, list(a.path), list(a.visit_history)) for a in sim.ants],
    }


class TestSerialHybridParity(unittest.TestCase):
    def _run_pair(self, seed, iters, n=120, chunks=3):
        a = Simulation(n, seed=seed, exploration_mode='foraging')
        b = Simulation(n, seed=seed, exploration_mode='foraging')
        h = HybridSimulation(b, chunks)
        try:
            for _ in range(iters):
                a.step(); h.step_parallel()
                if _snapshot(a) != _snapshot(b):
                    return False, a.iteration
            return True, iters
        finally:
            h.shutdown()

    def test_identical_state_each_iteration(self):
        """Serial and hybrid must match every iteration, every seed."""
        for seed in SEEDS:
            same, at = self._run_pair(seed, 120)
            self.assertTrue(same, f"diverged for seed={seed} at iteration {at}")


class TestFoodBalance(unittest.TestCase):
    def test_balance_conserved_serial_and_hybrid(self):
        for seed in SEEDS[:3]:
            for mode in ('serial', 'hybrid'):
                init = None
                if mode == 'serial':
                    sim = Simulation(120, seed=seed, exploration_mode='foraging')
                    init = int(sim.world.food_grid.sum())
                    for _ in range(120):
                        sim.step()
                    m = sim.get_metrics()
                else:
                    sim = Simulation(120, seed=seed, exploration_mode='foraging')
                    init = int(sim.world.food_grid.sum())
                    h = HybridSimulation(sim, 3)
                    try:
                        for _ in range(120):
                            h.step_parallel()
                    finally:
                        h.shutdown()
                    m = sim.get_metrics()
                total = m['food_remaining'] + m['food_collected'] + m['ants_with_food']
                self.assertEqual(total, init, f"{mode} seed={seed}: {total} != {init}")


class TestNoDoubleCount(unittest.TestCase):
    def test_never_collects_more_than_food(self):
        sim = Simulation(150, seed=config.SEED, exploration_mode='foraging')
        init = int(sim.world.food_grid.sum())
        for _ in range(300):
            sim.step()
        m = sim.get_metrics()
        # collected can never exceed available food
        self.assertLessEqual(m['food_collected'] + m['ants_with_food'], init)

    def test_collection_and_trips_consistent(self):
        sim = Simulation(150, seed=7, exploration_mode='foraging')
        for _ in range(200):
            sim.step()
        m = sim.get_metrics()
        self.assertEqual(m['food_collected'], m['total_trips'])


class TestGridAndObstacles(unittest.TestCase):
    def test_never_out_of_bounds_or_on_obstacle(self):
        sim = Simulation(150, seed=42, exploration_mode='foraging')
        obstacles = sim.world.obstacle_grid
        for _ in range(150):
            sim.step()
            for a in sim.ants:
                x, y = a.position
                self.assertTrue(0 <= x < config.WORLD_WIDTH and 0 <= y < config.WORLD_HEIGHT,
                                f"ant {a.id} out of bounds at {a.position}")
                self.assertFalse(obstacles[y][x], f"ant {a.id} on obstacle at {a.position}")


class TestPheromoneConsistency(unittest.TestCase):
    def test_serial_hybrid_pheromone_identical(self):
        a = Simulation(120, seed=config.SEED, exploration_mode='foraging')
        b = Simulation(120, seed=config.SEED, exploration_mode='foraging')
        h = HybridSimulation(b, 3)
        try:
            for _ in range(120):
                a.step(); h.step_parallel()
            self.assertTrue(np.array_equal(a.world.pheromone_grid, b.world.pheromone_grid))
        finally:
            h.shutdown()

    def test_decay_never_negative(self):
        sim = Simulation(50, seed=1, exploration_mode='foraging')
        for _ in range(100):
            sim.step()
        self.assertGreaterEqual(float(sim.world.pheromone_grid.min()), 0.0)


if __name__ == '__main__':
    unittest.main()
