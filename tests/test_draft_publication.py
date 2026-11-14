"""New release text enriches old drafts while preserving user-owned edits."""
import functools,http.server,json,threading,unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class DraftPublication(unittest.TestCase):
 def test_legacy_full_snapshot_keeps_objects_and_positions_but_adopts_unchanged_lore(self):
  old=json.loads((ROOT/'assets/data/publication-v1.json').read_text()) if (ROOT/'assets/data/publication-v1.json').exists() else json.loads((ROOT/'assets/data/atlas.json').read_text())
  loc=next(l for l in old['locations'] if l['id']=='gilneas-city');old_x=loc['x'];loc['x']+=12;loc['objects'].append({'id':'author-forge','type':'building','name':'Авторская кузница','description':'Мой текст','owner':'','modifiers':[{'id':'author-bonus','kind':'bonus','text':'+5 к снабжению'}]})
  release=json.loads((ROOT/'assets/data/atlas.json').read_text());next(l for l in release['locations'] if l['id']=='gilneas-city')['description']='Проверка новой публикации';release['meta']['publicationRevision']='faction-dossiers-v2-test';release['meta']['gilneasCrest']='assets/ui/rose.svg'
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch();context=browser.new_context();context.add_init_script("localStorage.setItem('gilneas-atlas-draft-v1',"+json.dumps(json.dumps(old,ensure_ascii=False))+')');page=context.new_page();page.route('**/assets/data/atlas.json',lambda route:route.fulfill(content_type='application/json',body=json.dumps(release,ensure_ascii=False)));page.goto(f'http://127.0.0.1:{server.server_port}/');page.wait_for_function('window.gilneasApp?.ready');data=page.evaluate('window.gilneasApp.getData()');result=next(l for l in data['locations'] if l['id']=='gilneas-city');self.assertEqual(result['description'],'Проверка новой публикации','Unchanged lore should adopt the new baseline without resetting the entire draft');self.assertAlmostEqual(result['x'],page.evaluate("async p=>(await import('./assets/js/map-publication.mjs')).projectMapPoint(p,window.gilneasApp.getData().meta.mapRegistration)",[old_x+12,loc['y']])[0],places=7);self.assertEqual(result['objects'],loc['objects']);self.assertEqual(page.evaluate("JSON.parse(localStorage.getItem('gilneas-atlas-draft-v1'))")['locations'],old['locations'],'The original saved draft remains intact until a user edits or exports');context.close();browser.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
