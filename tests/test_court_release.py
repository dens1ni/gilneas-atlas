"""Release-specific acceptance through the real parent bootstrap and native input."""
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

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

class CourtRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory=ROOT.parent if PREFIX!='/' else ROOT
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(directory)))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True); cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'+PREFIX
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch(args=['--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows'])
    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.playwright.stop(); cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)
    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        self.page=self.context.new_page(); self.page.set_default_timeout(8000)
        self.errors=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.on('console',lambda msg:self.errors.append(msg.text) if msg.type=='error' else None)
        self.page.on('response',lambda response:self.errors.append(f'{response.status} {response.url}') if response.status>=400 else None)
    def tearDown(self): self.context.close()
    def test_real_startup_keeps_loading_until_base_mist_mask_and_boundaries_ready(self):
        held={}; released=set()
        resources=[('assets/maps/gilneas-origins-enhanced.webp','image/webp'),('assets/maps/origins-inactive-mist.webp','image/webp'),('assets/maps/origins-inactive-mask.png','image/png')]
        for path,mime in resources:
            held[path]=[]
            def route_handler(route,request,path=path):
                if path in released: route.continue_()
                else: held[path].append(route)
            self.page.route('**/'+path,route_handler)
        self.page.goto(self.url,wait_until='domcontentloaded')
        self.page.wait_for_selector('#map-loading',state='visible')
        for path,mime in resources:
            self.page.wait_for_function('document.body.classList.contains("map-awaiting")',polling=50)
            self.assertEqual(self.page.locator('#world').evaluate('e=>getComputedStyle(e).visibility'),'hidden')
            self.assertFalse(self.page.evaluate('Boolean(window.gilneasApp?.ready)'))
            self.assertNotRegex(self.page.locator('#map-loading').inner_text(),r'\d+\s*%')
            # A request must really reach the route; DOM image readiness is not fabricated.
            deadline=100
            while not held[path] and deadline:
                self.page.wait_for_timeout(50); deadline-=1
            self.assertTrue(held[path],path+' did not request its actual raster')
            released.add(path)
            for route in held[path]: route.fulfill(status=200,content_type=mime,path=str(ROOT/path))
            held[path].clear()
        self.page.wait_for_function('window.gilneasApp?.ready',polling=50)
        self.assertFalse(self.page.locator('#map-loading').is_visible())
        self.assertEqual(self.page.locator('#world').evaluate('e=>getComputedStyle(e).visibility'),'visible')
        self.assertTrue(self.page.evaluate('document.querySelector("#base-map").complete && document.querySelector("#base-map").naturalWidth===5289'))
        self.assertTrue(self.page.evaluate('document.querySelector("#mist-map").complete && document.querySelector("#mist-map").naturalWidth>0'))
        self.assertEqual(self.page.locator('#map-frame').get_attribute('viewBox'),'0 0 3526 4548')
        self.assertEqual(self.page.locator('#map-frame').evaluate('e=>getComputedStyle(e).pointerEvents'),'none')
        self.assertTrue(self.page.evaluate('async()=>{await window.gilneasApp.boundaries.whenReady();return true;}'))
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertEqual(self.errors,[])

    def test_published_council_names_house_representatives_as_advisors_not_the_houses_themselves(self):
        self.page.goto(self.url,wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready',polling=50)
        before=self.page.evaluate('window.gilneasApp.getData()')
        self.page.locator('#council-open').click()
        expected_active=sum(member['active'] for member in before['royalCouncil']['members'])
        expected_history=sum(not member['active'] for member in before['royalCouncil']['members'])
        self.assertEqual(self.page.locator('.council-rosters .council-member').count(),expected_active)
        self.assertEqual(self.page.locator('#council-history .council-member').count(),0)
        for member in before['royalCouncil']['members']:
            if not member['active']: continue
            row=self.page.locator(f'.council-rosters [data-member-id="{member["id"]}"]')
            self.assertEqual(row.count(),1,member['id'])
            self.assertEqual(row.locator('.council-source-links a').count(),len(member['sources']))
            self.assertEqual(row.locator('.council-advisor-badge').count(),int(member['advisor']))
            if member['advisor']:
                expected='Представитель — советник короля' if member['kind']=='faction' else 'Королевский советник'
                self.assertEqual(row.locator('.council-advisor-badge').inner_text(),expected)
            if member['refId']=='noble-marley':
                self.assertNotIn('советник',row.locator('.council-member-title').inner_text().lower(),'Undated archive office must not override the early Council appointment')
            if member.get('potentialAlly'):
                self.assertEqual(row.locator('.council-potential-badge').inner_text(),'Возможный союзник')
        self.page.locator('label:has(#council-show-history)').click()
        self.assertEqual(self.page.locator('#council-history .council-member').count(),expected_history)
        self.assertEqual(self.page.locator('#council-history .council-advisor-badge').count(),0)
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertEqual(self.errors,[])

if __name__=='__main__': unittest.main()
