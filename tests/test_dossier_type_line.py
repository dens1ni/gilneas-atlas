"""Compact dossier type line without rewritten author records."""
import functools
import json
import os
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(os.environ.get('GILNEAS_TEST_ROOT', Path(__file__).resolve().parents[1]))
PREFIX = os.environ.get('GILNEAS_TEST_PREFIX', '/')
OUT = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-dossier-subtitles-evidence')

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass

class DossierTypeLine(unittest.TestCase):
    def test_every_dossier_uses_only_capital_or_type_label_without_author_subtitles(self):
        directory = ROOT.parent if PREFIX != '/' else ROOT
        server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(directory)))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        OUT.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(args=['--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows'])
                page = browser.new_page(viewport={'width':1440,'height':1000}, reduced_motion='reduce')
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('response', lambda response: errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
                page.goto(f'http://127.0.0.1:{server.server_port}' + PREFIX, wait_until='domcontentloaded')
                page.wait_for_function('window.gilneasApp?.ready', polling=50, timeout=25000)
                before = page.evaluate('window.gilneasApp.getData()')
                rows = []
                for location in before['locations']:
                    page.evaluate('id=>window.gilneasApp.selectId(id)', location['id'])
                    expected = 'Столица' if location.get('capital') else page.locator('#dossier-type').text_content()
                    self.assertEqual(page.locator('#dossier-subtitle').text_content(), expected, location['id'])
                    self.assertEqual(page.locator('#dossier-title').text_content(), location['name'])
                    self.assertEqual(page.locator('#dossier-description').text_content(), location.get('description') or '')
                    self.assertEqual(page.locator('#dossier-owner').text_content(), location.get('owner') or 'Не установлен')
                    rows.append({'id':location['id'], 'caption':expected})
                self.assertEqual(len(rows), len(before['locations']))
                self.assertEqual(len({row['id'] for row in rows}), len(rows))
                for location_id in ['gilneas-city','dalaran-city','lordaeron-city','ambermill']:
                    page.evaluate('id=>window.gilneasApp.selectId(id)', location_id)
                    page.screenshot(path=str(OUT / (location_id + '.png')))
                self.assertEqual(page.evaluate('window.gilneasApp.getData()'), before)
                self.assertIsNone(page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
                self.assertEqual(errors, [])
                (OUT/'verified-dossiers.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
                browser.close()
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

if __name__ == '__main__': unittest.main()
