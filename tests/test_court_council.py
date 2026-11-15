"""Royal Council vertical tracer bullets with real model, DOM, CSS and input.

Only app.mjs is isolated; the fixture commit normalizes before local storage.
Fixtures use seven existing houses and two leaders, never political research.
Run: /Users/daniil_si/.hermes/cache/scratch/gilneas-venv/bin/python tests/test_court_council.py -v
"""
import copy
import functools
import json
import os
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ.get('TMPDIR', '/Users/daniil_si/.hermes/cache/scratch')) / 'gilneas-council-evidence'
STORAGE_KEY = 'gilneas-council-fixture-v1'


def snapshot():
    data = json.loads((ROOT / 'assets/data/publication-v3.json').read_text())
    houses = {'gilneas', 'greymane', 'crowley', 'silverlaine', 'godfrey', 'ashbury', 'marley', 'walden'}
    data['factions'] = [f for f in data['factions'] if f['id'] in houses]
    data['nobles'] = [n for n in data['nobles'] if n['id'] in {'noble-genn', 'noble-darius'}]
    location = copy.deepcopy(data['locations'][0])
    location.update(id='council-fixture-place', name='Тестовое владение Совета', faction='silverlaine',
                    owner='Дариус Краули', x=1800, y=3400, objects=[])
    data['locations'] = [location]
    data['territories'] = []
    data.pop('royalCouncil', None)
    data['authorMetadata'] = {'falseLiteral': False, 'blankLiteral': '', 'scriptLiteral': '<script>untouched</script>'}
    return data


def assignment(**patch):
    value = dict(id='council-fixture-genn', kind='person', refId='noble-genn', party='royalists',
                 stance='unknown', advisor=False, active=True, note='', sources=[45], basis='scenario')
    value.update(patch)
    return value


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class CourtCouncil(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
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
            status=200, content_type='application/javascript', body='// Council: isolate parent bootstrap only.'))

    def tearDown(self):
        self.context.close()

    def boot(self, data=None, size=None, reload=False):
        if size:
            self.page.set_viewport_size(size)
        if not reload:
            self.data = copy.deepcopy(data if data is not None else snapshot())
        self.page.goto(self.url + '/index.html', wait_until='networkidle')
        self.page.evaluate("""async options => {
            document.body.classList.add('edit-mode');
            if (options.css && !document.querySelector('link[href$="royal-council.css"]')) {
                const link=document.createElement('link'); link.rel='stylesheet'; link.href='./assets/css/royal-council.css';
                document.querySelector('link[href$="royal-windows.css"]').after(link);
                await new Promise((resolve,reject)=>{link.onload=resolve;link.onerror=reject;});
            }
            if (!document.querySelector('#council-open')) {
                const opener=document.createElement('button'); opener.id='council-open'; opener.type='button';
                opener.className='text-button'; opener.textContent='Совет'; opener.setAttribute('aria-label','Королевский Совет');
                document.querySelector('.toolbar').prepend(opener);
            }
            const model=await import('./assets/js/model.mjs');
            const engine=await import('./assets/js/royal-council.mjs');
            window.fixtureData=model.normalizeData(options.reload ? JSON.parse(localStorage.getItem(options.key)) : options.snapshot);
            if(!options.reload){
                const {generate}=await import('./assets/js/territory-engine.mjs');
                const grid=generate(window.fixtureData.locations,window.fixtureData.factions,260,window.fixtureData.meta,()=>true,128);
                grid.cells[0]=0;grid.cells[1]=2;grid.cells[2]=3;
                grid.provenance={sources:[45],note:'Test-only manual owner and intentional zero cells'};
                grid.authorManualKeys={'0':0,'1':'greymane','2':'crowley'};
                window.fixtureData.territoryGrid=grid;
            }
            window.fixtureOriginal=structuredClone(window.fixtureData); window.calls=[]; window.rejectCommit=false;
            document.querySelector('#base-map').src=window.fixtureData.meta.image;
            window.fixtureCommit=incoming=>{
                engine.validateRoyalCouncil(incoming.royalCouncil,incoming);
                const next=model.normalizeData(incoming);
                if(window.rejectCommit)throw Error('Тест: сохранение отклонено до записи');
                model.saveDraft(localStorage,next,options.key);
                window.fixtureData=next; window.calls.push(['commit']);
                window.dispatchEvent(new CustomEvent('gilneas-data-changed'));
                return next;
            };
            window.fixtureExport=()=>model.serializeSnapshot(window.fixtureData);
            window.fixtureImport=text=>window.fixtureCommit(model.deserializeSnapshot(text));
            window.fixtureConfirmValue=true;
            const {initRoyalCouncilWindow}=await import('./assets/js/council-window.mjs');
            window.councilUI=initRoyalCouncilWindow({getData:()=>window.fixtureData,replaceData:window.fixtureCommit,
                toast:message=>window.calls.push(['toast',message]),
                confirm:async(title,message)=>{window.calls.push(['confirm',title,message]);return window.fixtureConfirmValue;},
                onShowNoble:id=>window.calls.push(['noble',id])});
            const {decorateIcons}=await import('./assets/js/icons.mjs'); decorateIcons();
        }""", {'snapshot': self.data, 'css': (ROOT / 'assets/css/royal-council.css').exists(), 'reload': reload, 'key': STORAGE_KEY})
        self.page.wait_for_function("document.querySelector('#base-map').complete && document.querySelector('#base-map').naturalWidth>0", polling=50)
        self.page.mouse.move(2, 2)

    def open(self):
        self.page.locator('#council-open').click()

    def clean(self):
        self.assertEqual(self.errors, [])

    def test_01_empty_legacy_council_has_live_two_leaders_and_neutral_without_invented_members(self):
        self.boot()
        self.open()
        dialog = self.page.locator('#royal-council')
        self.assertTrue(dialog.evaluate('e=>e.open'))
        self.assertIn('iron-dialog', dialog.get_attribute('class'))
        self.assertEqual(dialog.get_attribute('aria-labelledby'), 'council-title')
        self.assertEqual(self.page.locator('#council-title').inner_text(), 'Королевский Совет')
        self.assertEqual(self.page.locator('.council-party').count(), 3)
        self.assertIn('Генн Седогрив', self.page.locator('.council-party[data-party="royalists"] .council-leader').inner_text())
        self.assertIn('Дариус Краули', self.page.locator('.council-party[data-party="internationalists"] .council-leader').inner_text())
        self.assertEqual(self.page.locator('.council-party[data-party="neutral"] .council-leader').count(), 0)
        self.assertEqual(self.page.locator('.council-member').count(), 0)
        self.assertEqual(self.page.locator('.council-house-list').count(), 3)
        self.assertEqual(self.page.locator('.council-person-list').count(), 3)
        self.assertFalse(self.page.locator('#council-show-history').is_checked())
        self.assertFalse(self.page.evaluate('Object.hasOwn(window.fixtureData,"royalCouncil")'))
        self.page.evaluate("window.fixtureData.nobles[0].name='Генн — имя автора'; window.councilUI.render()")
        self.assertIn('Генн — имя автора', self.page.locator('.council-party[data-party="royalists"] .council-leader').inner_text())
        self.clean()

    def test_02_live_readonly_rosters_keep_advisors_separate_true_house_shields_unknown_stance_and_history(self):
        data = snapshot()
        data['royalCouncil'] = {'version': 1, 'members': [
            assignment(id='council-fixture-house-' + house['id'], kind='faction', refId=house['id'], party='neutral')
            for house in data['factions'] if house['parent'] is not None
        ] + [assignment(advisor=True, note='Тестовый советник; не политическое свидетельство.'),
             assignment(id='council-fixture-darius', refId='noble-darius', party='internationalists', stance='oppose', sources=[46]),
             dict(id='council-fixture-historical', kind='person', name='Тестовый предшественник', title='', party='royalists',
                  stance='unknown', advisor=True, active=False, note='Только историческая тестовая запись.', sources=[45], basis='scenario')]}
        data['sources'].append({'id': 'council-fixture-unsafe', 'title': '<script>bad source</script>', 'url': 'javascript:window.councilExecuted=1'})
        data['royalCouncil']['members'][0]['sources'] = [45, 'council-fixture-unsafe']
        self.boot(data)
        self.open()
        self.assertEqual(self.page.locator('.council-rosters .council-member').count(), 9)
        genn = self.page.locator('.council-rosters [data-member-id="council-fixture-genn"]')
        self.assertEqual(genn.locator('.council-advisor-badge').inner_text(), 'Королевский советник')
        self.assertEqual(genn.locator('.council-party-badge').inner_text(), 'Роялисты')
        self.assertEqual(genn.locator('.council-stance').inner_text(), 'Позиция по Стене не установлена')
        self.assertIn('Тестовый советник', genn.locator('.council-note').inner_text())
        self.assertEqual(genn.locator('.faction-shield').get_attribute('data-faction-id'), 'greymane')
        silverlaine = self.page.locator('.council-rosters [data-member-id="council-fixture-house-silverlaine"]')
        self.assertEqual(silverlaine.locator('.faction-shield').get_attribute('data-faction-id'), 'silverlaine')
        self.assertEqual(silverlaine.locator('.council-advisor-badge').count(), 0)
        self.assertEqual(silverlaine.locator('select').count(), 0, 'Roster is generated readonly, not an inline assignment registry')
        self.assertEqual(self.page.locator('.council-rosters [data-member-id="council-fixture-darius"] .council-stance').inner_text(), 'Против строительства Стены')
        self.assertTrue(self.page.locator('#council-history').is_hidden())
        self.page.locator('label:has(#council-show-history)').click()
        self.assertTrue(self.page.locator('#council-history').is_visible())
        self.assertIn('Исторические записи', self.page.locator('#council-history > h3').inner_text())
        historical = self.page.locator('#council-history [data-member-id="council-fixture-historical"]')
        self.assertIn('Не входит в действующий Совет', historical.inner_text())
        self.assertEqual(historical.locator('.council-stance').inner_text(), 'Позиция по Стене не установлена')
        self.assertEqual(historical.locator('.faction-shield').count(), 0)
        self.assertEqual(self.page.locator('#royal-council a[href^="javascript:"]').count(), 0)
        link = genn.locator('.council-source-links a').first
        self.assertEqual(link.get_attribute('rel'), 'noopener noreferrer')
        self.assertTrue(link.get_attribute('href').startswith('https://'))
        self.page.evaluate("window.fixtureData.royalCouncil.members.find(m=>m.id==='council-fixture-genn').stance='support'; window.dispatchEvent(new CustomEvent('gilneas-data-changed'))")
        self.assertEqual(genn.locator('.council-stance').inner_text(), 'Поддерживает строительство Стены')
        genn.locator('[data-council-noble]').click()
        self.assertEqual(self.page.evaluate("window.calls.filter(c=>c[0]==='noble')"), [['noble', 'noble-genn']])
        self.assertFalse(self.page.locator('#royal-council').evaluate('e=>e.open'))
        self.clean()

    def test_03_assign_new_house_move_to_neutral_and_toggle_existing_person_advisor_through_validated_full_commit(self):
        data = snapshot()
        data['royalCouncil'] = {'version': 1, 'members': [assignment(sources=[45, 46], title='', extension={'flag': False, 'blank': ''})],
                                'authorCouncilNote': '  literal council metadata  '}
        self.boot(data)
        self.page.evaluate("window.fixtureData.factions.push({id:'council-fixture-new-house',name:'Тестовый новый дом',color:'#123456',parent:'gilneas'}); window.dispatchEvent(new CustomEvent('gilneas-data-changed'))")
        original = self.page.evaluate('structuredClone(window.fixtureData)')
        self.open()
        self.page.locator('#council-add').click()
        self.page.locator('#council-kind').select_option('faction')
        self.page.locator('#council-faction').select_option('council-fixture-new-house')
        self.page.locator('#council-party').select_option('royalists')
        self.page.locator('#council-stance').select_option('unknown')
        self.page.locator('#council-note').fill('  Тестовая настройка без подтверждения лором  ')
        self.page.locator('#council-save').click()
        assigned = self.page.evaluate("window.fixtureData.royalCouncil.members.find(m=>m.refId==='council-fixture-new-house')")
        self.assertEqual(assigned['party'], 'royalists')
        self.assertTrue(assigned['active'])
        self.assertFalse(assigned['advisor'])
        self.assertTrue(assigned['id'].startswith('council-member-'))
        row = self.page.locator(f'.council-rosters [data-member-id="{assigned["id"]}"]')
        self.assertEqual(row.locator('.faction-shield').get_attribute('data-faction-id'), 'council-fixture-new-house')
        row.locator('[data-council-edit]').click()
        self.page.locator('#council-party').select_option('neutral')
        self.page.locator('#council-save').click()
        self.assertEqual(self.page.locator('.council-party[data-party="neutral"]').locator(f'[data-member-id="{assigned["id"]}"]').count(), 1)
        genn = self.page.locator('.council-rosters [data-member-id="council-fixture-genn"]')
        genn.locator('[data-council-edit]').click()
        self.page.locator('label:has(#council-advisor)').click()
        self.page.locator('#council-save').click()
        self.assertEqual(genn.locator('.council-advisor-badge').inner_text(), 'Королевский советник')
        committed = self.page.evaluate('window.fixtureData')
        edited = next(m for m in committed['royalCouncil']['members'] if m['id'] == 'council-fixture-genn')
        self.assertEqual(edited['sources'], [45, 46])
        self.assertEqual(edited['title'], '')
        self.assertEqual(edited['extension'], {'flag': False, 'blank': ''})
        self.assertEqual(committed['royalCouncil']['authorCouncilNote'], original['royalCouncil']['authorCouncilNote'])
        for field in original:
            if field != 'royalCouncil':
                self.assertEqual(committed[field], original[field], field)
        self.assertEqual(json.loads(self.page.evaluate('key=>localStorage.getItem(key)', STORAGE_KEY)), committed)
        self.assertEqual(self.page.evaluate("window.calls.filter(c=>c[0]==='commit').length"), 3)
        self.assertEqual(self.page.evaluate("window.calls.filter(c=>c[0]==='toast').length"), 3)
        self.clean()

    def test_04_independent_literal_person_create_edit_delete_reload_and_full_json_round_trip_keep_sources(self):
        self.boot()
        self.open()
        self.page.locator('#council-add').click()
        self.page.locator('#council-kind').select_option('person')
        self.page.locator('#council-person').select_option('')
        payload = '  <script>window.councilExecuted=1</script><img src=x onerror=window.councilExecuted=2>  '
        self.page.locator('#council-name').fill(payload)
        self.page.locator('#council-member-title').fill('  Тестовый отдельный советник  ')
        self.page.locator('#council-party').select_option('internationalists')
        self.page.locator('#council-stance').select_option('oppose')
        self.page.locator('label:has(#council-advisor)').click()
        self.page.locator('#council-note').fill('  <script>window.councilExecuted=3</script>  ')
        self.page.locator('#council-save').click()
        created = self.page.evaluate('window.fixtureData.royalCouncil.members[0]')
        self.assertEqual(created['name'], payload)
        self.assertNotIn('refId', created)
        self.assertTrue(created['advisor'])
        self.assertEqual(len(self.page.evaluate('window.fixtureData.nobles')), 2)
        row = self.page.locator(f'.council-rosters [data-member-id="{created["id"]}"]')
        self.assertIn('<script>', row.locator('.council-member-name').inner_text())
        self.assertEqual(row.locator('script, img').count(), 0)
        self.assertIsNone(self.page.evaluate('window.councilExecuted'))
        data = self.page.evaluate('window.fixtureData')
        source_ids = [source['id'] for source in data['sources']]
        exported = self.page.evaluate('window.fixtureExport()')
        self.assertEqual(json.loads(exported), data)
        self.page.evaluate('text=>window.fixtureImport(text)', exported)
        self.boot(reload=True)
        self.open()
        row = self.page.locator(f'.council-rosters [data-member-id="{created["id"]}"]')
        row.locator('[data-council-edit]').click()
        self.page.locator('#council-name').fill('  Самостоятельный человек после редактирования  ')
        self.page.locator('#council-member-title').fill('')
        self.page.locator('#council-note').fill('')
        self.page.locator('#council-party').select_option('neutral')
        self.page.locator('label:has(#council-advisor)').click()
        self.page.locator('#council-save').click()
        edited = self.page.evaluate('window.fixtureData.royalCouncil.members[0]')
        self.assertEqual(edited['name'], '  Самостоятельный человек после редактирования  ')
        self.assertEqual(edited['title'], '')
        self.assertEqual(edited['note'], '')
        self.assertFalse(edited['advisor'])
        self.assertEqual(edited['id'], created['id'])
        self.assertNotIn('refId', edited)
        self.page.evaluate('window.fixtureConfirmValue=false')
        row.locator('[data-council-remove]').click()
        self.assertEqual(self.page.evaluate('window.fixtureData.royalCouncil.members.length'), 1)
        self.assertEqual(self.page.evaluate("window.calls.filter(c=>c[0]==='confirm').length"), 1)
        self.page.evaluate('window.fixtureConfirmValue=true')
        row.locator('[data-council-remove]').click()
        self.assertEqual(self.page.evaluate('window.fixtureData.royalCouncil.members.length'), 0)
        self.assertEqual(self.page.evaluate('window.fixtureData.sources.map(s=>s.id)'), source_ids)
        self.assertEqual(self.page.evaluate('window.fixtureData.nobles.length'), 2)
        self.assertIsNone(self.page.evaluate('window.councilExecuted'))
        self.boot(reload=True)
        self.open()
        self.assertEqual(self.page.locator('.council-member').count(), 0)
        self.assertEqual(self.page.evaluate('window.fixtureData.sources.map(s=>s.id)'), source_ids)
        self.clean()

    def test_05_live_registry_refresh_preserves_unsaved_draft_and_deleted_record_cannot_resurrect(self):
        data = snapshot()
        data['royalCouncil'] = {'version': 1, 'members': [assignment(note='Original')], 'metadata': {'blank': '', 'flag': False}}
        self.boot(data)
        self.open()
        row = self.page.locator('.council-rosters [data-member-id="council-fixture-genn"]')
        row.locator('[data-council-edit]').click()
        self.page.locator('#council-note').fill('  Несохранённая авторская заметка  ')
        self.page.locator('#council-party').select_option('neutral')
        self.page.locator('#council-note').focus()
        self.page.evaluate("""() => {
            window.fixtureData.factions.push({id:'council-fixture-later-house',name:'Позднее добавленный тестовый дом',color:'#554433',parent:'gilneas'});
            window.fixtureData.nobles.push({id:'council-fixture-later-noble',name:'Позднее импортированный тестовый персонаж',title:'Тест',house:null});
            window.dispatchEvent(new CustomEvent('gilneas-data-changed'));
        }""")
        self.assertEqual(self.page.locator('#council-note').input_value(), '  Несохранённая авторская заметка  ')
        self.assertEqual(self.page.locator('#council-party').input_value(), 'neutral')
        self.assertEqual(self.page.locator('#council-person').input_value(), 'noble-genn')
        self.assertEqual(self.page.locator('#council-person option[value="council-fixture-later-noble"]').count(), 1)
        self.assertEqual(self.page.locator('#council-faction option[value="council-fixture-later-house"]').count(), 1)
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'council-note')
        self.page.evaluate("window.fixtureData.royalCouncil.members=[]; window.dispatchEvent(new CustomEvent('gilneas-data-changed'))")
        self.assertTrue(self.page.locator('#council-form-error').is_visible())
        self.assertIn('удалён', self.page.locator('#council-form-error').inner_text())
        self.assertTrue(self.page.locator('#council-save').is_disabled())
        self.assertEqual(self.page.locator('#council-note').input_value(), '  Несохранённая авторская заметка  ')
        self.assertEqual(self.page.evaluate('window.fixtureData.royalCouncil.members.length'), 0)
        self.page.locator('#council-cancel').click()
        self.page.locator('#council-add').click()
        self.assertTrue(self.page.locator('#council-save').is_enabled())
        self.page.locator('#council-person').select_option('council-fixture-later-noble')
        self.page.locator('#council-note').fill('Связь не должна молча превращаться в отдельного человека')
        self.page.evaluate("window.fixtureData.nobles=window.fixtureData.nobles.filter(n=>n.id!=='council-fixture-later-noble'); window.dispatchEvent(new CustomEvent('gilneas-data-changed'))")
        self.assertEqual(self.page.locator('#council-person').input_value(), 'council-fixture-later-noble')
        missing_option = self.page.locator('#council-person option[value="council-fixture-later-noble"]').evaluate('e=>({disabled:e.disabled,text:e.textContent})')
        self.assertTrue(missing_option['disabled'], missing_option)
        self.page.locator('#council-save').click()
        self.assertIn('ссылка', self.page.locator('#council-form-error').inner_text())
        self.assertEqual(self.page.evaluate('window.fixtureData.royalCouncil.members.length'), 0)
        self.clean()

    def test_06_failed_import_or_parent_commit_keeps_exact_storage_and_form_and_optional_literals(self):
        data = snapshot()
        data['royalCouncil'] = {'version': 1, 'members': [assignment(note='', title='', name='', sources=[], advisor=False, active=True)],
                                'customMetadata': {'empty': '', 'flag': False}}
        del data['royalCouncil']['members'][0]['title']
        del data['royalCouncil']['members'][0]['basis']
        self.boot(data)
        self.page.evaluate('window.fixtureCommit(window.fixtureData)')
        before = self.page.evaluate('window.fixtureData')
        saved = self.page.evaluate('key=>localStorage.getItem(key)', STORAGE_KEY)
        self.open()
        self.page.locator('.council-rosters [data-member-id="council-fixture-genn"] [data-council-edit]').click()
        self.page.locator('#council-note').fill('  draft retained after failed parent validation  ')
        self.page.evaluate('window.rejectCommit=true')
        self.page.locator('#council-save').click()
        self.assertTrue(self.page.locator('#council-form').is_visible())
        self.assertIn('до записи', self.page.locator('#council-form-error').inner_text())
        self.assertEqual(self.page.locator('#council-note').input_value(), '  draft retained after failed parent validation  ')
        self.assertEqual(self.page.evaluate('window.fixtureData'), before)
        self.assertEqual(self.page.evaluate('key=>localStorage.getItem(key)', STORAGE_KEY), saved)
        self.page.evaluate('window.rejectCommit=false')
        for patch in [{'advisor': 'false'}, {'active': None}, {'refId': 'greymane'}, {'sources': ['45']}, {'title': None}, {'basis': False}]:
            malformed = copy.deepcopy(before)
            malformed['royalCouncil']['members'][0].update(patch)
            result = self.page.evaluate("""text=>{try{window.fixtureImport(text);return {accepted:true};}catch(error){return {accepted:false,message:error.message};}}""", json.dumps(malformed))
            self.assertFalse(result['accepted'], patch)
            self.assertEqual(self.page.evaluate('window.fixtureData'), before)
            self.assertEqual(self.page.evaluate('key=>localStorage.getItem(key)', STORAGE_KEY), saved)
        self.page.locator('#council-note').fill('')
        self.page.locator('#council-save').click()
        edited = self.page.evaluate('window.fixtureData.royalCouncil.members[0]')
        self.assertEqual(edited['name'], '')
        self.assertNotIn('title', edited)
        self.assertEqual(edited['note'], '')
        self.assertEqual(edited['sources'], [])
        self.assertFalse(edited['advisor'])
        self.assertNotIn('basis', edited)
        self.clean()

    def test_07_native_close_keyboard_focus_return_and_queued_close_do_not_erase_reopened_editor(self):
        self.boot()
        self.open()
        self.page.locator('#council-add').click()
        self.page.locator('#council-name').focus()
        self.page.keyboard.type('  Клавиатурное имя  ')
        self.assertEqual(self.page.locator('#council-name').input_value(), '  Клавиатурное имя  ')
        self.page.keyboard.press('Tab')
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'council-member-title')
        outline = self.page.locator('#council-member-title').evaluate('e=>({style:getComputedStyle(e).outlineStyle,width:getComputedStyle(e).outlineWidth})')
        self.assertEqual(outline['style'], 'solid')
        self.assertEqual(outline['width'], '2px')
        self.page.keyboard.press('Escape')
        self.assertFalse(self.page.locator('#royal-council').evaluate('e=>e.open'))
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'council-open')
        self.page.wait_for_function('document.querySelector("#council-form").hidden', polling=20)
        self.assertTrue(self.page.locator('#council-form').evaluate('e=>e.hidden'))
        self.open()
        self.page.locator('#council-add').click()
        self.page.locator('#council-name').fill('Новый несохранённый текст после открытия')
        self.page.evaluate("""() => {
            const dialog=document.querySelector('#royal-council'); dialog.close(); window.councilUI.open();
        }""")
        self.page.wait_for_timeout(100)
        self.assertTrue(self.page.locator('#royal-council').evaluate('e=>e.open'))
        self.assertTrue(self.page.locator('#council-form').is_visible())
        self.assertEqual(self.page.locator('#council-name').input_value(), 'Новый несохранённый текст после открытия')
        self.page.locator('#council-close').click()
        self.assertFalse(self.page.locator('#royal-council').evaluate('e=>e.open'))
        self.assertEqual(self.page.evaluate('document.activeElement.id'), 'council-open')
        self.page.wait_for_function('document.querySelector("#council-form").hidden', polling=20)
        self.assertTrue(self.page.locator('#council-form').evaluate('e=>e.hidden'))
        self.assertEqual(self.page.evaluate('window.fixtureData.royalCouncil ?? null'), None)
        self.clean()

    def test_08_mobile_stacks_parties_preserves_royal_surfaces_44px_targets_and_last_save_access(self):
        self.boot(size={'width': 390, 'height': 844})
        self.open()
        geometry = self.page.locator('#royal-council').evaluate("""dialog=>{
            const r=dialog.getBoundingClientRect(),c=getComputedStyle(dialog),body=dialog.querySelector('.council-body');
            return {width:r.width,height:r.height,overflow:dialog.scrollWidth>dialog.clientWidth+1,
                background:c.backgroundColor,bodyOverflow:getComputedStyle(body).overflowY,
                parties:[...dialog.querySelectorAll('.council-party')].map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width};}),
                shield:[...dialog.querySelectorAll('.faction-shield')].map(e=>{const r=e.getBoundingClientRect();return {width:r.width,height:r.height};})};
        }""")
        self.assertLessEqual(geometry['width'], 390)
        self.assertLessEqual(geometry['height'], 828)
        self.assertFalse(geometry['overflow'], geometry)
        self.assertEqual(geometry['background'], 'rgb(26, 29, 31)')
        self.assertEqual(geometry['bodyOverflow'], 'auto')
        self.assertEqual(geometry['parties'][0]['x'], geometry['parties'][1]['x'])
        self.assertGreater(geometry['parties'][1]['y'], geometry['parties'][0]['y'])
        self.assertGreaterEqual(geometry['parties'][0]['width'], 300)
        self.page.locator('#council-add').click()
        self.page.locator('#council-name').fill('  Тестовое мобильное назначение  ')
        self.page.locator('#council-note').fill('Мобильный текст ' * 80)
        self.page.locator('#council-save').scroll_into_view_if_needed()
        dimensions = self.page.locator('#royal-council button:visible, #royal-council input:not([type=checkbox]):visible, #royal-council select:visible, #royal-council label.council-check:visible').evaluate_all("""nodes=>nodes.map(e=>{
            const r=e.getBoundingClientRect();return {id:e.id||e.textContent.slice(0,30),width:r.width,height:r.height};
        })""")
        for control in dimensions:
            self.assertGreaterEqual(control['height'], 44, control)
            self.assertGreaterEqual(control['width'], 44, control)
        access = self.page.locator('#council-save').evaluate("""save=>{
            const r=save.getBoundingClientRect(),head=document.querySelector('#royal-council > .dialog-head').getBoundingClientRect();
            const p=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
            return {bottom:r.bottom,top:r.top,headBottom:head.bottom,hit:!!p&&save.contains(p)};
        }""")
        self.assertLessEqual(access['bottom'], 844)
        self.assertGreaterEqual(access['top'], access['headBottom'])
        self.assertTrue(access['hit'], access)
        self.page.screenshot(path=str(ARTIFACTS / 'mobile-editor.png'))
        self.page.locator('#council-save').click()
        self.assertEqual(self.page.evaluate('window.fixtureData.royalCouncil.members[0].name'), '  Тестовое мобильное назначение  ')
        self.page.locator('#council-close').click()
        self.boot(size={'width': 844, 'height': 390})
        self.open()
        self.page.locator('#council-add').click()
        self.page.locator('#council-name').fill('Тестовое назначение в landscape')
        self.page.locator('#council-save').scroll_into_view_if_needed()
        landscape = self.page.locator('#royal-council').evaluate("""dialog=>{
            const r=dialog.getBoundingClientRect(),save=dialog.querySelector('#council-save').getBoundingClientRect();
            return {height:r.height,saveBottom:save.bottom,scrollOverflow:dialog.scrollWidth>dialog.clientWidth+1};
        }""")
        self.assertLessEqual(landscape['height'], 374)
        self.assertLessEqual(landscape['saveBottom'], 390)
        self.assertFalse(landscape['scrollOverflow'])
        self.page.locator('#council-save').click()
        self.assertEqual(self.page.evaluate('window.fixtureData.royalCouncil.members.length'), 1)
        self.page.screenshot(path=str(ARTIFACTS / 'landscape-council.png'))
        self.clean()

    def test_09_real_parent_toolbar_chronicle_crud_reload_and_native_confirmation_preserve_full_atlas(self):
        self.page.unroute('**/assets/js/app.mjs')
        data = snapshot()
        self.page.route('**/assets/data/atlas.json', lambda route: route.fulfill(
            status=200, content_type='application/json', body=json.dumps(data)))
        self.page.goto(self.url + '/index.html', wait_until='networkidle')
        self.page.wait_for_function('window.gilneasApp?.ready', timeout=30000, polling=50)
        self.page.wait_for_function("document.querySelector('#base-map').complete && document.querySelector('#base-map').naturalWidth>0", polling=50)
        original = self.page.evaluate('window.gilneasApp.getData()')
        self.page.locator('#editor-open').click()
        self.page.locator('label:has(#editing-enabled)').click()
        self.page.locator('[data-close=editor]').click()
        self.page.locator('#chronicle-open').click()
        self.page.locator('#chronicle-council').click()
        self.assertTrue(self.page.locator('#royal-council').evaluate('e=>e.open'))
        self.assertFalse(self.page.locator('#chronicle').evaluate('e=>e.open'))
        self.page.locator('#council-add').click()
        self.page.locator('#council-name').fill('  Только тестовый участник реального bootstrap  ')
        self.page.locator('#council-save').click()
        saved = self.page.evaluate('window.gilneasApp.getData()')
        self.assertEqual(saved['royalCouncil']['members'][0]['name'], '  Только тестовый участник реального bootstrap  ')
        for field in original:
            if field != 'royalCouncil':
                self.assertEqual(saved[field], original[field], field)
        self.assertEqual(json.loads(self.page.evaluate("localStorage.getItem('gilneas-atlas-draft-v1')")), saved)
        self.page.reload(wait_until='networkidle')
        self.page.wait_for_function('window.gilneasApp?.ready', timeout=30000, polling=50)
        self.page.locator('#editor-open').click()
        self.page.locator('label:has(#editing-enabled)').click()
        self.page.locator('[data-close=editor]').click()
        self.page.locator('#council-open').click()
        self.assertEqual(self.page.locator('.council-member').count(), 1)
        self.page.locator('[data-council-remove]').click()
        self.assertTrue(self.page.locator('#confirmation').evaluate('e=>e.open'))
        self.page.locator('#confirm-no').click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData().royalCouncil.members.length'), 1)
        self.page.locator('[data-council-remove]').click()
        self.page.locator('#confirm-yes').click()
        self.assertEqual(self.page.evaluate('window.gilneasApp.getData().royalCouncil.members.length'), 0)
        self.assertTrue(self.page.locator('#royal-council').evaluate('e=>e.open'))
        self.page.screenshot(path=str(ARTIFACTS / 'real-bootstrap-council.png'))
        self.clean()

    def test_10_existing_inactive_linked_person_is_editable_but_not_activated_by_render_or_house_party(self):
        data = snapshot()
        data['sources'].append({'id': 'council-fixture-literal-source', 'title': '<script>literal archive title</script>',
                                'url': 'https://example.com/archive?literal=%3Cscript%3E'})
        data['royalCouncil'] = {'version': 1, 'members': [
            assignment(id='council-fixture-greymane', kind='faction', refId='greymane', party='royalists'),
            assignment(party='neutral', advisor=False),
            assignment(id='council-fixture-inactive-darius', refId='noble-darius', party='neutral', active=False, advisor=True,
                       sources=[46, 'council-fixture-literal-source'], note='Только тестовая историческая запись.'),
        ]}
        self.boot(data)
        self.open()
        self.assertEqual(self.page.locator('.council-rosters [data-member-id="council-fixture-genn"] .council-party-badge').inner_text(), 'Нейтралы')
        self.assertEqual(self.page.locator('.council-rosters [data-member-id="council-fixture-inactive-darius"]').count(), 0)
        self.page.locator('label:has(#council-show-history)').click()
        row = self.page.locator('#council-history [data-member-id="council-fixture-inactive-darius"]')
        self.assertEqual(row.locator('.faction-shield').get_attribute('data-faction-id'), 'crowley')
        self.assertEqual(row.locator('.council-source-links a').count(), 2)
        self.assertIn('<script>literal archive title</script>', row.locator('.council-source-links').inner_text())
        self.assertEqual(row.locator('script').count(), 0)
        row.locator('[data-council-edit]').click()
        self.assertFalse(self.page.locator('#council-active').is_checked())
        self.assertTrue(self.page.locator('#council-advisor').is_checked())
        self.assertEqual(self.page.locator('#council-person option[value="noble-darius"]').count(), 1)
        self.page.locator('#council-note').fill('  Историческая заметка изменена без активации  ')
        self.page.locator('#council-save').click()
        saved = self.page.evaluate("window.fixtureData.royalCouncil.members.find(m=>m.id==='council-fixture-inactive-darius')")
        self.assertFalse(saved['active'])
        self.assertEqual(saved['sources'], [46, 'council-fixture-literal-source'])
        self.assertEqual(self.page.locator('.council-rosters [data-member-id="council-fixture-inactive-darius"]').count(), 0)
        self.assertEqual(row.count(), 1)
        row.locator('[data-council-edit]').click()
        self.page.locator('label:has(#council-active)').click()
        self.page.locator('#council-save').click()
        self.assertEqual(row.count(), 0)
        self.assertEqual(self.page.locator('.council-rosters [data-member-id="council-fixture-inactive-darius"]').count(), 1)
        self.assertEqual(self.page.evaluate('window.fixtureData.nobles.length'), 2)
        self.clean()

    def test_11_render_keeps_keyboard_focus_on_existing_member_action_not_the_dialog_root(self):
        data = snapshot()
        data['royalCouncil'] = {'version': 1, 'members': [assignment()]}
        self.boot(data)
        self.open()
        action = self.page.locator('.council-rosters [data-council-edit="council-fixture-genn"]')
        action.focus()
        self.page.evaluate("window.fixtureData.royalCouncil.members[0].note='Live external edit';window.dispatchEvent(new CustomEvent('gilneas-data-changed'))")
        self.assertEqual(self.page.evaluate('document.activeElement.dataset.councilEdit'), 'council-fixture-genn')
        self.clean()


if __name__ == '__main__':
    unittest.main()
