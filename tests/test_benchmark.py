import unittest

from benchmark import _build_configurations, _comparison_series


class TestBenchmarkComparisons(unittest.TestCase):

    def test_configuration_grid_contains_every_combination(self):
        configurations = _build_configurations([1, 3], [2, 4], [100, 200], 25)

        self.assertEqual(len(configurations), 8)
        self.assertEqual(
            {(row['threads'], row['processes'], row['ants'], row['iterations'])
             for row in configurations},
            {
                (threads, processes, ants, 25)
                for threads in (1, 3)
                for processes in (2, 4)
                for ants in (100, 200)
            },
        )

    def test_thread_series_excludes_mismatched_workloads(self):
        results = [
            {'Threads': 1, 'Processes': 2, 'Data': 500, 'Iterations': 100,
             'Seed': 7, 'Run ID': 'run-a', 'Time': 5.0},
            {'Threads': 3, 'Processes': 2, 'Data': 500, 'Iterations': 100,
             'Seed': 7, 'Run ID': 'run-a', 'Time': 4.0},
            {'Threads': 1, 'Processes': 2, 'Data': 1000, 'Iterations': 100,
             'Seed': 7, 'Run ID': 'run-a', 'Time': 9.0},
            {'Threads': 3, 'Processes': 2, 'Data': 1000, 'Iterations': 100,
             'Seed': 7, 'Run ID': 'run-a', 'Time': 8.0},
            {'Threads': 1, 'Processes': 2, 'Data': 500, 'Iterations': 200,
             'Seed': 7, 'Run ID': 'run-a', 'Time': 10.0},
            {'Threads': 1, 'Processes': 3, 'Data': 500, 'Iterations': 100,
             'Seed': 7, 'Run ID': 'run-a', 'Time': 6.0},
            {'Threads': 3, 'Processes': 3, 'Data': 500, 'Iterations': 100,
             'Seed': 7, 'Run ID': 'run-a', 'Time': 5.0},
            {'Threads': 1, 'Processes': 1, 'Data': 500, 'Iterations': 100,
             'Seed': 7, 'Run ID': 'run-a', 'Time': 7.0},
            {'Threads': 5, 'Processes': 2, 'Data': 500, 'Iterations': 300,
             'Seed': 7, 'Run ID': 'run-a', 'Time': 3.0},
        ]

        groups = _comparison_series(results, 'Threads')

        self.assertEqual(len(groups), 3)
        for key, values in groups:
            self.assertEqual(set(values), {1, 3})
        self.assertTrue(any(key[1:3] == (500, 100) for key, _ in groups))
        self.assertFalse(any(5 in values for _, values in groups))

    def test_process_series_excludes_mismatched_thread_counts(self):
        results = [
            {'Threads': 5, 'Processes': 2, 'Data': 1390, 'Iterations': 100,
             'Seed': 9, 'Run ID': 'run-b', 'Time': 3.0},
            {'Threads': 5, 'Processes': 3, 'Data': 1390, 'Iterations': 100,
             'Seed': 9, 'Run ID': 'run-b', 'Time': 2.0},
            {'Threads': 1, 'Processes': 2, 'Data': 1390, 'Iterations': 100,
             'Seed': 9, 'Run ID': 'run-b', 'Time': 4.0},
            {'Threads': 3, 'Processes': 3, 'Data': 1390, 'Iterations': 100,
             'Seed': 9, 'Run ID': 'run-b', 'Time': 2.5},
        ]

        groups = _comparison_series(results, 'Processes')

        self.assertEqual(len(groups), 1)
        key, values = groups[0]
        self.assertEqual(key[0], 5)
        self.assertEqual(values, {2: 3.0, 3: 2.0})


if __name__ == '__main__':
    unittest.main()
