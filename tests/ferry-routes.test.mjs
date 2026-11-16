import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';

const MODULE = new URL('../assets/js/ferry-routes.mjs', import.meta.url);
const CSS = new URL('../assets/css/ferry-routes.css', import.meta.url);
const ferryModule = () => import(MODULE);

// All records and coordinates below are synthetic unit fixtures, never atlas data.
const syntheticRoute = () => ({
  id: 'test-route-a', fromLocationId: 'test-dock-a', toLocationId: 'test-dock-b',
  points: [[10, 20], [40, 30], [90, 60]],
  author: { note: '  <svg onload="literal">  ', values: [false, null, '', 0] },
});
const syntheticSnapshot = (withNetwork = true) => {
  const snapshot = {
    version: 1,
    meta: { image: 'test-only-map.svg', mapRevision: 'test-revision', width: 100, height: 80,
      author: { note: '  unchanged  ', values: [null, false, 0, ''] } },
    locations: [
      { id: 'test-dock-a', type: 'ferry', x: 10, y: 20, objects: [
        { id: 'test-inline-ferry', type: 'ferry', author: { untouched: false } },
      ] },
      { id: 'test-dock-b', type: 'ferry', x: 90, y: 60, objects: [] },
      { id: 'test-dock-c', type: 'ferry', x: 60, y: 10, objects: [] },
      { id: 'test-harbor', type: 'harbor', x: 20, y: 40, name: 'test-dock-by-name', objects: [] },
    ],
    factions: [{ id: 'test-faction', author: { zero: 0 } }],
    nobles: [{ id: 'test-noble', author: { nil: null } }],
    sources: [{ id: 1, title: 'Synthetic numeric ID' }, { id: 'test-source', title: '' }],
    territories: [], royalCouncil: { members: [] },
    authorExtension: JSON.parse('{"__proto__":{"literal":true},"constructor":"own JSON key","keep":[false,null,"",0]}'),
  };
  if (withNetwork) snapshot.meta.ferryNetwork = {
    image: snapshot.meta.image, mapRevision: snapshot.meta.mapRevision,
    width: snapshot.meta.width, height: snapshot.meta.height,
    routes: [syntheticRoute()],
    author: { routePlanning: 'opaque JSON, not inferred', values: ['', null, false, 0] },
    ...JSON.parse('{"__proto__":{"opaque":true},"constructor":"literal extension"}'),
  };
  return snapshot;
};
const deepFreeze = value => {
  // Non-JSON typed arrays are rejection fixtures; Node cannot freeze their elements.
  if (ArrayBuffer.isView(value)) return value;
  if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
    for (const item of Object.values(value)) deepFreeze(item);
    Object.freeze(value);
  }
  return value;
};
const assertRussianError = (run, ...details) => {
  assert.throws(run, error => {
    assert.ok(error instanceof Error);
    assert.match(error.message, /[А-Яа-яЁё]/);
    for (const detail of details) {
      if (detail instanceof RegExp) assert.match(error.message, detail);
      else assert.ok(error.message.includes(detail), `Missing ${JSON.stringify(detail)} in ${JSON.stringify(error.message)}`);
    }
    return true;
  });
};
const assertRejected = (validate, snapshot, ...details) => {
  const before = structuredClone(snapshot);
  const json = JSON.stringify(snapshot);
  deepFreeze(snapshot);
  assertRussianError(() => validate(snapshot), ...details);
  assert.deepEqual(snapshot, before);
  assert.equal(JSON.stringify(snapshot), json);
};
const assertUnchanged = (snapshot, before, json) => {
  assert.deepEqual(snapshot, before);
  assert.equal(JSON.stringify(snapshot), json);
};

test('V01 absent ferryNetwork stays absent on full frozen snapshots without a DOM', async () => {
  assert.ok(existsSync(MODULE), 'Ожидается модуль необязательных паромных маршрутов');
  const { validateFerryNetwork } = await ferryModule();
  assert.equal(typeof validateFerryNetwork, 'function');
  assert.equal(typeof globalThis.document, 'undefined');
  for (const snapshot of [syntheticSnapshot(false), {}, { meta: {} }]) {
    const before = structuredClone(snapshot);
    const json = JSON.stringify(snapshot);
    deepFreeze(snapshot);
    assert.equal(validateFerryNetwork(snapshot), true);
    assertUnchanged(snapshot, before, json);
    assert.equal(Object.hasOwn(snapshot.meta ?? {}, 'ferryNetwork'), false);
  }
});

test('V02 present ferryNetwork must be a record; malformed envelopes reject in Russian', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const snapshot of [undefined, null, [], '', 1, false]) {
    assertRussianError(() => validateFerryNetwork(snapshot), /снимок/i);
  }
  for (const value of [undefined, null, [], '', false, 1]) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork = value;
    assertRejected(validateFerryNetwork, snapshot, 'meta.ferryNetwork', /запис|объект/i);
  }
});

test('V03 network image and revision are required literal strings without normalization', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const image of [undefined, null, false, 1, {}, [], new String('test-only-map.svg'), '',
    ' test-only-map.svg', 'test-only-map.svg ', '\ttest-only-map.svg', 'map\n.svg', 'map\u0000.svg',
    'map\u007f.svg', 'map\u0085.svg', '\u00a0test-only-map.svg']) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.image = image;
    assertRejected(validateFerryNetwork, snapshot, 'meta.ferryNetwork.image', /строк|путь/i);
  }
  const missingImage = syntheticSnapshot();
  delete missingImage.meta.ferryNetwork.image;
  assertRejected(validateFerryNetwork, missingImage, 'meta.ferryNetwork.image');
  for (const mapRevision of [undefined, null, false, 1, {}, [], new String('r'), '']) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.mapRevision = mapRevision;
    assertRejected(validateFerryNetwork, snapshot, 'meta.ferryNetwork.mapRevision', /строк/i);
  }
  const missingRevision = syntheticSnapshot();
  delete missingRevision.meta.ferryNetwork.mapRevision;
  assertRejected(validateFerryNetwork, missingRevision, 'meta.ferryNetwork.mapRevision');
  for (const mapRevision of ['test-revision', '  author revision  ', ' ', '\n']) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.mapRevision = mapRevision;
    snapshot.meta.ferryNetwork.image = 'literal-path-with-internal space.svg';
    const before = structuredClone(snapshot);
    const json = JSON.stringify(snapshot);
    const network = snapshot.meta.ferryNetwork;
    const route = network.routes[0];
    deepFreeze(snapshot);
    assert.equal(validateFerryNetwork(snapshot), true);
    assertUnchanged(snapshot, before, json);
    assert.equal(snapshot.meta.ferryNetwork, network);
    assert.equal(snapshot.meta.ferryNetwork.routes[0], route);
    assert.equal(Object.hasOwn(network, '__proto__'), true);
  }
});

test('V04 network dimensions are finite positive numbers, never coerced or tied to current map', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const field of ['width', 'height']) {
    for (const value of [undefined, null, false, true, '', '100', 0, -1, NaN, Infinity, -Infinity, [], {}, new Number(100)]) {
      const snapshot = syntheticSnapshot();
      snapshot.meta.ferryNetwork[field] = value;
      assertRejected(validateFerryNetwork, snapshot, `meta.ferryNetwork.${field}`, /конечн/i, /положительн/i);
    }
    const missing = syntheticSnapshot();
    delete missing.meta.ferryNetwork[field];
    assertRejected(validateFerryNetwork, missing, `meta.ferryNetwork.${field}`);
  }
  for (const dimensions of [[0.5, 0.25], [Number.MIN_VALUE, Number.MAX_VALUE], [200, 160]]) {
    const snapshot = syntheticSnapshot();
    [snapshot.meta.ferryNetwork.width, snapshot.meta.ferryNetwork.height] = dimensions;
    snapshot.meta.ferryNetwork.routes = [];
    const before = structuredClone(snapshot);
    const json = JSON.stringify(snapshot);
    deepFreeze(snapshot);
    assert.equal(validateFerryNetwork(snapshot), true);
    assertUnchanged(snapshot, before, json);
  }
});

test('V05 routes is a required array capped at 64; explicit empty is deliberate clearing', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const routes of [undefined, null, false, 1, '', 'route', {}, new Set()]) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.routes = routes;
    assertRejected(validateFerryNetwork, snapshot, 'meta.ferryNetwork.routes', /массив/i);
  }
  const missing = syntheticSnapshot();
  delete missing.meta.ferryNetwork.routes;
  assertRejected(validateFerryNetwork, missing, 'meta.ferryNetwork.routes');
  const tooMany = syntheticSnapshot();
  tooMany.meta.ferryNetwork.routes = Array.from({ length: 65 }, (_, i) => ({ ...syntheticRoute(), id: `test-route-${i}` }));
  assertRejected(validateFerryNetwork, tooMany, 'meta.ferryNetwork.routes', '64');
  for (const count of [0, 64]) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.routes = Array.from({ length: count }, (_, i) => ({ ...syntheticRoute(), id: `test-route-${i}` }));
    const before = structuredClone(snapshot);
    const json = JSON.stringify(snapshot);
    const claimed = [];
    deepFreeze(snapshot);
    assert.equal(validateFerryNetwork(snapshot), true);
    if (count === 0) assert.equal(validateFerryNetwork(snapshot, { claim: (...args) => claimed.push(args) }), true);
    assertUnchanged(snapshot, before, json);
    assert.equal(snapshot.meta.ferryNetwork.routes.length, count);
    assert.deepEqual(claimed, []);
  }
});

test('V06 every route requires a record with an exact string ID of length 1 through 100', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const route of [undefined, null, [], '', 1, false]) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.routes[0] = route;
    assertRejected(validateFerryNetwork, snapshot, 'meta.ferryNetwork.routes[0]', /запис/i);
  }
  const sparse = syntheticSnapshot();
  sparse.meta.ferryNetwork.routes = Array(1);
  assertRejected(validateFerryNetwork, sparse, 'meta.ferryNetwork.routes[0]');
  for (const id of [undefined, null, false, 1, {}, [], new String('route'), '', 'x'.repeat(101)]) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.routes[0].id = id;
    assertRejected(validateFerryNetwork, snapshot, 'meta.ferryNetwork.routes[0].id', '1', '100', /строк/i);
  }
  const missing = syntheticSnapshot();
  delete missing.meta.ferryNetwork.routes[0].id;
  assertRejected(validateFerryNetwork, missing, 'meta.ferryNetwork.routes[0].id');
  for (const id of ['1', ' ', '\n\t', '__proto__', 'constructor', ' " literal ID " ', 'x'.repeat(100)]) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.routes[0].id = id;
    const before = structuredClone(snapshot);
    const json = JSON.stringify(snapshot);
    deepFreeze(snapshot);
    assert.equal(validateFerryNetwork(snapshot), true);
    assertUnchanged(snapshot, before, json);
  }
});

test('V07 duplicate route IDs reject locally without deduplicating authored routes', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const id of ['test-route-a', '__proto__', 'constructor', ' " literal " ']) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.routes = [
      { ...syntheticRoute(), id }, { ...syntheticRoute(), id, toLocationId: 'test-dock-c' },
    ];
    assertRejected(validateFerryNetwork, snapshot, 'meta.ferryNetwork.routes[1]', id, /повтор/i);
  }
  const snapshot = syntheticSnapshot();
  snapshot.meta.ferryNetwork.routes = ['route', 'Route', ' route', 'route '].map(id => ({ ...syntheticRoute(), id }));
  const before = structuredClone(snapshot);
  const json = JSON.stringify(snapshot);
  deepFreeze(snapshot);
  assert.equal(validateFerryNetwork(snapshot), true);
  assertUnchanged(snapshot, before, json);
});

test('V08 endpoint tokens require exact string IDs before canonical lookup', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const field of ['fromLocationId', 'toLocationId']) {
    for (const token of [undefined, null, false, 1, {}, [], new String('test-dock-b'), '', 'x'.repeat(101)]) {
      const snapshot = syntheticSnapshot();
      // Even malformed IDs existing in another record must not legitimize a token.
      snapshot.locations.push({ id: token, type: 'ferry', x: 1, y: 2 });
      snapshot.meta.ferryNetwork.routes[0][field] = token;
      assertRejected(validateFerryNetwork, snapshot, `meta.ferryNetwork.routes[0].${field}`, '1', '100', /строк/i);
    }
    const missing = syntheticSnapshot();
    delete missing.meta.ferryNetwork.routes[0][field];
    assertRejected(validateFerryNetwork, missing, `meta.ferryNetwork.routes[0].${field}`);
  }
  const snapshot = syntheticSnapshot();
  snapshot.locations[0].id = ' dock literal ';
  snapshot.locations[1].id = 'x'.repeat(100);
  snapshot.meta.ferryNetwork.routes[0].fromLocationId = snapshot.locations[0].id;
  snapshot.meta.ferryNetwork.routes[0].toLocationId = snapshot.locations[1].id;
  const before = structuredClone(snapshot);
  const json = JSON.stringify(snapshot);
  deepFreeze(snapshot);
  assert.equal(validateFerryNetwork(snapshot), true);
  assertUnchanged(snapshot, before, json);
});

test('V09 endpoints resolve only unique canonical locations of literal type ferry', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const field of ['fromLocationId', 'toLocationId']) {
    for (const token of ['missing', 'test-inline-ferry', 'test-noble', 'test-faction', 'test-source', 'test-dock-by-name',
      'TEST-DOCK-A', ' test-dock-a', 'test-dock-b ']) {
      const snapshot = syntheticSnapshot();
      snapshot.meta.ferryNetwork.routes[0][field] = token;
      assertRejected(validateFerryNetwork, snapshot, `meta.ferryNetwork.routes[0].${field}`, token, 'locations', /не найден/i);
    }
    const wrongType = syntheticSnapshot();
    wrongType.meta.ferryNetwork.routes[0][field] = 'test-harbor';
    assertRejected(validateFerryNetwork, wrongType, `meta.ferryNetwork.routes[0].${field}`, 'ferry', /тип/i);
  }
  for (const type of [undefined, null, '', 'Ferry', ' ferry', 'ferry ', 1, { id: 'ferry' }]) {
    const snapshot = syntheticSnapshot();
    snapshot.locations[1].type = type;
    assertRejected(validateFerryNetwork, snapshot, 'toLocationId', 'ferry', /тип/i);
  }
  for (const locations of [undefined, null, {}, '', false]) {
    const snapshot = syntheticSnapshot();
    snapshot.locations = locations;
    assertRejected(validateFerryNetwork, snapshot, 'locations', /массив/i);
  }
  const duplicate = syntheticSnapshot();
  duplicate.locations.push({ ...duplicate.locations[1] });
  assertRejected(validateFerryNetwork, duplicate, 'toLocationId', 'test-dock-b', /повтор|неоднознач/i);
  for (const id of ['1', '__proto__', 'constructor', ' quoted dock ']) {
    const snapshot = syntheticSnapshot();
    snapshot.locations[1].id = id;
    snapshot.meta.ferryNetwork.routes[0].toLocationId = id;
    const before = structuredClone(snapshot);
    const json = JSON.stringify(snapshot);
    deepFreeze(snapshot);
    assert.equal(validateFerryNetwork(snapshot), true);
    assertUnchanged(snapshot, before, json);
  }
});

test('V10 a route cannot connect the same literal canonical dock to itself', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const id of ['test-dock-a', '__proto__', ' quoted dock ']) {
    const snapshot = syntheticSnapshot();
    snapshot.locations[0].id = id;
    snapshot.meta.ferryNetwork.routes[0].fromLocationId = id;
    snapshot.meta.ferryNetwork.routes[0].toLocationId = id;
    assertRejected(validateFerryNetwork, snapshot, 'meta.ferryNetwork.routes[0]', 'fromLocationId', 'toLocationId', /разн|сам/i);
  }
});

test('V11 points is a required array of 2 through 4096 authored vertices', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const points of [undefined, null, false, '', '10,20 90,60', {}, new Set(), [], [[10, 20]],
    Array.from({ length: 4097 }, (_, i) => [i % 2, 0])]) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.routes[0].points = points;
    assertRejected(validateFerryNetwork, snapshot, 'meta.ferryNetwork.routes[0].points', '2', '4096', /массив/i);
  }
  const missing = syntheticSnapshot();
  delete missing.meta.ferryNetwork.routes[0].points;
  assertRejected(validateFerryNetwork, missing, 'meta.ferryNetwork.routes[0].points');
  for (const points of [[[0, 0], [100, 80]], Array.from({ length: 4096 }, (_, i) => [i % 2, 0])]) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.routes[0].points = points;
    const before = structuredClone(snapshot);
    const json = JSON.stringify(snapshot);
    deepFreeze(snapshot);
    assert.equal(validateFerryNetwork(snapshot), true);
    assertUnchanged(snapshot, before, json);
  }
});

test('V12 vertices are dense finite two-number pairs, not strings or partial pairs', async () => {
  const { validateFerryNetwork } = await ferryModule();
  const sparsePair = Array(2); sparsePair[1] = 30;
  for (const point of [undefined, null, false, 1, '', '40,30', {}, new Float64Array([40, 30]),
    [], [40], [40, 30, 0], ['40', 30], [40, '30'], [null, 30], [40, false],
    [NaN, 30], [40, Infinity], [-Infinity, 30], [new Number(40), 30], sparsePair]) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.routes[0].points[1] = point;
    assertRejected(validateFerryNetwork, snapshot, 'meta.ferryNetwork.routes[0].points[1]', /пар|два|двух/i, /конечн/i);
  }
  const missingPair = syntheticSnapshot();
  delete missingPair.meta.ferryNetwork.routes[0].points[1];
  assertRejected(validateFerryNetwork, missingPair, 'meta.ferryNetwork.routes[0].points[1]');
  const snapshot = syntheticSnapshot();
  snapshot.meta.ferryNetwork.routes[0].points = [[0, 0], [0.125, 0.25], [100, 80]];
  snapshot.locations[0].x = 12;
  snapshot.locations[1].y = 61;
  const before = structuredClone(snapshot);
  const json = JSON.stringify(snapshot);
  deepFreeze(snapshot);
  // Intentional pin moves remain valid metadata; renderer hides unmatched endpoints.
  assert.equal(validateFerryNetwork(snapshot), true);
  assertUnchanged(snapshot, before, json);
});

test('V13 every vertex is inside the network dimensions including exact boundaries', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const point of [[-0.001, 30], [40, -0.001], [100.001, 30], [40, 80.001]]) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.routes[0].points[1] = point;
    assertRejected(validateFerryNetwork, snapshot, 'meta.ferryNetwork.routes[0].points[1]', /границ|размер/i);
  }
  const smallerNetwork = syntheticSnapshot();
  smallerNetwork.meta.ferryNetwork.width = 50;
  assertRejected(validateFerryNetwork, smallerNetwork, 'points[2]', /границ|размер/i);
  const snapshot = syntheticSnapshot();
  snapshot.meta.ferryNetwork.width = 200;
  snapshot.meta.ferryNetwork.height = 160;
  snapshot.meta.ferryNetwork.routes[0].points = [[-0, 0], [200, 160], [150.5, 120.25]];
  const before = structuredClone(snapshot);
  const json = JSON.stringify(snapshot);
  deepFreeze(snapshot);
  assert.equal(validateFerryNetwork(snapshot), true);
  assertUnchanged(snapshot, before, json);
  assert.equal(Object.is(snapshot.meta.ferryNetwork.routes[0].points[0][0], -0), true);
});

test('V14 consecutive identical vertices reject without changing nonconsecutive revisits', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const points of [[[10, 20], [10, 20]], [[10, 20], [40, 30], [40, 30], [90, 60]],
    [[0, 0], [-0, 0], [90, 60]]]) {
    const snapshot = syntheticSnapshot();
    snapshot.meta.ferryNetwork.routes[0].points = points;
    assertRejected(validateFerryNetwork, snapshot, 'meta.ferryNetwork.routes[0].points', /подряд|соседн|последовательн/i, /повтор|одинаков/i);
  }
  const snapshot = syntheticSnapshot();
  snapshot.meta.ferryNetwork.routes[0].points = [[10, 20], [40, 30], [10, 20], [90, 60]];
  const before = structuredClone(snapshot);
  const json = JSON.stringify(snapshot);
  deepFreeze(snapshot);
  assert.equal(validateFerryNetwork(snapshot), true);
  assertUnchanged(snapshot, before, json);
});

test('V15 claim shares whole-model IDs with original routes and exact Russian labels', async () => {
  const { validateFerryNetwork } = await ferryModule();
  const snapshot = syntheticSnapshot();
  snapshot.meta.ferryNetwork.routes.push({ ...syntheticRoute(), id: 'test-route-b', toLocationId: 'test-dock-c' });
  const before = structuredClone(snapshot);
  const json = JSON.stringify(snapshot);
  deepFreeze(snapshot);
  const calls = [];
  assert.equal(validateFerryNetwork(snapshot, { claim: (...args) => calls.push(args) }), true);
  assert.equal(calls.length, 2);
  snapshot.meta.ferryNetwork.routes.forEach((route, index) => {
    assert.equal(calls[index][0], route);
    assert.deepEqual(calls[index], [route, 'паромный маршрут']);
  });
  assertUnchanged(snapshot, before, json);
  for (const id of ['test-dock-a', 'test-inline-ferry', 'test-faction', 'test-noble', 'test-source']) {
    const collision = syntheticSnapshot();
    collision.meta.ferryNetwork.routes[0].id = id;
    const collisionBefore = structuredClone(collision);
    const collisionJSON = JSON.stringify(collision);
    deepFreeze(collision);
    const failure = new Error(`Повтор ID модели: ${id}`);
    assert.throws(() => validateFerryNetwork(collision, { claim: record => {
      assert.equal(record, collision.meta.ferryNetwork.routes[0]);
      throw failure;
    } }), error => error === failure);
    assertUnchanged(collision, collisionBefore, collisionJSON);
    // Without the model callback this module owns route IDs only.
    assert.equal(validateFerryNetwork(collision), true);
  }
  const localDuplicate = syntheticSnapshot();
  localDuplicate.meta.ferryNetwork.routes.push(syntheticRoute());
  assertRussianError(() => validateFerryNetwork(localDuplicate, { claim: () => {} }), /повтор/i);
  const absentCalls = [];
  assert.equal(validateFerryNetwork(deepFreeze(syntheticSnapshot(false)), { claim: (...args) => absentCalls.push(args) }), true);
  assert.deepEqual(absentCalls, []);
  for (const claim of [null, false, 1, 'claim', {}, []]) {
    assertRussianError(() => validateFerryNetwork(snapshot, { claim }), 'claim', /функц/i);
  }
  for (const broken of ['id', 'points', 'toLocationId']) {
    const invalid = syntheticSnapshot();
    invalid.meta.ferryNetwork.routes[0][broken] = undefined;
    const invalidCalls = [];
    assertRussianError(() => validateFerryNetwork(invalid, { claim: (...args) => invalidCalls.push(args) }), broken);
    assert.deepEqual(invalidCalls, []);
  }
});

test('V16 required metadata fields must be own JSON values rather than prototype fallbacks', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const field of ['image', 'mapRevision', 'width', 'height', 'routes']) {
    const snapshot = syntheticSnapshot();
    const network = snapshot.meta.ferryNetwork;
    const inherited = network[field];
    delete network[field];
    Object.setPrototypeOf(network, { [field]: inherited });
    deepFreeze(snapshot);
    assertRussianError(() => validateFerryNetwork(snapshot), `meta.ferryNetwork.${field}`);
    assert.equal(Object.hasOwn(network, field), false);
    assert.equal(network[field], inherited);
  }
  for (const field of ['id', 'fromLocationId', 'toLocationId', 'points']) {
    const snapshot = syntheticSnapshot();
    const route = snapshot.meta.ferryNetwork.routes[0];
    const inherited = route[field];
    delete route[field];
    Object.setPrototypeOf(route, { [field]: inherited });
    deepFreeze(snapshot);
    assertRussianError(() => validateFerryNetwork(snapshot), `meta.ferryNetwork.routes[0].${field}`);
    assert.equal(Object.hasOwn(route, field), false);
    assert.equal(route[field], inherited);
  }
  const absent = syntheticSnapshot(false);
  Object.setPrototypeOf(absent.meta, { ferryNetwork: syntheticSnapshot().meta.ferryNetwork });
  assert.equal(validateFerryNetwork(deepFreeze(absent)), true);
  assert.equal(Object.hasOwn(absent.meta, 'ferryNetwork'), false);
  const snapshot = syntheticSnapshot();
  Object.setPrototypeOf(snapshot.meta.ferryNetwork, null);
  Object.setPrototypeOf(snapshot.meta.ferryNetwork.routes[0], null);
  assert.equal(validateFerryNetwork(deepFreeze(snapshot)), true);
});

test('V17 inherited array slots cannot stand in for missing routes or coordinate pairs', async () => {
  const { validateFerryNetwork } = await ferryModule();
  for (const kind of ['route', 'vertex', 'coordinate']) {
    const snapshot = syntheticSnapshot();
    let array, expectedPath;
    if (kind === 'route') {
      array = Array(1);
      const prototype = Object.create(Array.prototype);
      prototype[0] = syntheticRoute();
      Object.setPrototypeOf(array, prototype);
      snapshot.meta.ferryNetwork.routes = array;
      expectedPath = 'meta.ferryNetwork.routes[0]';
    } else if (kind === 'vertex') {
      array = Array(2); array[1] = [90, 60];
      const prototype = Object.create(Array.prototype);
      prototype[0] = [10, 20];
      Object.setPrototypeOf(array, prototype);
      snapshot.meta.ferryNetwork.routes[0].points = array;
      expectedPath = 'meta.ferryNetwork.routes[0].points[0]';
    } else {
      array = Array(2); array[1] = 20;
      const prototype = Object.create(Array.prototype);
      prototype[0] = 10;
      Object.setPrototypeOf(array, prototype);
      snapshot.meta.ferryNetwork.routes[0].points[0] = array;
      expectedPath = 'meta.ferryNetwork.routes[0].points[0]';
    }
    const json = JSON.stringify(snapshot);
    deepFreeze(snapshot);
    assertRussianError(() => validateFerryNetwork(snapshot), expectedPath);
    assert.equal(Object.hasOwn(array, 0), false);
    assert.equal(JSON.stringify(snapshot), json);
  }
});

// Deterministic DOM fake: attribute/tree safety only, NOT native browser evidence.
const SVG_NS = 'http://www.w3.org/2000/svg';
class UnitElement {
  constructor(ownerDocument, namespaceURI, localName) {
    this.ownerDocument = ownerDocument;
    this.namespaceURI = namespaceURI;
    this.localName = localName;
    this.attributes = new Map();
    this.style = {};
    this.children = [];
    this.parentNode = null;
  }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  append(...nodes) {
    for (const node of nodes) {
      assert.ok(node instanceof UnitElement, 'Only explicit element nodes may be appended');
      node.remove();
      node.parentNode = this;
      this.children.push(node);
    }
  }
  replaceChildren(...nodes) {
    for (const child of this.children) child.parentNode = null;
    this.children = [];
    this.append(...nodes);
  }
  remove() {
    if (!this.parentNode) return;
    const siblings = this.parentNode.children;
    siblings.splice(siblings.indexOf(this), 1);
    this.parentNode = null;
  }
  querySelectorAll(selector) {
    assert.equal(selector, '#ferry-routes', 'Do not interpolate authored IDs into selectors');
    const found = [];
    const visit = node => {
      for (const child of node.children) {
        if (child.getAttribute('id') === 'ferry-routes') found.push(child);
        visit(child);
      }
    };
    visit(this);
    return found;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] ?? null; }
  set innerHTML(_) { assert.fail('innerHTML is not allowed for ferry vectors'); }
  insertAdjacentHTML() { assert.fail('insertAdjacentHTML is not allowed for ferry vectors'); }
}
const unitDOM = () => {
  const created = [];
  const document = {
    createElementNS(namespace, tag) {
      assert.equal(namespace, SVG_NS);
      assert.ok(['svg', 'polyline'].includes(tag), `Unexpected vector ${tag}`);
      const node = new UnitElement(document, namespace, tag);
      created.push(node);
      return node;
    },
    getElementById(id) { assert.equal(id, 'world'); return world; },
    createElement() { assert.fail('Only createElementNS is allowed for route vectors'); },
  };
  const world = new UnitElement(document, null, 'div');
  world.setAttribute('id', 'world');
  return { document, world, created };
};
const temporaryGlobal = (t, name, descriptor) => {
  const original = Object.getOwnPropertyDescriptor(globalThis, name);
  Object.defineProperty(globalThis, name, { configurable: true, ...descriptor });
  t.after(() => {
    if (original) Object.defineProperty(globalThis, name, original);
    else delete globalThis[name];
  });
};
const routeVectors = world => world.querySelector('#ferry-routes')?.children ?? [];
const assertRoutePair = (world, route) => {
  const nodes = routeVectors(world).filter(node => node.getAttribute('data-ferry-route') === route.id);
  assert.equal(nodes.length, 2);
  assert.deepEqual(nodes.map(node => node.getAttribute('class')), ['ferry-route-halo', 'ferry-route-line']);
  for (const node of nodes) {
    assert.equal(node.namespaceURI, SVG_NS);
    assert.equal(node.localName, 'polyline');
    assert.equal(node.getAttribute('points'), route.points.map(point => point.join(',')).join(' '));
    assert.equal(node.getAttribute('pointer-events'), 'none');
    assert.equal(node.getAttribute('d'), null);
    assert.deepEqual([...node.attributes.keys()].sort(), ['class', 'data-ferry-route', 'pointer-events', 'points']);
    assert.equal(node.children.length, 0);
  }
  return nodes;
};

test('R01 DOM fake: renderer creates one inert vector frame at the current map dimensions', async () => {
  const { renderFerryNetwork } = await ferryModule();
  assert.equal(typeof renderFerryNetwork, 'function');
  const { world } = unitDOM();
  const marker = new UnitElement(world.ownerDocument, null, 'div');
  marker.setAttribute('id', 'test-marker');
  world.append(marker);
  const snapshot = syntheticSnapshot(false);
  const before = structuredClone(snapshot);
  const json = JSON.stringify(snapshot);
  deepFreeze(snapshot);
  const layer = renderFerryNetwork(snapshot, world);
  assert.equal(world.querySelectorAll('#ferry-routes').length, 1);
  assert.equal(layer, world.querySelector('#ferry-routes'));
  assert.equal(layer.namespaceURI, SVG_NS);
  assert.equal(layer.localName, 'svg');
  for (const [name, value] of Object.entries({ id: 'ferry-routes', viewBox: '0 0 100 80', width: '100', height: '80',
    'pointer-events': 'none', 'aria-hidden': 'true', focusable: 'false' })) {
    assert.equal(layer.getAttribute(name), value);
  }
  assert.deepEqual({ position: layer.style.position, left: layer.style.left, top: layer.style.top,
    width: layer.style.width, height: layer.style.height, pointerEvents: layer.style.pointerEvents },
  { position: 'absolute', left: '0px', top: '0px', width: '100px', height: '80px', pointerEvents: 'none' });
  assert.equal(layer.children.length, 0);
  assert.equal(marker.parentNode, world);
  assertUnchanged(snapshot, before, json);
  assert.equal(Object.hasOwn(snapshot.meta, 'ferryNetwork'), false);
  assert.equal(typeof globalThis.document, 'undefined');
});

test('R02 DOM fake: two safe unsmoothed polylines preserve literal IDs without HTML, storage or image fetches', async t => {
  const { renderFerryNetwork } = await ferryModule();
  const dom = unitDOM();
  temporaryGlobal(t, 'document', { value: dom.document });
  for (const name of ['fetch', 'Image', 'localStorage', 'sessionStorage']) {
    temporaryGlobal(t, name, { get() { assert.fail(`Renderer must not access ${name}`); } });
  }
  const snapshot = syntheticSnapshot();
  const route = snapshot.meta.ferryNetwork.routes[0];
  route.id = '"/><script>alert(1)</script><polyline onload="x';
  route.points[1] = [40.125, 30.25];
  route.innerHTML = '<script>ignored extension</script>';
  route.style = 'pointer-events:auto;stroke:red';
  route['onload'] = 'ignored';
  snapshot.meta.ferryNetwork.image = snapshot.meta.image = 'literal-image-token-not-loaded.svg';
  const before = structuredClone(snapshot);
  const json = JSON.stringify(snapshot);
  deepFreeze(snapshot);
  const layer = renderFerryNetwork(snapshot);
  assert.equal(layer, dom.world.querySelector('#ferry-routes'));
  assert.equal(layer.children.length, 2);
  assertRoutePair(dom.world, route);
  assert.deepEqual(dom.created.map(node => node.localName), ['svg', 'polyline', 'polyline']);
  assertUnchanged(snapshot, before, json);
});

test('R03 DOM fake: repeated renders replace vectors, repair duplicates and use latest same-revision geometry', async () => {
  const { renderFerryNetwork } = await ferryModule();
  const { world } = unitDOM();
  const first = deepFreeze(syntheticSnapshot());
  const layer = renderFerryNetwork(first, world);
  const previousLines = [...layer.children];
  assert.equal(renderFerryNetwork(first, world), layer);
  assert.equal(world.querySelectorAll('#ferry-routes').length, 1);
  assert.equal(layer.children.length, 2);
  for (const node of previousLines) assert.equal(node.parentNode, null);
  const second = syntheticSnapshot();
  second.meta.ferryNetwork.routes[0].points[1] = [31, 42];
  second.meta.ferryNetwork.routes.push({ id: 'test-route-b', fromLocationId: 'test-dock-a', toLocationId: 'test-dock-c',
    points: [[10, 20], [60, 10]], author: { keep: 0 } });
  const before = structuredClone(second);
  const json = JSON.stringify(second);
  deepFreeze(second);
  const duplicate = world.ownerDocument.createElementNS(SVG_NS, 'svg');
  duplicate.setAttribute('id', 'ferry-routes');
  world.append(duplicate);
  renderFerryNetwork(second, world);
  assert.equal(world.querySelectorAll('#ferry-routes').length, 1);
  assert.equal(duplicate.parentNode, null);
  assert.equal(layer.children.length, 4);
  second.meta.ferryNetwork.routes.forEach(route => assertRoutePair(world, route));
  assertUnchanged(second, before, json);
  const otherWorld = unitDOM().world;
  renderFerryNetwork(first, otherWorld);
  assert.equal(otherWorld.querySelectorAll('#ferry-routes').length, 1);
  assert.notEqual(otherWorld.querySelector('#ferry-routes'), layer);
  assert.equal(layer.children.length, 4);
});

test('R04 DOM fake: map identity mismatches clear stale vectors while keeping the current SVG frame', async () => {
  const { validateFerryNetwork, renderFerryNetwork } = await ferryModule();
  const mismatches = [
    snapshot => { snapshot.meta.image = 'other-test-map.svg'; },
    snapshot => { snapshot.meta.image = './test-only-map.svg'; },
    snapshot => { snapshot.meta.mapRevision = 'test-revision-next'; },
    snapshot => { snapshot.meta.mapRevision = undefined; },
    snapshot => { snapshot.meta.width = 101; },
    snapshot => { snapshot.meta.height = 81; },
    snapshot => { snapshot.meta.ferryNetwork.image = 'author-other-map.svg'; },
    snapshot => { snapshot.meta.ferryNetwork.mapRevision = 'author-other-revision'; },
    snapshot => { snapshot.meta.ferryNetwork.width = 200; },
    snapshot => { snapshot.meta.ferryNetwork.height = 160; },
    snapshot => { snapshot.meta.ferryNetwork.routes = []; },
    snapshot => { delete snapshot.meta.ferryNetwork; },
    snapshot => {
      delete snapshot.meta.ferryNetwork;
      Object.setPrototypeOf(snapshot.meta, { ferryNetwork: syntheticSnapshot().meta.ferryNetwork });
    },
  ];
  for (const change of mismatches) {
    const { world } = unitDOM();
    const valid = deepFreeze(syntheticSnapshot());
    const layer = renderFerryNetwork(valid, world);
    const previous = [...layer.children];
    assert.equal(previous.length, 2);
    const changed = syntheticSnapshot();
    change(changed);
    const json = JSON.stringify(changed);
    deepFreeze(changed);
    assert.equal(validateFerryNetwork(changed), true);
    assert.equal(renderFerryNetwork(changed, world), layer);
    assert.equal(world.querySelectorAll('#ferry-routes').length, 1);
    assert.equal(layer.children.length, 0);
    assert.equal(layer.getAttribute('viewBox'), `0 0 ${changed.meta.width} ${changed.meta.height}`);
    assert.equal(layer.style.width, `${changed.meta.width}px`);
    assert.equal(layer.style.height, `${changed.meta.height}px`);
    previous.forEach(node => assert.equal(node.parentNode, null));
    assert.equal(JSON.stringify(changed), json);
    assert.equal(renderFerryNetwork(valid, world), layer);
    assertRoutePair(world, valid.meta.ferryNetwork.routes[0]);
  }
});

test('R05 DOM fake: only routes with exact current dock endpoints render after pin moves', async () => {
  const { validateFerryNetwork, renderFerryNetwork } = await ferryModule();
  const changes = [
    snapshot => { snapshot.locations[0].x += 0.000001; },
    snapshot => { snapshot.locations[0].y += 0.000001; },
    snapshot => { snapshot.locations[1].x += 0.000001; },
    snapshot => { snapshot.locations[1].y += 0.000001; },
    snapshot => { snapshot.locations[0].x = '10'; },
    snapshot => { snapshot.locations[1].y = '60'; },
    snapshot => { snapshot.meta.ferryNetwork.routes[0].points[0][0] += 1; },
    snapshot => { snapshot.meta.ferryNetwork.routes[0].points.at(-1)[1] += 1; },
    snapshot => { snapshot.meta.ferryNetwork.routes[0].points.reverse(); },
  ];
  const unaffected = { id: 'test-route-unaffected', fromLocationId: 'test-dock-c', toLocationId: 'test-dock-d',
    points: [[60, 10], [80, 10]], author: { unchanged: null } };
  for (const change of changes) {
    const valid = syntheticSnapshot();
    valid.locations.push({ id: 'test-dock-d', type: 'ferry', x: 80, y: 10 });
    valid.meta.ferryNetwork.routes.push(structuredClone(unaffected));
    deepFreeze(valid);
    const { world } = unitDOM();
    const layer = renderFerryNetwork(valid, world);
    assert.equal(layer.children.length, 4);
    const changed = structuredClone(valid);
    change(changed);
    const before = structuredClone(changed);
    const json = JSON.stringify(changed);
    deepFreeze(changed);
    assert.equal(validateFerryNetwork(changed), true);
    renderFerryNetwork(changed, world);
    assert.equal(layer.children.length, 2);
    assertRoutePair(world, unaffected);
    assert.equal(layer.children.some(node => node.getAttribute('data-ferry-route') === 'test-route-a'), false);
    assertUnchanged(changed, before, json);
    renderFerryNetwork(valid, world);
    assert.equal(layer.children.length, 4);
  }
  const moved = syntheticSnapshot();
  moved.locations[0].x = 11;
  moved.locations[1].y = 61;
  moved.meta.ferryNetwork.routes[0].points[0][0] = 11;
  moved.meta.ferryNetwork.routes[0].points.at(-1)[1] = 61;
  const { world } = unitDOM();
  renderFerryNetwork(deepFreeze(moved), world);
  assertRoutePair(world, moved.meta.ferryNetwork.routes[0]);
});

test('R06 DOM fake: malformed metadata clears stale paths before Russian validation errors', async () => {
  const { renderFerryNetwork } = await ferryModule();
  const changes = [
    snapshot => { snapshot.meta.ferryNetwork.routes[0].points[1] = ['40 onload="literal"', 30]; },
    snapshot => { snapshot.meta.ferryNetwork = null; },
    snapshot => { snapshot.meta.ferryNetwork = []; },
    snapshot => { delete snapshot.meta.ferryNetwork.routes; },
    snapshot => { snapshot.meta.ferryNetwork.routes[0].points = [[10, 20]]; },
    snapshot => { snapshot.meta.ferryNetwork.routes[0].points[1] = [Infinity, 30]; },
    snapshot => { snapshot.meta.ferryNetwork.routes[0].points[1] = [101, 30]; },
    snapshot => { snapshot.meta.ferryNetwork.routes[0].toLocationId = 'test-inline-ferry'; },
    snapshot => { snapshot.meta.ferryNetwork.routes[0].toLocationId = 'test-harbor'; },
    snapshot => { snapshot.meta.ferryNetwork.routes.push(syntheticRoute()); },
  ];
  for (const change of changes) {
    const { world, created } = unitDOM();
    const valid = deepFreeze(syntheticSnapshot());
    const layer = renderFerryNetwork(valid, world);
    const createdBefore = created.length;
    const invalid = syntheticSnapshot();
    change(invalid);
    const before = structuredClone(invalid);
    const json = JSON.stringify(invalid);
    deepFreeze(invalid);
    assertRussianError(() => renderFerryNetwork(invalid, world), 'meta.ferryNetwork');
    assert.equal(layer.children.length, 0);
    assert.equal(world.querySelectorAll('#ferry-routes').length, 1);
    assert.equal(created.length, createdBefore);
    assertUnchanged(invalid, before, json);
    renderFerryNetwork(valid, world);
    assertRoutePair(world, valid.meta.ferryNetwork.routes[0]);
  }
});

test('R07 DOM fake: deliberate empty network needs no locations lookup or reseeding', async () => {
  const { validateFerryNetwork, renderFerryNetwork } = await ferryModule();
  const { world } = unitDOM();
  const layer = renderFerryNetwork(deepFreeze(syntheticSnapshot()), world);
  assert.equal(layer.children.length, 2);
  const snapshot = { meta: { image: 'test-only-map.svg', mapRevision: 'test-revision', width: 100, height: 80,
    ferryNetwork: { image: 'test-only-map.svg', mapRevision: 'test-revision', width: 100, height: 80, routes: [],
      author: { deliberateClear: true } } } };
  const before = structuredClone(snapshot);
  const json = JSON.stringify(snapshot);
  deepFreeze(snapshot);
  assert.equal(validateFerryNetwork(snapshot), true);
  assert.doesNotThrow(() => renderFerryNetwork(snapshot, world));
  assert.equal(world.querySelector('#ferry-routes'), layer);
  assert.equal(layer.children.length, 0);
  assertUnchanged(snapshot, before, json);
  assert.equal(Object.hasOwn(snapshot, 'locations'), false);
});

test('R08 DOM fake: invalid current map dimensions reject before attribute coercion and clear stale vectors', async () => {
  const { renderFerryNetwork } = await ferryModule();
  for (const field of ['width', 'height']) {
    for (const value of [undefined, null, false, '100', '100;position:fixed', 0, -1, NaN, Infinity, {}]) {
      const { world } = unitDOM();
      const valid = deepFreeze(syntheticSnapshot());
      const layer = renderFerryNetwork(valid, world);
      const invalid = syntheticSnapshot();
      invalid.meta[field] = value;
      const before = structuredClone(invalid);
      const json = JSON.stringify(invalid);
      deepFreeze(invalid);
      assertRussianError(() => renderFerryNetwork(invalid, world), 'meta', /размер/i, /конечн/i);
      assert.equal(layer.children.length, 0);
      assert.equal(layer.getAttribute('viewBox'), '0 0 100 80');
      assertUnchanged(invalid, before, json);
    }
  }
  for (const snapshot of [undefined, null, {}, { meta: null }, { meta: [] }]) {
    assertRussianError(() => renderFerryNetwork(snapshot, unitDOM().world), /снимок|meta/i);
  }
});

// Static CSS contract only: no computed styles, visual acceptance or native hit testing.
const cssRules = async () => {
  assert.ok(existsSync(CSS), 'Ожидается отдельный CSS слой паромных маршрутов');
  const source = await readFile(CSS, 'utf8');
  const stripped = source.replace(/\/\*[\s\S]*?\*\//g, '');
  const rules = [];
  for (const [, selectors, body] of stripped.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const declarations = Object.fromEntries(body.split(';').map(item => item.trim()).filter(Boolean).map(item => {
      const colon = item.indexOf(':');
      assert.ok(colon > 0, `Malformed declaration: ${item}`);
      return [item.slice(0, colon).trim(), item.slice(colon + 1).trim()];
    }));
    rules.push({ selectors: selectors.split(',').map(item => item.trim()), declarations });
  }
  return { source: stripped, rules };
};
const declarationsFor = (rules, selector) => Object.assign({}, ...rules.filter(rule => rule.selectors.includes(selector)).map(rule => rule.declarations));

test('C01 static CSS contract: inert routes occupy only layer 4 with modest opacity and no animation', async () => {
  const { source, rules } = await cssRules();
  const layer = declarationsFor(rules, '#ferry-routes');
  assert.deepEqual({ position: layer.position, left: layer.left, top: layer.top, zIndex: layer['z-index'],
    pointerEvents: layer['pointer-events'], overflow: layer.overflow },
  { position: 'absolute', left: '0', top: '0', zIndex: '4', pointerEvents: 'none', overflow: 'hidden' });
  const opacity = Number(layer.opacity);
  assert.ok(opacity > 0 && opacity <= 0.75, 'Route layer needs modest opacity');
  assert.equal(declarationsFor(rules, '#ferry-routes *')['pointer-events'], 'none');
  // Parent may append unrelated ferry-marker ornament after this bounded handoff.
  const routeRules = rules.filter(rule => rule.selectors.some(selector => /ferry-routes|ferry-route-/.test(selector)));
  for (const rule of routeRules) for (const selector of rule.selectors) {
    assert.match(selector, /^#ferry-routes(?:\s|$)/, `Unscoped route selector: ${selector}`);
  }
  const routeStyles = routeRules.map(rule => JSON.stringify(rule.declarations)).join(' ');
  assert.doesNotMatch(routeStyles, /animation|transition|url\s*\(/i);
  assert.doesNotMatch(source, /@keyframes\s+ferry-route/i);
});

test('C02 static CSS contract: dark halo and light cyan main share fixed rounded dash geometry', async () => {
  const { rules } = await cssRules();
  const common = declarationsFor(rules, '#ferry-routes *');
  const halo = { ...common, ...declarationsFor(rules, '#ferry-routes .ferry-route-halo') };
  const main = { ...common, ...declarationsFor(rules, '#ferry-routes .ferry-route-line') };
  for (const line of [halo, main]) {
    assert.equal(line.fill, 'none');
    assert.equal(line['stroke-linecap'], 'round');
    assert.equal(line['stroke-linejoin'], 'round');
    assert.equal(line['vector-effect'], 'non-scaling-stroke');
    assert.equal(line['stroke-dasharray'], '5 7');
    assert.equal(line['pointer-events'], 'none');
  }
  assert.equal(halo['stroke-width'], '3.5');
  assert.equal(main['stroke-width'], '1.8');
  assert.match(halo.stroke, /^#[0-9a-f]{6}$/i);
  assert.match(main.stroke, /^#[0-9a-f]{6}$/i);
  const channels = color => [1, 3, 5].map(index => parseInt(color.slice(index, index + 2), 16));
  assert.ok(channels(halo.stroke).every(value => value < 64), 'Halo must be dark');
  const [red, green, blue] = channels(main.stroke);
  assert.ok(red >= 120 && green > red && blue > red && green >= 150 && blue >= 150, 'Main must be muted light cyan');
});
