"""Native regression for mirrored top-row panel return controls."""
import functools
import json
import os
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT=Path(os.environ.get('GILNEAS_TEST_ROOT',str(Path(__file__).resolve().parents[1])))
PREFIX=os.environ.get('GILNEAS_TEST_PREFIX','/')
ARTIFACTS=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-panel-position-evidence')

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

class CourtPanelPosition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(ROOT)))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'+PREFIX
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows'])
        ARTIFACTS.mkdir(parents=True,exist_ok=True)
    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.playwright.stop()
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)
    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        self.page=self.context.new_page(); self.page.set_default_timeout(10000)
        self.errors=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.on('console',lambda message:self.errors.append(message.text) if message.type=='error' else None)
        self.page.on('response',lambda response:self.errors.append(f'{response.status} {response.url}') if response.status>=400 else None)
    def tearDown(self): self.context.close()
    def boot(self,width,height):
        self.page.set_viewport_size({'width':width,'height':height})
        self.page.goto(self.url,wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready',polling=50)
    def mirrored_bounds(self):
        nav=self.page.locator('#nav-open').bounding_box()
        layers=self.page.locator('#layers-open').bounding_box()
        viewport=self.page.locator('#viewport').bounding_box()
        self.assertIsNotNone(nav); self.assertIsNotNone(layers)
        self.assertAlmostEqual(layers['y'],nav['y'],delta=0.5,msg='Державы и дома must share the registry return control top row, not the bottom camera row')
        self.assertAlmostEqual(layers['y']-viewport['y'],22,delta=0.5)
        left=nav['x']-viewport['x']
        right=viewport['x']+viewport['width']-layers['x']-layers['width']
        self.assertAlmostEqual(right,left,delta=0.5,msg='Return controls need mirrored left/right edge insets')
        self.assertGreaterEqual(layers['height'],44)
        return {'registry':nav,'layers':layers,'viewport':viewport}
    def test_desktop_return_controls_are_mirrored_at_the_top_with_dossier_below(self):
        measurements=[]
        for width,height in [(1920,1080),(1440,1000),(1000,800),(800,800)]:
            with self.subTest(width=width,height=height):
                self.boot(width,height)
                before=self.page.evaluate('JSON.stringify(window.gilneasApp.getData())')
                stored=self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")')
                self.page.locator('#nav-close').click()
                self.page.locator('#layers-close').click()
                measurements.append({'size':[width,height],**self.mirrored_bounds()})
                self.page.locator('#layers-open').click()
                self.assertTrue(self.page.locator('#layers').is_visible())
                self.assertTrue(self.page.locator('#layers-open').is_hidden())
                self.page.locator('#layers-close').click()
                self.page.evaluate('window.gilneasApp.selectId("gilneas-city")')
                self.page.wait_for_timeout(500)
                bounds=self.mirrored_bounds()
                dossier=self.page.locator('#dossier').bounding_box()
                self.assertGreaterEqual(dossier['y'],bounds['layers']['y']+bounds['layers']['height']+8,'Reserve a separate return-control row above the dossier')
                # The actual top-right button must remain clickable with the dossier open.
                self.page.locator('#layers-open').click()
                self.assertTrue(self.page.locator('#layers').is_visible())
                self.assertTrue(self.page.locator('#dossier').is_hidden())
                self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),'gilneas-city')
                self.assertEqual(self.page.evaluate('JSON.stringify(window.gilneasApp.getData())'),before)
                self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'),stored)
                self.page.locator('#layers-close').click()
                self.page.screenshot(path=str(ARTIFACTS/f'return-controls-{width}x{height}.png'))
        (ARTIFACTS/'desktop-bounds.json').write_text(json.dumps(measurements,ensure_ascii=False,indent=2)+'\n')
        self.assertEqual(self.errors,[])
    def test_mobile_keeps_its_dock_instead_of_desktop_return_buttons(self):
        for width,height in [(390,844),(844,390)]:
            with self.subTest(width=width,height=height):
                self.boot(width,height)
                self.assertTrue(self.page.locator('#layers-open').is_hidden())
                self.assertTrue(self.page.locator('#nav-open').is_hidden())
                self.page.locator('#mobile-layers').click()
                self.assertTrue(self.page.locator('#layers').is_visible())
                self.page.locator('#layers-close').click()
                self.assertTrue(self.page.locator('#layers').is_hidden())
                self.page.locator('#mobile-layers').click()
                self.assertTrue(self.page.locator('#layers').is_visible())
        self.assertEqual(self.errors,[])
    def test_layers_close_is_not_intercepted_at_760_by_541(self):
        self.boot(760,541)
        before=self.page.evaluate('window.gilneasApp.getData()')
        stored=self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")')
        self.page.locator('#mobile-layers').click()
        self.assertTrue(self.page.locator('#layers').is_visible())
        probe=self.page.locator('#layers-close').evaluate('e=>{const r=e.getBoundingClientRect();return {box:{x:r.x,y:r.y,width:r.width,height:r.height},hit:document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest("button")?.id};}')
        self.assertEqual(probe['hit'],'layers-close','Visible close action is intercepted: '+json.dumps(probe))
        self.page.locator('#layers-close').click()
        self.assertTrue(self.page.locator('#layers').is_hidden())
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
        self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'),stored)
        self.assertEqual(self.errors,[])

if __name__=='__main__': unittest.main()
