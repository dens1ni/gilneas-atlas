"""Reconstruction bookkeeping must not interrupt the immersive UI."""
import functools,http.server,threading,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class ImmersivePresentation(unittest.TestCase):
 def test_no_status_control_in_location_editor_or_layers(self):
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page();page.goto(f'http://127.0.0.1:{server.server_port}/');page.wait_for_function('window.gilneasApp?.ready');page.locator('#editor-open').click();page.locator('label:has(#editing-enabled)').click();page.locator('[data-close=editor]').click();page.evaluate("window.gilneasApp.editor.editLocation('shadowfang')");self.assertNotIn('Реконструкция для эпохи',page.locator('#location-editor').inner_text());self.assertTrue(page.locator('#location-confidence').is_hidden(),'Internal historical classification must not be an editing form field');page.locator('[data-close=location-editor]').click();page.evaluate("window.gilneasApp.ui.setPanel('layers',true)");self.assertNotIn('Исторические реконструкции',page.locator('#layers').inner_text());browser.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
