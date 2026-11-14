"""Exercise actual map placement and polygon drawing in the integrated app."""
import unittest,json,functools,http.server,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class MapEditingAcceptance(unittest.TestCase):
 def test_real_location_and_polygon_clicks_persist_and_honor_inactive_mask(self):
  srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=srv.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    b=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows']);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{srv.server_port}/');page.wait_for_function('window.gilneasApp?.ready');page.evaluate("window.gilneasApp.ui.setPanel('navigation',false);window.gilneasApp.ui.setPanel('layers',false);window.gilneasApp.ui.home(false)");before=page.evaluate('window.gilneasApp.getData()')
    self.assertFalse(page.evaluate('window.gilneasApp.canPlace([1800,150])'));self.assertFalse(page.evaluate('window.gilneasApp.canPlace([3120,2200])'));self.assertTrue(page.evaluate('window.gilneasApp.canPlace([1800,3370])'))
    page.locator('#editor-open').click();page.locator('#location-create').click()
    cam=page.evaluate('window.gilneasApp.ui.getCamera()');viewport=page.locator('#viewport').bounding_box();pt=[1550,3820];page.mouse.click(viewport['x']+cam['x']+pt[0]*cam['scale'],viewport['y']+cam['y']+pt[1]*cam['scale']);self.assertTrue(page.locator('#location-editor').is_visible());page.locator('#location-name').fill('Тестовая лесная сторожка');page.locator('#location-faction').select_option('crowley');page.locator('#location-form button[type=submit]').click();d=page.evaluate('window.gilneasApp.getData()');l=next(l for l in d['locations'] if l['name']=='Тестовая лесная сторожка');self.assertAlmostEqual(l['x'],pt[0],delta=1/cam['scale']+1);self.assertAlmostEqual(l['y'],pt[1],delta=1/cam['scale']+1);self.assertEqual(d['territories'],before['territories'])
    page.evaluate("window.gilneasApp.ui.setPanel('dossier',false);window.gilneasApp.ui.setPanel('navigation',false);window.gilneasApp.ui.setPanel('layers',false);window.gilneasApp.ui.home(false)")
    page.evaluate('window.gilneasApp.editor.openTerritories()');page.locator('#territory-name').fill('Тестовая область Краули');page.locator('#territory-faction').select_option('crowley');page.locator('#territory-form button[type=submit]').click();cam=page.evaluate('window.gilneasApp.ui.getCamera()');viewport=page.locator('#viewport').bounding_box()
    for x,y in [(1450,3730),(1620,3730),(1620,3910),(1450,3910)]:page.mouse.click(viewport['x']+cam['x']+x*cam['scale'],viewport['y']+cam['y']+y*cam['scale'])
    page.locator('#territory-finish').click();d=page.evaluate('window.gilneasApp.getData()');area=next(t for t in d['territories'] if t['name']=='Тестовая область Краули');self.assertEqual(area['faction'],'crowley');self.assertEqual(len(area['points']),4);self.assertFalse(page.locator('#map-task').is_visible());self.assertEqual(len(d['locations']),len(before['locations'])+1)
    page.reload();page.wait_for_function('window.gilneasApp?.ready');restored=page.evaluate('window.gilneasApp.getData()');self.assertEqual(restored,d)
    page.locator('#editor-open').click();page.locator('#draft-reset').click();page.locator('#confirm-yes').click();self.assertEqual(page.evaluate('window.gilneasApp.getData()'),before);self.assertFalse(errors,errors);b.close()
  finally:srv.shutdown();srv.server_close()
if __name__=='__main__':unittest.main()
