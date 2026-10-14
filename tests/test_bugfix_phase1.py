"""Regression tests for Bug Fix Phase 1.

Covers:
- A. status consistency: mark_completed() makes status/metrics/state agree.
- B. return-path gradient: a food-carrying ant heads home efficiently and
     serial/hybrid stay deterministic.
Run: python -m pytest tests/ -q
"""
import unittest
from src.simulation import Simulation
from src.parallel import HybridSimulation
import config


class TestStatusConsistency(unittest.TestCase):
    def test_initial_status_is_ready(self):
        sim = Simulation(10, seed=1)
        self.assertEqual(sim.status, 'ready')
        self.assertEqual(sim.get_metrics()['status'], 'ready')
        self.assertEqual(sim.get_state()['status'], 'ready')

    def test_status_running_after_step(self):
        sim = Simulation(10, seed=1)
        sim.step()
        self.assertEqual(sim.status, 'running')
        self.assertEqual(sim.get_metrics()['status'], 'running')
        self.assertEqual(sim.get_state()['status'], 'running')

    def test_mark_completed_keeps_status_consistent(self):
        sim = Simulation(10, seed=1)
        for _ in range(3):
            sim.step()
        sim.mark_completed()
        # Top-level, metrics, and state must all agree.
        self.assertEqual(sim.status, 'completed')
        self.assertEqual(sim.get_metrics()['status'], 'completed')
        self.assertEqual(sim.get_state()['status'], 'completed')

    def test_run_marks_completed(self):
        sim = Simulation(10, seed=1)
        sim.run(5)
        self.assertEqual(sim.get_metrics()['status'], 'completed')


class TestReturnGradient(unittest.TestCase):
    def test_food_carrying_ant_reaches_nest_reasonably(self):
        """A food-carrying ant near the nest should return in a bounded time."""
        sim = Simulation(1, seed=7)
        ant = sim.ants[0]
        ant.has_food = True
        ant.position = (60, 50)          # 10 cells east of nest (50, 50)
        ant.path = []
        steps = 0
        while ant.has_food and steps < 5000:
            ant.move(sim.world, config.ALPHA, config.BETA, steps)
            ant.try_deposit_food()
            steps += 1
        self.assertFalse(ant.has_food, "ant should reach the nest and deposit food")
        # straight-line Manhattan distance is 10; allow generous slack but far
        # below the pre-fix random-walk average (~2.3x with old heuristic).
        self.assertLess(steps, 60, f"return took {steps} steps for a 10-cell trip")

    def test_serial_hybrid_return_determinism(self):
        """Serial and hybrid must produce identical metrics (same seed)."""
        serial = Simulation(150, seed=config.SEED, exploration_mode='foraging')
        hybrid_sim = Simulation(150, seed=config.SEED, exploration_mode='foraging')
        hybrid = HybridSimulation(hybrid_sim, 2)
        try:
            for _ in range(30):
                serial.step()
                hybrid.step_parallel()
            self.assertEqual(serial.get_metrics(), hybrid_sim.get_metrics())
            self.assertEqual(serial.world.pheromone_grid.tolist(),
                             hybrid_sim.world.pheromone_grid.tolist())
        finally:
            hybrid.shutdown()


class TestCompletionSemantics(unittest.TestCase):
    """Group D: completion criterion is the iteration limit; ants still holding
    food at the end are reported, not forced home, and food balance is untouched."""

    def test_trips_in_progress_reported(self):
        sim = Simulation(50, seed=config.SEED, exploration_mode='foraging')
        for ant in sim.ants[:5]:
            ant.has_food = True
        metrics = sim.get_metrics()
        self.assertEqual(metrics['ants_with_food'], 5)
        self.assertEqual(metrics['trips_in_progress'], 5)
        # Food balance must be untouched by the report.
        self.assertEqual(metrics['food_collected'], 0)
        self.assertEqual(metrics['food_remaining'], int(sim.world.food_grid.sum()))


class TestControlCycleGuards(unittest.TestCase):
    """Group E: control request guards must match the current status."""

    def setUp(self):
        from src.dashboard_server import DashboardState
        self.state = DashboardState()

    def test_start_only_when_ready(self):
        self.state.update({'status': 'running'})
        accepted, _ = self.state.request_start()
        self.assertFalse(accepted)
        self.state.update({'status': 'ready'})
        accepted, _ = self.state.request_start()
        self.assertTrue(accepted)

    def test_pause_only_when_running(self):
        self.state.update({'status': 'ready'})
        self.assertFalse(self.state.request_pause()[0])
        self.state.update({'status': 'running'})
        self.assertTrue(self.state.request_pause()[0])

    def test_resume_only_when_paused(self):
        self.state.update({'status': 'running'})
        self.assertFalse(self.state.request_resume()[0])
        self.state.update({'status': 'paused'})
        self.assertTrue(self.state.request_resume()[0])

    def test_restart_guarded_on_ready(self):
        self.state.update({'status': 'ready'})
        self.assertFalse(self.state.request_restart()[0])
        self.state.update({'status': 'completed'})
        self.assertTrue(self.state.request_restart()[0])


class TestNoLeftoverPool(unittest.TestCase):
    """Group E: shutdown must release the ProcessPool (no leftover children)."""

    def test_hybrid_shutdown_releases_pool(self):
        import threading, time
        sim = Simulation(40, seed=1)
        hybrid = HybridSimulation(sim, 2)
        hybrid.step_parallel()
        hybrid.shutdown()
        time.sleep(0.3)
        # executor threads (if any) must not remain alive after shutdown
        alive = [t for t in threading.enumerate() if t.is_alive() and 'futures' in t.name.lower()]
        self.assertEqual(alive, [], f"leftover executor threads: {alive}")


if __name__ == '__main__':
    unittest.main()
