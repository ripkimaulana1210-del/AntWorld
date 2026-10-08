"""
Ant module: Individual ant behavior and movement
"""

import random
import numpy as np
from typing import Tuple, List
import config


class Ant:
    """Individual ant agent with foraging behavior"""
    
    def __init__(self, ant_id: int, nest_position: Tuple[int, int], seed: int = None):
        self.id = ant_id
        self.nest_position = nest_position
        self.position = nest_position
        self.has_food = False
        self.behavior = 'at_nest'
        self.path: List[Tuple[int, int]] = []
        # Use Python's random for deterministic behavior with large seeds
        if seed is not None:
            self.ant_rng = random.Random(seed)
        else:
            self.ant_rng = random.Random()
        # Keep numpy RNG for compatibility (use reduced seed)
        self.rng = np.random.RandomState(seed if seed is None else seed % (2**32))
        
    def move(self, world, alpha: float = 1.0, beta: float = 2.0, iteration: int = 0):
        """Move ant to next position based on pheromone and distance heuristics"""
        neighbors = world.get_neighbors(self.position[0], self.position[1])
        
        if not neighbors:
            return  # Stuck, no valid moves
        
        if self.has_food:
            # Return to nest - follow gradient toward nest
            target = self.nest_position
        else:
            # Search for food - use pheromone and random exploration
            target = None
        
        # Calculate probabilities for each neighbor
        probabilities = []
        for nx, ny in neighbors:
            pheromone = world.get_pheromone(nx, ny) + 0.01  # Avoid zero
            
            if target:
                # Distance heuristic (inverse distance to target)
                distance = np.sqrt((nx - target[0])**2 + (ny - target[1])**2) + 0.01
                heuristic = 1.0 / distance
            else:
                # Exploration mode - slight preference for unvisited areas
                heuristic = 1.0
            
            prob = (pheromone ** alpha) * (heuristic ** beta)
            probabilities.append(prob)
        
        # Normalize probabilities
        total = sum(probabilities)
        if total > 0:
            probabilities = [p / total for p in probabilities]
        else:
            probabilities = [1.0 / len(neighbors)] * len(neighbors)
        
        # Choose next position using deterministic seed per iteration
        # Use same formula as parallel workers for consistency
        iteration_seed = (self.id * 100000 + iteration) % (2**31)
        iteration_rng = random.Random(iteration_seed)
        choice_idx = iteration_rng.choices(range(len(neighbors)), weights=probabilities, k=1)[0]
        self.position = neighbors[choice_idx]
        if self.has_food:
            self.behavior = 'returning'
        elif world.get_pheromone(*self.position) > 0:
            self.behavior = 'following_pheromone'
        else:
            self.behavior = 'searching'
        
        # Record path for pheromone deposition
        if self.has_food:
            self.path.append(self.position)
    
    def try_collect_food(self, world) -> bool:
        """Try to collect food at current position"""
        if not self.has_food:
            x, y = self.position
            if world.collect_food(x, y):
                self.has_food = True
                self.behavior = 'at_food'
                self.path = [self.position]  # Start recording path
                return True
        return False
    
    def try_deposit_food(self) -> bool:
        """Try to deposit food at nest"""
        if self.has_food and self.position == self.nest_position:
            self.has_food = False
            self.behavior = 'at_nest'
            return True
        return False
    
    def deposit_pheromone_trail(self, world, amount: float):
        """Deposit pheromone along recorded path"""
        if self.has_food or (not self.has_food and self.path):
            for x, y in self.path:
                world.deposit_pheromone(x, y, amount)
            self.path = []
    
    def get_state_dict(self, world=None) -> dict:
        """Return render state with behavior inferred from the ant's actual state."""
        if self.behavior == 'at_food':
            behavior = 'at_food'
        elif self.position == self.nest_position and not self.has_food:
            behavior = 'at_nest'
        elif self.has_food:
            behavior = 'returning'
        else:
            behavior = self.behavior

        return {
            'id': self.id,
            'position': self.position,
            'has_food': self.has_food,
            'path_length': len(self.path),
            'behavior': behavior,
        }
    
    def get_state_dict_full(self) -> dict:
        """Get full ant state including path for parallel workers"""
        return {
            'id': self.id,
            'position': self.position,
            'has_food': self.has_food,
            'path': self.path.copy(),
            'behavior': self.behavior,
        }
