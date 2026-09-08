from types import SimpleNamespace
import unittest
from unittest.mock import patch
import runtime
from settings import DEFAULTS


class RuntimeTests(unittest.TestCase):
    def args(self, **updates):
        return SimpleNamespace(**{**DEFAULTS, **updates})

    def backend(self, count=0, types=('int8', 'float32')):
        return SimpleNamespace(get_cuda_device_count=lambda: count, get_supported_compute_types=lambda *args: set(types))

    def test_cpu_never_queries_cuda_driver(self):
        with patch.object(runtime, 'cuda_state', side_effect=AssertionError('GPU touched')):
            result = runtime.resolve_runtime(self.args(), self.backend())
        self.assertEqual((result['device'], result['compute_type']), ('cpu', 'int8'))

    def test_auto_without_cuda_selects_cpu(self):
        self.assertEqual(runtime.resolve_runtime(self.args(device='auto'), self.backend())['device'], 'cpu')

    def test_cpu_compute_fallback_and_validation(self):
        self.assertEqual(runtime.resolve_runtime(self.args(), self.backend(types=['float32']))['compute_type'], 'float32')
        with self.assertRaises(ValueError):
            runtime.resolve_runtime(self.args(compute_type='float16'), self.backend())

    def test_any_cuda_device_with_admission(self):
        with patch.object(runtime, 'cuda_state', return_value=dict(free_mib=2048, utilization=0)) as state:
            result = runtime.resolve_runtime(self.args(device='cuda', device_index=1), self.backend(2, ['float16']))
            state.assert_called_once_with(1)
        self.assertEqual(result['device_index'], 1)
        self.assertEqual(result['compute_type'], 'float16')

    def test_cuda_busy_does_not_silently_fall_back(self):
        for free, utilization in [(500, 0), (2048, 80)]:
            with patch.object(runtime, 'cuda_state', return_value=dict(free_mib=free, utilization=utilization)):
                with self.assertRaises(RuntimeError):
                    runtime.resolve_runtime(self.args(device='auto'), self.backend(1, ['float16']))
        with self.assertRaises(RuntimeError):
            runtime.resolve_runtime(self.args(device='cuda'), self.backend())


if __name__ == '__main__':
    unittest.main()
