"""Gold favorite state and a stable registry icon column, real bootstrap."""
import functools
import json
import os
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(os.environ.get('GILNEAS_TEST_ROOT', Path(__file__).resolve().parents[1]))
PREFIX = os.environ.get('GILNEAS_TEST_PREFIX', '/')
OUT = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-favorite-layout-evidence')
GOLD = 'rgb(224, 196, 147)'

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass

class FavoriteStarLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = ROOT.parent if PREFIX != '/' else ROOT
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(directory)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}' + PREFIX
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(args=['--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'])
        OUT.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.playwright.stop()
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':1440, 'height':1000}, reduced_motion='reduce')
        self.page = self.context.new_page(); self.page.set_default_timeout(10000)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
        self.page.goto(self.url, wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready', polling=50, timeout=30000)

    def tearDown(self): self.context.close()

    def fill(self, selector):
        return self.page.locator(selector).evaluate('e=>getComputedStyle(e).fill')

    def assert_opaque_gold(self, selector):
        style = self.page.locator(selector).evaluate('''e=>{const style=getComputedStyle(e);let opacity=1;for(let node=e;node;node=node.parentElement)opacity*=Number(getComputedStyle(node).opacity);return {fill:style.fill,stroke:style.stroke,fillOpacity:Number(style.fillOpacity),strokeOpacity:Number(style.strokeOpacity),opacity};}''')
        self.assertEqual(style, {'fill':GOLD,'stroke':GOLD,'fillOpacity':1,'strokeOpacity':1,'opacity':1})

    def test_01_active_favorites_fill_existing_stars_gold_and_survive_readonly_reload(self):
        before = self.page.evaluate('window.gilneasApp.getData()')
        self.page.locator('#search').fill('Торговая площадь')
        self.page.locator('#location-list button.location-row[data-location-id="merchant-square"]').click()
        favorite = self.page.locator('#dossier-favorite')
        shape = favorite.locator('svg path').get_attribute('d')
        favorite.scroll_into_view_if_needed()
        box = favorite.bounding_box()
        self.assertEqual(favorite.get_attribute('aria-pressed'), 'false')
        self.assertEqual(self.fill('#dossier-favorite svg path'), 'none')
        favorite.click(); self.page.mouse.move(2, 2)
        self.assertEqual(favorite.get_attribute('aria-pressed'), 'true')
        self.assertEqual(self.fill('#dossier-favorite svg path'), GOLD, 'A selected favorite needs real opaque gold fill, not only a gold border')
        self.assert_opaque_gold('#dossier-favorite svg path')
        self.assertEqual(favorite.locator('svg path').get_attribute('d'), shape)
        self.assertEqual(favorite.bounding_box(), box)
        self.page.locator('#filter-favorites').click(); self.page.mouse.move(2, 2)
        self.assertEqual(self.fill('#filter-favorites svg path'), GOLD)
        self.assertEqual(self.fill('#location-list .row-favorite path'), GOLD)
        self.assert_opaque_gold('#filter-favorites svg path')
        self.assert_opaque_gold('#location-list .row-favorite path')
        self.assertEqual(self.page.evaluate('JSON.parse(localStorage.getItem("gilneas-atlas-favorites-v1"))'), ['merchant-square'])
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertFalse(self.page.evaluate('document.body.classList.contains("edit-mode")'))
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), before)
        self.page.reload(); self.page.wait_for_function('window.gilneasApp?.ready', polling=50, timeout=30000)
        self.page.locator('#search').fill('Торговая площадь')
        self.page.locator('#location-list button.location-row[data-location-id="merchant-square"]').click()
        self.assertEqual(favorite.get_attribute('aria-pressed'), 'true')
        self.assertEqual(self.fill('#dossier-favorite svg path'), GOLD)
        favorite.click(); self.page.mouse.move(2, 2)
        self.assertEqual(favorite.get_attribute('aria-pressed'), 'false')
        self.assertEqual(self.fill('#dossier-favorite svg path'), 'none')
        self.assertEqual(self.page.evaluate('JSON.parse(localStorage.getItem("gilneas-atlas-favorites-v1"))'), [])
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), before)
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertEqual(self.errors, [])

    def row_geometry(self, id):
        row = self.page.locator('#location-list button.location-row[data-location-id="' + id + '"]')
        return row.evaluate('''e=>{const r=e.getBoundingClientRect();const relative=node=>{const b=node.getBoundingClientRect();return {x:b.left-r.left,y:b.top-r.top,w:b.width,h:b.height,right:b.right-r.left,bottom:b.bottom-r.top};};return {w:r.width,h:r.height,name:relative(e.querySelector('.row-name')),type:relative(e.querySelector('.location-type')),star:e.querySelector('.row-favorite')?relative(e.querySelector('.row-favorite')):null,marks:e.querySelector('.row-marks')?relative(e.querySelector('.row-marks')):null};}''')

    def test_02_registry_star_has_a_fixed_right_column_without_moving_name_or_type(self):
        before = self.page.evaluate('window.gilneasApp.getData()')
        measurements = []
        for width, height in [(1440,1000),(390,844),(844,390),(320,640)]:
            self.page.set_viewport_size({'width':width,'height':height})
            self.page.wait_for_function('Math.abs(parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--app-height"))-innerHeight)<1', polling=50)
            for id in ['merchant-square','shadowfang','gilneas-city']:
                with self.subTest(viewport=(width,height), location=id):
                    self.page.evaluate('''id=>{window.gilneasApp.selectId(id);if(document.querySelector('#dossier-favorite').getAttribute('aria-pressed')==='true')document.querySelector('#dossier-favorite').click();window.gilneasApp.ui.setPanel('navigation',true);}''', id)
                    name = next(location['name'] for location in before['locations'] if location['id']==id)
                    self.page.locator('#search').fill(name)
                    unselected = self.row_geometry(id)
                    self.page.evaluate('id=>window.gilneasApp.selectId(id)', id)
                    self.page.locator('#dossier-favorite').click()
                    self.page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)')
                    selected = self.row_geometry(id)
                    self.assertGreater(selected['w'],0)
                    self.assertLessEqual(selected['h'],72,'Favorite must not create a separate extra row')
                    self.assertEqual(selected['name'],unselected['name'],'Star column is always reserved; title geometry must not shift')
                    self.assertEqual(selected['type'],unselected['type'],'Type geometry must not shift when favorited')
                    self.assertEqual(selected['h'],unselected['h'],'Adding a favorite must not add a grid row')
                    self.assertIsNotNone(selected['star'])
                    self.assertGreaterEqual(selected['star']['x'],selected['name']['right']+3)
                    self.assertGreaterEqual(selected['star']['x'],selected['type']['right']+3)
                    self.assertLessEqual(selected['star']['right'],selected['w']-3)
                    self.assertGreaterEqual(selected['star']['y'],0)
                    self.assertLessEqual(selected['star']['bottom'],selected['h'])
                    self.assertLess(selected['w']-selected['star']['right'],12,'Favorite icon sits at the shared trailing edge')
                    self.assertAlmostEqual(selected['star']['y']+selected['star']['h']/2,selected['h']/2,delta=2)
                    if id=='gilneas-city':self.assertEqual(self.page.locator('#location-list .location-row[data-location-id="gilneas-city"] .row-capital svg').count(),1)
                    self.page.locator('#filter-favorites').click()
                    self.assertEqual(self.row_geometry(id),selected,'Favorite-only filter keeps the same row layout')
                    row = self.page.locator('#location-list button.location-row[data-location-id="' + id + '"]')
                    row.scroll_into_view_if_needed()
                    visible = row.evaluate('''e=>{const r=e.getBoundingClientRect(),list=e.closest('#location-list').getBoundingClientRect();return {top:r.top,bottom:r.bottom,listTop:list.top,listBottom:list.bottom};}''')
                    self.assertGreaterEqual(visible['top'],visible['listTop']-1)
                    self.assertLessEqual(visible['bottom'],visible['listBottom']+1)
                    self.assert_opaque_gold('#location-list button.location-row[data-location-id="' + id + '"] .row-favorite path')
                    row.locator('.row-favorite').click()
                    self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),id)
                    self.page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)')
                    row.scroll_into_view_if_needed()
                    self.page.screenshot(path=str(OUT/f'{id}-{width}x{height}.png'))
                    self.page.locator('#filter-all').click()
                    measurements.append({'viewport':[width,height],'id':id,'before':unselected,'after':selected})
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
        (OUT/'row-measurements.json').write_text(json.dumps(measurements,ensure_ascii=False,indent=2))
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertEqual(self.errors,[])

    def test_03_narrow_phone_shows_the_whole_favorite_row_and_its_gold_star(self):
        self.page.set_viewport_size({'width':320,'height':640})
        self.page.wait_for_function('Math.abs(parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--app-height"))-innerHeight)<1',polling=50)
        before=self.page.evaluate('window.gilneasApp.getData()')
        self.page.evaluate('''()=>{window.gilneasApp.selectId('shadowfang');document.querySelector('#dossier-favorite').click();window.gilneasApp.ui.setPanel('navigation',true);}''')
        self.page.locator('#search').fill('Крепость над Пирвудом')
        self.page.locator('#filter-favorites').click()
        row=self.page.locator('#location-list .location-row[data-location-id="shadowfang"]')
        list=self.page.locator('#location-list')
        self.assertGreaterEqual(list.bounding_box()['height'],row.bounding_box()['height']+12,'The registry must leave room to see a complete favorite row, not an invisible offscreen screenshot')
        row.scroll_into_view_if_needed()
        rect=row.bounding_box();bounds=list.bounding_box()
        self.assertGreaterEqual(rect['y'],bounds['y']-1)
        self.assertLessEqual(rect['y']+rect['height'],bounds['y']+bounds['height']+1)
        self.assertTrue(row.locator('.row-favorite').evaluate('''e=>{const r=e.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('.location-row')===e.closest('.location-row');}'''))
        self.page.screenshot(path=str(OUT/'favorite-row-visible-320x640.png'))
        row.click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),'shadowfang')
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertEqual(self.errors,[])

    def test_04_favorite_controls_keep_44px_hit_targets_in_both_dimensions(self):
        before=self.page.evaluate('window.gilneasApp.getData()')
        for width,height in [(1440,1000),(390,844),(844,390),(320,640)]:
            with self.subTest(viewport=(width,height)):
                self.page.set_viewport_size({'width':width,'height':height})
                self.page.wait_for_function('Math.abs(parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--app-height"))-innerHeight)<1',polling=50)
                self.page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)')
                rect=self.page.locator('#filter-favorites').bounding_box()
                self.assertGreaterEqual(rect['width'],44,'The favorite tab needs the same 44px horizontal hit target as its height')
                self.assertGreaterEqual(rect['height'],44)
                self.page.evaluate('window.gilneasApp.selectId("merchant-square")')
                favorite=self.page.locator('#dossier-favorite');favorite.scroll_into_view_if_needed()
                rect=favorite.bounding_box()
                self.assertGreaterEqual(rect['width'],44)
                self.assertGreaterEqual(rect['height'],44)
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertEqual(self.errors,[])

    def test_05_favorites_only_write_their_key_and_preserve_an_existing_author_draft_exactly(self):
        before = self.page.evaluate('window.gilneasApp.getData()')
        raw = json.dumps(before,ensure_ascii=False,indent=3)+'\n'
        self.page.evaluate('raw=>localStorage.setItem("gilneas-atlas-draft-v1",raw)',raw)
        self.page.evaluate('''()=>{window.favoriteStorageWrites=[];for(const name of ['setItem','removeItem','clear']){const original=Storage.prototype[name];Storage.prototype[name]=function(...args){window.favoriteStorageWrites.push({method:name,args});return original.apply(this,args);};}}''')
        self.assertFalse(self.page.evaluate('document.body.classList.contains("edit-mode")'))
        self.page.locator('#search').fill('Торговая площадь')
        self.page.locator('#location-list button.location-row[data-location-id="merchant-square"]').click()
        self.page.locator('#dossier-favorite').click()
        self.page.locator('#filter-favorites').click()
        row = self.page.locator('#location-list button.location-row[data-location-id="merchant-square"]')
        row.scroll_into_view_if_needed()
        row.locator('.row-favorite').click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),'merchant-square')
        self.page.locator('#dossier-favorite').click()
        writes = self.page.evaluate('window.favoriteStorageWrites')
        self.assertEqual(len(writes),2)
        self.assertTrue(all(write['method']=='setItem' and write['args'][0]=='gilneas-atlas-favorites-v1' for write in writes))
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
        self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'),raw)
        self.page.reload(wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=30000)
        self.assertFalse(self.page.evaluate('document.body.classList.contains("edit-mode")'))
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
        self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'),raw)
        self.assertEqual(self.page.evaluate('JSON.parse(localStorage.getItem("gilneas-atlas-favorites-v1"))'),[])
        self.assertEqual(self.errors,[])

if __name__ == '__main__': unittest.main()
