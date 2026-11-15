"""Wall journal slices against full HTML, real icons/model and frozen author data."""
import copy
import functools
import http.server
import threading
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DRAFT_KEY = 'court-wall-test-draft'
BASELINE = {
    'version': 1,
    'meta': {
        'width': 64, 'height': 64, 'image': 'assets/maps/gilneas-enhanced.webp',
        'wallConstruction': {'value': 10, 'max': 100, 'note': '  Авторский трек  '},
        'authorExtra': {'literal': '  <script>window.bad=1</script>  '},
    },
    'factions': [{'id': 'crown', 'name': 'Тестовая корона', 'parent': None, 'color': '#990000'}],
    'locations': [{'id': 'keep', 'name': 'Тестовый замок', 'x': 20, 'y': 20, 'faction': 'crown',
                   'type': 'fortress', 'description': '  Авторское досье  ', 'objects': []}],
    'territories': [],
    'nobles': [{'id': 'baron', 'name': 'Тестовый барон', 'house': 'crown', 'description': '  Биография  '}],
    'sources': [{'id': 'archive', 'title': 'Тестовый архив', 'url': 'https://example.invalid/archive'}],
    'territoryGrid': {'version': 1, 'width': 2, 'height': 2, 'step': 32, 'mapWidth': 64, 'mapHeight': 64,
                      'keys': ['crown'], 'cells': [1, 0, 0, 1], 'radius': 260, 'manual': True},
    'authorRegistry': [{'literal': '  <img onerror="window.bad=1">  '}],
}

BOOTSTRAP = """async ({baseline, key}) => {
    document.body.classList.add('edit-mode');
    const model = await import('/assets/js/model.mjs');
    const wall = await import('/assets/js/wall-progress.mjs');
    const {decorateIcons} = await import('/assets/js/icons.mjs');
    const {initWallJournal} = await import('/assets/js/wall-journal.mjs');
    const freeze = value => {
        if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
        return value;
    };
    const validate = next => {
        const normalized = model.normalizeData(next);
        const ids = new Set();
        const claim = record => {
            if (ids.has(record.id)) throw new Error(`Повтор ID: ${record.id}`);
            ids.add(record.id);
        };
        [...normalized.factions, ...normalized.locations, ...normalized.territories, ...normalized.nobles, ...normalized.sources].forEach(claim);
        normalized.locations.forEach(record => record.objects.forEach(object => {
            claim(object); object.modifiers.forEach(claim);
        }));
        if (Object.hasOwn(normalized.meta, 'wallConstruction')) wall.validateWallConstruction(normalized.meta.wallConstruction, {
            claim,
            validateSources: record => {
                for (const id of record.sources ?? []) {
                    if (!normalized.sources.some(source => source.id === id)) throw new Error(`Неизвестный источник: ${String(id)}`);
                }
            },
        });
        return normalized;
    };
    const loaded = model.loadDraft(localStorage, baseline, key);
    if (loaded.error) throw loaded.error;
    let data = freeze(validate(loaded.data));
    const commits = [], toasts = [], confirmations = [];
    window.__wall = {
        get data() { return data; }, original: structuredClone(data), commits, toasts, confirmations,
        rejectCommit: false, confirmationResult: true, model, validate,
        replace: next => { data = freeze(validate(next)); window.dispatchEvent(new CustomEvent('gilneas-data-changed')); },
    };
    decorateIcons();
    window.__wall.journal = initWallJournal({
        getData: () => data,
        replaceData: next => {
            if (window.__wall.rejectCommit) throw new Error('Тестовый отказ сохранения');
            const normalized = validate(next);
            model.saveDraft(localStorage, normalized, key);
            data = freeze(normalized);
            commits.push(structuredClone(data));
            window.dispatchEvent(new CustomEvent('gilneas-data-changed'));
        },
        toast: message => toasts.push(message),
        confirm: async (title, message) => {
            confirmations.push([title, message]);
            return window.__wall.confirmationResult;
        },
    });
}"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class CourtWall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
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
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.page = self.context.new_page()
        self.page.set_default_timeout(4000)
        self.page_errors, self.console_errors, self.http_errors = [], [], []
        self.page.on('pageerror', lambda error: self.page_errors.append(str(error)))
        self.page.on('console', lambda message: self.console_errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.http_errors.append([response.status, response.url]) if response.status >= 400 else None)
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(status=200, content_type='text/javascript', body=''))
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/')

    def tearDown(self):
        self.context.close()

    def init_journal(self, baseline=None):
        self.assertTrue((ROOT / 'assets/js/wall-journal.mjs').is_file(), 'initWallJournal UI module is required')
        css = ROOT / 'assets/css/wall-journal.css'
        if css.exists():
            self.page.add_style_tag(path=str(css))
        self.page.evaluate(BOOTSTRAP, {'baseline': baseline or BASELINE, 'key': DRAFT_KEY})

    def data(self):
        return self.page.evaluate('window.__wall.data')

    def saved(self):
        return self.page.evaluate('(key) => localStorage.getItem(key)', DRAFT_KEY)

    def assert_clean(self):
        self.assertEqual(self.page_errors, [])
        self.assertEqual(self.console_errors, [])
        self.assertEqual(self.http_errors, [])
        self.assertIsNone(self.page.evaluate('window.bad'))

    def test_native_header_and_keyboard_open_an_honest_empty_journal(self):
        self.init_journal()
        self.assertIsNone(self.saved(), 'initial rendering must not create a local draft')
        self.assertEqual(self.data()['meta']['wallConstruction'], BASELINE['meta']['wallConstruction'])
        progress = self.page.locator('#wall-progress')
        self.assertEqual(progress.get_attribute('value'), '10')
        self.assertEqual(progress.get_attribute('max'), '100')
        self.assertEqual(progress.get_attribute('aria-valuenow'), '10')
        self.assertEqual(progress.get_attribute('aria-valuemax'), '100')
        self.assertEqual(progress.get_attribute('aria-valuemin'), '0')
        self.assertEqual(self.page.locator('#wall-progress-value').inner_text(), '10 / 100')
        opener = self.page.locator('#wall-history-open')
        opener.click()
        dialog = self.page.locator('#wall-journal')
        self.assertTrue(dialog.is_visible())
        self.assertEqual(dialog.locator('.dialog-head h2').inner_text(), 'Летопись Стены Седогрива')
        self.assertIn('События ещё не добавлены', dialog.inner_text())
        self.assertIn('порядке добавления', dialog.inner_text())
        self.assertEqual(dialog.locator('#wall-event-form').count(), 1)
        self.assertEqual(dialog.locator('#wall-event-id, #wall-event-name, #wall-event-description, #wall-event-delta').count(), 4)
        self.page.locator('[data-close="wall-journal"]').click()
        self.assertFalse(dialog.is_visible())
        opener.focus()
        self.page.keyboard.press('Enter')
        self.assertTrue(dialog.is_visible())
        self.page.keyboard.press('Escape')
        self.assertFalse(dialog.is_visible())
        opener.focus()
        self.page.keyboard.press('Space')
        self.assertTrue(dialog.is_visible())
        self.assertIsNone(self.saved())
        self.assert_clean()

    def test_header_track_is_centered_on_the_entire_underlay_without_overlapping_controls(self):
        self.init_journal()
        for width, height in [(1440, 1000), (1280, 900), (1000, 900), (768, 900), (390, 844), (360, 780), (320, 640), (844, 390)]:
            with self.subTest(viewport=(width, height)):
                self.page.set_viewport_size({'width': width, 'height': height})
                self.page.wait_for_timeout(30)
                geometry = self.page.evaluate("""() => {
                    const box = selector => {
                        const r = document.querySelector(selector).getBoundingClientRect();
                        return {x:r.x, y:r.y, width:r.width, height:r.height, right:r.right, bottom:r.bottom};
                    };
                    return {header:box('.topbar'), brand:box('.brand'), toolbar:box('.toolbar'),
                            track:box('#wall-history-open'), progress:box('#wall-progress'),
                            brandTitle:box('.brand h1'), brandTitleVisible:getComputedStyle(document.querySelector('.brand h1')).display !== 'none',
                            buttons:[...document.querySelectorAll('.toolbar > button')].map(button => {
                                const r = button.getBoundingClientRect();
                                return {x:r.x, y:r.y, width:r.width, height:r.height, right:r.right, bottom:r.bottom};
                            }), scrollWidth:document.documentElement.scrollWidth};
                }""")
                header = geometry['header']
                for key in ['track', 'progress']:
                    rect = geometry[key]
                    self.assertAlmostEqual(rect['x'] + rect['width'] / 2, header['x'] + header['width'] / 2, delta=1, msg=geometry)
                    self.assertGreater(rect['width'], 180)
                    self.assertLessEqual(rect['bottom'], header['bottom'] + 1)
                self.assertEqual(len(geometry['buttons']), 5)
                self.assertLessEqual(geometry['scrollWidth'], width)
                rects = [geometry['brand'], geometry['track'], *geometry['buttons']]
                if geometry['brandTitleVisible']:
                    self.assertLessEqual(geometry['brandTitle']['right'], geometry['toolbar']['x'], geometry)
                for index, rect in enumerate(rects):
                    self.assertGreaterEqual(rect['x'], header['x'] - 1, geometry)
                    self.assertLessEqual(rect['right'], header['right'] + 1, geometry)
                    for other in rects[index + 1:]:
                        overlap_x = min(rect['right'], other['right']) - max(rect['x'], other['x'])
                        overlap_y = min(rect['bottom'], other['bottom']) - max(rect['y'], other['y'])
                        self.assertFalse(overlap_x > 1 and overlap_y > 1, geometry)
                for button in geometry['buttons']:
                    self.assertEqual(button['height'], 44, geometry)
                    self.assertGreaterEqual(button['width'], 44)
                    self.assertAlmostEqual(button['height'], geometry['buttons'][2]['height'], delta=0.01, msg='Editor and all toolbar peers must have the same height')
        self.assert_clean()

    def add_event(self, name, delta, description=''):
        self.assertEqual(self.page.locator('#wall-event-form button[type="submit"]').count(), 1, 'wall form needs a native save button')
        self.page.locator('#wall-event-name').fill(name)
        self.page.locator('#wall-event-description').fill(description)
        self.page.locator('#wall-event-delta').fill(str(delta))
        self.page.locator('#wall-event-form button[type="submit"]').click()

    def test_add_signed_events_atomically_and_reload_from_the_author_current_base(self):
        baseline = copy.deepcopy(BASELINE)
        baseline['meta']['wallConstruction']['value'] = 43
        self.init_journal(baseline)
        original = self.page.evaluate('window.__wall.original')
        self.page.locator('#wall-history-open').click()
        self.add_event('  Поставка камня  ', 15, '  <script>window.bad=1</script>  ')
        track = self.data()['meta']['wallConstruction']
        self.assertEqual(track['baseValue'], 43)
        self.assertEqual(track['value'], 58)
        self.assertEqual(track['events'][0]['name'], '  Поставка камня  ')
        self.assertEqual(track['events'][0]['description'], '  <script>window.bad=1</script>  ')
        first_id = track['events'][0]['id']
        self.assertTrue(first_id)
        self.assertEqual(self.page.locator('#wall-progress-value').inner_text(), '58 / 100')
        self.assertIn('+15', self.page.locator('#wall-event-history').inner_text())
        self.assertIn('43 → 58', self.page.locator('#wall-event-history').inner_text())
        self.assertEqual(self.page.locator('#wall-event-history script').count(), 0)
        self.add_event('Шторм', -20, 'Потери строительного материала')
        track = self.data()['meta']['wallConstruction']
        self.assertEqual(track['baseValue'], 43)
        self.assertEqual(track['value'], 38)
        self.assertEqual(len(track['events']), 2)
        self.assertNotEqual(track['events'][0]['id'], track['events'][1]['id'])
        self.assertEqual(self.page.locator('#wall-progress').get_attribute('aria-valuenow'), '38')
        self.assertIn('58 → 38', self.page.locator('#wall-event-history').inner_text())
        self.assertIn('−20', self.page.locator('#wall-event-history').inner_text())
        current = self.data()
        current['meta']['wallConstruction'] = original['meta']['wallConstruction']
        self.assertEqual(current, original, 'event edits must preserve the full unrelated snapshot and manual zero cells')
        self.assertEqual(self.page.evaluate('window.__wall.commits.length'), 2)
        saved = self.saved()
        self.assertIsNotNone(saved)
        self.page.reload()
        self.init_journal(baseline)
        self.assertEqual(self.saved(), saved, 'reload must not rewrite the saved draft')
        self.assertEqual(self.page.locator('#wall-progress-value').inner_text(), '38 / 100')
        self.assertEqual(self.data()['meta']['wallConstruction']['events'][0]['id'], first_id)
        self.page.locator('#wall-history-open').click()
        self.assertEqual(self.page.locator('[data-wall-event-id]').count(), 2)
        self.assert_clean()

    def test_edit_and_confirmed_delete_recalculate_following_cards_with_exact_ids(self):
        self.init_journal()
        self.page.locator('#wall-history-open').click()
        self.add_event('Поставка', 15, '  Оставить описание  ')
        self.add_event('Шторм', -20)
        track = self.data()['meta']['wallConstruction']
        first_id, second_id = [record['id'] for record in track['events']]
        edit_button = self.page.locator('[data-wall-event-edit]').filter(has_text='Редактировать').first
        self.assertEqual(self.page.locator('[data-wall-event-edit]').count(), 2, 'each exact event needs an edit button')
        self.assertEqual(edit_button.get_attribute('data-wall-event-edit'), first_id)
        edit_button.click()
        self.assertEqual(self.page.locator('#wall-event-id').input_value(), first_id)
        self.assertEqual(self.page.locator('#wall-event-name').input_value(), 'Поставка')
        self.assertEqual(self.page.locator('#wall-event-description').input_value(), '  Оставить описание  ')
        self.page.locator('#wall-event-name').fill('Усиленная поставка')
        self.page.locator('#wall-event-delta').fill('30')
        self.page.locator('#wall-event-form button[type="submit"]').click()
        track = self.data()['meta']['wallConstruction']
        self.assertEqual([record['id'] for record in track['events']], [first_id, second_id])
        self.assertEqual(track['value'], 20)
        self.assertEqual(self.page.locator('#wall-progress-value').inner_text(), '20 / 100')
        self.assertIn('10 → 40', self.page.locator('#wall-event-history').inner_text())
        self.assertIn('40 → 20', self.page.locator('#wall-event-history').inner_text())
        saved = self.saved()
        self.page.evaluate('window.__wall.confirmationResult = false')
        delete_button = self.page.locator('[data-wall-event-delete]').first
        self.assertEqual(delete_button.get_attribute('data-wall-event-delete'), first_id)
        delete_button.click()
        self.assertEqual(self.saved(), saved)
        self.assertEqual(self.data()['meta']['wallConstruction'], track)
        self.page.evaluate('window.__wall.confirmationResult = true')
        delete_button.click()
        track = self.data()['meta']['wallConstruction']
        self.assertEqual(track['value'], 0)
        self.assertEqual(track['baseValue'], 10)
        self.assertEqual([record['id'] for record in track['events']], [second_id])
        self.assertIn('10 → 0', self.page.locator('#wall-event-history').inner_text())
        self.page.locator('[data-wall-event-delete]').click()
        self.assertEqual(self.data()['meta']['wallConstruction']['value'], 10)
        self.assertEqual(self.data()['meta']['wallConstruction']['events'], [])
        self.assertIn('События ещё не добавлены', self.page.locator('#wall-event-history').inner_text())
        self.assertEqual(self.page.evaluate('window.__wall.confirmations.length'), 3)
        self.assert_clean()

    def test_invalid_forms_and_parent_commit_errors_leave_live_and_exact_saved_json_unchanged(self):
        self.init_journal()
        self.page.locator('#wall-history-open').click()
        self.add_event('Сохранённая запись', 15)
        original, saved = self.data(), self.saved()
        for name, delta, expected in [('Ошибка', '1.5', 'целое'), ('  ', '15', 'название'),
                                      ('Ошибка', '', 'Укажите'), ('Ошибка', '1000001', 'целое'), ('Ошибка', '-1000001', 'целое')]:
            with self.subTest(name=name, delta=delta):
                self.page.locator('#wall-event-name').fill(name)
                self.page.locator('#wall-event-delta').fill(delta)
                self.page.locator('#wall-event-form button[type="submit"]').click()
                self.assertIn(expected, self.page.locator('#wall-event-error').inner_text(), 'validation belongs in the journal error field')
                self.assertEqual(self.data(), original)
                self.assertEqual(self.saved(), saved)
        self.page.locator('#wall-event-name').fill('Новая запись')
        self.page.locator('#wall-event-delta').fill('20')
        self.page.evaluate('window.__wall.rejectCommit = true')
        self.page.locator('#wall-event-form button[type="submit"]').click()
        self.assertIn('Тестовый отказ сохранения', self.page.locator('#wall-event-error').inner_text())
        self.assertEqual(self.data(), original)
        self.assertEqual(self.saved(), saved)
        self.assertEqual(self.page.locator('#wall-event-name').input_value(), 'Новая запись', 'failed commits must retain the author draft')
        self.page.evaluate('window.__wall.rejectCommit = false')
        self.page.locator('#wall-event-form button[type="submit"]').click()
        self.assertEqual(self.data()['meta']['wallConstruction']['value'], 45)
        self.assertEqual(self.page.locator('#wall-event-error').inner_text(), '')
        self.assert_clean()

    def test_effects_are_editable_literal_records_with_separate_bonus_and_penalty_colors(self):
        self.init_journal()
        self.page.locator('#wall-history-open').click()
        self.assertEqual(self.page.locator('#wall-effect-bonus-add, #wall-effect-penalty-add').count(), 2, 'wall events need separate bonus/penalty controls')
        self.page.locator('#wall-effect-bonus-add').click()
        bonus_text = '  <b>Крепкий камень</b>  '
        self.page.locator('#wall-effect-list textarea').last.fill(bonus_text)
        self.page.locator('#wall-effect-penalty-add').click()
        penalty_text = '  <img onerror="window.bad=1">  '
        self.page.locator('#wall-effect-list textarea').last.fill(penalty_text)
        self.add_event('Справка об условиях', 0, 'Эффекты без изменения прогресса')
        event = self.data()['meta']['wallConstruction']['events'][0]
        self.assertEqual(event['delta'], 0)
        self.assertEqual(self.data()['meta']['wallConstruction']['value'], 10)
        self.assertEqual([effect['kind'] for effect in event['effects']], ['bonus', 'penalty'])
        self.assertEqual([effect['text'] for effect in event['effects']], [bonus_text, penalty_text])
        self.assertEqual(len({event['id'], *[effect['id'] for effect in event['effects']]}), 3)
        self.assertEqual(self.page.locator('#wall-event-history img, #wall-event-history b').count(), 0)
        self.assertEqual(self.page.locator('.wall-event-effect').count(), 2)
        colors = self.page.locator('.wall-event-effect').evaluate_all('nodes => nodes.map(node => getComputedStyle(node).color)')
        self.assertNotEqual(colors[0], colors[1])
        ids = [effect['id'] for effect in event['effects']]
        self.page.locator('[data-wall-event-edit]').click()
        self.assertEqual(self.page.locator('#wall-effect-list textarea').count(), 2)
        self.assertEqual(self.page.locator('#wall-effect-list textarea').first.input_value(), bonus_text)
        self.page.locator('#wall-effect-list textarea').first.fill('  Изменённый бонус  ')
        self.page.locator('#wall-event-form button[type="submit"]').click()
        event = self.data()['meta']['wallConstruction']['events'][0]
        self.assertEqual([effect['id'] for effect in event['effects']], ids)
        self.assertEqual(event['effects'][0]['text'], '  Изменённый бонус  ')
        self.page.locator('[data-wall-event-edit]').click()
        self.page.locator('[data-wall-effect-remove]').last.click()
        self.page.locator('#wall-event-form button[type="submit"]').click()
        event = self.data()['meta']['wallConstruction']['events'][0]
        self.assertEqual(event['effects'], [{'id': ids[0], 'kind': 'bonus', 'text': '  Изменённый бонус  '}])
        self.assert_clean()

    def test_clipped_events_keep_the_requested_delta_and_show_the_effective_step(self):
        self.init_journal()
        self.page.locator('#wall-history-open').click()
        self.add_event('Избыток материалов', 500)
        card = self.page.locator('.wall-event-card').first
        self.assertIn('+500', card.inner_text())
        self.assertIn('10 → 100', card.inner_text())
        self.assertIn('Фактически: +90', card.inner_text(), 'clamping must not hide the requested delta')
        self.add_event('Утрата всего запаса', -200)
        card = self.page.locator('.wall-event-card').last
        self.assertIn('−200', card.inner_text())
        self.assertIn('100 → 0', card.inner_text())
        self.assertIn('Фактически: −100', card.inner_text())
        self.assertEqual(self.data()['meta']['wallConstruction']['value'], 0)
        self.add_event('Пополнение', 15)
        self.add_event('Часть материалов потеряна', -20)
        card = self.page.locator('.wall-event-card').last
        self.assertIn('15 → 0', card.inner_text())
        self.assertIn('Фактически: −15', card.inner_text())
        self.assertEqual(self.page.locator('#wall-progress').get_attribute('aria-valuenow'), '0')
        self.assert_clean()

    def test_closing_discards_drafts_without_queued_close_erasing_a_reopened_editor(self):
        self.init_journal()
        self.page.locator('#wall-history-open').click()
        self.page.locator('#wall-event-name').fill('Несохранённое событие')
        self.page.locator('#wall-event-delta').fill('15')
        self.page.locator('#wall-effect-bonus-add').click()
        self.page.locator('#wall-effect-list textarea').fill('Несохранённый бонус')
        self.page.locator('[data-close="wall-journal"]').click()
        self.page.locator('#wall-history-open').click()
        self.assertEqual(self.page.locator('#wall-event-name').input_value(), '', 'closing must discard unsaved author text')
        self.assertEqual(self.page.locator('#wall-event-id').input_value(), '')
        self.assertEqual(self.page.locator('#wall-effect-list textarea').count(), 0)
        self.assertIsNone(self.saved())
        self.add_event('Сохранённая запись', 15)
        saved = self.saved()
        event_id = self.data()['meta']['wallConstruction']['events'][0]['id']
        self.page.evaluate("""() => {
            const dialog = document.getElementById('wall-journal');
            dialog.close();
            window.__wall.journal.open();
            document.querySelector('[data-wall-event-edit]').click();
            document.getElementById('wall-event-name').value = 'Быстро открытая правка';
        }""")
        self.page.wait_for_timeout(40)
        self.assertEqual(self.page.locator('#wall-event-id').input_value(), event_id)
        self.assertEqual(self.page.locator('#wall-event-name').input_value(), 'Быстро открытая правка')
        self.page.locator('#wall-event-form button[type="submit"]').click()
        self.assertEqual(self.data()['meta']['wallConstruction']['events'][0]['name'], 'Быстро открытая правка')
        self.assertNotEqual(self.saved(), saved)
        self.page.locator('[data-wall-event-edit]').click()
        self.page.locator('#wall-event-name').fill('Не сохранять Escape')
        self.page.keyboard.press('Escape')
        self.page.locator('#wall-history-open').click()
        self.assertEqual(self.page.locator('#wall-event-id').input_value(), '')
        self.assertEqual(self.page.locator('#wall-event-name').input_value(), '')
        self.assert_clean()

    def test_missing_legacy_track_renders_without_writing_or_throwing_after_import(self):
        self.init_journal()
        minimal = copy.deepcopy(BASELINE)
        del minimal['meta']['wallConstruction']
        result = self.page.evaluate("""next => {
            try { window.__wall.replace(next); return null; }
            catch (error) { return error.message; }
        }""", minimal)
        self.assertIsNone(result, 'rendering an absent optional track must not throw after snapshot replacement')
        self.assertFalse('wallConstruction' in self.data()['meta'])
        self.assertIsNone(self.saved(), 'view-only fallback must not invent progress in storage')
        self.page.locator('#wall-history-open').click()
        self.assertIn('не задана', self.page.locator('#wall-journal-summary').inner_text())
        self.assertTrue(self.page.locator('#wall-event-form button[type="submit"]').is_disabled())
        self.assertFalse('wallConstruction' in self.data()['meta'])
        self.assert_clean()

    def test_dialog_uses_a_scrollable_responsive_window_and_44px_controls(self):
        self.init_journal()
        for width, height in [(1440, 1000), (1000, 900), (390, 844), (844, 390)]:
            with self.subTest(viewport=(width, height)):
                self.page.evaluate("document.getElementById('wall-journal').close()")
                self.page.set_viewport_size({'width': width, 'height': height})
                self.page.locator('#wall-history-open').click()
                self.assertEqual(self.page.locator('#wall-journal').get_attribute('open'), '')
                metrics = self.page.evaluate("""() => {
                    const dialog = document.getElementById('wall-journal');
                    const rect = dialog.getBoundingClientRect();
                    const head = dialog.querySelector('.dialog-head').getBoundingClientRect();
                    const form = document.getElementById('wall-event-form');
                    return {x:rect.x, y:rect.y, right:rect.right, bottom:rect.bottom, width:rect.width, height:rect.height,
                            scrollWidth:dialog.scrollWidth, clientWidth:dialog.clientWidth, headY:head.y,
                            display:getComputedStyle(form).display,
                            buttons:[...dialog.querySelectorAll('button')].map(button => button.getBoundingClientRect().height)};
                }""")
                self.assertEqual(metrics['display'], 'grid', 'wall editor fields need their own consistent vertical layout')
                self.assertGreaterEqual(metrics['x'], 0)
                self.assertLessEqual(metrics['right'], width)
                self.assertGreaterEqual(metrics['y'], 0)
                self.assertLessEqual(metrics['bottom'], height)
                self.assertLessEqual(metrics['scrollWidth'], metrics['clientWidth'])
                self.assertTrue(all(button >= 44 for button in metrics['buttons']), metrics)
                if width == 844 and height == 390:
                    dialog_box = self.page.locator('#wall-journal').bounding_box()
                    self.page.mouse.move(dialog_box['x'] + dialog_box['width'] / 2, dialog_box['y'] + dialog_box['height'] / 2)
                    self.page.mouse.wheel(0, 1500)
                    self.page.wait_for_function("document.getElementById('wall-journal').scrollTop > 0")
                    head_y = self.page.locator('#wall-journal .dialog-head').bounding_box()['y']
                    self.assertAlmostEqual(head_y, metrics['headY'], delta=1)
                    self.page.locator('#wall-event-name').fill('Мобильная запись')
                    self.page.locator('#wall-event-delta').fill('0')
                    self.page.locator('#wall-event-form button[type="submit"]').click()
                    self.assertEqual(self.data()['meta']['wallConstruction']['events'][0]['name'], 'Мобильная запись')
                self.page.locator('[data-close="wall-journal"]').click()
        self.assert_clean()

    def test_parent_model_rejects_invalid_event_sources_and_global_effect_ids_before_save(self):
        self.init_journal()
        self.page.locator('#wall-history-open').click()
        self.add_event('Сохранённая запись', 0)
        original, saved = self.data(), self.saved()
        invalid = []
        duplicate = copy.deepcopy(original)
        duplicate['meta']['wallConstruction']['events'][0]['effects'] = [{'id': 'crown', 'kind': 'bonus', 'text': 'Повтор'}]
        invalid.append((duplicate, 'Повтор ID'))
        unknown = copy.deepcopy(original)
        unknown['meta']['wallConstruction']['events'][0]['sources'] = ['missing-archive']
        invalid.append((unknown, 'Неизвестный источник'))
        effect_source = copy.deepcopy(original)
        effect_source['meta']['wallConstruction']['events'][0]['effects'] = [{'id': 'new-effect', 'kind': 'penalty', 'text': 'Штраф', 'sources': ['missing-archive']}]
        invalid.append((effect_source, 'Неизвестный источник'))
        cached = copy.deepcopy(original)
        cached['meta']['wallConstruction']['value'] = 42
        invalid.append((cached, 'value'))
        for incoming, expected in invalid:
            with self.subTest(error=expected):
                message = self.page.evaluate("""({incoming, key}) => {
                    try { window.__wall.model.saveDraft(localStorage, incoming, key); return null; }
                    catch (error) { return error.message; }
                }""", {'incoming': incoming, 'key': DRAFT_KEY})
                self.assertIsNotNone(message)
                self.assertIn(expected, message)
                self.assertEqual(self.saved(), saved)
                self.assertEqual(self.data(), original)
        self.assert_clean()

    def test_edits_preserve_source_refs_and_literal_event_effect_extensions(self):
        baseline = copy.deepcopy(BASELINE)
        baseline['meta']['wallConstruction'].update({
            'baseValue': 10, 'value': 25,
            'events': [{'id': 'literal-event', 'name': '  <script>window.bad=1</script>  ', 'description': '  Источник  ',
                        'delta': 15, 'sources': ['archive'], 'authorExtra': {'notes': '  Не переписывать  '},
                        'effects': [{'id': 'literal-effect', 'kind': 'bonus', 'text': '  <img onerror="window.bad=1">  ',
                                     'sources': ['archive'], 'authorExtra': {'weight': 7}}]}],
        })
        self.init_journal(baseline)
        self.page.locator('#wall-history-open').click()
        self.page.locator('[data-wall-event-edit]').click()
        self.page.locator('#wall-event-delta').fill('20')
        self.page.locator('#wall-event-form button[type="submit"]').click()
        expected = copy.deepcopy(baseline['meta']['wallConstruction']['events'][0])
        expected['delta'] = 20
        self.assertEqual(self.data()['meta']['wallConstruction']['events'][0], expected)
        self.assertEqual(self.data()['meta']['wallConstruction']['value'], 30)
        self.assertEqual(self.page.locator('#wall-event-history script, #wall-event-history img').count(), 0)
        self.assert_clean()


if __name__ == '__main__':
    unittest.main()
