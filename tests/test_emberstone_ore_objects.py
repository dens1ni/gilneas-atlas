"""Emberstone ore objects through real native dossiers and complete exports."""
import functools
import json
import threading
import unittest
import zipfile
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/emberstone-ore-objects/native-evidence')
DRAFT='gilneas-atlas-draft-v1'
WHEEL='object-emberstone-ore-crushing-waterwheel'
COPPER='object-emberstone-copper-deposit'
TIN='object-emberstone-tin-deposit'

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class EmberstoneOreObjects(unittest.TestCase):
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
    def select(self,page,identifier):
        location=next(l for l in self.source['locations'] if l['id']==identifier)
        page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)')
        page.locator('#filter-all').click();page.locator('#search').fill(location['name'])
        row=page.locator(f'#location-list button.location-row[data-location-id="{identifier}"]')
        row.scroll_into_view_if_needed();row.click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),identifier)
    def check_objects(self,page,identifier,expected_ids):
        location=next(l for l in self.source['locations'] if l['id']==identifier)
        cards=page.locator('#dossier-objects .object-card')
        self.assertEqual(cards.evaluate_all('nodes=>nodes.map(node=>node.dataset.objectId)'),expected_ids)
        for object_id in expected_ids:
            record=next(o for o in location['objects'] if o['id']==object_id)
            card=page.locator(f'#dossier-objects .object-card[data-object-id="{object_id}"]')
            self.assertEqual(card.locator('.object-title').text_content(),record['name'])
            self.assertEqual(card.locator('.object-icon svg').get_attribute('data-type'),record['type'])
            self.assertEqual(card.locator('.object-faction-badge').text_content(),'Дом Марли')
            self.assertEqual(card.locator('.object-icon .faction-shield').count(),0)
            if not card.evaluate('node=>node.open'):card.locator('summary').click()
            self.assertEqual(card.locator('.object-description').text_content(),record['description'])
            self.assertEqual(card.locator('.modifier').all_text_contents(),[m['text'] for m in record['modifiers']])
            if object_id in [WHEEL,COPPER,TIN]:
                self.assertEqual(card.locator('.amount').count(),0)
                self.assertEqual(card.locator('.object-sources').count(),0)
                self.assertFalse(card.locator('.object-actions').is_visible())
    def check_both_places(self,page):
        self.select(page,'emberstone-village')
        self.check_objects(page,'emberstone-village',['object-043cd8bc-00a8-57c7-9ab5-bd58cb000164',WHEEL,'object-emberstone-watch-post'])
        page.locator('#dossier-location-links button.location-link-row[data-location-link="emberstone-mine"]').click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),'emberstone-mine')
        self.check_objects(page,'emberstone-mine',['object-2cd23821-608a-534c-9d26-125f4dd6fba5',COPPER,TIN])
        page.locator('#dossier-parent-locations button.location-link-row[data-location-link="emberstone-village"]').click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),'emberstone-village')
        self.assertEqual(self.data(page),self.source)
    def test_01_fresh_readonly_cards_have_the_requested_types_and_descriptions_with_original_objects_retained(self):
        self.boot();self.assertEqual(self.data(),self.source);self.assertIsNone(self.draft())
        self.assertEqual(sum(len(l['objects']) for l in self.source['locations']),98)
        self.check_both_places(self.page)
        self.assertIsNone(self.draft());self.assertFalse(self.page.locator('#editing-enabled').is_checked())
        self.page.screenshot(path=str(OUT/'emberstone-waterwheel-desktop.png'))
        self.select(self.page,'emberstone-mine');self.check_objects(self.page,'emberstone-mine',['object-2cd23821-608a-534c-9d26-125f4dd6fba5',COPPER,TIN])
        self.page.screenshot(path=str(OUT/'emberstone-deposits-desktop.png'))
        self.assertEqual(self.data(),self.source);self.assertEqual(self.errors,[])
    def test_02_original_author_draft_adopts_all_three_objects_without_storage_writes_and_exports_boot_at_root_and_subpath(self):
        raw=json.dumps(self.author,ensure_ascii=False,indent=3)+'\n';self.boot(raw)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw);self.check_both_places(self.page)
        self.page.locator('#editor-open').click()
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        snapshot=OUT/'emberstone-ore.json';download.value.save_as(str(snapshot));self.assertEqual(json.loads(snapshot.read_text()),self.source)
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-site').click()
        path=OUT/'emberstone-ore.zip';download.value.save_as(str(path))
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
                    self.assertEqual(self.data(page),self.source);self.assertIsNone(self.draft(page));self.check_both_places(page)
                    self.assertFalse(page.locator('#editing-enabled').is_checked());self.assertEqual(errors,[])
                finally:context.close();server.shutdown();server.server_close();thread.join(timeout=2)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw)
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page);self.check_both_places(self.page)
        self.assertEqual(self.draft(),raw);self.assertEqual(self.errors,[])
    def test_03_current_literal_draft_preserves_all_objects_on_phone_portrait_landscape_and_reload(self):
        draft=json.loads(json.dumps(self.source));draft['authorExtension']={'literal':[None,False,0,'0','  Руда  ']}
        raw=json.dumps(draft,ensure_ascii=False,indent=3)+'\n';self.boot(raw)
        for width,height in [(390,844),(844,390)]:
            self.page.set_viewport_size({'width':width,'height':height})
            self.page.wait_for_function('height=>Math.abs(parseFloat(document.documentElement.style.getPropertyValue("--app-height"))-height)<1',arg=height,polling=50)
            self.select(self.page,'emberstone-village');self.check_objects(self.page,'emberstone-village',['object-043cd8bc-00a8-57c7-9ab5-bd58cb000164',WHEEL,'object-emberstone-watch-post'])
            self.select(self.page,'emberstone-mine');self.check_objects(self.page,'emberstone-mine',['object-2cd23821-608a-534c-9d26-125f4dd6fba5',COPPER,TIN])
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
            self.assertEqual(self.data(),draft);self.assertEqual(self.draft(),raw)
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page)
        self.assertEqual(self.data(),draft);self.assertEqual(self.draft(),raw)
        self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
