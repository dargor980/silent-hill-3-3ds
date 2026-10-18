import unittest
from capacity import budgeted_size


class CapacityTests(unittest.TestCase):
    def test_index_reservation(self):
        self.assertEqual(budgeted_size('a/CompilationCache.noindex/generic/v1.1/v8.index', 8*1024**3, 16384), (16384, True))

    def test_data_growth_is_charged(self):
        self.assertEqual(budgeted_size('a/CompilationCache.noindex/generic/v1.1/v8.data', 16*1024**3, 5*1024**3), (5*1024**3, True))

    def test_ordinary_sparse_file_is_not_exempt(self):
        self.assertEqual(budgeted_size('payload.bin', 8*1024**3, 16384), (8*1024**3, False))

    def test_name_without_full_location_is_not_exempt(self):
        self.assertEqual(budgeted_size('v8.index', 8*1024**3, 16384), (8*1024**3, False))

    def test_unexpected_size_is_not_exempt(self):
        self.assertEqual(budgeted_size('CompilationCache.noindex/generic/v1.1/v8.index', 9*1024**3, 16384), (9*1024**3, False))

    def test_allocation_is_never_discounted(self):
        self.assertEqual(budgeted_size('small.o', 100, 4096), (4096, False))

    def test_fully_allocated_reservation(self):
        self.assertEqual(budgeted_size('CompilationCache.noindex/generic/v1.1/v8.index', 8*1024**3, 8*1024**3), (8*1024**3, False))


if __name__ == '__main__':
    unittest.main()
