"""Royal Registry totals stay next to their own collapse chevron."""
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
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-registry-count-evidence')

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class RegistryCountAlignment(unittest.TestCase):
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
        self.page=self.context.new_page();self.page.set_default_timeout(10000);self.errors=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.on('console',lambda message:self.errors.append(message.text) if message.type=='error' else None)
        self.page.on('response',lambda response:self.errors.append(f'{response.status} {response.url}') if response.status>=400 else None)
        self.page.goto(self.url,wait_until='domcontentloaded');self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=40000)
    def tearDown(self):self.context.close()
    def test_counts_align_with_the_chevron_at_every_current_nesting_depth_and_viewport(self):
        before=self.page.evaluate('window.gilneasApp.getData()')
        measurements=[]
        for width,height in [(1440,1000),(390,844),(844,390),(320,640)]:
            with self.subTest(viewport=(width,height)):
                self.page.set_viewport_size({'width':width,'height':height})
                self.page.wait_for_function('Math.abs(parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--app-height"))-innerHeight)<1',polling=50)
                self.page.evaluate('''()=>{window.gilneasApp.ui.setPanel('navigation',true);for(const details of document.querySelectorAll('#location-list details'))details.open=true;}''')
                rows=self.page.locator('#location-list .faction-tree > summary, #location-list .registry-category > summary').evaluate_all('''nodes=>nodes.map(e=>{const r=e.getBoundingClientRect(),count=e.querySelector(':scope > .group-count, :scope > .category-count'),arrow=e.querySelector(':scope > .chevron'),name=e.querySelector(':scope > .group-heading, :scope > .category-name'),c=count.getBoundingClientRect(),a=arrow.getBoundingClientRect(),n=name.getBoundingClientRect();return {faction:e.closest('.faction-tree').dataset.factionId,category:e.parentElement.dataset.categoryId??null,text:count.textContent,expectedCount:e.parentElement.classList.contains('registry-category')?e.parentElement.querySelectorAll(':scope > .location-row, :scope > .object-row').length:Number(e.parentElement.dataset.locationCount),summary:{x:r.x,y:r.y,w:r.width,h:r.height},countRight:c.right,arrowLeft:a.left,arrowRight:a.right,gap:a.left-c.right,nameRight:n.right,countLeft:c.left,countCenterY:c.y+c.height/2,arrowCenterY:a.y+a.height/2,shield:e.querySelector('.faction-shield')?.getAttribute('viewBox')??null};})''')
                self.assertTrue(rows)
                self.assertTrue(any(row['faction']=='lordaeron' and row['category']=='locations' for row in rows))
                self.assertTrue(any(row['faction']=='silverlaine' and row['category']=='locations' for row in rows))
                for row in rows:
                    self.assertGreaterEqual(row['gap'],3,row)
                    self.assertLessEqual(row['gap'],10,'A total belongs beside its chevron, not in the middle: '+str(row))
                    self.assertAlmostEqual(row['gap'],7,delta=0.1,msg='The total must keep the exact shared 7px gap to its own chevron: '+str(row))
                    self.assertLessEqual(row['summary']['x']+row['summary']['w']-row['arrowRight'],10,row)
                    self.assertLessEqual(row['nameRight'],row['countLeft']-3,row)
                    self.assertAlmostEqual(row['countCenterY'],row['arrowCenterY'],delta=1,msg=str(row))
                    self.assertGreaterEqual(row['summary']['h'],31 if row['category'] else 44,row)
                    self.assertEqual(int(row['text']),row['expectedCount'])
                target=self.page.locator('#location-list details[data-faction-id="lordaeron"] > .registry-category[data-category-id="locations"] > summary')
                target.scroll_into_view_if_needed()
                self.assertTrue(target.evaluate('''e=>{const r=e.querySelector('.category-count').getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('summary')===e;}'''))
                self.page.screenshot(path=str(OUT/f'counts-{width}x{height}.png'))
                measurements.append({'viewport':[width,height],'rows':rows})
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
        (OUT/'measurements.json').write_text(json.dumps(measurements,ensure_ascii=False,indent=2)+'\n')
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertEqual(self.errors,[])
    def test_clicking_the_right_aligned_total_still_toggles_the_own_category(self):
        before=self.page.evaluate('window.gilneasApp.getData()')
        self.page.locator('#search').fill('Королевство Лордерон')
        category=self.page.locator('#location-list details[data-faction-id="lordaeron"] > .registry-category[data-category-id="locations"]')
        self.assertTrue(category.evaluate('e=>e.open'))
        category.locator(':scope > summary > .category-count').click()
        self.assertFalse(category.evaluate('e=>e.open'))
        category.locator(':scope > summary').focus();self.page.keyboard.press('Enter')
        self.assertTrue(category.evaluate('e=>e.open'))
        self.assertEqual(category.locator(':scope > summary > .category-count').inner_text(),str(category.locator(':scope > .location-row').count()))
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'),before)
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
