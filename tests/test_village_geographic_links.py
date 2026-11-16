"""Two village links resolve original map records without changing ownership."""
import functools
import json
import threading
import unittest
import zipfile
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/village-geographic-links/native-evidence')
DRAFT='gilneas-atlas-draft-v1'
GRAY='location-df0aa1e2-31ba-43fa-b6b0-84c7733f625a'
MOSSY='location-fb88bb30-c639-4f75-a142-92445555a772'
PAIRS=[('northern-headlands',GRAY,['galewatch-lighthouse',GRAY]),('northgate-woods',MOSSY,[MOSSY])]

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class VillageGeographicLinks(unittest.TestCase):
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
    def check_pair(self,page,parent_id,child_id,expected_links):
        parent=next(l for l in self.source['locations'] if l['id']==parent_id)
        child=next(l for l in self.source['locations'] if l['id']==child_id)
        page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)')
        page.locator('#filter-all').click();page.locator('#search').fill(parent['name'])
        entry=page.locator(f'#location-list button.location-row[data-location-id="{parent_id}"]')
        entry.scroll_into_view_if_needed();entry.click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),parent_id)
        rows=page.locator('#dossier-location-links button.location-link-row')
        self.assertEqual(rows.evaluate_all('nodes=>nodes.map(node=>node.dataset.locationLink)'),expected_links)
        self.assertEqual(page.locator('#dossier-objects .object-card').count(),len(parent['objects']))
        self.assertEqual(page.locator(f'#dossier-objects [data-object-id="{child["objects"][0]["id"]}"]').count(),0)
        link=page.locator(f'#dossier-location-links button.location-link-row[data-location-link="{child_id}"]')
        self.assertEqual(link.locator('.location-link-name').text_content(),child['name'])
        link.scroll_into_view_if_needed();link.click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),child_id)
        self.assertEqual(page.locator('#dossier-title').text_content(),child['name'])
        self.assertEqual(page.locator('#dossier-description').text_content(),child['description'])
        self.assertEqual(page.locator('#dossier-faction').text_content(),'Королевство Гилнеас')
        self.assertEqual(page.locator('#dossier-objects .object-card').count(),len(child['objects']))
        parents=page.locator('#dossier-parent-locations button.location-link-row')
        self.assertEqual(parents.evaluate_all('nodes=>nodes.map(node=>node.dataset.locationLink)'),[parent_id])
        back=parents.first;back.scroll_into_view_if_needed();back.click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),parent_id)
        self.assertEqual(self.data(page),self.source)
    def test_01_both_native_village_links_and_returns_keep_complete_snapshot_and_exact_raw_draft_on_desktop_phone_reload(self):
        self.boot();self.assertEqual(self.data(),self.source);self.assertIsNone(self.draft())
        for pair in PAIRS:self.check_pair(self.page,*pair)
        raw=json.dumps(self.source,ensure_ascii=False,indent=3)+'\n';self.page.evaluate('raw=>localStorage.setItem("'+DRAFT+'",raw)',raw)
        evidence=[]
        for width,height in [(1440,1000),(390,844)]:
            self.page.set_viewport_size({'width':width,'height':height})
            self.page.wait_for_function('height=>Math.abs(parseFloat(document.documentElement.style.getPropertyValue("--app-height"))-height)<1',arg=height,polling=50)
            for pair in PAIRS:
                self.check_pair(self.page,*pair)
                evidence.append({'viewport':[width,height],'parentId':pair[0],'childId':pair[1],'fullSnapshotExact':self.data()==self.source,'rawDraftExact':self.draft()==raw})
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
            self.assertEqual(self.draft(),raw)
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page)
        for pair in PAIRS:self.check_pair(self.page,*pair)
        self.assertEqual(self.draft(),raw);self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertEqual(self.errors,[])
        self.assertEqual(len(evidence),4);self.assertTrue(all(row['fullSnapshotExact'] and row['rawDraftExact'] for row in evidence))
        (OUT/'village-link-readback.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    def test_02_saved_original_author_adopts_both_links_and_real_exports_preserve_every_runtime_byte(self):
        raw=json.dumps(self.author,ensure_ascii=False,indent=3)+'\n';self.boot(raw)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw)
        for pair in PAIRS:self.check_pair(self.page,*pair)
        self.page.locator('#editor-open').click()
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        snapshot=OUT/'village-links.json';download.value.save_as(str(snapshot));self.assertEqual(json.loads(snapshot.read_text()),self.source)
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-site').click()
        path=OUT/'village-links.zip';download.value.save_as(str(path))
        with zipfile.ZipFile(path) as archive:
            names=archive.namelist();self.assertIsNone(archive.testzip());self.assertEqual(len(names),len(set(names)));self.assertEqual(set(names),set(self.manifest))
            self.assertTrue(all(not name.startswith('/') and '..' not in Path(name).parts for name in names))
            self.assertEqual(json.loads(archive.read('assets/data/atlas.json')),self.source)
            for name in names:
                if name!='assets/data/atlas.json':self.assertEqual(archive.read(name),(ROOT/name).read_bytes(),name)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw);self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
