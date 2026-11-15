import test from 'node:test';
import assert from 'node:assert/strict';

const engine = () => import('../assets/js/council-influence.mjs');

function freeze(value) {
  if (value !== null && typeof value === 'object') {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}

const person = (patch = {}) => ({
  id: '  council-person  ', kind: 'person', name: '  Авторский персонаж  ',
  party: 'royalists', stance: 'unknown', advisor: false, active: true,
  note: '  Авторский текст  ', sources: [45, ' archive-46 '], ...patch,
});

const council = (patch = {}) => ({ version: 1, members: [], ...patch });

const snapshot = (patch = {}) => ({
  version: 1, meta: { width: 100, height: 100, author: { note: '  Не менять  ' } },
  factions: [{ id: '  house  ', name: '  Авторский дом  ', color: '#112233', parent: null }],
  locations: [{ id: '  town  ', name: '  Владение  ', type: 'settlement', x: 10, y: 20,
    faction: '  house  ', owner: '', description: '  Описание  ', objects: [], sources: [45] }],
  territories: [], nobles: [],
  sources: [{ id: 45, title: '  Числовой источник  ', url: 'https://example.com/45' },
    { id: ' archive-46 ', title: '  Строковый источник  ', url: 'https://example.com/46' }],
  authorMetadata: { blank: '', flag: false, zero: 0, nil: null, payload: '<script>literal</script>' },
  ...patch,
});

test('influence colors are immutable exact silver and muted Crowley identities', async () => {
  const { COUNCIL_INFLUENCE_COLORS } = await engine();
  assert.deepEqual(COUNCIL_INFLUENCE_COLORS, {
    royalists: '#9aa8b6', internationalists: '#639096',
  });
  assert.ok(Object.isFrozen(COUNCIL_INFLUENCE_COLORS));
  assert.throws(() => { COUNCIL_INFLUENCE_COLORS.royalists = '#ffffff'; }, TypeError);
  assert.equal(typeof globalThis.document, 'undefined');
});

test('stored pools require both exact nonnegative safe integers without a game maximum', async () => {
  const { validateCouncilInfluence } = await engine();
  assert.equal(typeof validateCouncilInfluence, 'function');
  assert.equal(validateCouncilInfluence(undefined), true);
  assert.equal(validateCouncilInfluence(council()), true);
  for (const influence of [
    { royalists: 0, internationalists: 0 },
    { royalists: 1000001, internationalists: 3 },
    { royalists: Number.MAX_SAFE_INTEGER, internationalists: Number.MAX_SAFE_INTEGER },
  ]) {
    const value = freeze(council({ influence, author: { blank: '', nil: null } }));
    const before = structuredClone(value);
    assert.equal(validateCouncilInfluence(value), true);
    assert.deepEqual(value, before);
  }
  for (const influence of [null, undefined, false, '', [], {}, { royalists: 0 }, { internationalists: 0 }]) {
    assert.throws(() => validateCouncilInfluence(council({ influence })), /[Вв]лияни|influence/);
  }
  for (const field of ['royalists', 'internationalists']) {
    for (const invalid of [-1, 0.5, NaN, Infinity, -Infinity, Number.MAX_SAFE_INTEGER + 1,
      Number.MAX_VALUE, '0', '', null, undefined, false, {}, [], 1n]) {
      const influence = { royalists: 0, internationalists: 0, [field]: invalid };
      const value = council({ influence });
      assert.throws(() => validateCouncilInfluence(value), error => {
        assert.match(error.message, /[Вв]лияни|influence/);
        assert.ok(error.message.includes(field), error.message);
        assert.match(error.message, /целое|целых/);
        assert.match(error.message, /9007199254740991|MAX_SAFE_INTEGER/);
        assert.match(error.message, /техническ/i);
        assert.match(error.message, /укажите|введите|уменьшите/i);
        return true;
      });
      assert.ok(Object.is(value.influence[field], invalid));
    }
  }
  for (const invalid of [null, false, 'council', []]) {
    assert.throws(() => validateCouncilInfluence(invalid), /[Сс]овет|[Вв]лияни/);
  }
});

test('personal ratings are optional complete integer pairs 0..100 only for people', async () => {
  const { validateCouncilInfluence } = await engine();
  for (const influence of [{ party: 0, kingdom: 0 }, { party: 75, kingdom: 25 },
    { party: 100, kingdom: 100 }, { party: 0, kingdom: 100, lore: { note: '  Автор  ', sources: [45] } }]) {
    const value = freeze(council({ members: [person({ influence, party: 'neutral', active: false })] }));
    const before = structuredClone(value);
    assert.equal(validateCouncilInfluence(value), true);
    assert.deepEqual(value, before);
  }
  const legacy = council({ members: [person(), person({ id: 'house-seat', kind: 'faction', refId: '  house  ' })] });
  assert.equal(validateCouncilInfluence(freeze(legacy)), true);
  assert.ok(legacy.members.every(member => !Object.hasOwn(member, 'influence')));
  for (const influence of [null, undefined, false, 'ratings', [], {}, { party: 0 }, { kingdom: 0 }]) {
    assert.throws(() => validateCouncilInfluence(council({ members: [person({ influence })] })), /[Вв]лияни|influence/);
  }
  for (const field of ['party', 'kingdom']) {
    for (const invalid of [-1, 101, 0.5, NaN, Infinity, Number.MAX_SAFE_INTEGER,
      Number.MAX_SAFE_INTEGER + 1, '0', '', false, null, undefined, {}, [], 1n]) {
      const value = council({ members: [person({ influence: { party: 0, kingdom: 0, [field]: invalid } })] });
      assert.throws(() => validateCouncilInfluence(value), error => {
        assert.match(error.message, /[Вв]лияни|influence/);
        assert.ok(error.message.includes(field), error.message);
        assert.ok(error.message.includes(value.members[0].id), error.message);
        assert.match(error.message, /целое|целых/);
        assert.match(error.message, /0.*100/);
        return true;
      });
      assert.ok(Object.is(value.members[0].influence[field], invalid));
    }
  }
  for (const kind of ['faction', 'house', undefined]) {
    for (const influence of [{ party: 0, kingdom: 0 }, null, undefined]) {
      assert.throws(() => validateCouncilInfluence(council({ members: [person({ kind, influence })] })),
        /персон|человек|kind.*person/);
    }
  }
});

test('party view uses only stored balances and returns overflow-safe fractional shares', async () => {
  const { derivePartyInfluence } = await engine();
  assert.equal(typeof derivePartyInfluence, 'function');
  const empty = { royalists: 0, internationalists: 0, royalistShare: 0,
    internationalistShare: 0, empty: true, initialized: false };
  assert.deepEqual(derivePartyInfluence(undefined), empty);
  for (const value of [council(), council({ members: [person({ influence: { party: 100, kingdom: 100 } })] })]) {
    const before = structuredClone(value);
    assert.deepEqual(derivePartyInfluence(freeze(value)), empty);
    assert.deepEqual(value, before);
    assert.equal(Object.hasOwn(value, 'influence'), false);
  }
  for (const [royalists, internationalists, royalistShare, internationalistShare] of [
    [75, 25, 0.75, 0.25], [25, 75, 0.25, 0.75],
    [0, 0, 0, 0], [0, 25, 0, 1], [75, 0, 1, 0],
    [6000000000000000, 2000000000000000, 0.75, 0.25],
    [Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER, 0.5, 0.5],
  ]) {
    const value = freeze(council({ influence: { royalists, internationalists }, members: [
      person({ influence: { party: 100, kingdom: 1 } }),
      person({ id: 'house-seat', kind: 'faction', refId: '  house  ' }),
    ] }));
    const before = structuredClone(value);
    const result = derivePartyInfluence(value);
    assert.deepEqual(result, { royalists, internationalists, royalistShare,
      internationalistShare, empty: royalists === 0 && internationalists === 0, initialized: true });
    assert.deepEqual(value, before);
  }
  for (const [royalists, internationalists] of [[Number.MAX_SAFE_INTEGER, 1], [1, Number.MAX_SAFE_INTEGER],
    [Number.MAX_SAFE_INTEGER, Number.MAX_SAFE_INTEGER - 1]]) {
    const result = derivePartyInfluence(council({ influence: { royalists, internationalists } }));
    const maximum = Math.max(royalists, internationalists);
    const denominator = royalists / maximum + internationalists / maximum;
    assert.equal(result.royalistShare, (royalists / maximum) / denominator);
    assert.equal(result.internationalistShare, (internationalists / maximum) / denominator);
    for (const share of [result.royalistShare, result.internationalistShare]) {
      assert.ok(Number.isFinite(share) && share >= 0 && share <= 1);
    }
    assert.ok(Math.abs(result.royalistShare + result.internationalistShare - 1) <= Number.EPSILON);
  }
  for (const value of [council({ influence: null }), council({ influence: { royalists: 5 } }),
    council({ influence: { royalists: Number.MAX_SAFE_INTEGER + 1, internationalists: 1 } }),
    council({ members: [person({ influence: { party: 101, kingdom: 0 } })] })]) {
    assert.throws(() => derivePartyInfluence(value), /[Вв]лияни|influence/);
  }
});

test('direct validation rejects non-JSON payloads and malformed member collections without running getters', async () => {
  const { validateCouncilInfluence, derivePartyInfluence } = await engine();
  const cycle = {}; cycle.self = cycle;
  const sparse = Array(1);
  const withSymbol = { valid: 0, [Symbol('hidden')]: 1 };
  let getterCalls = 0;
  const accessor = { royalists: 0 };
  Object.defineProperty(accessor, 'internationalists', { enumerable: true, get() { getterCalls++; return 0; } });
  const getterCouncil = council();
  Object.defineProperty(getterCouncil, 'influence', { enumerable: true, get() { getterCalls++; return { royalists: 0, internationalists: 0 }; } });
  const metadataGetter = {};
  Object.defineProperty(metadataGetter, 'value', { enumerable: true, get() { getterCalls++; return 'not JSON'; } });
  const invalidValues = [undefined, NaN, Infinity, -Infinity, () => {}, Symbol('value'), 1n,
    new Date(), new Map(), new Set(), /not-json/, cycle, sparse, withSymbol, metadataGetter];
  for (const value of invalidValues) {
    for (const bad of [council({ author: value }),
      council({ influence: { royalists: 0, internationalists: 0, metadata: value } }),
      council({ members: [person({ influence: { party: 0, kingdom: 0, metadata: value } })] })]) {
      const keys = Reflect.ownKeys(bad);
      for (const read of [validateCouncilInfluence, derivePartyInfluence]) {
        assert.throws(() => read(bad), /JSON/);
      }
      assert.deepEqual(Reflect.ownKeys(bad), keys);
    }
  }
  for (const bad of [council({ influence: accessor }), getterCouncil]) {
    assert.throws(() => validateCouncilInfluence(bad), /JSON/);
    assert.throws(() => derivePartyInfluence(bad), /JSON/);
  }
  assert.equal(getterCalls, 0);
  for (const members of [null, undefined, 'members', false, {}, [null], [[]], [false], [1], ['person'], Array(1)]) {
    const value = council({ members });
    assert.throws(() => validateCouncilInfluence(value), /[Сс]овет|участник|members|JSON/);
    assert.throws(() => derivePartyInfluence(value), /[Сс]овет|участник|members|JSON/);
  }
  const shared = { note: '  shared JSON is not a cycle  ', zero: 0, flag: false, nil: null, decimalMetadata: 0.5 };
  const value = council({ influence: { royalists: 0, internationalists: 0, author: shared }, author: shared });
  assert.equal(validateCouncilInfluence(freeze(value)), true);
  assert.deepEqual(derivePartyInfluence(value), { royalists: 0, internationalists: 0, royalistShare: 0,
    internationalistShare: 0, empty: true, initialized: true });
  const nullRecord = Object.assign(Object.create(null), { royalists: 3, internationalists: 1, author: shared });
  assert.equal(validateCouncilInfluence(council({ influence: nullRecord })), true);
});

test('Royal Council CRUD and the real model reject invalid influence before any storage write', async () => {
  const { validateRoyalCouncil, upsertCouncilMember } = await import('../assets/js/royal-council.mjs');
  const { normalizeData, serializeSnapshot, saveDraft } = await import('../assets/js/model.mjs');
  const original = freeze(snapshot({ royalCouncil: council({ members: [person()],
    influence: { royalists: 7, internationalists: 3 }, author: { note: '  Council metadata  ' } }) }));
  const before = structuredClone(original);
  const stored = new Map([['gilneas-atlas-draft-v1', 'previous unchanged draft']]);
  const calls = [];
  const storage = { setItem(key, value) { calls.push([key, value]); stored.set(key, value); } };
  const invalidCouncils = [];
  for (const influence of [null, undefined, false, [], {}, { royalists: 0 }, { internationalists: 0 },
    ...[-1, 0.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1, '0', null, undefined].flatMap(value => [
      { royalists: value, internationalists: 0 }, { royalists: 0, internationalists: value },
    ])]) invalidCouncils.push(council({ influence, members: [person()] }));
  const invalidMembers = [];
  for (const influence of [null, undefined, false, [], {}, { party: 0 }, { kingdom: 0 },
    ...[-1, 101, 0.5, NaN, Infinity, '0', null, undefined].flatMap(value => [
      { party: value, kingdom: 0 }, { party: 0, kingdom: value },
    ])]) invalidMembers.push(person({ influence }));
  invalidMembers.push(person({ kind: 'faction', refId: '  house  ', influence: { party: 0, kingdom: 0 } }));
  invalidCouncils.push(...invalidMembers.map(member => council({ members: [member] })));
  for (const royalCouncil of invalidCouncils) {
    const invalid = { ...before, royalCouncil };
    const invalidBefore = structuredClone(invalid);
    assert.throws(() => validateRoyalCouncil(royalCouncil, invalid), /[Вв]лияни|influence|JSON/);
    assert.throws(() => normalizeData(invalid), /[Вв]лияни|influence|JSON/);
    assert.throws(() => serializeSnapshot(invalid), /[Вв]лияни|influence|JSON/);
    assert.throws(() => saveDraft(storage, invalid), /[Вв]лияни|influence|JSON/);
    assert.deepEqual(invalid, invalidBefore);
    assert.deepEqual(calls, []);
    assert.equal(stored.get('gilneas-atlas-draft-v1'), 'previous unchanged draft');
  }
  for (const member of invalidMembers) {
    assert.throws(() => upsertCouncilMember(original, member), /[Вв]лияни|influence|JSON/);
    assert.deepEqual(original, before);
  }
  const edited = upsertCouncilMember(original, person({ influence: { party: 0, kingdom: 100 } }));
  assert.deepEqual(edited.royalCouncil.influence, before.royalCouncil.influence);
  assert.deepEqual(normalizeData(edited), edited);
  assert.deepEqual(original, before);
});

test('explicit pool updates return detached full snapshots preserving ratings and every author field', async () => {
  const { updatePartyInfluence, derivePartyInfluence } = await engine();
  assert.equal(typeof updatePartyInfluence, 'function');
  const legacy = freeze(snapshot());
  const legacyBefore = structuredClone(legacy);
  const initialized = updatePartyInfluence(legacy, freeze({ royalists: 0, internationalists: 0 }));
  assert.deepEqual(initialized, { ...legacyBefore, royalCouncil: council({ influence: { royalists: 0, internationalists: 0 } }) });
  assert.deepEqual(legacy, legacyBefore);
  const original = freeze(snapshot({ royalCouncil: council({
    influence: { royalists: 19, internationalists: 23, author: { note: '  Original balance metadata  ', sources: [45, ' archive-46 '] }, blank: '', flag: false, nil: null },
    members: [person({ influence: { party: 0, kingdom: 100, lore: { literal: '  Не менять  ' } },
      rating: 87, author: { whitespace: '  exact  ' } }),
      person({ id: 'house-seat', kind: 'faction', refId: '  house  ', party: 'internationalists', rating: 91 }),
      person({ id: 'legacy-person', party: 'neutral', active: false })],
    author: { note: '  Council metadata  ', flag: false, nil: null }, rating: 64,
  }) }));
  const before = structuredClone(original);
  const input = freeze({ royalists: Number.MAX_SAFE_INTEGER, internationalists: 0,
    custom: { note: '  New balance metadata  ', nil: null } });
  const inputBefore = structuredClone(input);
  const updated = updatePartyInfluence(original, input);
  const expected = structuredClone(before);
  expected.royalCouncil.influence = { ...expected.royalCouncil.influence, ...inputBefore };
  assert.deepEqual(updated, expected);
  assert.deepEqual(original, before);
  assert.deepEqual(input, inputBefore);
  assert.notEqual(updated, original);
  assert.notEqual(updated.meta, original.meta);
  assert.notEqual(updated.royalCouncil, original.royalCouncil);
  assert.notEqual(updated.royalCouncil.members, original.royalCouncil.members);
  assert.notEqual(updated.royalCouncil.influence.custom, input.custom);
  assert.equal(Object.hasOwn(updated.royalCouncil.members[2], 'influence'), false);
  assert.deepEqual(derivePartyInfluence(updated.royalCouncil), { royalists: Number.MAX_SAFE_INTEGER,
    internationalists: 0, royalistShare: 1, internationalistShare: 0, empty: false, initialized: true });
  updated.meta.author.note = 'changed result';
  updated.royalCouncil.members[0].influence.party = 99;
  updated.royalCouncil.influence.author.sources[0] = 'changed result';
  updated.royalCouncil.influence.custom.note = 'changed result';
  assert.deepEqual(original, before);
  assert.deepEqual(input, inputBefore);
  const noPool = snapshot({ royalCouncil: council({ members: [person()], author: { note: '  Legacy Council  ' } }) });
  const next = updatePartyInfluence(freeze(noPool), { royalists: 75, internationalists: 25 });
  assert.deepEqual(next.royalCouncil.members, noPool.royalCouncil.members);
  assert.deepEqual(next.royalCouncil.author, noPool.royalCouncil.author);
  assert.equal(Object.hasOwn(noPool.royalCouncil, 'influence'), false);
});

test('updates reject malformed current state and non-JSON direct patches instead of repairing or dropping them', async () => {
  const { updatePartyInfluence } = await engine();
  const original = freeze(snapshot({ royalCouncil: council({ influence: { royalists: 3, internationalists: 7 },
    members: [person({ influence: { party: 0, kingdom: 100 } })] }) }));
  const before = structuredClone(original);
  for (const invalid of [null, undefined, false, '', [], {}, { royalists: 0 }, { internationalists: 0 },
    ...[-1, 0.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1, '0', null, undefined, false, {}, [], 1n].flatMap(value => [
      { royalists: value, internationalists: 0 }, { royalists: 0, internationalists: value },
    ])]) {
    assert.throws(() => updatePartyInfluence(original, invalid), /[Вв]лияни|influence|JSON/);
    assert.deepEqual(original, before);
  }
  const cyclic = {}; cyclic.self = cyclic;
  let getterCalls = 0;
  const accessor = {};
  Object.defineProperty(accessor, 'value', { enumerable: true, get() { getterCalls++; return 1; } });
  for (const metadata of [undefined, NaN, Infinity, () => {}, Symbol('value'), 1n, new Date(), new Map(),
    new Set(), /not-json/, cyclic, Array(1), accessor, { [Symbol('field')]: 0 }]) {
    const influence = { royalists: 0, internationalists: 0, metadata };
    assert.throws(() => updatePartyInfluence(original, influence), /JSON/);
    assert.deepEqual(original, before);
    assert.equal(influence.metadata, metadata);
  }
  assert.equal(getterCalls, 0);
  for (const invalid of [null, undefined, [], '', false, new Map(), new Date()]) {
    assert.throws(() => updatePartyInfluence(invalid, { royalists: 0, internationalists: 0 }), /снимок|JSON/);
  }
  for (const royalCouncil of [null, undefined, [], false,
    council({ influence: null }), council({ influence: { royalists: 0 } }),
    council({ influence: { royalists: Number.MAX_SAFE_INTEGER + 1, internationalists: 0 } }),
    council({ members: [person({ influence: { party: 101, kingdom: 0 } })] }),
    council({ members: [person({ kind: 'faction', influence: { party: 0, kingdom: 0 } })] })]) {
    const invalid = snapshot({ royalCouncil });
    const invalidBefore = structuredClone(invalid);
    assert.throws(() => updatePartyInfluence(invalid, { royalists: 0, internationalists: 0 }), /[Вв]лияни|influence|JSON/);
    assert.deepEqual(invalid, invalidBefore);
  }
  for (const authorMetadata of [undefined, NaN, Infinity, () => {}, new Date(), cyclic, accessor]) {
    assert.throws(() => updatePartyInfluence({ ...before, authorMetadata }, { royalists: 0, internationalists: 0 }), /JSON/);
  }
  assert.equal(getterCalls, 0);
});

test('JSON-only boundaries reject invisible or discarded metadata instead of losing it on save and reload', async () => {
  const { validateCouncilInfluence, derivePartyInfluence, updatePartyInfluence } = await engine();
  const { upsertCouncilMember } = await import('../assets/js/royal-council.mjs');
  const { normalizeData, serializeSnapshot, deserializeSnapshot, saveDraft, loadDraft } = await import('../assets/js/model.mjs');
  const original = freeze(snapshot({ royalCouncil: council({ influence: { royalists: 75, internationalists: 25,
    author: { note: '  Точный текст  ', sources: [45, ' archive-46 '] } },
    members: [person({ influence: { party: 0, kingdom: 100 }, rating: 37 }),
      person({ id: 'house-seat', kind: 'faction', refId: '  house  ', active: false, rating: 82 }),
      person({ id: 'legacy-seat', party: 'neutral', active: false })],
    author: { note: '  Не менять Совет  ', blank: '', flag: false, nil: null } }) }));
  const before = structuredClone(original);
  const hiddenMetadata = { note: 'visible' };
  Object.defineProperty(hiddenMetadata, 'authorDecision', { value: 'must not disappear', enumerable: false });
  const arrayMetadata = [45, ' archive-46 ']; arrayMetadata.authorDecision = 'must not disappear';
  for (const metadata of [hiddenMetadata, arrayMetadata]) {
    const value = council({ influence: { royalists: 75, internationalists: 25, metadata } });
    assert.throws(() => validateCouncilInfluence(value), /JSON/);
    assert.throws(() => derivePartyInfluence(value), /JSON/);
    assert.throws(() => updatePartyInfluence(original, { royalists: 75, internationalists: 25, metadata }), /JSON/);
    assert.throws(() => updatePartyInfluence({ ...before, authorMetadata: metadata }, { royalists: 75, internationalists: 25 }), /JSON/);
    assert.deepEqual(original, before);
  }
  const updated = updatePartyInfluence(original, { royalists: 0, internationalists: Number.MAX_SAFE_INTEGER });
  const edited = upsertCouncilMember(updated, { ...updated.royalCouncil.members[0], influence: { party: 100, kingdom: 0 },
    note: '  Отредактированная запись  ', active: false, advisor: true, party: 'internationalists' });
  assert.deepEqual(edited.royalCouncil.influence, updated.royalCouncil.influence);
  assert.deepEqual(normalizeData(edited), edited);
  assert.deepEqual(deserializeSnapshot(serializeSnapshot(edited)), edited);
  const records = new Map();
  const storage = { setItem: (key, value) => records.set(key, value), getItem: key => records.get(key) ?? null };
  const saved = saveDraft(storage, freeze(edited));
  assert.equal(records.get('gilneas-atlas-draft-v1'), saved);
  assert.deepEqual(JSON.parse(saved), edited);
  const reloaded = loadDraft(storage, original);
  assert.equal(reloaded.isDraft, true);
  assert.equal(reloaded.error, null);
  assert.deepEqual(reloaded.data, edited);
  assert.deepEqual(reloaded.data.sources.map(value => value.id), [45, ' archive-46 ']);
  assert.deepEqual(reloaded.data.royalCouncil.members[0].sources, [45, ' archive-46 ']);
  assert.equal(reloaded.data.royalCouncil.members[0].id, '  council-person  ');
  assert.equal(reloaded.data.factions[0].id, '  house  ');
  assert.deepEqual(reloaded.data.royalCouncil.author, before.royalCouncil.author);
  assert.equal(Object.hasOwn(reloaded.data.royalCouncil.members[2], 'influence'), false);
  assert.deepEqual(original, before);
  const legacy = snapshot({ royalCouncil: council({ members: [person()] }) });
  assert.deepEqual(deserializeSnapshot(serializeSnapshot(legacy)), legacy);
  assert.equal(Object.hasOwn(normalizeData(legacy).royalCouncil, 'influence'), false);
  assert.equal(Object.hasOwn(normalizeData(legacy).royalCouncil.members[0], 'influence'), false);
});

test('malformed member IDs never execute author coercion code while building influence errors', async () => {
  const { validateCouncilInfluence, derivePartyInfluence, updatePartyInfluence } = await engine();
  let coercionCalls = 0;
  const id = { toString() { coercionCalls++; return 'executed author code'; } };
  const value = council({ members: [person({ id, influence: { party: 0, kingdom: 100 } })] });
  for (const read of [validateCouncilInfluence, derivePartyInfluence]) {
    assert.throws(() => read(value), /JSON/);
    assert.equal(coercionCalls, 0);
  }
  assert.throws(() => updatePartyInfluence(snapshot({ royalCouncil: value }), { royalists: 0, internationalists: 0 }), /JSON/);
  assert.equal(coercionCalls, 0);
  assert.equal(value.members[0].id, id);
});
