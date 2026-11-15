"""Linked-map UI, isolated only at app bootstrap, using the real atlas DOM.

Run with the supplied Playwright interpreter:
  /Users/daniil_si/.hermes/cache/scratch/gilneas-venv/bin/python \
    -m unittest discover -s tests -p test_location_links_ui.py -v

Test-only records never enter assets/data. Browser evidence stays in scratch.
"""
import copy
import functools
import http.server
import json
import threading
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / 'assets/js/location-links-ui.mjs'
CSS_PATH = ROOT / 'assets/css/location-links.css'
ARTIFACTS = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-location-links-evidence')
DRAFT_KEY = 'gilneas-location-links-test-draft'
DISTRICT_ID = '  military "district\'"  '
PRISON_ID = '  prison "stone\'ward"  '
ROOT_ID = 'root "north"'
SENTINEL_ID = '__location_link_placeholder__'

BASELINE = {
    'version': 1,
    'meta': {
        'width': 3526, 'height': 4548,
        'image': 'assets/maps/gilneas-enhanced.webp',
        'mist': 'assets/maps/inactive-mist.webp',
        'inactiveMask': 'assets/maps/inactive-mask.png',
        'authorMetadata': {'literal': '  <script>window.bad=1</script>  '},
    },
    'factions': [
        {'id': 'crown', 'name': 'Тестовая Корона', 'parent': None, 'color': '#990000'},
        {'id': 'vassal', 'name': 'Тестовый дом <img onerror="window.bad=1">',
         'parent': 'crown', 'color': '#005577'},
        {'id': 'foreign', 'name': 'Тестовая чужая держава', 'parent': None, 'color': '#557744'},
    ],
    'locations': [
        {'id': ROOT_ID, 'name': 'Тестовая область', 'type': 'city', 'faction': 'crown',
         'x': 1200, 'y': 2300, 'capital': True, 'description': '  Тестовая область  ',
         'owner': '  Тестовый король  ', 'objects': [], 'isLocation': True,
         'linkedLocationIds': [DISTRICT_ID]},
        {'id': DISTRICT_ID, 'name': 'Тестовый военный квартал', 'type': 'district',
         'faction': 'vassal', 'x': 1400, 'y': 2600, 'owner': '', 'description': '  Тестовый квартал  ',
         'isLocation': True, 'linkedLocationIds': [PRISON_ID, 'port'],
         'objects': [{'id': 'test-inline-barracks', 'name': 'Тестовые казармы квартала',
                      'type': 'barracks', 'description': '  Собственный состав квартала  ', 'owner': '',
                      'modifiers': [{'id': 'test-district-bonus', 'kind': 'bonus',
                                     'text': '  Тестовый бонус только квартала  '}]}],
         'authorExtra': {'order': ['  Keep literal  ', {'name': '<script>literal</script>'}]}},
        {'id': PRISON_ID, 'name': '  Тестовая тюрьма <script>window.bad=1</script>  ',
         'type': 'fortress', 'faction': 'foreign', 'x': 1600, 'y': 2600,
         'owner': '  Тестовый смотритель  ', 'description': '  Полное самостоятельное досье тюрьмы  ',
         'objects': [{'id': 'test-prison-cells', 'name': 'Тестовые камеры тюрьмы',
                      'type': 'building', 'owner': '', 'description': '  Тестовые условия владения  ',
                      'modifiers': [{'id': 'test-prison-bonus', 'kind': 'bonus', 'text': '  Тестовый порядок +2  '},
                                    {'id': 'test-prison-penalty', 'kind': 'penalty', 'text': '  Тестовый расход -1  '}]}]},
        {'id': 'outer', 'name': 'Тестовая вторая локация', 'type': 'forest', 'faction': 'crown',
         'x': 1800, 'y': 2700, 'owner': '', 'description': '', 'objects': [],
         'isLocation': True, 'linkedLocationIds': [PRISON_ID]},
        {'id': 'port', 'name': 'Тестовый порт', 'type': 'harbor', 'faction': 'crown',
         'x': 1700, 'y': 2800, 'owner': '', 'description': '  Собственное досье порта  ', 'objects': []},
        {'id': 'legacy', 'name': 'Тестовая мастерская', 'type': 'workshop', 'faction': None,
         'x': 1900, 'y': 2600, 'owner': '', 'description': '  Старое досье  ', 'objects': []},
        {'id': SENTINEL_ID, 'name': 'Тестовая ферма', 'type': 'farm', 'faction': 'foreign',
         'x': 1500, 'y': 2800, 'owner': '', 'description': '', 'objects': []},
        {'id': ' ', 'name': 'Тестовое кладбище с буквальным ID-пробелом', 'type': 'cemetery',
         'faction': None, 'x': 1800, 'y': 2900, 'owner': '', 'description': '', 'objects': []},
    ],
    'territories': [],
    'nobles': [{'id': 'test-baron', 'name': 'Тестовый барон', 'house': 'vassal', 'description': '  Не менять  '}],
    'sources': [{'id': 17, 'title': 'Тестовый архив', 'url': 'https://example.invalid/archive'}],
    'authorRegistry': [{'literal': '  Unrelated registry  '}],
}

BOOTSTRAP = """async ({baseline, selectedId, key}) => {
    document.body.classList.add('edit-mode');
    const model = await import('/assets/js/model.mjs');
    const types = await import('/assets/js/object-types.mjs');
    const {decorateIcons} = await import('/assets/js/icons.mjs');
    const {initUI} = await import('/assets/js/ui.mjs');
    const helper = await import('/assets/js/location-links-ui.mjs');
    decorateIcons();
    const freeze = value => {
        if (value && typeof value === 'object') {
            Object.values(value).forEach(freeze);
            Object.freeze(value);
        }
        return value;
    };
    let data = freeze(model.normalizeData(baseline));
    let selected = selectedId;
    let ui;
    let editor;
    const selections = [];
    const renderLinks = () => {
        if (helper.renderLocationLinkSections) helper.renderLocationLinkSections({
            snapshot: data, locationId: selected, onSelect: select,
            body: document.getElementById('dossier-body'),
        });
    };
    const decorateMarkers = () => {
        for (const marker of document.querySelectorAll('#markers .map-marker')) {
            const location = data.locations.find(record => record.id === marker.dataset.locationId);
            helper.decorateLocationMarker(marker, location);
        }
    };
    function select(id) {
        if (!data.locations.some(record => record.id === id)) return;
        selected = id;
        selections.push(id);
        ui.render();
        decorateMarkers();
        renderLinks();
        ui.setPanel('dossier', true);
        ui.focusLocation(id, false);
    }
    ui = initUI({
        getData: () => data, getSelectedId: () => selected, onSelect: select,
        onClearSelection: () => { selected = null; ui.render(); renderLinks(); },
    });
    renderLinks();
    localStorage.setItem(key, JSON.stringify(data));
    localStorage.setItem('location-links-unrelated', '  Keep exact  ');
    const storageWrites = [];
    for (const method of ['setItem', 'removeItem', 'clear']) {
        const original = Storage.prototype[method];
        Storage.prototype[method] = function (...args) {
            storageWrites.push({method, args});
            return original.apply(this, args);
        };
    }
    window.__links = {
        model, types, helper, ui, selections, storageWrites, key,
        get data() { return data; }, get selected() { return selected; },
        get editor() { return editor; },
        select, renderLinks, decorateMarkers,
        original: structuredClone(data),
        replaceInMemory: incoming => { data = freeze(model.normalizeData(incoming)); },
        startEditor: () => {
            editor = helper.initLocationLinksEditor({getData: () => data});
            return Object.keys(editor);
        },
        fillEditor: id => {
            const location = data.locations.find(record => record.id === id);
            const form = document.getElementById('location-form');
            form.reset();
            document.getElementById('location-name').value = location.name;
            document.getElementById('location-owner').value = location.owner;
            document.getElementById('location-description').value = location.description;
            document.getElementById('location-x').value = location.x;
            document.getElementById('location-y').value = location.y;
            document.getElementById('location-capital').checked = Boolean(location.capital);
            types.populateTypeSelect(document.getElementById('location-type'), {scope: 'location', currentType: location.type});
            editor.fill(location);
            const dialog = document.getElementById('location-editor');
            if (!dialog.open) dialog.showModal();
            dialog.focus({preventScroll: true});
        },
    };
}"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class LocationLinksUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(args=[
            '--disable-renderer-backgrounding', '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
        ])
        ARTIFACTS.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.context = self.browser.new_context(
            viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        self.page = self.context.new_page()
        self.page.set_default_timeout(8000)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text)
                     if message.type == 'error' else None)
        self.page.on('response', lambda response: self.errors.append(f'{response.status} {response.url}')
                     if response.status >= 400 else None)
        # Keep every production document, style, raster, model and UI module real.
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(
            status=200, content_type='text/javascript', body=''))
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/', wait_until='networkidle')

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [], 'isolated browser must have no page/console/HTTP errors')
            self.assertIsNone(self.page.evaluate('window.bad'), 'names must never execute HTML')
        finally:
            self.context.close()

    def boot(self, baseline=None, selected_id=DISTRICT_ID):
        self.assertTrue(UI_PATH.is_file(), 'the new linked-location UI module is missing')
        self.assertTrue(CSS_PATH.is_file(), 'the new scoped linked-location stylesheet is missing')
        self.page.add_style_tag(url='/assets/css/location-links.css')
        self.page.evaluate(BOOTSTRAP, {
            'baseline': baseline if baseline is not None else BASELINE,
            'selectedId': selected_id, 'key': DRAFT_KEY,
        })
        self.page.wait_for_function(
            'document.getElementById("base-map").complete && document.getElementById("base-map").naturalWidth > 0',
            polling=50)

    def data(self):
        return self.page.evaluate('window.__links.data')

    def patch(self):
        return self.page.evaluate('window.__links.editor.readPatch()')

    def start_editor(self, location_id=DISTRICT_ID, baseline=None):
        self.boot(baseline=baseline, selected_id=location_id)
        available = self.page.evaluate('typeof window.__links.helper.initLocationLinksEditor')
        self.assertEqual(available, 'function', 'initLocationLinksEditor must be exported')
        self.page.evaluate('window.__links.startEditor()')
        self.page.evaluate('id => window.__links.fillEditor(id)', location_id)

    def assert_no_writes(self):
        self.assertEqual(self.page.evaluate('window.__links.storageWrites'), [])
        self.assertEqual(self.page.evaluate('localStorage.getItem("location-links-unrelated")'), '  Keep exact  ')
        self.assertEqual(json.loads(self.page.evaluate('localStorage.getItem(window.__links.key)')),
                         self.page.evaluate('window.__links.original'))

    def test_special_marker_frame_is_a_sibling_without_changing_real_primary_geometry(self):
        self.boot()
        result = self.page.evaluate("""() => {
            const marker = [...document.querySelectorAll('#markers .map-marker')]
                .find(node => node.dataset.locationId === window.__links.data.locations[1].id);
            const original = marker.querySelector('svg');
            const label = marker.querySelector('.marker-label');
            const location = window.__links.data.locations[1];
            const measure = () => {
                const box = marker.getBoundingClientRect();
                const glyph = original.getBoundingClientRect();
                const style = getComputedStyle(marker);
                const pseudo = name => {
                    const value = getComputedStyle(marker, name);
                    return [value.content, value.transform, value.border, value.backgroundColor, value.boxShadow, value.inset];
                };
                return {box: [box.x, box.y, box.width, box.height], glyph: [glyph.x, glyph.y, glyph.width, glyph.height],
                    transform: style.transform, origin: style.transformOrigin, inline: marker.style.cssText,
                    before: pseudo('::before'), after: pseudo('::after'), svg: original.outerHTML};
            };
            const before = measure();
            window.__links.helper.decorateLocationMarker(marker, location);
            window.__links.helper.decorateLocationMarker(marker, location);
            const frame = marker.querySelector('.location-container-frame');
            const after = measure();
            const enabled = {special: marker.classList.contains('location-container'),
                frames: marker.querySelectorAll('.location-container-frame').length,
                frameSibling: frame?.parentElement === original.parentElement,
                primarySame: marker.querySelector('svg') === original,
                labelSame: marker.querySelector('.marker-label') === label,
                frameHidden: frame?.getAttribute('aria-hidden'),
                frameEvents: frame ? getComputedStyle(frame).pointerEvents : null};
            window.__links.helper.decorateLocationMarker(marker, {...location, isLocation: false});
            const disabled = {special: marker.classList.contains('location-container'),
                frames: marker.querySelectorAll('.location-container-frame').length, same: marker.querySelector('svg') === original};
            window.__links.helper.decorateLocationMarker(marker, {...location, isLocation: 'true'});
            return {before, after, enabled, disabled, strict: marker.classList.contains('location-container')};
        }""")
        self.assertEqual(result['enabled'], {
            'special': True, 'frames': 1, 'frameSibling': True, 'primarySame': True,
            'labelSame': True, 'frameHidden': 'true', 'frameEvents': 'none',
        })
        self.assertEqual(result['before'], result['after'])
        self.assertEqual(result['disabled'], {'special': False, 'frames': 0, 'same': True})
        self.assertFalse(result['strict'], 'only the boolean flag enables location containers')
        self.assert_no_writes()

    def test_editor_checkbox_preserves_optional_presence_for_legacy_noop(self):
        self.start_editor('legacy')
        before = self.data()
        for element_id in ['location-is-location', 'location-link-search', 'location-link-target',
                           'location-link-add', 'location-linked-list']:
            self.assertEqual(self.page.locator(f'#{element_id}').count(), 1)
            self.assertTrue(self.page.locator(f'#{element_id}').evaluate(
                'element => element.closest("#location-form") !== null'))
        self.assertEqual(self.patch(), {}, 'legacy no-op must not create false or empty fields')
        self.page.locator('#location-is-location').focus()
        self.page.keyboard.press('Space')
        self.assertEqual(self.patch(), {'isLocation': True})
        self.page.keyboard.press('Space')
        self.assertEqual(self.patch(), {}, 'returning to legacy state must remain a no-op')
        explicit = copy.deepcopy(before['locations'][5])
        explicit.update(isLocation=False, linkedLocationIds=[])
        self.page.evaluate('location => window.__links.editor.fill(location)', explicit)
        self.assertEqual(self.patch(), {'isLocation': False, 'linkedLocationIds': []})
        self.page.evaluate('window.__links.editor.refresh()')
        self.assertEqual(self.patch(), {'isLocation': False, 'linkedLocationIds': []})
        self.assertEqual(self.data(), before)
        self.assert_no_writes()

    def test_editor_initialization_reuses_the_same_unsaved_form(self):
        self.start_editor('legacy')
        result = self.page.evaluate("""() => {
            const first = window.__links.editor;
            document.getElementById('location-is-location').checked = true;
            const again = window.__links.helper.initLocationLinksEditor({getData: () => window.__links.data});
            return {same: first === again, fields: document.querySelectorAll('#location-links-fields').length,
                checks: document.querySelectorAll('#location-is-location').length, patch: again.readPatch()};
        }""")
        self.assertEqual(result, {'same': True, 'fields': 1, 'checks': 1, 'patch': {'isLocation': True}})
        self.assert_no_writes()

    def test_link_rows_open_canonical_dossiers_then_return_even_across_faction_filter(self):
        self.boot()
        self.assertEqual(self.page.evaluate('typeof window.__links.helper.renderLocationLinkSections'), 'function',
                         'renderLocationLinkSections must be exported')
        before = self.data()
        self.page.evaluate('window.__links.renderLinks(); window.__links.renderLinks()')
        result = self.page.evaluate("""() => {
            const body = document.getElementById('dossier-body');
            const section = body.querySelector('#dossier-location-links');
            const parents = body.querySelector('#dossier-parent-locations');
            const rows = [...section.querySelectorAll('button[data-location-link]')];
            return {sectionCount: document.querySelectorAll('#dossier-location-links').length,
                parentCount: document.querySelectorAll('#dossier-parent-locations').length,
                inBody: section.parentElement === body && parents.parentElement === body,
                heading: section.querySelector('h3')?.textContent, note: section.textContent,
                unsafe: section.querySelectorAll('script,img').length,
                rows: rows.map(row => ({id: row.dataset.locationLink, text: row.textContent,
                    type: row.querySelector('svg')?.dataset.type,
                    path: row.querySelector('svg path')?.getAttribute('d'),
                    edits: row.querySelectorAll('input,textarea,[contenteditable=true],[data-object-edit],[data-object-delete]').length})),
                inline: body.querySelector('#dossier-objects').textContent};
        }""")
        self.assertEqual(result['sectionCount'], 1)
        self.assertEqual(result['parentCount'], 1)
        self.assertTrue(result['inBody'])
        self.assertEqual(result['heading'], 'Объекты локации')
        self.assertIn('Ссылки на метки карты', result['note'])
        self.assertEqual(result['unsafe'], 0)
        self.assertEqual([row['id'] for row in result['rows']], [PRISON_ID, 'port'])
        for row, location in zip(result['rows'], [before['locations'][2], before['locations'][4]]):
            self.assertIn(location['name'], row['text'])
            faction = next(item for item in before['factions'] if item['id'] == location['faction'])
            self.assertIn(faction['name'], row['text'])
            self.assertEqual(row['type'], location['type'])
            self.assertEqual(row['edits'], 0)
            self.assertNotIn(location['description'], row['text'])
        self.assertNotEqual(result['rows'][0]['path'], result['rows'][1]['path'])
        self.assertIn('Тестовый бонус только квартала', result['inline'])
        self.assertNotIn('Тестовый порядок +2', result['note'])
        self.assertNotIn('Тестовый расход -1', result['note'])

        # Select a faction with the real layer controls, making the prison dimmed.
        self.page.locator('#layers-open').click()
        self.page.locator('#faction-list button[data-faction-id="vassal"]').click()
        self.page.locator('#layers-close').click()
        self.page.evaluate('window.__links.ui.setPanel("dossier", true); window.__links.renderLinks()')
        dimmed = self.page.locator('#markers .map-marker').filter(
            has=self.page.locator('svg')).evaluate_all(
                '(markers, id) => markers.find(marker => marker.dataset.locationId === id).classList.contains("dimmed")', PRISON_ID)
        self.assertTrue(dimmed)
        self.page.locator('#dossier-location-links button[data-location-link]').nth(0).click()
        self.assertEqual(self.page.evaluate('window.__links.selected'), PRISON_ID)
        self.assertEqual(self.page.locator('#dossier-title').text_content(), before['locations'][2]['name'])
        self.assertIn('Тестовый порядок +2', self.page.locator('#dossier-objects').text_content())
        self.assertIn('Тестовый расход -1', self.page.locator('#dossier-objects').text_content())
        self.assertTrue(self.page.locator('#dossier-location-links').is_hidden(), 'ordinary target has no copied child section')
        self.assertEqual(self.page.locator('#dossier-parent-locations button[data-location-link]').evaluate_all(
            'rows => rows.map(row => row.dataset.locationLink)'), [DISTRICT_ID, 'outer'])
        breadcrumb = self.page.locator('#dossier-parent-locations button[data-location-link]').nth(0)
        breadcrumb.focus()
        self.page.keyboard.press('Enter')
        self.assertEqual(self.page.evaluate('window.__links.selected'), DISTRICT_ID)
        self.assertEqual(self.page.evaluate('window.__links.selections'), [PRISON_ID, DISTRICT_ID])
        self.assertEqual(self.data(), before)
        self.assert_no_writes()

    def test_empty_container_exposes_native_link_authoring_without_copying_inline_content(self):
        baseline = copy.deepcopy(BASELINE)
        baseline['locations'][5]['isLocation'] = True
        self.boot(baseline=baseline, selected_id='legacy')
        self.assertEqual(self.page.evaluate('typeof window.__links.helper.renderLocationLinkSections'), 'function')
        self.page.evaluate("""() => {
            window.__links.startEditor();
            window.__links.editRequests = [];
            window.__links.helper.renderLocationLinkSections({
                snapshot: window.__links.data, locationId: 'legacy', body: document.getElementById('dossier-body'),
                onSelect: window.__links.select, onEditLocation: id => {
                    window.__links.editRequests.push(id);
                    window.__links.fillEditor(id);
                },
            });
        }""")
        self.assertTrue(self.page.locator('#dossier-location-links').is_visible(), 'empty containers need a discoverable link section')
        self.assertIn('Связанные метки ещё не добавлены', self.page.locator('#dossier-location-links').text_content())
        self.assertEqual(self.page.locator('#dossier-location-links button[data-location-link]').count(), 0)
        self.assertEqual(self.page.locator('#dossier-link-edit').text_content(), 'Связать метку')
        self.page.locator('#dossier-link-edit').click()
        self.assertEqual(self.page.evaluate('window.__links.editRequests'), ['legacy'])
        self.assertTrue(self.page.locator('#location-editor').is_visible())
        self.assertTrue(self.page.locator('#location-is-location').is_checked())
        self.assertEqual(self.patch(), {'isLocation': True})
        self.page.keyboard.press('Escape')
        self.page.wait_for_function('!document.getElementById("location-editor").open')
        self.page.evaluate('window.__links.renderLinks()')
        self.assertTrue(self.page.locator('#dossier-location-links').is_visible())
        self.assertEqual(self.page.locator('#dossier-link-edit').count(), 0, 'no stale edit callback when omitted')
        self.assert_no_writes()

    def test_sections_rebuild_current_identity_then_clear_on_missing_selection(self):
        self.boot()
        before_inline = self.page.locator('#dossier-objects').evaluate('node => node.outerHTML')
        incoming = self.data()
        incoming['locations'][2].update(name='  Новое имя <img onerror="window.bad=1">  ', type='church', faction=None)
        incoming['factions'][1]['name'] = '  Новый текущий дом  '
        self.page.evaluate('data => window.__links.replaceInMemory(data)', incoming)
        self.page.evaluate('window.__links.renderLinks()')
        row = self.page.locator('#dossier-location-links button[data-location-link]').nth(0)
        self.assertIn(incoming['locations'][2]['name'], row.text_content())
        self.assertIn('Церковь', row.text_content())
        self.assertIn('Без державы', row.text_content())
        self.assertEqual(row.locator('svg[data-type]').get_attribute('data-type'), 'church')
        self.assertEqual(self.page.locator('#dossier-objects').evaluate('node => node.outerHTML'), before_inline,
                         'link rendering may not rebuild or rename ordinary composition')
        self.page.evaluate('window.__links.select("legacy")')
        for section_id in ['dossier-location-links', 'dossier-parent-locations']:
            self.assertTrue(self.page.locator(f'#{section_id}').is_hidden())
            self.assertEqual(self.page.locator(f'#{section_id} button').count(), 0, 'hidden sections must lose stale actions')
        self.page.evaluate('id => window.__links.select(id)', DISTRICT_ID)
        self.assertEqual(self.page.locator('#dossier-location-links button[data-location-link]').count(), 2)
        error = self.page.evaluate("""() => {
            try {
                window.__links.helper.renderLocationLinkSections({
                    snapshot: window.__links.data, locationId: 'deleted "literal" ', onSelect: window.__links.select,
                    body: document.getElementById('dossier-body'),
                });
                return '';
            } catch (error) { return error.message; }
        }""")
        self.assertEqual(error, '', 'stale selection must hide links, not call the engine with a missing ID')
        for section_id in ['dossier-location-links', 'dossier-parent-locations']:
            self.assertTrue(self.page.locator(f'#{section_id}').is_hidden())
            self.assertEqual(self.page.locator(f'#{section_id} button').count(), 0)
        self.page.evaluate("""() => window.__links.helper.renderLocationLinkSections({
            snapshot: window.__links.data, locationId: null, onSelect: window.__links.select,
        })""")
        self.assertTrue(self.page.locator('#dossier-location-links').is_hidden())
        self.assert_no_writes()

    def test_editor_adds_literal_canonical_targets_only_to_the_unsaved_form(self):
        self.start_editor(DISTRICT_ID)
        before = self.data()
        self.assertEqual(self.patch(), {'isLocation': True, 'linkedLocationIds': [PRISON_ID, 'port']})
        options = self.page.locator('#location-link-target').evaluate(
            'select => [...select.options].map(option => ({id: option.value, text: option.textContent, disabled: option.disabled}))')
        enabled_ids = [option['id'] for option in options if not option['disabled']]
        self.assertIn(SENTINEL_ID, enabled_ids, 'a real ID that looks like a placeholder must remain selectable')
        self.assertIn(' ', enabled_ids, 'literal whitespace is an ID, not a blank sentinel')
        self.assertNotIn(DISTRICT_ID, enabled_ids)
        self.assertNotIn(ROOT_ID, enabled_ids, 'ancestors would create cycles')
        self.assertNotIn('test-inline-barracks', enabled_ids, 'inline objects are never canonical targets')
        self.assertEqual(self.page.locator('#location-linked-list [data-location-link-remove]').count(), 2)
        for literal_id in [SENTINEL_ID, ' ']:
            self.page.locator('#location-link-target').select_option(literal_id)
            self.page.locator('#location-link-add').click()
        self.assertEqual(self.patch(), {
            'isLocation': True, 'linkedLocationIds': [PRISON_ID, 'port', SENTINEL_ID, ' '],
        })
        self.assertEqual(self.page.locator('#location-linked-list [data-location-linked-id]').evaluate_all(
            'rows => rows.map(row => row.dataset.locationLinkedId)'), [PRISON_ID, 'port', SENTINEL_ID, ' '])
        self.assertEqual(self.page.locator('#location-linked-list svg[data-type]').evaluate_all(
            'icons => icons.map(icon => icon.dataset.type)'), ['fortress', 'harbor', 'farm', 'cemetery'])
        self.assertIn('Тестовая чужая держава', self.page.locator('#location-linked-list').text_content())
        self.assertNotIn('Тестовый порядок +2', self.page.locator('#location-linked-list').text_content())
        self.assertEqual(self.data(), before)
        self.assert_no_writes()

    def test_search_filters_targets_without_losing_the_literal_selection_or_link_roster(self):
        self.start_editor(DISTRICT_ID)
        before = self.data()
        self.page.locator('#location-link-target').select_option(SENTINEL_ID)
        self.page.locator('#location-link-search').fill('мастерская')
        result = self.page.locator('#location-link-target').evaluate("""select => ({
            selected: select.selectedOptions[0]?.value,
            ids: [...select.options].filter(option => !option.disabled).map(option => option.value),
        })""")
        self.assertEqual(result['selected'], SENTINEL_ID, 'search must keep the unsaved selected ID')
        self.assertEqual(result['ids'], ['legacy', SENTINEL_ID], 'only matches plus the selected canonical target remain')
        self.assertEqual(self.page.locator('#location-linked-list [data-location-linked-id]').evaluate_all(
            'rows => rows.map(row => row.dataset.locationLinkedId)'), [PRISON_ID, 'port'])
        self.page.locator('#location-link-search').fill('ТЕСТОВАЯ ЧУЖАЯ ДЕРЖАВА')
        enabled = self.page.locator('#location-link-target').evaluate(
            'select => [...select.options].filter(option => !option.disabled).map(option => option.value)')
        self.assertEqual(enabled, [SENTINEL_ID], 'filter matches the current target faction, not inherited container faction')
        self.page.locator('#location-link-search').fill('ничего не найдено')
        self.assertEqual(self.page.locator('#location-link-target').input_value(), SENTINEL_ID)
        self.page.locator('#location-link-add').click()
        self.assertEqual(self.patch(), {'isLocation': True, 'linkedLocationIds': [PRISON_ID, 'port', SENTINEL_ID]})
        self.page.locator('#location-link-search').fill('')
        self.assertEqual(self.page.locator('#location-linked-list [data-location-linked-id]').evaluate_all(
            'rows => rows.map(row => row.dataset.locationLinkedId)'), [PRISON_ID, 'port', SENTINEL_ID])
        self.assertEqual(self.data(), before)
        self.assert_no_writes()

    def test_refresh_keeps_a_disappeared_selected_literal_disabled_until_deliberate_reselection(self):
        self.start_editor(DISTRICT_ID)
        self.page.locator('#location-link-target').select_option(SENTINEL_ID)
        incoming = self.data()
        incoming['locations'] = [location for location in incoming['locations'] if location['id'] != SENTINEL_ID]
        self.page.evaluate('data => window.__links.replaceInMemory(data)', incoming)
        self.page.evaluate('window.__links.editor.refresh()')
        selected = self.page.locator('#location-link-target').evaluate("""select => ({
            value: select.value, selected: select.selectedOptions[0]?.value,
            disabled: select.selectedOptions[0]?.disabled, label: select.selectedOptions[0]?.textContent,
        })""")
        self.assertEqual(selected['value'], SENTINEL_ID, 'record removal must not silently choose another target')
        self.assertEqual(selected['selected'], SENTINEL_ID)
        self.assertTrue(selected['disabled'])
        self.assertIn(SENTINEL_ID, selected['label'])
        self.assertIn('не найдена', selected['label'].lower())
        self.assertTrue(self.page.locator('#location-link-add').is_disabled())
        self.page.locator('#location-link-search').fill('любой фильтр')
        self.assertEqual(self.page.locator('#location-link-target').input_value(), SENTINEL_ID)
        self.assertEqual(self.patch(), {'isLocation': True, 'linkedLocationIds': [PRISON_ID, 'port']})
        self.assert_no_writes()

    def test_disabling_the_flag_keeps_links_removable_and_leaves_save_rejection_to_the_model(self):
        self.start_editor(DISTRICT_ID)
        before = self.data()
        self.page.locator('#location-is-location').focus()
        self.page.keyboard.press('Space')
        self.assertEqual(self.patch(), {'isLocation': False, 'linkedLocationIds': [PRISON_ID, 'port']})
        self.assertTrue(self.page.locator('#location-link-add').is_disabled())
        self.assertEqual(self.page.locator('#location-linked-list [data-location-link-remove]').count(), 2)
        self.assertTrue(self.page.locator('#location-links-warning').is_visible(), 'retained links need an actionable explanation')
        self.assertIn('Уберите ссылки', self.page.locator('#location-links-warning').text_content())
        error = self.page.evaluate("""async id => {
            const {validateLocationLinks} = await import('/assets/js/location-links.mjs');
            try {
                const patch = window.__links.editor.readPatch();
                const incoming = {...window.__links.data,
                    locations: window.__links.data.locations.map(location => location.id === id ? {...location, ...patch} : location)};
                validateLocationLinks(incoming);
                window.__links.model.updateLocation(window.__links.data, id, patch);
                return '';
            } catch (error) { return error.message; }
        }""", DISTRICT_ID)
        self.assertIn('isLocation', error)
        self.page.locator('#location-linked-list [data-location-link-remove]').nth(0).click()
        self.assertEqual(self.patch(), {'isLocation': False, 'linkedLocationIds': ['port']})
        self.page.locator('#location-linked-list [data-location-link-remove]').nth(0).click()
        self.assertEqual(self.patch(), {'isLocation': False, 'linkedLocationIds': []})
        self.assertTrue(self.page.locator('#location-links-warning').is_hidden())
        self.assertEqual(self.data(), before)
        self.assert_no_writes()

    def test_remove_restores_keyboard_focus_to_adjacent_exact_id_then_the_target_control(self):
        self.start_editor(DISTRICT_ID)
        self.page.locator('#location-linked-list [data-location-link-remove]').nth(0).focus()
        self.page.keyboard.press('Enter')
        self.assertEqual(self.patch(), {'isLocation': True, 'linkedLocationIds': ['port']})
        focused = self.page.evaluate('document.activeElement?.dataset.locationLinkRemove')
        self.assertEqual(focused, 'port', 'removal must not strand focus on the document body')
        self.page.keyboard.press('Enter')
        self.assertEqual(self.patch(), {'isLocation': True, 'linkedLocationIds': []})
        self.assertEqual(self.page.evaluate('document.activeElement?.id'), 'location-link-target')
        self.assert_no_writes()

    def test_opening_another_record_clears_the_previous_unsaved_target_and_links(self):
        self.start_editor(DISTRICT_ID)
        self.page.locator('#location-link-target').select_option(SENTINEL_ID)
        self.page.locator('#location-link-search').fill('ничего')
        self.page.evaluate('window.__links.fillEditor("legacy")')
        selected = self.page.locator('#location-link-target').evaluate(
            'select => ({placeholder: select.selectedOptions[0]?.hasAttribute("data-placeholder"), value: select.value})')
        self.assertTrue(selected['placeholder'], 'new records must not inherit a pending literal selection')
        self.assertEqual(selected['value'], '')
        self.assertEqual(self.page.locator('#location-link-search').input_value(), '')
        self.assertEqual(self.patch(), {})
        self.assertEqual(self.page.locator('#location-linked-list [data-location-linked-id]').count(), 0)
        self.assert_no_writes()

    def test_new_unsaved_location_can_link_existing_markers_without_entering_the_snapshot(self):
        self.start_editor('legacy')
        before = self.data()
        draft = {
            'id': '  new "container\'"  ', 'name': 'Тестовая новая локация', 'type': 'landmark',
            'faction': None, 'x': 1500, 'y': 2500, 'owner': '', 'description': '', 'objects': [],
        }
        error = self.page.evaluate("""location => {
            try { window.__links.editor.fill(location); return ''; }
            catch (error) { return error.message; }
        }""", draft)
        self.assertEqual(error, '', 'new point forms have an ID before their parent transaction creates the record')
        self.assertEqual(self.patch(), {})
        self.page.locator('#location-is-location').focus()
        self.page.keyboard.press('Space')
        self.page.locator('#location-link-target').select_option(PRISON_ID)
        self.page.locator('#location-link-add').click()
        self.assertEqual(self.patch(), {'isLocation': True, 'linkedLocationIds': [PRISON_ID]})
        self.assertEqual(self.data(), before)
        self.assert_no_writes()

    def test_link_surfaces_use_scoped_registry_palette_and_accessible_responsive_geometry(self):
        baseline = copy.deepcopy(BASELINE)
        baseline['locations'][1]['linkedLocationIds'] = [PRISON_ID, 'port', 'legacy', SENTINEL_ID, ' ']
        baseline['locations'][2]['name'] = '  Тестовая тюрьма с длинным буквальным именем <script>window.bad=1</script>  '
        self.boot(baseline=baseline)
        measurements = []
        for width, height in [(1440, 1000), (390, 844), (844, 390)]:
            with self.subTest(width=width, height=height):
                self.page.set_viewport_size({'width': width, 'height': height})
                self.page.wait_for_function(
                    'getComputedStyle(document.documentElement).getPropertyValue("--app-height").trim() === `${window.innerHeight}px`',
                    polling=50)
                self.page.evaluate('window.__links.ui.setPanel("dossier", true); window.__links.renderLinks()')
                self.page.wait_for_timeout(250)
                rows = self.page.locator('#dossier-location-links button[data-location-link]').evaluate_all("""rows => rows.map(row => {
                    const box = row.getBoundingClientRect();
                    const glyph = row.querySelector('svg[data-type]').getBoundingClientRect();
                    const name = row.querySelector('.location-link-name');
                    const style = getComputedStyle(row);
                    return {width: box.width, height: box.height, display: style.display,
                        background: style.backgroundColor, color: style.color,
                        iconWidth: glyph.width, iconHeight: glyph.height,
                        overflow: row.scrollWidth > row.clientWidth + 1,
                        nameOverflow: name.scrollWidth > name.clientWidth + 1};
                })""")
                for row in rows:
                    self.assertEqual(row['display'], 'grid', 'type/name/return must have separate shrinkable tracks')
                    self.assertGreaterEqual(row['height'], 44)
                    self.assertEqual(row['background'], 'rgb(38, 40, 42)')
                    self.assertEqual(row['color'], 'rgb(221, 213, 194)')
                    self.assertLessEqual(row['iconWidth'], 24)
                    self.assertLessEqual(row['iconHeight'], 24)
                    self.assertFalse(row['overflow'])
                    self.assertFalse(row['nameOverflow'])
                last = self.page.locator('#dossier-location-links button[data-location-link]').last
                last.focus()
                self.page.keyboard.press('Enter')
                self.assertEqual(self.page.evaluate('window.__links.selected'), ' ')
                self.page.locator('#dossier-parent-locations button[data-location-link]').nth(0).focus()
                self.page.keyboard.press('Enter')
                self.assertEqual(self.page.evaluate('window.__links.selected'), DISTRICT_ID)
                self.page.screenshot(path=str(ARTIFACTS / f'linked-dossier-{width}x{height}.png'))
                if self.page.evaluate('typeof window.__links.editor') == 'undefined':
                    self.page.evaluate('window.__links.startEditor()')
                self.page.evaluate('id => window.__links.fillEditor(id)', DISTRICT_ID)
                self.page.mouse.move(0, 0)
                self.page.wait_for_timeout(250)
                controls = self.page.locator('#location-links-fields').evaluate("""fields => {
                    const measure = node => {
                        const box = node.getBoundingClientRect(), style = getComputedStyle(node);
                        return {id: node.id, x: box.x, y: box.y, width: box.width, height: box.height,
                            background: style.backgroundColor, color: style.color, border: style.borderColor};
                    };
                    return [...fields.querySelectorAll('#location-link-search,#location-link-target,#location-link-add,button[data-location-link-remove],.location-container-check')]
                        .map(measure);
                }""")
                for control in controls:
                    self.assertGreaterEqual(control['height'], 44, control['id'])
                    self.assertGreaterEqual(control['width'], 44)
                    self.assertGreaterEqual(control['x'], 0)
                    self.assertLessEqual(control['x'] + control['width'], width)
                    if control['id'] in ['location-link-search', 'location-link-target', 'location-link-add']:
                        self.assertEqual(control['background'], 'rgb(38, 40, 42)', control['id'])
                        self.assertEqual(control['color'], 'rgb(221, 213, 194)', control['id'])
                self.page.locator('#location-linked-list [data-location-link-remove]').last.focus()
                self.page.keyboard.press('Space')
                self.assertEqual(self.patch()['linkedLocationIds'], [PRISON_ID, 'port', 'legacy', SENTINEL_ID])
                save = self.page.locator('#location-form button[type=submit]')
                save.focus()
                self.assertEqual(self.page.evaluate('document.activeElement?.type'), 'submit')
                self.page.screenshot(path=str(ARTIFACTS / f'linked-editor-{width}x{height}.png'))
                self.page.keyboard.press('Escape')
                self.page.wait_for_function('!document.getElementById("location-editor").open')
                measurements.append({'viewport': [width, height], 'rows': rows, 'controls': controls})
        (ARTIFACTS / 'responsive-measurements.json').write_text(json.dumps(measurements, ensure_ascii=False, indent=2) + '\n')
        self.assert_no_writes()

    def test_link_hover_and_keyboard_focus_are_visible_without_restyling_existing_panels(self):
        self.boot()
        self.page.locator('#dossier-location-links button[data-location-link]').nth(0).focus()
        focused = self.page.locator('#dossier-location-links button[data-location-link]').nth(0).evaluate(
            'node => ({style: getComputedStyle(node).outlineStyle, width: getComputedStyle(node).outlineWidth})')
        self.assertEqual(focused, {'style': 'solid', 'width': '2px'})
        self.page.locator('#dossier-location-links button[data-location-link]').nth(0).hover()
        self.page.wait_for_timeout(250)
        hover = self.page.locator('#dossier-location-links button[data-location-link]').nth(0).evaluate(
            'node => ({background: getComputedStyle(node).backgroundColor, border: getComputedStyle(node).borderColor, color: getComputedStyle(node).color})')
        self.assertEqual(hover, {'background': 'rgb(48, 52, 50)', 'border': 'rgb(155, 138, 104)', 'color': 'rgb(224, 196, 147)'},
                         'link actions must expose the existing registry hover treatment')
        self.assert_no_writes()

    def test_refresh_preserves_a_removal_actions_exact_focus_without_recreating_form_inputs(self):
        self.start_editor(DISTRICT_ID)
        self.page.locator('#location-linked-list [data-location-link-remove]').nth(0).focus()
        result = self.page.evaluate("""() => {
            const name = document.getElementById('location-name');
            const search = document.getElementById('location-link-search');
            const target = document.getElementById('location-link-target');
            window.__links.editor.refresh();
            return {focused: document.activeElement?.dataset.locationLinkRemove,
                sameInputs: name === document.getElementById('location-name') &&
                    search === document.getElementById('location-link-search') && target === document.getElementById('location-link-target')};
        }""")
        self.assertEqual(result['focused'], PRISON_ID, 'refresh must retain focus by literal ID, never an interpolated selector')
        self.assertTrue(result['sameInputs'])
        self.assert_no_writes()


if __name__ == '__main__':
    unittest.main()
