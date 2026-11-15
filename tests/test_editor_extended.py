"""Isolated real-DOM editor tests; only the parent bootstrap/camera is replaced."""
import functools
import http.server
import threading
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

BASELINE = {
    'version': 1,
    'meta': {'width': 3247, 'height': 4860, 'image': 'assets/map.webp', 'inactiveMask': 'assets/mist.webp'},
    'factions': [
        {'id': 'crown', 'name': 'Корона', 'parent': None, 'color': '#990000', 'ruler': 'Король'},
        {'id': 'vassal', 'name': 'Дом Вассала', 'parent': 'crown', 'color': '#005577', 'ruler': 'Барон'},
        {'id': 'free-house', 'name': 'Свободный дом', 'parent': None, 'color': '#778899'},
    ],
    'locations': [
        {'id': 'keep', 'name': 'Замок', 'x': 1200, 'y': 2200, 'type': 'fortress', 'faction': 'vassal',
         'owner': 'Барон', 'description': 'История замка', 'capital': False,
         'provenance': {'confidence': 'confirmed', 'chronology': 'До Стены', 'note': 'Архив', 'sources': ['archive']},
         'objects': []},
        {'id': 'port', 'name': 'Порт', 'x': 1800, 'y': 2800, 'type': 'harbor', 'faction': 'crown',
         'owner': '', 'description': 'Чужое досье', 'objects': []},
    ],
    'territories': [],
    'nobles': [{'id': 'baron', 'name': 'Барон', 'faction': 'vassal'}],
    'sources': [{'id': 'archive', 'title': 'Архив', 'url': 'https://example.invalid/archive'}],
}

BOOTSTRAP = """async (baseline) => {
    document.body.classList.add('edit-mode');
    const model = await import('/assets/js/model.mjs');
    let data = model.normalizeData(baseline);
    let selected = 'keep';
    let interaction = null;
    const errors = [];
    const commits = [];
    const events = [];
    const freeze = value => {
        if (value && typeof value === 'object') {
            Object.values(value).forEach(freeze);
            Object.freeze(value);
        }
        return value;
    };
    data = freeze(data);
    window.__atlas = {
        get data() { return data; },
        get selected() { return selected; },
        errors, commits, events,
        confirmation: true,
        canPlace: true,
        failCommit: false,
        failParent: false,
        clickMap: async (point, event = {}) => {
            if (interaction) await interaction(point, event);
        },
        get interacting() { return typeof interaction === 'function'; },
        replace: next => { data = freeze(model.normalizeData(next)); },
        select: id => { selected = id; },
    };
    const ui = {
        setMapInteraction: callback => { interaction = callback; },
        toMap: (x, y) => [x, y],
        focusLocation: id => events.push(['focus', id]),
    };
    try {
        const {initEditor} = await import('/assets/js/editor.mjs');
        const editor = initEditor({
            getData: () => data,
            getSelectedId: () => selected,
            replaceData: next => {
                if (window.__atlas.failCommit) throw new Error('Черновик не сохранён: квота хранилища');
                data = freeze(model.normalizeData(next));
                commits.push(structuredClone(data));
            },
            onSelect: id => { selected = id; events.push(['select', id]); },
            ui,
            canPlace: () => window.__atlas.canPlace,
            toast: message => events.push(['toast', message]),
            confirm: async (title, message) => {
                events.push(['confirm', title, message]);
                return window.__atlas.confirmation;
            },
            onExportSite: async () => events.push(['site']),
            onExportJson: () => events.push(['json']),
            onImport: async file => events.push(['import', file.name]),
            onReset: async () => {
                if (window.__atlas.failParent) {
                    document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
                    throw new Error('Не удалось восстановить <script>window.bad=1</script>');
                }
                events.push(['reset']);
            },
        });
        window.__atlas.editor = editor;
        document.querySelector('#editor-open').addEventListener('click', editor.open);
    } catch (error) {
        errors.push(error.message);
    }
}"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class IsolatedEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(QuietHandler, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.page = self.browser.new_page(viewport={'width': 1440, 'height': 1000})
        self.page_errors = []
        self.page.on('pageerror', lambda error: self.page_errors.append(str(error)))
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(status=200, content_type='text/javascript', body=''))
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')
        self.page.evaluate(BOOTSTRAP, BASELINE)

    def tearDown(self):
        self.page.close()

    def assert_ready(self):
        self.assertEqual(self.page.evaluate('window.__atlas.errors'), [], 'editor module should initialize against the real DOM')
        self.assertEqual(self.page_errors, [])

    def data(self):
        return self.page.evaluate('window.__atlas.data')

    def location(self, location_id='keep'):
        return next(record for record in self.data()['locations'] if record['id'] == location_id)

    def test_building_commits_semantic_bonus_and_penalty_once(self):
        self.assert_ready()
        self.page.evaluate("window.__atlas.editor.addObject('keep')")
        self.assertTrue(self.page.locator('#object-editor').is_visible())
        self.assertEqual(self.page.locator('#object-editor').get_attribute('aria-labelledby'), 'object-form-title')
        self.page.locator('#object-name').fill('  Кузница <script>window.bad=1</script>  ')
        self.page.locator('#object-description').fill('  Сталь для войска  ')
        self.page.locator('#modifier-bonus-add').click()
        self.page.locator('#modifier-list textarea').nth(0).fill('Без числового знака — снабжение')
        self.page.locator('#modifier-penalty-add').click()
        self.page.locator('#modifier-list textarea').nth(1).fill('+2 расходы, но это штраф')
        self.assertEqual(self.page.locator('.modifier-editor-row.bonus').count(), 1)
        self.assertEqual(self.page.locator('.modifier-editor-row.penalty').count(), 1)
        self.assertNotEqual(
            self.page.locator('.modifier-editor-row.bonus').evaluate("e => getComputedStyle(e).borderLeftColor"),
            self.page.locator('.modifier-editor-row.penalty').evaluate("e => getComputedStyle(e).borderLeftColor"),
        )
        self.page.locator('#object-form button[type=submit]').click()
        self.assertFalse(self.page.locator('#object-editor').is_visible())
        obj = self.location()['objects'][0]
        self.assertEqual(obj['name'], '  Кузница <script>window.bad=1</script>  ')
        self.assertEqual(obj['description'], '  Сталь для войска  ')
        self.assertEqual([modifier['kind'] for modifier in obj['modifiers']], ['bonus', 'penalty'])
        self.assertEqual([modifier['text'] for modifier in obj['modifiers']], ['Без числового знака — снабжение', '+2 расходы, но это штраф'])
        self.assertTrue(obj['id'].startswith('object-'))
        self.assertEqual(len({obj['id'], *(modifier['id'] for modifier in obj['modifiers'])}), 3)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertIsNone(self.page.evaluate('window.bad'))
        self.assertEqual(self.page_errors, [])
    def test_edit_object_preserves_ids_and_unrelated_records_with_explicit_independence(self):
        self.assert_ready()
        self.page.evaluate("""() => {
            const data = structuredClone(window.__atlas.data);
            data.locations[0].objects = [
                {id: 'smithy', type: 'building', name: 'Кузница', owner: '', description: 'Сталь',
                 modifiers: [{id: 'supply', kind: 'bonus', text: 'Снабжение'}, {id: 'cost', kind: 'penalty', text: 'Расходы'}],
                 provenance: {note: 'Не потерять'}},
                {id: 'ore', type: 'resource', name: 'Железо', amount: '20 тонн', modifiers: []},
            ];
            window.__atlas.replace(data);
        }""")
        before = self.data()
        self.assertEqual(self.page.evaluate('typeof window.__atlas.editor.editObject'), 'function', 'existing objects need an edit workflow')
        self.page.evaluate("window.__atlas.editor.editObject('keep', 'smithy')")
        self.assertEqual(self.page.locator('#object-faction').input_value(), '__inherit__')
        self.page.locator('#object-faction').select_option('__independent__')
        self.page.locator('#object-owner').fill('  Мастер  ')
        self.page.locator('#object-name').fill('Новая кузница')
        self.page.locator('#modifier-list textarea').nth(0).fill('Лучшее снабжение')
        self.page.locator('#object-form button[type=submit]').click()
        after = self.data()
        expected = before
        obj = expected['locations'][0]['objects'][0]
        obj.update(name='Новая кузница', owner='  Мастер  ', faction=None)
        obj['modifiers'][0]['text'] = 'Лучшее снабжение'
        self.assertEqual(after, expected)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.page.evaluate("window.__atlas.editor.editObject('keep', 'smithy')")
        self.assertEqual(self.page.locator('#object-faction').input_value(), '__independent__')
        self.page.locator('#object-faction').select_option('__inherit__')
        self.page.locator('#object-form button[type=submit]').click()
        self.assertNotIn('faction', self.location()['objects'][0])
        self.assertEqual(self.location()['objects'][0]['id'], 'smithy')
        self.assertEqual([m['id'] for m in self.location()['objects'][0]['modifiers']], ['supply', 'cost'])
        self.assertEqual(self.page_errors, [])
    def test_resource_type_toggle_preserves_unsaved_building_modifiers_until_save(self):
        self.assert_ready()
        self.page.evaluate("window.__atlas.editor.addObject('keep')")
        self.page.locator('#object-name').fill('Железный рудник')
        self.page.locator('#modifier-bonus-add').click()
        self.page.locator('#modifier-list textarea').fill('Снабжение')
        modifier_id = self.page.locator('.modifier-editor-row').get_attribute('data-modifier-id')
        self.page.locator('#object-type').select_option('resource')
        self.assertTrue(self.page.locator('#object-amount-field').is_visible(), 'resources expose an amount field')
        self.assertTrue(self.page.locator('#modifier-fields').is_visible(), 'The expanded shared catalog keeps resource effects editable')
        self.page.locator('#object-amount').fill('  20 тонн железа  ')
        self.page.locator('#object-type').select_option('building')
        self.assertEqual(self.page.locator('#modifier-list textarea').input_value(), 'Снабжение')
        self.assertEqual(self.page.locator('.modifier-editor-row').get_attribute('data-modifier-id'), modifier_id)
        self.page.locator('#object-type').select_option('resource')
        self.page.locator('#object-form button[type=submit]').click()
        obj = self.location()['objects'][0]
        self.assertEqual(obj['type'], 'resource')
        self.assertEqual(obj['amount'], '  20 тонн железа  ')
        self.assertEqual(obj['modifiers'], [{'id':modifier_id,'kind':'bonus','text':'Снабжение'}], 'Changing to resource preserves effects instead of discarding them')
        self.page.evaluate("window.__atlas.editor.editObject('keep', window.__atlas.data.locations[0].objects[0].id)")
        self.assertEqual(self.page.locator('#object-amount').input_value(), '  20 тонн железа  ')
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertEqual(self.page_errors, [])
    def test_modifier_remove_and_cancel_discard_unsaved_changes(self):
        self.assert_ready()
        before = self.data()
        self.page.evaluate("window.__atlas.editor.addObject('keep')")
        self.page.locator('#object-name').fill('Не сохранять')
        self.page.locator('#modifier-bonus-add').click()
        self.page.locator('#modifier-list textarea').fill('Первый')
        self.page.locator('#modifier-penalty-add').click()
        self.page.locator('#modifier-list textarea').nth(1).fill('Второй')
        survivor = self.page.locator('.modifier-editor-row').nth(1).get_attribute('data-modifier-id')
        self.assertEqual(self.page.locator('[data-modifier-remove]').count(), 2, 'each modifier needs an accessible delete control')
        self.page.locator('[data-modifier-remove]').nth(0).click()
        self.assertEqual(self.page.locator('#modifier-list textarea').count(), 1)
        self.assertEqual(self.page.locator('#modifier-list textarea').input_value(), 'Второй')
        self.assertEqual(self.page.locator('.modifier-editor-row').get_attribute('data-modifier-id'), survivor)
        self.page.locator('[data-close="object-editor"]').click()
        self.assertFalse(self.page.locator('#object-editor').is_visible())
        self.assertEqual(self.data(), before)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.page.evaluate("window.__atlas.editor.addObject('keep')")
        self.assertEqual(self.page.locator('#modifier-list textarea').count(), 0)
        self.assertEqual(self.page_errors, [])
    def test_object_deletion_uses_confirmation_and_exact_target(self):
        self.assert_ready()
        self.page.evaluate("""() => {
            const data = structuredClone(window.__atlas.data);
            data.locations[0].objects = [{id: 'smithy', name: 'Кузница', type: 'building', modifiers: []},
                                         {id: 'ore', name: 'Руда', type: 'resource', amount: '20', modifiers: []}];
            window.__atlas.replace(data);
        }""")
        before = self.data()
        self.assertEqual(self.page.evaluate('typeof window.__atlas.editor.deleteObject'), 'function', 'objects need a confirmation-gated delete workflow')
        self.page.evaluate('window.__atlas.confirmation = false')
        self.page.evaluate("window.__atlas.editor.deleteObject('keep', 'smithy')")
        self.assertEqual(self.data(), before)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.page.evaluate('window.__atlas.confirmation = true')
        self.page.evaluate("window.__atlas.editor.deleteObject('keep', 'smithy')")
        expected = before
        expected['locations'][0]['objects'] = expected['locations'][0]['objects'][1:]
        self.assertEqual(self.data(), expected)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        confirmations = self.page.evaluate("window.__atlas.events.filter(e => e[0] === 'confirm')")
        self.assertEqual(len(confirmations), 2)
        self.assertIn('Кузница', confirmations[0][2])
        self.assertEqual(self.page_errors, [])
    def test_location_edit_preserves_nested_objects_provenance_and_other_registries(self):
        self.assert_ready()
        self.page.evaluate("""() => {
            const data = structuredClone(window.__atlas.data);
            data.locations[0].objects = [{id: 'hall', name: 'Зал', type: 'building',
                modifiers: [{id: 'prestige', kind: 'bonus', text: 'Престиж'}]}];
            window.__atlas.replace(data);
        }""")
        before = self.data()
        self.assertEqual(self.page.evaluate('typeof window.__atlas.editor.editLocation'), 'function', 'locations need a full dossier edit workflow')
        self.page.evaluate("window.__atlas.editor.editLocation('keep')")
        self.assertTrue(self.page.locator('#location-editor').is_visible())
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'location-editor')
        self.page.locator('#location-name').fill('  Каменный замок  ')
        self.page.locator('#location-owner').fill('')
        self.page.locator('#location-description').fill('  Новая история <img onerror="window.bad=1">  ')
        self.page.locator('#location-capital').check()
        self.page.locator('#location-form button[type=submit]').click()
        expected = before
        expected['locations'][0].update(name='  Каменный замок  ', owner='',
            description='  Новая история <img onerror="window.bad=1">  ', capital=True)
        self.assertEqual(self.data(), expected)
        self.assertFalse(self.page.locator('#location-editor').is_visible())
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertIsNone(self.page.evaluate('window.bad'))
        self.assertEqual(self.page_errors, [])
    def test_new_location_picks_active_coordinate_then_commits_once_on_save(self):
        self.assert_ready()
        before = self.data()
        self.assertEqual(self.page.evaluate('typeof window.__atlas.editor.open'), 'function', 'dashboard opens editor actions')
        self.page.locator('#editor-open').click()
        self.assertEqual(self.page.locator('#editor-selection-name').inner_text(), 'Замок')
        self.page.locator('#location-create').click()
        self.assertFalse(self.page.locator('#editor').is_visible())
        self.assertTrue(self.page.locator('#map-task').is_visible())
        self.assertTrue(self.page.evaluate('window.__atlas.interacting'))
        self.page.evaluate('window.__atlas.canPlace = false')
        self.page.evaluate('window.__atlas.clickMap([1500,2400])')
        self.assertFalse(self.page.locator('#location-editor').is_visible())
        self.assertEqual(self.data(), before)
        self.page.evaluate('window.__atlas.canPlace = true')
        self.page.evaluate('window.__atlas.clickMap([1500.25,2400.8])')
        self.assertTrue(self.page.locator('#location-editor').is_visible())
        self.assertFalse(self.page.locator('#map-task').is_visible())
        self.assertFalse(self.page.evaluate('window.__atlas.interacting'))
        self.assertEqual(self.page.locator('#location-x').input_value(), '1500')
        self.assertEqual(self.page.locator('#location-y').input_value(), '2401')
        self.assertEqual(self.page.locator('#location-confidence').input_value(), 'custom')
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.page.locator('#location-name').fill('  Речной двор  ')
        self.page.locator('#location-type').select_option('estate')
        self.page.locator('#location-faction').select_option('vassal')
        self.page.locator('#location-owner').fill('')
        self.page.locator('#location-form button[type=submit]').click()
        result = self.data()
        self.assertEqual(result['locations'][:-1], before['locations'])
        self.assertEqual(result['factions'], before['factions'])
        location = result['locations'][-1]
        self.assertTrue(location['id'].startswith('location-'))
        self.assertEqual(location['name'], '  Речной двор  ')
        self.assertEqual(location['x'], 1500)
        self.assertEqual(location['y'], 2401)
        self.assertEqual(location['objects'], [])
        self.assertEqual(location['owner'], '')
        self.assertEqual(location['faction'], 'vassal')
        self.assertEqual(location['provenance']['confidence'], 'custom')
        self.assertEqual(self.page.evaluate('window.__atlas.selected'), location['id'])
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertEqual(self.page_errors, [])
    def test_move_task_can_cancel_then_updates_coordinates_without_touching_territories(self):
        self.assert_ready()
        self.page.evaluate("""() => {
            const data = structuredClone(window.__atlas.data);
            data.territories = [{id: 'land', name: 'Земля', faction: 'vassal', points: [[1000,2000],[1400,2000],[1200,2400]]}];
            window.__atlas.replace(data);
        }""")
        before = self.data()
        self.page.locator('#editor-open').click()
        self.page.locator('#location-move').click()
        self.assertTrue(self.page.evaluate('window.__atlas.interacting'), 'move starts one map point-picking task')
        self.page.locator('#map-task-cancel').click()
        self.assertFalse(self.page.evaluate('window.__atlas.interacting'))
        self.page.evaluate('window.__atlas.clickMap([2000,3000])')
        self.assertEqual(self.data(), before)
        self.page.locator('#editor-open').click()
        self.page.locator('#location-move').click()
        self.page.keyboard.press('Escape')
        self.assertFalse(self.page.evaluate('window.__atlas.interacting'))
        self.assertFalse(self.page.locator('#map-task').is_visible())
        self.page.locator('#editor-open').click()
        self.page.locator('#location-move').click()
        self.page.evaluate('window.__atlas.clickMap([1800,3100])')
        expected = before
        expected['locations'][0].update(x=1800, y=3100)
        self.assertEqual(self.data(), expected)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertFalse(self.page.evaluate('window.__atlas.interacting'))
        self.assertEqual(self.page_errors, [])
    def test_location_delete_is_confirmation_gated_and_preserves_separate_territories(self):
        self.assert_ready()
        before = self.data()
        self.page.locator('#editor-open').click()
        self.page.evaluate('window.__atlas.confirmation = false')
        self.page.locator('#location-delete').click()
        self.page.wait_for_timeout(30)
        self.assertEqual(self.data(), before)
        self.page.evaluate('window.__atlas.confirmation = true')
        self.page.locator('#location-delete').click()
        self.page.wait_for_timeout(30)
        self.assertEqual([record['id'] for record in self.data()['locations']], ['port'], 'confirmed delete removes only the selected dossier')
        self.assertIsNone(self.page.evaluate('window.__atlas.selected'))
        expected = before
        expected['locations'] = expected['locations'][1:]
        self.assertEqual(self.data(), expected)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertEqual(self.page_errors, [])
    def test_house_create_saves_vassal_parent_color_ruler_and_safe_registry_text(self):
        self.assert_ready()
        before = self.data()
        self.assertEqual(self.page.evaluate('typeof window.__atlas.editor.openHouses'), 'function', 'houses need a real registry editor')
        self.page.evaluate('window.__atlas.editor.openHouses()')
        self.assertTrue(self.page.locator('#houses-editor').is_visible())
        self.assertEqual(self.page.locator('.house-entry').count(), 3)
        self.page.locator('#house-name').fill('  Дом <img src=x onerror="window.bad=1">  ')
        self.page.locator('#house-parent').select_option('crown')
        self.page.locator('#house-color').fill('#33aa77')
        self.page.locator('#house-ruler').fill('  Леди  ')
        self.page.locator('#house-description').fill('  История дома  ')
        self.page.locator('#house-form button[type=submit]').click()
        after = self.data()
        self.assertEqual(after['factions'][:-1], before['factions'])
        faction = after['factions'][-1]
        self.assertTrue(faction['id'].startswith('house-'))
        self.assertEqual(faction['name'], '  Дом <img src=x onerror="window.bad=1">  ')
        self.assertEqual(faction['parent'], 'crown')
        self.assertEqual(faction['color'], '#33aa77')
        self.assertEqual(faction['ruler'], '  Леди  ')
        self.assertEqual(faction['description'], '  История дома  ')
        self.assertEqual(after['locations'], before['locations'])
        row = self.page.locator(f'[data-house-id="{faction["id"]}"]')
        self.assertIn('<img src=x onerror="window.bad=1">', row.inner_text())
        self.assertIn('Корона', row.inner_text())
        self.assertEqual(row.locator('img').count(), 0)
        swatch = row.locator('.house-swatch').bounding_box()
        self.assertGreaterEqual(swatch['width'], 12, 'registry exposes a visible heraldic color swatch')
        self.assertGreaterEqual(swatch['height'], 12)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertIsNone(self.page.evaluate('window.bad'))
        self.assertEqual(self.page_errors, [])
    def test_house_edit_excludes_descendants_rejects_stale_cycle_and_keeps_color(self):
        self.assert_ready()
        before = self.data()
        self.page.evaluate('window.__atlas.editor.openHouses()')
        self.assertEqual(self.page.locator('[data-house-id="crown"] [data-house-edit]').count(), 1, 'registry houses have edit actions')
        self.page.locator('[data-house-id="crown"] [data-house-edit]').click()
        self.assertEqual(self.page.locator('#house-id').input_value(), 'crown')
        self.assertEqual(self.page.locator('#house-parent option[value="crown"]').count(), 0)
        self.assertEqual(self.page.locator('#house-parent option[value="vassal"]').count(), 0)
        # A registry can change while the form is open. Revalidate against latest data.
        self.page.evaluate("document.querySelector('#house-parent').add(new Option('Недопустимый потомок', 'vassal'))")
        self.page.locator('#house-parent').select_option('vassal')
        self.page.locator('#house-form button[type=submit]').click()
        self.assertRegex(self.page.locator('#house-error').inner_text().lower(), 'цикл|сюзерен|родител')
        self.assertEqual(self.data(), before)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.page.locator('#house-parent').select_option('')
        self.page.locator('#house-name').fill('Новая корона')
        self.page.locator('#house-color').fill('#aa4455')
        self.page.locator('#house-form button[type=submit]').click()
        expected = before
        expected['factions'][0].update(name='Новая корона', color='#aa4455', description='')
        self.assertEqual(self.data(), expected)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertEqual(self.page.locator('#house-error').inner_text(), '')
        self.assertEqual(self.page_errors, [])
    def test_house_delete_rejects_references_then_deletes_unused_house(self):
        self.assert_ready()
        before = self.data()
        self.page.evaluate('window.__atlas.editor.openHouses()')
        self.assertEqual(self.page.locator('[data-house-id="vassal"] [data-house-delete]').count(), 1, 'house deletion must be available with reference validation')
        self.page.locator('[data-house-id="vassal"] [data-house-delete]').click()
        self.page.wait_for_timeout(30)
        self.assertEqual(self.data(), before)
        self.assertRegex(self.page.locator('#house-error').inner_text().lower(), 'использ|назнач|переназнач')
        self.assertIn('локац', self.page.locator('#house-error').inner_text().lower())
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.assertTrue(self.page.locator('#houses-editor').is_visible())
        self.page.evaluate('window.__atlas.confirmation = false')
        self.page.locator('[data-house-id="free-house"] [data-house-delete]').click()
        self.page.wait_for_timeout(30)
        self.assertEqual(self.data(), before)
        self.page.evaluate('window.__atlas.confirmation = true')
        self.page.locator('[data-house-id="free-house"] [data-house-delete]').click()
        self.page.wait_for_timeout(30)
        expected = before
        expected['factions'] = expected['factions'][:2]
        self.assertEqual(self.data(), expected)
        self.assertEqual(self.page.locator('[data-house-id="free-house"]').count(), 0)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertEqual(self.page.locator('#house-error').inner_text(), '')
        self.assertEqual(self.page_errors, [])
    def test_territory_click_drawing_undo_validation_and_atomic_finish(self):
        self.assert_ready()
        before = self.data()
        self.assertEqual(self.page.evaluate('typeof window.__atlas.editor.openTerritories'), 'function', 'territories need a polygon drawing workflow')
        self.page.evaluate('window.__atlas.editor.openTerritories()')
        self.page.locator('#territory-name').fill('  Земли вассала  ')
        self.page.locator('#territory-faction').select_option('vassal')
        self.page.locator('#territory-form button[type=submit]').click()
        self.assertFalse(self.page.locator('#territory-editor').is_visible())
        self.assertTrue(self.page.locator('#territory-actions').is_visible())
        self.assertTrue(self.page.evaluate('window.__atlas.interacting'))
        self.page.evaluate('window.__atlas.clickMap([-1,2000])')
        self.page.evaluate('window.__atlas.canPlace = false')
        self.page.evaluate('window.__atlas.clickMap([1000,2000])')
        self.assertEqual(self.page.locator('#drawing-layer circle').count(), 0)
        self.page.evaluate('window.__atlas.canPlace = true')
        self.page.evaluate('window.__atlas.clickMap([1000,2000])')
        self.page.evaluate('window.__atlas.clickMap([1400,2000])')
        self.assertEqual(self.page.locator('#drawing-layer circle').count(), 2)
        self.assertEqual(self.page.locator('#drawing-layer polyline').get_attribute('points'), '1000,2000 1400,2000')
        self.page.locator('#territory-finish').click()
        self.assertEqual(self.data(), before)
        self.assertTrue(self.page.evaluate('window.__atlas.interacting'))
        self.assertRegex(self.page.locator('#map-task-text').inner_text().lower(), 'три|3')
        self.page.evaluate('window.__atlas.clickMap([1400,2400])')
        self.page.locator('#territory-undo').click()
        self.assertEqual(self.page.locator('#drawing-layer circle').count(), 2)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.page.evaluate('window.__atlas.clickMap([1000,2400])')
        self.page.locator('#territory-finish').click()
        self.page.wait_for_timeout(30)
        result = self.data()
        territory = result['territories'][0]
        self.assertTrue(territory['id'].startswith('territory-'))
        self.assertEqual(territory['name'], '  Земли вассала  ')
        self.assertEqual(territory['faction'], 'vassal')
        self.assertEqual(territory['points'], [[1000,2000],[1400,2000],[1000,2400]])
        self.assertEqual(result['locations'], before['locations'])
        self.assertEqual(result['factions'], before['factions'])
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertFalse(self.page.evaluate('window.__atlas.interacting'))
        self.assertFalse(self.page.locator('#map-task').is_visible())
        self.assertEqual(self.page.locator('#drawing-layer circle').count(), 0)
        self.page.evaluate('window.__atlas.editor.openTerritories()')
        self.assertEqual(self.page.locator(f'[data-territory-id="{territory["id"]}"]').count(), 1)
        self.assertEqual(self.page_errors, [])
    def test_territory_self_intersection_is_rejected_then_double_click_finishes(self):
        self.assert_ready()
        before = self.data()
        self.page.evaluate('window.__atlas.editor.openTerritories()')
        self.page.locator('#territory-name').fill('Спорная земля')
        self.page.locator('#territory-faction').select_option('vassal')
        self.page.locator('#territory-form button[type=submit]').click()
        for point in [[1000,2000],[1400,2400],[1000,2400],[1400,2000]]:
            self.page.evaluate('point => window.__atlas.clickMap(point)', point)
        self.page.locator('#territory-finish').click()
        self.assertEqual(self.data(), before)
        self.assertIn('пересеч', self.page.locator('#map-task-text').inner_text().lower())
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.page.keyboard.press('Escape')
        self.assertFalse(self.page.evaluate('window.__atlas.interacting'))
        self.assertEqual(self.page.locator('#drawing-layer circle').count(), 0)
        self.page.evaluate('window.__atlas.editor.openTerritories()')
        self.page.locator('#territory-name').fill('Чистая граница')
        self.page.locator('#territory-faction').select_option('vassal')
        self.page.locator('#territory-form button[type=submit]').click()
        for point in [[1000,2000],[1400,2000],[1000,2400]]:
            self.page.evaluate('point => window.__atlas.clickMap(point)', point)
        self.page.locator('#viewport').dispatch_event('dblclick', {'clientX': 1000, 'clientY': 2400})
        self.assertEqual(len(self.data()['territories']), 1, 'double-click closes and saves a valid polygon')
        self.assertEqual(self.data()['territories'][0]['points'], [[1000,2000],[1400,2000],[1000,2400]])
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertFalse(self.page.evaluate('window.__atlas.interacting'))
        self.assertEqual(self.page_errors, [])
    def test_territory_inline_name_and_owner_changes_preserve_polygon_and_locations(self):
        self.assert_ready()
        self.page.evaluate("""() => {
            const data = structuredClone(window.__atlas.data);
            data.territories = [{id: 'land', name: 'Земля', faction: 'vassal',
                points: [[1000,2000],[1400,2000],[1200,2400]], note: 'Авторская граница'}];
            window.__atlas.replace(data);
        }""")
        before = self.data()
        self.page.evaluate('window.__atlas.editor.openTerritories()')
        self.assertEqual(self.page.locator('[data-territory-id="land"] [data-territory-name]').count(), 1, 'territory names are editable without browser prompts')
        self.page.locator('[data-territory-name]').fill('  Переправа <script>bad()</script>  ')
        self.page.locator('[data-territory-name]').press('Tab')
        self.page.locator('[data-territory-owner]').select_option('crown')
        expected = before
        expected['territories'][0].update(name='  Переправа <script>bad()</script>  ', faction='crown')
        self.assertEqual(self.data(), expected)
        self.assertEqual(self.page.locator('[data-territory-name]').input_value(), '  Переправа <script>bad()</script>  ')
        self.assertEqual(self.page.locator('[data-territory-owner]').input_value(), 'crown')
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 2)
        self.assertGreaterEqual(self.page.locator('[data-territory-name]').bounding_box()['height'], 44)
        self.assertGreaterEqual(self.page.locator('[data-territory-owner]').bounding_box()['height'], 44)
        self.assertEqual(self.page_errors, [])
    def test_territory_redraw_cancel_keeps_original_until_valid_replacement(self):
        self.assert_ready()
        self.page.evaluate("""() => {
            const data = structuredClone(window.__atlas.data);
            data.territories = [{id: 'land', name: 'Граница', faction: 'vassal',
                points: [[1000,2000],[1400,2000],[1200,2400]], note: 'Сохранить заметку'}];
            window.__atlas.replace(data);
        }""")
        before = self.data()
        self.page.evaluate('window.__atlas.editor.openTerritories()')
        self.assertEqual(self.page.locator('[data-territory-redraw]').count(), 1, 'redraw starts a deferred replacement, not a delete')
        self.page.locator('[data-territory-redraw]').click()
        self.page.evaluate('window.__atlas.clickMap([1700,2200])')
        self.page.locator('#map-task-cancel').click()
        self.assertEqual(self.data(), before)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.page.evaluate('window.__atlas.editor.openTerritories()')
        self.page.locator('[data-territory-redraw]').click()
        for point in [[1600,2200],[2000,2200],[1800,2600]]:
            self.page.evaluate('point => window.__atlas.clickMap(point)', point)
        self.page.locator('#territory-finish').click()
        expected = before
        expected['territories'][0]['points'] = [[1600,2200],[2000,2200],[1800,2600]]
        self.assertEqual(self.data(), expected)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertFalse(self.page.evaluate('window.__atlas.interacting'))
        self.assertEqual(self.page_errors, [])
    def test_territory_delete_confirmation_removes_only_exact_area(self):
        self.assert_ready()
        self.page.evaluate("""() => {
            const data = structuredClone(window.__atlas.data);
            data.territories = [
                {id: 'land', name: 'Граница', faction: 'vassal', points: [[1000,2000],[1400,2000],[1200,2400]]},
                {id: 'coast', name: 'Побережье', faction: 'crown', points: [[1500,2600],[1900,2600],[1700,3000]]}];
            window.__atlas.replace(data);
        }""")
        before = self.data()
        self.page.evaluate('window.__atlas.editor.openTerritories()')
        self.assertEqual(self.page.locator('[data-territory-id="land"] [data-territory-delete]').count(), 1, 'areas need a confirmation-gated delete control')
        self.page.evaluate('window.__atlas.confirmation = false')
        self.page.locator('[data-territory-id="land"] [data-territory-delete]').click()
        self.page.wait_for_timeout(30)
        self.assertEqual(self.data(), before)
        self.page.evaluate('window.__atlas.confirmation = true')
        self.page.locator('[data-territory-id="land"] [data-territory-delete]').click()
        self.page.wait_for_timeout(30)
        expected = before
        expected['territories'] = expected['territories'][1:]
        self.assertEqual(self.data(), expected)
        self.assertEqual(self.page.locator('[data-territory-id="land"]').count(), 0)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertEqual(self.page_errors, [])
    def test_dashboard_selection_buttons_open_forms_without_stacked_modals(self):
        self.assert_ready()
        self.page.locator('#editor-open').click()
        self.page.locator('#location-edit').click()
        self.assertTrue(self.page.locator('#location-editor').is_visible(), 'selected dossier is editable from the dashboard')
        self.assertEqual(self.page.locator('dialog[open]').count(), 1)
        self.page.locator('[data-close="location-editor"]').click()
        self.assertFalse(self.page.locator('#location-editor').is_visible())
        self.page.locator('#editor-open').click()
        self.page.locator('#object-create').click()
        self.assertTrue(self.page.locator('#object-editor').is_visible())
        self.assertEqual(self.page.locator('dialog[open]').count(), 1)
        self.page.locator('[data-close="object-editor"]').click()
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.page.locator('#editor-open').click()
        self.page.locator('#houses-open').click()
        self.assertTrue(self.page.locator('#houses-editor').is_visible())
        self.page.locator('[data-close="houses-editor"]').click()
        self.assertFalse(self.page.locator('#houses-editor').is_visible())
        self.page.locator('#editor-open').click()
        self.page.locator('#territories-open').click()
        self.assertTrue(self.page.locator('#territory-editor').is_visible())
        self.page.locator('[data-close="territory-editor"]').click()
        self.assertFalse(self.page.locator('#territory-editor').is_visible())
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.assertEqual(self.page_errors, [])
    def test_export_import_and_reset_delegate_to_parent_without_duplicate_confirmation(self):
        self.assert_ready()
        before = self.data()
        self.page.locator('#editor-open').click()
        self.page.locator('#export-site').click()
        self.page.locator('#export-json').click()
        self.page.locator('#import-json').set_input_files({'name': 'archive.json', 'mimeType': 'application/json', 'buffer': b'{"version":1}'})
        self.page.wait_for_timeout(30)
        actions = self.page.evaluate("window.__atlas.events.filter(e => ['site','json','import'].includes(e[0]))")
        self.assertEqual(actions, [['site'], ['json'], ['import', 'archive.json']], 'all persistence controls must call the parent single-path handlers')
        self.assertEqual(self.page.locator('#import-json').input_value(), '')
        # onReset owns its confirmation; editor must not add another.
        self.page.evaluate('window.__atlas.confirmation = false')
        self.page.locator('#draft-reset').click()
        self.page.wait_for_timeout(30)
        self.assertEqual(self.page.evaluate("window.__atlas.events.filter(e => e[0] === 'reset')"), [['reset']])
        self.assertEqual(self.page.evaluate("window.__atlas.events.filter(e => e[0] === 'confirm')"), [])
        self.assertEqual(self.data(), before, 'editor does not independently replace or write drafts')
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.assertEqual(self.page.evaluate('localStorage.length'), 0)
        self.assertEqual(self.page_errors, [])


    def test_parent_action_error_reopens_accessible_dashboard_without_html_injection(self):
        self.assert_ready()
        self.page.evaluate('window.__atlas.failParent = true')
        self.page.locator('#editor-open').click()
        self.page.locator('#draft-reset').click()
        self.page.wait_for_timeout(30)
        self.assertTrue(self.page.locator('#editor').is_visible(), 'parent callback failures remain accessible after a replacing confirmation dialog')
        self.assertIn('<script>window.bad=1</script>', self.page.locator('#editor-error').inner_text())
        self.assertEqual(self.page.locator('#editor-error script').count(), 0)
        self.assertFalse(self.page.locator('#draft-reset').is_disabled())
        self.assertIsNone(self.page.evaluate('window.bad'))
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.assertEqual(self.page_errors, [])

    def test_double_click_first_polygon_vertex_closes_without_duplicate_vertex(self):
        self.assert_ready()
        self.page.evaluate('window.__atlas.editor.openTerritories()')
        self.page.locator('#territory-name').fill('Замкнутая область')
        self.page.locator('#territory-faction').select_option('vassal')
        self.page.locator('#territory-form button[type=submit]').click()
        points = [[1000,2000],[1400,2000],[1000,2400]]
        for point in points:
            self.page.evaluate('point => window.__atlas.clickMap(point)', point)
        # The camera emits pointer-up for both clicks before native dblclick.
        self.page.evaluate('window.__atlas.clickMap([1000,2000], {detail:1})')
        self.page.evaluate('window.__atlas.clickMap([1000,2000], {detail:2})')
        self.page.locator('#viewport').dispatch_event('dblclick', {'clientX': 1000, 'clientY': 2000})
        self.assertEqual(len(self.data()['territories']), 1, 'closing at the first vertex does not create an invalid repeated point')
        self.assertEqual(self.data()['territories'][0]['points'], points)
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 1)
        self.assertEqual(self.page_errors, [])

    def test_refresh_tracks_selection_without_overwriting_open_unsaved_form(self):
        self.assert_ready()
        self.assertEqual(self.page.evaluate('typeof window.__atlas.editor.refresh'), 'function', 'parent can refresh dashboard selection after atomic changes')
        self.page.evaluate('window.__atlas.select(null); window.__atlas.editor.refresh()')
        self.assertEqual(self.page.locator('#editor-selection-name').inner_text(), 'Не выбрано')
        self.assertTrue(self.page.locator('#location-edit').is_disabled())
        self.page.evaluate("window.__atlas.select('port'); window.__atlas.editor.refresh()")
        self.assertEqual(self.page.locator('#editor-selection-name').inner_text(), 'Порт')
        self.assertFalse(self.page.locator('#location-edit').is_disabled())
        self.page.evaluate("window.__atlas.editor.editLocation('keep')")
        self.page.locator('#location-name').fill('Не потерять черновик формы')
        self.page.evaluate('window.__atlas.editor.refresh()')
        self.assertEqual(self.page.locator('#location-name').input_value(), 'Не потерять черновик формы')
        self.assertEqual(self.page.evaluate('window.__atlas.commits.length'), 0)
        self.assertEqual(self.page_errors, [])


if __name__ == '__main__':
    unittest.main()
