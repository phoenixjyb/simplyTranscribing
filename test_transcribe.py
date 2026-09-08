import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import transcribe as t

class Exports(unittest.TestCase):
    def test_srt_carries(self):
        self.assertEqual(t.stamp(59.9996), '00:01:00,000')
        self.assertEqual(t.stamp(3599.9996), '01:00:00,000')

    def test_rejects_invalid_timeline(self):
        for start, end in [(3, 2), (-1, 1), (1, 20), (float('nan'), 2)]:
            with self.assertRaises(ValueError):
                t.validate([dict(start=start, end=end)], 10)

    def test_exports_consistent(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            segments = [dict(start=0.1, end=1.2, text=' Hello world.'), dict(start=2, end=3, text=' Second sentence.')]
            t.export(out, segments, dict(input='sample.mp3', duration_seconds=3))
            self.assertEqual(len(json.loads((out / 'transcript.json').read_text())['segments']), 2)
            self.assertEqual((out / 'transcript.srt').read_text().count(' --> '), 2)
            self.assertEqual((out / 'transcript.txt').read_text().splitlines(), [s['text'] for s in segments])
            from docx import Document
            self.assertTrue(any('Second sentence.' in p.text for p in Document(out / 'transcript.docx').paragraphs))

    def test_interrupted_generator_preserves_partial(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'input.mp3'
            source.write_bytes(b'fixture')
            out = root / 'out'
            def interrupted():
                yield dict(start=0, end=1, text='One retained segment')
                raise KeyboardInterrupt()
            model = SimpleNamespace(transcribe=lambda *a, **k: (interrupted(), SimpleNamespace(language='en', language_probability=1.0, duration_after_vad=3)))
            args = t.parser().parse_args([str(source), '--output-dir', str(out)])
            probe = json.dumps(dict(format=dict(duration='3'), streams=[dict(codec_type='audio')]))
            with patch.object(t, 'ROOT', root), patch.object(t.subprocess, 'check_output', return_value=probe), patch.object(t.importlib.metadata, 'version', return_value='fixture'), patch.object(t, 'resolve_runtime', return_value=dict(device='cpu', device_index=0, compute_type='int8', admission=None)), patch.dict(t.os.environ):
                with self.assertRaises(KeyboardInterrupt):
                    t.run(args, model_factory=lambda *a, **k: model)
            receipt = json.loads((out / 'run.json').read_text())
            self.assertFalse(receipt['complete'])
            self.assertEqual(receipt['status'], 'failed')
            self.assertEqual(receipt['segment_count'], 1)
            self.assertEqual(len((out / 'segments.jsonl').read_text().splitlines()), 1)
            self.assertFalse((out / 'transcript.txt').exists())

if __name__ == '__main__':
    unittest.main()
