"""Map heraldry permits vertical scrolling, never sideways movement."""
import functools
import json
import os
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(os.environ.get('GILNEAS_TEST_ROOT',Path(__file__).resolve().parents[1]))
PREFIX=os.environ.get('GILNEAS_TEST_PREFIX','/')
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-layers-scroll-evidence')

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class LayersVerticalScroll(unittest.TestCase):
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
        self.page=self.context.new_page();self.page.set_default_timeout(12000);self.errors=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.on('console',lambda message:self.errors.append(message.text) if message.type=='error' else None)
        self.page.on('response',lambda response:self.errors.append(f'{response.status} {response.url}') if response.status>=400 else None)
    def tearDown(self):self.context.close()
    def boot(self,width,height,extra_factions=False):
        self.page.set_viewport_size({'width':width,'height':height})
        if extra_factions:
            fixture=json.loads((ROOT/'assets/data/atlas.json').read_text())
            for index in range(35):
                fixture['factions'].append({'id':f'layer-scroll-fixture-{index}','name':f'Тестовый дом {index} с очень длинным названием без новых владений','color':'#778899','parent':'gilneas','ruler':''})
            self.page.route('**/assets/data/atlas.json',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(fixture,ensure_ascii=False)))
        self.page.goto(self.url,wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=45000)
        if not self.page.locator('#layers').is_visible():self.page.locator('#mobile-layers').click()
        self.assertTrue(self.page.locator('#layers').is_visible())
    def geometry(self):
        return self.page.locator('#layers').evaluate('''e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {width:r.width,height:r.height,client:e.clientWidth,scroll:e.scrollWidth,top:e.scrollTop,left:e.scrollLeft,overflowX:s.overflowX,overflowY:s.overflowY,offenders:[...e.querySelectorAll('*')].filter(n=>n.getBoundingClientRect().right>r.right+.1).map(n=>({tag:n.tagName,class:n.getAttribute('class'),right:n.getBoundingClientRect().right-r.right}))};}''')
    def assert_vertical_only(self):
        panel=self.page.locator('#layers');profile=self.geometry()
        self.assertIn(profile['overflowX'],['hidden','clip'],'Layers must explicitly prohibit horizontal scroll: '+str(profile))
        self.assertEqual(profile['overflowY'],'auto')
        panel.evaluate('e=>{e.scrollLeft=0;}')
        rect=panel.bounding_box();self.page.mouse.move(rect['x']+rect['width']/2,rect['y']+min(rect['height']/2,100))
        self.page.mouse.wheel(400,0);self.page.wait_for_timeout(100)
        self.assertEqual(panel.evaluate('e=>e.scrollLeft'),0,'Native horizontal wheel must not move the heraldry pane')
        return profile
    def test_01_current_heraldry_panel_cannot_be_scrolled_sideways_on_desktop_or_phone(self):
        measurements=[]
        for width,height in [(1440,1000),(800,800),(390,844),(844,390),(320,640),(760,541)]:
            with self.subTest(viewport=(width,height)):
                self.boot(width,height);before=self.page.evaluate('window.gilneasApp.getData()')
                profile=self.assert_vertical_only();measurements.append({'viewport':[width,height],**profile})
                self.assertEqual(self.page.locator('#faction-list button.faction-row').count(),len(before['factions']))
                self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
                self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
                self.page.screenshot(path=str(OUT/f'layers-{width}x{height}.png'))
                self.assertEqual(self.errors,[])
        (OUT/'current-measurements.json').write_text(json.dumps(measurements,ensure_ascii=False,indent=2)+'\n')
    def test_02_more_real_faction_rows_keep_native_vertical_scroll_and_last_filter_reachable(self):
        self.boot(390,844,extra_factions=True)
        before=self.page.evaluate('window.gilneasApp.getData()')
        self.assert_vertical_only()
        panel=self.page.locator('#layers')
        self.assertGreater(panel.evaluate('e=>e.scrollHeight'),panel.evaluate('e=>e.clientHeight'))
        rect=panel.bounding_box();self.page.mouse.move(rect['x']+rect['width']/2,rect['y']+rect['height']/2)
        self.page.mouse.wheel(0,1400)
        self.page.wait_for_function('document.getElementById("layers").scrollTop>0',polling=50)
        self.assertEqual(panel.evaluate('e=>e.scrollLeft'),0)
        last=self.page.locator('#faction-list button.faction-row[data-faction-id="layer-scroll-fixture-34"]')
        last.scroll_into_view_if_needed();last.click()
        self.assertEqual(self.page.locator('#faction-list button.faction-row[data-faction-id="layer-scroll-fixture-34"]').get_attribute('aria-pressed'),'true')
        self.assertEqual(panel.evaluate('e=>e.scrollLeft'),0)
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.page.screenshot(path=str(OUT/'layers-many-factions-390x844.png'))
        self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
