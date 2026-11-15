"""Actual family release, historical statuses and read-only full-snapshot exports."""
import copy
import functools
import json
import os
import threading
import unittest
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

SOURCE_ROOT=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('GILNEAS_TEST_ROOT',SOURCE_ROOT))
PREFIX=os.environ.get('GILNEAS_TEST_PREFIX','/')
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-family-release-evidence')
DRAFT='gilneas-atlas-draft-v1'
LABELS={'alive':'Жив','dead':'Мертв','unknown':'Неизвестно'}
COLORS={'alive':'rgb(94, 170, 120)','dead':'rgb(211, 121, 120)','unknown':'rgb(150, 151, 141)'}

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class FamilyRegistryRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory=ROOT.parent if PREFIX!='/' else ROOT
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(directory)))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'+PREFIX
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch(args=['--disable-renderer-backgrounding','--disable-background-timer-throttling','--disable-backgrounding-occluded-windows'])
        cls.census=json.loads((SOURCE_ROOT/'docs/noble-family-census.json').read_text())
        OUT.mkdir(parents=True,exist_ok=True)
    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.playwright.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2)
    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        self.page=self.context.new_page();self.page.set_default_timeout(10000)
        self.errors=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.on('console',lambda message:self.errors.append(message.text) if message.type=='error' else None)
        self.page.on('response',lambda response:self.errors.append(f'{response.status} {response.url}') if response.status>=400 else None)
    def tearDown(self):self.context.close()
    def boot(self):
        self.page.goto(self.url,wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=40000)
    def data(self):return self.page.evaluate('window.gilneasApp.getData()')
    def draft(self):return self.page.evaluate(f'localStorage.getItem("{DRAFT}")')
    def assert_tag(self,node,status):
        self.assertEqual(node.count(),1)
        self.assertEqual(node.text_content(),LABELS[status])
        self.assertEqual(node.get_attribute('data-life-status'),status)
        self.assertEqual(node.evaluate('e=>getComputedStyle(e).color'),COLORS[status])
    def test_01_every_reviewed_new_identity_is_in_the_current_registry_and_council_without_invented_votes(self):
        self.boot();before=self.data()
        self.assertEqual(before['meta']['publicationRevision'],'royal-council-v5')
        self.assertFalse(self.page.locator('#editing-enabled').is_checked())
        self.page.locator('#filter-nobles').click()
        ids=self.page.locator('#location-list .noble-row').evaluate_all('nodes=>nodes.map(n=>n.dataset.nobleId)')
        self.assertEqual(len(ids),len(before['nobles']));self.assertEqual(len(set(ids)),len(ids))
        self.assertEqual(ids[0],'noble-genn')
        self.assertEqual(ids[-1],'noble-archibald')
        self.assertEqual(ids[1:4],['noble-mia','noble-tess','noble-liam'])
        for addition in self.census['additions']:
            noble=addition['noble'];identifier=noble['id']
            row=self.page.locator(f'#location-list .noble-row[data-noble-id="{identifier}"]')
            self.assert_tag(row.locator('.noble-life-status'),noble['lifeStatus'])
            row.click()
            self.assertEqual(self.page.locator('#noble-name').inner_text(),noble['name'])
            self.assert_tag(self.page.locator('#noble-dossier .noble-life-status'),noble['lifeStatus'])
            self.assertEqual(self.page.locator('#noble-holdings .noble-holding').count(),0)
            self.assertIn(noble['holdingsNote'],self.page.locator('#noble-holdings').inner_text())
            if noble.get('canonicality')=='hearthstone_noncanon':
                self.assertIn('неканоническ',self.page.locator('#noble-title').inner_text()+' '+self.page.locator('#noble-description').inner_text())
            self.page.locator('[data-close="noble-dossier"]').click()
        self.page.locator('#council-open').click()
        for addition in self.census['additions']:
            member=addition['council'];row=self.page.locator(f'#royal-council [data-member-id="{member["id"]}"]')
            self.assertEqual(row.count(),int(member['active']),member['id'])
        self.page.locator('label:has(#council-show-history)').click()
        for addition in self.census['additions']:
            member=addition['council'];row=self.page.locator(f'#royal-council [data-member-id="{member["id"]}"]')
            self.assertEqual(row.count(),1)
            self.assertEqual(row.locator('.council-advisor-badge').count(),0)
            self.assertEqual(row.locator('progress').count(),2)
            self.assertEqual(row.locator('progress').evaluate_all('nodes=>nodes.map(n=>[n.max,n.value])'),[[100,member['influence']['party']],[100,member['influence']['kingdom']]])
            self.assert_tag(row.locator('.noble-life-status'),addition['noble']['lifeStatus'])
        self.page.screenshot(path=str(OUT/'family-council-desktop.png'))
        self.assertEqual(self.data(),before);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])
    def test_02_old_court_draft_enriches_without_rewriting_author_data_or_storage_on_startup(self):
        self.page.goto(self.url+'assets/data/publication-v4.json',wait_until='domcontentloaded')
        prior=json.loads((ROOT/'assets/data/publication-v4.json').read_text())
        draft=copy.deepcopy(prior)
        draft['nobles']=[n for n in draft['nobles'] if n['id']!='noble-aderic']
        draft['locations'][0]['description']='  Личный текст старой карты  '
        draft['royalCouncil']['members']=[m for m in draft['royalCouncil']['members'] if m.get('refId') not in ['noble-aderic','noble-marley']]
        draft['royalCouncil']['influence']={'royalists':31,'internationalists':27}
        draft['authorExtension']={'literal':[False,None,0,'0','  Текст  ']}
        raw=json.dumps(draft,ensure_ascii=False,indent=3)+'\n'
        self.page.evaluate('(value)=>localStorage.setItem("gilneas-atlas-draft-v1",value)',raw)
        self.boot();actual=self.data()
        self.assertEqual(actual['meta']['publicationRevision'],'royal-council-v5')
        self.assertEqual(actual['locations'][0]['description'],draft['locations'][0]['description'])
        self.assertEqual(actual['royalCouncil']['influence'],draft['royalCouncil']['influence'])
        self.assertEqual(actual['authorExtension'],draft['authorExtension'])
        self.assertFalse(any(n['id']=='noble-aderic' for n in actual['nobles']))
        self.assertFalse(any(m.get('refId')=='noble-marley' for m in actual['royalCouncil']['members']))
        for addition in self.census['additions']:
            self.assertEqual(next(n for n in actual['nobles'] if n['id']==addition['noble']['id']),addition['noble'])
        self.assertEqual(self.draft(),raw)
        self.assertFalse(self.page.locator('#editing-enabled').is_checked())
        self.page.reload(wait_until='domcontentloaded');self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=40000)
        self.assertEqual(self.data(),actual);self.assertEqual(self.draft(),raw);self.assertEqual(self.errors,[])
    def test_03_view_only_json_and_zip_downloads_preserve_the_complete_family_snapshot(self):
        self.boot();before=self.data()
        self.page.locator('#editor-open').click()
        self.assertFalse(self.page.locator('#editing-enabled').is_checked())
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        json_path=OUT/'family-full-snapshot.json';download.value.save_as(str(json_path))
        self.assertEqual(json.loads(json_path.read_text()),before)
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-site').click()
        zip_path=OUT/'family-full-site.zip';download.value.save_as(str(zip_path))
        manifest=json.loads((ROOT/'assets/runtime-manifest.json').read_text())
        with zipfile.ZipFile(zip_path) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()),set(manifest))
            self.assertEqual(json.loads(archive.read('assets/data/atlas.json')),before)
            for resource in ['assets/css/favorites.css','assets/js/noble-order.mjs','assets/js/noble-life-status.mjs','assets/js/location-links.mjs','assets/data/publication-v5.json']:
                self.assertEqual(archive.read(resource),(ROOT/resource).read_bytes())
        self.assertEqual(self.data(),before);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])

    def test_04_migration_preserves_author_deleted_optional_registries_on_startup_reload_and_json_export(self):
        self.page.goto(self.url+'assets/data/publication-v4.json',wait_until='domcontentloaded')
        prior=json.loads((ROOT/'assets/data/publication-v4.json').read_text())
        draft=copy.deepcopy(prior)
        draft.pop('royalCouncil')
        draft['meta'].pop('wallConstruction')
        draft['locations'][0]['description']='  Автор удалил Совет и журнал Стены  '
        draft['authorExtension']={'literal':[False,None,0,'0','  Не восстанавливать  ']}
        raw=json.dumps(draft,ensure_ascii=False,indent=3)+'\n'
        self.page.evaluate('raw=>localStorage.setItem("gilneas-atlas-draft-v1",raw)',raw)
        self.boot();actual=self.data()
        self.assertNotIn('royalCouncil',actual)
        self.assertNotIn('wallConstruction',actual['meta'])
        self.assertEqual(actual['meta']['publicationRevision'],'royal-council-v5')
        self.assertEqual(actual['locations'][0]['description'],draft['locations'][0]['description'])
        self.assertEqual(actual['authorExtension'],draft['authorExtension'])
        self.assertEqual(actual['factions'],draft['factions'])
        self.assertEqual(actual['territories'],draft['territories'])
        for addition in self.census['additions']:
            self.assertEqual(next(n for n in actual['nobles'] if n['id']==addition['noble']['id']),addition['noble'])
        self.assertEqual(self.draft(),raw)
        self.assertFalse(self.page.locator('#editing-enabled').is_checked())
        self.page.locator('#council-open').click()
        self.assertEqual(self.page.locator('#royal-council .council-member').count(),0)
        self.assertNotIn('royalCouncil',self.data())
        self.page.keyboard.press('Escape')
        self.page.reload(wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=40000)
        self.assertEqual(self.data(),actual)
        self.assertEqual(self.draft(),raw)
        self.assertFalse(self.page.locator('#editing-enabled').is_checked())
        self.page.locator('#editor-open').click()
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        path=OUT/'family-author-deleted-registries.json';download.value.save_as(str(path))
        self.assertEqual(json.loads(path.read_text()),actual)
        self.assertNotIn('royalCouncil',json.loads(path.read_text()))
        self.assertNotIn('wallConstruction',json.loads(path.read_text())['meta'])
        self.assertEqual(self.draft(),raw)
        self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
