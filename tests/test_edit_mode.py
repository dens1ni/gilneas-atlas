"""Global editing opt-in, exercised through the real application."""
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
SCRATCH = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-edit-mode-evidence')

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass

class EditMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = ROOT.parent if PREFIX != '/' else ROOT
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(directory)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}' + PREFIX
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(args=['--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'])
        SCRATCH.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.playwright.stop()
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':1440, 'height':1000}, reduced_motion='reduce', accept_downloads=True)
        self.page = self.context.new_page(); self.page.set_default_timeout(8000)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
        # Memory-only full-snapshot fixtures, not production author data.
        fixture_targets = {
            'test_02_checkbox_reveals_all_dossier_actions_then_removes_them_without_gaps_or_writes': 'northern-headlands',
            'test_03_all_windows_keep_viewing_but_hide_dynamic_editing_and_cancel_forms_when_disabled': 'northern-headlands',
            'test_07_reading_views_are_compact_and_native_toggle_fits_desktop_portrait_and_landscape': 'northern-headlands',
            'test_empty_canonical_container_allows_its_first_object_only_after_editing_opt_in': 'ambermill',
        }
        if self._testMethodName in fixture_targets:
            fixture = json.loads((ROOT / 'assets/data/atlas.json').read_text())
            location = next(record for record in fixture['locations'] if record['id'] == fixture_targets[self._testMethodName])
            # Change only this container's own objects; retain all links and records.
            location['objects'] = []
            if self._testMethodName == 'test_02_checkbox_reveals_all_dossier_actions_then_removes_them_without_gaps_or_writes':
                location['objects'] = [{'id':'editing-test-object', 'name':'Проверочный объект теста', 'type':'building', 'description':'Только тестовый снимок — не production', 'modifiers':[]}]
            self.page.route('**/assets/data/atlas.json', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps(fixture, ensure_ascii=False)))
        self.page.goto(self.url, wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready', polling=50, timeout=25000)
        self.page.wait_for_function('document.querySelector("#base-map").complete && document.querySelector("#base-map").naturalWidth > 0', polling=50)

    def tearDown(self): self.context.close()

    def data(self): return self.page.evaluate('window.gilneasApp.getData()')
    def draft(self): return self.page.evaluate('localStorage.getItem("gilneas-atlas-draft-v1")')
    def editor(self):
        if not self.page.locator('#editor').is_visible(): self.page.locator('#editor-open').click()
    def toggle(self):
        self.editor(); self.page.locator('label:has(#editing-enabled)').click()
    def close_editor(self): self.page.locator('[data-close="editor"]').click()

    def test_01_new_visit_is_view_only_and_editor_is_compact_without_writing_data(self):
        before = self.data(); self.assertIsNone(self.draft())
        self.page.evaluate('window.gilneasApp.selectId("northern-headlands")')
        self.assertFalse(self.page.locator('#dossier-edit').is_visible(), 'Atlas must start with editing hidden')
        self.assertFalse(self.page.locator('#dossier-add-object').is_visible())
        self.assertTrue(self.page.locator('#dossier-favorite').is_visible())
        self.assertTrue(self.page.locator('#dossier-focus').is_visible())
        self.editor()
        checkbox = self.page.locator('#editing-enabled')
        self.assertEqual(checkbox.count(), 1)
        self.assertFalse(checkbox.is_checked())
        self.assertIn('Включить режим редактирования', self.page.locator('label:has(#editing-enabled)').inner_text())
        for selector in ['.editor-actions', '.editor-selection', '.destructive-actions', 'label:has(#import-json)']:
            self.assertFalse(self.page.locator(selector).is_visible(), selector)
        self.assertTrue(self.page.locator('#export-json').is_visible())
        self.assertTrue(self.page.locator('#export-site').is_visible())
        self.page.screenshot(path=str(SCRATCH / 'editor-view-desktop.png'))
        self.assertEqual(self.data(), before); self.assertIsNone(self.draft())
        self.assertEqual(self.errors, [])

    def test_02_checkbox_reveals_all_dossier_actions_then_removes_them_without_gaps_or_writes(self):
        before = self.data()
        self.page.evaluate('window.gilneasApp.selectId("northern-headlands")')
        self.toggle()
        editing_height = self.page.locator('#editor').bounding_box()['height']
        for selector in ['.editor-actions', '.editor-selection', '.destructive-actions', 'label:has(#import-json)']:
            self.assertTrue(self.page.locator(selector).is_visible(), selector)
        self.assertTrue(self.page.evaluate('document.body.classList.contains("edit-mode")'))
        self.close_editor()
        self.assertTrue(self.page.locator('#dossier-edit').is_visible())
        self.assertTrue(self.page.locator('#dossier-add-object').is_visible())
        cards = self.page.locator('#dossier-objects .object-card')
        self.assertGreater(cards.count(), 0)
        cards.first.locator('summary').click()
        self.assertTrue(cards.first.locator('.object-actions').is_visible())
        self.toggle()
        self.assertLess(self.page.locator('#editor').bounding_box()['height'], editing_height - 120)
        self.close_editor()
        self.assertFalse(cards.first.locator('.object-actions').is_visible())
        self.assertEqual(cards.first.locator('.object-actions').evaluate('e=>e.getBoundingClientRect().height'), 0)
        self.assertFalse(self.page.locator('#dossier-edit').is_visible())
        self.assertTrue(self.page.locator('#dossier-favorite').is_visible())
        self.assertTrue(self.page.locator('#dossier-focus').is_visible())
        self.assertEqual(self.page.evaluate('window.gilneasApp.getSelectedId()'), 'northern-headlands')
        self.assertEqual(self.data(), before); self.assertIsNone(self.draft())
        self.assertEqual(self.errors, [])

    def test_03_all_windows_keep_viewing_but_hide_dynamic_editing_and_cancel_forms_when_disabled(self):
        before = self.data()
        self.page.locator('#council-open').click()
        for selector in ['#council-add', '#council-influence-edit', '.council-member button[data-council-edit]', '.council-member button[data-council-remove]']:
            self.assertEqual(self.page.locator(selector).evaluate_all('nodes=>nodes.filter(e=>e.getClientRects().length && getComputedStyle(e).display!=="none").length'), 0, selector)
        self.assertTrue(self.page.locator('#council-filter-party').is_visible())
        self.assertTrue(self.page.locator('#council-filter-kind').is_visible())
        self.assertTrue(self.page.locator('#council-influence').is_visible())
        self.page.locator('#council-close').click()
        self.page.locator('#wall-history-open').click()
        self.assertFalse(self.page.locator('#wall-event-form').is_visible())
        self.assertTrue(self.page.locator('#wall-journal-summary').is_visible())
        self.assertTrue(self.page.locator('#wall-event-history').is_visible())
        self.page.locator('[data-close="wall-journal"]').click()
        self.toggle(); self.close_editor()
        self.page.locator('#wall-history-open').click()
        self.assertTrue(self.page.locator('#wall-event-form').is_visible())
        self.page.locator('#wall-event-name').fill('Несохранённая запись режима')
        self.page.locator('[data-close="wall-journal"]').click()
        self.toggle(); self.close_editor()
        self.page.locator('#wall-history-open').click()
        self.assertFalse(self.page.locator('#wall-event-form').is_visible())
        self.assertEqual(self.page.locator('#wall-event-name').input_value(), '')
        self.page.locator('[data-close="wall-journal"]').click()
        self.page.evaluate('window.gilneasApp.selectId("northern-headlands")')
        self.assertFalse(self.page.locator('#dossier .composition').is_visible(), 'An empty editor-only composition must not make a blank block in reading mode')
        self.assertEqual(self.data(), before); self.assertIsNone(self.draft())
        self.assertEqual(self.errors, [])

    def test_04_hidden_actions_keyboard_and_public_edit_callbacks_cannot_modify_a_readonly_snapshot(self):
        before = self.data()
        self.page.evaluate('window.gilneasApp.selectId("northern-headlands")')
        self.page.keyboard.press('e')
        self.assertFalse(self.page.locator('#location-editor').is_visible(), 'Quick edit is inactive without opt-in')
        self.page.evaluate('document.getElementById("dossier-edit").click()')
        self.assertFalse(self.page.locator('#location-editor').is_visible())
        self.page.evaluate('window.gilneasApp.editor.editLocation("northern-headlands")')
        self.assertFalse(self.page.locator('#location-editor').is_visible())
        self.page.evaluate('document.getElementById("location-create").click()')
        self.assertFalse(self.page.locator('#map-task').is_visible())
        self.page.evaluate('window.gilneasApp.boundaries.open()')
        self.assertFalse(self.page.locator('#boundary-tools').is_visible())
        message = self.page.evaluate('''()=>{try{window.gilneasApp.replaceData(window.gilneasApp.getData());return null;}catch(error){return error.message;}}''')
        self.assertIn('режим редактирования', message)
        self.assertEqual(self.data(), before); self.assertIsNone(self.draft())
        self.assertEqual(self.errors, [])

    def test_05_editing_only_dialogs_have_no_readonly_layout_or_submit_path(self):
        before = self.data()
        self.toggle(); self.close_editor()
        self.page.evaluate('window.gilneasApp.selectId("northern-headlands")')
        self.page.locator('#dossier-edit').click()
        self.page.locator('#location-name').fill('Не сохранять после выключения')
        self.page.evaluate('''()=>{const checkbox=document.getElementById('editing-enabled');checkbox.checked=false;checkbox.dispatchEvent(new Event('change',{bubbles:true}));}''')
        for selector in ['#location-editor', '#object-editor', '#houses-editor', '#territory-editor']:
            self.assertEqual(self.page.locator(selector).get_attribute('data-edit-only'), '', selector)
            self.assertFalse(self.page.locator(selector).is_visible(), selector)
        self.page.evaluate('''()=>{for(const id of ['location-form','object-form','house-form','territory-form','wall-event-form','council-form','council-influence-form'])document.getElementById(id).dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));}''')
        self.assertEqual(self.data(), before); self.assertIsNone(self.draft())
        self.assertEqual(self.errors, [])

    def test_06_saved_edits_survive_reload_but_the_mode_never_survives_entry(self):
        original = self.data()
        self.page.evaluate('window.gilneasApp.selectId("northern-headlands")')
        self.toggle(); self.close_editor()
        self.page.locator('#dossier-edit').click()
        self.page.locator('#location-description').fill('  Сохранённый авторский текст режима.  ')
        self.page.locator('#location-form button[type=submit]').click()
        self.page.wait_for_function('localStorage.getItem("gilneas-atlas-draft-v1")!==null', polling=50)
        saved = self.data(); literal_draft = self.draft()
        self.assertNotEqual(saved, original)
        self.toggle(); self.close_editor()
        self.assertEqual(self.data(), saved); self.assertEqual(self.draft(), literal_draft)
        self.toggle(); self.close_editor()
        self.page.reload(wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready', polling=50, timeout=25000)
        self.assertEqual(self.data(), saved); self.assertEqual(self.draft(), literal_draft)
        self.editor()
        self.assertFalse(self.page.locator('#editing-enabled').is_checked())
        self.assertFalse(self.page.locator('.editor-actions').is_visible())
        self.assertFalse(self.page.evaluate('document.body.classList.contains("edit-mode")'))
        self.close_editor()
        self.page.evaluate('window.gilneasApp.selectId("northern-headlands")')
        self.assertEqual(self.page.locator('#dossier-description').inner_text(), '  Сохранённый авторский текст режима.  ')
        self.assertFalse(self.page.locator('#dossier-edit').is_visible())
        self.assertNotIn('editingEnabled', json.loads(literal_draft))
        self.assertNotIn('editMode', json.loads(literal_draft))
        self.assertEqual(self.errors, [])

    def test_07_reading_views_are_compact_and_native_toggle_fits_desktop_portrait_and_landscape(self):
        results = []
        before = self.data()
        for width, height in [(1440,1000), (390,844), (844,390), (320,640)]:
            with self.subTest(viewport=(width,height)):
                self.page.set_viewport_size({'width':width, 'height':height})
                self.page.wait_for_function('Math.abs(parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--app-height"))-innerHeight)<1', polling=50)
                self.editor()
                checkbox = self.page.locator('#editing-enabled')
                label = self.page.locator('label:has(#editing-enabled)')
                self.assertFalse(checkbox.is_checked())
                self.assertGreaterEqual(label.bounding_box()['height'], 44)
                geometry = label.evaluate('''e=>{const input=e.querySelector('input').getBoundingClientRect(),text=e.querySelector('span').getBoundingClientRect();return {inputRight:input.right,textLeft:text.left,inputY:(input.top+input.bottom)/2,textY:(text.top+text.bottom)/2};}''')
                self.assertLess(geometry['inputRight'], geometry['textLeft'])
                self.assertLess(abs(geometry['inputY'] - geometry['textY']), 2)
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width)
                view_height = self.page.locator('#editor').bounding_box()['height']
                self.page.screenshot(path=str(SCRATCH / f'editor-view-{width}x{height}.png'))
                label.click(); self.assertTrue(checkbox.is_checked())
                self.page.screenshot(path=str(SCRATCH / f'editor-edit-{width}x{height}.png'))
                self.assertTrue(self.page.locator('#location-create').is_visible())
                edit_height = self.page.locator('#editor').bounding_box()['height']
                self.assertLess(view_height, edit_height)
                self.page.locator('#editor').evaluate('e=>e.scrollTop=0')
                label.click(); self.assertFalse(checkbox.is_checked()); self.close_editor()
                self.page.locator('#wall-history-open').click()
                self.assertFalse(self.page.locator('#wall-event-form').is_visible())
                self.page.screenshot(path=str(SCRATCH / f'wall-view-{width}x{height}.png'))
                self.page.locator('[data-close="wall-journal"]').click()
                self.page.locator('#council-open').click()
                self.page.screenshot(path=str(SCRATCH / f'council-view-{width}x{height}.png'))
                self.assertTrue(self.page.locator('#council-filter-party').is_visible())
                self.assertFalse(self.page.locator('#council-add').is_visible())
                self.page.locator('#council-close').click()
                self.page.evaluate('window.gilneasApp.selectId("northern-headlands")')
                self.page.screenshot(path=str(SCRATCH / f'dossier-view-{width}x{height}.png'))
                self.assertFalse(self.page.locator('#dossier .composition').is_visible())
                self.assertTrue(self.page.locator('#dossier-focus').is_visible())
                results.append({'width':width, 'height':height, 'viewEditorHeight':view_height, 'editEditorHeight':edit_height, 'label':geometry})
                self.assertEqual(self.data(), before); self.assertIsNone(self.draft())
        (SCRATCH / 'responsive-measurements.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
        self.assertEqual(self.errors, [])

    def test_08_disabling_mode_cancels_native_brush_preview_without_a_commit(self):
        before = self.data()
        self.toggle()
        self.page.locator('#territories-open').click()
        self.assertTrue(self.page.locator('#boundary-tools').is_visible())
        self.page.locator('#boundary-mode').select_option('erase')
        self.page.evaluate('window.gilneasApp.ui.home(false)')
        point = self.page.evaluate('''()=>{const app=window.gilneasApp,rect=document.getElementById('viewport').getBoundingClientRect(),grid=app.getData().territoryGrid;for(let y=rect.top+rect.height*.3;y<rect.top+rect.height*.75;y+=12)for(let x=rect.left+rect.width*.3;x<rect.left+rect.width*.65;x+=12){const p=app.ui.toMap(x,y),ix=Math.floor(p[0]/grid.step),iy=Math.floor(p[1]/grid.step);if(app.canPlace(p)&&ix>=0&&ix<grid.width&&iy>=0&&iy<grid.height&&grid.cells[iy*grid.width+ix]>0)return [x,y];}throw new Error('No active occupied test point');}''')
        self.page.mouse.move(*point); self.page.mouse.down()
        self.page.mouse.move(point[0]+15, point[1]+8, steps=3)
        self.assertNotEqual(self.page.evaluate('window.gilneasApp.boundaries.getGrid().cells'), before['territoryGrid']['cells'])
        self.assertEqual(self.data(), before); self.assertIsNone(self.draft())
        self.page.evaluate('''()=>{const input=document.getElementById('editing-enabled');input.checked=false;input.dispatchEvent(new Event('change',{bubbles:true}));}''')
        self.page.mouse.up()
        self.page.evaluate('window.gilneasApp.boundaries.whenReady()')
        self.assertFalse(self.page.locator('#boundary-tools').is_visible())
        self.assertFalse(self.page.evaluate('document.body.classList.contains("boundary-editing")'))
        self.assertEqual(self.page.evaluate('window.gilneasApp.boundaries.getGrid().cells'), before['territoryGrid']['cells'])
        self.assertEqual(self.data(), before); self.assertIsNone(self.draft())
        self.assertEqual(self.errors, [])

    def test_09_an_inflight_import_cannot_complete_after_disable_and_reenable(self):
        before = self.data()
        self.toggle(); self.close_editor()
        self.page.evaluate('''()=>{const file=new File(['{}'],'delayed-import.json',{type:'application/json'});file.text=()=>new Promise(resolve=>{window.releaseEditingImport=()=>resolve(JSON.stringify(window.gilneasApp.getData()));});window.editingImportOutcome=null;window.gilneasApp.importSnapshot(file).then(()=>window.editingImportOutcome='committed',error=>window.editingImportOutcome=error.message);}''')
        self.toggle(); self.toggle(); self.close_editor()
        self.page.evaluate('window.releaseEditingImport()')
        self.page.wait_for_function('window.editingImportOutcome!==null', polling=50)
        self.assertIn('режим редактирования', self.page.evaluate('window.editingImportOutcome'))
        self.assertEqual(self.data(), before); self.assertIsNone(self.draft())
        self.assertEqual(self.errors, [])

    def test_council_views_hide_editing_prompts_when_the_editing_controls_are_hidden(self):
        self.page.locator('#council-open').click()
        if not self.data()['royalCouncil'].get('influence'):
            self.assertNotIn('Задайте', self.page.locator('.council-influence-message').inner_text())
        self.assertFalse(self.page.locator('#council-influence-edit').is_visible())
        self.assertEqual(self.errors, [])

    def test_empty_canonical_container_allows_its_first_object_only_after_editing_opt_in(self):
        before=self.data()
        target=next(location for location in before['locations'] if location['id']=='ambermill')
        self.assertTrue(target['isLocation'])
        self.assertEqual(target['objects'],[])
        self.page.locator('#search').fill('Янтарная')
        self.page.locator('#location-list button.location-row[data-location-id="ambermill"]').click()
        composition=self.page.locator('#dossier-body .composition')
        self.assertTrue(composition.is_hidden())
        self.assertFalse(self.page.locator('#dossier-add-object').is_visible())
        self.assertTrue(self.page.locator('#dossier-location-links').is_visible())
        self.toggle();self.close_editor()
        self.assertTrue(composition.is_visible(),'An empty location container must expose first-object creation when editing is enabled')
        self.assertTrue(self.page.locator('#dossier-add-object').is_visible())
        self.page.locator('#dossier-add-object').click()
        self.page.locator('#object-type').select_option('building')
        self.page.locator('#object-name').fill('  Первый объект контейнера  ')
        self.page.locator('#object-description').fill('  Авторская запись без изменения связанных меток  ')
        self.page.locator('#object-form button[type=submit]').click()
        after=self.data()
        actual=next(location for location in after['locations'] if location['id']=='ambermill')
        self.assertEqual(len(actual['objects']),1)
        self.assertEqual(actual['objects'][0]['name'],'  Первый объект контейнера  ')
        self.assertEqual(actual['objects'][0]['description'],'  Авторская запись без изменения связанных меток  ')
        expected=json.loads(json.dumps(before))
        next(location for location in expected['locations'] if location['id']=='ambermill')['objects']=actual['objects']
        self.assertEqual(after,expected)
        raw=self.draft();self.assertEqual(json.loads(raw),after)
        self.toggle();self.close_editor()
        self.assertFalse(self.page.locator('#dossier-add-object').is_visible())
        self.assertTrue(composition.is_visible(),'The saved object stays readable while editing actions are hidden')
        self.assertEqual(self.data(),after);self.assertEqual(self.draft(),raw)
        self.page.reload(wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready',polling=50,timeout=25000)
        self.assertFalse(self.page.locator('#editing-enabled').is_checked())
        self.assertEqual(self.data(),after);self.assertEqual(self.draft(),raw)
        self.page.evaluate('window.gilneasApp.selectId("ambermill")')
        self.assertTrue(self.page.locator('#dossier-body .composition').is_visible())
        self.assertFalse(self.page.locator('#dossier-add-object').is_visible())
        self.assertEqual(self.errors,[])

if __name__ == '__main__': unittest.main()
