"""Northern Headlands → original Storm Lighthouse through native navigation."""
import functools
import json
import threading
import unittest
import zipfile
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/northern-cape-lighthouse-link/native-evidence')
PARENT='northern-headlands'
CHILD='galewatch-lighthouse'
DRAFT='gilneas-atlas-draft-v1'

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class NorthernCapeLighthouseLink(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=json.loads((ROOT/'assets/data/atlas.json').read_text())
        cls.author=json.loads((ROOT/'assets/data/publication-author-v5.json').read_text())
        cls.manifest=json.loads((ROOT/'assets/runtime-manifest.json').read_text())
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}/'
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows'])
        OUT.mkdir(parents=True,exist_ok=True)
    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.playwright.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2)
    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce',accept_downloads=True)
        self.page=self.context.new_page();self.page.set_default_timeout(15000);self.errors=[];self.watch(self.page,self.errors)
    def tearDown(self):self.context.close()
    def watch(self,page,errors):
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.on('response',lambda r:errors.append(f'{r.status} {r.url}') if r.status>=400 else None)
    def ready(self,page):
        page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=50000)
        page.wait_for_function('document.querySelector("#base-map").complete&&document.querySelector("#base-map").naturalWidth>0',polling=50)
    def boot(self,raw=None):
        if raw is not None:self.page.add_init_script('localStorage.setItem("'+DRAFT+'",'+json.dumps(raw)+');')
        self.page.goto(self.url,wait_until='domcontentloaded');self.ready(self.page)
    def data(self,page=None):return (page or self.page).evaluate('window.gilneasApp.getData()')
    def draft(self,page=None):return (page or self.page).evaluate('localStorage.getItem("'+DRAFT+'")')
    def check_navigation(self,page):
        parent=next(l for l in self.source['locations'] if l['id']==PARENT)
        child=next(l for l in self.source['locations'] if l['id']==CHILD)
        page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)')
        page.locator('#filter-all').click();page.locator('#search').fill(parent['name'])
        entry=page.locator(f'#location-list button.location-row[data-location-id="{PARENT}"]')
        entry.scroll_into_view_if_needed();entry.click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),PARENT)
        self.assertEqual(page.locator('#dossier-title').text_content(),parent['name'])
        rows=page.locator('#dossier-location-links button.location-link-row')
        self.assertEqual(rows.count(),2)
        self.assertEqual(rows.evaluate_all('nodes=>nodes.map(node=>node.dataset.locationLink)'),[CHILD,'location-df0aa1e2-31ba-43fa-b6b0-84c7733f625a'])
        row=page.locator(f'#dossier-location-links button.location-link-row[data-location-link="{CHILD}"]');self.assertEqual(row.get_attribute('data-location-link'),CHILD)
        self.assertEqual(row.locator('.location-link-name').text_content(),child['name'])
        self.assertEqual(row.locator('svg').first.get_attribute('data-type'),'lighthouse')
        self.assertEqual(page.locator('#dossier-objects .object-card').count(),len(parent['objects']))
        self.assertEqual(page.locator(f'#dossier-objects [data-object-id="{child["objects"][0]["id"]}"]').count(),0,'Reference does not copy child bonuses into the cape')
        row.scroll_into_view_if_needed();row.click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),CHILD)
        self.assertEqual(page.locator('#dossier-title').text_content(),child['name'])
        self.assertEqual(page.locator('#dossier-type').text_content(),'Маяк')
        self.assertEqual(page.locator('#dossier-faction').text_content(),'Королевство Гилнеас')
        self.assertEqual(page.locator('#dossier-objects .object-card').count(),len(child['objects']))
        card=page.locator(f'#dossier-objects .object-card[data-object-id="{child["objects"][0]["id"]}"]')
        card.locator('summary').click()
        self.assertEqual(card.locator('.modifier.bonus').text_content(),child['objects'][0]['modifiers'][0]['text'])
        back=page.locator(f'#dossier-parent-locations button.location-link-row[data-location-link="{PARENT}"]')
        self.assertEqual(back.count(),1);back.scroll_into_view_if_needed();back.click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),PARENT)
        self.assertEqual(self.data(page),self.source)
    def test_01_native_cape_lighthouse_return_preserves_full_snapshot_and_exact_draft_at_desktop_and_phone(self):
        self.boot();self.assertEqual(self.data(),self.source);self.assertIsNone(self.draft())
        self.check_navigation(self.page);self.assertIsNone(self.draft())
        raw=json.dumps(self.source,ensure_ascii=False,indent=3)+'\n'
        self.page.evaluate('raw=>localStorage.setItem("'+DRAFT+'",raw)',raw)
        for width,height in [(1440,1000),(390,844)]:
            self.page.set_viewport_size({'width':width,'height':height})
            self.page.wait_for_function('height=>Math.abs(parseFloat(document.documentElement.style.getPropertyValue("--app-height"))-height)<1',arg=height,polling=50)
            self.check_navigation(self.page)
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
            self.page.screenshot(path=str(OUT/f'northern-cape-link-{width}x{height}.png'))
            self.assertEqual(self.draft(),raw)
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page);self.check_navigation(self.page)
        self.assertEqual(self.draft(),raw);self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertEqual(self.errors,[])
    def test_02_old_author_draft_adopts_the_link_and_current_json_zip_boots_cleanly_at_root_and_subpath(self):
        raw=json.dumps(self.author,ensure_ascii=False,indent=3)+'\n';self.boot(raw)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw);self.check_navigation(self.page)
        self.page.locator('#editor-open').click()
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        snapshot=OUT/'northern-cape-link.json';download.value.save_as(str(snapshot));self.assertEqual(json.loads(snapshot.read_text()),self.source)
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-site').click()
        path=OUT/'northern-cape-link.zip';download.value.save_as(str(path))
        with zipfile.ZipFile(path) as archive:
            names=archive.namelist();self.assertIsNone(archive.testzip())
            self.assertEqual(len(names),len(set(names)));self.assertEqual(set(names),set(self.manifest))
            self.assertTrue(all(not name.startswith('/') and '..' not in Path(name).parts for name in names))
            self.assertEqual(json.loads(archive.read('assets/data/atlas.json')),self.source)
            for name in names:
                if name!='assets/data/atlas.json':self.assertEqual(archive.read(name),(ROOT/name).read_bytes(),name)
            for mode in ['root','subpath']:
                host=OUT/('clean-'+mode);host.mkdir()
                target=host if mode=='root' else host/'gilneas-atlas';target.mkdir(exist_ok=True);archive.extractall(target)
                server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(host)))
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                page=context.new_page();errors=[];self.watch(page,errors)
                try:
                    prefix='/' if mode=='root' else '/gilneas-atlas/'
                    page.goto(f'http://127.0.0.1:{server.server_port}'+prefix,wait_until='domcontentloaded');self.ready(page)
                    self.assertEqual(self.data(page),self.source);self.assertIsNone(self.draft(page));self.check_navigation(page)
                    self.assertFalse(page.locator('#editing-enabled').is_checked());self.assertEqual(errors,[])
                finally:context.close();server.shutdown();server.server_close();thread.join(timeout=2)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw);self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
