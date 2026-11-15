"""Async edit authorization against real modules and test-only full snapshots.

Only app.mjs is suppressed for isolated cases. Confirmation is deliberately
held at the documented ctx seam, independently of the parent's modal cancel.
Run standalone with the supplied gilneas-venv interpreter.
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
EVIDENCE = Path('/Users/daniil_si/.hermes/cache/scratch/gilneas-edit-async-evidence')
STORAGE_KEY = 'gilneas-edit-async-fixture-v1'
DELETE_PATHS = ('object', 'location', 'house', 'territory', 'council', 'wall')


def fixture_snapshot():
    """No published records: every identity and description is test-only."""
    events = [
        {'id': 'async-fixture-wall-target', 'name': 'Только тест: целевое событие',
         'description': '  Test-only wall description  ', 'delta': 15, 'sources': [47],
         'effects': [{'id': 'async-fixture-wall-effect', 'kind': 'bonus',
                      'text': '  Test-only wall effect  ', 'sources': ['async-fixture-source']}],
         'extension': {'blank': '', 'flag': False}},
        {'id': 'async-fixture-wall-keep', 'name': 'Только тест: сохранить событие',
         'delta': -5, 'effects': [], 'extension': {'literal': None}},
    ]
    value = 10
    for event in events:
        value = max(0, min(100, value + event['delta']))
    return {
        'version': 1,
        'meta': {
            'width': 64, 'height': 64, 'image': 'assets/maps/gilneas-enhanced.webp',
            'inactiveMask': 'assets/maps/inactive-mask.png', 'mist': 'assets/maps/inactive-mist.webp',
            'labels': [], 'chronicle': [],
            'wallConstruction': {'baseValue': 10, 'value': value, 'max': 100, 'events': events,
                                 'note': '  Test-only author wall note  '},
            'authorExtra': {'literal': '  <script>not executable</script>  ', 'flag': False},
        },
        'factions': [
            {'id': 'async-fixture-crown', 'name': 'Только тест: корона', 'parent': None,
             'color': '#990000', 'ruler': 'Только тест: правитель', 'extension': {'blank': ''}},
            {'id': 'async-fixture-house-target', 'name': 'Только тест: удаляемый дом',
             'parent': None, 'color': '#557799', 'extension': {'literal': None}},
        ],
        'locations': [
            {'id': 'async-fixture-place-target', 'name': 'Только тест: целевое владение',
             'x': 20, 'y': 20, 'type': 'fortress', 'faction': 'async-fixture-crown',
             'owner': '', 'description': '  Test-only target dossier  ', 'capital': False,
             'provenance': {'confidence': 'custom', 'sources': [47], 'note': '  Keep literal  '},
             'objects': [
                 {'id': 'async-fixture-object-target', 'type': 'building',
                  'name': 'Только тест: целевой объект', 'owner': '', 'description': '  Target object  ',
                  'modifiers': [{'id': 'async-fixture-modifier', 'kind': 'bonus', 'text': '  Test-only modifier  '}],
                  'sources': ['async-fixture-source'], 'extension': {'blank': '', 'flag': False}},
                 {'id': 'async-fixture-object-keep', 'type': 'resource',
                  'name': 'Только тест: сохранить объект', 'amount': 0, 'faction': None,
                  'description': '', 'owner': '', 'modifiers': []},
             ]},
            {'id': 'async-fixture-place-keep', 'name': 'Только тест: сохранить владение',
             'x': 45, 'y': 45, 'type': 'harbor', 'faction': 'async-fixture-crown',
             'description': '  Keep dossier  ', 'owner': '', 'objects': [],
             'extension': {'literal': None}},
        ],
        'territories': [
            {'id': 'async-fixture-territory-target', 'name': 'Только тест: целевая область',
             'faction': 'async-fixture-crown', 'points': [[8, 8], [24, 8], [16, 24]],
             'extension': {'flag': False}},
            {'id': 'async-fixture-territory-keep', 'name': 'Только тест: сохранить область',
             'faction': 'async-fixture-crown', 'points': [[40, 40], [56, 40], [48, 56]]},
        ],
        'nobles': [{'id': 'async-fixture-noble', 'name': 'Только тест: персонаж',
                    'house': 'async-fixture-crown', 'description': '  Keep biography  ', 'sources': [47]}],
        'sources': [
            {'id': 47, 'title': 'Только тест: числовой источник', 'url': 'https://example.invalid/test-only-47'},
            {'id': 'async-fixture-source', 'title': 'Только тест: строковый источник',
             'url': 'https://example.invalid/test-only-source'},
        ],
        'royalCouncil': {
            'version': 1,
            'members': [
                {'id': 'async-fixture-council-target', 'kind': 'person', 'refId': 'async-fixture-noble',
                 'party': 'neutral', 'stance': 'unknown', 'advisor': False, 'active': True,
                 'note': '  Test-only target appointment  ', 'sources': [47],
                 'influence': {'party': 12, 'kingdom': 18}, 'extension': {'flag': False}},
                {'id': 'async-fixture-council-keep', 'kind': 'person', 'name': 'Только тест: сохранить назначение',
                 'party': 'royalists', 'stance': 'unknown', 'advisor': False, 'active': True,
                 'note': '', 'influence': {'party': 0, 'kingdom': 0}},
            ],
            'influence': {'royalists': 70, 'internationalists': 40, 'extension': {'blank': ''}},
            'authorNote': '  Keep council metadata  ',
        },
        'territoryGrid': {
            'version': 1, 'width': 2, 'height': 2, 'step': 32, 'mapWidth': 64, 'mapHeight': 64,
            'keys': ['async-fixture-crown'], 'cells': [1, 0, 1, 0], 'radius': 260, 'manual': True,
            'authorManualKeys': {'1': 0, '2': 'async-fixture-crown'},
            'provenance': {'sources': [47], 'note': 'Test-only manual ownership and intentional zero cells'},
        },
        'authorRegistry': [{'blank': '', 'flag': False, 'null': None, 'literal': '  Preserve whole snapshot  '}],
    }


BOOTSTRAP = """async ({snapshot, key, contextGetter, enabled}) => {
    const model = await import('./assets/js/model.mjs');
    const editModule = await import('./assets/js/edit-mode.mjs');
    const {initEditor} = await import('./assets/js/editor.mjs');
    const {initRoyalCouncilWindow} = await import('./assets/js/council-window.mjs');
    const {initWallJournal} = await import('./assets/js/wall-journal.mjs');
    const freeze = value => {
        if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
        return value;
    };
    let data = freeze(model.normalizeData(snapshot));
    let selected = 'async-fixture-place-target';
    let interaction = null;
    const mode = editModule.initEditMode();
    const commits = [], confirmations = [], pending = [], toasts = [];
    // Seed intentionally noncanonical whitespace: a stale operation must not
    // even rewrite the same saved draft through the real model serializer.
    const saved = JSON.stringify(data, null, 3) + '\\n';
    localStorage.setItem(key, saved);
    const ctx = {
        getData: () => data,
        getSelectedId: () => selected,
        replaceData: incoming => {
            if (!mode.isEnabled()) throw new Error('Test-only readonly parent guard');
            const next = freeze(model.normalizeData(incoming));
            model.saveDraft(localStorage, next, key);
            data = next; commits.push(structuredClone(data));
            window.dispatchEvent(new CustomEvent('gilneas-data-changed'));
            return data;
        },
        onSelect: id => { selected = id; },
        ui: { setMapInteraction: callback => { interaction = callback; } },
        canPlace: () => true,
        toast: message => toasts.push(message),
        confirm: (title, message) => {
            confirmations.push([title, message]);
            return new Promise(resolve => pending.push({resolve}));
        },
    };
    if (contextGetter) ctx.isEditingEnabled = () => mode.isEnabled() && window.asyncFixture.contextEnabled;
    window.asyncFixture = {
        getData: () => data, original: structuredClone(data), saved, model, mode, editModule,
        contextEnabled: true,
        commits, confirmations, pending, toasts,
        get selected() { return selected; },
        get interacting() { return typeof interaction === 'function'; },
        state: () => ({data: structuredClone(data), saved: localStorage.getItem(key),
                      commits: commits.length, confirmations: confirmations.length,
                      pending: pending.length, enabled: mode.isEnabled()}),
        release: async value => {
            if (pending.length !== 1) throw new Error('Expected exactly one held confirmation');
            pending.shift().resolve(value);
            // The actual module continuation is queued before this microtask.
            await Promise.resolve();
        },
    };
    window.asyncFixture.editor = initEditor(ctx);
    window.asyncFixture.council = initRoyalCouncilWindow(ctx);
    window.asyncFixture.wall = initWallJournal(ctx);
    const {decorateIcons} = await import('./assets/js/icons.mjs'); decorateIcons();
    mode.setEnabled(enabled);
}"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class EditAsyncRevision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(args=[
            '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
        ])
        EVIDENCE.mkdir(parents=True, exist_ok=True)

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
        self.page.set_default_timeout(8000)
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)
        self.page.on('response', lambda response: self.errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
        self.page.route('**/assets/js/app.mjs', lambda route: route.fulfill(
            status=200, content_type='application/javascript', body='// Async fixture: isolate parent bootstrap only.'))

    def tearDown(self):
        self.context.close()

    def boot(self, context_getter=False, enabled=True):
        self.page.goto(self.url, wait_until='load')
        self.page.evaluate(BOOTSTRAP, {'snapshot': fixture_snapshot(), 'key': STORAGE_KEY,
                                      'contextGetter': context_getter, 'enabled': enabled})
        self.assertEqual(self.errors, [])
        return self.state()

    def state(self):
        return self.page.evaluate('window.asyncFixture.state()')

    def begin_delete(self, kind):
        if kind == 'object':
            self.page.evaluate("""() => {
                window.asyncFixture.operation = window.asyncFixture.editor.deleteObject(
                    'async-fixture-place-target', 'async-fixture-object-target');
            }""")
        elif kind == 'location':
            self.page.evaluate('window.asyncFixture.editor.open()')
            self.page.locator('#location-delete').click()
        elif kind == 'house':
            self.page.evaluate('window.asyncFixture.editor.openHouses()')
            self.page.locator('button[data-house-delete="async-fixture-house-target"]').click()
        elif kind == 'territory':
            self.page.evaluate('window.asyncFixture.editor.openTerritories()')
            self.page.locator('button[data-territory-delete="async-fixture-territory-target"]').click()
        elif kind == 'council':
            self.page.evaluate('window.asyncFixture.council.open()')
            self.page.locator('button[data-council-remove="async-fixture-council-target"]').click()
        elif kind == 'wall':
            self.page.evaluate('window.asyncFixture.wall.open()')
            self.page.locator('button[data-wall-event-delete="async-fixture-wall-target"]').click()
        else:
            self.fail(f'Unknown delete path: {kind}')

    def expected_delete(self, before, kind):
        expected = copy.deepcopy(before)
        if kind == 'object':
            location = next(record for record in expected['locations'] if record['id'] == 'async-fixture-place-target')
            location['objects'] = [record for record in location['objects'] if record['id'] != 'async-fixture-object-target']
        elif kind == 'location':
            expected['locations'] = [record for record in expected['locations'] if record['id'] != 'async-fixture-place-target']
        elif kind == 'house':
            expected['factions'] = [record for record in expected['factions'] if record['id'] != 'async-fixture-house-target']
        elif kind == 'territory':
            expected['territories'] = [record for record in expected['territories'] if record['id'] != 'async-fixture-territory-target']
        elif kind == 'council':
            expected['royalCouncil']['members'] = [record for record in expected['royalCouncil']['members']
                                                    if record['id'] != 'async-fixture-council-target']
        elif kind == 'wall':
            track = expected['meta']['wallConstruction']
            track['events'] = [record for record in track['events'] if record['id'] != 'async-fixture-wall-target']
            value = track['baseValue']
            for event in track['events']:
                value = max(0, min(track['max'], value + event['delta']))
            track['value'] = value
        else:
            self.fail(f'Unknown delete path: {kind}')
        return expected

    def exercise_revision_guard(self, kind, context_getter=False):
        before = self.boot(context_getter=context_getter)
        self.begin_delete(kind)
        held = self.state()
        self.assertEqual(held['pending'], 1, f'{kind}: real module must reach the held confirmation')
        self.assertEqual(held['confirmations'], 1)
        self.assertEqual(held['data'], before['data'])
        self.assertEqual(held['saved'], before['saved'])
        self.page.evaluate("""() => {
            window.asyncFixture.mode.setEnabled(false);
            window.asyncFixture.mode.setEnabled(true);
        }""")
        toggled = self.state()
        self.assertTrue(toggled['enabled'])
        self.assertEqual(toggled['pending'], 1, 'The ctx promise intentionally does not auto-cancel on disable')
        self.assertEqual(toggled['data'], before['data'])
        self.assertEqual(toggled['saved'], before['saved'])
        self.page.evaluate('window.asyncFixture.release(true)')
        stale = self.state()
        evidence = {'path': kind, 'before': before, 'after_stale_confirmation': stale}
        path = EVIDENCE / f'{kind}-{"context" if context_getter else "fallback"}-latest.json'
        path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
        self.assertEqual(stale['data'], before['data'], f'{kind}: OFF -> ON must not reauthorize the old pending deletion')
        self.assertEqual(stale['saved'], before['saved'], f'{kind}: exact saved draft must survive stale confirmation')
        self.assertEqual(stale['commits'], 0)
        self.assertEqual(stale['pending'], 0)
        self.assertEqual(self.errors, [])
        # A fresh confirmation in the current active session still deletes only
        # its literal target, preserving the complete unrelated snapshot.
        self.begin_delete(kind)
        self.assertEqual(self.state()['pending'], 1)
        self.page.evaluate('window.asyncFixture.release(true)')
        active = self.state()
        expected = self.expected_delete(before['data'], kind)
        self.assertEqual(active['data'], expected, f'{kind}: active confirmed deletion must succeed exactly once')
        self.assertEqual(json.loads(active['saved']), expected)
        self.assertEqual(active['commits'], 1)
        self.assertEqual(active['confirmations'], 2)
        self.assertEqual(active['pending'], 0)
        self.assertEqual(self.errors, [])
        evidence['after_fresh_confirmation'] = active
        path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    def test_shared_editing_revision_tracks_transitions_without_changing_the_snapshot(self):
        before = self.boot(enabled=False)
        revisions = self.page.evaluate("""() => {
            const fixture = window.asyncFixture;
            if (typeof fixture.editModule.getEditingRevision !== 'function') {
                return {hasSharedGetter: false};
            }
            const values = [];
            const record = () => values.push({shared: fixture.editModule.getEditingRevision(),
                parent: fixture.mode.getRevision(), enabled: fixture.mode.isEnabled()});
            record(); fixture.mode.setEnabled(false); record();
            fixture.mode.setEnabled(true); record(); fixture.mode.setEnabled(true); record();
            fixture.mode.setEnabled(false); record(); fixture.mode.setEnabled(true); record();
            return {hasSharedGetter: true, values};
        }""")
        self.assertTrue(revisions['hasSharedGetter'], 'Async module guards need the same revision as the real parent')
        self.assertEqual(revisions['values'], [
            {'shared': 0, 'parent': 0, 'enabled': False},
            {'shared': 0, 'parent': 0, 'enabled': False},
            {'shared': 1, 'parent': 1, 'enabled': True},
            {'shared': 1, 'parent': 1, 'enabled': True},
            {'shared': 2, 'parent': 2, 'enabled': False},
            {'shared': 3, 'parent': 3, 'enabled': True},
        ])
        after = self.state()
        self.assertEqual(after['data'], before['data'])
        self.assertEqual(after['saved'], before['saved'])
        self.assertEqual(after['commits'], 0)
        self.assertEqual(self.errors, [])

    def test_delete_object_cannot_reauthorize_a_confirmation_from_before_disable(self):
        self.exercise_revision_guard('object')

    def test_delete_location_cannot_reauthorize_a_confirmation_from_before_disable(self):
        self.exercise_revision_guard('location')

    def test_delete_house_cannot_reauthorize_a_confirmation_from_before_disable(self):
        self.exercise_revision_guard('house')

    def test_delete_territory_cannot_reauthorize_a_confirmation_from_before_disable(self):
        self.exercise_revision_guard('territory')

    def test_delete_council_member_cannot_reauthorize_a_confirmation_from_before_disable(self):
        self.exercise_revision_guard('council')

    def test_delete_wall_event_cannot_reauthorize_a_confirmation_from_before_disable(self):
        self.exercise_revision_guard('wall')

    def test_context_enabled_getter_uses_the_shared_revision_for_each_deletion(self):
        for kind in DELETE_PATHS:
            with self.subTest(path=kind):
                self.exercise_revision_guard(kind, context_getter=True)

    def test_enabled_context_is_rechecked_after_await_even_without_a_revision_change(self):
        for kind in DELETE_PATHS:
            with self.subTest(path=kind):
                before = self.boot(context_getter=True)
                self.begin_delete(kind)
                self.assertEqual(self.state()['pending'], 1)
                # A custom context can revoke permission without the global
                # transition event. The post-await enabled check still matters.
                self.page.evaluate('window.asyncFixture.contextEnabled = false')
                self.page.evaluate('window.asyncFixture.release(true)')
                after = self.state()
                self.assertEqual(after['data'], before['data'])
                self.assertEqual(after['saved'], before['saved'])
                self.assertEqual(after['commits'], 0)
                self.assertEqual(after['pending'], 0)
                self.assertEqual(self.errors, [])

    def test_omitted_context_getter_keeps_each_hidden_deletion_readonly(self):
        actions = {
            'object': "window.asyncFixture.editor.deleteObject('async-fixture-place-target', 'async-fixture-object-target')",
            'location': "document.getElementById('location-delete').click()",
            'house': "document.querySelector('button[data-house-delete=\"async-fixture-house-target\"]').click()",
            'territory': "document.querySelector('button[data-territory-delete=\"async-fixture-territory-target\"]').click()",
            'council': "document.querySelector('button[data-council-remove=\"async-fixture-council-target\"]').click()",
            'wall': "document.querySelector('button[data-wall-event-delete=\"async-fixture-wall-target\"]').click()",
        }
        for kind in DELETE_PATHS:
            with self.subTest(path=kind):
                before = self.boot()
                self.page.evaluate("""() => {
                    window.asyncFixture.editor.open();
                    window.asyncFixture.editor.openHouses();
                    window.asyncFixture.editor.openTerritories();
                    window.asyncFixture.council.open();
                    window.asyncFixture.wall.open();
                    window.asyncFixture.mode.setEnabled(false);
                }""")
                self.page.evaluate(f'async () => {{ await ({actions[kind]}); }}')
                after = self.state()
                self.assertFalse(after['enabled'])
                self.assertEqual(after['data'], before['data'])
                self.assertEqual(after['saved'], before['saved'])
                self.assertEqual(after['commits'], 0)
                self.assertEqual(after['confirmations'], 0)
                self.assertEqual(after['pending'], 0)
                self.assertEqual(self.errors, [])

    def test_disable_discards_private_object_location_council_and_wall_drafts(self):
        for kind in ('object', 'location', 'council', 'wall'):
            with self.subTest(draft=kind):
                before = self.boot()
                self.page.evaluate("""kind => {
                    const fixture = window.asyncFixture;
                    if (kind === 'object') {
                        fixture.editor.editObject('async-fixture-place-target', 'async-fixture-object-target');
                        document.getElementById('object-name').value = 'Test-only cancelled object';
                        document.getElementById('modifier-bonus-add').click();
                    } else if (kind === 'location') {
                        fixture.editor.editLocation('async-fixture-place-target');
                        document.getElementById('location-name').value = 'Test-only cancelled location';
                    } else if (kind === 'council') {
                        fixture.council.open();
                        document.querySelector('button[data-council-edit="async-fixture-council-target"]').click();
                        document.getElementById('council-note').value = 'Test-only cancelled appointment';
                        document.getElementById('council-influence-edit').click();
                        document.getElementById('council-royalist-points').value = '81';
                    } else {
                        fixture.wall.open();
                        document.querySelector('button[data-wall-event-edit="async-fixture-wall-target"]').click();
                        document.getElementById('wall-event-name').value = 'Test-only cancelled event';
                        document.getElementById('wall-effect-bonus-add').click();
                    }
                    fixture.mode.setEnabled(false); fixture.mode.setEnabled(true);
                }""", kind)
                self.page.evaluate("""kind => {
                    const forms = {object: ['object-form'], location: ['location-form'],
                        council: ['council-form', 'council-influence-form'], wall: []};
                    for (const id of forms[kind]) document.getElementById(id).dispatchEvent(
                        new Event('submit', {bubbles: true, cancelable: true}));
                }""", kind)
                after = self.state()
                self.assertEqual(after['data'], before['data'])
                self.assertEqual(after['saved'], before['saved'])
                self.assertEqual(after['commits'], 0)
                if kind == 'council':
                    self.assertTrue(self.page.locator('#council-form').evaluate('node => node.hidden'))
                    self.assertTrue(self.page.locator('#council-influence-form').evaluate('node => node.hidden'))
                    self.assertEqual(self.page.locator('#council-note').input_value(), '')
                elif kind == 'wall':
                    self.assertEqual(self.page.locator('#wall-event-id').input_value(), '')
                    self.assertEqual(self.page.locator('#wall-event-name').input_value(), '')
                    self.assertEqual(self.page.locator('#wall-effect-list textarea').count(), 0)
                else:
                    self.assertFalse(self.page.locator(f'#{kind}-editor').evaluate('node => node.open'))
                    self.assertEqual(self.page.locator(f'#{kind}-name').input_value(), '')
                self.assertEqual(self.errors, [])

    def test_queued_native_close_does_not_erase_a_new_current_session_draft(self):
        for kind in ('object', 'location', 'council', 'wall'):
            with self.subTest(draft=kind):
                before = self.boot()
                self.page.evaluate("""async kind => {
                    const fixture = window.asyncFixture;
                    const reopen = () => {
                        if (kind === 'object') fixture.editor.editObject('async-fixture-place-target', 'async-fixture-object-target');
                        else if (kind === 'location') fixture.editor.editLocation('async-fixture-place-target');
                        else if (kind === 'council') {
                            fixture.council.open();
                            document.querySelector('button[data-council-edit="async-fixture-council-target"]').click();
                        } else {
                            fixture.wall.open();
                            document.querySelector('button[data-wall-event-edit="async-fixture-wall-target"]').click();
                        }
                    };
                    reopen();
                    const dialog = document.getElementById({object: 'object-editor', location: 'location-editor',
                        council: 'royal-council', wall: 'wall-journal'}[kind]);
                    const closed = new Promise(resolve => dialog.addEventListener('close', resolve, {once: true}));
                    dialog.close(); reopen();
                    document.getElementById({object: 'object-name', location: 'location-name',
                        council: 'council-note', wall: 'wall-event-name'}[kind]).value = '  Test-only current reopened draft  ';
                    await closed;
                }""", kind)
                form = {'object': 'object-form', 'location': 'location-form',
                        'council': 'council-form', 'wall': 'wall-event-form'}[kind]
                self.page.locator(f'#{form} button[type=submit]').click()
                after = self.state()
                expected = copy.deepcopy(before['data'])
                if kind == 'object':
                    expected['locations'][0]['objects'][0]['name'] = '  Test-only current reopened draft  '
                elif kind == 'location':
                    expected['locations'][0]['name'] = '  Test-only current reopened draft  '
                elif kind == 'council':
                    expected['royalCouncil']['members'][0]['note'] = '  Test-only current reopened draft  '
                else:
                    expected['meta']['wallConstruction']['events'][0]['name'] = '  Test-only current reopened draft  '
                self.assertEqual(after['data'], expected)
                self.assertEqual(json.loads(after['saved']), expected)
                self.assertEqual(after['commits'], 1)
                self.assertEqual(self.errors, [])

    def test_parent_native_confirmation_cancels_and_settles_on_disable_without_a_lingering_modal(self):
        self.page.unroute('**/assets/js/app.mjs')
        self.page.route('**/assets/data/atlas.json', lambda route: route.fulfill(
            status=200, content_type='application/json', body=json.dumps(fixture_snapshot(), ensure_ascii=False)))
        self.page.goto(self.url, wait_until='domcontentloaded')
        self.page.wait_for_function('window.gilneasApp?.ready', polling=50, timeout=30000)
        self.page.wait_for_function('document.getElementById("base-map").complete && document.getElementById("base-map").naturalWidth > 0', polling=50)
        before = self.page.evaluate('window.gilneasApp.getData()')
        raw = json.dumps(before, ensure_ascii=False, indent=3) + '\n'
        self.page.evaluate("raw => { localStorage.setItem('gilneas-atlas-draft-v1', raw); }", raw)
        self.page.locator('#editor-open').click()
        self.page.locator('label:has(#editing-enabled)').click()
        self.page.locator('[data-close="editor"]').click()
        self.page.evaluate("""() => {
            window.nativeConfirmationCancelled = 0;
            window.nativeDeleteSettled = false;
            document.getElementById('confirm-no').addEventListener('click', () => {
                window.nativeConfirmationCancelled += 1;
            });
            window.nativeDeleteOperation = window.gilneasApp.editor.deleteObject(
                'async-fixture-place-target', 'async-fixture-object-target').then(() => {
                    window.nativeDeleteSettled = true;
                });
        }""")
        self.assertTrue(self.page.locator('#confirmation').evaluate('node => node.open'))
        self.assertFalse(self.page.evaluate('window.nativeDeleteSettled'))
        self.page.evaluate("""() => {
            const input = document.getElementById('editing-enabled');
            input.checked = false; input.dispatchEvent(new Event('change', {bubbles: true}));
            input.checked = true; input.dispatchEvent(new Event('change', {bubbles: true}));
        }""")
        self.page.evaluate('window.nativeDeleteOperation')
        cancellation = self.page.evaluate("""() => ({
            settled: window.nativeDeleteSettled, cancelled: window.nativeConfirmationCancelled,
            open: document.getElementById('confirmation').open,
            yesHandlerCleared: document.getElementById('confirm-yes').onclick === null,
            noHandlerCleared: document.getElementById('confirm-no').onclick === null,
            data: window.gilneasApp.getData(), saved: localStorage.getItem('gilneas-atlas-draft-v1'),
        })""")
        self.assertTrue(cancellation['settled'])
        self.assertEqual(cancellation['cancelled'], 1, 'The actual parent must settle through confirm-no (false)')
        self.assertFalse(cancellation['open'])
        self.assertTrue(cancellation['yesHandlerCleared'])
        self.assertTrue(cancellation['noHandlerCleared'])
        self.assertEqual(cancellation['data'], before)
        self.assertEqual(cancellation['saved'], raw)
        # A late click cannot resolve the cancelled prompt as true.
        self.page.evaluate("document.getElementById('confirm-yes').click()")
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), before)
        self.assertEqual(self.page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')"), raw)
        # New native confirmations still have their ordinary active behavior.
        self.page.evaluate("""() => {
            window.nativeDeleteOperation = window.gilneasApp.editor.deleteObject(
                'async-fixture-place-target', 'async-fixture-object-target');
        }""")
        self.page.locator('#confirm-yes').click()
        self.page.evaluate('window.nativeDeleteOperation')
        expected = self.expected_delete(before, 'object')
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData()'), expected)
        self.assertEqual(json.loads(self.page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')")), expected)
        self.assertFalse(self.page.locator('#confirmation').evaluate('node => node.open'))
        self.assertEqual(self.errors, [])
        (EVIDENCE / 'native-parent-confirmation.json').write_text(json.dumps(
            {'cancelled': cancellation, 'active': self.page.evaluate('window.gilneasApp.getData()')},
            ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
