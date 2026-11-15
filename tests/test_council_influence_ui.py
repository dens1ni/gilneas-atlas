"""Royal Council influence UI: native vertical slices, real model and CSS.

Run: /Users/daniil_si/.hermes/cache/scratch/gilneas-venv/bin/python \
    tests/test_council_influence_ui.py -v
Only the parent bootstrap is replaced; test-only records stay out of data files.
"""
import copy
import functools
import json
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-council-influence-evidence')
DRAFT_KEY = 'gilneas-council-influence-test-draft'


def member(member_id, party='neutral', kind='person', active=True, **patch):
    record = dict(id=member_id, kind=kind, party=party, stance='unknown',
                  advisor=False, active=active, note='', sources=[17],
                  authorExtra={'literal': '  Keep exact  ', 'flag': False})
    if kind == 'person':
        record.update(name='Тестовый участник ' + member_id, title='')
    else:
        record['refId'] = 'test-house-' + member_id
    record.update(patch)
    return record


def snapshot():
    records = [
        member('royal-person-b', 'royalists'),
        member('intl-house', 'internationalists', 'faction'),
        member('neutral-person', 'neutral'),
        member('royal-house', 'royalists', 'faction'),
        member('royal-person-a', 'royalists'),
        member('intl-person', 'internationalists'),
        member('neutral-house', 'neutral', 'faction'),
        member('old-royal-person-b', 'royalists', active=False),
        member('old-intl-house', 'internationalists', 'faction', active=False),
        member('old-neutral-person', 'neutral', active=False),
        member('old-royal-house', 'royalists', 'faction', active=False),
        member('old-royal-person-a', 'royalists', active=False),
    ]
    return {
        'version': 1,
        'meta': {'width': 3526, 'height': 4548, 'image': 'assets/maps/gilneas-enhanced.webp',
                 'authorExtra': {'literal': '  <script>window.bad=1</script>  '}},
        'factions': [
            {'id': 'test-crown', 'name': 'Тестовая корона', 'color': '#777777', 'parent': None},
            *[{'id': record['refId'], 'name': 'Тестовый дом ' + record['id'],
               'color': '#557777', 'parent': 'test-crown'}
              for record in records if record['kind'] == 'faction'],
        ],
        'locations': [], 'territories': [],
        'nobles': [{'id': 'test-noble', 'name': 'Тестовый реестровый персонаж', 'title': '  Роль автора  ',
                    'house': 'test-crown', 'description': '  Не менять  '}],
        'sources': [{'id': 17, 'title': 'Тестовый архив', 'url': 'https://example.invalid/archive'}],
        'royalCouncil': {'version': 1, 'members': records,
                         'authorExtra': {'literal': '  Council metadata  ', 'flag': False}},
        'authorRegistry': [{'literal': '  Full unrelated snapshot  '}],
    }


BOOTSTRAP = """async ({baseline, key, reload}) => {
    const model = await import('/assets/js/model.mjs');
    const engine = await import('/assets/js/royal-council.mjs');
    const {initRoyalCouncilWindow} = await import('/assets/js/council-window.mjs');
    const {decorateIcons} = await import('/assets/js/icons.mjs');
    // Match the parent edit-mode gate explicitly; fixture controls remain native.
    document.body.classList.add('edit-mode');
    const freeze = value => {
        if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
        return value;
    };
    const validate = incoming => {
        engine.validateRoyalCouncil(incoming.royalCouncil, incoming);
        return model.normalizeData(incoming);
    };
    let data = freeze(validate(reload ? JSON.parse(localStorage.getItem(key)) : baseline));
    const commits = [], toasts = [], storageWrites = [];
    for (const method of ['setItem', 'removeItem', 'clear']) {
        const original = Storage.prototype[method];
        Storage.prototype[method] = function (...args) {
            storageWrites.push({method, args}); return original.apply(this, args);
        };
    }
    window.__council = {
        model, engine, key, commits, toasts, storageWrites, original: structuredClone(data),
        get data() { return data; }, rejectCommit: false, confirmValue: true, editingEnabled: true,
        replace: incoming => { data = freeze(validate(incoming)); window.dispatchEvent(new CustomEvent('gilneas-data-changed')); },
        commit: incoming => {
            const next = validate(incoming);
            if (window.__council.rejectCommit) throw Error('Тест: запись отклонена до сохранения');
            model.saveDraft(localStorage, next, key);
            data = freeze(next); commits.push(structuredClone(next));
            window.dispatchEvent(new CustomEvent('gilneas-data-changed'));
        },
    };
    document.querySelector('#base-map').src = data.meta.image;
    window.__council.ui = initRoyalCouncilWindow({
        getData: () => data, replaceData: window.__council.commit,
        isEditingEnabled: () => window.__council.editingEnabled,
        toast: message => toasts.push(message),
        confirm: async () => window.__council.confirmValue,
    });
    decorateIcons();
}"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class CouncilInfluenceUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
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
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        self.page = self.context.new_page()
        self.page.set_default_timeout(5000)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(
            status=200, content_type='application/javascript', body='// Only parent bootstrap isolated.'))

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [], 'real browser must have no page, console or HTTP errors')
            self.assertIsNone(self.page.evaluate('window.bad'))
        finally:
            self.context.close()

    def boot(self, baseline=None, reload=False):
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/index.html', wait_until='networkidle')
        self.page.evaluate(BOOTSTRAP, {'baseline': baseline if baseline is not None else snapshot(),
                                      'key': DRAFT_KEY, 'reload': reload})
        self.page.wait_for_function("document.querySelector('#base-map').complete && document.querySelector('#base-map').naturalWidth>0", polling=50)
        self.page.locator('#council-open').click()
        self.page.mouse.move(2, 2)

    def data(self):
        return self.page.evaluate('window.__council.data')

    def saved(self):
        return self.page.evaluate('key => localStorage.getItem(key)', DRAFT_KEY)

    def assert_no_writes(self, before):
        self.assertEqual(self.data(), before)
        self.assertEqual(self.page.evaluate('window.__council.commits'), [])
        self.assertEqual(self.page.evaluate('window.__council.storageWrites'), [])
        self.assertIsNone(self.saved())

    def row_ids(self, selector):
        return self.page.locator(selector + ' .council-member').evaluate_all('rows => rows.map(row => row.dataset.memberId)')

    def test_filters_combine_party_kind_for_rosters_history_without_writes_or_lost_draft(self):
        self.boot()
        before = self.data()
        for selector, values in [('#council-filter-party', ['all', 'royalists', 'internationalists', 'neutral']),
                                 ('#council-filter-kind', ['all', 'person', 'faction'])]:
            self.assertEqual(self.page.locator(selector).count(), 1, 'Council needs its native presentation filter')
            self.assertEqual(self.page.locator(selector + ' option').evaluate_all('options => options.map(option => option.value)'), values)
            self.assertEqual(self.page.locator(selector).input_value(), 'all')
            self.assertEqual(self.page.locator(selector).evaluate('e => e.labels.length'), 1)
        self.page.locator('.council-rosters [data-council-edit="royal-person-b"]').click()
        self.page.locator('#council-note').fill('  Несохранённое назначение  ')
        self.page.locator('#council-party').select_option('neutral')
        self.page.locator('label:has(#council-show-history)').click()
        self.page.locator('#council-filter-party').select_option('royalists')
        self.page.locator('#council-filter-kind').select_option('person')
        self.assertEqual(self.row_ids('.council-rosters'), ['royal-person-b', 'royal-person-a'])
        self.assertEqual(self.row_ids('#council-history'), ['old-royal-person-b', 'old-royal-person-a'])
        self.assertEqual(self.page.locator('.council-rosters .council-party:visible').count(), 1)
        self.assertEqual(self.page.locator('.council-house-list:visible').count(), 0)
        self.assertIn('2', self.page.locator('.council-party[data-party="royalists"] > h3').inner_text())
        self.assertIn('2', self.page.locator('.council-person-list > h4:visible').inner_text())
        self.assertIn('2', self.page.locator('#council-history > h3').inner_text())
        self.assertEqual(self.page.locator('#council-form').is_visible(), True)
        self.assertEqual(self.page.locator('#council-note').input_value(), '  Несохранённое назначение  ')
        self.assertEqual(self.page.locator('#council-party').input_value(), 'neutral')
        self.page.locator('#council-filter-kind').select_option('faction')
        self.assertEqual(self.row_ids('.council-rosters'), ['royal-house'])
        self.assertEqual(self.row_ids('#council-history'), ['old-royal-house'])
        self.assertEqual(self.page.locator('.council-person-list:visible').count(), 0)
        self.page.locator('#council-filter-party').select_option('neutral')
        self.page.locator('#council-filter-kind').select_option('person')
        self.assertEqual(self.row_ids('.council-rosters'), ['neutral-person'])
        self.assertEqual(self.row_ids('#council-history'), ['old-neutral-person'])
        self.page.locator('#council-filter-party').select_option('internationalists')
        self.assertEqual(self.row_ids('.council-rosters'), ['intl-person'])
        self.assertEqual(self.row_ids('#council-history'), [])
        self.page.locator('#council-filter-party').select_option('all')
        self.page.locator('#council-filter-kind').select_option('all')
        self.assertEqual(self.page.locator('.council-rosters .council-member').count(), 7)
        self.assertEqual(self.page.locator('#council-history .council-member').count(), 5)
        self.assertEqual(self.page.locator('#council-note').input_value(), '  Несохранённое назначение  ')
        self.assert_no_writes(before)

    def test_party_balance_track_uses_global_pool_shares_including_empty_and_large_values(self):
        baseline = snapshot()
        baseline['royalCouncil']['influence'] = {'royalists': 3, 'internationalists': 1,
                                                 'authorExtra': {'literal': '  Pool metadata  '}}
        self.boot(baseline)
        before = self.data()
        self.assertEqual(self.page.locator('#council-influence').count(), 1, 'Council needs a global party influence track')
        self.assertEqual(self.page.locator('#council-influence-royalists').count(), 1)
        self.assertEqual(self.page.locator('#council-influence-internationalists').count(), 1)
        track = self.page.locator('#council-influence')
        track_text = track.inner_text()
        self.assertIn('Роялисты', track_text)
        self.assertIn('Интернационалисты', track_text)
        self.assertIn('3 очк.', track_text)
        self.assertIn('1 очк.', track_text)
        self.assertIn('75%', track_text)
        self.assertIn('25%', track_text)
        values = self.page.locator('#council-influence-royalists, #council-influence-internationalists').evaluate_all(
            'spans => spans.map(span => ({width:span.style.width, color:getComputedStyle(span).backgroundColor}))')
        self.assertEqual(values, [{'width': '75%', 'color': 'rgb(154, 168, 182)'},
                                  {'width': '25%', 'color': 'rgb(99, 144, 150)'}])
        self.assertTrue(self.page.evaluate("document.querySelector('#council-influence').compareDocumentPosition(document.querySelector('.council-rosters')) & Node.DOCUMENT_POSITION_FOLLOWING"))
        for party in ['royalists', 'internationalists', 'neutral', 'all']:
            self.page.locator('#council-filter-party').select_option(party)
            self.page.locator('#council-filter-kind').select_option('person')
            self.assertEqual(track.inner_text(), track_text, 'global pools do not change with roster filters')
            self.assertEqual(self.page.locator('#council-influence-royalists').evaluate('e => e.style.width'), '75%')
        self.assert_no_writes(before)
        empty = copy.deepcopy(before)
        empty['royalCouncil']['influence'].update(royalists=0, internationalists=0)
        self.page.evaluate('incoming => window.__council.replace(incoming)', empty)
        self.assertIn('нет очков', track.inner_text().lower())
        self.assertEqual(track.get_attribute('data-empty'), 'true')
        self.assertEqual(self.page.locator('#council-influence-royalists, #council-influence-internationalists').evaluate_all('spans => spans.map(span => span.style.width)'), ['0%', '0%'])
        large = copy.deepcopy(before)
        large['royalCouncil']['influence'].update(royalists=9007199254740991, internationalists=9007199254740991)
        self.page.evaluate('incoming => window.__council.replace(incoming)', large)
        self.assertEqual(self.page.locator('#council-influence-royalists, #council-influence-internationalists').evaluate_all('spans => spans.map(span => span.style.width)'), ['50%', '50%'])
        self.assertEqual(track.inner_text().count('9007199254740991 очк.'), 2)
        absent = copy.deepcopy(before)
        del absent['royalCouncil']['influence']
        self.page.evaluate('incoming => window.__council.replace(incoming)', absent)
        self.assertIn('не заданы', track.inner_text().lower())
        self.assertNotIn('influence', self.data()['royalCouncil'])
        self.assertEqual(self.page.evaluate('window.__council.commits'), [])
        self.assertEqual(self.page.evaluate('window.__council.storageWrites'), [])

    def test_balance_editor_saves_full_snapshot_atomically_without_max_or_discarding_member_draft(self):
        baseline = snapshot()
        baseline['royalCouncil']['influence'] = {'royalists': 3, 'internationalists': 1,
                                                 'authorExtra': {'literal': '  Pool metadata  '}}
        self.boot(baseline)
        before = self.data()
        self.assertEqual(self.page.locator('#council-influence-edit').count(), 1, 'global pools need a collapsible author action')
        self.assertTrue(self.page.locator('#council-influence-form').is_hidden())
        self.assertEqual(self.page.locator('#council-influence-edit').get_attribute('aria-expanded'), 'false')
        self.page.locator('.council-rosters [data-council-edit="royal-person-b"]').click()
        self.page.locator('#council-note').fill('  Оставить несохранённое назначение  ')
        self.page.locator('#council-influence-edit').click()
        self.assertTrue(self.page.locator('#council-influence-form').is_visible())
        self.assertEqual(self.page.locator('#council-influence-edit').get_attribute('aria-expanded'), 'true')
        for selector, value in [('#council-royalist-points', '3'), ('#council-internationalist-points', '1')]:
            field = self.page.locator(selector)
            self.assertEqual(field.input_value(), value)
            self.assertEqual(field.get_attribute('type'), 'number')
            self.assertEqual(field.get_attribute('min'), '0')
            self.assertEqual(field.get_attribute('step'), '1')
            self.assertIsNone(field.get_attribute('max'), 'party pools have no game maximum')
            self.assertEqual(field.evaluate('e => e.labels.length'), 1)
        self.assertEqual(self.page.locator('#council-influence-save').get_attribute('type'), 'submit')
        self.page.locator('#council-royalist-points').fill('1000000')
        self.page.locator('#council-internationalist-points').fill('333333')
        self.page.locator('#council-filter-party').select_option('neutral')
        self.assertEqual(self.page.locator('#council-royalist-points').input_value(), '1000000')
        self.page.locator('#council-influence-cancel').click()
        self.assertTrue(self.page.locator('#council-influence-form').is_hidden())
        self.assert_no_writes(before)
        self.page.locator('#council-influence-edit').click()
        self.assertEqual(self.page.locator('#council-royalist-points').input_value(), '3')
        self.page.locator('#council-royalist-points').fill('1000000')
        self.page.locator('#council-internationalist-points').fill('333333')
        self.page.locator('#council-influence-save').click()
        committed = self.data()
        expected = copy.deepcopy(before)
        expected['royalCouncil']['influence'].update(royalists=1000000, internationalists=333333)
        self.assertEqual(committed, expected)
        self.assertEqual(json.loads(self.saved()), committed)
        self.assertTrue(self.page.locator('#council-influence-form').is_hidden())
        self.assertEqual(self.page.locator('#council-note').input_value(), '  Оставить несохранённое назначение  ')
        self.assertTrue(self.page.locator('#council-form').is_visible())
        self.assertEqual(self.page.evaluate('window.__council.commits.length'), 1)
        self.page.locator('#council-influence-edit').click()
        saved = self.saved()
        for selector, value, expected_message in [
                ('#council-royalist-points', '-1', 'Роялист'),
                ('#council-internationalist-points', '1.5', 'Интернационалист'),
                ('#council-royalist-points', '', 'Роялист'),
                ('#council-internationalist-points', '9007199254740992', 'Интернационалист')]:
            self.page.locator('#council-royalist-points').fill('1000000')
            self.page.locator('#council-internationalist-points').fill('333333')
            self.page.locator(selector).fill(value)
            self.page.locator('#council-influence-save').click()
            error = self.page.locator('#council-influence-error')
            self.assertTrue(error.is_visible())
            self.assertIn(expected_message, error.inner_text(), 'each invalid field needs a fresh specific error')
            self.assertEqual(self.data(), committed)
            self.assertEqual(self.saved(), saved)
            self.assertEqual(self.page.locator(selector).input_value(), value, 'invalid input must not silently clamp')
            self.page.locator(selector).fill('0')
            self.assertTrue(error.is_hidden(), 'editing invalid input clears the old error')
            self.assertEqual(error.text_content(), '')
        self.page.locator('#council-royalist-points').fill('0')
        self.page.locator('#council-internationalist-points').fill('0')
        self.page.evaluate('window.__council.rejectCommit = true')
        self.page.locator('#council-influence-save').click()
        self.assertIn('до сохранения', self.page.locator('#council-influence-error').inner_text())
        self.assertEqual(self.data(), committed)
        self.assertEqual(self.saved(), saved)
        self.assertEqual(self.page.locator('#council-royalist-points').input_value(), '0')
        self.page.evaluate('window.__council.rejectCommit = false')
        self.page.locator('#council-influence-save').click()
        self.assertEqual(self.data()['royalCouncil']['influence']['royalists'], 0)
        self.assertEqual(self.data()['royalCouncil']['influence']['internationalists'], 0)
        self.assertIn('нет очков', self.page.locator('#council-influence').inner_text().lower())
        self.assertEqual(self.page.locator('#council-note').input_value(), '  Оставить несохранённое назначение  ')
        self.boot(reload=True)
        self.assertEqual(self.data()['royalCouncil']['influence'], expected['royalCouncil']['influence'] | {'royalists': 0, 'internationalists': 0})
        self.assertEqual(self.page.locator('#council-filter-party').input_value(), 'all')
        self.assertEqual(self.page.locator('#council-filter-kind').input_value(), 'all')

    def test_person_rows_have_two_labeled_max100_ratings_but_houses_never_have_personal_bars(self):
        baseline = snapshot()
        for record in baseline['royalCouncil']['members']:
            if record['kind'] == 'person' and record['id'] != 'neutral-person':
                record['influence'] = {'party': 72, 'kingdom': 31}
        baseline['royalCouncil']['members'][4]['influence'] = {'party': 100, 'kingdom': 0}
        self.boot(baseline)
        before = self.data()
        self.page.locator('label:has(#council-show-history)').click()
        for record in before['royalCouncil']['members']:
            row = self.page.locator('#royal-council .council-member').filter(
                has=self.page.locator('button[data-council-edit="' + record['id'] + '"]'))
            if record['kind'] == 'faction':
                self.assertEqual(row.locator('progress').count(), 0, 'houses have no person rating')
                continue
            self.assertEqual(row.locator('progress').count(), 2, 'every real person has separate party and kingdom ratings')
            expected = record.get('influence', {'party': 0, 'kingdom': 0})
            for scope in ['party', 'kingdom']:
                progress = row.locator('progress[data-influence-scope="' + scope + '"]')
                self.assertEqual(progress.get_attribute('max'), '100')
                self.assertEqual(progress.get_attribute('value'), str(expected[scope]))
                self.assertEqual(progress.evaluate('e => e.labels.length'), 1)
                self.assertIn(str(expected[scope]) + ' / 100', progress.locator('..').inner_text())
            party_label = {'royalists': 'Среди роялистов', 'internationalists': 'Среди интернационалистов',
                           'neutral': 'Среди нейтралов'}[record['party']]
            self.assertIn(party_label, row.inner_text())
            self.assertIn('Во всём королевстве', row.inner_text())
        legacy = self.page.locator('.council-rosters [data-member-id="neutral-person"]')
        self.assertIn('не заданы', legacy.inner_text())
        self.assertNotIn('influence', self.data()['royalCouncil']['members'][2])
        self.page.locator('#council-filter-party').select_option('neutral')
        self.page.locator('#council-filter-kind').select_option('person')
        self.assertEqual(self.page.locator('.council-rosters progress').count(), 2)
        self.assert_no_writes(before)

    def test_person_form_keeps_legacy_absence_until_deliberate_rating_save_and_preserves_assignment_metadata(self):
        baseline = snapshot()
        baseline['royalCouncil']['members'][0].update(refId='test-noble')
        del baseline['royalCouncil']['members'][0]['name']
        baseline['royalCouncil']['members'][4]['influence'] = {'party': 73, 'kingdom': 29,
                                                             'authorExtra': {'literal': '  Rating metadata  '}}
        self.boot(baseline)
        before = self.data()
        self.page.locator('.council-rosters [data-council-edit="royal-person-b"]').click()
        for selector in ['#council-person-party-influence', '#council-person-kingdom-influence']:
            field = self.page.locator(selector)
            self.assertEqual(field.count(), 1, 'person assignment form needs both explicit rating fields')
            self.assertEqual(field.input_value(), '0')
            self.assertEqual(field.get_attribute('type'), 'number')
            self.assertEqual(field.get_attribute('min'), '0')
            self.assertEqual(field.get_attribute('max'), '100')
            self.assertEqual(field.get_attribute('step'), '1')
        self.assertIn('только для справки', self.page.locator('#council-person-influence-hint').inner_text())
        self.page.locator('#council-save').click()
        self.assertEqual(self.data(), before, 'saving untouched legacy person must not fabricate ratings or title')
        self.page.locator('.council-rosters [data-council-edit="royal-person-b"]').click()
        self.page.locator('#council-party').select_option('neutral')
        self.page.locator('#council-save').click()
        self.assertNotIn('influence', self.data()['royalCouncil']['members'][0])
        self.page.locator('.council-rosters [data-council-edit="royal-person-b"]').click()
        self.page.locator('#council-person-party-influence').fill('0')
        self.page.locator('#council-person-kingdom-influence').fill('45')
        self.page.locator('#council-save').click()
        self.assertEqual(self.data()['royalCouncil']['members'][0]['influence'], {'party': 0, 'kingdom': 45})
        self.page.locator('.council-rosters [data-council-edit="royal-person-a"]').click()
        self.assertEqual(self.page.locator('#council-person-party-influence').input_value(), '73')
        self.assertEqual(self.page.locator('#council-person-kingdom-influence').input_value(), '29')
        self.page.locator('#council-person-party-influence').fill('84')
        self.page.locator('#council-note').fill('  Несохранённые поля и рейтинг  ')
        self.page.locator('#council-filter-party').select_option('internationalists')
        self.assertEqual(self.page.locator('#council-person-party-influence').input_value(), '84')
        self.assertEqual(self.page.locator('#council-note').input_value(), '  Несохранённые поля и рейтинг  ')
        incoming = self.data()
        incoming['royalCouncil']['members'][4]['influence']['kingdom'] = 37
        self.page.evaluate('incoming => window.__council.replace(incoming)', incoming)
        self.assertEqual(self.page.locator('#council-person-party-influence').input_value(), '84')
        self.assertEqual(self.page.locator('#council-person-kingdom-influence').input_value(), '29', 'readonly refresh leaves unsaved form alone')
        self.page.locator('#council-party').select_option('internationalists')
        self.page.locator('#council-save').click()
        edited = self.data()['royalCouncil']['members'][4]
        self.assertEqual(edited['influence'], {'party': 84, 'kingdom': 37,
                                             'authorExtra': {'literal': '  Rating metadata  '}}, 'untouched rating preserves newest literal value')
        expected = copy.deepcopy(incoming['royalCouncil']['members'][4])
        expected.update(party='internationalists', note='  Несохранённые поля и рейтинг  ')
        expected['influence']['party'] = 84
        self.assertEqual(edited, expected)
        self.assertEqual(self.data()['royalCouncil']['authorExtra'], before['royalCouncil']['authorExtra'])
        for field in before:
            if field != 'royalCouncil':
                self.assertEqual(self.data()[field], before[field], field)
        self.page.locator('#council-add').click()
        self.assertEqual(self.page.locator('#council-person-party-influence').input_value(), '0')
        self.assertEqual(self.page.locator('#council-person-kingdom-influence').input_value(), '0')
        self.assertIn('сохранены', self.page.locator('#council-person-influence-hint').inner_text())
        count = len(self.data()['royalCouncil']['members'])
        self.page.locator('#council-name').fill('  Авторское новое лицо  ')
        self.assertEqual(len(self.data()['royalCouncil']['members']), count)
        self.page.locator('#council-save').click()
        created = self.data()['royalCouncil']['members'][-1]
        self.assertEqual(created['name'], '  Авторское новое лицо  ')
        self.assertEqual(created['influence'], {'party': 0, 'kingdom': 0})
        saved = self.saved()
        self.boot(reload=True)
        self.assertEqual(self.saved(), saved)
        self.assertEqual(self.data()['royalCouncil']['members'][4], edited)
        self.assertEqual(self.data()['royalCouncil']['members'][-1], created)

    def test_person_rating_fields_reject_each_invalid_value_atomically_with_fresh_errors_and_no_clamp(self):
        baseline = snapshot()
        baseline['royalCouncil']['members'][0]['influence'] = {'party': 72, 'kingdom': 31,
                                                             'authorExtra': {'literal': '  Rating metadata  '}}
        self.boot(baseline)
        self.page.evaluate('window.__council.commit(window.__council.data)')
        before, saved = self.data(), self.saved()
        self.page.locator('.council-rosters [data-council-edit="royal-person-b"]').click()
        for selector, value, expected_message in [
                ('#council-person-party-influence', '101', 'партии'),
                ('#council-person-kingdom-influence', '-1', 'королевстве'),
                ('#council-person-party-influence', '1.5', 'партии'),
                ('#council-person-kingdom-influence', '', 'королевстве')]:
            self.page.locator('#council-person-party-influence').fill('72')
            self.page.locator('#council-person-kingdom-influence').fill('31')
            self.page.locator(selector).fill(value)
            self.page.locator('#council-save').click()
            error = self.page.locator('#council-form-error')
            self.assertTrue(error.is_visible(), 'native submit must show actionable field-specific validation')
            self.assertIn(expected_message, error.inner_text())
            self.assertIn('0', error.inner_text())
            self.assertIn('100', error.inner_text())
            self.assertEqual(self.data(), before)
            self.assertEqual(self.saved(), saved)
            self.assertEqual(self.page.locator(selector).input_value(), value, 'ratings never silently clamp')
            self.page.locator(selector).fill('0')
            self.assertTrue(error.is_hidden())
            self.assertEqual(error.text_content(), '')
        self.page.locator('#council-person-party-influence').fill('100')
        self.page.locator('#council-person-kingdom-influence').fill('0')
        self.page.locator('#council-note').fill('  Не терять после отклонённой записи  ')
        self.page.evaluate('window.__council.rejectCommit=true')
        self.page.locator('#council-save').click()
        self.assertIn('до сохранения', self.page.locator('#council-form-error').inner_text())
        self.assertEqual(self.data(), before)
        self.assertEqual(self.saved(), saved)
        self.assertEqual(self.page.locator('#council-person-party-influence').input_value(), '100')
        self.assertEqual(self.page.locator('#council-note').input_value(), '  Не терять после отклонённой записи  ')
        self.page.evaluate('window.__council.rejectCommit=false')
        self.page.locator('#council-save').click()
        edited = self.data()['royalCouncil']['members'][0]
        self.assertEqual(edited['influence'], {'party': 100, 'kingdom': 0,
                                             'authorExtra': {'literal': '  Rating metadata  '}})
        self.assertEqual(edited['note'], '  Не терять после отклонённой записи  ')
        self.assertEqual(json.loads(self.saved()), self.data())
        self.assertEqual(self.page.locator('#council-form-error').text_content(), '')

    def test_intentional_person_house_conversion_removes_only_person_ratings_and_retains_other_fields(self):
        baseline = snapshot()
        baseline['royalCouncil']['members'][0].update(title='  Титул автора  ', note='  Заметка автора  ',
                                                     influence={'party': 72, 'kingdom': 31})
        self.boot(baseline)
        before = self.data()
        self.page.locator('.council-rosters [data-council-edit="royal-person-b"]').click()
        self.page.locator('#council-person-party-influence').fill('84')
        self.page.locator('#council-kind').select_option('faction')
        self.assertTrue(self.page.locator('#council-person-party-influence').is_hidden())
        self.assertTrue(self.page.locator('#council-person-kingdom-influence').is_hidden())
        self.assertTrue(self.page.locator('#council-person-party-influence').is_disabled(), 'hidden kind-specific ratings cannot block house save')
        self.assert_no_writes(before)
        self.page.locator('#council-kind').select_option('person')
        self.assertEqual(self.page.locator('#council-person-party-influence').input_value(), '84')
        self.assertEqual(self.page.locator('#council-person-kingdom-influence').input_value(), '31')
        self.assertTrue(self.page.locator('#council-person-party-influence').is_enabled())
        self.page.locator('#council-person-party-influence').fill('101')
        self.page.locator('#council-kind').select_option('faction')
        self.page.locator('#council-faction').select_option('test-house-intl-house')
        # Use an unassigned house to avoid duplicate fixture assignments.
        incoming = self.data()
        incoming['factions'].append({'id': 'test-conversion-house', 'name': 'Тестовый дом для превращения',
                                     'parent': 'test-crown', 'color': '#556666'})
        self.page.evaluate('incoming => window.__council.replace(incoming)', incoming)
        self.page.locator('#council-faction').select_option('test-conversion-house')
        self.page.locator('#council-save').click()
        edited = self.data()['royalCouncil']['members'][0]
        expected = copy.deepcopy(incoming['royalCouncil']['members'][0])
        expected.update(kind='faction', refId='test-conversion-house')
        del expected['influence']
        self.assertEqual(edited, expected, 'conversion must remove only the now-inapplicable personal influence')
        self.assertEqual(json.loads(self.saved()), self.data())
        row = self.page.locator('.council-rosters [data-member-id="royal-person-b"]')
        self.assertEqual(row.locator('progress').count(), 0)
        row.locator('[data-council-edit]').click()
        self.page.locator('#council-kind').select_option('person')
        self.page.locator('#council-person').select_option('')
        self.page.locator('#council-person-party-influence').fill('25')
        self.page.locator('#council-person-kingdom-influence').fill('80')
        self.page.locator('#council-save').click()
        reconverted = self.data()['royalCouncil']['members'][0]
        self.assertEqual(reconverted['influence'], {'party': 25, 'kingdom': 80})
        self.assertNotIn('refId', reconverted)
        self.assertEqual(reconverted['name'], before['royalCouncil']['members'][0]['name'])
        self.assertEqual(reconverted['title'], '  Титул автора  ')
        self.assertEqual(reconverted['authorExtra'], before['royalCouncil']['members'][0]['authorExtra'])
        self.assertEqual(reconverted['sources'], [17])

    def test_responsive_controls_global_labels_and_single_party_width_stay_inside_real_dialog(self):
        baseline = snapshot()
        baseline['royalCouncil']['influence'] = {'royalists': 9007199254740991, 'internationalists': 9007199254740991}
        baseline['royalCouncil']['members'][0]['influence'] = {'party': 73, 'kingdom': 29}
        self.boot(baseline)
        metrics = []
        for width, height in [(1440, 1000), (1000, 900), (390, 844), (844, 390)]:
            with self.subTest(viewport=(width, height)):
                self.page.set_viewport_size({'width': width, 'height': height})
                self.page.wait_for_timeout(80)
                self.page.locator('#council-filter-party').select_option('royalists')
                self.page.locator('#council-filter-kind').select_option('person')
                self.page.locator('#council-influence-edit').click()
                self.page.locator('.council-rosters [data-council-edit="royal-person-b"]').click()
                geometry = self.page.evaluate("""() => {
                    const dialog = document.querySelector('#royal-council');
                    const rect = node => {const r=node.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom};};
                    const overflow = node => node.scrollWidth > node.clientWidth + 1;
                    const poolLabels = [...dialog.querySelectorAll('.council-influence-label')];
                    return {dialog:rect(dialog), background:getComputedStyle(dialog).backgroundColor,
                        overflow:overflow(dialog), bodyOverflow:overflow(dialog.querySelector('.council-body')),
                        rosters:rect(dialog.querySelector('.council-rosters')), party:rect(dialog.querySelector('.council-party')),
                        filters:[...dialog.querySelectorAll('.council-filters select')].map(node => ({...rect(node),overflow:overflow(node)})),
                        labels:poolLabels.map(node => ({...rect(node),overflow:overflow(node),color:getComputedStyle(node).color,text:node.innerText})),
                        points:[...dialog.querySelectorAll('.council-influence-points')].map(node => ({...rect(node),overflow:overflow(node),text:node.innerText})),
                        controls:[...dialog.querySelectorAll('button,input:not([type=checkbox]),select')].filter(node => node.getClientRects().length).map(node => ({id:node.id,...rect(node)})),
                        influenceForm:rect(dialog.querySelector('#council-influence-form')),
                        memberForm:rect(dialog.querySelector('#council-form'))};
                }""")
                metrics.append({'viewport': [width, height], **geometry})
                self.assertGreaterEqual(geometry['dialog']['x'], 0)
                self.assertGreaterEqual(geometry['dialog']['y'], 0)
                self.assertLessEqual(geometry['dialog']['right'], width)
                self.assertLessEqual(geometry['dialog']['bottom'], height)
                self.assertEqual(geometry['background'], 'rgb(26, 29, 31)')
                self.assertFalse(geometry['overflow'], geometry)
                self.assertFalse(geometry['bodyOverflow'], geometry)
                self.assertAlmostEqual(geometry['party']['width'], geometry['rosters']['width'], delta=1)
                self.assertLessEqual(geometry['labels'][0]['right'], geometry['labels'][1]['x'])
                self.assertEqual([label['color'] for label in geometry['labels']], ['rgb(154, 168, 182)', 'rgb(99, 144, 150)'])
                for label in geometry['labels']:
                    self.assertFalse(label['overflow'], label)
                    self.assertIn('50%', label['text'])
                for points in geometry['points']:
                    self.assertFalse(points['overflow'], points)
                    self.assertEqual(points['text'], '9007199254740991 очк.')
                for control in geometry['controls']:
                    self.assertGreaterEqual(control['width'], 44, control)
                    self.assertGreaterEqual(control['height'], 44, control)
                    self.assertGreaterEqual(control['x'], geometry['dialog']['x'], control)
                    self.assertLessEqual(control['right'], geometry['dialog']['right'], control)
                for selector in ['#council-influence-save', '#council-save']:
                    self.page.locator(selector).scroll_into_view_if_needed()
                    access = self.page.locator(selector).evaluate("""button => {
                        const r=button.getBoundingClientRect(),head=document.querySelector('#royal-council > .dialog-head').getBoundingClientRect();
                        const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                        return {top:r.top,bottom:r.bottom,headBottom:head.bottom,hit:button.contains(hit)};
                    }""")
                    self.assertGreaterEqual(access['top'], access['headBottom'])
                    self.assertLessEqual(access['bottom'], height)
                    self.assertTrue(access['hit'], access)
                    self.page.locator(selector).focus()
                    self.page.keyboard.press('Shift+Tab')
                    focus = self.page.evaluate("""() => ({id:document.activeElement.id,style:getComputedStyle(document.activeElement).outlineStyle,width:getComputedStyle(document.activeElement).outlineWidth})""")
                    self.assertEqual(focus['style'], 'solid', focus)
                    self.assertEqual(focus['width'], '2px', focus)
                self.page.locator('#council-influence').scroll_into_view_if_needed()
                self.page.screenshot(path=str(ARTIFACTS / f'council-{width}x{height}.png'))
                self.page.locator('#council-influence-cancel').click()
                self.page.locator('#council-cancel').click()
        (ARTIFACTS / 'responsive-metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2))
        self.assertIsNone(self.saved(), 'layout checks must not create drafts')
        self.assertEqual(self.page.evaluate('window.__council.commits'), [])

    def test_edit_mode_hides_only_author_actions_cancels_drafts_and_guards_native_or_direct_saves(self):
        self.boot()
        before = self.data()
        self.assertTrue(self.page.evaluate("document.querySelector('#council-influence-form').hasAttribute('data-edit-only')"))
        for selector in ['#council-add', '#council-form', '#council-influence-edit', '#council-influence-form',
                         '.council-member button[data-council-edit]', '.council-member button[data-council-remove]']:
            self.assertTrue(self.page.locator(selector).evaluate_all('nodes => nodes.length > 0 && nodes.every(node => node.hasAttribute("data-edit-only"))'), selector)
        self.page.locator('.council-rosters [data-council-edit="royal-person-b"]').click()
        self.page.locator('#council-note').fill('  Отменить при отключении правок  ')
        self.page.locator('#council-person-party-influence').fill('45')
        self.page.locator('#council-influence-edit').click()
        self.page.locator('#council-royalist-points').fill('100')
        self.page.evaluate("""() => {
            window.__council.editingEnabled = false;
            document.body.classList.remove('edit-mode');
            window.dispatchEvent(new CustomEvent('gilneas-edit-mode-changed', {detail:{enabled:false}}));
        }""")
        self.assertTrue(self.page.locator('#council-form').is_hidden())
        self.assertTrue(self.page.locator('#council-influence-form').is_hidden())
        for selector in ['#council-add', '#council-influence-edit', '.council-member button[data-council-edit]',
                         '.council-member button[data-council-remove]']:
            self.assertEqual(self.page.locator(selector + ':visible').count(), 0, selector)
        for selector in ['#council-filter-party', '#council-filter-kind', '#council-show-history', '#council-influence']:
            self.assertTrue(self.page.locator(selector).is_visible(), selector)
        self.assertGreater(self.page.locator('.council-rosters progress').count(), 0)
        self.page.locator('#council-filter-party').select_option('neutral')
        self.page.locator('label:has(#council-show-history)').click()
        self.assertEqual(self.row_ids('#council-history'), ['old-neutral-person'])
        self.page.evaluate("""() => {
            document.querySelector('#council-add').click();
            document.querySelector('[data-council-edit]').click();
            document.querySelector('[data-council-remove]').click();
            document.querySelector('#council-influence-edit').click();
            document.querySelector('#council-form').dispatchEvent(new Event('submit', {bubbles:true,cancelable:true}));
            document.querySelector('#council-influence-form').dispatchEvent(new Event('submit', {bubbles:true,cancelable:true}));
        }""")
        self.assertTrue(self.page.locator('#council-form').is_hidden())
        self.assertTrue(self.page.locator('#council-influence-form').is_hidden())
        self.assert_no_writes(before)
        self.page.evaluate("""() => {
            window.__council.editingEnabled = true;
            document.body.classList.add('edit-mode');
            window.dispatchEvent(new CustomEvent('gilneas-edit-mode-changed', {detail:{enabled:true}}));
        }""")
        self.assertTrue(self.page.locator('#council-add').is_visible())
        self.assertTrue(self.page.locator('#council-influence-edit').is_visible())
        self.assertEqual(self.page.locator('#council-filter-party').input_value(), 'neutral')
        self.assertTrue(self.page.locator('#council-show-history').is_checked())
        self.page.locator('.council-rosters [data-council-edit="neutral-person"]').click()
        self.assertEqual(self.page.locator('#council-note').input_value(), '')
        self.assertEqual(self.page.locator('#council-person-party-influence').input_value(), '0')
        self.page.locator('#council-influence-edit').click()
        self.assertEqual(self.page.locator('#council-royalist-points').input_value(), '0')
        self.assert_no_writes(before)

    def test_person_model_validation_rejects_each_field_before_live_or_saved_snapshot_replacement(self):
        baseline = snapshot()
        baseline['royalCouncil']['members'][0]['influence'] = {'party': 72, 'kingdom': 31}
        baseline['royalCouncil']['influence'] = {'royalists': 3, 'internationalists': 1}
        self.boot(baseline)
        self.page.evaluate('window.__council.commit(window.__council.data)')
        before, saved = self.data(), self.saved()
        for scope in ['party', 'kingdom']:
            for invalid in [-1, 101, 1.5, None, '72', True]:
                with self.subTest(scope=scope, invalid=invalid):
                    incoming = copy.deepcopy(before)
                    incoming['royalCouncil']['members'][0]['influence'][scope] = invalid
                    error = self.page.evaluate("""incoming => {
                        try {window.__council.commit(incoming);return null;} catch(error){return error.message;}
                    }""", incoming)
                    self.assertIsNotNone(error)
                    self.assertIn(scope, error)
                    self.assertEqual(self.data(), before)
                    self.assertEqual(self.saved(), saved)
            incoming = copy.deepcopy(before)
            del incoming['royalCouncil']['members'][0]['influence'][scope]
            error = self.page.evaluate("""incoming => {
                try {window.__council.model.saveDraft(localStorage,incoming,window.__council.key);return null;} catch(error){return error.message;}
            }""", incoming)
            self.assertIsNotNone(error)
            self.assertIn(scope, error)
            self.assertEqual(self.saved(), saved)
        malformed_house = copy.deepcopy(before)
        malformed_house['royalCouncil']['members'][1]['influence'] = {'party': 20, 'kingdom': 10}
        error = self.page.evaluate("""incoming => {
            try {window.__council.commit(incoming);return null;} catch(error){return error.message;}
        }""", malformed_house)
        self.assertIsNotNone(error)
        self.assertEqual(self.data(), before)
        self.assertEqual(self.saved(), saved)

    def test_native_person_crud_literal_text_sources_reload_and_delete_preserve_full_snapshot(self):
        baseline = snapshot()
        baseline['sources'].extend([
            {'id': '17', 'title': '  <script>window.bad=1</script>  ', 'url': 'https://example.invalid/literal'},
            {'id': 'unsafe-test', 'title': 'Тестовая небезопасная ссылка', 'url': 'javascript:window.bad=1'},
        ])
        self.boot(baseline)
        original = self.data()
        self.page.locator('#council-add').click()
        literal = '  <script>window.bad=1</script><img src=x onerror=window.bad=2>  '
        self.page.locator('#council-name').fill(literal)
        self.page.locator('#council-note').fill('  <b>Заметка автора</b>  ')
        self.page.locator('#council-person-party-influence').fill('65')
        self.page.locator('#council-person-kingdom-influence').fill('23')
        self.page.locator('#council-save').click()
        created = self.data()['royalCouncil']['members'][-1]
        self.assertEqual(created['name'], literal)
        self.assertEqual(created['influence'], {'party': 65, 'kingdom': 23})
        incoming = self.data()
        incoming['royalCouncil']['members'][-1].update(sources=[17, '17', 'unsafe-test'],
                                                       authorExtra={'literal': '  Keep exact source references  '})
        self.page.evaluate('incoming => window.__council.commit(incoming)', incoming)
        row = self.page.locator('.council-rosters [data-member-id="' + created['id'] + '"]')
        self.assertIn('<script>', row.inner_text())
        self.assertIn('<img', row.inner_text())
        self.assertEqual(row.locator('script,img,b').count(), 0)
        self.assertEqual(row.locator('.council-source-links a').count(), 2)
        self.assertEqual(row.locator('a[href^="javascript:"]').count(), 0)
        self.assertIn('<script>', row.locator('.council-source-links').inner_text())
        self.assertEqual(row.locator('.council-source-links a').first.get_attribute('rel'), 'noopener noreferrer')
        row.locator('[data-council-edit]').click()
        self.page.locator('#council-party').select_option('internationalists')
        self.page.locator('#council-save').click()
        edited = self.data()['royalCouncil']['members'][-1]
        self.assertEqual(edited['sources'], [17, '17', 'unsafe-test'])
        self.assertEqual(edited['influence'], {'party': 65, 'kingdom': 23})
        self.assertEqual(edited['authorExtra'], {'literal': '  Keep exact source references  '})
        saved = self.saved()
        self.boot(reload=True)
        self.assertEqual(self.saved(), saved)
        self.assertEqual(self.data()['royalCouncil']['members'][-1], edited)
        row = self.page.locator('.council-rosters [data-member-id="' + created['id'] + '"]')
        self.page.evaluate('window.__council.confirmValue=false')
        row.locator('[data-council-remove]').click()
        self.assertEqual(self.saved(), saved)
        self.assertEqual(self.data()['royalCouncil']['members'][-1], edited)
        self.page.evaluate('window.__council.confirmValue=true')
        row.locator('[data-council-remove]').click()
        self.assertEqual(self.data(), original)
        self.assertEqual(json.loads(self.saved()), original)
        self.boot(reload=True)
        self.assertEqual(self.data(), original)
        self.assertEqual(self.page.locator('.council-rosters [data-member-id="' + created['id'] + '"]').count(), 0)

    def test_native_wheel_reaches_last_filtered_rating_without_moving_header_or_saving(self):
        baseline = snapshot()
        baseline['royalCouncil']['influence'] = {'royalists': 3, 'internationalists': 1}
        baseline['royalCouncil']['members'][0]['influence'] = {'party': 73, 'kingdom': 29}
        self.boot(baseline)
        before = self.data()
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.page.locator('#council-filter-party').select_option('royalists')
        self.page.locator('#council-filter-kind').select_option('person')
        self.page.evaluate("document.querySelector('.council-body').scrollTop=0")
        self.page.screenshot(path=str(ARTIFACTS / 'portrait-readonly-pools.png'))
        header_before = self.page.locator('#royal-council > .dialog-head').bounding_box()
        body = self.page.locator('.council-body').bounding_box()
        self.page.mouse.move(body['x'] + body['width'] / 2, body['y'] + body['height'] / 2)
        self.page.mouse.wheel(0, 2200)
        self.page.wait_for_function("document.querySelector('.council-body').scrollTop>0", polling=20)
        self.assertAlmostEqual(self.page.locator('#royal-council > .dialog-head').bounding_box()['y'], header_before['y'], delta=1)
        self.page.locator('.council-rosters [data-member-id="royal-person-a"]').scroll_into_view_if_needed()
        last = self.page.locator('.council-rosters [data-member-id="royal-person-a"] progress').last.bounding_box()
        self.assertLessEqual(last['y'] + last['height'], 844)
        self.page.screenshot(path=str(ARTIFACTS / 'portrait-filtered-ratings.png'))
        self.assert_no_writes(before)


if __name__ == '__main__':
    unittest.main()
