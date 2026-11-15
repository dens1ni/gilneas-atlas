"""Canonical location links through the real parent bootstrap and native controls."""
import functools
import json
import os
import threading
import unittest
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(os.environ.get('GILNEAS_TEST_ROOT',str(Path(__file__).resolve().parents[1])))
PREFIX=os.environ.get('GILNEAS_TEST_PREFIX','/')
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-location-links-evidence')
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
class LinkedLocations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory=ROOT.parent if PREFIX!='/' else ROOT
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(directory)))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'+PREFIX
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows'])
        OUT.mkdir(parents=True,exist_ok=True)
    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.playwright.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2)
    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        self.page=self.context.new_page();self.page.set_default_timeout(15000);self.errors=[]
        self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.page.on('console',lambda msg:self.errors.append(msg.text) if msg.type=='error' else None)
        self.page.on('response',lambda r:self.errors.append(f'{r.status} {r.url}') if r.status>=400 else None)
    def tearDown(self): self.context.close()
    def boot(self,data=None):
        if data is not None:
            self.page.route('**/assets/data/atlas.json',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(data,ensure_ascii=False)))
        self.page.goto(self.url,wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready',polling=50)
        self.page.wait_for_function('document.querySelector("#base-map").complete&&document.querySelector("#base-map").naturalWidth>0',polling=50)
    def test_container_frames_preserve_all_original_type_icons_and_marker_anchors(self):
        data=json.loads((ROOT/'assets/data/atlas.json').read_text())
        for location in data['locations']:
            location.pop('isLocation',None);location.pop('linkedLocationIds',None)
        self.boot(data)
        prepared=self.page.evaluate('window.gilneasApp.getData()')
        glyphs=self.page.locator('#markers .map-marker').evaluate_all('nodes=>nodes.map(e=>({id:e.dataset.locationId,path:e.querySelector("svg path").getAttribute("d"),viewBox:e.querySelector("svg").getAttribute("viewBox"),x:e.style.left,y:e.style.top}))')
        for location in data['locations']:
            if location['id']=='military-district':location.update(isLocation=True,linkedLocationIds=['stoneward-prison'])
        expected=json.loads(json.dumps(prepared))
        next(location for location in expected['locations'] if location['id']=='military-district').update(isLocation=True,linkedLocationIds=['stoneward-prison'])
        self.page.unroute('**/assets/data/atlas.json');self.boot(data)
        marker=self.page.locator('#markers .map-marker[data-location-id="military-district"]')
        self.assertIn('location-container',marker.get_attribute('class'),'Локация needs its own frame independent of the type icon')
        self.assertEqual(self.page.locator('#markers .location-container').count(),1)
        current=self.page.locator('#markers .map-marker').evaluate_all('nodes=>nodes.map(e=>({id:e.dataset.locationId,path:e.querySelector("svg path").getAttribute("d"),viewBox:e.querySelector("svg").getAttribute("viewBox"),x:e.style.left,y:e.style.top}))')
        self.assertEqual(current,glyphs)
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),expected)
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData().locations'),data['locations'])
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData().nobles'),data['nobles'])
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertEqual(self.errors,[])
    def test_canonical_link_and_return_keep_child_affiliation_and_effects_at_the_actual_map_record(self):
        data=json.loads((ROOT/'assets/data/atlas.json').read_text())
        district=next(l for l in data['locations'] if l['id']=='military-district')
        prison=next(l for l in data['locations'] if l['id']=='stoneward-prison')
        district.update(isLocation=True,linkedLocationIds=['stoneward-prison'])
        prison['objects']=[{'id':'test-prison-supply','type':'resource','name':'Поставка для тюрьмы','description':'  Причина тюремного бонуса  ','owner':'','amount':0,'modifiers':[{'id':'test-prison-bonus','kind':'bonus','text':'  Бонус фракции тюрьмы +1  '},{'id':'test-prison-penalty','kind':'penalty','text':'  Штраф фракции тюрьмы −1  '}]}]
        self.boot(data)
        before=self.page.evaluate('window.gilneasApp.getData()')
        raw=json.dumps(before,ensure_ascii=False,indent=3)+'\n'
        self.page.evaluate('raw=>localStorage.setItem("gilneas-atlas-draft-v1",raw)',raw)
        self.page.locator('#search').fill('Военный квартал')
        self.page.locator('#location-list button[data-location-id="military-district"]').click()
        row=self.page.locator('#dossier-location-links button[data-location-link="stoneward-prison"]')
        self.assertEqual(row.count(),1)
        self.assertIn(prison['name'],row.inner_text())
        self.assertNotIn('Бонус фракции тюрьмы',self.page.locator('#dossier').inner_text(),'Parent renders a reference, not a copied child/effect dossier')
        self.assertTrue(self.page.locator('#dossier-body .composition').is_hidden(),'An empty container uses canonical references rather than inline copied objects')
        row.click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),'stoneward-prison')
        self.assertEqual(self.page.locator('#dossier-title').inner_text(),prison['name'])
        self.assertEqual(self.page.locator('#dossier-faction').text_content(),next(f['name'] for f in data['factions'] if f['id']==prison['faction']))
        card=self.page.locator('#dossier-objects [data-object-id="test-prison-supply"]')
        card.locator('summary').click()
        self.assertEqual(card.locator('.modifier.bonus').text_content(),'  Бонус фракции тюрьмы +1  ')
        self.assertEqual(card.locator('.modifier.penalty').text_content(),'  Штраф фракции тюрьмы −1  ')
        self.assertEqual(card.locator('.object-faction-badge').inner_text(),next(f['name'] for f in data['factions'] if f['id']==prison['faction']))
        self.page.locator('#dossier-parent-locations button[data-location-link="military-district"]').click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),'military-district')
        self.assertEqual(self.page.locator('#dossier-objects .modifier').count(),0)
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
        self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'),raw)
        self.page.screenshot(path=str(OUT/'district-prison-links.png'))
        self.assertEqual(self.errors,[])
    def test_native_point_editor_saves_location_flag_and_links_in_one_full_snapshot_then_reload(self):
        data=json.loads((ROOT/'assets/data/atlas.json').read_text())
        village=next(l for l in data['locations'] if l['id']=='emberstone-village')
        village.pop('isLocation',None);village.pop('linkedLocationIds',None)
        self.boot(data);before=self.page.evaluate('window.gilneasApp.getData()')
        self.page.locator('#editor-open').click();self.page.locator('label:has(#editing-enabled)').click();self.page.locator('[data-close=editor]').click()
        self.page.locator('#search').fill('Деревня Тлеющего Угля')
        self.page.locator('#location-list button[data-location-id="emberstone-village"]').click()
        self.page.locator('#dossier-edit').click()
        self.assertEqual(self.page.locator('#location-is-location').count(),1,'The real point editor exposes location-container authoring')
        self.assertFalse(self.page.locator('#location-is-location').is_checked())
        self.page.locator('label:has(#location-is-location)').click()
        self.page.locator('#location-link-target').select_option('emberstone-mine')
        self.page.locator('#location-link-add').click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before,'Link selection remains unsaved until the point transaction')
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.page.locator('#location-form button[type=submit]').click()
        self.assertTrue(self.page.locator('#location-editor').is_hidden())
        after=self.page.evaluate('window.gilneasApp.getData()')
        saved=next(l for l in after['locations'] if l['id']=='emberstone-village')
        self.assertTrue(saved['isLocation']);self.assertEqual(saved['linkedLocationIds'],['emberstone-mine'])
        expected=json.loads(json.dumps(before));target=next(l for l in expected['locations'] if l['id']=='emberstone-village');target.update(isLocation=True,linkedLocationIds=['emberstone-mine'])
        self.assertEqual(after,expected)
        self.assertEqual(json.loads(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")')),after)
        self.page.reload();self.page.wait_for_function('window.gilneasApp?.ready',polling=50)
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),after)
        self.page.evaluate('window.gilneasApp.selectId("emberstone-village")')
        self.assertEqual(self.page.locator('#dossier-location-links button[data-location-link="emberstone-mine"]').count(),1)
        self.assertEqual(self.errors,[])
if __name__=='__main__':unittest.main()
