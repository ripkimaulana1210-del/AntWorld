"""
Tests for world module
"""

import unittest
import numpy as np
from src.world import World
import config


class TestWorld(unittest.TestCase):
    
    def setUp(self):
        self.world = World(50, 50, seed=42)
    
    def test_initialization(self):
        """Test world initialization"""
        self.assertEqual(self.world.width, 50)
        self.assertEqual(self.world.height, 50)
        self.assertEqual(self.world.nest_position, config.NEST_POSITION)
    
    def test_initialize_with_food_and_obstacles(self):
        """Test placing food and obstacles"""
        self.world.initialize(5, 3)
        
        # Check food sources
        self.assertEqual(len(self.world.food_positions), 5)
        total_food = np.sum(self.world.food_grid)
        self.assertGreater(total_food, 0)
        
        # Check obstacles
        self.assertEqual(len(self.world.obstacle_positions), 3)
        total_obstacles = np.sum(self.world.obstacle_grid)
        self.assertEqual(total_obstacles, 3)
    
    def test_valid_position(self):
        """Test position validation"""
        # Valid position
        self.assertTrue(self.world.is_valid_position(10, 10))
        
        # Out of bounds
        self.assertFalse(self.world.is_valid_position(-1, 10))
        self.assertFalse(self.world.is_valid_position(100, 10))
        
        # Obstacle
        self.world.obstacle_grid[5, 5] = True
        self.assertFalse(self.world.is_valid_position(5, 5))
    
    def test_food_collection(self):
        """Test food collection mechanism"""
        # Place food
        self.world.food_grid[10, 10] = 50
        self.world.food_positions.add((10, 10))
        
        # Collect food
        self.assertTrue(self.world.collect_food(10, 10, 10))
        self.assertEqual(self.world.get_food(10, 10), 40)
        
        # Collect remaining food
        for _ in range(4):
            self.world.collect_food(10, 10, 10)
        
        self.assertEqual(self.world.get_food(10, 10), 0)
        self.assertNotIn((10, 10), self.world.food_positions)
    
    def test_pheromone_deposit_and_decay(self):
        """Test pheromone deposit and decay"""
        # Deposit pheromone
        self.world.deposit_pheromone(20, 20, 10.0)
        self.assertEqual(self.world.get_pheromone(20, 20), 10.0)
        
        # Multiple deposits accumulate
        self.world.deposit_pheromone(20, 20, 5.0)
        self.assertEqual(self.world.get_pheromone(20, 20), 15.0)
        
        # Decay
        self.world.decay_pheromones(0.1)
        self.assertAlmostEqual(self.world.get_pheromone(20, 20), 13.5, places=5)
    
    def test_get_neighbors(self):
        """Test neighbor finding"""
        # Center position (should have 8 neighbors)
        neighbors = self.world.get_neighbors(25, 25)
        self.assertEqual(len(neighbors), 8)
        
        # Corner position (should have 3 neighbors)
        neighbors = self.world.get_neighbors(0, 0)
        self.assertEqual(len(neighbors), 3)
        
        # Edge position (should have 5 neighbors)
        neighbors = self.world.get_neighbors(0, 25)
        self.assertEqual(len(neighbors), 5)
        
        # With obstacles
        for x in range(24, 27):
            for y in range(24, 27):
                if (x, y) != (25, 25):
                    self.world.obstacle_grid[y, x] = True
        neighbors = self.world.get_neighbors(25, 25)
        self.assertEqual(len(neighbors), 0)
    
    def test_get_state_dict(self):
        """Test state dictionary export"""
        self.world.initialize(3, 2)
        state = self.world.get_state_dict()
        
        self.assertIn('width', state)
        self.assertIn('height', state)
        self.assertIn('food_grid', state)
        self.assertIn('total_food', state)
        self.assertGreater(state['total_food'], 0)


if __name__ == '__main__':
    unittest.main()
