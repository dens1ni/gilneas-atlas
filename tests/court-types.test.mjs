import test from 'node:test';
import assert from 'node:assert/strict';

const requiredTypes = [
  'city', 'settlement', 'estate', 'fortress', 'district', 'harbor', 'forest', 'mine', 'landmark', 'building', 'resource',
  'farm', 'workshop', 'barracks', 'church', 'cemetery', 'quarry', 'lumbermill', 'mill', 'warehouse', 'market', 'inn',
  'stable', 'watchtower', 'military-camp', 'gate', 'bridge', 'school', 'library', 'hospital', 'garden', 'orchard',
  'fishery', 'granary', 'shipyard', 'forge', 'ruins', 'monument', 'well',
];

test('shared catalog exposes immutable Russian definitions for all useful object and location kinds without a DOM', async () => {
  assert.equal(typeof globalThis.document, 'undefined');
  const { TYPE_DEFINITIONS, OBJECT_TYPE_IDS } = await import('../assets/js/object-types.mjs');
  assert.ok(Array.isArray(TYPE_DEFINITIONS));
  assert.ok(Object.isFrozen(TYPE_DEFINITIONS));
  assert.ok(TYPE_DEFINITIONS.length >= 30);
  assert.ok(Array.isArray(OBJECT_TYPE_IDS));
  assert.ok(Object.isFrozen(OBJECT_TYPE_IDS));
  assert.deepEqual(OBJECT_TYPE_IDS, TYPE_DEFINITIONS.map(definition => definition.id));
  assert.equal(new Set(OBJECT_TYPE_IDS).size, TYPE_DEFINITIONS.length);
  for (const id of requiredTypes) assert.ok(OBJECT_TYPE_IDS.includes(id), `missing literal type ID: ${id}`);
  for (const definition of TYPE_DEFINITIONS) {
    assert.ok(Object.isFrozen(definition), definition.id);
    assert.deepEqual(Object.keys(definition).sort(), ['id', 'label', 'path']);
    assert.match(definition.id, /^[a-z]+(?:-[a-z]+)*$/);
    assert.match(definition.label, /[А-Яа-яЁё]/);
    assert.match(definition.path, /^M/);
    assert.ok(!/[<>]/.test(definition.path));
  }
  assert.throws(() => TYPE_DEFINITIONS.push({ id: 'rogue' }), TypeError);
  assert.throws(() => { TYPE_DEFINITIONS[0].label = 'Changed'; }, TypeError);
  assert.throws(() => OBJECT_TYPE_IDS.push('rogue'), TypeError);
});

test('type names use Russian catalog labels while keeping unknown IDs literal', async () => {
  const { TYPE_DEFINITIONS, typeName } = await import('../assets/js/object-types.mjs');
  assert.equal(typeof typeName, 'function');
  for (const definition of TYPE_DEFINITIONS) assert.equal(typeName(definition.id), definition.label);
  for (const legacy of ['author-type', ' farm ', '<script>globalThis.bad=1</script>', '__proto__', 'constructor']) {
    assert.equal(typeName(legacy), legacy);
  }
  assert.equal(typeName(''), 'Не указан');
  assert.equal(typeName(null), 'Не указан');
  assert.equal(typeName(undefined), 'Не указан');
});

function deepFreeze(value) {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(deepFreeze);
    Object.freeze(value);
  }
  return value;
}

function snapshot() {
  return {
    version: 1, meta: { width: 3526, height: 4548, custom: { literal: '  <script>literal</script>  ' } },
    factions: [{ id: 'house', name: 'Тестовый дом', color: '#005577', parent: null }],
    locations: [
      { id: 'keep', name: '  Тестовый замок  ', x: 1200, y: 2200, type: 'fortress', faction: 'house', owner: '', description: '', objects: [] },
      { id: 'port', name: 'Тестовый порт', x: 1800, y: 2800, type: 'harbor', faction: null, owner: '', description: '  Не менять  ', objects: [] },
    ],
    territories: [], nobles: [], sources: [],
    authorRegistry: [{ literal: '  <script>literal</script>  ' }],
  };
}

test('every catalog kind survives an immutable nested-object upsert and exact full JSON reload with its effects', async () => {
  const { OBJECT_TYPE_IDS } = await import('../assets/js/object-types.mjs');
  const { normalizeData, upsertObject, serializeSnapshot, deserializeSnapshot } = await import('../assets/js/model.mjs');
  const original = deepFreeze(normalizeData(snapshot()));
  const originalJSON = JSON.stringify(original);
  for (const type of OBJECT_TYPE_IDS) {
    const object = {
      id: 'typed-object', type, name: '  <script>literal</script>  ', owner: '', description: '  Exact text  ',
      amount: '  30 tonnes  ',
      modifiers: [{ id: 'bonus', kind: 'bonus', text: '  Supply  ', extra: { literal: '<img onerror="bad=1">' } },
                  { id: 'penalty', kind: 'penalty', text: '  +2 costs — penalty  ' }],
      custom: { nested: ['  Preserve  ', { type: 'author-extension' }] },
    };
    const next = upsertObject(original, 'keep', object);
    const expected = structuredClone(original);
    expected.locations[0].objects.push(object);
    assert.deepEqual(next, expected, type);
    assert.deepEqual(deserializeSnapshot(serializeSnapshot(next)), expected, type);
    assert.equal(JSON.stringify(original), originalJSON, type);
    assert.equal(Object.hasOwn(next.locations[0].objects[0], 'faction'), false, type);
  }
});
