/** Stored Council balances and personal ratings are independent author values. */
export const COUNCIL_INFLUENCE_COLORS = Object.freeze({
  royalists: '#9aa8b6',
  internationalists: '#639096',
});

const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);

function ownValue(value, key) {
  const descriptor = Object.getOwnPropertyDescriptor(value, key);
  if (descriptor && !Object.hasOwn(descriptor, 'value')) {
    throw new Error('Совет / снимок JSON не содержит вычисляемых полей');
  }
  return descriptor?.value;
}

function assertJSON(value, ancestors = new Set()) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean' ||
      typeof value === 'number' && Number.isFinite(value)) return;
  if (typeof value !== 'object' || ancestors.has(value)) {
    throw new Error('Совет / снимок содержит значение, несовместимое с JSON');
  }
  if (!Array.isArray(value) && ![Object.prototype, null].includes(Object.getPrototypeOf(value))) {
    throw new Error('Совет / снимок JSON требует простые записи');
  }
  ancestors.add(value);
  if (Array.isArray(value)) {
    for (let index = 0; index < value.length; index++) {
      if (!Object.hasOwn(value, index)) throw new Error('Разреженный массив не является JSON');
    }
  }
  for (const key of Reflect.ownKeys(value)) {
    if (typeof key !== 'string') throw new Error('Символьное поле не является JSON');
    const item = ownValue(value, key);
    if (Array.isArray(value) && key === 'length') continue;
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (!descriptor.enumerable || Array.isArray(value) &&
        (!/^(0|[1-9]\d*)$/.test(key) || Number(key) >= value.length)) {
      throw new Error(`Поле ${key} будет потеряно при сохранении JSON; используйте обычную запись или массив без дополнительных полей`);
    }
    assertJSON(item, ancestors);
  }
  ancestors.delete(value);
}

function validateBalances(influence) {
  if (!record(influence)) throw new Error('Влияние royalCouncil.influence: ожидается запись с обоими балансами партий');
  for (const field of ['royalists', 'internationalists']) {
    const value = ownValue(influence, field);
    if (!Object.hasOwn(influence, field) || !Number.isSafeInteger(value) || value < 0) {
      throw new Error(`Влияние royalCouncil.influence.${field}: укажите целое число от 0 до ${Number.MAX_SAFE_INTEGER} (технический предел Number.MAX_SAFE_INTEGER, не игровой максимум)`);
    }
  }
}

/** Validate optional influence without initializing or recalculating stored values. */
export function validateCouncilInfluence(council) {
  if (council === undefined) return true;
  if (!record(council)) throw new Error('Влияние Совета: ожидается запись Королевского Совета');
  if (Object.hasOwn(council, 'influence')) validateBalances(ownValue(council, 'influence'));
  const members = ownValue(council, 'members');
  if (Object.hasOwn(council, 'members') && !Array.isArray(members)) {
    throw new Error('Влияние Совета: ожидается массив members');
  }
  for (let index = 0; index < (members?.length ?? 0); index++) {
    const member = ownValue(members, index);
    if (!record(member)) throw new Error('Некорректный участник Совета');
    if (!Object.hasOwn(member, 'influence')) continue;
    if (ownValue(member, 'kind') !== 'person') throw new Error('Личное влияние допустимо только для персонажа (kind: person)');
    const id = ownValue(member, 'id');
    const label = `Влияние участника Совета ${typeof id === 'string' ? id : `#${index}`}.influence`;
    const influence = ownValue(member, 'influence');
    if (!record(influence)) throw new Error(`${label}: ожидается запись party и kingdom`);
    for (const field of ['party', 'kingdom']) {
      const value = ownValue(influence, field);
      if (!Object.hasOwn(influence, field) || !Number.isInteger(value) || value < 0 || value > 100) {
        throw new Error(`${label}.${field}: укажите целое число от 0 до 100`);
      }
    }
  }
  assertJSON(council);
  return true;
}

/**
 * Read-only view of the stored party pools; people and houses never add to them.
 * Returns { royalists, internationalists, royalistShare, internationalistShare,
 * empty, initialized }. Shares are fractions 0..1, normalized to the larger
 * balance before addition. Missing influence is view-only zero / uninitialized;
 * an explicit zero pair is empty but initialized. Neither case writes defaults.
 */
export function derivePartyInfluence(council) {
  validateCouncilInfluence(council);
  const initialized = council !== undefined && Object.hasOwn(council, 'influence');
  const royalists = initialized ? council.influence.royalists : 0;
  const internationalists = initialized ? council.influence.internationalists : 0;
  const maximum = Math.max(royalists, internationalists);
  const royalistRatio = maximum === 0 ? 0 : royalists / maximum;
  const internationalistRatio = maximum === 0 ? 0 : internationalists / maximum;
  const denominator = royalistRatio + internationalistRatio;
  return {
    royalists,
    internationalists,
    royalistShare: denominator === 0 ? 0 : royalistRatio / denominator,
    internationalistShare: denominator === 0 ? 0 : internationalistRatio / denominator,
    empty: maximum === 0,
    initialized,
  };
}

/**
 * Explicitly replace both balances in a detached full snapshot. Existing balance
 * extras, Council metadata and personal ratings survive; no membership-derived
 * calculations, spending, coercion or clamping occurs here.
 */
export function updatePartyInfluence(snapshot, influence) {
  if (!record(snapshot)) throw new Error('Ожидается снимок атласа');
  validateCouncilInfluence(ownValue(snapshot, 'royalCouncil'));
  assertJSON(snapshot);
  validateBalances(influence);
  assertJSON(influence);
  const next = structuredClone(snapshot);
  const council = next.royalCouncil ?? { version: 1, members: [] };
  council.influence = { ...council.influence, ...structuredClone(influence) };
  next.royalCouncil = council;
  return next;
}
