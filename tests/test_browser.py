from pathlib import Path
import unittest
import threading
import functools
import http.server
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class BrowserSlice(unittest.TestCase):
    def test_real_map_location_opens_parchment_dossier(self):
        self.assertTrue((ROOT / 'index.html').exists(), 'the atlas screen is not implemented')
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={'width':1440,'height':1000})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.wait_for_function('window.gilneasApp?.ready === true')
                self.assertIn('Гилнеас', page.locator('h1').inner_text())
                self.assertGreater(page.locator('#base-map').evaluate('(e)=>e.naturalWidth'), 3247)
                page.locator('#search').fill('Город Гилнеас')
                page.locator('[data-location-id="gilneas-city"]').first.click()
                self.assertTrue(page.locator('#dossier').is_visible())
                self.assertEqual(page.locator('#dossier-title').inner_text(), 'Город Гилнеас')
                self.assertIn('Генн',page.locator('#dossier-owner').inner_text())
                self.assertIn('parchment', page.locator('#dossier').get_attribute('class'))
                self.assertFalse(errors, errors)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

if __name__ == '__main__':
    unittest.main()
