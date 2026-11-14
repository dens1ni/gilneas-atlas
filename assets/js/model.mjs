const clone = (value, ancestors = new Set(), path = 'snapshot') => {
  if (value && typeof value === 'object') {
    if (ancestors.has(value)) throw new Error('Циклический снимок не является JSON');
    ancestors.add(value);
  }
  if (Array.isArray(value)) {
    for (let index = 0; index < value.length; index++) {
      if (!Object.hasOwn(value, index)) throw new Error('Разреженный массив не является снимком JSON');
    }
    const result = value.map((item, index) => clone(item, ancestors, `${path}[${index}]`));
    ancestors.delete(value);
    return result;
  }
  if (value && typeof value === 'object') {
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== null && prototype !== Object.prototype) throw new Error('Снимок JSON требует простые записи');
    const result = Object.fromEntries(Object.entries(value).map(([key, item]) => [key, clone(item, ancestors, `${path}.${key}`)]));
    ancestors.delete(value);
    return result;
  }
  if (typeof value === 'number' && !Number.isFinite(value)) {
    const field = /\.(x|y)$|\.points\b/.test(path) ? 'координаты' :
      /\.(width|height)$/.test(path) ? 'размеры' : /\.id$/.test(path) ? 'ID' : 'число';
    throw new Error(`Неверные ${field} в снимке JSON: ${path}`);
  }
  if (['function', 'symbol', 'bigint'].includes(typeof value)) throw new Error('Снимок содержит значение, несовместимое с JSON');
  return value;
};
const colorPattern = /^#[0-9a-f]{6}$/i;
const text = (value, max = 20000) => String(value ?? '').slice(0, max);

export function sovereignOf(factions, id) {
  const map = new Map(factions.map(f => [f.id, f]));
  if (id == null) return null;
  const visited = new Set();
  let current = map.get(id);
  if (!current) throw new Error(`Неизвестная фракция: ${id}`);
  while (current.parent != null) {
    if (visited.has(current.id)) throw new Error('Цикл вассальной зависимости');
    visited.add(current.id);
    current = map.get(current.parent);
    if (!current) throw new Error('Сюзерен не найден');
  }
  return current.id;
}

export function factionMembers(factions, id) {
  if (id == null) return [];
  const map = new Map(factions.map(f => [f.id, f]));
  if (!map.has(id)) throw new Error(`Неизвестная фракция: ${id}`);
  factions.forEach(f => sovereignOf(factions, f.id));
  return factions.filter(f => {
    let current = f;
    while (true) {
      if (current.id === id) return true;
      if (current.parent == null) return false;
      current = map.get(current.parent);
    }
  }).map(f => f.id);
}

export function effectiveFaction(location, obj) {
  return obj && Object.hasOwn(obj, 'faction') ? obj.faction : location.faction ?? null;
}

const cross = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
const onSegment = (point, a, b) => {
  // A few ULPs cover interpolated edge points without a fixed map-sized epsilon.
  const scale = Math.max(1, ...point.map(Math.abs), ...a.map(Math.abs), ...b.map(Math.abs));
  const tolerance = Number.EPSILON * 8 * scale;
  const length = Math.hypot(b[0] - a[0], b[1] - a[1]);
  return Math.abs(cross(a, b, point)) <= tolerance * length &&
    point[0] >= Math.min(a[0], b[0]) - tolerance && point[0] <= Math.max(a[0], b[0]) + tolerance &&
    point[1] >= Math.min(a[1], b[1]) - tolerance && point[1] <= Math.max(a[1], b[1]) + tolerance;
};

export function inPolygon(point, points) {
  if (!Array.isArray(point) || point.length !== 2 || !Number.isFinite(point[0]) || !Number.isFinite(point[1])) return false;
  if (!Array.isArray(points) || points.length < 3) return false;
  let inside = false;
  for (let i = 0, j = points.length - 1; i < points.length; j = i++) {
    const a = points[j], b = points[i];
    if (onSegment(point, a, b)) return true;
    if ((a[1] > point[1]) !== (b[1] > point[1]) &&
        point[0] < (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]) inside = !inside;
  }
  return inside;
}

export function validatePolygon(points) {
  if (!Array.isArray(points) || points.length < 3) throw new Error('Полигон требует минимум три вершины');
  for (const point of points) {
    if (!Array.isArray(point) || point.length !== 2 || !Number.isFinite(point[0]) || !Number.isFinite(point[1]) || point[0] < 0 || point[1] < 0) throw new Error('Неверные координаты полигона');
  }
  const vertices = new Set(points.map(point => JSON.stringify(point)));
  if (vertices.size !== points.length) throw new Error('Повтор вершины полигона');
  const segmentsIntersect = (a, b, c, d) => {
    const abC = cross(a, b, c), abD = cross(a, b, d);
    const cdA = cross(c, d, a), cdB = cross(c, d, b);
    return ((abC > 0 && abD < 0 || abC < 0 && abD > 0) &&
      (cdA > 0 && cdB < 0 || cdA < 0 && cdB > 0)) ||
      onSegment(c, a, b) || onSegment(d, a, b) || onSegment(a, c, d) || onSegment(b, c, d);
  };
  for (let i = 0; i < points.length; i++) {
    const a = points[i], b = points[(i + 1) % points.length], c = points[(i + 2) % points.length];
    if (onSegment(c, a, b) || onSegment(a, b, c)) throw new Error('Перекрытие ребер полигона');
    for (let j = i + 1; j < points.length; j++) {
      if (j === i + 1 || i === 0 && j === points.length - 1) continue;
      if (segmentsIntersect(a, b, points[j], points[(j + 1) % points.length])) throw new Error('Самопересечение полигона');
    }
  }
  let area = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i], b = points[(i + 1) % points.length];
    area += cross(points[0], a, b);
  }
  if (area === 0 || !Number.isFinite(area)) throw new Error('Полигон имеет нулевую или неверную площадь');
  return true;
}

const mutateSnapshot = (data, change) => {
  const next = normalizeData(data);
  change(next);
  return normalizeData(next);
};
const findLocation = (data, id) => {
  const location = data.locations.find(l => l.id === id);
  if (!location) throw new Error(`Локация не найдена: ${id}`);
  return location;
};

export function updateLocation(data, id, patch) {
  if (!patch || typeof patch !== 'object' || Array.isArray(patch)) throw new Error('Ожидается изменение локации');
  if (Object.hasOwn(patch, 'id') && patch.id !== id) throw new Error('ID локации нельзя изменить');
  return mutateSnapshot(data, next => {
    const location = findLocation(next, id);
    next.locations[next.locations.indexOf(location)] = { ...location, ...clone(patch) };
  });
}

export function removeLocation(data, id) {
  return mutateSnapshot(data, next => {
    findLocation(next, id);
    next.locations = next.locations.filter(l => l.id !== id);
  });
}

export function upsertFaction(data, faction) {
  if (!faction || typeof faction !== 'object' || Array.isArray(faction)) throw new Error('Ожидается фракция');
  return mutateSnapshot(data, next => {
    const index = next.factions.findIndex(f => f.id === faction.id);
    if (index < 0) next.factions.push(clone(faction));
    else next.factions[index] = { ...next.factions[index], ...clone(faction) };
  });
}

export function deleteFaction(data, id) {
  return mutateSnapshot(data, next => {
    if (!next.factions.some(f => f.id === id)) throw new Error(`Фракция не найдена: ${id}`);
    const referenced = next.factions.some(f => f.parent === id) ||
      next.locations.some(l => l.faction === id || l.objects.some(o => o.faction === id)) ||
      next.territories.some(t => t.faction === id);
    if (referenced) throw new Error(`Фракция используется: ${id}`);
    next.factions = next.factions.filter(f => f.id !== id);
  });
}

export function upsertObject(data, locationId, obj) {
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) throw new Error('Ожидается объект');
  return mutateSnapshot(data, next => {
    const location = findLocation(next, locationId);
    const index = location.objects.findIndex(o => o.id === obj.id);
    if (index < 0) location.objects.push(clone(obj));
    else location.objects[index] = { ...location.objects[index], ...clone(obj) };
    // An explicit undefined edit clears an override; omission leaves it unchanged.
    if (Object.hasOwn(obj, 'faction') && obj.faction === undefined) {
      delete location.objects[index < 0 ? location.objects.length - 1 : index].faction;
    }
  });
}

const findObject = (data, locationId, objId) => {
  const location = findLocation(data, locationId);
  const obj = location.objects.find(o => o.id === objId);
  if (!obj) throw new Error(`Объект не найден: ${objId}`);
  return obj;
};

export function removeObject(data, locationId, objId) {
  return mutateSnapshot(data, next => {
    findObject(next, locationId, objId);
    const location = findLocation(next, locationId);
    location.objects = location.objects.filter(o => o.id !== objId);
  });
}

export function addModifier(data, locationId, objId, modifier) {
  return mutateSnapshot(data, next => {
    findObject(next, locationId, objId).modifiers.push(clone(modifier));
  });
}

export function removeModifier(data, locationId, objId, modifierId) {
  return mutateSnapshot(data, next => {
    const obj = findObject(next, locationId, objId);
    if (!obj.modifiers.some(m => m.id === modifierId)) throw new Error(`Модификатор не найден: ${modifierId}`);
    obj.modifiers = obj.modifiers.filter(m => m.id !== modifierId);
  });
}

// JSON is data, not HTML. Escape only where an exporter embeds it into HTML.
export function serializeSnapshot(data) {
  return JSON.stringify(normalizeData(data), null, 2);
}

export function deserializeSnapshot(text) {
  if (typeof text !== 'string') throw new Error('Ожидается текст JSON');
  return normalizeData(JSON.parse(text));
}

export function saveDraft(storage, data, key = 'gilneas-atlas-draft-v1') {
  const snapshot = serializeSnapshot(data);
  storage.setItem(key, snapshot);
  return snapshot;
}

export function loadDraft(storage, baseline, key = 'gilneas-atlas-draft-v1') {
  const fallback = normalizeData(baseline);
  try {
    const snapshot = storage.getItem(key);
    if (snapshot === null) return { data: fallback, isDraft: false, error: null };
    return { data: deserializeSnapshot(snapshot), isDraft: true, error: null };
  } catch (error) {
    return { data: fallback, isDraft: false, error };
  }
}

export function resetDraft(storage, key = 'gilneas-atlas-draft-v1') {
  storage.removeItem(key);
}

export function upsertTerritory(data, territory) {
  if (!territory || typeof territory !== 'object' || Array.isArray(territory)) throw new Error('Ожидается территория');
  return mutateSnapshot(data, next => {
    const index = next.territories.findIndex(t => t.id === territory.id);
    if (index < 0) next.territories.push(clone(territory));
    else next.territories[index] = { ...next.territories[index], ...clone(territory) };
  });
}

export function removeTerritory(data, id) {
  return mutateSnapshot(data, next => {
    if (!next.territories.some(t => t.id === id)) throw new Error(`Территория не найдена: ${id}`);
    next.territories = next.territories.filter(t => t.id !== id);
  });
}

// Use only inside an HTML script/data element, never for downloaded JSON or drafts.
export function serializeSnapshotForHtml(data) {
  const escapes = { '<': '\\u003c', '>': '\\u003e', '&': '\\u0026', '\u2028': '\\u2028', '\u2029': '\\u2029' };
  return serializeSnapshot(data).replace(/[<>&\u2028\u2029]/g, character => escapes[character]);
}

let idSequence = 0;
export function makeId(prefix) {
  if (typeof prefix !== 'string' || !prefix.length || prefix.length > 100 - 37) throw new Error('Неверный префикс ID');
  const token = globalThis.crypto?.randomUUID?.() ??
    `${Date.now().toString(36)}-${(++idSequence).toString(36)}-${Math.random().toString(36).slice(2, 14)}`;
  return `${prefix}-${token}`;
}

export function normalizeData(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error('Ожидается снимок атласа');
  const data = clone(raw);
  if (data.version !== 1) throw new Error('Несовместимая версия снимка');
  data.meta = { ...data.meta };
  if (!Number.isFinite(data.meta.width) || !Number.isFinite(data.meta.height) || data.meta.width <= 0 || data.meta.height <= 0) throw new Error('Неверные размеры карты');
  if (data.meta.labels !== undefined && !Array.isArray(data.meta.labels)) throw new Error('Ожидается массив: meta.labels');
  for (const label of data.meta.labels ?? []) {
    if (!label || typeof label !== 'object' || Array.isArray(label)) throw new Error('Некорректная запись: метка');
    if (!Number.isFinite(label.x) || !Number.isFinite(label.y) || label.x < 0 || label.y < 0 ||
        label.x > data.meta.width || label.y > data.meta.height) throw new Error('Неверные координаты метки');
    if (typeof label.text !== 'string' || label.size !== undefined && (!Number.isFinite(label.size) || label.size <= 0)) throw new Error('Некорректная метка');
  }
  if (data.meta.chronicle !== undefined && !Array.isArray(data.meta.chronicle)) throw new Error('Ожидается массив: meta.chronicle');
  for (const section of data.meta.chronicle ?? []) {
    if (!section || typeof section !== 'object' || Array.isArray(section) ||
        typeof section.title !== 'string' || typeof section.text !== 'string') throw new Error('Некорректный раздел летописи');
  }
  if (!Array.isArray(data.factions) || !Array.isArray(data.locations)) throw new Error('Отсутствует реестр');
  for (const field of ['territories', 'nobles', 'sources']) {
    if (data[field] === undefined) data[field] = [];
    if (!Array.isArray(data[field])) throw new Error(`Ожидается массив: ${field}`);
  }
  const ids = new Set();
  const claim = (record, label, numeric = false) => {
    if (!record || typeof record !== 'object' || Array.isArray(record)) throw new Error(`Некорректная запись: ${label}`);
    const id = record.id;
    if (!(typeof id === 'string' && id.length > 0 && id.length <= 100) && !(numeric && Number.isFinite(id))) throw new Error(`Некорректный ID: ${label}`);
    if (ids.has(id)) throw new Error(`Повтор ID: ${id}`);
    ids.add(id);
  };
  data.factions.forEach(f => claim(f, 'фракция'));
  data.locations.forEach(l => {
    claim(l, 'локация');
    if (l.objects === undefined) l.objects = [];
    if (!Array.isArray(l.objects)) throw new Error('Ожидается массив объектов');
    l.objects.forEach(o => {
      claim(o, 'объект');
      if (o.modifiers === undefined) o.modifiers = [];
      if (!Array.isArray(o.modifiers)) throw new Error('Ожидается массив модификаторов');
      o.modifiers.forEach(m => claim(m, 'модификатор'));
    });
  });
  data.territories.forEach(t => claim(t, 'территория'));
  data.nobles.forEach(n => claim(n, 'знать'));
  data.sources.forEach(s => {
    claim(s, 'источник', true);
    for (const field of ['title', 'url', 'canonicalUrl', 'quote', 'note']) {
      if (s[field] !== undefined && typeof s[field] !== 'string') throw new Error(`Некорректное поле источника: ${field}`);
    }
  });
  const sourceIds = new Set(data.sources.map(s => s.id));
  const validateSources = record => {
    if (!Object.hasOwn(record, 'sources')) return;
    if (!Array.isArray(record.sources)) throw new Error('Ожидается массив источников');
    for (const id of record.sources) {
      if (!sourceIds.has(id)) throw new Error(`Неизвестный источник: ${String(id)}`);
    }
  };
  (data.meta.chronicle ?? []).forEach(validateSources);
  data.locations.forEach(location => { validateSources(location); location.objects.forEach(validateSources); });
  data.nobles.forEach(validateSources);
  const validateProvenance = record => {
    const provenance = record.provenance;
    if (provenance && Object.hasOwn(provenance, 'sources')) {
      if (!Array.isArray(provenance.sources)) throw new Error('Ожидается массив источников provenance');
      for (const id of provenance.sources) {
        if (!sourceIds.has(id)) throw new Error(`Неизвестный источник: ${String(id)}`);
      }
    }
  };
  data.locations.forEach(l => { validateProvenance(l); l.objects.forEach(validateProvenance); });
  data.factions.forEach(validateProvenance);
  data.territories.forEach(validateProvenance);
  data.nobles.forEach(validateProvenance);
  data.factions = data.factions.map(f => {
    if (typeof f.name !== 'string' || !f.name.length || !colorPattern.test(f.color)) throw new Error('Некорректная фракция');
    return { ...f, name: text(f.name, 160), parent: f.parent ?? null };
  });
  const factionIds = new Set(data.factions.map(f => f.id));
  data.factions.forEach(f => sovereignOf(data.factions, f.id));
  data.locations = data.locations.map(l => {
    if (typeof l.name !== 'string' || !l.name.length) throw new Error('Некорректная локация');
    if (l.aliases !== undefined && (!Array.isArray(l.aliases) || l.aliases.some(alias => typeof alias !== 'string'))) throw new Error('Ожидается массив строк: aliases');
    if (l.faction != null && !factionIds.has(l.faction)) throw new Error('Неизвестная фракция локации');
    if (!Number.isFinite(l.x) || !Number.isFinite(l.y) || l.x < 0 || l.y < 0 || l.x > data.meta.width || l.y > data.meta.height) throw new Error('Точка вне карты');
    l.objects = l.objects.map(o => {
      if (Object.hasOwn(o, 'faction') && o.faction !== null && !factionIds.has(o.faction)) throw new Error('Неизвестная фракция объекта');
      if (!['building', 'resource', 'landmark'].includes(o.type)) throw new Error('Неверный тип объекта');
      if (typeof o.name !== 'string' || !o.name.length) throw new Error('Отсутствует название объекта');
      o.modifiers = o.modifiers.map(m => {
        if (!['bonus', 'penalty'].includes(m.kind)) throw new Error('Неверный вид модификатора');
        return { ...m, text: text(m.text) };
      });
      return { ...o, name: text(o.name, 160), description: text(o.description), owner: text(o.owner, 160) };
    });
    return { ...l, name: text(l.name, 160), description: text(l.description), owner: text(l.owner, 160), faction: l.faction ?? null, type: l.type ?? 'settlement' };
  });
  data.territories.forEach(t => {
    if (!factionIds.has(t.faction)) throw new Error('Неизвестная фракция территории');
    validatePolygon(t.points);
    for (const [x, y] of t.points) {
      if (x < 0 || y < 0 || x > data.meta.width || y > data.meta.height) throw new Error('Координаты территории вне карты');
    }
    if (Object.hasOwn(t, 'name')) t.name = text(t.name, 160);
  });
  return data;
}
