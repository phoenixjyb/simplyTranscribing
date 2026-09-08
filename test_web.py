"""HTTP acceptance checks against an isolated temporary queue, with real ffprobe."""
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import wave


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        for directory in ('jobs', 'input', 'output'):
            (cls.root / directory).mkdir()
        (cls.root / 'web-config.json').write_text(json.dumps(dict(allowed_logins=['family@example.test'], admin_token='test-only-token')))
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            cls.port = s.getsockname()[1]
        cls.base = f'http://127.0.0.1:{cls.port}'
        cls.server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'web:app', '--host', '127.0.0.1', '--port', str(cls.port), '--no-access-log'], env=dict(os.environ, TRANSCRIBER_ROOT=str(cls.root)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + '/health', timeout=1).close()
                return
            except OSError:
                time.sleep(.05)
        raise RuntimeError('Test server failed to start')

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait(timeout=10)
        cls.temp.cleanup()

    def request(self, path, data=None, headers=None, auth=True):
        h = {'X-Transcriber-Admin': 'test-only-token'} if auth else {}
        h.update(headers or {})
        req = urllib.request.Request(self.base + path, data=data, headers=h)
        try:
            response = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as exc:
            response = exc
        return response.status, response.read()

    def test_access_and_csrf(self):
        self.assertEqual(self.request('/api/jobs', auth=False)[0], 403)
        self.assertEqual(self.request('/api/jobs', auth=False, headers={'Tailscale-User-Login': 'stranger@example.test'})[0], 403)
        self.assertEqual(self.request('/api/jobs', auth=False, headers={'Tailscale-User-Login': 'family@example.test'})[0], 200)
        self.assertEqual(self.request('/api/jobs', b'x')[0], 403)
        self.assertEqual(self.request('/api/jobs', b'x', {'X-Transcriber-Request': '1', 'Origin': 'https://evil.example'})[0], 403)

    def test_bad_media_and_size(self):
        headers = {'X-Transcriber-Request': '1'}
        self.assertEqual(self.request('/api/jobs?filename=bad.mp3', b'not audio', headers)[0], 422)
        self.assertEqual(self.request('/api/jobs?filename=empty.wav', b'', headers)[0], 400)
        self.assertEqual(self.request('/api/jobs?language=invalid', b'bad', headers)[0], 422)
        headers['Content-Length'] = str(3 * 1024**3)
        self.assertEqual(self.request('/api/jobs', b'x', headers)[0], 413)
        self.assertFalse(list((self.root / 'input').glob('*.part')))

    def test_valid_upload_and_progress(self):
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
            w.writeframes(b'\0\0' * 16000)
        status, body = self.request('/api/jobs?filename=test.wav&title=Acceptance&language=en', buf.getvalue(), {'X-Transcriber-Request': '1'})
        self.assertEqual(status, 202, body)
        item = json.loads(body)
        job_id = item['id']
        queue = self.root / 'jobs' / (job_id + '.json')
        job = json.loads(queue.read_text())
        self.assertTrue(Path(job['input']).is_file())
        self.assertEqual(job['status'], 'queued')
        job.update(status='running', started_at=time.time())
        queue.write_text(json.dumps(job))
        out = self.root / 'output' / job_id
        out.mkdir()
        (out / 'run.json').write_text(json.dumps(dict(complete=False, duration_seconds=1, last_segment_end=1, segment_count=1)))
        status, body = self.request('/api/jobs/' + job_id)
        self.assertEqual(json.loads(body)['progress'], 99)
        self.assertEqual(self.request(f'/api/jobs/{job_id}/download/txt')[0], 409)
        job.update(status='completed', finished_at=time.time())
        queue.write_text(json.dumps(job))
        (out / 'run.json').write_text(json.dumps(dict(complete=True, duration_seconds=1)))
        (out / 'transcript.json').write_text(json.dumps(dict(metadata={'input': '/secret/path'}, segments=[dict(start=0,end=1,text='<script>hello</script>')])))
        (out / 'transcript.txt').write_text('hello')
        self.assertEqual(json.loads(self.request('/api/jobs/' + job_id)[1])['progress'], 100)
        self.assertEqual(self.request(f'/api/jobs/{job_id}/download/txt'), (200, b'hello'))
        self.assertNotIn(b'/secret/path', self.request(f'/api/jobs/{job_id}/download/json')[1])
        self.assertEqual(self.request(f'/api/jobs/{job_id}/download/py')[0], 404)
        self.assertEqual(self.request('/api/jobs/not-a-job')[0], 404)


if __name__ == '__main__':
    unittest.main(verbosity=2)
