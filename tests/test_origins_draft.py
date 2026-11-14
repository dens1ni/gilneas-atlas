"""The published Origins map migrates an old author draft without saving it."""
import functools,http.server,json,threading,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class OriginsDraft(unittest.TestCase):
    def test_previous_full_draft_keeps_objects_and_moved_points_on_new_map(self):
        old=json.loads((ROOT/'assets/data/publication-v2.json').read_text())
        city=next(l for l in old['locations'] if l['id']=='gilneas-city')
        city['objects']=[{'id':'origins-author-forge','type':'building','name':'Авторская кузница','description':'Мой объект','owner':'','faction':None,'modifiers':[{'id':'origins-author-bonus','kind':'bonus','text':'+5 снабжение'}]}]
        town=next(l for l in old['locations'] if l['id']=='pyrewood');town['x']+=8
        raw=json.dumps(old,ensure_ascii=False)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling']);context=browser.new_context();context.add_init_script("if(!localStorage.getItem('gilneas-atlas-draft-v1'))localStorage.setItem('gilneas-atlas-draft-v1',"+json.dumps(raw)+')')
                page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(f'http://127.0.0.1:{server.server_port}/');page.wait_for_function('window.gilneasApp?.ready')
                data=page.evaluate('window.gilneasApp.getData()')
                self.assertEqual(data['meta']['mapRevision'],'origins-map-v3')
                self.assertEqual([data['meta']['width'],data['meta']['height']],[3526,4548])
                result=next(l for l in data['locations'] if l['id']=='gilneas-city');self.assertEqual(result['objects'],city['objects'])
                baseline=json.loads((ROOT/'assets/data/atlas.json').read_text());reviewed=next(l for l in baseline['locations'] if l['id']=='gilneas-city');self.assertEqual([result['x'],result['y']],[reviewed['x'],reviewed['y']])
                projected=page.evaluate("async point=>(await import('./assets/js/map-publication.mjs')).projectMapPoint(point,window.gilneasApp.getData().meta.mapRegistration)",[town['x'],town['y']]);placed=next(l for l in data['locations'] if l['id']=='pyrewood');self.assertAlmostEqual(placed['x'],projected[0],places=7);self.assertAlmostEqual(placed['y'],projected[1],places=7)
                self.assertEqual(page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')"),raw)
                self.assertEqual(page.locator('#base-map').evaluate('e=>[e.naturalWidth,e.naturalHeight]'),[5289,6822])
                self.assertEqual(errors,[]);context.close();browser.close()
        finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
