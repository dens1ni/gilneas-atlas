import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const engineModule = () => import('../assets/js/location-links.mjs');

const deepFreeze = value => {
  const pending = [value];
  const seen = new Set();
  while (pending.length) {
    const current = pending.pop();
    if (current === null || typeof current !== 'object' || seen.has(current)) continue;
    seen.add(current);
    pending.push(...Object.values(current));
    Object.freeze(current);
  }
  return value;
};

const fullSnapshot = () => ({
  version: 1,
  meta: { width: 1000, height: 800, map: 'assets/maps/origins.jpg', author: { empty: '', flag: false, nil: null } },
  factions: [
    { id: 'crowley', name: 'Краули', parent: 'gilneas', color: '#654321' },
    { id: 'gilneas', name: 'Гилнеас', parent: null, color: '#123456' },
  ],
  locations: [
    { id: 'military-district', name: 'Военный квартал', type: 'district', faction: 'crowley', owner: 'Краули', x: 10, y: 20,
      objects: [{ id: 'barracks-inline', name: 'Казармы', type: 'barracks', owner: '',
        modifiers: [{ id: 'district-bonus', kind: 'bonus', text: '  Авторский бонус  ' }] }],
      author: { blank: '', literal: false } },
    { id: 'stoneward-prison', name: 'Тюрьма Каменной Стражи', type: 'building', faction: 'gilneas', owner: 'Королевская стража', x: 30, y: 40,
      objects: [{ id: 'prison-inline', name: 'Караул', type: 'building', faction: null, owner: 'Собственный владелец',
        modifiers: [{ id: 'prison-penalty', kind: 'penalty', text: '<script>буквальный текст</script>', value: 0 }] }],
      modifiers: [{ id: 'prison-local-effect', text: 'Не переносить' }], sources: [1, 'source-1'], note: '  Авторская заметка  ' },
    { id: 'harbor', name: 'Гавань', type: 'harbor', faction: null, owner: '', x: 50, y: 60, objects: [] },
  ],
  territories: [{ id: 'territory-1', faction: 'crowley', points: [[0, 0], [100, 0], [0, 100]], author: { keep: false } }],
  territoryGrid: { version: 1, cellSize: 100, columns: 2, rows: 2, keys: ['crowley', 'gilneas'], cells: [0, 1, 2, 0], manual: { 0: 0 } },
  nobles: [{ id: 'noble-1', name: 'Авторский персонаж', house: 'crowley', holdingsNote: '' }],
  sources: [{ id: 1, title: 'Числовой источник' }, { id: 'source-1', title: 'Строковый источник' }],
  royalCouncil: { version: 1, members: [] },
  authorMetadata: { untouched: [false, null, '', 0], dossier: { owner: 'Не суммировать' } },
});

const graph = (...locations) => ({ locations });
const place = (id, linkedLocationIds = []) => ({ id, isLocation: true, linkedLocationIds });

const assertRussianError = (run, ...details) => {
  assert.throws(run, error => {
    assert.ok(error instanceof Error);
    assert.match(error.message, /[А-Яа-яЁё]/);
    for (const detail of details) {
      if (detail instanceof RegExp) assert.match(error.message, detail);
      else assert.ok(error.message.includes(detail), `Ожидалась подсказка ${JSON.stringify(detail)} в ${JSON.stringify(error.message)}`);
    }
    return true;
  });
};

test('isMapLocation recognizes only the literal true flag without writing a record', async () => {
  const { isMapLocation } = await engineModule();
  assert.equal(typeof isMapLocation, 'function');
  const marked = deepFreeze({ id: 'literal', isLocation: true, type: 'district' });
  assert.equal(isMapLocation(marked), true);
  for (const value of [undefined, null, false, 0, '', {}, { isLocation: false }, { isLocation: undefined },
    { isLocation: null }, { isLocation: 'true' }, { isLocation: 1 }]) {
    assert.equal(isMapLocation(value), false);
  }
  assert.deepEqual(marked, { id: 'literal', isLocation: true, type: 'district' });
  assert.equal(typeof globalThis.document, 'undefined');
});

test('legacy snapshots validate without adding optional schema or changing full frozen author data', async () => {
  const { validateLocationLinks, resolveLocationLinks, eligibleLocationLinkTargets } = await engineModule();
  assert.equal(typeof validateLocationLinks, 'function');
  const published = JSON.parse(await readFile(new URL('../assets/data/atlas.json', import.meta.url), 'utf8'));
  assert.equal(published.locations.length, 39);
  const publishedBefore = structuredClone(published);
  assert.equal(validateLocationLinks(deepFreeze(published)), true);
  assert.deepEqual(published, publishedBefore);
  // Exercise a legacy copy even after publication starts using the optional fields.
  const legacyPublished = structuredClone(published);
  for (const record of legacyPublished.locations) {
    delete record.isLocation;
    delete record.linkedLocationIds;
  }
  for (const data of [fullSnapshot(), legacyPublished, graph()]) {
    const before = structuredClone(data);
    const json = JSON.stringify(data);
    deepFreeze(data);
    assert.equal(validateLocationLinks(data), true);
    for (const record of data.locations) {
      assert.deepEqual(resolveLocationLinks(data, record.id), { location: record, children: [], parents: [] });
      assert.deepEqual(eligibleLocationLinkTargets(data, record.id), data.locations.filter(other => other !== record));
    }
    assert.deepEqual(data, before);
    assert.equal(JSON.stringify(data), json);
    for (let index = 0; index < data.locations.length; index++) {
      for (const field of ['isLocation', 'linkedLocationIds']) {
        assert.equal(Object.hasOwn(data.locations[index], field), Object.hasOwn(before.locations[index], field));
      }
    }
  }
});

test('validation rejects missing snapshot input and malformed locations collections with Russian guidance', async () => {
  const { validateLocationLinks } = await engineModule();
  for (const data of [undefined, null, [], '', false, 1]) {
    assertRussianError(() => validateLocationLinks(data), /снимок/i);
  }
  for (const data of [{}, { locations: undefined }, { locations: null }, { locations: {} }, { locations: '' }, { locations: false }]) {
    assertRussianError(() => validateLocationLinks(data), 'locations', /массив/i);
  }
});

test('every canonical record requires a nonempty exact string ID of at most 100 characters', async () => {
  const { validateLocationLinks } = await engineModule();
  for (const record of [null, undefined, [], false, 'record', 1]) {
    assertRussianError(() => validateLocationLinks(graph(record)), 'locations[0]', /запись/i);
  }
  for (const record of [{}, { id: undefined }, { id: null }, { id: false }, { id: 1 }, { id: '' }, { id: 'x'.repeat(101) }]) {
    assertRussianError(() => validateLocationLinks(graph(record)), 'locations[0]', 'id', '1', '100');
  }
  for (const id of ['1', ' ', '\n\t', ' quoted " ID ', '__proto__', 'constructor', 'x'.repeat(100)]) {
    assert.equal(validateLocationLinks(graph({ id })), true);
  }
});

test('duplicate canonical IDs are rejected rather than selecting an arbitrary current record', async () => {
  const { validateLocationLinks } = await engineModule();
  for (const id of ['same', '__proto__', ' "quoted" ', '1']) {
    assertRussianError(() => validateLocationLinks(graph({ id }, { id })), /повтор/i, id, 'locations[1]');
  }
});

test('optional isLocation accepts only booleans when the flag is present', async () => {
  const { validateLocationLinks } = await engineModule();
  for (const isLocation of [undefined, null, '', 'true', 'false', 0, 1, [], {}]) {
    assertRussianError(() => validateLocationLinks(graph({ id: 'flagged', isLocation })), 'flagged', 'isLocation', /логическ|boolean/i);
  }
  for (const record of [{ id: 'absent' }, { id: 'no', isLocation: false }, { id: 'yes', isLocation: true }]) {
    const before = structuredClone(record);
    assert.equal(validateLocationLinks(graph(deepFreeze(record))), true);
    assert.deepEqual(record, before);
  }
});

test('optional linkedLocationIds must be an array and empty links stay empty without writes', async () => {
  const { validateLocationLinks } = await engineModule();
  for (const linkedLocationIds of [undefined, null, false, '', 'target', 1, {}, new Set(['target'])]) {
    assertRussianError(() => validateLocationLinks(graph({ id: 'links', linkedLocationIds })), 'links', 'linkedLocationIds', /массив/i);
  }
  for (const record of [{ id: 'absent' }, { id: 'legacy', linkedLocationIds: [] },
    { id: 'plain', isLocation: false, linkedLocationIds: [] }, place('marked')]) {
    const before = structuredClone(record);
    assert.equal(validateLocationLinks(graph(deepFreeze(record))), true);
    assert.deepEqual(record, before);
  }
});

test('nonempty links require the source marker literal isLocation true but not a marked target', async () => {
  const { validateLocationLinks } = await engineModule();
  for (const source of [{ id: 'source', linkedLocationIds: ['target'] },
    { id: 'source', isLocation: false, linkedLocationIds: ['target'] }]) {
    assertRussianError(() => validateLocationLinks(graph(source, { id: 'target' })), 'source', 'isLocation', 'true');
  }
  assert.equal(validateLocationLinks(graph(place('source', ['target']), { id: 'target', isLocation: false })), true);
});

test('link tokens must be literal strings of length 1 through 100 before any lookup', async () => {
  const { validateLocationLinks } = await engineModule();
  for (const token of ['', 1, false, null, undefined, {}, [], { id: 'target' }, new String('target'), 'x'.repeat(101)]) {
    assertRussianError(() => validateLocationLinks(graph(place('source', [token]), { id: 'target' }, { id: '1' })),
      'source', 'linkedLocationIds[0]', '1', '100', /строк/i);
  }
  const maximum = 'x'.repeat(100);
  assert.equal(validateLocationLinks(graph(place('source', [maximum]), { id: maximum })), true);
  const sparse = []; sparse.length = 1;
  assertRussianError(() => validateLocationLinks(graph(place('source', sparse))), 'source', 'linkedLocationIds[0]');
});

test('duplicate reference tokens are rejected within one source without deduplication or writes', async () => {
  const { validateLocationLinks } = await engineModule();
  for (const targetId of ['target', '__proto__', ' "quoted" ']) {
    const data = graph(place('source', [targetId, targetId]), { id: targetId });
    const before = structuredClone(data);
    deepFreeze(data);
    assertRussianError(() => validateLocationLinks(data), 'source', 'linkedLocationIds[1]', targetId, /повтор/i);
    assert.deepEqual(data, before);
  }
});

test('a source cannot link to itself even with prototype-like or whitespace IDs', async () => {
  const { validateLocationLinks } = await engineModule();
  for (const id of ['self', '__proto__', ' ', ' "quoted" ']) {
    assertRussianError(() => validateLocationLinks(graph(place(id, [id]))), id, 'linkedLocationIds[0]', /сам|себя/i);
  }
});

test('dangling links reject inline objects, modifiers, names and other registries as map targets', async () => {
  const { validateLocationLinks } = await engineModule();
  for (const targetId of ['missing', 'prison-inline', 'prison-penalty', 'prison-local-effect', 'noble-1', 'territory-1', 'crowley', 'source-1',
    'Тюрьма Каменной Стражи', '1']) {
    const data = fullSnapshot();
    data.locations[0].isLocation = true;
    data.locations[0].linkedLocationIds = [targetId];
    data.locations[1].objects[0].isLocation = true;
    const before = structuredClone(data);
    deepFreeze(data);
    assertRussianError(() => validateLocationLinks(data), 'military-district', 'linkedLocationIds[0]', targetId, /не найден|неизвестн/i);
    assert.deepEqual(data, before);
  }
  assert.equal(validateLocationLinks(graph(place('source', ['later']), { id: 'later' })), true);
  assert.equal(validateLocationLinks(graph({ id: 'earlier' }, place('source', ['earlier']))), true);
  for (const targetId of ['target', 'Target', ' target', 'target ']) {
    assertRussianError(() => validateLocationLinks(graph(place('source', [targetId]), { id: ' target ' })), targetId, /не найден/i);
  }
});

test('acyclic nested graphs and diamonds are valid while directed cycles anywhere in the graph are rejected', async () => {
  const { validateLocationLinks } = await engineModule();
  for (const data of [graph(place('A', ['B']), place('B', ['A'])),
    graph(place('A', ['B']), place('B', ['C']), place('C', ['A'])),
    graph({ id: 'unrelated' }, place('X', ['Y']), place('Y', ['Z']), place('Z', ['X']))]) {
    const before = structuredClone(data);
    deepFreeze(data);
    assertRussianError(() => validateLocationLinks(data), /цикл/i, 'linkedLocationIds', /удал|убер|разорв/i);
    assert.deepEqual(data, before);
  }
  assert.equal(validateLocationLinks(graph(place('A', ['B']), place('B', ['C']), { id: 'C' })), true);
  assert.equal(validateLocationLinks(graph(place('A', ['B', 'C']), place('B', ['D']), place('C', ['D']), { id: 'D' })), true);
  const depth = 20000;
  const chain = graph(...Array.from({ length: depth }, (_, index) => place(`deep-${index}`, index + 1 < depth ? [`deep-${index + 1}`] : [])));
  assert.equal(validateLocationLinks(deepFreeze(chain)), true);
  const cyclic = { locations: [...chain.locations.slice(0, -1), place(`deep-${depth - 1}`, ['deep-0'])] };
  assertRussianError(() => validateLocationLinks(deepFreeze(cyclic)), /цикл/i, 'deep-0', /удал|убер|разорв/i);
});

test('resolve returns canonical direct children in authored link order and direct parents in registry order', async () => {
  const { resolveLocationLinks } = await engineModule();
  assert.equal(typeof resolveLocationLinks, 'function');
  const data = graph(place('second-parent', ['root']), place('root', ['right', 'left']),
    place('left', ['leaf']), place('right', ['leaf']), { id: 'leaf', name: 'Текущая запись' }, place('first-parent', ['root']));
  deepFreeze(data);
  const root = resolveLocationLinks(data, 'root');
  assert.deepEqual(Object.keys(root).sort(), ['children', 'location', 'parents']);
  assert.equal(root.location, data.locations[1]);
  assert.deepEqual(root.children, [data.locations[3], data.locations[2]]);
  assert.equal(root.children[0], data.locations[3]);
  assert.equal(root.children[1], data.locations[2]);
  assert.deepEqual(root.parents, [data.locations[0], data.locations[5]]);
  assert.equal(root.parents[0], data.locations[0]);
  assert.equal(root.parents[1], data.locations[5]);
  const leaf = resolveLocationLinks(data, 'leaf');
  assert.equal(leaf.location, data.locations[4]);
  assert.deepEqual(leaf.children, []);
  assert.deepEqual(leaf.parents, [data.locations[2], data.locations[3]]);
  assert.equal(leaf.parents[0], data.locations[2]);
  assert.equal(leaf.parents[1], data.locations[3]);
  assert.deepEqual(resolveLocationLinks(graph({ id: 'legacy' }), 'legacy'), { location: { id: 'legacy' }, children: [], parents: [] });
  const renamed = structuredClone(data);
  renamed.locations[3].name = '  Текущее авторское имя  ';
  renamed.locations[3].owner = 'Новый собственный владелец';
  renamed.locations[3].objects = [{ id: 'current-inline', modifiers: [{ id: 'current-effect', text: 'Текущий эффект' }] }];
  deepFreeze(renamed);
  const current = resolveLocationLinks(renamed, 'root');
  assert.equal(current.children[0], renamed.locations[3]);
  assert.notEqual(current.children[0], root.children[0]);
  assert.equal(current.children[0].name, '  Текущее авторское имя  ');
  assert.equal(current.children[0].owner, 'Новый собственный владелец');
  assert.equal(current.children[0].objects[0].modifiers[0], renamed.locations[3].objects[0].modifiers[0]);
  assert.equal(root.children[0], data.locations[3]);
  const literalIds = ['__proto__', 'constructor', ' quoted " ID ', ' ', '\n\t', '1', 'x'.repeat(100)];
  const literalGraph = deepFreeze(graph(place('literal-root', literalIds), ...literalIds.map(id => ({ id }))));
  const literals = resolveLocationLinks(literalGraph, 'literal-root');
  assert.deepEqual(literals.children, literalGraph.locations.slice(1));
  for (let index = 0; index < literals.children.length; index++) {
    assert.equal(literals.children[index], literalGraph.locations[index + 1]);
    assert.equal(resolveLocationLinks(literalGraph, literalIds[index]).parents[0], literalGraph.locations[0]);
  }
});

test('resolve fails clearly for missing snapshot, malformed exact ID and missing canonical records', async () => {
  const { resolveLocationLinks } = await engineModule();
  for (const data of [undefined, null, false, [], '', 1]) {
    assertRussianError(() => resolveLocationLinks(data, 'record'), /снимок/i);
  }
  for (const data of [{}, { locations: null }, { locations: {} }]) {
    assertRussianError(() => resolveLocationLinks(data, 'record'), 'locations', /массив/i);
  }
  const data = graph({ id: 'record' }, { id: '1' }, { id: ' quoted " ID ' }, { id: ' ' }, { id: '__proto__' });
  for (const id of [undefined, null, false, 1, '', {}, new String('record'), 'x'.repeat(101)]) {
    assertRussianError(() => resolveLocationLinks(data, id), 'exactLocationId', /строк/i, '1', '100');
  }
  for (const id of ['missing', ' record ', 'Record', 'quoted " ID', 'constructor']) {
    assertRussianError(() => resolveLocationLinks(data, id), id, /не найден/i);
  }
  for (const record of data.locations) assert.equal(resolveLocationLinks(data, record.id).location, record);
  for (const invalid of [graph(place('record', ['missing'])), graph(place('record', ['record'])),
    graph(place('record', ['other']), place('other', ['record'])), graph({ id: 'record', isLocation: 'true' }),
    graph({ id: 'record' }, place('unrelated', ['missing']))]) {
    assertRussianError(() => resolveLocationLinks(deepFreeze(invalid), 'record'));
  }
});

test('eligible targets are canonical records in original registry order including existing children and unmarked cross-faction markers', async () => {
  const { eligibleLocationLinkTargets } = await engineModule();
  assert.equal(typeof eligibleLocationLinkTargets, 'function');
  const data = fullSnapshot();
  data.locations[0].isLocation = true;
  data.locations[0].linkedLocationIds = ['stoneward-prison'];
  const before = structuredClone(data);
  deepFreeze(data);
  const candidates = eligibleLocationLinkTargets(data, 'military-district');
  assert.deepEqual(candidates, [data.locations[1], data.locations[2]]);
  assert.equal(candidates[0], data.locations[1]);
  assert.equal(candidates[1], data.locations[2]);
  assert.ok(!candidates.some(record => record.id === 'prison-inline'));
  assert.deepEqual(data, before);
  assert.deepEqual(eligibleLocationLinkTargets(graph({ id: 'legacy' }), 'legacy'), []);
  const legacy = fullSnapshot();
  assert.deepEqual(eligibleLocationLinkTargets(legacy, 'harbor'), legacy.locations.slice(0, 2));
});

test('eligible targets exclude every ancestor through nested and diamond paths without recursion or ownership changes', async () => {
  const { eligibleLocationLinkTargets, resolveLocationLinks, validateLocationLinks } = await engineModule();
  const data = fullSnapshot();
  data.locations[0].isLocation = true;
  data.locations[0].linkedLocationIds = ['stoneward-prison'];
  data.locations.unshift(place('grandparent', ['parent-left', 'parent-right']), place('parent-left', ['military-district']),
    place('parent-right', ['military-district']));
  const before = structuredClone(data);
  const json = JSON.stringify(data);
  deepFreeze(data);
  const eligible = eligibleLocationLinkTargets(data, 'military-district');
  assert.deepEqual(eligible, [data.locations[4], data.locations[5]]);
  assert.equal(eligible[0], data.locations[4]);
  assert.deepEqual(eligibleLocationLinkTargets(data, 'stoneward-prison'), [data.locations[5]]);
  const resolved = resolveLocationLinks(data, 'military-district');
  assert.equal(resolved.location, data.locations[3]);
  assert.equal(resolved.children[0], data.locations[4]);
  assert.equal(resolved.children[0].faction, 'gilneas');
  assert.equal(resolved.children[0].owner, 'Королевская стража');
  assert.equal(resolved.children[0].objects, data.locations[4].objects);
  assert.equal(resolved.children[0].objects[0].modifiers, data.locations[4].objects[0].modifiers);
  assert.equal(resolved.children[0].modifiers, data.locations[4].modifiers);
  assert.equal(resolved.location.objects, data.locations[3].objects);
  assert.deepEqual(data, before);
  assert.equal(JSON.stringify(data), json);
  const depth = 20000;
  const chain = { locations: Array.from({ length: depth }, (_, index) => place(`chain-${index}`, index + 1 < depth ? [`chain-${index + 1}`] : [])) };
  chain.locations.push({ id: 'independent' });
  deepFreeze(chain);
  assert.deepEqual(eligibleLocationLinkTargets(chain, `chain-${depth - 1}`), [chain.locations[depth]]);
  assert.deepEqual(eligibleLocationLinkTargets(chain, 'chain-1'), chain.locations.slice(2));
  const middle = resolveLocationLinks(chain, 'chain-10000');
  assert.equal(middle.children[0], chain.locations[10001]);
  assert.equal(middle.parents[0], chain.locations[9999]);
  assert.equal(validateLocationLinks(chain), true);
});

test('eligible API rejects missing input, missing exact records and malformed graphs instead of returning misleading options', async () => {
  const { eligibleLocationLinkTargets } = await engineModule();
  for (const data of [undefined, null, false, [], '', 1]) {
    assertRussianError(() => eligibleLocationLinkTargets(data, 'record'), /снимок/i);
  }
  for (const data of [{}, { locations: null }, { locations: {} }]) {
    assertRussianError(() => eligibleLocationLinkTargets(data, 'record'), 'locations', /массив/i);
  }
  const data = graph({ id: 'record' }, { id: '1' }, { id: ' quoted " ID ' }, { id: ' ' }, { id: '__proto__' });
  for (const id of [undefined, null, false, 1, '', {}, new String('record'), 'x'.repeat(101)]) {
    assertRussianError(() => eligibleLocationLinkTargets(data, id), 'exactLocationId', /строк/i, '1', '100');
  }
  for (const id of ['missing', ' record ', 'Record', 'quoted " ID', 'constructor']) {
    assertRussianError(() => eligibleLocationLinkTargets(data, id), id, /не найден/i);
  }
  for (const record of data.locations) {
    const result = eligibleLocationLinkTargets(data, record.id);
    assert.deepEqual(result, data.locations.filter(other => other !== record));
    for (const candidate of result) assert.equal(candidate, data.locations.find(other => other.id === candidate.id));
  }
  for (const invalid of [graph(place('record', ['missing'])), graph(place('record', ['record'])),
    graph(place('record', ['other']), place('other', ['record'])), graph({ id: 'record', isLocation: 'true' }),
    graph({ id: 'record' }, place('unrelated', ['missing']))]) {
    const before = structuredClone(invalid);
    assertRussianError(() => eligibleLocationLinkTargets(deepFreeze(invalid), 'record'));
    assert.deepEqual(invalid, before);
  }
});
