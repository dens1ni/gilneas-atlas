"""Native scrollbars belong below the fixed Chronicle and Help headers."""
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
OUT = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-dialog-scroll-evidence')

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass

class DialogScrollHeaders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = ROOT.parent if PREFIX != '/' else ROOT
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(directory)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}' + PREFIX
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(args=['--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows'])
        OUT.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.playwright.stop()
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':1440,'height':1000}, reduced_motion='reduce')
        self.page = self.context.new_page(); self.page.set_default_timeout(8000)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
        self.page.goto(self.url, wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready', polling=50, timeout=25000)

    def tearDown(self): self.context.close()

    def assert_scroll_below_header(self, name):
        dialog = self.page.locator('#' + name)
        header = dialog.locator(':scope > .dialog-head')
        body = dialog.locator(':scope > .dialog-content')
        profile = dialog.evaluate('''e=>{const b=e.querySelector('.dialog-content'),h=e.querySelector('.dialog-head'),ds=getComputedStyle(e),bs=getComputedStyle(b),dr=e.getBoundingClientRect(),hr=h.getBoundingClientRect(),br=b.getBoundingClientRect();return {dialogOverflow:ds.overflowY,bodyOverflow:bs.overflowY,dialogScroll:e.scrollHeight,dialogClient:e.clientHeight,bodyScroll:b.scrollHeight,bodyClient:b.clientHeight,headerBottom:hr.bottom,bodyTop:br.top,headerTop:hr.top,dialogTop:dr.top,dialogHeight:dr.height,bodyWidth:br.width,bodyScrollWidth:b.scrollWidth,bodyClientWidth:b.clientWidth};}''')
        self.assertEqual(profile['dialogOverflow'], 'hidden', name + ' scrollbar must not belong to the dialog/header')
        self.assertEqual(profile['bodyOverflow'], 'auto', name + ' content keeps its real native scrollbar')
        self.assertGreaterEqual(profile['bodyTop'], profile['headerBottom'] - 1)
        self.assertLessEqual(profile['dialogScroll'], profile['dialogClient'] + 1)
        self.assertLessEqual(profile['bodyScrollWidth'], profile['bodyClientWidth'] + 1)
        self.assertLessEqual(profile['headerTop'] - profile['dialogTop'], 2)
        before = header.bounding_box()
        rect = body.bounding_box()
        self.page.mouse.move(rect['x'] + rect['width'] / 2, rect['y'] + min(rect['height'] / 2, 100))
        self.page.mouse.wheel(0, 600)
        if profile['bodyScroll'] > profile['bodyClient']:
            self.page.wait_for_function('id=>document.querySelector("#"+id+" > .dialog-content").scrollTop>0', arg=name, polling=50)
        body.evaluate('e=>e.scrollTop=e.scrollHeight')
        self.page.wait_for_timeout(100)
        self.assertAlmostEqual(header.bounding_box()['y'], before['y'], delta=1)
        self.assertEqual(dialog.evaluate('e=>e.scrollTop'), 0)
        bottom = body.evaluate('e=>({top:e.scrollTop,client:e.clientHeight,total:e.scrollHeight})')
        self.assertGreaterEqual(bottom['top'] + bottom['client'], bottom['total'] - 2)
        button = header.locator('[data-close]')
        target = button.evaluate('''e=>{const r=e.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('button')===e;}''')
        self.assertTrue(target, name + ' close stays natively reachable while scrolled')
        return profile

    def test_chronicle_sources_scroll_below_its_title_with_reachable_last_source(self):
        self.page.locator('#chronicle-open').click()
        self.page.locator('#chronicle-sources').click()
        self.assert_scroll_below_header('chronicle')
        last = self.page.locator('#chronicle-content > section').last
        self.assertTrue(last.is_visible())
        self.page.screenshot(path=str(OUT/'chronicle-sources-desktop.png'))
        self.page.locator('[data-close="chronicle"]').click()
        self.assertFalse(self.page.locator('#chronicle').is_visible())
        self.assertEqual(self.errors, [])

    def test_help_keeps_only_controls_with_its_native_scrollbar_below_title_and_close(self):
        before = self.page.evaluate('window.gilneasApp.getData()')
        self.page.locator('#help-open').click()
        body = self.page.locator('#help > .dialog-content')
        self.assertEqual(body.locator(':scope > section').count(), 1, 'Only the controls section remains in Help')
        self.assertEqual(body.locator('h3').all_text_contents(), ['Управление картой'])
        self.assertEqual(body.locator('.shortcuts kbd').all_text_contents(), ['/', 'G', '0', 'E', 'У', 'N', 'Т', 'Esc'])
        self.assertEqual(body.locator('.shortcuts dd').count(), 6)
        self.assertEqual(body.locator(':scope > section').evaluate('e=>getComputedStyle(e).borderBottomWidth'), '0px', 'A controls-only guide needs no separator for removed sections')
        self.assertIn('Перетаскивайте карту мышью или пальцем', body.inner_text())
        for removed in ['Досье и объекты', 'Державы, вассалы и границы', 'Черновик и общая публикация', 'Свидетельства', 'GitHub Pages', 'JSON']:
            self.assertNotIn(removed, body.inner_text())
        self.assert_scroll_below_header('help')
        self.page.screenshot(path=str(OUT/'help-controls-desktop.png'))
        self.page.locator('[data-close="help"]').click()
        self.assertFalse(self.page.locator('#help').is_visible())
        self.page.locator('#help-open').click()
        self.page.keyboard.press('Escape')
        self.assertFalse(self.page.locator('#help').is_visible())
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), before)
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertEqual(self.errors, [])

    def test_all_reading_tabs_and_help_keep_header_separate_on_phone_and_landscape(self):
        before = self.page.evaluate('window.gilneasApp.getData()')
        measurements = []
        for width, height in [(1440,1000), (390,844), (844,390), (320,640)]:
            self.page.set_viewport_size({'width':width,'height':height})
            self.page.wait_for_function('Math.abs(parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--app-height"))-innerHeight)<1', polling=50)
            for tab in ['history','nobles','sources']:
                with self.subTest(viewport=(width,height), tab=tab):
                    self.page.locator('#chronicle-open').click()
                    self.page.locator('#chronicle-' + tab).click()
                    profile = self.assert_scroll_below_header('chronicle')
                    self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width)
                    self.page.screenshot(path=str(OUT / f'chronicle-{tab}-{width}x{height}.png'))
                    measurements.append({'dialog':'chronicle','tab':tab,'width':width,'height':height,**profile})
                    self.page.locator('[data-close="chronicle"]').click()
            with self.subTest(viewport=(width,height), dialog='help'):
                self.page.locator('#help-open').click()
                profile = self.assert_scroll_below_header('help')
                self.page.screenshot(path=str(OUT / f'help-bottom-{width}x{height}.png'))
                measurements.append({'dialog':'help','width':width,'height':height,**profile})
                self.page.locator('[data-close="help"]').click()
        (OUT/'measurements.json').write_text(json.dumps(measurements,ensure_ascii=False,indent=2))
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), before)
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertEqual(self.errors, [])

    def test_opening_a_specific_source_scrolls_the_content_not_the_dialog(self):
        sources = self.page.evaluate('window.gilneasApp.getData().sources.map(source=>source.id)')
        self.page.evaluate('id=>window.gilneasApp.chronicle.open("sources",id)', sources[-1])
        body = self.page.locator('#chronicle > .dialog-content')
        self.page.wait_for_function('document.querySelector("#chronicle > .dialog-content").scrollTop>0', polling=50)
        self.assertGreater(body.evaluate('e=>e.scrollTop'), 0)
        self.assertEqual(self.page.locator('#chronicle').evaluate('e=>e.scrollTop'), 0)
        target = self.page.locator('#chronicle-content > section').last
        self.assertTrue(target.is_visible())
        rect = target.bounding_box(); content = body.bounding_box()
        self.assertLess(rect['y'], content['y'] + content['height'])
        self.assertGreater(rect['y'] + rect['height'], content['y'])
        self.assertEqual(self.errors, [])

if __name__ == '__main__': unittest.main()
