"""A Pages artifact excludes dotfiles; browser ZIP must still work there."""
import functools
import http.server
import json
import shutil
import subprocess
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

class PagesExport(unittest.TestCase):
    def test_browser_export_from_actual_pages_payload_restores_hidden_configs(self):
        workflow = (ROOT / '.github/workflows/deploy-pages.yml').read_text()
        step = workflow.split('      - name: Prepare static publish root\n')[1].split('      - name: Upload Pages artifact')[0]
        script = '\n'.join(line[10:] for line in step.split('        run: |\n')[1].splitlines() if line.strip())
        with tempfile.TemporaryDirectory(prefix='gilneas-pages-export-') as scratch:
            target = Path(scratch) / 'gilneas-atlas'
            subprocess.run(['bash', '-e', '-c', script.replace('_site', json.dumps(str(target)))], cwd=ROOT, check=True)
            for hidden in list(target.iterdir()):
                if hidden.name.startswith('.'):
                    shutil.rmtree(hidden) if hidden.is_dir() else hidden.unlink()
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=scratch))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(args=['--disable-renderer-backgrounding', '--disable-background-timer-throttling'])
                    page = browser.new_page(accept_downloads=True, viewport={'width': 1440, 'height': 1000})
                    errors, bad = [], []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('response', lambda response: bad.append([response.status, response.url]) if response.status >= 400 else None)
                    page.goto(f'http://127.0.0.1:{server.server_port}/gilneas-atlas/')
                    page.wait_for_function('window.gilneasApp?.ready')
                    page.locator('#editor-open').click()
                    with page.expect_download(timeout=10000) as download:
                        page.locator('#export-site').click()
                    archive = Path(scratch) / 'download.zip'
                    download.value.save_as(str(archive))
                    with zipfile.ZipFile(archive) as z:
                        self.assertIsNone(z.testzip())
                        self.assertEqual(z.read('.nojekyll'), b'')
                        self.assertEqual(z.read('.github/workflows/deploy-pages.yml'), (ROOT / '.github/workflows/deploy-pages.yml').read_bytes())
                        manifest = json.loads((ROOT / 'assets/runtime-manifest.json').read_text())
                        for name in manifest:
                            if name == 'assets/data/atlas.json':
                                self.assertEqual(json.loads(z.read(name)), page.evaluate('window.gilneasApp.getData()'))
                            else:
                                self.assertEqual(z.read(name), (ROOT / name).read_bytes(), name)
                    self.assertFalse(errors, errors)
                    self.assertFalse(bad, bad)
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()

if __name__ == '__main__':
    unittest.main()
