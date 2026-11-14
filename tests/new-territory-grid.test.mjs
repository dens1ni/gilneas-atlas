import test from 'node:test';
import assert from 'node:assert/strict';
import * as model from '../assets/js/model.mjs';

// Small, explicitly test-only records; never additions to atlas lore.
function fixture() {
  return {
    version: 1,
    meta: { width: 96, height: 80 },
    factions: [
      { id: 'root', name: 'Тестовая держава', color: '#913e50', parent: null },
      { id: '  house  ', name: 'Тестовый вассал', color: '#559080', parent: 'root' },
      { id: 'unused', name: 'Тестовая свободная фракция', color: '#896bac', parent: null },
    ],
    locations: [{ id: 'test-place', name: 'Тестовая точка', x: 24, y: 24, faction: 'root', objects: [] }],
    territories: [{ id: 'test-polygon', faction: 'root', points: [[0, 0], [96, 0], [96, 80], [0, 80]],
      provenance: { sources: [0, '0'], note: '  Авторская реконструкция  ' } }],
    sources: [{ id: 0 }, { id: '0' }], nobles: [],
  };
}
function grid(patch = {}) {
  return { version: 1, width: 6, height: 5, step: 16, mapWidth: 96, mapHeight: 80,
    keys: ['root', '  house  ', 'unused'], cells: new Array(30).fill(1), radius: 260, ...patch };
}
function storage() {
  const entries = new Map();
  return { getItem: key => entries.get(key) ?? null, setItem: (key, value) => entries.set(key, value) };
}

test('invalid optional territory grids are rejected before replacing a stored snapshot', () => {
  const good = fixture();
  good.territoryGrid = grid();
  const saved = storage();
  model.saveDraft(saved, good);
  const previous = saved.getItem('gilneas-atlas-draft-v1');
  const bad = structuredClone(good);
  bad.territoryGrid.width = 1;
  const before = structuredClone(bad);
  assert.throws(() => model.saveDraft(saved, bad), /территор|сетк|grid/i);
  assert.deepEqual(bad, before);
  assert.equal(saved.getItem('gilneas-atlas-draft-v1'), previous);
});

test('grid schema rejects malformed values and oversized allocations while preserving full extensions', async () => {
  const E = await import('../assets/js/territory-engine.mjs');
  const raw = fixture();
  const original = grid({ provenance: { sources: [0, '0'], note: '  </script>  ' }, extension: { exact: false } });
  const cloned = E.validate(original, raw.factions, raw.meta);
  assert.deepEqual(cloned, original);
  cloned.extension.exact = true;
  assert.equal(original.extension.exact, false);
  const invalid = [null, [], grid({ version: '1' }), grid({ step: 0 }), grid({ step: 257 }),
    grid({ width: 1.5 }), grid({ height: 0 }), grid({ radius: 39 }), grid({ radius: 601 }),
    grid({ radius: '260' }), grid({ keys: ['root', 'root', 'unused'] }), grid({ keys: ['root', 'house', 'unused'] }),
    grid({ cells: new Array(29).fill(0) }), grid({ cells: [4, ...new Array(29).fill(0)] }),
    grid({ cells: [1.5, ...new Array(29).fill(0)] }), grid({ cells: new Array(30) }),
    grid({ mapWidth: 97 }), grid({ mapHeight: 81 })];
  for (const value of invalid) assert.throws(() => E.validate(value, raw.factions, raw.meta), /территор|grid/i);
  const huge = grid({ width: E.MAX_CELLS, height: 2 });
  Object.defineProperty(huge, 'cells', { get() { throw Error('cells must not be inspected after size cap fails'); } });
  assert.throws(() => model.normalizeData({ ...raw, territoryGrid: huge }), /территор|grid/i);
  assert.equal(Object.hasOwn(model.normalizeData(raw), 'territoryGrid'), false);
  const valid = { ...raw, territoryGrid: original };
  assert.deepEqual(model.deserializeSnapshot(model.serializeSnapshot(valid)).territoryGrid, original);
});

test('new optional grid provenance resolves exact source IDs before storage', () => {
  const raw = fixture();
  raw.territoryGrid = grid({ provenance: { sources: ['missing'] } });
  assert.throws(() => model.normalizeData(raw), /источник/i);
});

test('nearest-location generation uses exact centres, step16, and partial-edge map dimensions', async () => {
  const E = await import('../assets/js/territory-engine.mjs');
  assert.equal(typeof E.generate, 'function', 'port the actual Naitroud nearest-location engine');
  const meta = { width: 35, height: 33 };
  const factions = [{ id: 'left' }, { id: 'right' }];
  const locations = [{ x: 8, y: 8, faction: 'left' }, { x: 24, y: 8, faction: 'right' }];
  const layer = E.generate(locations, factions, 40, meta, point => point[1] < 32);
  assert.deepEqual([layer.width, layer.height, layer.step, layer.mapWidth, layer.mapHeight], [3, 3, 16, 35, 33]);
  assert.deepEqual(layer.cells, [1, 2, 2, 1, 2, 2, 0, 0, 0]);
  const noOffset = E.generate([{ x: 0, y: 0, faction: 'left' }], factions, 40, { width: 64, height: 16 });
  assert.deepEqual(noOffset.cells, [1, 1, 0, 0], 'an 11px source marker offset would wrongly fill the third cell');
  const actual = E.generate([], factions, 260, { width: 3247, height: 4860 });
  assert.equal(actual.cells.length, 61712);
  assert.equal(actual.cells.every(value => value === 0), true);
  assert.throws(() => E.generate([], factions, 39, meta), /радиус|территор/i);
  assert.throws(() => E.generate([], factions, 40, { width: 100000, height: 100000 }), /сетк|территор/i);
});

test('explicit migration rasterizes all legacy polygons with deepest vassal overriding ancestors', async () => {
  const module = await import('../assets/js/territory-data.mjs').catch(() => ({}));
  assert.equal(typeof module.prepareTerritoryGrid, 'function', 'bootstrap needs one explicit, immutable grid materializer');
  const raw = fixture();
  raw.factions.push({ id: 'cadet', name: 'Тестовый младший дом', color: '#aa8888', parent: '  house  ' });
  const polygon = (id, faction, left, top, right, bottom) => ({ id, faction,
    points: [[left, top], [right, top], [right, bottom], [left, bottom]], provenance: { sources: [0, '0'] } });
  // Intentionally place the sovereign last. Array order must not erase a vassal.
  raw.territories = [polygon('test-house-area', '  house  ', 16, 16, 80, 64),
    polygon('test-cadet-area', 'cadet', 32, 32, 64, 48), raw.territories[0]];
  const before = structuredClone(raw);
  const next = module.prepareTerritoryGrid(raw, point => point[0] !== 8);
  assert.deepEqual(raw, before);
  assert.deepEqual(next.territories, before.territories);
  assert.deepEqual(next.locations, model.normalizeData(raw).locations);
  assert.deepEqual(next.territoryGrid.keys, raw.factions.map(f => f.id));
  assert.equal(next.territoryGrid.cells[0], 0, 'inactive-mask cells stay unclaimed');
  assert.equal(next.territoryGrid.cells[1], 1);
  assert.equal(next.territoryGrid.cells[7], 2);
  assert.equal(next.territoryGrid.cells[14], 4);
  assert.deepEqual(next.territoryGrid.migration.polygonIds, before.territories.map(t => t.id));
  assert.equal(next.territoryGrid.precision.cellSizeMapUnits, 16);
  next.territoryGrid.cells[14] = 0;
  next.locations[0].x = 64;
  const preparedAgain = module.prepareTerritoryGrid(next, () => false);
  assert.deepEqual(preparedAgain.territoryGrid, next.territoryGrid, 'existing manual state is never regenerated');
  assert.notEqual(preparedAgain.territoryGrid, next.territoryGrid);
});

test('source circular brush paints exact map centres and cannot change inactive cells', async () => {
  const E = await import('../assets/js/territory-engine.mjs');
  assert.equal(typeof E.paint, 'function');
  const layer = grid({ cells: new Array(30).fill(0) });
  const before = layer.cells.slice();
  const changed = E.paint(layer, 24, 24, 17, 2, point => point[0] !== 8);
  assert.equal(changed, 4);
  assert.deepEqual(layer.cells.map((value, i) => value !== before[i] ? i : -1).filter(i => i >= 0), [1, 7, 8, 13]);
  assert.equal(E.paint(layer, 24, 24, 17, 2, () => true), 1);
  assert.equal(E.paint(layer, 24, 24, 17, 0, () => true), 5);
  assert.equal(layer.cells.every(value => value === 0), true);
  for (const params of [[NaN, 1, 2, 1], [1, Infinity, 2, 1], [1, 1, -1, 1], [1, 1, 5, 4]]) {
    assert.throws(() => E.paint(layer, ...params), /кист|территор/i);
    assert.equal(layer.cells.every(value => value === 0), true);
  }
});

test('deleting a grid-painted faction is rejected and unused key deletion remaps owner indices losslessly', () => {
  const raw = fixture();
  raw.territoryGrid = grid({ cells: new Array(30).fill(2) });
  const before = structuredClone(raw);
  assert.throws(() => model.deleteFaction(raw, '  house  '), /использ|ссыл|завис/i);
  assert.deepEqual(raw, before);
  // Place an unused key before a painted owner, so deleting it must renumber cells.
  raw.territoryGrid.keys = ['unused', 'root', '  house  '];
  raw.territoryGrid.cells.fill(3);
  const next = model.deleteFaction(raw, 'unused');
  assert.deepEqual(next.territoryGrid.keys, ['root', '  house  ']);
  assert.ok(next.territoryGrid.cells.every(value => value === 2));
  assert.deepEqual(next.territories, raw.territories);
});

test('painted grid ownership survives location, object, faction relation and legacy polygon CRUD plus JSON storage', async () => {
  const { prepareTerritoryGrid } = await import('../assets/js/territory-data.mjs');
  const data = prepareTerritoryGrid(fixture());
  data.territoryGrid.cells[7] = 2;
  data.territoryGrid.future = { exact: '  AUTHOR FIELD  ' };
  const before = structuredClone(data.territoryGrid);
  let edited = model.updateLocation(data, 'test-place', { x: 64, description: '  PLAYER DESCRIPTION  ' });
  edited = model.upsertObject(edited, 'test-place', { id: 'test-mill', name: 'Тестовая мельница', type: 'building', faction: null });
  edited = model.upsertFaction(edited, { id: '  house  ', parent: null, color: '#123456' });
  edited = model.removeTerritory(edited, 'test-polygon');
  assert.deepEqual(edited.territoryGrid, before);
  const saved = storage(); model.saveDraft(saved, edited);
  assert.deepEqual(model.loadDraft(saved, data).data, edited);
  assert.deepEqual(model.deserializeSnapshot(model.serializeSnapshot(edited)).territoryGrid, before);
  assert.deepEqual(prepareTerritoryGrid(edited, () => false).territoryGrid, before);
  assert.deepEqual(data.territoryGrid, before);
});
