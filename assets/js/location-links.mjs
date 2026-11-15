/** Pure marker semantics; the flag never replaces a location's type. */
export function isMapLocation(record) {
  return record?.isLocation === true;
}

const isRecord = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const isExactId = value => typeof value === 'string' && value.length >= 1 && value.length <= 100;

/** Validate only the canonical map graph; unrelated snapshot fields remain opaque. */
export function validateLocationLinks(snapshot) {
  if (!isRecord(snapshot)) throw new Error('Ожидается снимок атласа');
  if (!Array.isArray(snapshot.locations)) throw new Error('Ожидается массив locations в снимке атласа');
  const byId = new Map();
  for (let index = 0; index < snapshot.locations.length; index++) {
    const location = snapshot.locations[index];
    if (!isRecord(location)) throw new Error(`Некорректная запись locations[${index}]: ожидается запись локации`);
    if (!isExactId(location.id)) {
      throw new Error(`Некорректный locations[${index}].id: ожидается точная строка длиной 1–100 символов`);
    }
    if (byId.has(location.id)) throw new Error(`Повтор ID локации в locations[${index}]: ${location.id}`);
    byId.set(location.id, location);
    if (Object.hasOwn(location, 'isLocation') && typeof location.isLocation !== 'boolean') {
      throw new Error(`Некорректное поле isLocation локации ${location.id}: ожидается логическое значение boolean`);
    }
    if (Object.hasOwn(location, 'linkedLocationIds') && !Array.isArray(location.linkedLocationIds)) {
      throw new Error(`Некорректное поле linkedLocationIds локации ${location.id}: ожидается массив строк`);
    }
    if (location.linkedLocationIds?.length && !isMapLocation(location)) {
      throw new Error(`Локация ${location.id}: непустые linkedLocationIds требуют isLocation === true`);
    }
    const references = new Set();
    for (let linkIndex = 0; linkIndex < (location.linkedLocationIds?.length ?? 0); linkIndex++) {
      const targetId = location.linkedLocationIds[linkIndex];
      if (!isExactId(targetId)) {
        throw new Error(`Локация ${location.id}, linkedLocationIds[${linkIndex}]: ожидается точная строка длиной 1–100 символов`);
      }
      if (references.has(targetId)) {
        throw new Error(`Локация ${location.id}, linkedLocationIds[${linkIndex}]: повтор ссылки ${targetId}`);
      }
      references.add(targetId);
      if (targetId === location.id) {
        throw new Error(`Локация ${location.id}, linkedLocationIds[${linkIndex}]: нельзя ссылаться на саму себя`);
      }
    }
  }
  for (const location of snapshot.locations) {
    for (let linkIndex = 0; linkIndex < (location.linkedLocationIds?.length ?? 0); linkIndex++) {
      const targetId = location.linkedLocationIds[linkIndex];
      if (!byId.has(targetId)) {
        throw new Error(`Локация ${location.id}, linkedLocationIds[${linkIndex}]: цель ${targetId} не найдена в locations; укажите ID существующего маркера`);
      }
    }
  }
  // Iterative DFS distinguishes shared DAG children from an active-path cycle.
  const state = new Map();
  for (const root of snapshot.locations) {
    if (state.has(root.id)) continue;
    state.set(root.id, 1);
    const pending = [{ location: root, next: 0 }];
    while (pending.length) {
      const frame = pending[pending.length - 1];
      const links = frame.location.linkedLocationIds ?? [];
      if (frame.next === links.length) {
        state.set(frame.location.id, 2);
        pending.pop();
        continue;
      }
      const targetId = links[frame.next++];
      if (state.get(targetId) === 1) {
        throw new Error(`Цикл linkedLocationIds: ${frame.location.id} → ${targetId}; удалите эту ссылку, чтобы разорвать цикл`);
      }
      if (!state.has(targetId)) {
        state.set(targetId, 1);
        pending.push({ location: byId.get(targetId), next: 0 });
      }
    }
  }
  return true;
}

function requireLocation(snapshot, exactLocationId) {
  validateLocationLinks(snapshot);
  if (!isExactId(exactLocationId)) {
    throw new Error('Некорректный exactLocationId: ожидается точная строка длиной 1–100 символов');
  }
  const location = snapshot.locations.find(record => record.id === exactLocationId);
  if (!location) throw new Error(`Локация не найдена: ${exactLocationId}`);
  return location;
}

/** Direct neighbors only, as current canonical objects, never copied dossiers. */
export function resolveLocationLinks(snapshot, exactLocationId) {
  const location = requireLocation(snapshot, exactLocationId);
  const byId = new Map(snapshot.locations.map(record => [record.id, record]));
  return {
    location,
    children: (location.linkedLocationIds ?? []).map(id => byId.get(id)),
    parents: snapshot.locations.filter(parent => (parent.linkedLocationIds ?? []).includes(exactLocationId)),
  };
}

/** All canonical targets except self and ancestors; includes existing children. */
export function eligibleLocationLinkTargets(snapshot, exactLocationId) {
  requireLocation(snapshot, exactLocationId);
  const parentsById = new Map(snapshot.locations.map(location => [location.id, []]));
  for (const parent of snapshot.locations) {
    for (const targetId of parent.linkedLocationIds ?? []) parentsById.get(targetId).push(parent.id);
  }
  const excluded = new Set([exactLocationId]);
  const pending = [exactLocationId];
  while (pending.length) {
    for (const parentId of parentsById.get(pending.pop()) ?? []) {
      if (excluded.has(parentId)) continue;
      excluded.add(parentId);
      pending.push(parentId);
    }
  }
  return snapshot.locations.filter(location => !excluded.has(location.id));
}
