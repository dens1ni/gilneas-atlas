"""Real zero-start Wall history, saved-author migration and clean exports."""
import functools
import json
import threading
import unittest
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/wall-base-zero/native-evidence')
DRAFT='gilneas-atlas-draft-v1'
EVENT='wall-event-f885cf03-ff4a-46aa-b195-436b5f0d9622'

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

class WallBaseZero(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=json.loads((ROOT/'assets/data/atlas.json').read_text())
        cls.author=json.loads((ROOT/'assets/data/publication-author-v5.json').read_text())
        cls.manifest=json.loads((ROOT/'assets/runtime-manifest.json').read_text())
        cls.approved_event=json.loads((ROOT/'tests/fixtures/crown-order-event.json').read_text())
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
        self.watch(self.page,self.errors)
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
    def check_zero_history(self,page):
        track=self.source['meta']['wallConstruction']
        self.assertEqual(track['baseValue'],0);self.assertEqual(track['value'],10)
        original=self.author['meta']['wallConstruction']['events'][0]
        self.assertEqual(original['name'],'Седогрив вкусно покушал','The immutable author input remains original')
        self.assertEqual(track['events'],[self.approved_event])
        self.assertEqual([(e['id'],e['delta'],[(v['id'],v['kind']) for v in e['effects']]) for e in track['events']],[(e['id'],e['delta'],[(v['id'],v['kind']) for v in e['effects']]) for e in self.author['meta']['wallConstruction']['events']])
        self.assertEqual(page.locator('#wall-progress-value').text_content(),'10 / 100')
        self.assertEqual(page.locator('#wall-progress').get_attribute('value'),'10')
        self.assertFalse(page.locator('#editing-enabled').is_checked())
        page.locator('#wall-history-open').click()
        self.assertEqual(page.locator('#wall-journal-progress-value').text_content(),'10 / 100');self.assertNotIn('Начальная отметка',page.locator('#wall-journal').inner_text())
        self.assertEqual(page.locator('#wall-event-history .wall-event-card').count(),1)
        card=page.locator(f'#wall-event-history .wall-event-card[data-wall-event-id="{EVENT}"]')
        event=track['events'][0]
        self.assertEqual(card.locator('h3').text_content(),event['name'])
        self.assertEqual(card.locator('.wall-event-description').text_content(),event['description'])
        self.assertEqual(card.locator('.wall-event-progress').text_content(),'+10 · 0 → 10')
        self.assertEqual(card.locator('.wall-event-effect.bonus').text_content(),'Бонус: '+event['effects'][0]['text'])
        self.assertEqual(card.locator('.wall-event-effect.penalty').text_content(),'Штраф: '+event['effects'][1]['text'])
        self.assertFalse(page.locator('#wall-event-form').is_visible())
        self.assertFalse(card.locator('[data-wall-event-delete]').is_visible())
        self.assertEqual(self.data(page)['meta']['wallConstruction'],track)
    def test_01_fresh_readonly_history_shows_zero_base_and_the_complete_original_event_after_reload(self):
        self.boot();self.assertEqual(self.data(),self.source);self.assertIsNone(self.draft())
        for width,height in [(1440,1000),(390,844),(844,390)]:
            self.page.set_viewport_size({'width':width,'height':height})
            self.page.wait_for_function('height=>Math.abs(parseFloat(document.documentElement.style.getPropertyValue("--app-height"))-height)<1',arg=height,polling=50)
            self.check_zero_history(self.page)
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
            self.page.screenshot(path=str(OUT/f'wall-zero-{width}x{height}.png'))
            self.page.locator('[data-close=wall-journal]').click()
            self.assertEqual(self.data(),self.source);self.assertIsNone(self.draft())
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page);self.check_zero_history(self.page)
        self.assertEqual(self.data(),self.source);self.assertIsNone(self.draft());self.assertEqual(self.errors,[])
    def test_02_saved_author_input_migrates_without_storage_writes_and_exports_zero_base_to_both_publish_paths(self):
        raw=json.dumps(self.author,ensure_ascii=False,indent=3)+'\n';self.boot(raw)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw)
        self.check_zero_history(self.page);self.page.locator('[data-close=wall-journal]').click()
        self.page.locator('#editor-open').click()
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-json').click()
        snapshot=OUT/'wall-zero.json';download.value.save_as(str(snapshot));self.assertEqual(json.loads(snapshot.read_text()),self.source)
        with self.page.expect_download(timeout=60000) as download:self.page.locator('#export-site').click()
        path=OUT/'wall-zero.zip';download.value.save_as(str(path))
        with zipfile.ZipFile(path) as archive:
            names=archive.namelist()
            self.assertIsNone(archive.testzip());self.assertEqual(len(names),len(self.manifest));self.assertEqual(len(names),len(set(names)))
            self.assertEqual(set(names),set(self.manifest))
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
                    self.assertEqual(self.data(page),self.source);self.assertIsNone(self.draft(page));self.check_zero_history(page)
                    page.screenshot(path=str(OUT/('wall-zero-clean-'+mode+'.png')))
                    page.locator('[data-close=wall-journal]').click();page.reload(wait_until='domcontentloaded');self.ready(page)
                    self.assertEqual(self.data(page),self.source);self.assertIsNone(self.draft(page));self.assertEqual(errors,[])
                finally:context.close();server.shutdown();server.server_close();thread.join(timeout=2)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw)
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page);self.check_zero_history(self.page)
        self.assertEqual(self.data(),self.source);self.assertEqual(self.draft(),raw);self.assertEqual(self.errors,[])
    def test_03_a_later_author_event_and_literal_notes_survive_real_bootstrap_reload(self):
        draft=json.loads(json.dumps(self.author));track=draft['meta']['wallConstruction']
        track['events'].append({'id':'wall-zero-extra-native-event','name':'  Своя задержка  ','description':'  Не терять пробелы  ','delta':-4,'effects':[]})
        track['value']=16;track['note']='  Личный журнал  '
        raw=json.dumps(draft,ensure_ascii=False,indent=3)+'\n';expected=json.loads(json.dumps(self.source));expected['meta']['wallConstruction']=track
        self.boot(raw);self.assertEqual(self.data(),expected);self.assertEqual(self.draft(),raw)
        self.assertEqual(self.page.locator('#wall-progress-value').text_content(),'16 / 100')
        self.page.locator('#wall-history-open').click()
        self.assertEqual(self.page.locator('#wall-journal-progress-value').text_content(),'16 / 100');self.assertNotIn('Начальная отметка',self.page.locator('#wall-journal').inner_text())
        self.assertEqual(self.page.locator('#wall-event-history .wall-event-card').count(),2)
        self.assertEqual(self.page.locator(f'[data-wall-event-id="{EVENT}"] .wall-event-description').text_content(),self.author['meta']['wallConstruction']['events'][0]['description'])
        self.page.reload(wait_until='domcontentloaded');self.ready(self.page)
        self.assertEqual(self.data(),expected);self.assertEqual(self.draft(),raw)
        self.assertFalse(self.page.locator('#editing-enabled').is_checked());self.assertEqual(self.errors,[])

if __name__=='__main__':unittest.main()
