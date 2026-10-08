"""
Tests for ant module
"""

import unittest
from src.ant import Ant
from src.world import World
import config


class TestAnt(unittest.TestCase):
    
    def setUp(self):
        self.world = World(50, 50, seed=42)
        self.world.initialize(5, 3)
        self.ant = Ant(0, config.NEST_POSITION, seed=42)
    
    def test_initialization(self):
        """Test ant initialization"""
        self.assertEqual(self.ant.id, 0)
        self.assertEqual(self.ant.position, config.NEST_POSITION)
        self.assertFalse(self.ant.has_food)
        self.assertEqual(len(self.ant.path), 0)
    
    def test_movement(self):
        """Test ant movement"""
        initial_pos = self.ant.position
        
        # Move ant
        self.ant.move(self.world)
        
        # Position should change
        self.assertNotEqual(self.ant.position, initial_pos)
        
        # Position should be valid
        x, y = self.ant.position
        self.assertTrue(self.world.is_valid_position(x, y))
    
    def test_food_collection(self):
        """Test food collection"""
        # Place ant on food
        food_pos = list(self.world.food_positions)[0]
        self.ant.position = food_pos
        
        # Collect food
        self.assertTrue(self.ant.try_collect_food(self.world))
        self.assertTrue(self.ant.has_food)
        self.assertGreater(len(self.ant.path), 0)
        
        # Can't collect again while carrying food
        self.assertFalse(self.ant.try_collect_food(self.world))
    
    def test_food_deposit(self):
        """Test food deposit at nest"""
        # Give ant food
        self.ant.has_food = True
        self.ant.position = config.NEST_POSITION
        
        # Deposit food
        self.assertTrue(self.ant.try_deposit_food())
        self.assertFalse(self.ant.has_food)
        
        # Can't deposit without food
        self.assertFalse(self.ant.try_deposit_food())
    
    def test_pheromone_trail(self):
        """Test pheromone trail deposition"""
        # Create path
        self.ant.has_food = True
        self.ant.path = [(25, 25), (26, 26), (27, 27)]
        
        # Deposit pheromone
        self.ant.deposit_pheromone_trail(self.world, 5.0)
        
        # Check pheromone deposited
        self.assertGreater(self.world.get_pheromone(25, 25), 0)
        self.assertGreater(self.world.get_pheromone(26, 26), 0)
        
        # Path should be cleared
        self.assertEqual(len(self.ant.path), 0)
    
    def test_get_state_dict(self):
        """Test state dictionary export"""
        state = self.ant.get_state_dict()
        
        self.assertIn('id', state)
        self.assertIn('position', state)
        self.assertIn('has_food', state)
        self.assertEqual(state['id'], 0)


if __name__ == '__main__':
    unittest.main()
