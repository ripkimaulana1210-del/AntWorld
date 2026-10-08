"""
Simulation module: Core simulation logic and coordination
"""

from typing import List, Dict
import random
import numpy as np
from src.world import World
from src.ant import Ant
import config


class Simulation:
    """Manages the ant colony simulation"""
    
    def __init__(self, num_ants: int, seed: int = None):
        self.seed = seed
        # Use Python's random.seed() with exact NIM value for deterministic comparison
        if seed is not None:
            random.seed(seed)
        self.rng = np.random.RandomState(seed if seed is None else seed % (2**32))
        
        # Initialize world
        self.world = World(config.WORLD_WIDTH, config.WORLD_HEIGHT, seed)
        self.world.initialize(config.FOOD_SOURCES, config.OBSTACLES)
        
        # Initialize ants with unique seeds for reproducibility
        self.ants: List[Ant] = []
        for i in range(num_ants):
            ant_seed = None if seed is None else seed + i
            ant = Ant(i, config.NEST_POSITION, ant_seed)
            self.ants.append(ant)
        
        # Simulation state
        self.iteration = 0
        self.total_iterations = config.MAX_ITERATIONS
        self.status = 'ready'
        self.food_collected = 0
        self.total_trips = 0
        self.completed_paths = []  # Track path lengths for completed trips
        self.path_length_total = 0
        self.path_count = 0
        self.best_path_length = None
    
    def step(self):
        """Execute one simulation step"""
        self.status = 'running'
        # Phase 1: Move all ants
        completed_ants = []
        for ant in self.ants:
            ant.move(self.world, config.ALPHA, config.BETA, self.iteration)
            
            # Try to collect food
            if ant.try_collect_food(self.world):
                pass  # Food collected
            
            # Try to deposit food at nest
            if ant.try_deposit_food():
                self.food_collected += 1
                self.total_trips += 1
                # Record completed path length
                if len(ant.path) > 0:
                    path_length = len(ant.path)
                    self.record_completed_path(path_length)
                completed_ants.append(ant)
        
        # Barrier: all ants made decisions from the same pheromone snapshot.
        # Merge completed trails only after movement, as in hybrid mode.
        for ant in completed_ants:
            ant.deposit_pheromone_trail(self.world, config.PHEROMONE_DEPOSIT)

        # Phase 2: decay global pheromones after all deposits have been merged.
        self.world.decay_pheromones(config.PHEROMONE_DECAY)
        
        self.iteration += 1
    
    def run(self, max_iterations: int) -> Dict:
        """Run simulation for specified iterations"""
        for _ in range(max_iterations):
            self.step()
        
        return self.get_metrics()
    
    def get_metrics(self) -> Dict:
        """Get current simulation metrics"""
        return {
            'iteration': self.iteration,
            'status': self.status,
            'food_collected': self.food_collected,
            'total_trips': self.total_trips,
            'food_remaining': int(np.sum(self.world.food_grid)),
            'avg_pheromone': float(np.mean(self.world.pheromone_grid)),
            'max_pheromone': float(np.max(self.world.pheromone_grid)),
            'ants_with_food': sum(1 for ant in self.ants if ant.has_food),
            'average_path_length': (self.path_length_total / self.path_count
                                    if self.path_count else None),
            'best_path_length': self.best_path_length,
        }

    def record_completed_path(self, path_length: int) -> None:
        """Accumulate measured successful trip path metrics."""
        if path_length <= 0:
            return
        self.completed_paths.append(path_length)
        self.path_length_total += path_length
        self.path_count += 1
        self.best_path_length = (path_length if self.best_path_length is None
                                 else min(self.best_path_length, path_length))
    
    def get_state(self) -> Dict:
        """Get complete simulation state"""
        return {
            'iteration': self.iteration,
            'metrics': self.get_metrics(),
            'world': self.world.get_state_dict(),
            'ants': [ant.get_state_dict(self.world) for ant in self.ants],
            'seed': self.seed,
            'status': self.status,
            'simulation': {'total_iterations': self.total_iterations},
        }
    
    def get_and_clear_completed_paths(self) -> list:
        """Get completed path lengths since last call and clear buffer"""
        paths = self.completed_paths.copy()
        self.completed_paths.clear()
        return paths
