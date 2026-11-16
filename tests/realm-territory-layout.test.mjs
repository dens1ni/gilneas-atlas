import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { validate } from '../assets/js/territory-engine.mjs';
import { sovereignOf, factionMembers } from '../assets/js/model.mjs';

const module = await import('../assets/js/realm-territory-layout.mjs').catch(error => {
  if (error.code !== 'ERR_MODULE_NOT_FOUND') throw error;
  return {};
});
const generate = (...args) => {
  assert.equal(typeof module.generateRealmTerritoryLayout, 'function', 'export generateRealmTerritoryLayout');
  return module.generateRealmTerritoryLayout(...args);
};
function fixture(width = 128, height = 16) {
  const snapshot = {
    meta: { width, height, image: 'map.webp', mapRevision: 'map-v1' },
    factions: [
      { id: 'silverlaine', parent: 'crowley' }, { id: 'dalaran', parent: null },
      { id: 'gilneas', parent: null }, { id: 'crowley', parent: 'gilneas' },
      { id: 'lordaeron', parent: null }, { id: '  house  ', parent: 'gilneas' },
    ],
    locations: [], territories: [{ id: 'discard-me', faction: 'dalaran', points: [] }],
    territoryGrid: { cells: ['obsolete'] }, sources: [{ id: 0 }, { id: '0' }],
  };
  const plan = { version: 1, image: snapshot.meta.image, mapRevision: snapshot.meta.mapRevision,
    width: Math.ceil(width / 16), height: Math.ceil(height / 16), step: 16,
    mapWidth: width, mapHeight: height, keys: ['gilneas', 'lordaeron', 'dalaran'],
    cells: new Array(Math.ceil(width / 16) * Math.ceil(height / 16)).fill(1) };
  return { snapshot, plan };
}
function freeze(value) {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
const owner = (layer, index) => layer.cells[index] ? layer.keys[layer.cells[index] - 1] : null;

test('R02 canonical immediate pin owners make radius-clipped leaf areas within sovereign unions', () => {
  const { snapshot, plan } = fixture(256);
  plan.cells = [1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 3, 3, 0];
  snapshot.locations = [
    { id: 0, faction: 'crowley', x: 8, y: 8 },
    { id: '0', faction: 'silverlaine', x: 56, y: 8 },
    { id: 'repeat', faction: 'crowley', x: 104, y: 8 },
    { id: 'root-pin', faction: 'gilneas', x: 136, y: 8 },
    { id: 'foreign-crowley', faction: 'crowley', x: 168, y: 8 },
    { id: 'foreign-dalaran', faction: 'dalaran', x: 152, y: 8 },
    { id: 'lord', faction: 'lordaeron', x: 184, y: 8 },
  ];
  const layer = generate(snapshot, plan, { radius: 40 });
  assert.deepEqual(layer.cells.map((_, index) => owner(layer, index)), [
    'crowley', 'crowley', null, 'silverlaine', 'silverlaine', 'crowley', 'crowley', 'crowley',
    'gilneas', 'gilneas', 'lordaeron', 'lordaeron', 'lordaeron', 'dalaran', 'dalaran', null,
  ]);
  const union = new Set(factionMembers(snapshot.factions, 'crowley'));
  assert.equal(union.has('silverlaine'), true);
  assert.deepEqual(layer.cells.map((_, i) => i).filter(i => union.has(owner(layer, i))), [0, 1, 3, 4, 5, 6, 7]);
  for (let i = 0; i < plan.cells.length; i++) {
    assert.equal(owner(layer, i) === null, plan.cells[i] === 0);
    if (plan.cells[i]) assert.equal(sovereignOf(snapshot.factions, owner(layer, i)), plan.keys[plan.cells[i] - 1]);
  }
});

test('R03 rejects malformed JSON plans, dimensions, references and radii before inspecting cells', () => {
  const { snapshot, plan } = fixture();
  const reject = (input, source = snapshot, options) => assert.throws(() => generate(source, input, options));
  for (const patch of [
    { version: '1' }, { width: '8' }, { height: 0 }, { step: 8 }, { mapWidth: '128' },
    { mapHeight: Infinity }, { image: 'other.webp' }, { mapRevision: 'other-v1' },
    { keys: ['gilneas', 'lordaeron', 'crowley'] }, { keys: ['gilneas', 'missing', 'dalaran'] },
    { keys: ['gilneas', 'gilneas', 'dalaran'] }, { cells: new Array(8) },
    { cells: [1, 1, 1, 1, 1, 1, 1, '1'] }, { cells: [4, 1, 1, 1, 1, 1, 1, 1] },
    { extra: new Date() }, { extra: undefined }, { extra: NaN }, { extra: () => 1 },
  ]) reject({ ...plan, ...patch });
  const inherited = Object.create(plan); reject(inherited);
  const missing = { ...plan }; delete missing.keys; reject(missing);
  const sparseKeys = plan.keys.slice(); delete sparseKeys[0]; reject({ ...plan, keys: sparseKeys });
  for (const radius of ['260', null, NaN, Infinity, 39, 601, true]) reject(plan, snapshot, { radius });
  const huge = { ...plan, width: 131072, height: 2, mapWidth: 2097152, mapHeight: 32 };
  Object.defineProperty(huge, 'cells', { get() { assert.fail('oversized cells were accessed'); } });
  assert.throws(() => generate({ ...snapshot, meta: { ...snapshot.meta, width: 2097152, height: 32 } }, huge), /layout|grid|large/i);
  const invalidRoot = structuredClone(snapshot); invalidRoot.factions.find(f => f.id === 'gilneas').parent = 'lordaeron';
  reject(plan, invalidRoot);
  const missingParent = structuredClone(snapshot); missingParent.factions[0].parent = 'missing'; reject(plan, missingParent);
  const cycle = structuredClone(snapshot); cycle.factions.find(f => f.id === 'crowley').parent = 'silverlaine'; reject(plan, cycle);
  const unknownPin = structuredClone(snapshot); unknownPin.locations = [{ x: 8, y: 8, faction: 'missing' }]; reject(plan, unknownPin);
});

test('R04 clipped map-edge harbour pins seed land without painting water or coercing literal IDs', () => {
  const { snapshot, plan } = fixture(41, 17);
  plan.cells = [1, 0, 1, 0, 1, 1];
  snapshot.locations = [{ id: 0, faction: '  house  ', x: 41, y: 17 },
    { id: '0', faction: null, x: 8, y: 8 }, { faction: 'crowley', x: -1, y: 8 }];
  plan.generation = { identity: '  exact-id  ', sources: [0, '0'], evidence: false };
  Object.defineProperty(plan, '__proto__', { value: { opaque: 'safe' }, enumerable: true });
  const before = structuredClone({ snapshot, plan }); freeze(snapshot); freeze(plan);
  const layer = generate(snapshot, plan, { radius: 40 });
  assert.deepEqual(layer.cells.map((_, i) => owner(layer, i)), ['  house  ', null, '  house  ', null, '  house  ', '  house  ']);
  assert.deepEqual(layer.realmLayout.generation, plan.generation);
  assert.notEqual(layer.realmLayout.generation, plan.generation);
  assert.equal(Object.hasOwn(layer.realmLayout, '__proto__'), true);
  assert.equal(Object.getPrototypeOf(layer.realmLayout), Object.prototype);
  layer.realmLayout.generation.sources[0] = 9;
  assert.deepEqual({ snapshot, plan }, before);
});

test('R05 first literal location wins equal distance and the established strict radius cutoff is retained', () => {
  const { snapshot, plan } = fixture(80);
  snapshot.locations = [{ faction: 'silverlaine', x: 0, y: 8 }, { faction: 'crowley', x: 16, y: 8 }];
  assert.equal(owner(generate(snapshot, plan, { radius: 40 }), 0), 'silverlaine');
  snapshot.locations.reverse();
  assert.equal(owner(generate(snapshot, plan, { radius: 40 }), 0), 'crowley');
  snapshot.locations = [{ faction: '  house  ', x: 0, y: 8 }];
  assert.deepEqual(generate(snapshot, plan, { radius: 40 }).cells.map((_, i) => owner(generate(snapshot, plan, { radius: 40 }), i)),
    ['  house  ', '  house  ', 'gilneas', 'gilneas', 'gilneas']);
  assert.doesNotThrow(() => generate(snapshot, plan, { radius: 600 }));
});

test('R06 accepts the exact established cell limit with null-prototype JSON records', () => {
  const { snapshot, plan } = fixture(131072 * 16);
  const input = Object.assign(Object.create(null), plan);
  assert.equal(generate(snapshot, input).cells.length, 131072);
});

test('R07 actual atlas canonical pins retain exact inputs and sovereign membership', async () => {
  const snapshot = JSON.parse(await readFile(new URL('../assets/data/atlas.json', import.meta.url), 'utf8'));
  const { plan } = fixture(snapshot.meta.width, snapshot.meta.height);
  plan.image = snapshot.meta.image; plan.mapRevision = snapshot.meta.mapRevision;
  const before = structuredClone(snapshot); freeze(snapshot);
  const layer = generate(snapshot, plan);
  assert.deepEqual(snapshot, before);
  assert.deepEqual(layer.keys, snapshot.factions.map(f => f.id));
  assert.ok(layer.cells.some(value => layer.keys[value - 1] === 'crowley'));
  assert.ok(layer.cells.some(value => layer.keys[value - 1] === 'silverlaine'));
  for (const value of layer.cells) assert.equal(sovereignOf(snapshot.factions, layer.keys[value - 1]), 'gilneas');
});

test('R01 fills the complete authored sovereign domain without retaining old boundaries', () => {
  const { snapshot, plan } = fixture();
  plan.cells = [1, 1, 0, 1, 2, 2, 3, 0];
  const before = structuredClone({ snapshot, plan });
  freeze(snapshot); freeze(plan);
  const layer = generate(snapshot, plan);
  assert.deepEqual(layer.cells, [3, 3, 0, 3, 5, 5, 2, 0]);
  assert.deepEqual(layer.keys, snapshot.factions.map(f => f.id));
  assert.equal(validate(layer, snapshot.factions, snapshot.meta, { clone: false }), layer);
  assert.deepEqual(layer.realmLayout, { version: 1, image: 'map.webp', mapRevision: 'map-v1',
    rootKeys: plan.keys, domainCells: plan.cells });
  assert.deepEqual(layer.precision, { cellSizeMapUnits: 16, sampling: 'cell-centre', clippedEdgeCells: true });
  assert.equal(layer.migration.method, 'author-full-realm-layout');
  assert.equal(layer.migration.legacyPolygonsRetained, false);
  assert.equal(Object.hasOwn(layer.migration, 'polygonIds'), false);
  assert.equal(layer.radius, 260);
  assert.notEqual(layer.realmLayout.domainCells, plan.cells);
  assert.notEqual(layer.realmLayout.rootKeys, plan.keys);
  layer.realmLayout.domainCells[0] = 0; layer.keys[0] = 'changed';
  assert.deepEqual({ snapshot, plan }, before);
});
