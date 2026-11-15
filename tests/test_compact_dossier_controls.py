"""Compact visual dossier actions retain native mouse and touch usability."""
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
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-compact-dossier-evidence')
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
class CompactDossierControls(unittest.TestCase):
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
    def boot(self,width=1440,height=1000):
        self.page.route('**/assets/js/app.mjs',lambda route:route.fulfill(status=200,content_type='application/javascript',body='// Isolate unrelated in-flight Council bootstrap.'))
        self.page.set_viewport_size({'width':width,'height':height});self.page.goto(self.url,wait_until='domcontentloaded')
        data=json.loads((ROOT/'assets/data/atlas.json').read_text())
        self.page.evaluate('''async data=>{const {initUI}=await import('./assets/js/ui.mjs');const {decorateIcons}=await import('./assets/js/icons.mjs');decorateIcons();window.fixtureData=data;window.fixtureSelected='northgate-river';const ui=initUI({getData:()=>window.fixtureData,getSelectedId:()=>window.fixtureSelected,onSelect:id=>{window.fixtureSelected=id;ui.render();}});window.gilneasApp={ready:true,ui,getData:()=>window.fixtureData,selectId:id=>{window.fixtureSelected=id;ui.render();}};ui.focusLocation('northgate-river',false);}''',data)
        self.page.wait_for_function('document.querySelector("#base-map").complete&&document.querySelector("#base-map").naturalWidth>0',polling=50)
    def test_desktop_dossier_buttons_are_32px_inside_the_unchanged_44px_header(self):
        self.boot();before=self.page.evaluate('window.gilneasApp.getData()');stored=self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")')
        header=self.page.locator('#dossier .dossier-head').bounding_box();self.assertEqual(header['height'],44)
        rows=[]
        for id in ['dossier-fold','dossier-close']:
            button=self.page.locator('#'+id);box=button.bounding_box()
            self.assertEqual([box['width'],box['height']],[32,32],'Only the two short-header actions shrink')
            self.assertAlmostEqual(box['y']-header['y'],5.5,delta=0.5)
            self.assertAlmostEqual(header['y']+header['height']-box['y']-box['height'],6.5,delta=0.5)
            icon=button.locator('svg').bounding_box();self.assertEqual([icon['width'],icon['height']],[16,16])
            self.assertAlmostEqual(icon['x']+icon['width']/2,box['x']+box['width']/2,delta=0.1)
            self.assertAlmostEqual(icon['y']+icon['height']/2,box['y']+box['height']/2,delta=0.1)
            rows.append({'id':id,'box':box,'icon':icon})
        self.page.mouse.move(2,2);self.page.screenshot(path=str(OUT/'desktop-controls.png'))
        self.page.locator('#dossier-fold').click();self.assertTrue(self.page.locator('#dossier-body').is_hidden())
        self.page.locator('#dossier-fold').click();self.assertTrue(self.page.locator('#dossier-body').is_visible())
        self.page.locator('#dossier-close').focus();self.page.keyboard.press('Enter');self.assertTrue(self.page.locator('#dossier').is_hidden())
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
        self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'),stored)
        self.assertEqual(self.errors,[]);(OUT/'desktop-controls.json').write_text(json.dumps(rows,indent=2)+'\n')
    def test_mobile_32px_visual_controls_keep_separate_44px_touch_targets(self):
        for width,height in [(390,844),(844,390)]:
            self.boot(width,height)
            for id in ['dossier-fold','dossier-close']:
                button=self.page.locator('#'+id);box=button.bounding_box()
                self.assertEqual([box['width'],box['height']],[44,44],'Touch hit target must not shrink with the visual housing')
                visual=button.evaluate('e=>{const c=getComputedStyle(e,"::before");return {width:c.width,height:c.height,content:c.content,border:c.borderTopWidth,boxSizing:c.boxSizing};}')
                self.assertEqual(visual['boxSizing'],'border-box','The declared32px housing includes its border')
                self.assertEqual([visual['width'],visual['height']],['32px','32px'])
                self.assertEqual(visual['border'],'1px')
                self.assertEqual(button.evaluate('e=>getComputedStyle(e).backgroundColor'),'rgba(0, 0, 0, 0)')
                icon=button.locator('svg').bounding_box()
                self.assertAlmostEqual(icon['x']+icon['width']/2,box['x']+box['width']/2,delta=0.1)
                self.assertAlmostEqual(icon['y']+icon['height']/2,box['y']+box['height']/2,delta=0.1)
            fold=self.page.locator('#dossier-fold').bounding_box();close=self.page.locator('#dossier-close').bounding_box()
            self.assertGreaterEqual(close['x']-fold['x']-fold['width'],6)
            self.page.mouse.move(2,2);self.page.screenshot(path=str(OUT/f'mobile-controls-{width}x{height}.png'))
            box=self.page.locator('#dossier-fold').bounding_box()
            self.page.mouse.click(box['x']+2,box['y']+box['height']/2)
            self.assertTrue(self.page.locator('#dossier-body').is_hidden(),'Outer invisible hit area still performs a native fold')
            self.page.locator('#dossier-fold').click();self.page.locator('#dossier-close').click()
            self.assertTrue(self.page.locator('#dossier').is_hidden())
        self.assertEqual(self.errors,[])
if __name__=='__main__':unittest.main()
