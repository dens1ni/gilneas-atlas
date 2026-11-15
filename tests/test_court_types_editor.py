"""Shared type chooser and editor behavior against the real DOM and immutable model."""
import copy
import functools
import http.server
import threading
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DRAFT_KEY = 'court-types-test-draft'
BASELINE = {
    'version': 1,
    'meta': {
        'width': 3526, 'height': 4548,
        'image': 'assets/maps/gilneas-enhanced.webp',
        'inactiveMask': 'assets/maps/inactive-mask.png',
        'authorExtra': {'literal': '  <script>window.bad=1</script>  '},
    },
    'factions': [
        {'id': 'crown', 'name': 'Корона', 'parent': None, 'color': '#990000'},
        {'id': 'vassal', 'name': 'Дом Вассала', 'parent': 'crown', 'color': '#005577'},
    ],
    'locations': [
        {'id': 'keep', 'name': '  Тестовый замок  ', 'x': 1200, 'y': 2200,
         'type': 'fortress', 'faction': 'vassal', 'owner': 'Барон',
         'description': '  История замка  ', 'capital': False,
         'provenance': {'confidence': 'confirmed', 'note': '  Архив  ', 'sources': ['archive']},
         'objects': [], 'authorExtra': {'nested': ['  Literal  ', {'name': '<img onerror="window.bad=1">'}]}},
        {'id': 'port', 'name': 'Тестовый порт', 'x': 1800, 'y': 2800,
         'type': 'harbor', 'faction': 'crown', 'owner': '', 'description': 'Чужое досье', 'objects': []},
    ],
    'territories': [{'id': 'land', 'name': 'Тестовые земли', 'faction': 'vassal',
                     'points': [[1100, 2100], [1300, 2100], [1300, 2300], [1100, 2300]]}],
    'nobles': [{'id': 'baron', 'name': 'Тестовый барон', 'house': 'vassal', 'description': '  Биография  '}],
    'sources': [{'id': 'archive', 'title': 'Тестовый архив', 'url': 'https://example.invalid/archive'}],
    'authorRegistry': [{'literal': '  <script>window.bad=1</script>  '}],
}

BOOTSTRAP = """async ({baseline, key}) => {
    document.body.classList.add('edit-mode');
    const model = await import('/assets/js/model.mjs');
    const freeze = value => {
        if (value && typeof value === 'object') {
            Object.values(value).forEach(freeze);
            Object.freeze(value);
        }
        return value;
    };
    const loaded = model.loadDraft(localStorage, baseline, key);
    if (loaded.error) throw loaded.error;
    let data = freeze(loaded.data);
    let selected = 'keep';
    let interaction = null;
    const commits = [];
    window.__court = {
        get data() { return data; },
        commits,
        replace: next => { data = freeze(model.normalizeData(next)); },
        clickMap: point => interaction?.(point),
        original: structuredClone(data),
        model,
    };
    const {initEditor} = await import('/assets/js/editor.mjs');
    window.__court.editor = initEditor({
        getData: () => data,
        getSelectedId: () => selected,
        replaceData: next => {
            const normalized = model.normalizeData(next);
            model.saveDraft(localStorage, normalized, key);
            data = freeze(normalized);
            commits.push(structuredClone(data));
        },
        onSelect: id => { selected = id; },
        ui: {setMapInteraction: callback => { interaction = callback; }},
        canPlace: () => true,
        toast: () => {},
        confirm: async () => true,
    });
}"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class CourtTypesEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(args=[
            '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
        ])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1100})
        self.page = self.context.new_page()
        self.page_errors = []
        self.console_errors = []
        self.http_errors = []
        self.page.on('pageerror', lambda error: self.page_errors.append(str(error)))
        self.page.on('console', lambda message: self.console_errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.http_errors.append([response.status, response.url]) if response.status >= 400 else None)
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(status=200, content_type='text/javascript', body=''))
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')

    def tearDown(self):
        self.context.close()

    def init_editor(self, baseline=None):
        self.page.evaluate(BOOTSTRAP, {'baseline': baseline or BASELINE, 'key': DRAFT_KEY})

    def data(self):
        return self.page.evaluate('window.__court.data')

    def location(self, location_id='keep'):
        return next(record for record in self.data()['locations'] if record['id'] == location_id)

    def assert_clean(self):
        self.assertEqual(self.page_errors, [])
        self.assertEqual(self.console_errors, [])
        self.assertEqual(self.http_errors, [])
        self.assertIsNone(self.page.evaluate('window.bad'))

    def test_type_icons_are_safe_catalog_line_paths_for_every_kind(self):
        result = self.page.evaluate("""async () => {
            const catalog = await import('/assets/js/object-types.mjs');
            if (typeof catalog.createTypeIcon !== 'function') return {available: false};
            const types = [...catalog.TYPE_DEFINITIONS.map(record => record.id), '', ' farm ', '<script>window.bad=1</script>', '__proto__'];
            const icons = types.map(type => {
                const icon = catalog.createTypeIcon(type, 'court-type-icon gold-line');
                document.body.append(icon);
                return {
                    type, tag: icon.tagName, namespace: icon.namespaceURI,
                    viewBox: icon.getAttribute('viewBox'), fill: icon.getAttribute('fill'),
                    stroke: icon.getAttribute('stroke'), width: icon.getAttribute('stroke-width'),
                    linecap: icon.getAttribute('stroke-linecap'), linejoin: icon.getAttribute('stroke-linejoin'),
                    hidden: icon.getAttribute('aria-hidden'), focusable: icon.getAttribute('focusable'),
                    className: icon.getAttribute('class'), dataType: icon.getAttribute('data-type'),
                    path: icon.querySelector('path')?.getAttribute('d'),
                    children: [...icon.children].map(child => child.tagName),
                };
            });
            return {available: true, icons, definitions: catalog.TYPE_DEFINITIONS};
        }""")
        self.assertTrue(result['available'], 'createTypeIcon must be exported by the shared registry')
        paths = {record['id']: record['path'] for record in result['definitions']}
        self.assertGreaterEqual(len(set(paths.values())), 30, 'new useful kinds need distinct line geometry')
        for icon in result['icons']:
            with self.subTest(type=icon['type']):
                self.assertEqual(icon['tag'], 'svg')
                self.assertEqual(icon['namespace'], 'http://www.w3.org/2000/svg')
                self.assertEqual(icon['viewBox'], '0 0 24 24')
                self.assertEqual(icon['fill'], 'none')
                self.assertEqual(icon['stroke'], 'currentColor')
                self.assertGreater(float(icon['width']), 0)
                self.assertEqual(icon['linecap'], 'round')
                self.assertEqual(icon['linejoin'], 'round')
                self.assertEqual(icon['hidden'], 'true')
                self.assertEqual(icon['focusable'], 'false')
                self.assertEqual(icon['className'], 'court-type-icon gold-line')
                self.assertEqual(icon['dataType'], icon['type'])
                self.assertEqual(icon['children'], ['path'])
                self.assertEqual(icon['path'], paths.get(icon['type'], paths['landmark']))
        self.assert_clean()

    def test_populate_type_select_gives_both_scopes_the_complete_identical_catalog(self):
        result = self.page.evaluate("""async () => {
            const catalog = await import('/assets/js/object-types.mjs');
            if (typeof catalog.populateTypeSelect !== 'function') return {available: false};
            const object = document.createElement('select');
            const location = document.createElement('select');
            document.body.append(object, location);
            catalog.populateTypeSelect(object);
            catalog.populateTypeSelect(location, {scope: 'location'});
            const choices = select => [...select.options].map(option => ({id: option.value, label: option.textContent}));
            const first = {object: choices(object), location: choices(location), objectType: object.value, locationType: location.value};
            for (const definition of catalog.TYPE_DEFINITIONS) {
                catalog.populateTypeSelect(object, {currentType: definition.id});
                catalog.populateTypeSelect(location, {scope: 'location', currentType: definition.id});
                if (object.value !== definition.id || location.value !== definition.id ||
                    JSON.stringify(choices(object)) !== JSON.stringify(choices(location))) {
                    return {available: true, mismatch: definition.id};
                }
            }
            return {available: true, first, definitions: catalog.TYPE_DEFINITIONS};
        }""")
        self.assertTrue(result['available'], 'populateTypeSelect must be exported by the shared registry')
        self.assertNotIn('mismatch', result)
        expected = [{'id': record['id'], 'label': record['label']} for record in result['definitions']]
        self.assertEqual(result['first']['object'], expected)
        self.assertEqual(result['first']['location'], expected)
        self.assertEqual(result['first']['objectType'], 'building')
        self.assertEqual(result['first']['locationType'], 'settlement')
        self.assert_clean()

    def test_populate_type_select_preserves_a_temporary_literal_legacy_option_including_empty(self):
        result = self.page.evaluate("""async () => {
            const {TYPE_DEFINITIONS, populateTypeSelect} = await import('/assets/js/object-types.mjs');
            const select = document.createElement('select');
            document.body.append(select);
            const values = ['', 'custom-legacy-place', ' farm ', '<script>window.bad=1</script>', '__proto__'];
            const rows = values.map(value => {
                populateTypeSelect(select, {scope: 'location', currentType: value});
                const selected = select.selectedOptions[0];
                const result = {value, actual: select.value, selected: selected?.value, label: selected?.textContent,
                    options: [...select.options].map(option => option.value),
                    unsafe: select.querySelectorAll('script,img').length};
                populateTypeSelect(select, {scope: 'location', currentType: 'farm'});
                result.after = [...select.options].map(option => option.value);
                result.afterSelected = select.value;
                return result;
            });
            return {rows, ids: TYPE_DEFINITIONS.map(definition => definition.id)};
        }""")
        for row in result['rows']:
            with self.subTest(value=row['value']):
                self.assertEqual(row['actual'], row['value'])
                self.assertEqual(row.get('selected'), row['value'], 'legacy values need a real selected option, not selectedIndex=-1')
                self.assertEqual(row['label'], row['value'] or 'Не указан')
                self.assertEqual(row['options'][:-1], result['ids'])
                self.assertEqual(row['options'][-1], row['value'])
                self.assertEqual(row['unsafe'], 0)
                self.assertEqual(row['after'], result['ids'], 'temporary legacy options must not leak into the next record')
                self.assertEqual(row['afterSelected'], 'farm')
        self.assert_clean()

    def test_editor_initializes_both_real_forms_with_the_identical_shared_choices(self):
        self.init_editor()
        before = self.data()
        result = self.page.evaluate("""async () => {
            const {TYPE_DEFINITIONS} = await import('/assets/js/object-types.mjs');
            const choices = id => [...document.getElementById(id).options].map(option => ({id: option.value, label: option.textContent}));
            return {object: choices('object-type'), location: choices('location-type'),
                definitions: TYPE_DEFINITIONS.map(({id, label}) => ({id, label}))};
        }""")
        self.assertEqual(result['object'], result['definitions'])
        self.assertEqual(result['location'], result['definitions'])
        self.page.evaluate("window.__court.editor.addObject('keep')")
        self.assertEqual(self.page.locator('#object-type').input_value(), 'building')
        self.assertEqual(self.data(), before)
        self.assert_clean()

    def test_explicit_object_owner_placeholder_does_not_claim_parent_inheritance(self):
        self.init_editor()
        before = self.data()
        self.page.evaluate("window.__court.editor.addObject('keep')")
        self.assertEqual(self.page.locator('#object-owner').get_attribute('placeholder'), 'Не установлен')
        self.assertEqual(self.page.locator('#object-owner').input_value(), '')
        self.assertEqual(self.page.locator('#object-faction').input_value(), '__inherit__')
        self.assertEqual(self.data(), before)
        self.assert_clean()

    def test_every_object_kind_exposes_the_generic_bonus_and_penalty_editor(self):
        self.init_editor()
        before = self.data()
        self.page.evaluate("window.__court.editor.addObject('keep')")
        self.page.locator('#object-type').select_option('resource')
        self.assertTrue(self.page.locator('#modifier-fields').is_visible(), 'resources can have bonuses and penalties too')
        self.assertEqual(self.page.locator('#modifier-fields h3').text_content(), 'Модификаторы объекта')
        choices = self.page.evaluate("[...document.getElementById('object-type').options].map(option => option.value)")
        for type_id in choices:
            with self.subTest(type=type_id):
                self.page.locator('#object-type').select_option(type_id)
                self.assertTrue(self.page.locator('#modifier-fields').is_visible())
                self.assertEqual(self.page.locator('#object-amount-field').is_visible(), type_id == 'resource')
        self.assertEqual(self.data(), before)
        self.assert_clean()

    def test_resource_submission_saves_literal_bonus_and_penalty_records_across_reload(self):
        self.init_editor()
        before = self.data()
        self.page.evaluate("window.__court.editor.addObject('keep')")
        self.page.locator('#object-type').select_option('resource')
        name = '  Железо <script>window.bad=1</script>  '
        self.page.locator('#object-name').fill(name)
        self.page.locator('#object-description').fill('  Запас для войска  ')
        self.page.locator('#object-amount').fill('  20 тонн  ')
        self.page.locator('#modifier-bonus-add').click()
        self.page.locator('#modifier-list textarea').nth(0).fill('  Снабжение <script>window.bad=1</script>  ')
        self.page.locator('#modifier-penalty-add').click()
        self.page.locator('#modifier-list textarea').nth(1).fill('  +2 расходы — штраф  ')
        modifier_ids = self.page.locator('.modifier-editor-row').evaluate_all('rows => rows.map(row => row.dataset.modifierId)')
        self.page.locator('#object-form button[type=submit]').click()
        self.assertEqual(self.page.locator('#object-form-error').text_content(), '')
        self.assertFalse(self.page.locator('#object-editor').is_visible())
        obj = self.location()['objects'][0]
        self.assertEqual([modifier['id'] for modifier in obj['modifiers']], modifier_ids)
        self.assertEqual([modifier['kind'] for modifier in obj['modifiers']], ['bonus', 'penalty'])
        self.assertEqual([modifier['text'] for modifier in obj['modifiers']], [
            '  Снабжение <script>window.bad=1</script>  ', '  +2 расходы — штраф  ',
        ])
        self.assertEqual(obj['type'], 'resource')
        self.assertEqual(obj['name'], name)
        self.assertEqual(obj['description'], '  Запас для войска  ')
        self.assertEqual(obj['amount'], '  20 тонн  ')
        self.assertEqual(obj['owner'], '')
        self.assertNotIn('faction', obj)
        expected = copy.deepcopy(before)
        expected['locations'][0]['objects'].append(obj)
        self.assertEqual(self.data(), expected)
        self.assertEqual(self.page.evaluate('window.__court.commits.length'), 1)
        self.page.reload()
        self.init_editor()
        self.assertEqual(self.data(), expected)
        self.page.evaluate("id => window.__court.editor.editObject('keep', id)", obj['id'])
        self.assertEqual(self.page.locator('#object-name').input_value(), name)
        self.assertEqual(self.page.locator('#modifier-list textarea').nth(0).input_value(), obj['modifiers'][0]['text'])
        self.assert_clean()

    def test_location_edit_keeps_empty_and_custom_legacy_type_ids_literal_on_save(self):
        self.init_editor()
        catalog_ids = self.page.evaluate("[...document.getElementById('location-type').options].map(option => option.value)")
        for type_id in ['', 'custom-legacy-place', ' farm ', '<script>window.bad=1</script>']:
            with self.subTest(type=type_id):
                data = copy.deepcopy(BASELINE)
                data['locations'][0]['type'] = type_id
                data['locations'][0]['objects'] = [{
                    'id': 'hall', 'name': '  Зал  ', 'type': 'building', 'owner': '', 'description': '  История  ',
                    'modifiers': [{'id': 'prestige', 'kind': 'bonus', 'text': '  Престиж  ', 'extra': {'literal': '<script>literal</script>'}}],
                    'custom': {'nested': ['  Object metadata  ']},
                }]
                self.page.evaluate('data => window.__court.replace(data)', data)
                before = self.data()
                self.page.evaluate("window.__court.editor.editLocation('keep')")
                self.assertEqual(self.page.locator('#location-type').input_value(), type_id)
                selected = self.page.locator('#location-type').evaluate('select => select.selectedOptions[0]?.value')
                self.assertEqual(selected, type_id, 'an empty or legacy location type must remain a real selected option')
                choices = self.page.locator('#location-type').evaluate('select => [...select.options].map(option => option.value)')
                self.assertEqual(choices, catalog_ids + [type_id])
                name = '  Досье <script>window.bad=1</script>  '
                self.page.locator('#location-name').fill(name)
                self.page.locator('#location-form button[type=submit]').click()
                self.assertEqual(self.page.locator('#location-form-error').text_content(), '')
                expected = copy.deepcopy(before)
                expected['locations'][0]['name'] = name
                self.assertEqual(self.data(), expected)
        self.page.evaluate("window.__court.editor.editLocation('port')")
        self.assertEqual(self.page.locator('#location-type').input_value(), 'harbor')
        self.assertEqual(self.page.locator('#location-type').evaluate('select => [...select.options].map(option => option.value)'), catalog_ids)
        self.assert_clean()

    def test_editing_resource_amount_then_changing_kind_does_not_discard_the_entered_value(self):
        baseline = copy.deepcopy(BASELINE)
        baseline['locations'][0]['objects'] = [{
            'id': 'ore', 'type': 'resource', 'name': '  Железо  ', 'owner': '', 'description': '  Запас  ',
            'amount': '  20 тонн  ', 'faction': None,
            'modifiers': [{'id': 'supply', 'kind': 'bonus', 'text': '  Снабжение  '},
                          {'id': 'cost', 'kind': 'penalty', 'text': '  Расходы  '}],
            'extra': {'literal': '  <script>window.bad=1</script>  '},
        }]
        self.init_editor(baseline)
        before = self.data()
        self.page.evaluate("window.__court.editor.editObject('keep', 'ore')")
        self.page.locator('#object-amount').fill('  30 тонн  ')
        self.page.locator('#object-type').select_option('building')
        self.assertFalse(self.page.locator('#object-amount-field').is_visible())
        self.assertEqual(self.page.locator('#object-amount').input_value(), '  30 тонн  ')
        self.page.locator('#object-form button[type=submit]').click()
        self.assertEqual(self.page.locator('#object-form-error').text_content(), '')
        expected = copy.deepcopy(before)
        expected['locations'][0]['objects'][0].update(type='building', amount='  30 тонн  ')
        self.assertEqual(self.data(), expected)
        self.page.reload()
        self.init_editor(baseline)
        self.assertEqual(self.data(), expected)
        self.page.evaluate("window.__court.editor.editObject('keep', 'ore')")
        self.page.locator('#object-type').select_option('resource')
        self.assertEqual(self.page.locator('#object-amount').input_value(), '  30 тонн  ')
        self.assertEqual(self.page.locator('#object-faction').input_value(), '__independent__')
        self.assert_clean()

    def test_an_unchanged_numeric_stock_is_not_converted_to_text_by_a_kind_edit(self):
        baseline = copy.deepcopy(BASELINE)
        baseline['locations'][0]['objects'] = [{
            'id': 'ore', 'type': 'resource', 'name': 'Железо', 'owner': '', 'description': '', 'amount': 0,
            'modifiers': [{'id': 'supply', 'kind': 'bonus', 'text': '  Снабжение  '}],
        }]
        self.init_editor(baseline)
        before = self.data()
        self.page.evaluate("window.__court.editor.editObject('keep', 'ore')")
        self.assertEqual(self.page.locator('#object-amount').input_value(), '0')
        self.page.locator('#object-type').select_option('building')
        self.page.locator('#object-form button[type=submit]').click()
        expected = copy.deepcopy(before)
        expected['locations'][0]['objects'][0]['type'] = 'building'
        self.assertEqual(self.data(), expected)
        self.assertEqual(type(self.location()['objects'][0]['amount']), int)
        self.assert_clean()

    def test_new_kinds_create_effects_and_explicit_faction_semantics_then_reload_without_unrelated_changes(self):
        self.init_editor()
        before = self.data()
        kinds = [('farm', '__inherit__'), ('workshop', '__independent__'), ('barracks', 'vassal'),
                 ('mine', '__inherit__'), ('church', '__independent__'), ('cemetery', 'crown')]
        records = []
        for type_id, faction in kinds:
            with self.subTest(type=type_id):
                self.page.evaluate("window.__court.editor.addObject('keep')")
                self.assertEqual(self.page.locator('#object-type').input_value(), 'building')
                self.page.locator('#object-type').select_option(type_id)
                name = f'  {type_id} <script>window.bad=1</script>  '
                self.page.locator('#object-name').fill(name)
                self.page.locator('#object-description').fill(f'  Описание {type_id}  ')
                self.page.locator('#object-faction').select_option(faction)
                self.page.locator('#modifier-bonus-add').click()
                self.page.locator('#modifier-list textarea').nth(0).fill(f'  Доход {type_id}  ')
                self.page.locator('#modifier-penalty-add').click()
                self.page.locator('#modifier-list textarea').nth(1).fill(f'  +2 расходы {type_id}  ')
                ids = self.page.locator('.modifier-editor-row').evaluate_all('rows => rows.map(row => row.dataset.modifierId)')
                self.page.locator('#object-form button[type=submit]').click()
                self.assertEqual(self.page.locator('#object-form-error').text_content(), '')
                self.assertFalse(self.page.locator('#object-editor').is_visible())
                obj = self.location()['objects'][-1]
                self.assertEqual(obj['type'], type_id)
                self.assertEqual(obj['name'], name)
                self.assertEqual(obj['description'], f'  Описание {type_id}  ')
                self.assertEqual(obj['owner'], '')
                self.assertEqual([modifier['id'] for modifier in obj['modifiers']], ids)
                self.assertEqual([modifier['kind'] for modifier in obj['modifiers']], ['bonus', 'penalty'])
                self.assertEqual([modifier['text'] for modifier in obj['modifiers']], [f'  Доход {type_id}  ', f'  +2 расходы {type_id}  '])
                if faction == '__inherit__':
                    self.assertNotIn('faction', obj)
                else:
                    self.assertEqual(obj['faction'], None if faction == '__independent__' else faction)
                records.append(obj)
        expected = copy.deepcopy(before)
        expected['locations'][0]['objects'].extend(records)
        self.assertEqual(self.data(), expected)
        self.assertEqual(self.page.evaluate('window.__court.commits.length'), len(kinds))
        self.page.reload()
        self.init_editor()
        self.assertEqual(self.data(), expected)
        for obj, (_type_id, faction) in zip(records, kinds):
            self.page.evaluate("id => window.__court.editor.editObject('keep', id)", obj['id'])
            self.assertEqual(self.page.locator('#object-type').input_value(), obj['type'])
            self.assertEqual(self.page.locator('#object-name').input_value(), obj['name'])
            self.assertEqual(self.page.locator('#object-faction').input_value(), faction)
            self.assertEqual(self.page.locator('#modifier-list textarea').nth(0).input_value(), obj['modifiers'][0]['text'])
        self.assert_clean()

    def test_resource_to_farm_kind_edit_keeps_exact_ids_effects_stock_and_unrelated_snapshot_then_reload(self):
        baseline = copy.deepcopy(BASELINE)
        baseline['locations'][0]['objects'] = [
            {'id': 'ore', 'type': 'resource', 'name': '  Запас  ', 'description': '  История  ', 'owner': '',
             'amount': '  20 тонн  ', 'faction': None,
             'modifiers': [{'id': 'supply', 'kind': 'bonus', 'text': '  Снабжение  ', 'custom': {'literal': '<script>literal</script>'}},
                           {'id': 'cost', 'kind': 'penalty', 'text': '  +2 расходы  '}],
             'custom': {'nested': [{'name': '  Дополнение  '}]}},
            {'id': 'sibling', 'type': 'building', 'name': '  Соседний объект  ', 'owner': '', 'description': '',
             'modifiers': [{'id': 'prestige', 'kind': 'bonus', 'text': '  Престиж  '}]},
        ]
        self.init_editor(baseline)
        before = self.data()
        self.page.evaluate("window.__court.editor.editObject('keep', 'ore')")
        self.page.locator('#object-type').select_option('farm')
        self.assertTrue(self.page.locator('#modifier-fields').is_visible())
        self.assertFalse(self.page.locator('#object-amount-field').is_visible())
        self.page.locator('#object-form button[type=submit]').click()
        self.assertEqual(self.page.locator('#object-form-error').text_content(), '')
        expected = copy.deepcopy(before)
        expected['locations'][0]['objects'][0]['type'] = 'farm'
        self.assertEqual(self.data(), expected)
        self.assertEqual(self.page.evaluate('window.__court.commits.length'), 1)
        self.page.reload()
        self.init_editor(baseline)
        self.assertEqual(self.data(), expected)
        self.page.evaluate("window.__court.editor.editObject('keep', 'ore')")
        self.assertEqual(self.page.locator('#object-type').input_value(), 'farm')
        self.assertEqual(self.page.locator('.modifier-editor-row').evaluate_all('rows => rows.map(row => row.dataset.modifierId)'), ['supply', 'cost'])
        self.page.locator('#object-type').select_option('resource')
        self.assertEqual(self.page.locator('#object-amount').input_value(), '  20 тонн  ')
        self.assert_clean()

    def test_direct_map_locations_can_create_and_reload_new_kinds_without_rewriting_other_records(self):
        self.init_editor()
        before = self.data()
        records = []
        kinds = ['farm', 'workshop', 'church', 'cemetery', 'granary', 'shipyard']
        for index, type_id in enumerate(kinds):
            with self.subTest(type=type_id):
                self.page.evaluate('window.__court.editor.open()')
                self.page.locator('#location-create').click()
                self.page.evaluate('point => window.__court.clickMap(point)', [1500 + index, 2400 + index])
                self.assertEqual(self.page.locator('#location-type').input_value(), 'settlement')
                self.page.locator('#location-type').select_option(type_id)
                self.page.locator('#location-name').fill(f'  {type_id} <script>window.bad=1</script>  ')
                self.page.locator('#location-owner').fill('')
                self.page.locator('#location-description').fill(f'  История {type_id}  ')
                self.page.locator('#location-form button[type=submit]').click()
                self.assertEqual(self.page.locator('#location-form-error').text_content(), '')
                self.assertFalse(self.page.locator('#location-editor').is_visible())
                location = self.data()['locations'][-1]
                self.assertEqual(location['type'], type_id)
                self.assertEqual(location['name'], f'  {type_id} <script>window.bad=1</script>  ')
                self.assertEqual(location['description'], f'  История {type_id}  ')
                self.assertEqual(location['owner'], '')
                self.assertIsNone(location['faction'])
                self.assertEqual(location['objects'], [])
                self.assertEqual([location['x'], location['y']], [1500 + index, 2400 + index])
                records.append(location)
        expected = copy.deepcopy(before)
        expected['locations'].extend(records)
        self.assertEqual(self.data(), expected)
        self.assertEqual(self.page.evaluate('window.__court.commits.length'), len(kinds))
        self.page.reload()
        self.init_editor()
        self.assertEqual(self.data(), expected)
        for location in records:
            self.page.evaluate('id => window.__court.editor.editLocation(id)', location['id'])
            self.assertEqual(self.page.locator('#location-type').input_value(), location['type'])
            self.assertEqual(self.page.locator('#location-name').input_value(), location['name'])
        self.assert_clean()

    def test_every_catalog_type_is_selected_in_both_editor_forms_without_losing_choices(self):
        self.init_editor()
        error = self.page.evaluate("""() => {
            const data = structuredClone(window.__court.data);
            data.locations[0].objects.push({id: 'probe', type: 'farm', name: 'Тестовая ферма', modifiers: []});
            try { window.__court.model.normalizeData(data); return ''; }
            catch (error) { return error.message; }
        }""")
        self.assertEqual(error, '', 'the shared catalog must be integrated into real model validation')
        definitions = self.page.evaluate("async () => (await import('/assets/js/object-types.mjs')).TYPE_DEFINITIONS")
        expected_choices = [{'id': record['id'], 'label': record['label']} for record in definitions]
        for definition in definitions:
            with self.subTest(type=definition['id']):
                baseline = copy.deepcopy(BASELINE)
                baseline['locations'][0]['type'] = definition['id']
                baseline['locations'][0]['objects'] = [{
                    'id': 'typed-object', 'type': definition['id'], 'name': '  Тестовый объект  ', 'owner': '', 'description': '',
                    'modifiers': [{'id': 'effect', 'kind': 'bonus', 'text': '  Не терять  '}],
                }]
                self.page.evaluate('data => window.__court.replace(data)', baseline)
                before = self.data()
                self.page.evaluate("window.__court.editor.editLocation('keep')")
                self.assertEqual(self.page.locator('#location-type').input_value(), definition['id'])
                self.assertEqual(self.page.locator('#location-type').evaluate(
                    'select => [...select.options].map(option => ({id: option.value, label: option.textContent}))'), expected_choices)
                self.page.evaluate("window.__court.editor.editObject('keep', 'typed-object')")
                self.assertEqual(self.page.locator('#object-type').input_value(), definition['id'])
                self.assertEqual(self.page.locator('#object-type').evaluate(
                    'select => [...select.options].map(option => ({id: option.value, label: option.textContent}))'), expected_choices)
                self.assertEqual(self.data(), before)
        self.assert_clean()

    def test_opening_an_object_removes_the_previous_records_temporary_type_choice(self):
        self.init_editor()
        self.page.evaluate("""async () => {
            const {populateTypeSelect} = await import('/assets/js/object-types.mjs');
            populateTypeSelect(document.getElementById('object-type'), {currentType: 'temporary-legacy'});
        }""")
        self.page.evaluate("window.__court.editor.addObject('keep')")
        result = self.page.evaluate("""async () => {
            const {TYPE_DEFINITIONS} = await import('/assets/js/object-types.mjs');
            return {actual: [...document.getElementById('object-type').options].map(option => option.value),
                    expected: TYPE_DEFINITIONS.map(definition => definition.id)};
        }""")
        self.assertEqual(result['actual'], result['expected'])
        self.assertEqual(self.page.locator('#object-type').input_value(), 'building')
        self.assert_clean()


if __name__ == '__main__':
    unittest.main()
