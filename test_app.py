import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request


class AppTests(unittest.TestCase):
    def test_local_init_launch_and_clean_shutdown_with_separate_data(self):
        source = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(prefix='transcriber data ') as folder:
            root = Path(folder)
            env = dict(os.environ, TRANSCRIBER_DATA_DIR=folder)
            subprocess.run([sys.executable, str(source / 'app.py'), 'init'], env=env, check=True, stdout=subprocess.DEVNULL)
            self.assertEqual(json.loads((root / 'runtime.json').read_text())['device'], 'cpu')
            self.assertEqual(json.loads((root / 'web-config.json').read_text())['auth_mode'], 'local')
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            with (root / 'test-app.log').open('wb') as log:
                process = subprocess.Popen([sys.executable, str(source / 'app.py'), 'start', '--port', str(port)], env=env, stdout=log, stderr=subprocess.STDOUT)
                try:
                    for _ in range(100):
                        try:
                            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/jobs', timeout=1) as response:
                                data = json.load(response)
                            if data['worker'] == 'ready':
                                break
                        except OSError:
                            pass
                        time.sleep(.1)
                    else:
                        self.fail('App failed to become ready: ' + (root / 'test-app.log').read_text(errors='replace'))
                    self.assertEqual(data['user'], 'Local user')
                    self.assertEqual(data['jobs'], [])
                    (root / '.stop-app').touch()
                    self.assertEqual(process.wait(timeout=20), 0)
                    self.assertEqual(json.loads((root / 'service-health.json').read_text())['status'], 'offline')
                finally:
                    (root / '.stop-app').touch()
                    if process.poll() is None:
                        process.wait(timeout=20)


if __name__ == '__main__':
    unittest.main()
