import test from 'node:test';
import assert from 'node:assert/strict';

const moduleURL = new URL('../assets/js/noble-life-status.mjs', import.meta.url);
const unknownDefinition = { id: 'unknown', label: 'Неизвестно', color: '#96978d' };

function deepFreeze(value) {
  if (value !== null && typeof value === 'object') {
    Object.values(value).forEach(deepFreeze);
    Object.freeze(value);
  }
  return value;
}

function legacyNoble() {
  return JSON.parse(`{
    "id": "author-noble", "name": "  Авторский персонаж  ",
    "role": "ruler", "active": true, "race": "undead",
    "lifecycle": "dead", "currentWiki": { "status": "alive" },
    "royalCouncil": { "active": true },
    "sources": [0, "0"], "description": "  <script>literal</script>  ",
    "extension": { "__proto__": { "literal": "  Не менять  " },
      "values": [null, false, 0, "", { "lifeStatus": "dead" }] }
  }`);
}

test('DOM-less legacy nobles resolve to immutable unknown without adding optional metadata', async () => {
  assert.equal(typeof globalThis.window, 'undefined');
  assert.equal(typeof globalThis.document, 'undefined');
  const { resolveNobleLifeStatus } = await import(moduleURL);
  const noble = deepFreeze(legacyNoble());
  const before = JSON.stringify(noble);

  const definition = resolveNobleLifeStatus(noble);

  assert.deepEqual(definition, unknownDefinition);
  assert.ok(Object.isFrozen(definition));
  assert.throws(() => { definition.label = 'Жив'; }, TypeError);
  assert.equal(Object.hasOwn(noble, 'lifeStatus'), false);
  assert.equal(JSON.stringify(noble), before);
});

test('shared definitions expose only the three exact statuses with deeply frozen Russian labels and colors', async () => {
  const { NOBLE_LIFE_STATUSES, resolveNobleLifeStatus } = await import(moduleURL);
  assert.deepEqual(NOBLE_LIFE_STATUSES, [
    { id: 'alive', label: 'Жив', color: '#5eaa78' },
    { id: 'dead', label: 'Мертв', color: '#d37978' },
    unknownDefinition,
  ]);
  assert.ok(Object.isFrozen(NOBLE_LIFE_STATUSES));
  assert.throws(() => NOBLE_LIFE_STATUSES.push(unknownDefinition), TypeError);
  for (const definition of NOBLE_LIFE_STATUSES) {
    assert.ok(Object.isFrozen(definition), definition.id);
    assert.throws(() => { definition.color = '#000000'; }, TypeError);
  }
  assert.equal(resolveNobleLifeStatus({}), NOBLE_LIFE_STATUSES[2]);
});

test('explicit alive, dead and unknown resolve by exact identity without race or role inference', async () => {
  const { NOBLE_LIFE_STATUSES, resolveNobleLifeStatus } = await import(moduleURL);
  for (const expected of NOBLE_LIFE_STATUSES) {
    const noble = deepFreeze({ ...legacyNoble(), lifeStatus: expected.id });
    const before = JSON.stringify(noble);
    assert.equal(resolveNobleLifeStatus(noble), expected, expected.id);
    assert.equal(noble.lifeStatus, expected.id);
    assert.equal(Object.hasOwn(noble, 'lifeStatus'), true);
    assert.equal(JSON.stringify(noble), before);
  }
});

test('malformed non-record inputs safely resolve unknown instead of accepting attached status fields', async () => {
  const { NOBLE_LIFE_STATUSES, resolveNobleLifeStatus } = await import(moduleURL);
  const invalid = [
    undefined, null, true, false, 0, 1, 'alive', '', Symbol('alive'),
    [], Object.assign([], { lifeStatus: 'alive' }),
    Object.assign(() => {}, { lifeStatus: 'dead' }),
  ];
  for (const noble of invalid) {
    assert.equal(resolveNobleLifeStatus(noble), NOBLE_LIFE_STATUSES[2]);
  }
});

test('resolution reads only an own data field and never executes inherited or computed metadata', async () => {
  const { NOBLE_LIFE_STATUSES, resolveNobleLifeStatus } = await import(moduleURL);
  const inherited = Object.create({ lifeStatus: 'alive' });
  assert.equal(Object.hasOwn(inherited, 'lifeStatus'), false);
  assert.equal(resolveNobleLifeStatus(inherited), NOBLE_LIFE_STATUSES[2]);
  assert.equal(Object.hasOwn(inherited, 'lifeStatus'), false);

  const computed = Object.defineProperty({}, 'lifeStatus', {
    enumerable: true,
    get() { throw new Error('Вычисляемое поле не должно выполняться'); },
  });
  assert.equal(resolveNobleLifeStatus(computed), NOBLE_LIFE_STATUSES[2]);

  const plain = Object.assign(Object.create(null), { lifeStatus: 'dead' });
  assert.equal(resolveNobleLifeStatus(plain), NOBLE_LIFE_STATUSES[1]);
});

test('validation returns true for absent optional metadata and every exact enum without changing full JSON', async () => {
  const { NOBLE_LIFE_STATUSES, validateNobleLifeStatus } = await import(moduleURL);
  assert.equal(typeof validateNobleLifeStatus, 'function');
  for (const noble of [
    legacyNoble(),
    ...NOBLE_LIFE_STATUSES.map(definition => ({ ...legacyNoble(), lifeStatus: definition.id })),
  ]) {
    deepFreeze(noble);
    const before = JSON.stringify(noble);
    const wasPresent = Object.hasOwn(noble, 'lifeStatus');
    assert.equal(validateNobleLifeStatus(noble), true);
    assert.equal(Object.hasOwn(noble, 'lifeStatus'), wasPresent);
    assert.equal(JSON.stringify(noble), before);
  }
});

function invalidLifeStatuses() {
  return [
    undefined, null, true, false, 0, 1, -1, 1.5, NaN, Infinity, -Infinity,
    0n, Symbol('alive'), new String('alive'), [], {}, ['alive'], { id: 'alive' },
    '', 'none', 'true', '0', 'Alive', 'ALIVE', 'Dead', 'DEAD', 'Unknown', 'UNKNOWN',
    ' alive', 'alive ', '\talive', 'dead\n', 'unknown ',
    'Жив', 'Мертв', 'Неизвестно', 'undead', 'toString', 'constructor', '__proto__',
    '<img src=x onerror="globalThis.injected=true">',
  ];
}

test('strict validation rejects every explicit non-enum without coercion or rewriting legacy values', async () => {
  const { NOBLE_LIFE_STATUSES, resolveNobleLifeStatus, validateNobleLifeStatus } = await import(moduleURL);
  let coercions = 0;
  const poison = {
    [Symbol.toPrimitive]() { coercions++; throw new Error('Не выполнять преобразование'); },
    toString() { coercions++; throw new Error('Не выполнять преобразование'); },
    valueOf() { coercions++; throw new Error('Не выполнять преобразование'); },
  };
  for (const lifeStatus of [...invalidLifeStatuses(), poison]) {
    const noble = deepFreeze({ ...legacyNoble(), lifeStatus });
    const original = Object.getOwnPropertyDescriptors(noble);
    const extensionJSON = JSON.stringify(noble.extension);
    assert.throws(() => validateNobleLifeStatus(noble), error => {
      assert.equal(error.name, 'Error');
      assert.match(error.message, /[А-Яа-яЁё].*lifeStatus/);
      assert.match(error.message, /alive.*dead.*unknown/);
      return true;
    });
    assert.equal(resolveNobleLifeStatus(noble), NOBLE_LIFE_STATUSES[2]);
    assert.deepEqual(Object.getOwnPropertyDescriptors(noble), original);
    assert.equal(JSON.stringify(noble.extension), extensionJSON);
  }
  assert.equal(coercions, 0);

  let reads = 0;
  const computed = Object.defineProperty({}, 'lifeStatus', {
    enumerable: true,
    get() { reads++; return 'alive'; },
  });
  assert.throws(() => validateNobleLifeStatus(computed), /Некорректн.*lifeStatus.*alive.*dead.*unknown/);
  assert.equal(reads, 0);
});

test('validation rejects malformed noble inputs with a clear Russian error instead of treating them as absence', async () => {
  const { validateNobleLifeStatus } = await import(moduleURL);
  for (const noble of [
    undefined, null, true, false, 0, 1, '', 'alive', Symbol('noble'),
    [], Object.assign([], { lifeStatus: 'alive' }),
    Object.assign(() => {}, { lifeStatus: 'dead' }),
  ]) {
    assert.throws(() => validateNobleLifeStatus(noble), error => {
      assert.equal(error.name, 'Error');
      assert.match(error.message, /Ожидается.*объект.*персонажа.*lifeStatus/);
      return true;
    });
  }
});

function withFakeDocument(run) {
  const original = Object.getOwnPropertyDescriptor(globalThis, 'document');
  const created = [];
  Object.defineProperty(globalThis, 'document', {
    configurable: true,
    value: {
      createElement(tagName) {
        const attributes = new Map();
        const node = {
          tagName: tagName.toUpperCase(),
          style: {},
          textContent: '',
          children: [],
          setAttribute(name, value) { attributes.set(name, String(value)); },
          getAttribute(name) { return attributes.get(name) ?? null; },
          get className() { return attributes.get('class') ?? ''; },
          get dataset() { return { lifeStatus: attributes.get('data-life-status') }; },
          set innerHTML(value) { assert.fail('Status tags must never write innerHTML'); },
        };
        created.push(node);
        return node;
      },
    },
  });
  try {
    return run(created);
  } finally {
    if (original) Object.defineProperty(globalThis, 'document', original);
    else delete globalThis.document;
  }
}

test('shared tags are safe accessible semantic-colored spans for exact statuses and unknown fallbacks', async () => {
  const { NOBLE_LIFE_STATUSES, resolveNobleLifeStatus, createNobleLifeStatusTag } = await import(moduleURL);
  assert.equal(typeof createNobleLifeStatusTag, 'function');
  const cases = [
    ...NOBLE_LIFE_STATUSES.map(definition => deepFreeze({ ...legacyNoble(), lifeStatus: definition.id })),
    deepFreeze(legacyNoble()),
    ...invalidLifeStatuses().map(lifeStatus => deepFreeze({ ...legacyNoble(), lifeStatus })),
    undefined, null, 'alive', Object.assign([], { lifeStatus: 'alive' }),
  ];
  withFakeDocument(created => {
    cases.forEach((noble, index) => {
      const expected = resolveNobleLifeStatus(noble);
      const descriptors = noble && typeof noble === 'object' ? Object.getOwnPropertyDescriptors(noble) : null;
      const tag = createNobleLifeStatusTag(noble);
      assert.equal(created.length, index + 1);
      assert.equal(created[index], tag);
      assert.equal(tag.tagName, 'SPAN');
      assert.equal(tag.className, `noble-life-status noble-life-status-${expected.id}`);
      assert.equal(tag.getAttribute('data-life-status'), expected.id);
      assert.equal(tag.dataset.lifeStatus, expected.id);
      assert.equal(tag.textContent, expected.label);
      assert.equal(tag.getAttribute('aria-label'), `Статус: ${expected.label}`);
      assert.equal(tag.style.color, expected.color);
      assert.deepEqual(tag.children, []);
      assert.ok([null, expected.label, `Статус: ${expected.label}`].includes(tag.getAttribute('title')));
      if (descriptors) assert.deepEqual(Object.getOwnPropertyDescriptors(noble), descriptors);
    });
    assert.equal(new Set(created).size, cases.length);
  });
  assert.equal(typeof globalThis.document, 'undefined');
  assert.equal(typeof globalThis.window, 'undefined');
});
