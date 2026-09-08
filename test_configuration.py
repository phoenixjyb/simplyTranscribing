import base64
import json
import os
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch
import importlib.util
_spec = importlib.util.spec_from_file_location("bridge", Path(__file__).parent / "examples/wsl/bridge.py")
bridge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bridge)
from configure_web import configure


class ConfigurationTests(unittest.TestCase):
    def test_direct_ssh_preserves_powershell_param_block(self):
        with patch.dict(os.environ, {'TRANSCRIBER_WINDOWS_ALIAS': 'windows-test'}, clear=True):
            command = bridge.command("param([string]$Name = 'hello')\nWrite-Output $Name")
        self.assertEqual(command[-2], 'windows-test')
        script = base64.b64decode(command[-1].split()[-1]).decode('utf-16le')
        self.assertIn('& {\nparam(', script)

    def test_relay_keeps_quoted_command_intact(self):
        env = dict(TRANSCRIBER_WINDOWS_ALIAS='windows-test', TRANSCRIBER_RELAY_HELPER='/tmp/example relay', TRANSCRIBER_RELAY_PROFILE='example')
        with patch.dict(os.environ, env, clear=True):
            command = bridge.command('Write-Output "quoted"')
        self.assertEqual(command[:2], ['/tmp/example relay', 'example'])
        nested = shlex.split(command[-1])
        self.assertEqual(nested[-2], 'windows-test')
        self.assertTrue(nested[-1].startswith('powershell.exe '))
        with patch.dict(os.environ, {'TRANSCRIBER_WINDOWS_ALIAS': '-oProxyCommand=bad'}, clear=True):
            with self.assertRaises(ValueError):
                bridge.command('test')

    def test_config_update_preserves_token_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            configure(root, ['First@example.test'])
            path = root / 'web-config.json'
            token = json.loads(path.read_text())['admin_token']
            configure(root, ['second@example.test'])
            result = json.loads(path.read_text())
            self.assertEqual(result['admin_token'], token)
            self.assertEqual(result['allowed_logins'], ['second@example.test'])
            if os.name != 'nt':
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                configure(root, [''])
            self.assertEqual(json.loads(path.read_text()), result)


if __name__ == '__main__':
    unittest.main()
