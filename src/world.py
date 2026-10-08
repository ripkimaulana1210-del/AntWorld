"""
World module: Grid, food sources, obstacles, and pheromone trails
"""

import random
import numpy as np
from typing import Tuple, List, Set
import config


class World:
    """Represents the 2D world grid with food, obstacles, and pheromones"""
    
    def __init__(self, width: int, height: int, seed: int = None):
        self.width = width
        self.height = height
        # Use reduced seed for numpy compatibility
        self.rng = np.random.RandomState(seed if seed is None else seed % (2**32))
        
        # Grid layers
        self.food_grid = np.zeros((height, width), dtype=int)
        self.obstacle_grid = np.zeros((height, width), dtype=bool)
        self.pheromone_grid = np.zeros((height, width), dtype=float)
        
        # Track positions
        self.nest_position = config.NEST_POSITION
        self.food_positions: Set[Tuple[int, int]] = set()
        self.obstacle_positions: Set[Tuple[int, int]] = set()
        
    def initialize(self, num_food_sources: int, num_obstacles: int, 
                   food_amount: int = 100):
        """Initialize world with random food sources and obstacles"""
        # Place food sources
        for _ in range(num_food_sources):
            while True:
                x = self.rng.randint(0, self.width)
                y = self.rng.randint(0, self.height)
                pos = (x, y)
                if (pos != self.nest_position and 
                    pos not in self.food_positions and 
                    pos not in self.obstacle_positions):
                    self.food_grid[y, x] = food_amount
                    self.food_positions.add(pos)
                    break
        
        # Place obstacles
        for _ in range(num_obstacles):
            while True:
                x = self.rng.randint(0, self.width)
                y = self.rng.randint(0, self.height)
                pos = (x, y)
                if (pos != self.nest_position and 
                    pos not in self.food_positions and 
                    pos not in self.obstacle_positions):
                    self.obstacle_grid[y, x] = True
                    self.obstacle_positions.add(pos)
                    break
    
    def is_valid_position(self, x: int, y: int) -> bool:
        """Check if position is within bounds and not an obstacle"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return False
        return not self.obstacle_grid[y, x]
    
    def get_food(self, x: int, y: int) -> int:
        """Get food amount at position"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.food_grid[y, x]
        return 0
    
    def collect_food(self, x: int, y: int, amount: int = 1) -> bool:
        """Try to collect food from position. Returns True if successful."""
        if self.get_food(x, y) > 0:
            self.food_grid[y, x] = max(0, self.food_grid[y, x] - amount)
            if self.food_grid[y, x] == 0:
                self.food_positions.discard((x, y))
            return True
        return False
    
    def deposit_pheromone(self, x: int, y: int, amount: float):
        """Deposit pheromone at position"""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pheromone_grid[y, x] += amount
    
    def get_pheromone(self, x: int, y: int) -> float:
        """Get pheromone level at position"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.pheromone_grid[y, x]
        return 0.0
    
    def decay_pheromones(self, decay_rate: float):
        """Apply decay to all pheromones"""
        self.pheromone_grid *= (1.0 - decay_rate)
        self.pheromone_grid = np.maximum(self.pheromone_grid, 0.0)
    
    def get_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Get valid neighboring positions (8-directional)"""
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if self.is_valid_position(nx, ny):
                    neighbors.append((nx, ny))
        return neighbors
    
    def get_state_dict(self) -> dict:
        """Get world state as dictionary for serialization"""
        return {
            'width': self.width,
            'height': self.height,
            'food_grid': self.food_grid.tolist(),
            'obstacle_grid': self.obstacle_grid.tolist(),
            'pheromone_grid': self.pheromone_grid.tolist(),
            'nest_position': self.nest_position,
            'total_food': int(np.sum(self.food_grid)),
            'food_sources': len(self.food_positions)
        }
