import unittest,threading,functools,http.server,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class ConsoleLayout(unittest.TestCase):
 def test_house_and_territory_fields_stay_inside_their_dialog_at_all_breakpoints(self):
  srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=srv.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    b=p.chromium.launch();page=b.new_page();page.goto(f'http://127.0.0.1:{srv.server_port}/');page.wait_for_function('window.gilneasApp?.ready')
    for width,height in [(1440,1000),(390,844),(360,780),(844,390)]:
     page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(80)
     for dialog,method in [('houses-editor','openHouses'),('territory-editor','openTerritories')]:
      page.evaluate(f'window.gilneasApp.editor.{method}()');page.wait_for_timeout(60)
      boxes=page.locator('#'+dialog).evaluate('''d=>{const r=d.getBoundingClientRect();return {dialog:{left:r.left,right:r.right},scrollWidth:d.scrollWidth,clientWidth:d.clientWidth,fields:[...d.querySelectorAll('input:not([type=hidden]),select,textarea,button')].map(e=>{const b=e.getBoundingClientRect();return {id:e.id||e.getAttribute('aria-label'),left:b.left,right:b.right,width:b.width}})}}''')
      self.assertLessEqual(boxes['scrollWidth'],boxes['clientWidth']+1,(width,height,dialog,boxes))
      for field in boxes['fields']:
       if field['width']:self.assertLessEqual(field['right'],boxes['dialog']['right']-3,(width,height,dialog,field))
      page.locator(f'[data-close="{dialog}"]').click()
    b.close()
  finally:srv.shutdown();srv.server_close()
if __name__=='__main__':unittest.main()
