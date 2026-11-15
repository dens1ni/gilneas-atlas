"""Dossier identity and all collapsed ownership labels stay legible."""
import functools,http.server,json,threading,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class ColoredTextContrast(unittest.TestCase):
 def test_house_label_and_object_badges_keep_exact_color_with_contrasting_background(self):
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1000});page.goto(f'http://127.0.0.1:{server.server_port}/');page.wait_for_function('window.gilneasApp?.ready');page.locator('#editor-open').click();page.locator('label:has(#editing-enabled)').click();page.locator('[data-close=editor]').click();page.evaluate("const a=window.gilneasApp,d=a.getData();d.locations.find(l=>l.id==='shadowfang').objects.push({id:'color-object',name:'Проверка',type:'building',faction:'greymane',modifiers:[]});a.replaceData(d);a.selectId('shadowfang');document.getElementById('dossier').scrollTop=0")
    label=page.locator('#dossier-faction');self.assertEqual(label.text_content(),'Дом Сребролена');self.assertTrue(label.is_visible());self.assertEqual(label.evaluate('e=>getComputedStyle(e).color'),'rgb(147, 167, 152)');badge=page.locator('[data-object-id=color-object] .object-faction-badge');self.assertEqual(badge.evaluate('e=>getComputedStyle(e).color'),'rgb(196, 155, 96)')
    def contrast(selector):
     return page.locator(selector).evaluate('''e=>{const c=getComputedStyle(e);const rgb=s=>(s.match(/[0-9.]+/g)||[]).slice(0,3).map(Number),lum=s=>rgb(s).map(x=>{x/=255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);let parent=e,bg=c.backgroundColor;while((bg==='rgba(0, 0, 0, 0)'||bg==='transparent')&&parent.parentElement){parent=parent.parentElement;bg=getComputedStyle(parent).backgroundColor}const a=lum(c.color),b=lum(bg);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)}''')
    self.assertGreaterEqual(contrast('#dossier-faction'),3,'Faction label must remain readable in its own exact heraldic color');self.assertGreaterEqual(contrast('[data-object-id=color-object] .object-faction-badge'),3,'Colored collapsed badge needs readable background');browser.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
