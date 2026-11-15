import { validateCouncilInfluence } from './council-influence.mjs';

/** Political identities only; membership is stored in the current snapshot. */
export const COUNCIL_PARTIES = Object.freeze([
  Object.freeze({ id: 'royalists', name: 'Роялисты', leaderId: 'noble-genn' }),
  Object.freeze({ id: 'internationalists', name: 'Интернационалисты', leaderId: 'noble-darius' }),
  Object.freeze({ id: 'neutral', name: 'Нейтралы' }),
]);

const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);

function assertJSON(value, ancestors = new Set()) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean' ||
      typeof value === 'number' && Number.isFinite(value)) return;
  if (typeof value !== 'object' || ancestors.has(value)) throw new Error('Совет / снимок содержит значение, несовместимое с JSON');
  if (!Array.isArray(value) && ![Object.prototype, null].includes(Object.getPrototypeOf(value))) {
    throw new Error('Снимок JSON требует простые записи');
  }
  ancestors.add(value);
  if (Array.isArray(value)) {
    for (let index = 0; index < value.length; index++) {
      if (!Object.hasOwn(value, index)) throw new Error('Разреженный массив не является JSON');
      assertJSON(value[index], ancestors);
    }
  } else for (const key of Reflect.ownKeys(value)) {
    if (typeof key !== 'string') throw new Error('Символьное поле не является JSON');
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (!Object.hasOwn(descriptor, 'value')) throw new Error('Снимок JSON не содержит вычисляемых полей');
    assertJSON(descriptor.value, ancestors);
  }
  ancestors.delete(value);
}

/** Validate before the parent normalizer or storage sees the assignment. */
export function validateRoyalCouncil(council, snapshot, { claim, validateSources } = {}) {
  if (council === undefined) return true;
  if (!record(council) || council.version !== 1 || !Array.isArray(council.members)) {
    throw new Error('Некорректный Королевский Совет: version / members');
  }
  const ids = new Set();
  for (const field of ['factions', 'locations', 'territories', 'nobles', 'sources']) {
    for (const value of snapshot?.[field] ?? []) {
      ids.add(value.id);
      if (field === 'locations') for (const object of value.objects ?? []) {
        ids.add(object.id);
        for (const modifier of object.modifiers ?? []) ids.add(modifier.id);
      }
    }
  }
  for (const event of snapshot?.meta?.wallConstruction?.events ?? []) ids.add(event.id);
  const assignments = new Set();
  for (const member of council.members) {
    if (!record(member)) throw new Error('Некорректный участник Совета');
    if (typeof member.id !== 'string' || !member.id.length || member.id.length > 100) {
      throw new Error('Некорректный ID участника Совета');
    }
    if (ids.has(member.id)) throw new Error(`Повтор ID: ${member.id}`);
    ids.add(member.id);
    if (!['faction', 'person'].includes(member.kind)) throw new Error('Некорректное поле kind участника Совета');
    if (!COUNCIL_PARTIES.some(party => party.id === member.party)) throw new Error('Некорректное поле party участника Совета');
    if (!['support', 'oppose', 'unknown'].includes(member.stance)) throw new Error('Некорректное поле stance участника Совета');
    for (const field of ['advisor', 'active']) {
      if (typeof member[field] !== 'boolean') throw new Error(`Некорректное поле ${field} участника Совета`);
    }
    if (typeof member.note !== 'string') throw new Error('Некорректное поле note участника Совета');
    for (const field of ['name', 'title']) {
      if (Object.hasOwn(member, field) && typeof member[field] !== 'string') {
        throw new Error(`Некорректное поле ${field} участника Совета`);
      }
    }
    if (Object.hasOwn(member, 'basis') && !['lore', 'scenario', 'unknown'].includes(member.basis)) {
      throw new Error('Некорректное поле basis участника Совета');
    }
    if (Object.hasOwn(member, 'refId')) {
      if (typeof member.refId !== 'string' || !member.refId.length || member.refId.length > 100) {
        throw new Error('Некорректное поле refId участника Совета');
      }
      const registry = member.kind === 'faction' ? snapshot?.factions : snapshot?.nobles;
      if (!(registry ?? []).some(value => value.id === member.refId)) {
        throw new Error(`Неизвестная ссылка ${member.kind === 'faction' ? 'фракция' : 'персонаж'}: ${member.refId}`);
      }
      const key = JSON.stringify([member.kind, member.refId]);
      if (assignments.has(key)) throw new Error(`Повтор назначения участника Совета: ${member.refId}`);
      assignments.add(key);
    } else if (member.kind === 'faction') {
      throw new Error('Необходима ссылка refId на фракцию участника Совета');
    } else if (typeof member.name !== 'string' || !member.name.trim().length) {
      throw new Error('Необходимо имя независимого участника Совета');
    }
    if (Object.hasOwn(member, 'sources')) {
      if (!Array.isArray(member.sources)) throw new Error('Ожидается массив источников участника Совета');
      const sourceIds = new Set((snapshot?.sources ?? []).map(source => source.id));
      for (const id of member.sources) if (!sourceIds.has(id)) throw new Error(`Неизвестный источник: ${String(id)}`);
    }
    claim?.(member, 'участник Совета');
    validateSources?.(member);
  }
  validateCouncilInfluence(council);
  assertJSON(council);
  return true;
}

/** Replace one complete assignment, never normalize unrelated snapshot data. */
export function upsertCouncilMember(snapshot, member) {
  if (!record(snapshot)) throw new Error('Ожидается снимок атласа');
  assertJSON(snapshot);
  assertJSON(member);
  validateRoyalCouncil(snapshot.royalCouncil, snapshot);
  const next = structuredClone(snapshot);
  const council = next.royalCouncil ?? { version: 1, members: [] };
  const index = council.members.findIndex(value => value.id === member?.id);
  if (index < 0) council.members.push(structuredClone(member));
  else council.members[index] = structuredClone(member);
  next.royalCouncil = council;
  validateRoyalCouncil(council, next);
  return next;
}

export function removeCouncilMember(snapshot, id) {
  if (!record(snapshot)) throw new Error('Ожидается снимок атласа');
  assertJSON(snapshot);
  if (typeof id !== 'string' || !id.length || id.length > 100) throw new Error('Некорректный ID участника Совета');
  validateRoyalCouncil(snapshot.royalCouncil, snapshot);
  if (!snapshot.royalCouncil?.members.some(member => member.id === id)) throw new Error('Участник Совета не найден');
  const next = structuredClone(snapshot);
  next.royalCouncil.members = next.royalCouncil.members.filter(member => member.id !== id);
  validateRoyalCouncil(next.royalCouncil, next);
  return next;
}

/** Identity is derived live; a party never changes the member's actual house. */
export function resolveCouncilMember(snapshot, member) {
  validateRoyalCouncil({ version: 1, members: [member] }, snapshot);
  const faction = member.kind === 'faction' ? snapshot.factions.find(value => value.id === member.refId) : null;
  const noble = member.kind === 'person' && Object.hasOwn(member, 'refId')
    ? snapshot.nobles.find(value => value.id === member.refId) : null;
  const house = noble ? (snapshot.factions ?? []).find(value => value.id === noble.house) ?? null : null;
  return {
    ...member,
    name: faction?.name ?? noble?.name ?? member.name,
    title: Object.hasOwn(member, 'title') ? member.title : noble?.title ?? '',
    faction, noble, house, heraldry: faction?.heraldry ?? house?.heraldry ?? null,
  };
}
