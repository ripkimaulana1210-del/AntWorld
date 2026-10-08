"""
Parallel module: Per-iteration hybrid parallelization using persistent ProcessPoolExecutor

Architecture:
- Main process owns canonical Simulation with world and all ants
- Persistent ProcessPool across all iterations (not recreated per step)
- Each iteration: snapshot world state, split ants into chunks for workers
- Workers compute next-state outcomes for their ant subset (deterministic per-ant RNG)
- Main gathers results at barrier, merges deterministically, applies global updates
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Tuple
import random
import config


def worker_step_ants(args: tuple) -> Dict:
    """
    Picklable worker: compute next state for a chunk of ants.
    
    Args:
        args: (ant_states, world_snapshot, iteration, chunk_id, base_seed)
        
    Returns:
        Dict with updated ant states and actions (food collected, deposits, pheromones)
    """
    ant_states, world_snapshot, iteration, chunk_id, base_seed = args
    
    # Unpack world snapshot
    width = world_snapshot['width']
    height = world_snapshot['height']
    food_grid = world_snapshot['food_grid']
    obstacle_grid = world_snapshot['obstacle_grid']
    pheromone_grid = world_snapshot['pheromone_grid']
    nest_position = world_snapshot['nest_position']
    
    # Results to return
    updated_ants = []
    food_attempts = []  # (ant_id, x, y)
    pheromone_deposits = []  # (x, y, amount)
    nest_deposits = []  # ant_id that deposited food
    completed_path_lengths = []  # path lengths for completed trips
    
    for ant_state in ant_states:
        ant_id = ant_state['id']
        position = ant_state['position']
        has_food = ant_state['has_food']
        path = ant_state['path']
        
        # Initialize deterministic RNG using same formula as serial mode
        iteration_seed = (ant_id * 100000 + iteration) % (2**31)
        ant_rng = random.Random(iteration_seed)
        
        # Get valid neighbors
        x, y = position
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height and not obstacle_grid[ny][nx]:
                    neighbors.append((nx, ny))
        
        if not neighbors:
            # Stuck, don't move
            updated_ants.append(ant_state)
            continue
        
        # Movement logic
        if has_food:
            target = nest_position
        else:
            target = None
        
        # Calculate probabilities
        probabilities = []
        for nx, ny in neighbors:
            pheromone = pheromone_grid[ny][nx] + 0.01
            
            if target:
                distance = ((nx - target[0])**2 + (ny - target[1])**2)**0.5 + 0.01
                heuristic = 1.0 / distance
            else:
                heuristic = 1.0
            
            prob = (pheromone ** config.ALPHA) * (heuristic ** config.BETA)
            probabilities.append(prob)
        
        # Normalize
        total = sum(probabilities)
        if total > 0:
            probabilities = [p / total for p in probabilities]
        else:
            probabilities = [1.0 / len(neighbors)] * len(neighbors)
        
        # Choose next position
        choice_idx = ant_rng.choices(range(len(neighbors)), weights=probabilities, k=1)[0]
        new_position = neighbors[choice_idx]
        if has_food:
            behavior = 'returning'
        elif pheromone_grid[new_position[1]][new_position[0]] > 0:
            behavior = 'following_pheromone'
        else:
            behavior = 'searching'
        
        # Update path if carrying food
        new_path = path.copy()
        if has_food:
            new_path.append(new_position)
        
        # Try to collect food (record attempt)
        if not has_food and food_grid[new_position[1]][new_position[0]] > 0:
            food_attempts.append((ant_id, new_position[0], new_position[1]))
        
        # Try to deposit food at nest
        new_has_food = has_food
        if has_food and new_position == nest_position:
            new_has_food = False
            behavior = 'at_nest'
            nest_deposits.append(ant_id)
            # Record completed path length
            if len(new_path) > 0:
                completed_path_lengths.append(len(new_path))
            # Deposit pheromone along path
            for px, py in new_path:
                pheromone_deposits.append((px, py, config.PHEROMONE_DEPOSIT))
            new_path = []
        
        updated_ants.append({
            'id': ant_id,
            'position': new_position,
            'has_food': new_has_food,
            'path': new_path,
            'behavior': behavior,
        })
    
    return {
        'updated_ants': updated_ants,
        'food_attempts': food_attempts,
        'pheromone_deposits': pheromone_deposits,
        'nest_deposits': nest_deposits,
        'completed_path_lengths': completed_path_lengths,
        'chunk_id': chunk_id
    }


class HybridSimulation:
    """
    Hybrid simulation with persistent ProcessPool across iterations.
    Main process maintains canonical world and ant states.
    """
    
    def __init__(self, simulation, num_processes: int | None = None):
        self.sim = simulation
        self.num_processes = num_processes or config.PROCESSES
        # Create persistent ProcessPool (reused across all iterations)
        self.executor = ProcessPoolExecutor(max_workers=self.num_processes)
    
    def step_parallel(self):
        """Execute one simulation step with parallel ant processing using persistent pool"""
        self.sim.status = 'running'
        # Split ants into chunks
        chunk_size = (len(self.sim.ants) + self.num_processes - 1) // self.num_processes
        ant_chunks = []
        for i in range(0, len(self.sim.ants), chunk_size):
            chunk = self.sim.ants[i:i + chunk_size]
            ant_states = [ant.get_state_dict_full() for ant in chunk]
            ant_chunks.append(ant_states)
        
        # Snapshot world (minimal - just grids)
        world_snapshot = {
            'width': self.sim.world.width,
            'height': self.sim.world.height,
            'food_grid': self.sim.world.food_grid.tolist(),
            'obstacle_grid': self.sim.world.obstacle_grid.tolist(),
            'pheromone_grid': self.sim.world.pheromone_grid.tolist(),
            'nest_position': self.sim.world.nest_position
        }
        
        # Prepare work items
        work_items = [
            (ant_chunks[i], world_snapshot, self.sim.iteration, i, self.sim.seed)
            for i in range(len(ant_chunks))
        ]
        
        # Execute in parallel with explicit barrier using persistent executor
        futures = [self.executor.submit(worker_step_ants, item) for item in work_items]
        
        # Barrier: wait for all futures
        results = []
        for future in futures:
            try:
                result = future.result()  # Propagate exceptions
                results.append(result)
            except Exception as e:
                raise RuntimeError(f"Worker failed during parallel step: {e}")
        
        # Sort results by chunk_id to maintain deterministic order
        results.sort(key=lambda r: r['chunk_id'])
        
        # Merge results deterministically
        all_updated_ants = []
        for result in results:
            all_updated_ants.extend(result['updated_ants'])
        
        # Update ant objects in main simulation
        for i, ant in enumerate(self.sim.ants):
            updated_state = all_updated_ants[i]
            ant.position = updated_state['position']
            ant.has_food = updated_state['has_food']
            ant.path = updated_state['path']
            ant.behavior = updated_state.get('behavior', 'searching')
        
        # Process food collection deterministically (by ant_id order)
        all_food_attempts = []
        for result in results:
            all_food_attempts.extend(result['food_attempts'])
        all_food_attempts.sort(key=lambda x: x[0])  # Sort by ant_id
        
        for ant_id, x, y in all_food_attempts:
            if self.sim.world.collect_food(x, y):
                self.sim.ants[ant_id].has_food = True
                self.sim.ants[ant_id].path = [(x, y)]
                self.sim.ants[ant_id].behavior = 'at_food'
        
        # Process nest deposits deterministically
        all_nest_deposits = []
        for result in results:
            all_nest_deposits.extend(result['nest_deposits'])
        all_nest_deposits.sort()  # Sort by ant_id
        
        for ant_id in all_nest_deposits:
            self.sim.food_collected += 1
            self.sim.total_trips += 1
        
        # Collect completed path lengths from all workers
        for result in results:
            for path_length in result['completed_path_lengths']:
                self.sim.record_completed_path(path_length)
        
        # Merge pheromone deposits deterministically
        all_pheromone_deposits = []
        for result in results:
            all_pheromone_deposits.extend(result['pheromone_deposits'])
        
        for x, y, amount in all_pheromone_deposits:
            self.sim.world.deposit_pheromone(x, y, amount)
        
        # Global pheromone decay (barrier - after all ants processed)
        self.sim.world.decay_pheromones(config.PHEROMONE_DECAY)
        
        self.sim.iteration += 1
    
    def shutdown(self):
        """Shutdown the persistent ProcessPool"""
        if self.executor:
            self.executor.shutdown(wait=True)
