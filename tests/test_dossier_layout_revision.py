"""Selected location labels and camera controls must be unobstructed."""
import functools,http.server,threading,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class DossierLayout(unittest.TestCase):
 def test_camera_controls_are_on_right_and_outside_dossier(self):
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000});page.goto(f'http://127.0.0.1:{server.server_port}/');page.wait_for_function('window.gilneasApp?.ready');page.evaluate("window.gilneasApp.selectId('northern-headlands')");page.wait_for_timeout(550)
    controls=page.locator('.zoom-tools').bounding_box();dossier=page.locator('#dossier').bounding_box();viewport=page.locator('#viewport').bounding_box();self.assertGreater(controls['x'],viewport['x']+viewport['width']*.75,'Camera tools should be at the right edge, not in the middle of the map');self.assertGreaterEqual(controls['y'],dossier['y']+dossier['height']+5,'Limit the dossier height above the tools');self.assertLessEqual(controls['x']+controls['width'],viewport['x']+viewport['width']-10)
    marker=page.locator('.map-marker.selected');label=marker.locator('.marker-label');self.assertEqual(label.text_content(),'Северный каменистый мыс');bbox=label.bounding_box();center=marker.bounding_box();self.assertAlmostEqual(bbox['x']+bbox['width']/2,center['x']+center['width']/2,delta=1)
    edges=label.evaluate('''el=>{const r=el.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(el);const t=range.getBoundingClientRect();return {left:r.left,right:r.right,textLeft:t.left,textRight:t.right,overflow:getComputedStyle(el.parentElement).overflow}}''');self.assertGreaterEqual(edges['textLeft'],edges['left']+4);self.assertLessEqual(edges['textRight'],edges['right']-4);self.assertEqual(edges['overflow'],'visible')
    browser.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
