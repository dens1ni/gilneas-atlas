"""Acceptance coverage for the author's numbered thirteen revisions."""
import functools,http.server,json,threading,unittest,os
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_ui_revision import (EXPECTED_LOCATION_IDS, EXPECTED_LOCATIONS, assert_current_canonical_collections, expected_citations)
ROOT=Path(os.environ.get('GILNEAS_TEST_ROOT',str(Path(__file__).resolve().parents[1])))
PREFIX=os.environ.get('GILNEAS_TEST_PREFIX','/')
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-revision-final-evidence')
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
class RevisionComplete(unittest.TestCase):
 def assert_record_evidence(self,page,location):
  expected=EXPECTED_LOCATIONS[location['id']]
  self.assertEqual(location.get('provenance',{}).get('sources',[]),expected['provenance']['sources'],location['id'])
  self.assertEqual(location.get('sources',[]),expected.get('sources',[]),location['id'])
  self.assertEqual(location.get('wowpediaUrl'),expected.get('wowpediaUrl'),location['id'])
  direct=expected_citations(expected)
  # Source archive includes canonical location evidence plus current own-object
  # evidence, all resolved against the frozen typed canonical source ledger.
  archive=list(direct);seen={row['id'] for row in archive}
  for obj in location.get('objects',[]):
   for citation in expected_citations(obj):
    if citation['id'] not in seen:archive.append(citation);seen.add(citation['id'])
  extract="nodes=>nodes.map(node=>({id:node.dataset.sourceId,href:node.getAttribute('href'),number:Number(node.textContent.match(/^\\[(\\d+)\\]/)[1])}))"
  self.assertEqual(page.locator('#dossier-provenance .source-citation').evaluate_all(extract),direct,location['id']+' exact available record citations')
  self.assertEqual(page.locator('#dossier-source-list .source-citation').evaluate_all(extract),archive,location['id']+' exact available archive IDs/hrefs/numbers')
  wow=page.locator('#dossier-provenance a.wowpedia-link')
  self.assertEqual(wow.count(),int(expected.get('wowpediaUrl') is not None),location['id']+' no fabricated Wowpedia link')
  if expected.get('wowpediaUrl') is not None:self.assertEqual(wow.get_attribute('href'),expected['wowpediaUrl'])
 def test_all_locations_hover_links_tree_colors_noble_modal_and_controls(self):
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start();OUT.mkdir(parents=True,exist_ok=True)
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling']);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];bad=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:bad.append([r.status,r.url]) if r.status>=400 else None);page.goto(f'http://127.0.0.1:{server.server_port}'+PREFIX);page.wait_for_function('window.gilneasApp?.ready');data=page.evaluate('window.gilneasApp.getData()');seen=[]
    assert_current_canonical_collections(self,data);self.assertEqual(len(data['locations']),len(EXPECTED_LOCATION_IDS));self.assertEqual(sorted(l['id'] for l in data['locations']),sorted(EXPECTED_LOCATION_IDS));raw=page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")')
    census=json.loads((Path(__file__).resolve().parents[1]/'docs/noble-family-census.json').read_text())
    previous=json.loads((ROOT/'assets/data/publication-v4.json').read_text())
    expected_ids=[noble['id'] for noble in previous['nobles']]+[entry['noble']['id'] for entry in census['additions']]
    self.assertEqual([noble['id'] for noble in data['nobles']],expected_ids)
    for location in data['locations']:
     page.evaluate('(id)=>{const a=window.gilneasApp;a.selectId(id);a.ui.focusLocation(id,false)}',location['id']);self.assertEqual(page.locator('#dossier-title').text_content(),location['name']);self.assertEqual(page.locator('#dossier-description').text_content(),location['description']);self.assert_record_evidence(page,location);self.assertNotIn('Реконструкция',page.locator('#dossier').inner_text());label=page.locator('.map-marker.selected .marker-label');self.assertEqual(label.text_content(),location['name']);seen.append(location['id'])
    self.assertEqual(len(set(seen)),len(EXPECTED_LOCATION_IDS));self.assertEqual(sorted(seen),sorted(EXPECTED_LOCATION_IDS));self.assertEqual(page.evaluate('window.gilneasApp.getData()'),data);self.assertEqual(page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'),raw)
    # Explicit cited canonical case: numeric IDs are original archive numbers.
    page.evaluate("window.gilneasApp.selectId('gilneas-city')");self.assertGreater(page.locator('#dossier-source-list .source-citation').count(),0);self.assert_record_evidence(page,next(l for l in data['locations'] if l['id']=='gilneas-city'));self.assertEqual(page.locator('#dossier-provenance .source-citation[data-source-id=\"1\"]').text_content(),'[1]')
    page.evaluate("const a=window.gilneasApp;a.ui.setPanel('dossier',false);a.ui.setPanel('navigation',false);a.ui.setPanel('layers',false);a.ui.focusLocation('shadowfang',false)");marker=page.locator('.map-marker[data-location-id=shadowfang]');marker.hover();self.assertTrue(page.locator('#marker-tooltip').is_visible());self.assertEqual(page.locator('.tooltip-title').inner_text(),EXPECTED_LOCATIONS['shadowfang']['name']);self.assertIn('Дом Сребролена',page.locator('.tooltip-faction').inner_text());self.assertIn('Королевство Гилнеас',page.locator('.tooltip-sovereign').inner_text());page.screenshot(path=str(OUT/'hover-desktop.png'));page.mouse.move(5,5)
    page.evaluate("window.gilneasApp.ui.setPanel('navigation',true);window.gilneasApp.ui.render()");tree=page.locator('#location-list details[data-faction-id=gilneas]');crowley=tree.locator('details[data-faction-id=crowley]');silver=crowley.locator('details[data-faction-id=silverlaine]');self.assertIn('Барон Сребролен',silver.locator('summary').first.inner_text());self.assertEqual(page.locator('button.location-row').count(),len(EXPECTED_LOCATION_IDS));self.assertEqual(sorted(page.locator('button.location-row').evaluate_all('rows=>rows.map(row=>row.dataset.locationId)')),sorted(EXPECTED_LOCATION_IDS))
    page.locator('#editor-open').click();page.locator('label:has(#editing-enabled)').click();page.locator('[data-close=editor]').click()
    page.evaluate("const d=window.gilneasApp.getData();const l=d.locations.find(l=>l.id==='shadowfang');l.objects.push({id:'acceptance-building',name:'Проверочная кузница',type:'building',faction:'crowley',owner:'Дариус Краули',modifiers:[{id:'acceptance-bonus',kind:'bonus',text:'+1 снабжение'},{id:'acceptance-penalty',kind:'penalty',text:'−1 казна'}]});window.gilneasApp.replaceData(d);window.gilneasApp.selectId('shadowfang')");card=page.locator('.object-card[data-object-id=acceptance-building]');self.assertEqual(card.locator('summary .object-faction-badge').inner_text(),'Дом Краули');self.assertEqual(card.evaluate('e=>e.style.getPropertyValue("--object-color")'),'#639096');self.assertEqual(page.locator('#dossier').evaluate('e=>e.style.getPropertyValue("--dossier-faction-color")'),'#93a798');card.locator('summary').click();self.assertNotEqual(card.locator('.bonus').evaluate('e=>getComputedStyle(e).color'),card.locator('.penalty').evaluate('e=>getComputedStyle(e).color'));page.wait_for_timeout(550);page.screenshot(path=str(OUT/'dossier-desktop.png'))
    page.evaluate("window.gilneasApp.ui.setPanel('navigation',true)");page.locator('#filter-nobles').click();page.locator('button.noble-row[data-noble-id=noble-darius]').click();self.assertTrue(page.locator('#noble-dossier').is_visible());self.assertIn('Генн Седогрив',page.locator('#noble-suzerain').inner_text());self.assertIn('Проверочная кузница',page.locator('#noble-holdings').inner_text());self.assertIn(EXPECTED_LOCATIONS['shadowfang']['name'],page.locator('#noble-holdings').inner_text());page.screenshot(path=str(OUT/'noble-desktop.png'));page.mouse.click(3,3);self.assertTrue(page.locator('#noble-dossier').is_hidden())
    for width,height in [(390,844),(360,780),(844,390)]:
     page.set_viewport_size({'width':width,'height':height});page.evaluate("window.gilneasApp.selectId('shadowfang');window.gilneasApp.ui.focusLocation('shadowfang',false)");page.wait_for_timeout(400);tools=page.locator('.zoom-tools').bounding_box();dossier=page.locator('#dossier').bounding_box();overlap=max(0,min(tools['x']+tools['width'],dossier['x']+dossier['width'])-max(tools['x'],dossier['x']))*max(0,min(tools['y']+tools['height'],dossier['y']+dossier['height'])-max(tools['y'],dossier['y']));self.assertEqual(overlap,0,(width,height));self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),width);page.screenshot(path=str(OUT/f'dossier-{width}x{height}.png'))
    self.assertFalse(errors,errors);self.assertFalse(bad,bad);browser.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
