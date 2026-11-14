import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeData, saveDraft } from '../assets/js/model.mjs';
import { deriveNobleProfile } from '../assets/js/noble-profile.mjs';

const fixture = () => ({
  version: 1,
  meta: { width: 100, height: 100 },
  factions: [
    { id: 'realm', name: 'Королевство', color: '#123456', parent: null, ruler: 'Король' },
    { id: 'house', name: 'Дом', color: '#654321', parent: 'realm', ruler: 'Лорд' },
  ],
  locations: [{ id: 'estate', name: 'Усадьба', x: 10, y: 20, faction: 'house', owner: '', objects: [] }],
  nobles: [{ id: 'lord', name: 'Лорд', house: 'house' }],
  sources: [],
  territories: [],
});

test('noble names must be nonempty literal strings before normalization or storage', () => {
  for (const value of ['', ' \t\n ', null, {}, [], 42, false, undefined]) {
    const raw = fixture();
    raw.nobles[0].name = value;
    const before = structuredClone(raw), writes = [];
    assert.throws(() => normalizeData(raw), /имя.*знат|имя.*персонаж|noble.*name/i);
    assert.throws(() => saveDraft({ setItem: (...args) => writes.push(args) }, raw), /имя.*знат|имя.*персонаж|noble.*name/i);
    assert.deepEqual(writes, []);
    assert.deepEqual(raw, before);
  }
});

test('optional noble houses resolve exact existing faction IDs before storage', () => {
  for (const house of ['missing-house', 1, '', {}, [], false]) {
    const raw = fixture();
    raw.nobles[0].house = house;
    const before = structuredClone(raw), writes = [];
    assert.throws(() => normalizeData(raw), /фракция.*персонаж|дом.*персонаж|noble.*house/i);
    assert.throws(() => saveDraft({ setItem: (...args) => writes.push(args) }, raw), /фракция.*персонаж|дом.*персонаж|noble.*house/i);
    assert.deepEqual(writes, []);
    assert.deepEqual(raw, before);
  }
});

const dossierTextFields = ['title', 'description', 'appearance', 'socialStatus', 'overlordText', 'allegiance', 'holdingsNote', 'wowpediaUrl'];

test('present noble dossier text fields reject non-string values before storage', () => {
  for (const field of dossierTextFields) {
    for (const value of [null, {}, [], 42, false, undefined]) {
      const raw = fixture();
      raw.nobles[0][field] = value;
      const before = structuredClone(raw), writes = [];
      assert.throws(() => normalizeData(raw), new RegExp(`поле персонажа: ${field}`));
      assert.throws(() => saveDraft({ setItem: (...args) => writes.push(args) }, raw), new RegExp(`поле персонажа: ${field}`));
      assert.deepEqual(writes, []);
      assert.deepEqual(raw, before);
    }
  }
});

test('published nullable or structured overlord metadata remains a valid snapshot', () => {
  for (const overlord of [null, '  Король  ', { id: 'king', name: '  Король  ', relation: 'Монарх' }]) {
    const raw = fixture();
    raw.nobles[0].overlord = overlord;
    assert.deepEqual(normalizeData(raw).nobles[0], raw.nobles[0]);
  }
});

test('missing house rulers never grant authority to ordinary members', () => {
  for (const ruler of [undefined, null, '', 'Другой лорд']) {
    const raw = fixture();
    if (ruler === undefined) delete raw.factions[1].ruler;
    else raw.factions[1].ruler = ruler;
    raw.nobles[0].role = 'court';
    raw.locations.push({ id: 'personal', name: 'Личное владение', x: 30, y: 40, faction: null, owner: 'Лорд', objects: [] });
    raw.locations[0].objects.push({ id: 'personal-forge', name: 'Личная кузница', owner: 'Лорд', type: 'building', faction: null });
    const before = structuredClone(raw), profile = deriveNobleProfile(raw, 'lord');
    assert.equal(profile.isSovereign, false);
    assert.equal(profile.suzerain, null);
    assert.deepEqual(profile.holdings.map(holding => [holding.id, holding.scope]), [['personal-forge', 'personal'], ['personal', 'personal']]);
    assert.deepEqual(raw, before);
  }
});

test('public noble derivation rejects blank or malformed names without claiming unowned estates', () => {
  for (const value of ['', ' \t\n ', null, undefined, {}, []]) {
    const raw = fixture();
    raw.nobles[0].name = value;
    raw.factions[0].ruler = value;
    raw.factions[1].ruler = value;
    const before = structuredClone(raw);
    assert.throws(() => deriveNobleProfile(raw, 'lord'), /имя.*персонаж|noble.*name/i);
    assert.deepEqual(raw, before);
  }
});

test('optional noble overlord metadata rejects malformed display references', () => {
  for (const overlord of [{}, { id: 'king', name: {} }, { id: 'king', name: '' }, { id: 'king', name: 'Король', relation: [] }, [], 42, false, undefined]) {
    const raw = fixture();
    raw.nobles[0].overlord = overlord;
    const writes = [];
    assert.throws(() => saveDraft({ setItem: (...args) => writes.push(args) }, raw), /поле персонажа: overlord/);
    assert.deepEqual(writes, []);
  }
});

test('minimal legacy nobles and absent optional fields retain exact literal text', () => {
  const raw = fixture();
  raw.nobles = [{ id: 'minimal', name: '  <script>Literal name</script>  ' }];
  assert.deepEqual(normalizeData(raw).nobles, raw.nobles);
  for (const house of [null, 'house']) {
    const noble = { id: 'literal', name: '  Лорд  ', house };
    for (const field of dossierTextFields) noble[field] = '  </script><b>Literal</b>  ';
    raw.nobles = [noble];
    assert.deepEqual(normalizeData(raw).nobles, raw.nobles);
  }
});
