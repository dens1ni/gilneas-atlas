"""Dossiers share the actual registry frame, not a parchment/silver inset."""
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
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-dossier-frame-evidence')
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
PROFILE="""id=>{const e=document.getElementById(id),s=getComputedStyle(e);const pseudo=p=>{const c=getComputedStyle(e,p);return {content:c.content,width:c.width,height:c.height,borderTop:c.borderTop,borderLeft:c.borderLeft,shadow:c.boxShadow,transform:c.transform,pointer:c.pointerEvents};};return {border:s.border,borderColor:s.borderColor,borderWidth:s.borderWidth,borderStyle:s.borderStyle,radius:s.borderRadius,shadow:s.boxShadow,outline:s.outline,before:pseudo('::before'),after:pseudo('::after')};}"""
class DossierRegistryFrame(unittest.TestCase):
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
        self.page.on('console',lambda m:self.errors.append(m.text) if m.type=='error' else None)
        self.page.on('response',lambda r:self.errors.append(f'{r.status} {r.url}') if r.status>=400 else None)
    def tearDown(self):self.context.close()
    def boot(self):
        self.page.goto(self.url,wait_until='domcontentloaded');self.page.wait_for_function('window.gilneasApp?.ready',polling=50)
        data=self.page.evaluate('window.gilneasApp.getData()')
        published=json.loads((ROOT/'assets/data/atlas.json').read_text())
        for collection in ['locations','factions','nobles']:
            self.assertEqual(data[collection],published[collection],collection)
        landmark=next(row for row in data['locations'] if row['id']=='northern-headlands')
        self.assertEqual(landmark['type'],'landmark')
        # A natural map marker can contain canonical own buildings.
        published=json.loads((ROOT/'assets/data/atlas.json').read_text())
        expected=next(row for row in published['locations'] if row['id']=='northern-headlands')
        self.assertEqual(landmark,expected,'Focus preserves the complete canonical landmark and its own objects')
    def profile(self,id):return self.page.evaluate(PROFILE,id)
    def assert_literal_frame(self, profile, mobile=False):
        self.assertEqual(profile['borderWidth'], '1px')
        self.assertEqual(profile['borderStyle'], 'solid')
        self.assertEqual(profile['borderColor'], 'rgb(107, 96, 75)')
        self.assertEqual(profile['radius'], '5px 5px 2px 2px' if mobile else '3px')
        self.assertEqual(profile['shadow'], 'rgba(0, 0, 0, 0.6) 0px -6px 24px 0px' if mobile else 'rgba(0, 0, 0, 0.533) 0px 10px 36px 0px, rgb(17, 22, 25) 0px 0px 0px 2px inset')
        for key in ['before', 'after']:
            self.assertEqual(profile[key]['width'], '11px')
            self.assertEqual(profile[key]['height'], '11px')
            self.assertEqual(profile[key]['pointer'], 'none')
    def test_all_map_dossiers_have_the_exact_registry_frame_and_keep_identity_colors(self):
        self.boot();data=self.page.evaluate('window.gilneasApp.getData()')
        stored=self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")')
        reference=self.profile('navigation');self.assertEqual(self.profile('layers'),reference)
        self.assert_literal_frame(reference)
        expected_ids=[row['id'] for row in json.loads((ROOT/'assets/data/atlas.json').read_text())['locations']]
        self.assertEqual(len(data['locations']), len(expected_ids))
        self.assertEqual(sorted(l['id'] for l in data['locations']), sorted(expected_ids))
        rows=[]
        for location in data['locations']:
            self.page.evaluate('id=>window.gilneasApp.selectId(id)',location['id'])
            self.assertEqual(self.profile('dossier'),reference,location['id']+' must lose the separate bright inset and share registry corners')
            color=self.page.locator('#dossier-seal .faction-shield .shield-field').get_attribute('fill')
            faction=next((f for f in data['factions'] if f['id']==location.get('faction')),None)
            expected=data['meta']['gilneasHeraldry']['field'] if location.get('faction')=='gilneas' else faction.get('heraldry',{}).get('field',faction['color']) if faction else '#87918d'
            self.assertEqual(color,expected,'Only exterior frame changes, not the inner heraldry')
            rows.append({'id':location['id'],'frame':self.profile('dossier'),'shield':color})
        self.page.evaluate('window.gilneasApp.selectId("northern-headlands")')
        self.page.screenshot(path=str(OUT/'headlands-dossier-desktop.png'))
        self.page.locator('#dossier-fold').click();self.assertTrue(self.page.locator('#dossier-body').is_hidden())
        self.assertEqual(self.profile('dossier'),reference)
        self.page.locator('#dossier-fold').click();self.assertTrue(self.page.locator('#dossier-body').is_visible())
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),data)
        self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'),stored)
        self.assertEqual(len(rows),len(data['locations']));self.assertEqual(sorted(row['id'] for row in rows),sorted(expected_ids));self.assertEqual(self.errors,[])
        (OUT/'map-dossier-frames.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    def test_mobile_dossier_keeps_the_registry_sheet_frame_and_native_controls(self):
        rows=[]
        for width,height in [(390,844),(844,390)]:
            self.page.set_viewport_size({'width':width,'height':height});self.boot()
            self.page.locator('#mobile-nav').click();reference=self.profile('navigation')
            self.assert_literal_frame(reference, mobile=True)
            self.page.locator('#mobile-layers').click();self.assertEqual(self.profile('layers'),reference)
            self.page.evaluate('window.gilneasApp.selectId("northern-headlands")')
            self.assertEqual(self.profile('dossier'),reference,'Mobile removes silver inset without moving the sheet')
            rows.append({'viewport':[width,height],'frame':self.profile('dossier')})
            self.page.screenshot(path=str(OUT/f'headlands-dossier-{width}x{height}.png'))
            header=self.page.locator('#dossier .dossier-head').bounding_box()
            self.page.locator('#dossier-focus').scroll_into_view_if_needed()
            self.assertTrue(self.page.locator('#dossier-focus').is_visible(),'The final action remains reachable below the full description')
            self.assertAlmostEqual(self.page.locator('#dossier .dossier-head').bounding_box()['y'],header['y'],delta=1)
            self.page.screenshot(path=str(OUT/f'headlands-dossier-scrolled-{width}x{height}.png'))
            self.page.locator('#dossier-fold').click();self.assertTrue(self.page.locator('#dossier-body').is_hidden())
            self.page.locator('#dossier-fold').click();self.page.locator('#dossier-close').click()
            self.assertTrue(self.page.locator('#dossier').is_hidden())
            self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),'northern-headlands')
        self.assertEqual(self.errors,[])
        (OUT/'mobile-frames.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    def test_noble_dossier_uses_registry_exterior_without_changing_the_house_device(self):
        self.boot();before=self.page.evaluate('window.gilneasApp.getData()');reference=self.profile('navigation')
        self.page.evaluate('window.gilneasApp.nobleDossier.open("noble-darius")')
        self.assertEqual(self.profile('noble-dossier'),reference,'Person dossiers use the same neutral exterior as land dossiers')
        self.assertEqual(self.page.locator('#noble-crest .shield-device').get_attribute('href'),'assets/ui/factions/crowley-device.svg')
        self.page.locator('#noble-dossier [data-close="noble-dossier"]').click()
        self.assertTrue(self.page.locator('#noble-dossier').is_hidden())
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before);self.assertEqual(self.errors,[])
if __name__=='__main__':unittest.main()
