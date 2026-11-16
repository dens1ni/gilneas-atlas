"""The requested silver resource through real readonly dossiers and exports."""
import functools
import json
import threading
import unittest
import zipfile
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/silver-mine-deposits/native-evidence')
DRAFT='gilneas-atlas-draft-v1'
MINE='deep-elem-mine'
SILVER='object-deep-elem-silver-deposits'
ASSAY='object-391326bb-4b22-5b76-9271-adb1d8e12d18'

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class SilverMineDeposits(unittest.TestCase):
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
    def check_card(self,page):
        mine=next(l for l in self.source['locations'] if l['id']==MINE)
        page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)')
        page.locator('#filter-all').click();page.locator('#search').fill(mine['name'])
        row=page.locator(f'#location-list button.location-row[data-location-id="{MINE}"]');row.scroll_into_view_if_needed();row.click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),MINE)
        self.assertEqual(page.locator('#dossier-title').text_content(),'Серебряный рудник')
        self.assertEqual(page.locator('#dossier-faction').text_content(),next(f['name'] for f in self.source['factions'] if f['id']=='lordaeron'))
        self.assertEqual(page.locator('#dossier-objects .object-card').evaluate_all('nodes=>nodes.map(node=>node.dataset.objectId)'),[ASSAY,SILVER])
        for object_id in [ASSAY,SILVER]:
            record=next(o for o in mine['objects'] if o['id']==object_id)
            card=page.locator(f'#dossier-objects .object-card[data-object-id="{object_id}"]')
            self.assertEqual(card.locator('.object-title').text_content(),record['name'])
            self.assertEqual(card.locator('.object-icon svg').get_attribute('data-type'),record['type'])
            if not card.evaluate('node=>node.open'):card.locator('summary').click()
            self.assertEqual(card.locator('.object-description').text_content(),record['description'])
            self.assertEqual(card.locator('.modifier').all_text_contents(),[m['text'] for m in record['modifiers']])
            if object_id==SILVER:
                self.assertEqual(card.locator('.amount').count(),0)
                self.assertEqual(card.locator('.object-owner-badge').count(),0)
                self.assertEqual(card.locator('.object-sources').count(),0)
                self.assertFalse(card.locator('.object-actions').is_visible())
        self.assertFalse(page.locator('#editing-enabled').is_checked())
        self.assertEqual(self.data(page),self.source)
    def test_01_silver_card_and_assay_yard_are_readable_without_data_or_draft_writes(self):
        self.boot();self.assertEqual(self.data(),self.source);self.assertIsNone(self.draft());self.check_card(self.page)
        card=self.page.locator(f'#dossier-objects .object-card[data-object-id="{SILVER}"]')
        card.scroll_into_view_if_needed();self.page.screenshot(path=str(OUT/'silver-deposits-desktop.png'))
        self.assertIsNone(self.draft());self.assertEqual(self.errors,[])
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page);self.check_card(self.page)
        self.assertIsNone(self.draft());self.assertEqual(self.errors,[])
    def test_02_author_draft_migration_json_zip_and_clean_root_subpath_preserve_the_complete_silver_record(self):
        raw=json.dumps(self.author,ensure_ascii=False,indent=3)+'\n';self.boot(raw)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw);self.check_card(self.page)
        self.page.locator('#editor-open').click()
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        snapshot=OUT/'silver-deposits.json';download.value.save_as(str(snapshot));self.assertEqual(json.loads(snapshot.read_text()),self.source)
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-site').click()
        path=OUT/'silver-deposits.zip';download.value.save_as(str(path))
        with zipfile.ZipFile(path) as archive:
            names=archive.namelist();self.assertIsNone(archive.testzip());self.assertEqual(len(names),len(set(names)));self.assertEqual(set(names),set(self.manifest))
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
                    self.check_card(page);self.assertIsNone(self.draft(page));self.assertEqual(errors,[])
                finally:context.close();server.shutdown();server.server_close();thread.join(timeout=2)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw)
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page);self.check_card(self.page)
        self.assertEqual(self.draft(),raw);self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
