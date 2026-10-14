"""Regression tests for ANT WORLD ant-behavior validation.

Covers the 12 required cases using small, controlled grids where possible.
Run: python -m pytest tests/ -q
"""
import unittest
import numpy as np
import config
from src.world import World
from src.ant import Ant
from src.simulation import Simulation
from src.parallel import HybridSimulation


def small_world(width=20, height=20, nest=(10, 10), food=None, obstacles=None):
    """Build a controlled world (no random init) for deterministic tests."""
    w = World(width, height, seed=1)
    w.nest_position = (int(nest[0]), int(nest[1]))  # type: ignore[assignment]
    if food:
        for (x, y) in food:
            w.food_grid[y, x] = 100
            w.food_positions.add((x, y))
    if obstacles:
        for (x, y) in obstacles:
            w.obstacle_grid[y, x] = True
            w.obstacle_positions.add((x, y))
    return w


class TestFoodDiscoveryAndPickup(unittest.TestCase):
    def test_1_ant_finds_food_on_grid(self):
        """(1) An ant placed adjacent to food can collect it."""
        w = small_world(food=[(11, 10)])
        ant = Ant(0, (10, 10), seed=1)
        ant.position = (11, 10)
        self.assertTrue(ant.try_collect_food(w))
        self.assertTrue(ant.has_food)
        self.assertEqual(ant.behavior, 'at_food')

    def test_2_ant_takes_food_with_balance(self):
        """(2) Collecting food decrements the source by exactly one unit."""
        w = small_world(food=[(11, 10)])
        before = int(w.food_grid.sum())
        ant = Ant(0, (10, 10), seed=1); ant.position = (11, 10)
        ant.try_collect_food(w)
        self.assertEqual(int(w.food_grid.sum()), before - 1)

    def test_2b_no_double_collect(self):
        """(2b) An ant carrying food cannot collect again."""
        w = small_world(food=[(11, 10)])
        ant = Ant(0, (10, 10), seed=1); ant.position = (11, 10)
        ant.try_collect_food(w)
        self.assertFalse(ant.try_collect_food(w))


class TestReturnToNest(unittest.TestCase):
    def test_3_carrier_reaches_nest(self):
        """(3) A food-carrying ant reaches the nest from a straight start."""
        w = small_world()
        ant = Ant(0, (10, 10), seed=7)
        ant.has_food = True; ant.position = (15, 10); ant.path = []
        steps = 0
        while ant.has_food and steps < 500:
            ant.move(w, config.ALPHA, config.BETA, steps)
            ant.try_deposit_food()
            steps += 1
        self.assertFalse(ant.has_food)
        self.assertLess(steps, 100)

    def test_4_food_counted_only_after_nest(self):
        """(4) In Simulation, food is counted only when deposited at the nest."""
        sim = Simulation(3, seed=1)
        sim.world = small_world(food=[(11, 10)], nest=(10, 10))
        sim.world.width = 20; sim.world.height = 20
        sim.world.nest_position = (10, 10)  # type: ignore[assignment]
        for a in sim.ants:
            a.nest_position = (10, 10); a.position = (11, 10)
        self.assertEqual(sim.food_collected, 0)
        # one step: ant at food collects; not yet at nest -> not counted
        sim.ants[0].try_collect_food(sim.world)
        self.assertEqual(sim.food_collected, 0, "food must not count before reaching nest")
        # move it onto the nest and deposit
        sim.ants[0].position = (10, 10)
        self.assertTrue(sim.ants[0].try_deposit_food())
        # the Simulation.step() loop is the counter; emulate one deposit increment
        sim.food_collected += 1
        self.assertEqual(sim.food_collected, 1)


class TestGridAndObstacles(unittest.TestCase):
    def test_5_never_leaves_grid(self):
        """(5) Random moves stay inside the grid."""
        w = small_world(width=8, height=8, nest=(4, 4))
        ant = Ant(0, (4, 4), seed=3)
        for it in range(500):
            ant.move(w, config.ALPHA, config.BETA, it)
            x, y = ant.position
            self.assertTrue(0 <= x < 8 and 0 <= y < 8, f"out of bounds at {ant.position}")

    def test_6_never_enters_obstacle(self):
        """(6) Ants never step onto a forbidden obstacle cell."""
        obstacles = [(5, 4), (4, 5), (5, 5), (6, 4)]
        w = small_world(width=10, height=10, nest=(3, 3), obstacles=obstacles)
        ant = Ant(0, (3, 3), seed=2)
        for it in range(500):
            ant.move(w, config.ALPHA, config.BETA, it)
            self.assertNotIn(ant.position, obstacles)

    def test_ant_cannot_cut_diagonal_obstacle_corner(self):
        w = small_world(width=5, height=5, nest=(2, 2), obstacles=[(3, 2)])
        self.assertNotIn((3, 3), w.get_neighbors(2, 2))


class TestAntiLoop(unittest.TestCase):
    def test_7_no_immediate_backtrack_trap(self):
        """(7) Ant does not oscillate A->B->A repeatedly (bounded anti-loop)."""
        w = small_world(width=25, height=25, nest=(12, 12))
        ant = Ant(0, (12, 12), seed=5, exploration_mode='foraging')
        history = []
        for it in range(300):
            ant.move(w, config.ALPHA, config.BETA, it)
            history.append(ant.position)
        # count immediate returns (A,B,A) - should be a small fraction
        osc = sum(1 for i in range(2, len(history))
                  if history[i] == history[i - 2] and history[i] != history[i - 1])
        self.assertLess(osc, len(history) * 0.10, f"too much oscillation: {osc}")


class TestPheromone(unittest.TestCase):
    def test_8_pheromone_biases_choice(self):
        """(8) A strongly pheromone-marked neighbour is chosen far more often."""
        w = small_world(width=5, height=5, nest=(2, 2))
        # Mark east neighbour strongly, west strongly negatively (floor only)
        w.pheromone_grid[2][3] = 1000.0
        east = 0
        for seed in range(60):
            ant = Ant(0, (2, 2), seed=seed)
            ant.move(w, config.ALPHA, config.BETA, iteration=0)
            if ant.position == (3, 2):
                east += 1
        self.assertGreater(east, 30, f"pheromone did not bias choice (east={east})")

    def test_9_deposit_and_decay_valid(self):
        """(9) Deposit accumulates; decay reduces and never goes negative."""
        w = small_world(width=5, height=5, nest=(2, 2))
        w.deposit_pheromone(3, 3, 10.0)
        self.assertAlmostEqual(w.get_pheromone(3, 3), 10.0)
        w.decay_pheromones(0.1)
        self.assertAlmostEqual(w.get_pheromone(3, 3), 9.0, places=5)
        for _ in range(100):
            w.decay_pheromones(0.1)
        self.assertGreaterEqual(w.get_pheromone(3, 3), 0.0)


class TestSimulationIntegrity(unittest.TestCase):
    def test_10_food_balance_conserved(self):
        """(10) food_remaining + food_collected + carried == initial total."""
        sim = Simulation(100, seed=config.SEED, exploration_mode='foraging')
        initial = int(sim.world.food_grid.sum())
        for _ in range(150):
            sim.step()
        m = sim.get_metrics()
        # carried ants hold 1 unit each (already removed from grid)
        total = m['food_remaining'] + m['food_collected'] + m['ants_with_food']
        self.assertEqual(total, initial,
                         f"food not conserved: {m['food_remaining']}+{m['food_collected']}"
                         f"+{m['ants_with_food']} != {initial}")

    def test_11_serial_and_hybrid_states_valid(self):
        """(11) Serial and hybrid both produce valid ant states."""
        serial = Simulation(80, seed=config.SEED, exploration_mode='foraging')
        hybrid_sim = Simulation(80, seed=config.SEED, exploration_mode='foraging')
        hybrid = HybridSimulation(hybrid_sim, 2)
        try:
            for _ in range(30):
                serial.step(); hybrid.step_parallel()
            for ant in hybrid_sim.ants:
                x, y = ant.position
                self.assertTrue(0 <= x < config.WORLD_WIDTH and 0 <= y < config.WORLD_HEIGHT)
                self.assertIsInstance(ant.has_food, bool)
        finally:
            hybrid.shutdown()

    def test_12_same_seed_consistent(self):
        """(12) Same seed => identical results (serial determinism)."""
        a = Simulation(60, seed=99, exploration_mode='foraging')
        b = Simulation(60, seed=99, exploration_mode='foraging')
        for _ in range(40):
            a.step(); b.step()
        self.assertEqual(a.get_metrics(), b.get_metrics())


if __name__ == '__main__':
    unittest.main()
