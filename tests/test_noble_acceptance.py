"""All registered nobles stay readable with reachable modal controls."""
import functools,http.server,threading,unittest,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class NobleAcceptance(unittest.TestCase):
 def test_every_noble_has_safe_readable_dossier_and_sticky_close_at_all_sizes(self):
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling']);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/');page.wait_for_function('window.gilneasApp?.ready');data=page.evaluate('window.gilneasApp.getData()');collected=[]
    for noble in data['nobles']:
     page.evaluate('(id)=>window.gilneasApp.nobleDossier.open(id)',noble['id']);self.assertEqual(page.locator('#noble-name').text_content(),noble['name']);self.assertTrue(page.locator('#noble-description').text_content());self.assertTrue(page.locator('#noble-appearance').text_content());self.assertTrue(page.locator('#noble-social-status').text_content());self.assertTrue(page.locator('#noble-suzerain').text_content());self.assertGreater(page.locator('#noble-sources a').count(),0);collected.append(noble['id']);page.locator('[data-close=noble-dossier]').click()
    self.assertEqual(set(collected),{n['id'] for n in data['nobles']});self.assertEqual(len(collected),len(data['nobles']))
    for width,height in [(1440,1000),(390,844),(360,780),(844,390)]:
     page.set_viewport_size({'width':width,'height':height});page.wait_for_function("parseInt(getComputedStyle(document.documentElement).getPropertyValue('--app-height'))===innerHeight");page.evaluate("window.gilneasApp.nobleDossier.open('noble-darius')");dialog=page.locator('#noble-dossier');head=dialog.locator('.dialog-head');before=head.bounding_box();dialog.evaluate('(e)=>e.scrollTop=e.scrollHeight');page.wait_for_timeout(40);after=head.bounding_box();self.assertAlmostEqual(after['y'],before['y'],delta=1);self.assertLessEqual(dialog.evaluate('(e)=>e.scrollWidth'),dialog.evaluate('(e)=>e.clientWidth')+1);page.locator('[data-close=noble-dossier]').click();self.assertTrue(dialog.is_hidden())
    self.assertFalse(errors,errors);browser.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
