import unittest,functools,http.server,threading,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class PublicationRegression(unittest.TestCase):
 def test_citation_numbers_match_global_archive_and_unknown_is_not_independence(self):
  handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT));server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    b=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows']);page=b.new_page(viewport={'width':1440,'height':1000})
    # Memory-only full canonical snapshot fixture, not production ownership/lore.
    fixture=json.loads((ROOT/'assets/data/atlas.json').read_text())
    unknown=next(l for l in fixture['locations'] if l['id']=='northern-headlands')
    unknown['faction']=None;unknown['provenance']['affiliationStatus']='unknown'
    unknown['provenance']['note']='Test-only unknown-affiliation and typed-citation fixture — not production'
    typed_source=next(s for s in fixture['sources'] if type(s['id']) is str)
    unknown['provenance']['sources']=list(dict.fromkeys(unknown['provenance'].get('sources',[])+[typed_source['id']]))
    page.route('**/assets/data/atlas.json',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(fixture,ensure_ascii=False)))
    page.goto(f'http://127.0.0.1:{server.server_port}/');page.wait_for_function('window.gilneasApp?.ready')
    before=page.evaluate('window.gilneasApp.getData()');draft=page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")');self.assertIsNone(draft)
    archive=before['sources'];numbers={(type(s['id']),s['id']):s['id'] if type(s['id']) is int else index+1 for index,s in enumerate(archive)}
    self.assertTrue(any(type(s['id']) is int for s in archive));self.assertTrue(any(type(s['id']) is str for s in archive))
    page.locator('#chronicle-open').click();page.locator('#chronicle-sources').click()
    archive_entries=page.locator('#chronicle-content section[id^="source-"]').evaluate_all('(nodes)=>nodes.map(n=>({id:n.id,text:n.querySelector("h3").textContent}))')
    self.assertEqual(archive_entries,[{'id':f"source-{s['id']}",'text':f"[{s['id']}] {s['title']}"} for s in archive],'Global archive must preserve every numeric/string literal source ID')
    page.locator('[data-close="chronicle"]').click()
    page.evaluate("window.gilneasApp.selectId('gilneas-city')")
    links=page.locator('#dossier-provenance .source-citation').evaluate_all('(nodes)=>nodes.map(n=>({id:n.dataset.sourceId,text:n.textContent}))')
    self.assertTrue(links)
    city=next(l for l in before['locations'] if l['id']=='gilneas-city');city_ids=list(dict.fromkeys(city.get('provenance',{}).get('sources',[])+city.get('sources',[])))
    self.assertEqual([link['id'] for link in links],[str(id) for id in city_ids])
    for id,link in zip(city_ids,links):self.assertEqual(link['text'],f"[{numbers[(type(id),id)]}]",'Dossier and archive must use the same source number')
    # Exercise both actual numeric and string source IDs without renumbering data.
    string_location=next(l for l in before['locations'] if l['id']=='northern-headlands')
    page.evaluate('(id)=>window.gilneasApp.selectId(id)',string_location['id'])
    typed_ids=list(dict.fromkeys(string_location.get('provenance',{}).get('sources',[])+string_location.get('sources',[])))
    typed_links=page.locator('#dossier-provenance .source-citation').evaluate_all('(nodes)=>nodes.map(n=>({id:n.dataset.sourceId,text:n.textContent}))')
    self.assertEqual([link['id'] for link in typed_links],[str(id) for id in typed_ids])
    for id,link in zip(typed_ids,typed_links):self.assertEqual(link['text'],f"[{numbers[(type(id),id)]}]",'Typed IDs must retain their global archive numbers')
    page.evaluate("window.gilneasApp.selectId('northern-headlands')")
    self.assertEqual(page.locator('#dossier-sovereign').inner_text(),'Не установлено','Unknown political tenure must not become confirmed independence')
    page.evaluate("window.gilneasApp.selectId('gilneas-city')")
    self.assertEqual(page.locator('#dossier-provenance .confidence').count(),0,'Historical bookkeeping stays in data, not the visible card')
    self.assertEqual(page.evaluate('window.gilneasApp.getData()'),before);self.assertEqual(page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'),draft)
    self.assertEqual(page.evaluate('window.gilneasApp.getData().sources'),archive,'Global archive records and exact ID types must remain unchanged')
    b.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
