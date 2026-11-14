"""Gilneas uses the existing plain shield with only the old emblem."""
import functools
import http.server
import threading
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHIELD = 'assets/ui/gilneas-royal-shield.svg'

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

class OldCrest(unittest.TestCase):
    def test_plain_shield_replaces_full_banner_in_every_identity(self):
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.wait_for_function('window.gilneasApp?.ready')
                self.assertEqual(page.locator('.brand img').get_attribute('src'), SHIELD,
                                 'Use the earlier plain shield, not the whole banner on a white card')
                self.assertEqual(page.locator('link[rel=icon]').get_attribute('href'), SHIELD)
                self.assertEqual(page.locator('link[rel=icon]').get_attribute('type'), 'image/svg+xml')
                self.assertEqual(page.evaluate('window.gilneasApp.getData().meta.gilneasCrest'), SHIELD)
                for selector in ['.brand img', '.registry-footer img', '#mobile-home img', '#map-home img',
                                 '#faction-list .faction-row[data-faction-id=gilneas] img',
                                 '#location-list .faction-tree[data-faction-id=gilneas] .group-heading img']:
                    image = page.locator(selector).first
                    self.assertEqual(image.get_attribute('src'), SHIELD, selector)
                    self.assertEqual(image.evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgba(0, 0, 0, 0)', selector)
                    self.assertEqual(image.evaluate('e=>getComputedStyle(e).borderTopWidth'), '0px', selector)
                    self.assertEqual(image.evaluate('e=>e.complete&&e.naturalWidth>0'), True, selector)
                page.evaluate("window.gilneasApp.selectId('gilneas-city')")
                seal = page.locator('#dossier-seal .faction-shield')
                self.assertEqual(seal.get_attribute('data-faction-id'), 'greymane')
                self.assertEqual(seal.locator('.shield-device').get_attribute('href'), 'assets/ui/gilneas-royal-symbol.png')
                self.assertEqual(seal.locator('.shield-field').get_attribute('fill'), '#c49b60')
                page.evaluate("window.gilneasApp.nobleDossier.open('noble-darius')")
                self.assertTrue(page.locator('#noble-crest').is_visible())
                self.assertEqual(page.locator('#noble-crest .faction-shield').get_attribute('data-faction-id'), 'crowley')
                self.assertEqual(page.locator('#noble-crest .shield-device').get_attribute('href'), 'assets/ui/gilneas-royal-symbol.png')
                self.assertEqual(page.locator('#noble-crest').evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgba(0, 0, 0, 0)')
                self.assertGreater(page.locator('.paper-rule [data-icon=rose]').count(), 0)
                self.assertEqual(page.locator('img[src*=gilneas-human-banner]').count(), 0)
                self.assertEqual(errors, [])
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

if __name__ == '__main__':
    unittest.main()
