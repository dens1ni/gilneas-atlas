import test from 'node:test';
import assert from 'node:assert/strict';
import * as model from '../assets/js/model.mjs';

function fixture() {
  return {
    version: 1,
    meta: { width: 3247, height: 4860, image: 'assets/maps/gilneas-enhanced.webp', inactiveMask: 'assets/maps/inactive-mask.png' },
    factions: [
      { id: 'gilneas', name: 'Гилнеас', color: '#9b3046', parent: null },
      { id: 'greymane', name: 'Дом Седогривов', color: '#c48a42', parent: 'gilneas' },
      { id: 'crowley', name: 'Дом Краули', color: '#477880', parent: 'gilneas' },
      { id: 'cadet', name: 'Младший дом', color: '#a48163', parent: 'crowley' },
      { id: 'dalaran', name: 'Даларан', color: '#8764ac', parent: null }
    ],
    locations: [{ id: 'city', name: 'Гилнеас', x: 1200, y: 3600, type: 'settlement', faction: 'greymane', owner: '', description: '', objects: [] }],
    territories: [{ id: 'city-land', faction: 'greymane', points: [[1100,3500],[1300,3500],[1300,3700],[1100,3700]] }],
    nobles: [],
    sources: []
  };
}

function memoryStorage(entries = []) {
  const store = new Map(entries);
  return {
    getItem: key => store.has(key) ? store.get(key) : null,
    setItem: (key, value) => { store.set(key, String(value)); },
    removeItem: key => { store.delete(key); }
  };
}

function building(patch = {}) {
  return { id: 'mill', type: 'building', name: 'Мельница', description: '', owner: '', modifiers: [], ...patch };
}

// A vertical first slice: incoming faction trees own their normalization.
test('sovereign influence includes differently colored vassals without changing their owners', async () => {
  const { normalizeData, sovereignOf, factionMembers } = await import('../assets/js/model.mjs');
  const data = normalizeData({
    version: 1,
    meta: { width: 3247, height: 4860 },
    factions: [
      { id: 'gilneas', name: 'Королевство Гилнеас', color: '#9b3046', parent: null },
      { id: 'greymane', name: 'Дом Седогривов', color: '#c48a42', parent: 'gilneas' },
      { id: 'crowley', name: 'Дом Краули', color: '#477880', parent: 'gilneas' },
      { id: 'dalaran', name: 'Королевство Даларан', color: '#8764ac', parent: null }
    ],
    locations: [{ id: 'city', name: 'Гилнеас', x: 1200, y: 3600, faction: 'greymane', owner: 'Генн Седогрив', objects: [] }],
    territories: [{ id: 'city-land', faction: 'greymane', points: [[1100,3500],[1300,3500],[1300,3700],[1100,3700]] }]
  });
  assert.equal(sovereignOf(data.factions, 'greymane'), 'gilneas');
  assert.deepEqual(factionMembers(data.factions, 'gilneas'), ['gilneas', 'greymane', 'crowley']);
  assert.equal(data.locations[0].faction, 'greymane');
  assert.equal(data.territories[0].faction, 'greymane');
  assert.equal(data.factions.find(f => f.id === 'greymane').color, '#c48a42');
});

test('selected houses include all of their descendants, not siblings or ancestors', () => {
  const data = model.normalizeData(fixture());
  assert.deepEqual(model.factionMembers(data.factions, 'crowley'), ['crowley', 'cadet']);
  assert.deepEqual(model.factionMembers(data.factions, 'cadet'), ['cadet']);
  assert.deepEqual(model.factionMembers(data.factions, 'gilneas'), ['gilneas', 'greymane', 'crowley', 'cadet']);
  assert.equal(model.sovereignOf(data.factions, 'cadet'), 'gilneas');
});

test('normalization rejects incompatible snapshot versions', () => {
  for (const version of [0, 2, '1', null, undefined]) {
    assert.throws(() => model.normalizeData({ ...fixture(), version }), /верси/i);
  }
  assert.equal(model.normalizeData(fixture()).version, 1);
});

test('normalization rejects nonnumeric or nonfinite map coordinates', () => {
  for (const coordinate of [NaN, Infinity, -Infinity, null, '', '12', false, [], {}]) {
    const raw = fixture();
    raw.locations[0].x = coordinate;
    assert.throws(() => model.normalizeData(raw), /точк|координат/i);
  }
  for (const dimension of [NaN, Infinity, -1, 0, '3247', null]) {
    const raw = fixture();
    raw.meta.width = dimension;
    assert.throws(() => model.normalizeData(raw), /размер/i);
  }
  for (const [x, y] of [[-1, 20], [3248, 20], [20, -1], [20, 4861]]) {
    const raw = fixture();
    Object.assign(raw.locations[0], { x, y });
    assert.throws(() => model.normalizeData(raw), /точк|координат/i);
  }
  for (const [x, y] of [[0, 0], [3247, 4860]]) {
    const raw = fixture();
    Object.assign(raw.locations[0], { x, y });
    const normalized = model.normalizeData(raw);
    assert.equal(normalized.locations[0].x, x);
    assert.equal(normalized.locations[0].y, y);
  }
});

test('normalization requires actual registry and object arrays', () => {
  for (const field of ['factions', 'locations', 'territories', 'nobles', 'sources']) {
    for (const value of [null, {}, 'records', false, 0]) {
      const raw = fixture();
      raw[field] = value;
      assert.throws(() => model.normalizeData(raw), /массив|реестр/i);
    }
  }
  for (const value of [null, {}, 'objects', false, 0]) {
    const raw = fixture();
    raw.locations[0].objects = value;
    assert.throws(() => model.normalizeData(raw), /массив/i);
  }
  const raw = fixture();
  delete raw.territories;
  delete raw.nobles;
  delete raw.sources;
  delete raw.locations[0].objects;
  const normalized = model.normalizeData(raw);
  assert.deepEqual(normalized.territories, []);
  assert.deepEqual(normalized.nobles, []);
  assert.deepEqual(normalized.sources, []);
  assert.deepEqual(normalized.locations[0].objects, []);
});

test('optional region labels must be arrays before a draft is stored', () => {
  const baseline = fixture();
  const storage = memoryStorage();
  model.saveDraft(storage, baseline);
  const stored = storage.getItem('gilneas-atlas-draft-v1');
  for (const labels of [null, {}, 'labels', false, 0]) {
    const raw = fixture();
    raw.meta.labels = labels;
    const before = structuredClone(raw);
    assert.throws(() => model.saveDraft(storage, raw), /массив.*labels/i);
    assert.equal(storage.getItem('gilneas-atlas-draft-v1'), stored);
    assert.deepEqual(raw, before);
  }
  assert.equal(Object.hasOwn(model.normalizeData(baseline).meta, 'labels'), false);
});

test('region label records validate coordinates and text without rewriting literals', () => {
  const label = { x: 0, y: 4860, text: '  </script>\n' + 'я'.repeat(20001), size: 15, future: { exact: true } };
  const cases = [null, [], 'label', {}, { ...label, x: '0' }, { ...label, y: null },
    { ...label, x: -1 }, { ...label, y: 4861 }, { ...label, text: {} },
    { ...label, size: '15' }, { ...label, size: 0 }];
  for (const invalid of cases) {
    const raw = fixture();
    raw.meta.labels = [invalid];
    const before = structuredClone(raw);
    assert.throws(() => model.normalizeData(raw), /метк|labels/i);
    assert.deepEqual(raw, before);
  }
  const raw = fixture();
  raw.meta.labels = [label, { x: 3247, y: 0, text: '' }];
  assert.deepEqual(model.deserializeSnapshot(model.serializeSnapshot(raw)).meta.labels, raw.meta.labels);
});

test('optional chronicle sections validate their array and readable shape before storage', () => {
  const baseline = fixture();
  const storage = memoryStorage();
  model.saveDraft(storage, baseline);
  const stored = storage.getItem('gilneas-atlas-draft-v1');
  const section = { title: '  Заголовок </script>  ', text: '\n' + 'я'.repeat(20001), future: { exact: true } };
  for (const chronicle of [null, {}, 'history', false, [null], [[]], ['history'], [{}],
    [{ ...section, title: {} }], [{ ...section, text: 42 }]]) {
    const raw = fixture();
    raw.meta.chronicle = chronicle;
    const before = structuredClone(raw);
    assert.throws(() => model.saveDraft(storage, raw), /chronicle|летопис/i);
    assert.equal(storage.getItem('gilneas-atlas-draft-v1'), stored);
    assert.deepEqual(raw, before);
  }
  assert.equal(Object.hasOwn(model.normalizeData(baseline).meta, 'chronicle'), false);
  const raw = fixture();
  raw.meta.chronicle = [section, { title: '', text: '' }];
  assert.deepEqual(model.deserializeSnapshot(model.serializeSnapshot(raw)).meta.chronicle, raw.meta.chronicle);
});

test('renderer citation collections validate exact source references before storage', () => {
  const raw = fixture();
  raw.sources = [{ id: 0 }, { id: 1 }, { id: '1' }, { id: '  book  ' }];
  raw.locations[0].objects = [building()];
  raw.nobles = [{ id: 'noble', name: 'Дворянин' }];
  raw.meta.chronicle = [{ title: 'Летопись', text: '  Текст  ' }];
  const records = data => [data.locations[0], data.locations[0].objects[0], data.nobles[0], data.meta.chronicle[0]];
  const storage = memoryStorage();
  model.saveDraft(storage, raw);
  const stored = storage.getItem('gilneas-atlas-draft-v1');
  for (let index = 0; index < records(raw).length; index++) {
    for (const sources of [null, {}, '  book  ', false, 0, [2], ['0'], ['book'], [null], [{}]]) {
      const bad = structuredClone(raw);
      records(bad)[index].sources = sources;
      const before = structuredClone(bad);
      assert.throws(() => model.saveDraft(storage, bad), /источник/i);
      assert.equal(storage.getItem('gilneas-atlas-draft-v1'), stored);
      assert.deepEqual(bad, before);
    }
  }
  for (const record of records(model.normalizeData(raw))) assert.equal(Object.hasOwn(record, 'sources'), false);
  for (const record of records(raw)) record.sources = [0, 1, '1', '  book  '];
  const restored = model.deserializeSnapshot(model.serializeSnapshot(raw));
  for (const record of records(restored)) assert.deepEqual(record.sources, [0, 1, '1', '  book  ']);
});

test('optional location aliases must contain literal strings safe to spread in search', () => {
  for (const aliases of [null, {}, 'alias', false, 0, [null], [{}], [1]]) {
    const raw = fixture();
    raw.locations[0].aliases = aliases;
    const before = structuredClone(raw);
    assert.throws(() => model.normalizeData(raw), /aliases|псевдоним/i);
    assert.deepEqual(raw, before);
  }
  const raw = fixture();
  assert.equal(Object.hasOwn(model.normalizeData(raw).locations[0], 'aliases'), false);
  raw.locations[0].aliases = ['', '  Город </script>\n' + 'я'.repeat(20001)];
  assert.deepEqual(model.deserializeSnapshot(model.serializeSnapshot(raw)).locations[0].aliases, raw.locations[0].aliases);
});

test('optional source readable fields require strings without editing text or IDs', () => {
  for (const field of ['title', 'url', 'canonicalUrl', 'quote', 'note']) {
    for (const value of [null, {}, [], 0, false]) {
      const raw = fixture();
      raw.sources = [{ id: '  book  ', [field]: value }];
      const before = structuredClone(raw);
      assert.throws(() => model.normalizeData(raw), /источник/i);
      assert.deepEqual(raw, before);
    }
  }
  const raw = fixture();
  const exact = '  </script>\n' + 'я'.repeat(20001);
  raw.sources = [{ id: 0 }, { id: '  book  ', title: exact, url: 'javascript:alert(1)',
    canonicalUrl: '  https://example.invalid/book  ', quote: exact, note: '', future: { keep: true } }];
  assert.deepEqual(model.deserializeSnapshot(model.serializeSnapshot(raw)).sources, raw.sources);
});

test('IDs are globally unique across nested atlas records', () => {
  const cases = [
    raw => { raw.locations[0].id = 'gilneas'; },
    raw => { raw.locations[0].objects = [building({ id: 'city' })]; },
    raw => { raw.locations.push({ ...raw.locations[0], id: 'port', objects: [building()] }); raw.locations[0].objects = [building()]; },
    raw => { raw.locations[0].objects = [building({ modifiers: [{ id: 'city-land', kind: 'bonus', text: 'Мука' }] })]; },
    raw => { raw.territories[0].id = 'crowley'; },
    raw => { raw.nobles = [{ id: 'city', name: 'Генн' }]; },
    raw => { raw.sources = [{ id: 'city', title: 'Справочник' }]; },
    raw => { raw.sources = [{ id: 1 }, { id: 1 }]; },
    raw => { raw.factions.push({ ...raw.factions[0] }); }
  ];
  for (const change of cases) {
    const raw = fixture();
    change(raw);
    const before = structuredClone(raw);
    assert.throws(() => model.normalizeData(raw), /ID/i);
    assert.deepEqual(raw, before);
  }
});

test('identifiers stay literal without truncating references', () => {
  for (const id of [1, null, '', 'x'.repeat(101)]) {
    const raw = fixture();
    raw.factions[0].id = id;
    assert.throws(() => model.normalizeData(raw), /ID/i);
  }
  for (const parent of [1, '', 'missing']) {
    const raw = fixture();
    raw.factions[1].parent = parent;
    assert.throws(() => model.normalizeData(raw), /сюзерен|родител|фракци/i);
  }
  const raw = fixture();
  raw.locations[0].id = '  city  ';
  raw.sources = [{ id: 0 }, { id: 1 }, { id: '1' }];
  raw.locations[0].provenance = { sources: [0, 1, '1'] };
  const normalized = model.normalizeData(raw);
  assert.equal(normalized.locations[0].id, '  city  ');
  assert.deepEqual(normalized.sources.map(source => source.id), [0, 1, '1']);
  const malformed = fixture();
  malformed.factions[1].parent = undefined;
  // An explicitly absent parent is normalized to a sovereign, not looked up.
  assert.equal(model.normalizeData(malformed).factions[1].parent, null);
  const objectRecord = fixture();
  objectRecord.locations[0].name = { label: 'bad' };
  assert.throws(() => model.normalizeData(objectRecord), /локаци/i);
});

test('nested objects normalize kinds without losing inherited ownership', () => {
  for (const type of ['unknown', '', null, undefined]) {
    const raw = fixture();
    raw.locations[0].objects = [building({ type })];
    assert.throws(() => model.normalizeData(raw), /тип.*объект|объект.*тип/i);
  }
  for (const kind of ['good', 'Bonus', '', null, undefined]) {
    const raw = fixture();
    raw.locations[0].objects = [building({ modifiers: [{ id: 'effect', kind, text: 'Доход' }] })];
    assert.throws(() => model.normalizeData(raw), /вид.*модификатор|модификатор.*вид/i);
  }
  for (const modifiers of [null, false, {}, 'bonus']) {
    const raw = fixture();
    raw.locations[0].objects = [building({ modifiers })];
    assert.throws(() => model.normalizeData(raw), /массив/i);
  }
  const raw = fixture();
  raw.locations[0].objects = [
    { id: 'mill', type: 'building', name: '  Мельница  ', modifiers: [{ id: 'bonus', kind: 'bonus', text: '  Доход\n ' }, { id: 'penalty', kind: 'penalty', text: '  Износ  ' }] },
    { id: 'ore', type: 'resource', name: 'Руда', faction: null, amount: 0 },
    { id: 'stone', type: 'landmark', name: 'Камень', faction: 'dalaran', custom: { era: 'до Стены' } }
  ];
  const normalized = model.normalizeData(raw);
  assert.equal(Object.hasOwn(normalized.locations[0].objects[0], 'faction'), false);
  assert.equal(normalized.locations[0].objects[0].owner, '');
  assert.equal(normalized.locations[0].objects[0].description, '');
  assert.equal(normalized.locations[0].objects[0].name, '  Мельница  ');
  assert.equal(normalized.locations[0].objects[0].modifiers[0].text, '  Доход\n ');
  assert.equal(normalized.locations[0].objects[1].faction, null);
  assert.equal(normalized.locations[0].objects[1].amount, 0);
  assert.deepEqual(normalized.locations[0].objects[2].custom, { era: 'до Стены' });
  const before = structuredClone(raw);
  normalized.locations[0].objects[0].modifiers[0].text = 'Изменено';
  assert.deepEqual(raw, before);
});

test('incoming object faction references must resolve in the incoming tree', () => {
  const raw = fixture();
  raw.locations[0].objects = [building({ faction: 'missing' })];
  const before = structuredClone(raw);
  assert.throws(() => model.normalizeData(raw), /фракци.*объект|объект.*фракци/i);
  assert.deepEqual(raw, before);
  raw.locations[0].objects[0].faction = undefined;
  assert.throws(() => model.normalizeData(raw), /фракци.*объект|объект.*фракци/i);
  raw.factions = [{ id: 'new-realm', name: 'Новая держава', parent: null, color: '#123456' }];
  raw.locations[0].faction = 'new-realm';
  raw.locations[0].objects[0].faction = 'new-realm';
  raw.territories[0].faction = 'new-realm';
  assert.equal(model.normalizeData(raw).locations[0].objects[0].faction, 'new-realm');
});

test('effective faction distinguishes inherited and explicitly independent objects', () => {
  assert.equal(typeof model.effectiveFaction, 'function');
  const location = fixture().locations[0];
  assert.equal(model.effectiveFaction(location, building()), 'greymane');
  assert.equal(model.effectiveFaction(location, building({ faction: null })), null);
  assert.equal(model.effectiveFaction(location, building({ faction: 'crowley' })), 'crowley');
  assert.equal(model.effectiveFaction({ ...location, faction: null }, building()), null);
  assert.equal(model.effectiveFaction(location), 'greymane');
  assert.equal(model.effectiveFaction(location, building({ faction: undefined })), undefined);
});

test('source references validate exact numeric or string IDs without editing provenance', () => {
  const raw = fixture();
  raw.sources = [{ id: 0, title: '  Источник  ', custom: { volume: 'II' } }, { id: 'book', title: 'Летопись' }];
  raw.locations[0].provenance = {
    confidence: '  Авторская оценка  ', chronology: 'Не точный год; после Второй войны',
    note: '  </script><script>alert(1)</script>\n', sources: [0, 'book'], future: { uncertain: true }
  };
  const before = structuredClone(raw);
  const result = model.normalizeData(raw);
  assert.deepEqual(result.locations[0].provenance, raw.locations[0].provenance);
  assert.deepEqual(result.sources, raw.sources);
  result.locations[0].provenance.future.uncertain = false;
  assert.deepEqual(raw, before);
  for (const unknown of [1, '0', 'missing', null, {}]) {
    const bad = structuredClone(raw);
    bad.locations[0].provenance.sources.push(unknown);
    assert.throws(() => model.normalizeData(bad), /источник/i);
  }
  for (const references of [null, 0, {}, 'book']) {
    const bad = structuredClone(raw);
    bad.locations[0].provenance.sources = references;
    assert.throws(() => model.normalizeData(bad), /массив.*источник/i);
  }
  raw.locations[0].provenance = { note: 'Сценарная реконструкция', unknownField: [1, 2] };
  assert.deepEqual(model.normalizeData(raw).locations[0].provenance, raw.locations[0].provenance);
});

test('point inclusion treats polygon edges as inside', () => {
  assert.equal(typeof model.inPolygon, 'function');
  const square = [[0, 0], [10, 0], [10, 10], [0, 10]];
  for (const point of [[5, 5], [0, 5], [10, 5], [5, 0], [5, 10], [0, 0], [10, 10]]) {
    assert.equal(model.inPolygon(point, square), true, JSON.stringify(point));
    assert.equal(model.inPolygon(point, square.toReversed()), true, JSON.stringify(point));
  }
  for (const point of [[-1, 5], [11, 5], [5, -1], [5, 11]]) assert.equal(model.inPolygon(point, square), false);
  const concave = [[0, 0], [10, 0], [10, 10], [5, 5], [0, 10]];
  assert.equal(model.inPolygon([5, 8], concave), false);
  assert.equal(model.inPolygon([8, 2], concave), true);
  assert.equal(model.inPolygon([7.5, 7.5], concave), true);
  assert.equal(model.inPolygon([1, 1], []), false);
});

test('polygon validation rejects malformed coordinates and zero-area shapes', () => {
  assert.equal(typeof model.validatePolygon, 'function');
  for (const points of [
    null, {}, [], [[0, 0]], [[0, 0], [10, 10]],
    [[0, 0], [1, 1], [2, 2]], [[0, 0], [0, 0], [10, 10]],
    [[0, 0], [10, 0], [0, null]], [[0, 0], [10, 0], [0, '10']],
    [[0, 0], [10, 0], [0, NaN]], [[0, 0], [10, 0], [0, Infinity]],
    [[0, 0], [10, 0], [0]], [[0, 0], [10, 0], [0, 10, 1]]
  ]) assert.throws(() => model.validatePolygon(points), /полигон|координат|вершин/i);
  const triangle = [[0, 0], [10, 0], [0, 10]];
  const before = structuredClone(triangle);
  assert.equal(model.validatePolygon(triangle), true);
  assert.equal(model.validatePolygon(triangle.toReversed()), true);
  assert.deepEqual(triangle, before);
  assert.equal(model.validatePolygon([[1.5, 1.5], [2.5, 1.5], [1.5, 2.5]]), true);
});

test('polygon validation rejects crossings and overlapping edges', () => {
  for (const points of [
    [[0, 0], [10, 10], [0, 8], [10, 0]],
    [[0, 0], [6, 0], [3, 0], [3, 3], [0, 3]],
    [[0, 0], [10, 0], [10, 10], [5, 0], [0, 10]],
    [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
  ]) assert.throws(() => model.validatePolygon(points), /полигон|пересеч|вершин/i);
  assert.equal(model.validatePolygon([[0, 0], [5, 0], [10, 0], [10, 10], [0, 10]]), true);
  assert.equal(model.validatePolygon([[0, 0], [10, 0], [10, 10], [5, 5], [0, 10]]), true);
});

test('territories validate factions and map-bounded polygon geometry', () => {
  const invalid = [
    territory => { territory.faction = 'missing'; },
    territory => { delete territory.faction; },
    territory => { territory.faction = null; },
    territory => { territory.points = []; },
    territory => { territory.points = [[0, 0], [10, 0]]; },
    territory => { territory.points = [[0, 0], [10, 0], [0, Infinity]]; },
    territory => { territory.points = [[0, 0], [10, 0], [-1, 10]]; },
    territory => { territory.points = [[0, 0], [3248, 0], [0, 10]]; },
    territory => { territory.points = [[0, 0], [10, 0], [0, 4861]]; },
    territory => { territory.points = [[0, 0], [10, 10], [0, 8], [10, 0]]; }
  ];
  for (const change of invalid) {
    const raw = fixture();
    change(raw.territories[0]);
    const before = structuredClone(raw);
    assert.throws(() => model.normalizeData(raw), /территор|полигон|вершин|фракци|координат/i);
    assert.deepEqual(raw, before);
  }
  const raw = fixture();
  raw.territories[0].points = [[0, 0], [3247, 0], [3247, 4860], [0, 4860]];
  raw.territories[0].name = '  Земли </script>  ';
  raw.territories[0].future = { canonical: false };
  const result = model.normalizeData(raw);
  assert.deepEqual(result.territories, raw.territories);
  result.territories[0].points[0][0] = 1;
  assert.equal(raw.territories[0].points[0][0], 0);
});

test('location updates normalize immutable patches while retaining nested objects', () => {
  assert.equal(typeof model.updateLocation, 'function');
  const data = model.normalizeData(fixture());
  data.locations[0].objects = [building({ modifiers: [{ id: 'income', kind: 'bonus', text: '  Доход  ' }] })];
  data.locations[0].provenance = { chronology: 'После Второй войны', note: 'Без точного года' };
  const before = structuredClone(data);
  const patch = { x: 1300, faction: 'crowley', description: '  </script><img src=x onerror=alert(1)>  ' };
  const patchBefore = structuredClone(patch);
  const result = model.updateLocation(data, 'city', patch);
  assert.notEqual(result, data);
  assert.notEqual(result.locations[0].objects, data.locations[0].objects);
  assert.deepEqual(result.locations[0].objects, data.locations[0].objects);
  assert.deepEqual(result.locations[0].provenance, data.locations[0].provenance);
  assert.deepEqual(result.territories, data.territories);
  assert.equal(result.locations[0].description, patch.description);
  assert.equal(result.locations[0].x, 1300);
  assert.equal(result.locations[0].faction, 'crowley');
  assert.deepEqual(data, before);
  assert.deepEqual(patch, patchBefore);
  result.locations[0].objects[0].modifiers[0].text = 'Изменено';
  assert.deepEqual(data, before);
  for (const bad of [{ faction: 'missing' }, { x: 4000 }, { objects: null }, { id: 'renamed' }]) {
    assert.throws(() => model.updateLocation(data, 'city', bad));
    assert.deepEqual(data, before);
  }
  assert.throws(() => model.updateLocation(data, 'missing', { name: 'Неизвестная' }), /локаци/i);
  assert.deepEqual(model.updateLocation(data, 'city', { objects: [] }).locations[0].objects, []);
});

test('removing a location never regenerates territories or alters other records', () => {
  assert.equal(typeof model.removeLocation, 'function');
  const data = model.normalizeData(fixture());
  data.locations[0].objects = [building({ modifiers: [{ id: 'income', kind: 'bonus', text: 'Доход' }] })];
  data.locations.push({ ...structuredClone(data.locations[0]), id: 'port', objects: [] });
  const before = structuredClone(data);
  const result = model.removeLocation(data, 'city');
  assert.deepEqual(result.locations.map(location => location.id), ['port']);
  assert.deepEqual(result.territories, data.territories);
  assert.deepEqual(result.factions, data.factions);
  assert.deepEqual(data, before);
  assert.throws(() => model.removeLocation(data, 'missing'), /локаци/i);
  assert.deepEqual(data, before);
});

test('faction upserts validate parent relationships atomically', () => {
  assert.equal(typeof model.upsertFaction, 'function');
  const data = model.normalizeData(fixture());
  data.factions[2].provenance = { note: '  Реконструкция  ' };
  const before = structuredClone(data);
  const added = model.upsertFaction(data, { id: 'new-house', name: '  Новый дом  ', color: '#aAbBcC', parent: 'cadet', extra: { established: 'После войны' } });
  assert.equal(added.factions.at(-1).id, 'new-house');
  assert.equal(added.factions.at(-1).name, '  Новый дом  ');
  assert.deepEqual(model.factionMembers(added.factions, 'crowley'), ['crowley', 'cadet', 'new-house']);
  assert.equal(model.sovereignOf(added.factions, 'new-house'), 'gilneas');
  const changed = model.upsertFaction(data, { id: 'crowley', parent: 'dalaran', color: '#aAbBcC' });
  assert.equal(model.sovereignOf(changed.factions, 'cadet'), 'dalaran');
  assert.equal(changed.factions.find(faction => faction.id === 'crowley').name, 'Дом Краули');
  assert.deepEqual(changed.factions.find(faction => faction.id === 'crowley').provenance, { note: '  Реконструкция  ' });
  assert.deepEqual(changed.locations, data.locations);
  assert.deepEqual(changed.territories, data.territories);
  for (const faction of [
    { id: 'crowley', parent: 'missing' }, { id: 'crowley', parent: 'crowley' },
    { id: 'gilneas', parent: 'cadet' }, { id: 'crowley', parent: 'cadet' },
    { id: 'crowley', color: 'red' }, { id: 'city', name: 'Collision', parent: null, color: '#123456' }
  ]) assert.throws(() => model.upsertFaction(data, faction));
  assert.deepEqual(data, before);
  added.factions.at(-1).extra.established = 'Изменено';
  assert.deepEqual(data, before);
});

test('faction deletion refuses every referenced house without modifying data', () => {
  assert.equal(typeof model.deleteFaction, 'function');
  const references = [
    raw => { raw.locations[0].faction = 'cadet'; },
    raw => { raw.locations[0].objects = [building({ faction: 'cadet' })]; },
    raw => { raw.territories[0].faction = 'cadet'; },
    raw => { raw.factions[1].parent = 'cadet'; }
  ];
  for (const reference of references) {
    const raw = fixture();
    reference(raw);
    const data = model.normalizeData(raw);
    const before = structuredClone(data);
    assert.throws(() => model.deleteFaction(data, 'cadet'), /использ|ссыл|завис/i);
    assert.deepEqual(data, before);
  }
  const data = model.normalizeData(fixture());
  const before = structuredClone(data);
  assert.throws(() => model.deleteFaction(data, 'gilneas'), /использ|ссыл|завис/i);
  assert.throws(() => model.deleteFaction(data, 'missing'), /фракци/i);
  const result = model.deleteFaction(data, 'cadet');
  assert.equal(result.factions.some(faction => faction.id === 'cadet'), false);
  assert.deepEqual(result.locations, data.locations);
  assert.deepEqual(result.territories, data.territories);
  assert.deepEqual(data, before);
});

test('object upserts retain modifiers and distinguish explicit independence', () => {
  assert.equal(typeof model.upsertObject, 'function');
  const data = model.normalizeData(fixture());
  const before = structuredClone(data);
  const object = building({ modifiers: [{ id: 'income', kind: 'bonus', text: '  Доход  ' }], provenance: { note: 'Не канон' } });
  const objectBefore = structuredClone(object);
  const added = model.upsertObject(data, 'city', object);
  assert.equal(model.effectiveFaction(added.locations[0], added.locations[0].objects[0]), 'greymane');
  const changed = model.upsertObject(added, 'city', { id: 'mill', faction: null, owner: '  Свободный мельник  ', description: '</script><script>evil()</script>' });
  assert.equal(model.effectiveFaction(changed.locations[0], changed.locations[0].objects[0]), null);
  assert.deepEqual(changed.locations[0].objects[0].modifiers, object.modifiers);
  assert.equal(changed.locations[0].objects[0].type, 'building');
  assert.equal(changed.locations[0].objects[0].name, 'Мельница');
  assert.deepEqual(changed.locations[0].objects[0].provenance, object.provenance);
  const resource = model.upsertObject(changed, 'city', { id: 'ore', name: 'Руда', type: 'resource', amount: 12, faction: 'crowley' });
  assert.equal(resource.locations[0].objects[1].amount, 12);
  assert.deepEqual(resource.locations[0].objects[1].modifiers, []);
  for (const invalid of [{ id: 'mill', type: 'bad' }, { id: 'mill', faction: 'missing' }, { id: 'mill', modifiers: [{ id: 'bad', kind: 'good', text: 'Неверно' }] }, building({ id: 'city-land' })]) {
    assert.throws(() => model.upsertObject(added, 'city', invalid));
  }
  assert.throws(() => model.upsertObject(data, 'missing', object), /локаци/i);
  assert.deepEqual(added.locations[0].objects[0], object);
  assert.deepEqual(data, before);
  assert.deepEqual(object, objectBefore);
  changed.locations[0].objects[0].modifiers[0].text = 'Изменено';
  assert.deepEqual(added.locations[0].objects[0], object);
});

test('removing nested objects preserves siblings and map geometry', () => {
  assert.equal(typeof model.removeObject, 'function');
  const raw = fixture();
  raw.locations[0].objects = [building({ modifiers: [{ id: 'income', kind: 'bonus', text: 'Доход' }] }), { id: 'ore', type: 'resource', name: 'Руда', modifiers: [] }];
  const data = model.normalizeData(raw);
  const before = structuredClone(data);
  const result = model.removeObject(data, 'city', 'mill');
  assert.deepEqual(result.locations[0].objects.map(object => object.id), ['ore']);
  assert.deepEqual(result.territories, data.territories);
  assert.equal(result.locations[0].faction, 'greymane');
  assert.throws(() => model.removeObject(data, 'city', 'missing'), /объект/i);
  assert.throws(() => model.removeObject(data, 'missing', 'mill'), /локаци/i);
  assert.deepEqual(data, before);
});

test('adding modifiers keeps semantic kinds and rejects invalid or duplicate IDs', () => {
  assert.equal(typeof model.addModifier, 'function');
  const raw = fixture();
  raw.locations[0].objects = [building()];
  const data = model.normalizeData(raw);
  const before = structuredClone(data);
  const bonus = { id: 'income', kind: 'bonus', text: '  +10% доход\n ', future: { assessed: false } };
  const bonusBefore = structuredClone(bonus);
  const added = model.addModifier(data, 'city', 'mill', bonus);
  const combined = model.addModifier(added, 'city', 'mill', { id: 'decay', kind: 'penalty', text: '  −5% износ  ' });
  assert.deepEqual(combined.locations[0].objects[0].modifiers.map(modifier => modifier.kind), ['bonus', 'penalty']);
  assert.deepEqual(added.locations[0].objects[0].modifiers[0], bonus);
  for (const invalid of [bonus, { id: 'bad', kind: 'positive', text: 'Ошибка' }, { id: 'city', kind: 'bonus', text: 'Повтор' }]) {
    assert.throws(() => model.addModifier(added, 'city', 'mill', invalid));
  }
  assert.throws(() => model.addModifier(data, 'missing', 'mill', bonus), /локаци/i);
  assert.throws(() => model.addModifier(data, 'city', 'missing', bonus), /объект/i);
  assert.deepEqual(data, before);
  assert.deepEqual(bonus, bonusBefore);
  combined.locations[0].objects[0].modifiers[0].future.assessed = true;
  assert.deepEqual(added.locations[0].objects[0].modifiers[0], bonus);
});

test('removing a modifier keeps other penalties and rejects unknown targets', () => {
  assert.equal(typeof model.removeModifier, 'function');
  const raw = fixture();
  raw.locations[0].objects = [building({ modifiers: [{ id: 'income', kind: 'bonus', text: 'Доход' }, { id: 'decay', kind: 'penalty', text: 'Износ' }] })];
  const data = model.normalizeData(raw);
  const before = structuredClone(data);
  const result = model.removeModifier(data, 'city', 'mill', 'income');
  assert.deepEqual(result.locations[0].objects[0].modifiers, [{ id: 'decay', kind: 'penalty', text: 'Износ' }]);
  assert.throws(() => model.removeModifier(data, 'city', 'mill', 'missing'), /модификатор/i);
  assert.throws(() => model.removeModifier(data, 'city', 'missing', 'income'), /объект/i);
  assert.throws(() => model.removeModifier(data, 'missing', 'mill', 'income'), /локаци/i);
  assert.deepEqual(data, before);
});

test('JSON serialization is a full validated snapshot that preserves script-shaped text', () => {
  assert.equal(typeof model.serializeSnapshot, 'function');
  const raw = fixture();
  raw.extension = { exact: '  raw\n</script><script>evil()</script>\u2028\u2029&<>  ' };
  raw.locations[0].description = raw.extension.exact;
  raw.locations[0].objects = [building({ faction: null, modifiers: [{ id: 'income', kind: 'bonus', text: '</script>  +10%' }] })];
  raw.sources = [{ id: 0, title: '  Источник  ', extra: true }];
  raw.nobles = [{ id: 'genn', name: 'Генн', date: 'Без произвольного года', provenance: { sources: [0] } }];
  raw.locations[0].provenance = { note: '  Сценарная реконструкция  ', sources: [0] };
  const before = structuredClone(raw);
  const text = model.serializeSnapshot(raw);
  assert.equal(typeof text, 'string');
  assert.equal(text.includes('</script><script>evil()</script>'), true);
  assert.deepEqual(JSON.parse(text), model.normalizeData(raw));
  assert.deepEqual(JSON.parse(text).extension, raw.extension);
  assert.deepEqual(raw, before);
  const invalid = fixture();
  invalid.locations[0].x = Infinity;
  assert.throws(() => model.serializeSnapshot(invalid), /точк|координат/i);
});

test('JSON import replaces faction trees and modifiers using immutable incoming data', () => {
  assert.equal(typeof model.deserializeSnapshot, 'function');
  const incoming = fixture();
  incoming.factions = [
    { id: 'new-realm', name: 'Новая держава', parent: null, color: '#123456' },
    { id: 'new-house', name: 'Новый дом', parent: 'new-realm', color: '#abcdef' },
    { id: 'new-cadet', name: 'Младший дом', parent: 'new-house', color: '#fedcba' }
  ];
  incoming.locations[0].faction = 'new-cadet';
  incoming.locations[0].description = '  </script><script>evil()</script>  ';
  incoming.locations[0].objects = [building({ modifiers: [{ id: 'income', kind: 'bonus', text: '  Доход  ' }, { id: 'decay', kind: 'penalty', text: '  Износ  ' }] }), { id: 'free-ore', type: 'resource', name: 'Руда', faction: null, amount: 17 }];
  incoming.territories[0].faction = 'new-house';
  incoming.sources = [{ id: 'source', title: 'Летопись' }];
  incoming.locations[0].provenance = { confidence: 'Не строго перечисление', chronology: 'Без точного года', sources: ['source'] };
  const text = JSON.stringify(incoming);
  const before = structuredClone(incoming);
  const imported = model.deserializeSnapshot(text);
  assert.deepEqual(imported, model.normalizeData(incoming));
  assert.equal(model.sovereignOf(imported.factions, 'new-cadet'), 'new-realm');
  assert.deepEqual(model.factionMembers(imported.factions, 'new-house'), ['new-house', 'new-cadet']);
  assert.equal(model.effectiveFaction(imported.locations[0], imported.locations[0].objects[0]), 'new-cadet');
  assert.equal(model.effectiveFaction(imported.locations[0], imported.locations[0].objects[1]), null);
  imported.locations[0].objects[0].modifiers.pop();
  assert.deepEqual(incoming, before);
  assert.deepEqual(model.deserializeSnapshot(text), model.normalizeData(before));
  assert.throws(() => model.deserializeSnapshot('{broken'), SyntaxError);
  assert.throws(() => model.deserializeSnapshot(JSON.stringify({ ...incoming, version: 2 })), /верси/i);
  assert.throws(() => model.deserializeSnapshot(null), /JSON|текст/i);
});

test('saving a draft writes only the map key as a normalized full snapshot', () => {
  assert.equal(typeof model.saveDraft, 'function');
  const storage = memoryStorage([['ugalaxy', 'leave alone']]);
  const raw = fixture();
  raw.locations[0].objects = [building({ faction: null, modifiers: [{ id: 'income', kind: 'bonus', text: '  </script> доход  ' }] })];
  const before = structuredClone(raw);
  model.saveDraft(storage, raw);
  const stored = storage.getItem('gilneas-atlas-draft-v1');
  assert.equal(stored, model.serializeSnapshot(raw));
  assert.deepEqual(JSON.parse(stored), model.normalizeData(raw));
  assert.equal(storage.getItem('ugalaxy'), 'leave alone');
  const invalid = fixture();
  invalid.factions[0].parent = 'cadet';
  assert.throws(() => model.saveDraft(storage, invalid));
  assert.equal(storage.getItem('gilneas-atlas-draft-v1'), stored);
  model.saveDraft(storage, raw, 'another-map');
  assert.equal(storage.getItem('another-map'), stored);
  assert.deepEqual(raw, before);
});

test('loading a draft reloads the entire edited snapshot instead of the baseline', () => {
  assert.equal(typeof model.loadDraft, 'function');
  const baseline = fixture();
  const baselineBefore = structuredClone(baseline);
  const storage = memoryStorage();
  const absent = model.loadDraft(storage, baseline);
  assert.deepEqual(absent, { data: model.normalizeData(baseline), isDraft: false, error: null });
  assert.notEqual(absent.data, baseline);
  let edited = model.upsertFaction(baseline, { id: 'crowley', parent: 'dalaran' });
  edited = model.updateLocation(edited, 'city', { name: '  Новый порт  ', faction: 'cadet', description: '  </script><script>evil()</script>  ' });
  edited = model.upsertObject(edited, 'city', building());
  edited = model.addModifier(edited, 'city', 'mill', { id: 'income', kind: 'bonus', text: '  Доход  ' });
  edited = model.addModifier(edited, 'city', 'mill', { id: 'decay', kind: 'penalty', text: '  Износ  ' });
  edited = model.upsertObject(edited, 'city', { id: 'ore', type: 'resource', name: 'Руда', amount: 7, faction: null });
  model.saveDraft(storage, edited);
  const result = model.loadDraft(storage, baseline);
  assert.equal(result.isDraft, true);
  assert.equal(result.error, null);
  assert.deepEqual(result.data, edited);
  assert.equal(model.sovereignOf(result.data.factions, 'cadet'), 'dalaran');
  assert.equal(model.effectiveFaction(result.data.locations[0], result.data.locations[0].objects[0]), 'cadet');
  assert.equal(model.effectiveFaction(result.data.locations[0], result.data.locations[0].objects[1]), null);
  result.data.locations[0].objects[0].modifiers[0].text = 'Изменено после reload';
  assert.deepEqual(model.loadDraft(storage, baseline).data, edited);
  model.saveDraft(storage, edited, 'custom-map');
  assert.deepEqual(model.loadDraft(storage, baseline, 'custom-map').data, edited);
  assert.deepEqual(baseline, baselineBefore);
});

test('broken or incompatible drafts fall back without erasing stored evidence', () => {
  const baseline = fixture();
  const before = structuredClone(baseline);
  const invalidTree = fixture();
  invalidTree.factions[0].parent = 'cadet';
  const invalidModifiers = fixture();
  invalidModifiers.locations[0].objects = [building({ modifiers: [{ id: 'bad', kind: 'positive', text: 'Ошибка' }] })];
  const invalidSource = fixture();
  invalidSource.locations[0].provenance = { sources: ['missing'] };
  for (const snapshot of ['', '{broken', 'null', '[]', JSON.stringify({ ...fixture(), version: 2 }), JSON.stringify(invalidTree), JSON.stringify(invalidModifiers), JSON.stringify(invalidSource)]) {
    const storage = memoryStorage([['gilneas-atlas-draft-v1', snapshot], ['unrelated-map', 'safe']]);
    let result;
    assert.doesNotThrow(() => { result = model.loadDraft(storage, baseline); });
    assert.equal(result.isDraft, false);
    assert.equal(result.error instanceof Error, true);
    assert.deepEqual(result.data, model.normalizeData(baseline));
    assert.notEqual(result.data, baseline);
    assert.equal(storage.getItem('gilneas-atlas-draft-v1'), snapshot);
    assert.equal(storage.getItem('unrelated-map'), 'safe');
  }
  const accessError = new Error('Storage access denied');
  const blocked = { getItem() { throw accessError; } };
  const unavailable = model.loadDraft(blocked, baseline);
  assert.equal(unavailable.error, accessError);
  assert.equal(unavailable.isDraft, false);
  assert.deepEqual(unavailable.data, model.normalizeData(baseline));
  assert.deepEqual(baseline, before);
});

test('resetting drafts removes only the requested map key', () => {
  assert.equal(typeof model.resetDraft, 'function');
  const storage = memoryStorage([['gilneas-atlas-draft-v1', 'broken'], ['custom-map', 'second draft'], ['ugalaxy', 'keep']]);
  model.resetDraft(storage);
  assert.equal(storage.getItem('gilneas-atlas-draft-v1'), null);
  assert.equal(storage.getItem('custom-map'), 'second draft');
  assert.equal(storage.getItem('ugalaxy'), 'keep');
  model.resetDraft(storage, 'custom-map');
  assert.equal(storage.getItem('custom-map'), null);
  assert.equal(storage.getItem('ugalaxy'), 'keep');
  const baseline = fixture();
  const loaded = model.loadDraft(storage, baseline);
  assert.equal(loaded.isDraft, false);
  assert.equal(loaded.error, null);
  assert.deepEqual(loaded.data, model.normalizeData(baseline));
  model.resetDraft(storage);
  assert.equal(storage.getItem('ugalaxy'), 'keep');
});

test('territory upserts validate manual boundaries without moving locations', () => {
  assert.equal(typeof model.upsertTerritory, 'function');
  const data = model.normalizeData(fixture());
  const before = structuredClone(data);
  const territory = { id: 'house-land', faction: 'cadet', name: '  Младшие владения  ', points: [[10, 10], [20, 10], [20, 20], [10, 20]], provenance: { note: 'Реконструкция' } };
  const territoryBefore = structuredClone(territory);
  const added = model.upsertTerritory(data, territory);
  assert.deepEqual(added.territories.at(-1), territory);
  const changed = model.upsertTerritory(added, { id: 'house-land', faction: 'crowley', points: [[30, 30], [40, 30], [30, 40]] });
  assert.equal(changed.territories.at(-1).name, territory.name);
  assert.deepEqual(changed.territories.at(-1).provenance, territory.provenance);
  assert.equal(changed.territories.at(-1).faction, 'crowley');
  assert.deepEqual(changed.locations, data.locations);
  assert.deepEqual(changed.factions, data.factions);
  for (const invalid of [{ id: 'house-land', points: [[0, 0], [10, 10], [0, 8], [10, 0]] }, { id: 'house-land', faction: 'missing' }, { ...territory, id: 'city' }]) {
    assert.throws(() => model.upsertTerritory(added, invalid));
  }
  assert.deepEqual(data, before);
  assert.deepEqual(territory, territoryBefore);
  changed.territories.at(-1).points[0][0] = 31;
  assert.deepEqual(added.territories.at(-1), territory);
});

test('removing territory leaves all locations and faction ownership intact', () => {
  assert.equal(typeof model.removeTerritory, 'function');
  const data = model.normalizeData(fixture());
  const before = structuredClone(data);
  const result = model.removeTerritory(data, 'city-land');
  assert.deepEqual(result.territories, []);
  assert.deepEqual(result.locations, data.locations);
  assert.deepEqual(result.factions, data.factions);
  assert.throws(() => model.removeTerritory(data, 'missing'), /территор/i);
  assert.deepEqual(data, before);
});

test('embedded HTML JSON escaping happens only at the explicit export boundary', () => {
  assert.equal(typeof model.serializeSnapshotForHtml, 'function');
  const raw = fixture();
  raw.locations[0].description = '  </ScRiPt><script>evil()</script><!-- <img src=x onerror=evil()> & > \u2028\u2029  ';
  const before = structuredClone(raw);
  const json = model.serializeSnapshot(raw);
  const embedded = model.serializeSnapshotForHtml(raw);
  assert.equal(json.includes('</ScRiPt>'), true);
  assert.equal(embedded.includes('<'), false);
  assert.equal(embedded.includes('>'), false);
  assert.equal(embedded.includes('&'), false);
  assert.equal(embedded.includes('\u2028'), false);
  assert.equal(embedded.includes('\u2029'), false);
  assert.equal(embedded.includes('\\u003c'), true);
  assert.deepEqual(JSON.parse(embedded), JSON.parse(json));
  assert.deepEqual(model.deserializeSnapshot(embedded), model.normalizeData(raw));
  assert.deepEqual(raw, before);
});

test('immutable location patches preserve special-key JSON extension fields', () => {
  const data = model.normalizeData(fixture());
  const patch = JSON.parse('{"__proto__":{"future":"preserved","polluted":true},"constructor":{"note":"raw"},"prototype":{"note":"unchanged"}}');
  const before = structuredClone(data);
  const result = model.updateLocation(data, 'city', patch);
  assert.equal(Object.hasOwn(result.locations[0], '__proto__'), true);
  assert.deepEqual(result.locations[0].__proto__, patch.__proto__);
  assert.deepEqual(result.locations[0].constructor, patch.constructor);
  assert.deepEqual(result.locations[0].prototype, patch.prototype);
  assert.equal(Object.getPrototypeOf(result.locations[0]), Object.prototype);
  assert.equal({}.polluted, undefined);
  assert.deepEqual(data, before);
  assert.deepEqual(JSON.parse(model.serializeSnapshot(result)).locations[0].__proto__, patch.__proto__);
});

test('polygon validation rejects negative atlas coordinates', () => {
  assert.throws(() => model.validatePolygon([[-1, 0], [10, 0], [0, 10]]), /координат/i);
  assert.throws(() => model.validatePolygon([[0, -1], [10, 0], [0, 10]]), /координат/i);
  assert.equal(model.validatePolygon([[0, 0], [10, 0], [0, 10]]), true);
});

test('polygon validation accepts tiny nonzero polygons without translation cancellation', () => {
  const points = [[3246, 4859], [3246.000001, 4859], [3246, 4859.000001]];
  assert.equal(model.validatePolygon(points), true);
  assert.equal(model.validatePolygon(points.toReversed()), true);
  const raw = fixture();
  raw.territories[0].points = points;
  assert.deepEqual(model.normalizeData(raw).territories[0].points, points);
});

test('normalization rejects sparse atlas collections instead of producing JSON null records', () => {
  const holes = () => new Array(1);
  for (const field of ['factions', 'locations', 'territories', 'nobles', 'sources']) {
    const raw = fixture();
    raw[field] = holes();
    assert.throws(() => model.normalizeData(raw), /массив|запис/i);
  }
  const objects = fixture();
  objects.locations[0].objects = holes();
  assert.throws(() => model.normalizeData(objects), /массив|запис/i);
  const modifiers = fixture();
  modifiers.locations[0].objects = [building({ modifiers: holes() })];
  assert.throws(() => model.normalizeData(modifiers), /массив|запис/i);
});

test('normalization rejects cyclic input with a readable snapshot error', () => {
  const raw = fixture();
  raw.extension = { self: raw };
  assert.throws(() => model.normalizeData(raw), /циклическ.*сним|сним.*циклическ/i);
  assert.equal(raw.extension.self, raw);
  const shared = { text: '  shared text  ' };
  const valid = fixture();
  valid.first = shared;
  valid.second = shared;
  const result = model.normalizeData(valid);
  assert.deepEqual(result.first, shared);
  assert.deepEqual(result.second, shared);
  assert.notEqual(result.first, shared);
  result.first.text = 'Изменено';
  assert.equal(shared.text, '  shared text  ');
  assert.equal(result.second.text, '  shared text  ');
});

test('generated IDs preserve a literal prefix and satisfy model ID limits', () => {
  assert.equal(typeof model.makeId, 'function');
  const id = model.makeId('  house  ');
  assert.equal(typeof id, 'string');
  assert.equal(id.startsWith('  house  -'), true);
  assert.equal(id.length <= 100, true);
  assert.match(id.slice('  house  -'.length), /^[a-zA-Z0-9-]+$/);
  for (const prefix of ['', null, undefined, 1, 'x'.repeat(100)]) assert.throws(() => model.makeId(prefix), /префикс/i);
  const raw = fixture();
  raw.locations[0].id = id;
  assert.equal(model.normalizeData(raw).locations[0].id, id);
});

test('normalization preserves explicitly empty type text instead of replacing it', () => {
  const raw = fixture();
  raw.locations[0].type = '';
  raw.locations[0].name = '  Без обрезки\n  ';
  raw.locations[0].owner = '  <владелец>  ';
  raw.locations[0].description = '\n  </script>  \n';
  raw.factions[0].name = '  Королевство\n  ';
  raw.custom = { id: 'city', title: '  Не известное модели поле  ' };
  const before = structuredClone(raw);
  const result = model.normalizeData(raw);
  assert.equal(result.locations[0].type, '');
  assert.equal(result.locations[0].name, raw.locations[0].name);
  assert.equal(result.locations[0].owner, raw.locations[0].owner);
  assert.equal(result.locations[0].description, raw.locations[0].description);
  assert.equal(result.factions[0].name, raw.factions[0].name);
  assert.deepEqual(result.custom, raw.custom);
  assert.deepEqual(raw, before);
  delete raw.locations[0].type;
  assert.equal(model.normalizeData(raw).locations[0].type, 'settlement');
});

test('faction descendant queries reject cycles even when the selected node is in the cycle', () => {
  const self = [{ id: 'root', parent: 'root' }];
  const mutual = [{ id: 'root', parent: 'house' }, { id: 'house', parent: 'root' }];
  for (const factions of [self, mutual]) {
    assert.throws(() => model.factionMembers(factions, 'root'), /цикл/i);
    assert.throws(() => model.sovereignOf(factions, 'root'), /цикл/i);
  }
  const missing = [{ id: 'root', parent: 'missing' }];
  assert.throws(() => model.factionMembers(missing, 'root'), /сюзерен|родител/i);
  const data = model.normalizeData(fixture());
  assert.throws(() => model.factionMembers(data.factions, 'missing'), /фракци/i);
  assert.throws(() => model.sovereignOf(data.factions, 'missing'), /фракци/i);
  assert.deepEqual(model.factionMembers(data.factions, null), []);
  assert.equal(model.sovereignOf(data.factions, null), null);
});

test('object edits can explicitly clear an override to restore faction inheritance', () => {
  const raw = fixture();
  raw.locations[0].objects = [building({ faction: null, modifiers: [{ id: 'income', kind: 'bonus', text: 'Доход' }] })];
  const data = model.normalizeData(raw);
  const before = structuredClone(data);
  let restored;
  assert.doesNotThrow(() => { restored = model.upsertObject(data, 'city', { id: 'mill', faction: undefined }); });
  assert.equal(Object.hasOwn(restored.locations[0].objects[0], 'faction'), false);
  assert.equal(model.effectiveFaction(restored.locations[0], restored.locations[0].objects[0]), 'greymane');
  assert.deepEqual(restored.locations[0].objects[0].modifiers, data.locations[0].objects[0].modifiers);
  const unchanged = model.upsertObject(data, 'city', { id: 'mill', description: 'Правка' });
  assert.equal(unchanged.locations[0].objects[0].faction, null);
  assert.deepEqual(data, before);
  const inherited = model.upsertObject(model.normalizeData(fixture()), 'city', building({ faction: undefined }));
  assert.equal(Object.hasOwn(inherited.locations[0].objects[0], 'faction'), false);
  assert.equal(model.deserializeSnapshot(model.serializeSnapshot(restored)).locations[0].objects[0].faction, undefined);
});

test('normalization rejects non-JSON extension records instead of silently erasing them', () => {
  for (const extension of [new Map([['key', 'value']]), new Set(['value']), new Date('2000-01-01T00:00:00Z'), /value/, new Uint8Array([1, 2])]) {
    const raw = fixture();
    raw.extension = extension;
    assert.throws(() => model.normalizeData(raw), /JSON|сним/i);
    assert.equal(raw.extension, extension);
  }
  const raw = fixture();
  raw.extension = Object.assign(Object.create(null), { future: '  exact  ', date: 'После Второй войны — неизвестный день' });
  assert.deepEqual(model.normalizeData(raw).extension, { future: '  exact  ', date: 'После Второй войны — неизвестный день' });
});

test('fractional polygon edges remain inclusive despite floating-point rounding', () => {
  const a = [741.920979693532, 3635.904393158853];
  const b = [2028.22097344324, 2965.366036631167];
  const c = [2134.796538390219, 1221.6905308887362];
  const edge = [1827.3007424029897, 3070.1042175917023];
  assert.equal(model.inPolygon(edge, [a, b, c]), true);
  assert.equal(model.inPolygon(edge, [c, b, a]), true);
  assert.equal(model.inPolygon([edge[0], edge[1] + 0.00001], [a, b, c]), false);
  assert.equal(model.validatePolygon([a, b, c]), true);
});

test('normalization rejects mutable function and unrepresentable extension values', () => {
  for (const extension of [() => 'value', Symbol('value'), 1n, NaN, Infinity, -Infinity]) {
    const raw = fixture();
    raw.extension = extension;
    assert.throws(() => model.normalizeData(raw), /JSON|сним/i);
    assert.equal(raw.extension, extension);
  }
  const raw = fixture();
  raw.extension = { zero: 0, independent: null, enabled: false, text: '  exact  ' };
  assert.deepEqual(model.normalizeData(raw).extension, raw.extension);
});

test('polygon queries return false for invalid points rather than matching incomplete coordinates', () => {
  const points = [[0, 0], [10, 0], [10, 10], [0, 10]];
  for (const point of [null, undefined, {}, [], [1], ['5', '5'], [NaN, 5], [5, Infinity], [1, 1, 0], new Array(2)]) {
    let included;
    assert.doesNotThrow(() => { included = model.inPolygon(point, points); });
    assert.equal(included, false);
  }
  assert.equal(model.inPolygon([5, 5], points), true);
});

test('polygon validation rejects sparse coordinate pairs before checking geometry', () => {
  const pair = new Array(2);
  pair[0] = 0;
  assert.throws(() => model.validatePolygon([[0, 0], [10, 0], pair]), /координат/i);
  const polygon = [[0, 0], [10, 0], [0, 10]];
  delete polygon[1];
  assert.throws(() => model.validatePolygon(polygon), /координат/i);
});
