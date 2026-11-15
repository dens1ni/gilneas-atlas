import test from 'node:test';
import assert from 'node:assert/strict';

const engine = () => import('../assets/js/noble-order.mjs');
const ids = rows => rows.map(row => row.id);
const person = (refId, kingdom, patch = {}) => ({
  kind: 'person', refId, influence: { kingdom }, ...patch,
});
const withCouncil = (nobles, members = [], patch = {}) => ({
  nobles, royalCouncil: { members }, ...patch,
});

function freeze(value, seen = new WeakSet()) {
  if (value !== null && typeof value === 'object' && !seen.has(value)) {
    seen.add(value);
    Object.values(value).forEach(item => freeze(item, seen));
    Object.freeze(value);
  }
  return value;
}

function assertOrder(orderNobles, snapshot, expected) {
  const originals = snapshot.nobles.slice();
  freeze(snapshot);
  const result = orderNobles(snapshot);
  assert.notStrictEqual(result, snapshot.nobles);
  assert.deepEqual(ids(result), expected);
  assert.equal(result.length, originals.length);
  assert.deepEqual(snapshot.nobles, originals);
  for (const row of result) assert.strictEqual(row, originals.find(value => value.id === row.id));
  return result;
}

test('returns a new array of original records without editing a deeply frozen snapshot', async () => {
  const { orderNobles } = await engine();
  assert.equal(typeof orderNobles, 'function');
  const snapshot = {
    nobles: [
      { id: ' first ', name: '  Авторский текст  ', house: null,
        relations: [{ relation: 'friend', name: '  Не связывать по имени  ', sourceIds: [45, ' source '] }],
        spouse: { name: '  Супруга  ', sourceIds: [45] }, metadata: { zero: 0, nil: null, blank: '' } },
      { id: '__proto__', name: '<script>literal</script>', relations: [], spouse: null },
    ],
    sources: [{ id: 45, title: '  Источник  ' }],
    author: { ids: [' first ', '__proto__'], flag: false },
  };
  const before = structuredClone(snapshot);
  const result = assertOrder(orderNobles, snapshot, [' first ', '__proto__']);
  result.reverse();
  result.push(snapshot.nobles[0]);
  assert.deepEqual(snapshot, before);
  assert.strictEqual(result[1], snapshot.nobles[0]);
  assert.equal(typeof globalThis.document, 'undefined');
});

test('missing or non-array noble collections have a fresh empty view-only result', async () => {
  const { orderNobles } = await engine();
  for (const value of [undefined, null, false, 3, 'snapshot', [], {},
    { nobles: undefined }, { nobles: null }, { nobles: false }, { nobles: 'records' },
    { nobles: {} }, { nobles: new Set() }, { nobles: [] }]) {
    freeze(value);
    const first = orderNobles(value);
    const second = orderNobles(value);
    assert.deepEqual(first, []);
    assert.deepEqual(second, []);
    assert.notStrictEqual(first, second);
    if (value?.nobles) assert.notStrictEqual(first, value.nobles);
  }
});

test('orders personal kingdom influence descending with stable zero and equal-rating ties', async () => {
  const { orderNobles } = await engine();
  const nobles = [
    { id: 'zero', name: 'Первый без влияния' },
    { id: 'mid-first', name: 'Средний первый' },
    { id: 'high', name: 'Самый влиятельный', lifeStatus: 'unknown' },
    { id: 'mid-second', name: 'Средний второй', lifeStatus: 'alive' },
    { id: 'one', name: 'Небольшое влияние' },
    { id: 'missing', registryPriority: 999, title: 'Король', age: 80 },
    { id: 'noble-only', influence: { kingdom: 100, party: 100 }, registryPriority: 1000 },
  ];
  const snapshot = withCouncil(nobles, [
    person('mid-second', 50, { influence: { kingdom: 50, party: 100 } }),
    person('one', 1), person('zero', 0, { influence: { kingdom: 0, party: 100 } }),
    person('high', 100, { active: false, influence: { kingdom: 100, party: 0 } }),
    person('mid-first', 50),
  ], { influence: { kingdom: 100 }, registryPriority: ['missing', 'noble-only'] });
  assertOrder(orderNobles, snapshot,
    ['high', 'mid-first', 'mid-second', 'one', 'zero', 'missing', 'noble-only']);
});

test('invalid kingdom values are view-only zero without coercion or clamping', async () => {
  const { orderNobles } = await engine();
  for (const invalid of [-1, 101, 0.5, NaN, Infinity, -Infinity, Number.MAX_VALUE,
    '100', '0', '', null, undefined, false, true, [], {}, 1n]) {
    const snapshot = withCouncil([
      { id: 'first-zero' }, { id: 'invalid' }, { id: 'rated' }, { id: 'last-zero' },
    ], [person('invalid', invalid), person('rated', 1)]);
    assertOrder(orderNobles, snapshot, ['rated', 'first-zero', 'invalid', 'last-zero']);
    assert.ok(Object.is(snapshot.royalCouncil.members[0].influence.kingdom, invalid));
  }
});

test('duplicate exact person refs use their maximum valid kingdom rating without summing', async () => {
  const { orderNobles } = await engine();
  const nobles = [{ id: 'repeated' }, { id: 'stronger' }, { id: 'weak' }];
  const base = [person('repeated', 70, { active: false }), person('repeated', 60),
    person('repeated', -1), person('repeated', '100'), person('stronger', 80), person('weak', 1)];
  const variants = [base, base.slice().reverse(), [...base.slice(2), ...base.slice(0, 2)],
    [...base, person('repeated', undefined), person('repeated', 0), person('repeated', 101)]];
  for (const members of variants) {
    assertOrder(orderNobles, withCouncil(nobles.slice(), members), ['stronger', 'repeated', 'weak']);
  }
});

test('missing or malformed Council collections contribute no ratings to partial legacy snapshots', async () => {
  const { orderNobles } = await engine();
  const nobles = [{ id: 'first' }, { id: 'second' }];
  for (const royalCouncil of [undefined, null, false, 'council', [], {},
    { members: null }, { members: false }, { members: 'members' }, { members: {} },
    { members: [null, undefined, false, 'person', [], {}, person('second', undefined)] }]) {
    assertOrder(orderNobles, { nobles: nobles.slice(), royalCouncil }, ['first', 'second']);
  }
});

test('malformed canonical noble arrays fail clearly without repairing or dropping records', async () => {
  const { orderNobles } = await engine();
  for (const record of [null, undefined, false, 42, 'noble', [], {}, { id: '' },
    { id: 0 }, { id: false }, { id: {} }, { id: new String('literal') }]) {
    const snapshot = freeze({ nobles: [{ id: 'valid' }, record] });
    assert.throws(() => orderNobles(snapshot), error => {
      assert.ok(error instanceof TypeError);
      assert.match(error.message, /nobles|noble|знат|реестр/i);
      return true;
    });
    assert.strictEqual(snapshot.nobles[1], record);
  }
  const sparse = freeze({ nobles: Array(2) });
  assert.throws(() => orderNobles(sparse), /nobles|noble|знат|реестр/i);
  const duplicate = freeze({ nobles: [{ id: ' same ' }, { id: ' same ', name: 'Не объединять' }] });
  assert.throws(() => orderNobles(duplicate), /duplicate|повтор/i);
});

test('keeps exact-house families contiguous by family maximum before stronger outsiders', async () => {
  const { orderNobles } = await engine();
  const nobles = [
    { id: 'royal-child', house: ' royal ', age: 8 },
    { id: 'outsider', house: 'solo' },
    { id: 'middle-child', house: 'middle' },
    { id: 'royal-second', house: ' royal ', age: 90 },
    { id: 'middle-leader', house: 'middle' },
    { id: 'royal-leader', house: ' royal ' },
    { id: 'unknown-outsider' },
  ];
  const snapshot = withCouncil(nobles, [person('royal-leader', 100), person('outsider', 90),
    person('middle-leader', 70), person('middle-child', 60), person('royal-child', 5), person('royal-second', 5)]);
  assertOrder(orderNobles, snapshot,
    ['royal-leader', 'royal-child', 'royal-second', 'outsider', 'middle-leader', 'middle-child', 'unknown-outsider']);

  const literalHouses = withCouncil([
    { id: 'not-trimmed', house: 'royal' }, { id: 'not-folded', house: 'ROYAL' },
    { id: 'outsider' }, { id: 'leader', house: ' royal ' },
  ], [person('leader', 100), person('outsider', 90)]);
  assertOrder(orderNobles, literalHouses, ['leader', 'outsider', 'not-trimmed', 'not-folded']);

  const noRatings = { nobles: [{ id: 'first', house: 'one' }, { id: 'middle', house: 'two' },
    { id: 'last', house: 'one' }] };
  assertOrder(orderNobles, noRatings, ['first', 'last', 'middle']);
});

test('exact explicit family relations form transitive undirected groups without filling missing houses', async () => {
  const { orderNobles } = await engine();
  const roles = ['father', 'mother', 'parent', 'child', 'son', 'daughter',
    'spouse', 'sibling', 'brother', 'sister'];
  for (const relation of roles) {
    for (const fromParent of [true, false]) {
      const link = { relation, nobleId: fromParent ? 'child' : ' parent ', name: '  Не совпадает  ' };
      const nobles = [
        { id: ' parent ', house: null, relations: fromParent ? [link] : [] },
        { id: 'outsider', house: 'solo' },
        { id: 'child', house: 'royal', relations: fromParent ? [] : [link] },
        { id: 'leader', house: 'royal' },
        { id: 'other-parent', relations: [{ relation: 'child', nobleId: 'child' }] },
        { id: 'other-sibling', relations: [{ relation: 'mother', nobleId: 'other-parent' }] },
      ];
      const snapshot = withCouncil(nobles, [person('leader', 100), person('outsider', 90)]);
      assertOrder(orderNobles, snapshot,
        ['leader', ' parent ', 'child', 'other-parent', 'other-sibling', 'outsider']);
      assert.strictEqual(nobles[0].house, null);
      assert.equal(Object.hasOwn(nobles[4], 'house'), false);
      assert.strictEqual((fromParent ? nobles[0] : nobles[2]).relations[0], link);
    }
  }
  const multipleParents = withCouncil([
    { id: 'first-parent', house: 'first' },
    { id: 'unrelated' },
    { id: 'second-parent', house: 'second' },
    { id: 'child', relations: [{ relation: 'father', nobleId: 'first-parent' },
      { relation: 'mother', nobleId: 'second-parent' }, { relation: 'parent', nobleId: 'first-parent' },
      { relation: 'child', nobleId: 'child' }] },
    { id: 'second-sibling', house: 'second' },
    { id: 'first-sibling', house: 'first' },
  ], [person('unrelated', 60), person('second-parent', 50), person('first-parent', 80)]);
  assertOrder(orderNobles, multipleParents,
    ['first-parent', 'second-parent', 'child', 'second-sibling', 'first-sibling', 'unrelated']);

  const zero = { nobles: [{ id: 'earliest', relations: [{ relation: 'sibling', nobleId: 'late' }] },
    { id: 'middle' }, { id: 'late' }] };
  assertOrder(orderNobles, zero, ['earliest', 'late', 'middle']);
});

test('exact spouse nobleId links join existing records across houses without name matching', async () => {
  const { orderNobles } = await engine();
  for (const fromSpouse of [true, false]) {
    const nobles = [
      { id: ' spouse ', house: 'different', spouse: fromSpouse ? { nobleId: 'leader', name: '  Не имя главы  ' } : null },
      { id: 'outsider' },
      { id: 'leader', house: 'royal', spouse: fromSpouse ? null : { nobleId: ' spouse ', name: '  Не имя супруга  ' } },
      { id: 'spouse-house-child', house: 'different' },
    ];
    assertOrder(orderNobles, withCouncil(nobles, [person('leader', 100), person('outsider', 90)]),
      ['leader', ' spouse ', 'spouse-house-child', 'outsider']);
  }
});

test('every exact dead record is last regardless of influence while all other statuses stay nondead', async () => {
  const { orderNobles } = await engine();
  const nobles = [
    { id: 'dead-royal', lifeStatus: 'dead', house: 'royal' },
    { id: 'outsider' },
    { id: 'dead-alone', lifeStatus: 'dead' },
    { id: 'royal-child', house: 'royal' },
    { id: 'royal-leader', house: 'royal', lifeStatus: 'alive' },
    { id: 'historical-unknown', title: 'Прежний король', deathDate: 'long ago' },
    ...['unknown', 'Dead', ' dead', 'dead ', 'deceased', false, null, undefined]
      .map((lifeStatus, index) => ({ id: `status-${index}`, lifeStatus })),
  ];
  const snapshot = withCouncil(nobles, [person('dead-royal', 100, { active: true }),
    person('royal-leader', 95), person('outsider', 90), person('dead-alone', 70),
    person('historical-unknown', 0, { active: false, provenance: { rosterRole: 'historical_predecessor' } })]);
  const result = assertOrder(orderNobles, snapshot,
    ['royal-leader', 'royal-child', 'outsider', 'historical-unknown',
      ...nobles.slice(6).map(row => row.id), 'dead-royal', 'dead-alone']);
  const firstDead = result.findIndex(row => row.lifeStatus === 'dead');
  assert.ok(result.slice(firstDead).every(row => row.lifeStatus === 'dead'));
  assert.equal(Object.hasOwn(nobles[5], 'lifeStatus'), false);
});

test('only living or unknown relatives contribute to family ranking including the dead section', async () => {
  const { orderNobles } = await engine();
  const snapshot = withCouncil([
    { id: 'less-dead-high', lifeStatus: 'dead', house: null,
      relations: [{ relation: 'child', nobleId: 'less-child' }] },
    { id: 'isolated-dead-first', lifeStatus: 'dead' },
    { id: 'royal-dead-low', lifeStatus: 'dead', house: null,
      relations: [{ relation: 'child', nobleId: 'royal-leader' }] },
    { id: 'less-child', house: 'less' },
    { id: 'middle-dead', lifeStatus: 'dead', house: 'middle' },
    { id: 'royal-child', house: 'royal' },
    { id: 'middle-leader', house: 'middle', lifeStatus: 'unknown' },
    { id: 'royal-leader', house: 'royal', lifeStatus: 'alive' },
    { id: 'royal-dead-high', lifeStatus: 'dead', house: 'royal' },
    { id: 'royal-dead-tie', lifeStatus: 'dead', house: 'royal' },
    { id: 'isolated-dead-late', lifeStatus: 'dead' },
    { id: 'unknown-zero' },
  ], [person('less-dead-high', 100), person('isolated-dead-late', 0),
    person('less-child', 10), person('middle-dead', 99), person('middle-leader', 70),
    person('royal-leader', 90), person('royal-dead-low', 1), person('royal-dead-high', 5),
    person('royal-dead-tie', 5)]);
  assertOrder(orderNobles, snapshot,
    ['royal-leader', 'royal-child', 'middle-leader', 'less-child', 'unknown-zero',
      'royal-dead-high', 'royal-dead-tie', 'royal-dead-low', 'middle-dead', 'less-dead-high',
      'isolated-dead-first', 'isolated-dead-late']);
  assert.strictEqual(snapshot.nobles[2].house, null);
});

test('ratings require an actual person record with an exact existing refId and influence record', async () => {
  const { orderNobles } = await engine();
  const arrayInfluence = Object.assign([], { kingdom: 100 });
  const arrayMember = Object.assign([], person('unrated', 100));
  const ignored = [
    arrayMember, person('unrated', 0, { influence: arrayInfluence }),
    person('unrated', 100, { kind: 'faction' }), person('unrated', 100, { kind: 'house' }),
    person('unrated', 100, { kind: 'Person' }), person('unrated', 100, { kind: ' person ' }),
    person('unrated', 100, { kind: undefined }), person('unrated ', 100), person('UNRATED', 100),
    person(new String('unrated'), 100), person(0, 100), person(null, 100), person(undefined, 100),
    person('', 100), person('missing', 100),
    { kind: 'person', id: 'unrated', name: 'Совпавшее имя', influence: { kingdom: 100 } },
    person('unrated', 0, { influence: { party: 100 } }), person('unrated', 0, { influence: null }),
    { kind: 'faction', refId: 'house', representativeId: 'unrated', influence: { kingdom: 100 } },
  ];
  for (const member of ignored) {
    const snapshot = withCouncil([
      { id: 'first' }, { id: 'unrated', name: 'Совпавшее имя', house: 'house' }, { id: 'rated' },
    ], [member, person('rated', 50)]);
    assertOrder(orderNobles, snapshot, ['rated', 'first', 'unrated']);
  }
  assertOrder(orderNobles, withCouncil([{ id: 'base' }, { id: 'exact' }],
    [person('base', 1), person('exact', 50, { influence: { kingdom: 50, party: 'ignored' } })]),
  ['exact', 'base']);

  for (const influence of [undefined, null, false, '100', 100, {}, { party: 100 }, [], [100]]) {
    assertOrder(orderNobles, withCouncil([{ id: 'first' }, { id: 'unrated' }, { id: 'rated' }],
      [person('unrated', 0, { influence }), person('rated', 1)]), ['rated', 'first', 'unrated']);
  }
});

test('malformed family references never create relatives or guess names and surnames', async () => {
  const { orderNobles } = await engine();
  const invalidRelations = [
    [Object.assign([], { relation: 'father', nobleId: 'leader' })],
    null, false, 'family', { relation: 'father', nobleId: 'leader' },
    [null, undefined, false, 'father', [], {}],
    [{ relation: 'father', name: 'Одинаковое имя', sourceIds: [45] }],
    [{ relation: 'father', nobleId: ' leader ' }],
    [{ relation: 'father', nobleId: 'LEADER' }],
    [{ relation: 'father', nobleId: 'missing', name: 'Одинаковое имя' }],
    [{ relation: 'father', nobleId: new String('leader') }],
    [{ relation: 'father', nobleId: null }, { relation: 'mother', nobleId: 0 }],
    [{ relation: 'father', refId: 'leader' }],
    ...['Father', ' father ', 'uncle', 'cousin', 'ancestor', 'vassal', 'liege', 'friend', 'advisor', '']
      .map(relation => [{ relation, nobleId: 'leader', name: 'Одинаковое имя' }]),
  ];
  for (const relations of invalidRelations) {
    const snapshot = withCouncil([
      { id: 'unrelated', name: 'Одинаковое имя', surname: 'Одна фамилия', relations },
      { id: 'outsider', name: 'Третий' },
      { id: 'leader', name: 'Одинаковое имя', surname: 'Одна фамилия' },
    ], [person('leader', 100), person('outsider', 90)]);
    assertOrder(orderNobles, snapshot, ['leader', 'outsider', 'unrelated']);
  }
  for (const spouse of [Object.assign([], { nobleId: 'leader' }), null, false, 'Одинаковое имя',
    {}, { name: 'Одинаковое имя', sourceIds: [45] }, { nobleId: ' leader ', name: 'Одинаковое имя' },
    { nobleId: 'missing', name: 'Одинаковое имя' }, { nobleId: new String('leader') },
    { nobleId: null }, { nobleId: 0 }, { refId: 'leader' }]) {
    assertOrder(orderNobles, withCouncil([
      { id: 'unrelated', name: 'Одинаковое имя', spouse }, { id: 'outsider' },
      { id: 'leader', name: 'Одинаковое имя' },
    ], [person('leader', 100), person('outsider', 90)]), ['leader', 'outsider', 'unrelated']);
  }
  for (const house of [null, undefined, '', false, 0, {}, [], new String('leader')]) {
    const snapshot = withCouncil([{ id: 'first', house }, { id: 'outsider' }, { id: 'leader', house }],
      [person('leader', 100), person('outsider', 90)]);
    assertOrder(orderNobles, snapshot, ['leader', 'outsider', 'first']);
  }
  const vassals = withCouncil([
    { id: 'vassal', house: 'junior', parent: 'leader', liege: 'leader', ancestry: ['leader'],
      relations: [{ relation: 'vassal', nobleId: 'leader' }] },
    { id: 'middle', house: 'middle' },
    { id: 'leader', house: 'senior' },
  ], [person('leader', 100), person('middle', 70)], { factions: [
    { id: 'senior', parent: null, nobles: ['leader'] },
    { id: 'junior', parent: 'senior', parentId: 'senior', ancestorId: 'senior', nobleId: 'leader' },
  ] });
  assertOrder(orderNobles, vassals, ['leader', 'middle', 'vassal']);
});

test('nondead group ties use the first nondead position rather than a dead ancestor position', async () => {
  const { orderNobles } = await engine();
  const simple = withCouncil([
    { id: 'dead-king', lifeStatus: 'dead', house: 'dynasty' },
    { id: 'living-kin', house: 'dynasty', lifeStatus: 'unknown' },
    { id: 'living-unrelated', lifeStatus: 'alive' },
  ], [person('dead-king', 100), person('living-kin', 5), person('living-unrelated', 70)]);
  assertOrder(orderNobles, simple, ['living-unrelated', 'living-kin', 'dead-king']);

  const tied = withCouncil([
    { id: 'dead-king', lifeStatus: 'dead', house: 'dynasty' },
    { id: 'living-unrelated', lifeStatus: 'alive' },
    { id: 'living-kin', house: 'dynasty', lifeStatus: 'unknown' },
  ], [person('dead-king', 100), person('living-kin', 5), person('living-unrelated', 5)]);
  assertOrder(orderNobles, tied, ['living-unrelated', 'living-kin', 'dead-king']);
});

test('dead-only groups rank by their dead maximum while mixed groups retain the nondead family rating', async () => {
  const { orderNobles } = await engine();
  const snapshot = withCouncil([
    { id: 'dead-only-zero', house: 'empty', lifeStatus: 'dead' },
    { id: 'dead-mixed', house: 'mixed', lifeStatus: 'dead' },
    { id: 'dead-only-high-child', house: 'historical-high', lifeStatus: 'dead' },
    { id: 'dead-only-equal', house: 'historical-equal', lifeStatus: 'dead' },
    { id: 'living-unrelated' },
    { id: 'living-kin', house: 'mixed' },
    { id: 'dead-only-high', house: 'historical-high', lifeStatus: 'dead' },
    { id: 'dead-only-zero-later', lifeStatus: 'dead' },
  ], [person('dead-mixed', 100), person('dead-only-high', 80), person('dead-only-equal', 80),
    person('dead-only-high-child', 0), person('living-unrelated', 70), person('living-kin', 5)]);
  assertOrder(orderNobles, snapshot, ['living-unrelated', 'living-kin',
    'dead-only-high', 'dead-only-high-child', 'dead-only-equal', 'dead-mixed',
    'dead-only-zero', 'dead-only-zero-later']);

  const allDead = withCouncil([
    { id: 'child', house: 'one', lifeStatus: 'dead' },
    { id: 'unrelated', lifeStatus: 'dead' },
    { id: 'leader', house: 'one', lifeStatus: 'dead' },
  ], [person('leader', 100), person('unrelated', 90)]);
  assertOrder(orderNobles, allDead, ['leader', 'child', 'unrelated']);

  const mixedZero = withCouncil([
    { id: 'mixed-dead', house: 'zero', lifeStatus: 'dead' },
    { id: 'unrelated-dead', lifeStatus: 'dead' },
    { id: 'living-zero', house: 'zero' },
  ], [person('mixed-dead', 100), person('unrelated-dead', 1)]);
  assertOrder(orderNobles, mixedZero, ['living-zero', 'unrelated-dead', 'mixed-dead']);
});

test('dead append ties preserve nondead family order for literal adversarial IDs and post-sort search', async () => {
  const { orderNobles } = await engine();
  const snapshot = withCouncil([
    { id: '__proto__', house: '__proto__', lifeStatus: 'dead', name: 'предок' },
    { id: ' toString ', house: 'constructor', name: 'найти', age: 5 },
    { id: 'valueOf', name: 'найти' },
    { id: ' constructor ', house: '__proto__', name: 'найти' },
    { id: 'constructor', house: '__proto__', name: 'глава', lifeStatus: 'unknown' },
    { id: 'toString', house: 'constructor', name: 'глава', lifeStatus: 'alive' },
    { id: 'hasOwnProperty', house: 'constructor', lifeStatus: 'dead', name: 'найти' },
  ], [person('__proto__', 100), person('constructor', 80), person('toString', 80),
    person('valueOf', 50), person(' toString ', 10), person('hasOwnProperty', 0)]);
  const ordered = assertOrder(orderNobles, snapshot,
    ['toString', ' toString ', 'constructor', ' constructor ', 'valueOf', 'hasOwnProperty', '__proto__']);
  const matches = noble => noble.name === 'найти';
  assert.deepEqual(ids(ordered.filter(matches)),
    [' toString ', ' constructor ', 'valueOf', 'hasOwnProperty']);
  // Removing leaders before ordering would lose the full-snapshot family ratings.
  assert.deepEqual(ids(orderNobles({ ...snapshot, nobles: snapshot.nobles.filter(matches) })),
    ['valueOf', ' toString ', ' constructor ', 'hasOwnProperty']);
  assert.deepEqual(ids(orderNobles(snapshot)), ids(ordered));

  const literalIds = [' ', ' a ', 'a', 'constructor', '__proto__', 'toString', 'hasOwnProperty',
    'é', 'e\u0301', 'a|b', 'a\\b', '10', '2'];
  const members = literalIds.map((id, index) => person(id, index));
  const independent = withCouncil(literalIds.map(id => ({ id })), members);
  assertOrder(orderNobles, independent, literalIds.slice().reverse());
});
