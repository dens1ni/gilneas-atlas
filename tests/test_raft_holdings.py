"""House Raft: real canonical navigation, preservation and clean site exports."""
import functools
import json
import threading
import unittest
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/raft-holdings/native-evidence')
DRAFT='gilneas-atlas-draft-v1'
ESTATE='location-raft-estate'
CARETAKER='location-544521a1-babb-4fea-af73-6ebb91c476e0'
HOLDINGS=['keel-harbor','aderics-repose','the-headlands',CARETAKER,ESTATE]

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class RaftHoldings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=json.loads((ROOT/'assets/data/atlas.json').read_text())
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
        self.page=self.context.new_page();self.page.set_default_timeout(15000);self.errors=[]
        self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.page.on('console',lambda m:self.errors.append(m.text) if m.type=='error' else None)
        self.page.on('response',lambda r:self.errors.append(f'{r.status} {r.url}') if r.status>=400 else None)
    def tearDown(self):self.context.close()
    def ready(self,page):
        page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=50000)
        page.wait_for_function('document.querySelector("#base-map").complete&&document.querySelector("#base-map").naturalWidth>0',polling=50)
    def boot(self,raw=None):
        if raw is not None:self.page.add_init_script('localStorage.setItem("'+DRAFT+'",'+json.dumps(raw)+');')
        self.page.goto(self.url,wait_until='domcontentloaded');self.ready(self.page)
    def data(self,page=None):return (page or self.page).evaluate('window.gilneasApp.getData()')
    def draft(self,page=None):return (page or self.page).evaluate('localStorage.getItem("'+DRAFT+'")')
    def select(self,identifier,page=None):
        page=page or self.page
        record=next(l for l in self.source['locations'] if l['id']==identifier)
        page.evaluate('window.gilneasApp.ui.setPanel("navigation",true)')
        page.locator('#filter-all').click();page.locator('#search').fill(record['name'])
        row=page.locator(f'#location-list button.location-row[data-location-id="{identifier}"]')
        row.scroll_into_view_if_needed();row.click()
        self.assertEqual(page.evaluate('window.gilneasApp.getSelectedId()'),identifier)
    def check_archive(self,path,expected):
        with zipfile.ZipFile(path) as archive:
            names=archive.namelist()
            self.assertIsNone(archive.testzip())
            self.assertEqual(len(names),len(self.manifest));self.assertEqual(len(names),len(set(names)))
            self.assertEqual(set(names),set(self.manifest))
            self.assertTrue(all(not n.startswith('/') and '..' not in Path(n).parts for n in names))
            self.assertEqual(json.loads(archive.read('assets/data/atlas.json')),expected)
            for name in names:
                if name!='assets/data/atlas.json':self.assertEqual(archive.read(name),(ROOT/name).read_bytes(),name)
    def test_01_all_five_holdings_and_estate_objects_use_the_exact_raft_identity_without_writes(self):
        self.boot();before=self.data()
        self.assertEqual(before,self.source)
        self.assertEqual(len(before['locations']),86);self.assertEqual(len(before['factions']),16)
        self.assertEqual([l['id'] for l in before['locations'] if l['faction']=='raft'],HOLDINGS+['ferry-keel-harbor'])
        self.assertTrue(self.page.evaluate('window.gilneasApp.canPlace([1163,2827])'))
        self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertIsNone(self.draft())
        types=self.page.evaluate('''async()=>{const m=await import('./assets/js/object-types.mjs');return Object.fromEntries(m.TYPE_DEFINITIONS.map(t=>[t.id,t.path]));}''')
        for identifier in HOLDINGS:
            self.select(identifier)
            record=next(l for l in before['locations'] if l['id']==identifier)
            self.assertEqual(self.page.locator('#dossier-faction').text_content(),'Дом Рафт')
            self.assertEqual(self.page.locator('#dossier-owner').text_content(),'Дом Рафт')
            self.assertEqual(self.page.locator('#dossier-description').text_content(),record['description'])
            self.assertEqual(self.page.locator('#dossier-seal .shield-field').get_attribute('d'),'M1 1H59V46.4L30 71 1 46.4Z')
            self.assertEqual(self.page.locator('#dossier-seal .shield-device').get_attribute('href'),'assets/ui/factions/raft-device.svg')
            marker=self.page.locator(f'#markers .map-marker[data-location-id="{identifier}"]')
            self.assertEqual(marker.locator('svg path').get_attribute('d'),types[record['type']])
            self.assertEqual(marker.get_attribute('data-location-id'),record['id'])
            self.assertEqual(marker.evaluate('node=>[node.style.left,node.style.top]'),[str(record['x'])+'px',str(record['y'])+'px'])
            self.assertEqual(self.page.locator('#dossier-objects .object-card').count(),len(record['objects']))
        self.assertEqual(self.page.locator('#dossier-objects .object-card').count(),2)
        for obj in next(l for l in before['locations'] if l['id']==ESTATE)['objects']:
            card=self.page.locator(f'#dossier-objects .object-card[data-object-id="{obj["id"]}"]')
            self.assertEqual(card.locator('summary .object-icon svg').get_attribute('data-type'),obj['type'])
            card.locator('summary').click()
            self.assertEqual(card.locator('.modifier.bonus').text_content(),obj['modifiers'][0]['text'])
            self.assertEqual(card.locator('.modifier.penalty').count(),0)
        self.select('keel-harbor')
        self.page.locator(f'#dossier-location-links button[data-location-link="{ESTATE}"]').click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),ESTATE)
        self.page.locator('#dossier-parent-locations button[data-location-link="keel-harbor"]').click()
        self.page.locator(f'#dossier-location-links button[data-location-link="{CARETAKER}"]').click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'),CARETAKER)
        self.assertEqual(self.data(),before);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])
        self.select('the-headlands');self.page.screenshot(path=str(OUT/'raft-forest-desktop.png'))
        self.select(ESTATE);self.page.screenshot(path=str(OUT/'raft-estate-desktop.png'))
    def test_02_readonly_json_zip_and_both_clean_publish_paths_preserve_raft_and_every_runtime_byte(self):
        self.boot();before=self.data();self.page.locator('#editor-open').click()
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        snapshot=OUT/'raft-readonly.json';download.value.save_as(str(snapshot));self.assertEqual(json.loads(snapshot.read_text()),before)
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-site').click()
        path=OUT/'raft-readonly.zip';download.value.save_as(str(path));self.check_archive(path,before)
        with zipfile.ZipFile(path) as archive:
            for mode in ['root','subpath']:
                host=OUT/('clean-'+mode);host.mkdir()
                publish=host if mode=='root' else host/'gilneas-atlas';publish.mkdir(exist_ok=True)
                archive.extractall(publish)
                server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(host)))
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                fresh=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce',accept_downloads=True)
                page=fresh.new_page();errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('response',lambda r:errors.append(f'{r.status} {r.url}') if r.status>=400 else None)
                try:
                    prefix='/' if mode=='root' else '/gilneas-atlas/'
                    page.goto(f'http://127.0.0.1:{server.server_port}'+prefix,wait_until='domcontentloaded');self.ready(page)
                    self.assertEqual(self.data(page),before);self.assertIsNone(self.draft(page))
                    self.assertFalse(page.locator('#editing-enabled').is_checked())
                    self.select(ESTATE,page);self.assertEqual(page.locator('#dossier-faction').text_content(),'Дом Рафт')
                    page.screenshot(path=str(OUT/('raft-clean-'+mode+'.png')))
                    page.locator('#editor-open').click()
                    with page.expect_download(timeout=60000) as download:page.locator('#export-site').click()
                    reexport=OUT/('raft-reexport-'+mode+'.zip');download.value.save_as(str(reexport));self.check_archive(reexport,before)
                    self.assertEqual(self.data(page),before);self.assertIsNone(self.draft(page));self.assertEqual(errors,[])
                finally:fresh.close();server.shutdown();server.server_close();thread.join(timeout=2)
        self.assertEqual(self.data(),before);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])
    def test_03_existing_literal_draft_and_mobile_navigation_keep_the_new_holdings_without_rewriting_storage(self):
        draft=json.loads(json.dumps(self.source));draft['authorExtension']={'literal':[None,False,0,'0','  Рафт  ']}
        raw=json.dumps(draft,ensure_ascii=False,indent=3)+'\n';self.boot(raw)
        self.assertEqual(self.data(),draft);self.assertEqual(self.draft(),raw)
        for width,height in [(390,844),(844,390)]:
            self.page.set_viewport_size({'width':width,'height':height})
            self.page.wait_for_function('height=>Math.abs(parseFloat(document.documentElement.style.getPropertyValue("--app-height"))-height)<1',arg=height,polling=50)
            self.page.evaluate('window.gilneasApp.selectId("'+ESTATE+'")')
            self.assertEqual(self.page.locator('#dossier-title').text_content(),'Поместье Дома Рафт')
            self.assertEqual(self.page.locator('#dossier-faction').text_content(),'Дом Рафт')
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
            self.page.screenshot(path=str(OUT/f'raft-mobile-{width}x{height}.png'))
            self.assertEqual(self.data(),draft);self.assertEqual(self.draft(),raw)
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page)
        self.assertEqual(self.data(),draft);self.assertEqual(self.draft(),raw)
        self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
