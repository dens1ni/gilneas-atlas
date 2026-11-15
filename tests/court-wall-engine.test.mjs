import test from 'node:test';
import assert from 'node:assert/strict';

const engineUrl = new URL('../assets/js/wall-progress.mjs', import.meta.url);
const engine = await import(engineUrl).catch(error => {
  if (error.code === 'ERR_MODULE_NOT_FOUND' && error.url === engineUrl.href) return {};
  throw error;
});
const freeze = value => {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
};

test('legacy wall progress preserves the exact author value without inventing history', () => {
  assert.equal(typeof engine.validateWallConstruction, 'function', 'wall validator is required');
  assert.equal(typeof engine.deriveWallProgress, 'function', 'wall derivation is required');
  const track = freeze({ value: 43, max: 91, note: '  Авторская стадия  ' });
  const original = structuredClone(track);
  assert.deepEqual(engine.validateWallConstruction(track), original);
  assert.deepEqual(engine.deriveWallProgress(track), {
    baseValue: 43, value: 43, max: 91, events: [],
  });
  assert.deepEqual(track, original);
  assert.equal(Object.hasOwn(track, 'events'), false);
  assert.equal(Object.hasOwn(track, 'baseValue'), false);
});

test('the first event starts from the exact current author value in an immutable full snapshot', () => {
  assert.equal(typeof engine.updateWallEvent, 'function', 'wall event updates are required');
  const snapshot = freeze({
    version: 1,
    meta: { wallConstruction: { value: 43, max: 100, note: '  Не менять  ' }, width: 3526, height: 4548 },
    locations: [{ id: 'keep', x: 1200, y: 2200, description: '  Личная запись  ' }],
    territoryGrid: { keys: ['crown'], cells: [1, 0, 1], author: 'manual' },
    authorRegistry: [{ nested: '<script>literal</script>' }],
  });
  const event = freeze({ id: 'wall-a', name: '  Поставка камня  ', description: '  Запись автора  ', delta: 15 });
  const original = structuredClone(snapshot);
  const next = engine.updateWallEvent(snapshot, event);
  assert.notEqual(next, snapshot);
  assert.notEqual(next.meta, snapshot.meta);
  assert.notEqual(next.meta.wallConstruction, snapshot.meta.wallConstruction);
  assert.deepEqual(next.meta.wallConstruction, {
    value: 58, max: 100, note: '  Не менять  ', baseValue: 43, events: [event],
  });
  assert.notEqual(next.meta.wallConstruction.events[0], event);
  assert.deepEqual({ ...next, meta: { ...next.meta, wallConstruction: original.meta.wallConstruction } }, original);
  assert.deepEqual(snapshot, original);
});

test('editing a stored event recalculates all following events in their original order', () => {
  const initial = { meta: { wallConstruction: { value: 10, max: 100 } }, extra: { manual: true } };
  const added = engine.updateWallEvent(initial, {
    id: 'wall-first', name: 'Камень', description: '  Сохранить  ', delta: 15,
    sources: ['source-1'], authorExtra: { literal: '  Запись  ' },
    effects: [{ id: 'wall-bonus', kind: 'bonus', text: '  Дополнительные рабочие  ' }],
  });
  const second = engine.updateWallEvent(added, { id: 'wall-second', name: 'Шторм', delta: -20 });
  assert.equal(second.meta.wallConstruction.value, 5);
  const original = structuredClone(second);
  freeze(second);
  const edited = engine.updateWallEvent(second, { id: 'wall-first', name: 'Новая поставка', delta: 30 });
  assert.deepEqual(edited.meta.wallConstruction.events.map(record => record.id), ['wall-first', 'wall-second']);
  assert.equal(edited.meta.wallConstruction.baseValue, 10);
  assert.equal(edited.meta.wallConstruction.value, 20);
  assert.deepEqual(edited.meta.wallConstruction.events[0], {
    ...original.meta.wallConstruction.events[0], name: 'Новая поставка', delta: 30,
  });
  assert.deepEqual(engine.deriveWallProgress(edited.meta.wallConstruction).events.map(record => [record.before, record.after, record.appliedDelta]), [
    [10, 40, 30], [40, 20, -20],
  ]);
  assert.deepEqual(second, original);
});

test('removing events recalculates history from the preserved base without touching unrelated data', () => {
  assert.equal(typeof engine.removeWallEvent, 'function', 'wall event removal is required');
  let snapshot = { meta: { wallConstruction: { value: 43, max: 100, note: '  Стадия  ' } }, manualGrid: [1, 0, 1] };
  snapshot = engine.updateWallEvent(snapshot, { id: 'wall-a', name: 'Поставка', delta: 15 });
  snapshot = engine.updateWallEvent(snapshot, { id: 'wall-b', name: 'Потери', delta: -20 });
  const original = structuredClone(snapshot);
  freeze(snapshot);
  const removed = engine.removeWallEvent(snapshot, 'wall-a');
  assert.deepEqual(removed.meta.wallConstruction, {
    value: 23, max: 100, note: '  Стадия  ', baseValue: 43,
    events: [{ id: 'wall-b', name: 'Потери', delta: -20 }],
  });
  assert.deepEqual(removed.manualGrid, original.manualGrid);
  const empty = engine.removeWallEvent(removed, 'wall-b');
  assert.deepEqual(empty.meta.wallConstruction, { value: 43, max: 100, note: '  Стадия  ', baseValue: 43, events: [] });
  assert.deepEqual(snapshot, original);
  assert.throws(() => engine.removeWallEvent(snapshot, 'missing'), /не найдено|не найден/i);
});

test('validation rejects malformed track bounds instead of coercing or repairing author values', () => {
  const invalid = [
    null, [], '10/100', {}, { value: 10, max: 0 }, { value: 10, max: -100 },
    { value: 10, max: 100.5 }, { value: 10, max: Infinity }, { value: 10, max: NaN },
    { value: 10, max: 1000001 }, { value: -1, max: 100 }, { value: 101, max: 100 },
    { value: 10.5, max: 100 }, { value: '10', max: 100 }, { value: Infinity, max: 100 },
    { value: 10, max: 100, baseValue: null }, { value: 10, max: 100, baseValue: -1 },
    { value: 10, max: 100, baseValue: 101 }, { value: 10, max: 100, baseValue: 10.5 },
    { value: 10, max: 100, baseValue: NaN }, { value: 10, max: 100, events: null },
    { value: 10, max: 100, events: {} },
  ];
  for (const track of invalid) {
    assert.throws(() => engine.validateWallConstruction(track), Error, JSON.stringify(track));
    assert.throws(() => engine.deriveWallProgress(track), Error, JSON.stringify(track));
  }
  for (const track of [{ value: 0, max: 1 }, { value: 1000000, max: 1000000 }]) {
    assert.deepEqual(engine.validateWallConstruction(freeze(track)), track);
  }
});

test('event validation rejects malformed records while preserving literal names, descriptions and zero delta', () => {
  const valid = { id: 'wall-literal', name: '  <img onerror="literal">  ', description: '  <script>literal</script>  ', delta: 0 };
  const invalid = [
    null, [], 'event', {}, { ...valid, id: '' }, { ...valid, id: 12 }, { ...valid, id: 'a'.repeat(101) },
    { ...valid, name: '' }, { ...valid, name: '  ' }, { ...valid, name: 12 },
    { ...valid, description: null }, { ...valid, description: {} }, { ...valid, description: 12 },
    { ...valid, delta: undefined }, { ...valid, delta: null }, { ...valid, delta: '15' },
    { ...valid, delta: 0.5 }, { ...valid, delta: Infinity }, { ...valid, delta: NaN },
    { ...valid, delta: 1000001 }, { ...valid, delta: -1000001 },
  ];
  for (const event of invalid) {
    assert.throws(() => engine.validateWallConstruction({ value: 10, max: 100, baseValue: 10, events: [event] }), Error);
  }
  const track = freeze({ value: 10, max: 100, baseValue: 10, events: [valid] });
  assert.deepEqual(engine.validateWallConstruction(track), track);
  assert.deepEqual(engine.deriveWallProgress(track).events[0], { ...valid, before: 10, after: 10, appliedDelta: 0 });
  assert.deepEqual(engine.validateWallConstruction({ value: 10, max: 100, events: [{ id: 'wall-optional', name: 'Справка', delta: 0 }] }).events[0], {
    id: 'wall-optional', name: 'Справка', delta: 0,
  });
  const tooMany = Array.from({ length: 1001 }, (_, index) => ({ id: `wall-${index}`, name: 'Справка', delta: 0 }));
  assert.throws(() => engine.validateWallConstruction({ value: 10, max: 100, events: tooMany }), /1000/);
  assert.throws(() => engine.validateWallConstruction({ value: 10, max: 100, events: Array(1) }), Error);
});

test('validation claims exact event and effect IDs and validates source references through parent callbacks', () => {
  const event = {
    id: 'wall-event', name: '  Справка  ', delta: 0, sources: ['archive', 7],
    effects: [
      { id: 'wall-bonus', kind: 'bonus', text: '  <b>Камень</b>  ', sources: ['archive'] },
      { id: 'wall-penalty', kind: 'penalty', text: '' },
    ],
  };
  const track = freeze({ value: 10, max: 100, baseValue: 10, events: [event] });
  const claimed = [], sourced = [];
  engine.validateWallConstruction(track, {
    claim: (record, label) => claimed.push([record.id, label]),
    validateSources: record => sourced.push(record),
  });
  assert.deepEqual(claimed.map(([id]) => id), ['wall-event', 'wall-bonus', 'wall-penalty']);
  assert.ok(claimed.every(([, label]) => typeof label === 'string' && label.length));
  assert.deepEqual(sourced, [event, ...event.effects]);
  assert.throws(() => engine.validateWallConstruction(track, { claim: () => { throw new Error('Global ID collision'); } }), /Global ID collision/);
  assert.throws(() => engine.validateWallConstruction(track, { validateSources: () => { throw new Error('Unknown source'); } }), /Unknown source/);
  const invalidEffects = [null, {}, [null], [[]], [{ id: '', kind: 'bonus', text: '' }], [{ id: 'effect', kind: 'boost', text: '' }],
    [{ id: 'effect', kind: 'penalty', text: 3 }], [{ id: 'effect', kind: 'bonus' }],
  ];
  for (const effects of invalidEffects) {
    assert.throws(() => engine.validateWallConstruction({ value: 10, max: 100, baseValue: 10, events: [{ ...event, effects }] }), Error);
  }
  for (const events of [
    [event, event],
    [{ ...event, effects: [{ id: 'wall-event', kind: 'bonus', text: '' }] }],
    [{ ...event, effects: [event.effects[0], event.effects[0]] }],
    [event, { id: 'other', name: 'Справка', delta: 0, effects: [event.effects[0]] }],
  ]) assert.throws(() => engine.validateWallConstruction({ value: 10, max: 100, baseValue: 10, events }), /ID/);
  for (const sources of [null, {}, [false], [''], [null], [Infinity], [NaN]]) {
    assert.throws(() => engine.validateWallConstruction({ value: 10, max: 100, events: [{ id: 'event', name: 'Справка', delta: 0, sources }] }), /источник/);
  }
});

test('validation rejects cached progress contradictions instead of silently rewriting history or author values', () => {
  for (const track of [
    { value: 58, max: 100, baseValue: 43, events: [{ id: 'event', name: 'Справка', delta: -20 }] },
    { value: 58, max: 100, baseValue: 43, events: [] },
    { value: 58, max: 100, baseValue: 43 },
    { value: 43, max: 100, events: [{ id: 'event', name: 'Справка', delta: 15 }] },
  ]) {
    const original = structuredClone(track);
    freeze(track);
    assert.throws(() => engine.validateWallConstruction(track), /value|прогресс/i);
    assert.throws(() => engine.deriveWallProgress(track), /value|прогресс/i);
    assert.deepEqual(track, original);
  }
  const track = freeze({ value: 0, max: 100, baseValue: 90, events: [
    { id: 'over', name: 'Большая поставка', delta: 500 },
    { id: 'under', name: 'Утрата', delta: -200 },
    { id: 'plus', name: 'Поставка', delta: 15 },
    { id: 'minus', name: 'Потеря', delta: -20 },
  ] });
  assert.deepEqual(engine.deriveWallProgress(track).events.map(record => [record.delta, record.before, record.after, record.appliedDelta]), [
    [500, 90, 100, 10], [-200, 100, 0, -100], [15, 0, 15, 15], [-20, 15, 0, -15],
  ]);
  assert.deepEqual(engine.validateWallConstruction(track), track);
});

test('immutable mutation boundaries reject invalid inputs before returning a changed snapshot', () => {
  const snapshot = freeze({ meta: { wallConstruction: { value: 43, max: 100 } }, manualGrid: [1, 0, 1] });
  const original = structuredClone(snapshot);
  for (const event of [null, [], { id: 'bad', name: '', delta: 15 }, { id: 'bad', name: 'Справка', delta: 1.5 },
    { id: 'bad', name: 'Справка', delta: 0, effects: [{ id: 'bad', kind: 'bonus', text: 'ID collision' }] },
  ]) assert.throws(() => engine.updateWallEvent(snapshot, event), Error);
  const invalid = freeze({ meta: { wallConstruction: { value: 43, max: 100, baseValue: 10, events: [{ id: 'wall', name: 'Справка', delta: 15 }] } } });
  assert.throws(() => engine.updateWallEvent(invalid, { id: 'wall', name: 'Новая', delta: 33 }), /value|прогресс/);
  assert.throws(() => engine.removeWallEvent(invalid, 'wall'), /value|прогресс/);
  assert.throws(() => engine.updateWallEvent({}, { id: 'wall', name: 'Справка', delta: 0 }), /сним|wallConstruction/);
  assert.throws(() => engine.removeWallEvent({}, 'wall'), /сним|wallConstruction/);
  assert.deepEqual(snapshot, original);
});

test('source callbacks receive exact legacy finite numeric reference IDs without integer coercion', () => {
  const seen = [];
  const track = freeze({ value: 10, max: 100, events: [{ id: 'event', name: 'Справка', delta: 0, sources: [1.5, '  archive  '] }] });
  assert.deepEqual(engine.validateWallConstruction(track, { validateSources: record => seen.push(...(record.sources ?? [])) }), track);
  assert.deepEqual(seen, [1.5, '  archive  ']);
});
