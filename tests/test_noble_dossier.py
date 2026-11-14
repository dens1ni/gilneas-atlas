"""The selected noble has an isolated, readable modal dossier."""
import functools,http.server,threading,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class NobleDossier(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=cls.server.serve_forever,daemon=True).start();cls.p=sync_playwright().start();cls.browser=cls.p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling'])
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.p.stop();cls.server.shutdown();cls.server.server_close()
 def test_navigation_opens_centered_noble_only_and_backdrop_discards_it(self):
  page=self.browser.new_page(viewport={'width':1440,'height':1000});page.goto(f'http://127.0.0.1:{self.server.server_port}/');page.wait_for_function('window.gilneasApp?.ready');page.locator('#filter-nobles').click();page.locator('[data-noble-id=noble-darius]').click()
  dialog=page.locator('#noble-dossier');self.assertEqual(dialog.count(),1,'A selected person requires their own modal dossier');self.assertTrue(dialog.is_visible());self.assertEqual(page.locator('#noble-name').inner_text(),'Дариус Краули');self.assertIn('краули',page.locator('#noble-house').inner_text().casefold());self.assertIn('Генн Седогрив',page.locator('#noble-suzerain').inner_text());self.assertTrue(page.locator('#noble-description').inner_text());self.assertTrue(page.locator('#noble-appearance').inner_text());self.assertTrue(page.locator('#noble-social-status').inner_text());self.assertGreater(page.locator('#noble-sources a').count(),0)
  self.assertTrue(page.locator('#chronicle').is_hidden());self.assertIn('Деревня Погребальных Костров',page.locator('#noble-holdings').inner_text());self.assertIn('Янтарная мельница',page.locator('#noble-holdings').inner_text());r=dialog.bounding_box();self.assertAlmostEqual(r['x']+r['width']/2,720,delta=5);self.assertAlmostEqual(r['y']+r['height']/2,500,delta=5)
  page.mouse.click(5,5);self.assertTrue(dialog.is_hidden());page.close()
 def test_chronicle_header_is_first_visible_row_and_old_intro_is_gone(self):
  page=self.browser.new_page(viewport={'width':1440,'height':1000});page.goto(f'http://127.0.0.1:{self.server.server_port}/');page.wait_for_function('window.gilneasApp?.ready');page.locator('#chronicle-open').click();self.assertEqual(page.locator('.chronicle-intro').count(),0,'Remove the obsolete opening paragraph entirely')
  d=page.locator('#chronicle');h=d.locator('.dialog-head');r=d.bounding_box();hr=h.bounding_box();self.assertLessEqual(hr['y']-r['y'],2);self.assertIn('Хроника',h.inner_text());d.evaluate('(e)=>e.scrollTop=e.scrollHeight');page.wait_for_timeout(50);self.assertAlmostEqual(h.bounding_box()['y'],hr['y'],delta=1);page.locator('[data-close=chronicle]').click();self.assertTrue(d.is_hidden());page.close()
if __name__=='__main__':unittest.main()
