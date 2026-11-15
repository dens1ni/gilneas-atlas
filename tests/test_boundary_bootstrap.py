"""The real app boots the ported Naitroud boundaries without a load-time save."""
import functools,http.server,json,threading,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class BoundaryBootstrap(unittest.TestCase):
 def test_real_bootstrap_and_legacy_import_keep_manual_boundaries(self):
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    b=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling']);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/');page.wait_for_function('window.gilneasApp?.ready');self.assertTrue(page.evaluate('Boolean(window.gilneasApp.boundaries)'), 'Ported boundary controller must be wired into the real bootstrap');data=page.evaluate('window.gilneasApp.getData()');self.assertEqual(len(data['territoryGrid']['cells']),62985);self.assertGreater(page.locator('#boundary-vector path').count(),0);self.assertIsNone(page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')"),'Initialization must not write an author draft')
    page.locator('#editor-open').click();page.locator('label:has(#editing-enabled)').click();page.locator('[data-close=editor]').click()
    page.locator('#editor-open').click();page.locator('#territories-open').click();self.assertTrue(page.locator('#boundary-tools').is_visible());self.assertTrue(page.locator('#territory-editor').is_hidden());page.locator('#boundary-close').click()
    page.evaluate("const d=window.gilneasApp.getData();d.territoryGrid.cells[d.territoryGrid.width*230+105]=0;window.gilneasApp.replaceData(d)");manual=page.evaluate('window.gilneasApp.getData().territoryGrid');page.evaluate("window.gilneasApp.selectId('gilneas-city');window.gilneasApp.ui.zoom(1.1)");self.assertEqual(page.evaluate('window.gilneasApp.getData().territoryGrid'),manual)
    page.reload();page.wait_for_function('window.gilneasApp?.ready');self.assertEqual(page.evaluate('window.gilneasApp.getData().territoryGrid'),manual)
    page.locator('#editor-open').click();page.locator('label:has(#editing-enabled)').click();page.locator('[data-close=editor]').click()
    legacy=page.evaluate('window.gilneasApp.getData()');del legacy['territoryGrid'];page.evaluate("async d=>await window.gilneasApp.importSnapshot(new File([JSON.stringify(d)],'legacy.json',{type:'application/json'}))",legacy);page.evaluate('window.gilneasApp.boundaries.whenReady()');self.assertEqual(len(page.evaluate('window.gilneasApp.getData().territoryGrid.cells')),62985);self.assertGreater(page.locator('#boundary-vector path').count(),0);self.assertFalse(errors,errors);b.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
