"""The noble modal displays literal text, safe links and live holdings only."""
import functools,http.server,threading,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class NobleSafety(unittest.TestCase):
 def test_script_shaped_text_safe_links_and_snapshot_refresh(self):
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page();page.goto(f'http://127.0.0.1:{server.server_port}/');page.wait_for_function('window.gilneasApp?.ready');page.locator('#editor-open').click();page.locator('label:has(#editing-enabled)').click();page.locator('[data-close=editor]').click();page.evaluate("const d=window.gilneasApp.getData();d.nobles.push({id:'test-person',name:'<img src=x onerror=window.unsafe=1>',title:'Тест',description:'<script>window.unsafe=2</script>',appearance:'<b>Человек</b>',overlord:'Нет',sources:['test-source']});d.sources.push({id:'test-source',title:'Тест',url:'javascript:window.unsafe=3'});window.gilneasApp.replaceData(d);window.gilneasApp.nobleDossier.open('test-person')");self.assertEqual(page.locator('#noble-name').text_content(),'<img src=x onerror=window.unsafe=1>');self.assertEqual(page.locator('#noble-description').text_content(),'<script>window.unsafe=2</script>');self.assertEqual(page.locator('#noble-appearance').text_content(),'<b>Человек</b>');self.assertEqual(page.locator('#noble-sources a').count(),0);self.assertIsNone(page.evaluate('window.unsafe'));self.assertEqual(page.locator('#noble-dossier script').count(),0)
    page.evaluate("const d=window.gilneasApp.getData();d.nobles=d.nobles.filter(n=>n.id!=='test-person');d.sources=d.sources.filter(s=>s.id!=='test-source');window.gilneasApp.replaceData(d)");self.assertTrue(page.locator('#noble-dossier').is_hidden());browser.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
