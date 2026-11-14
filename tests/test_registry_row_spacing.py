"""Inherited row ornaments cannot collide with revised registry labels."""
import functools,http.server,threading,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class RegistryRowSpacing(unittest.TestCase):
 def test_row_symbol_stays_left_of_text(self):
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    b=p.chromium.launch();page=b.new_page(viewport={'width':1440,'height':1000});page.goto(f'http://127.0.0.1:{server.server_port}/');page.wait_for_function('window.gilneasApp?.ready');boxes=page.locator('button.location-row').evaluate_all('rows=>rows.map(e=>{const r=e.getBoundingClientRect(),t=e.querySelector(".row-name").getBoundingClientRect(),p=getComputedStyle(e,"::before");return {name:e.textContent,pseudoRight:r.left+parseFloat(p.left)+parseFloat(p.width),textLeft:t.left}})');self.assertTrue(boxes)
    for box in boxes:self.assertLessEqual(box['pseudoRight']+5,box['textLeft'],box)
    b.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
