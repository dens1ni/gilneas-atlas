"""The header carries the author's 10/100 wall-construction track."""
import functools
import http.server
import threading
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
class WallProgress(unittest.TestCase):
    def test_progress_header_is_visible_and_exact_at_desktop_portrait_landscape(self):
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch()
                page=browser.new_page()
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                for width,height in [(1440,1000),(1000,900),(390,844),(360,780),(844,390)]:
                    page.set_viewport_size({'width':width,'height':height})
                    progress=page.locator('#wall-progress')
                    self.assertEqual(progress.count(),1,'Wall construction must have a visible progress widget')
                    self.assertTrue(progress.is_visible(),(width,height))
                    self.assertEqual(progress.get_attribute('value'),'10')
                    self.assertEqual(progress.get_attribute('max'),'100')
                    self.assertEqual(page.locator('#wall-progress-value').inner_text(),'10 / 100')
                    self.assertIn('Строительство Стены Седогрива',page.locator('.era').inner_text())
                    self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),width)
                    box=progress.bounding_box();header=page.locator('.topbar').bounding_box()
                    self.assertLessEqual(box['y']+box['height'],header['y']+header['height']+1)
                browser.close()
        finally:
            server.shutdown();server.server_close()
if __name__=='__main__': unittest.main()
