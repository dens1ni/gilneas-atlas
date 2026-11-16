"""Final real-bootstrap Origins acceptance, including every dossier shield."""
import functools,http.server,json,threading,unittest,os
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_ui_revision import (EXPECTED_LOCATION_IDS, assert_current_canonical_collections)
ROOT=Path(os.environ.get('GILNEAS_TEST_ROOT',str(Path(__file__).resolve().parents[1])))
PREFIX=os.environ.get('GILNEAS_TEST_PREFIX','/')
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-origins-final-evidence')

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class OriginsAcceptance(unittest.TestCase):
    def test_all_current_dossiers_share_registry_palette_and_keep_marker_types(self):
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)));threading.Thread(target=server.serve_forever,daemon=True).start();OUT.mkdir(parents=True,exist_ok=True)
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling']);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];bad=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:bad.append([r.status,r.url]) if r.status>=400 else None);page.goto(f'http://127.0.0.1:{server.server_port}'+PREFIX);page.wait_for_function('window.gilneasApp?.ready')
                data=page.evaluate('window.gilneasApp.getData()');self.assertEqual(data['meta']['mapRevision'],'origins-map-v3');assert_current_canonical_collections(self,data);self.assertEqual(len(data['locations']),len(EXPECTED_LOCATION_IDS));self.assertEqual(sorted(l['id'] for l in data['locations']),sorted(EXPECTED_LOCATION_IDS));self.assertEqual(page.locator('#base-map').evaluate('e=>[e.naturalWidth,e.naturalHeight]'),[5289,6822]);self.assertEqual(len(data['territoryGrid']['cells']),62985)
                before=page.locator('.map-marker').evaluate_all("nodes=>nodes.map(e=>[e.dataset.locationId,e.querySelector('svg path').getAttribute('d')])")
                checked=[];factions={f['id']:f for f in data['factions']}
                for location in data['locations']:
                    page.evaluate('id=>window.gilneasApp.selectId(id)',location['id']);shield=page.locator('#dossier-seal .faction-shield');self.assertEqual(shield.count(),1,location['id']);field=location['faction'];expected='#131516' if field=='gilneas' else factions[field].get('heraldry',{}).get('field',factions[field]['color']) if field else '#87918d';self.assertEqual(shield.locator('.shield-field').get_attribute('fill'),expected,location['id']);self.assertEqual(shield.get_attribute('data-faction-id'),field,location['id']);self.assertEqual(page.locator('#dossier').evaluate('e=>getComputedStyle(e).backgroundColor'),page.locator('#navigation').evaluate('e=>getComputedStyle(e).backgroundColor'));self.assertEqual(page.locator('#dossier').evaluate('e=>getComputedStyle(e).backgroundImage'),'none');self.assertEqual(page.locator('#dossier-title').text_content(),location['name']);checked.append(location['id'])
                self.assertEqual(len(set(checked)),len(EXPECTED_LOCATION_IDS));self.assertEqual(sorted(checked),sorted(EXPECTED_LOCATION_IDS));after=page.locator('.map-marker').evaluate_all("nodes=>nodes.map(e=>[e.dataset.locationId,e.querySelector('svg path').getAttribute('d')])");self.assertEqual(after,before)
                for id in ['duskhaven','dalaran-city','gilneas-city','galewatch-lighthouse']:
                    page.evaluate("id=>{const a=window.gilneasApp;a.selectId(id);a.ui.setPanel('navigation',false);a.ui.setPanel('layers',false);a.ui.setPanel('dossier',false);a.ui.focusLocation(id,false)}",id);page.wait_for_timeout(200);page.screenshot(path=str(OUT/(id+'-map.png')))
                page.evaluate("const a=window.gilneasApp;a.selectId('gilneas-city');a.ui.focusLocation('gilneas-city',false);document.getElementById('dossier').scrollTop=0");page.wait_for_timeout(250);page.screenshot(path=str(OUT/'dark-dossier.png'))
                page.locator('#editor-open').click();page.locator('label:has(#editing-enabled)').click();page.locator('[data-close=editor]').click()
                page.locator('#dossier').evaluate('e=>e.scrollTop=e.scrollHeight');page.locator('#dossier-edit').click();self.assertTrue(page.locator('#location-editor').is_visible());page.locator('[data-close=location-editor]').click()
                page.evaluate("window.gilneasApp.nobleDossier.open('noble-darius')");page.locator('#noble-dossier').evaluate('e=>e.scrollTop=e.scrollHeight');last=page.locator('#noble-sources .noble-source').last;self.assertTrue(last.is_visible());head=page.locator('#noble-dossier>.dialog-head').bounding_box();dialog=page.locator('#noble-dossier').bounding_box();self.assertAlmostEqual(head['y'],dialog['y']+2,delta=2);page.locator('[data-close=noble-dossier]').click();self.assertTrue(page.locator('#noble-dossier').is_hidden())
                for width,height in [(390,844),(844,390)]:
                    page.set_viewport_size({'width':width,'height':height});page.evaluate("window.gilneasApp.selectId('duskhaven');document.getElementById('dossier').scrollTop=0");page.wait_for_timeout(250);self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),width);page.screenshot(path=str(OUT/f'dossier-{width}x{height}.png'));page.locator('#dossier').evaluate('e=>e.scrollTop=e.scrollHeight');page.locator('#dossier-edit').click();self.assertTrue(page.locator('#location-editor').is_visible());page.locator('[data-close=location-editor]').click()
                self.assertEqual(errors,[]);self.assertEqual(bad,[]);browser.close()
        finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
