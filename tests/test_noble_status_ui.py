"""Shared status tags across each view, with canonical IDs and data untouched."""
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
OUT = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-noble-status-evidence')
LABELS = {'alive':'Жив','dead':'Мертв','unknown':'Неизвестно'}
COLORS = {'alive':'rgb(94, 170, 120)','dead':'rgb(211, 121, 120)','unknown':'rgb(150, 151, 141)'}

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass

class NobleStatusUI(unittest.TestCase):
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
        self.fixture = json.loads((ROOT/'assets/data/atlas.json').read_text())
        if self._testMethodName == 'test_shared_tags_use_current_life_status_in_registry_dossier_chronicle_and_council':
            for index, noble in enumerate(self.fixture['nobles']): noble['lifeStatus'] = list(LABELS)[index % 3]
            self.page.route('**/assets/data/atlas.json', lambda route: route.fulfill(status=200,content_type='application/json',body=json.dumps(self.fixture,ensure_ascii=False)))
        self.page.goto(self.url, wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready', polling=50, timeout=25000)

    def tearDown(self): self.context.close()

    def assert_tag(self, tag, expected):
        self.assertEqual(tag.count(), 1)
        self.assertEqual(tag.text_content(), LABELS[expected])
        self.assertEqual(tag.get_attribute('data-life-status'), expected)
        self.assertEqual(tag.get_attribute('aria-label'), 'Статус: ' + LABELS[expected])
        self.assertEqual(tag.evaluate('e=>getComputedStyle(e).color'), COLORS[expected])

    def test_shared_tags_use_current_life_status_in_registry_dossier_chronicle_and_council(self):
        before = self.page.evaluate('window.gilneasApp.getData()')
        self.page.locator('#filter-nobles').click()
        self.assertEqual(self.page.locator('#location-list button.noble-row').count(), len(before['nobles']))
        for noble in before['nobles']:
            row = self.page.locator('#location-list button.noble-row').filter(has=self.page.locator('span.noble-row-name', has_text=noble['name']))
            self.assertEqual(row.get_attribute('data-noble-id'), noble['id'])
            self.assert_tag(row.locator('.noble-life-status'), noble['lifeStatus'])
            self.page.evaluate('id=>window.gilneasApp.nobleDossier.open(id)', noble['id'])
            self.assert_tag(self.page.locator('#noble-dossier .noble-life-status'), noble['lifeStatus'])
            self.page.locator('[data-close="noble-dossier"]').click()
        self.page.locator('#chronicle-open').click(); self.page.locator('#chronicle-nobles').click()
        for noble in before['nobles']:
            self.assert_tag(self.page.locator('#noble-' + noble['id'] + ' .noble-life-status'), noble['lifeStatus'])
        self.page.locator('[data-close="chronicle"]').click()
        self.page.locator('#council-open').click()
        self.page.locator('label:has(#council-show-history)').click()
        by_id = {noble['id']:noble for noble in before['nobles']}
        for member in before['royalCouncil']['members']:
            row = self.page.locator('#royal-council [data-member-id="' + member['id'] + '"]')
            if member['kind'] == 'person':
                self.assert_tag(row.locator('.noble-life-status'), by_id.get(member.get('refId'), {}).get('lifeStatus', 'unknown'))
            else: self.assertEqual(row.locator('.noble-life-status').count(), 0)
        self.page.screenshot(path=str(OUT/'council-statuses.png'))
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), before)
        self.assertIsNone(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'))
        self.assertEqual(self.errors, [])

    def test_invalid_status_import_preserves_the_live_snapshot_and_exact_saved_draft(self):
        self.page.locator('#editor-open').click()
        self.page.locator('label:has(#editing-enabled)').click()
        self.page.locator('[data-close="editor"]').click()
        before = self.page.evaluate('window.gilneasApp.getData()')
        raw = json.dumps(before, ensure_ascii=False, indent=3) + '\n'
        self.page.evaluate('raw=>localStorage.setItem("gilneas-atlas-draft-v1",raw)', raw)
        incoming = json.loads(json.dumps(before)); incoming['nobles'][0]['lifeStatus'] = ' alive '
        result = self.page.evaluate('''async text=>{try {await window.gilneasApp.importSnapshot(new File([text], 'invalid-status.json', {type:'application/json'})); return 'unexpected success';} catch(error) {return error.message;}}''', json.dumps(incoming, ensure_ascii=False))
        self.assertIn('lifeStatus', result)
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), before)
        self.assertEqual(self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")'), raw)
        self.assertEqual(self.errors, [])

if __name__ == '__main__': unittest.main()
