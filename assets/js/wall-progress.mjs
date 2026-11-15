// Wall bookkeeping stays independent of the atlas model and the DOM.
const LIMIT = 1000000;
const recordRequired = (value, label) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(`Некорректная запись: ${label}`);
};
const integerRequired = (value, min, max, label) => {
  if (!Number.isSafeInteger(value) || value < min || value > max) throw new Error(`Некорректное ${label}: требуется целое число от ${min} до ${max}`);
};

export function validateWallConstruction(track, { claim, validateSources } = {}) {
  recordRequired(track, 'meta.wallConstruction');
  integerRequired(track.max, 1, LIMIT, 'max стены');
  integerRequired(track.value, 0, track.max, 'value стены');
  if (Object.hasOwn(track, 'baseValue')) integerRequired(track.baseValue, 0, track.max, 'baseValue стены');
  if (Object.hasOwn(track, 'events') && !Array.isArray(track.events)) throw new Error('Ожидается массив событий стены');
  if ((track.events ?? []).length > 1000) throw new Error('Допустимо не более 1000 событий стены');
  const ids = new Set();
  const claimRecord = (record, label) => {
    recordRequired(record, label);
    if (typeof record.id !== 'string' || !record.id.length || record.id.length > 100) throw new Error(`Некорректный ID: ${label}`);
    if (ids.has(record.id)) throw new Error(`Повтор ID: ${record.id}`);
    ids.add(record.id);
    claim?.(record, label);
  };
  const sourceRefs = record => {
    if (Object.hasOwn(record, 'sources')) {
      if (!Array.isArray(record.sources)) throw new Error('Ожидается массив источников события стены');
      for (const id of record.sources) {
        if (!(typeof id === 'string' && id.length && id.length <= 100) && !(typeof id === 'number' && Number.isFinite(id))) throw new Error('Некорректный ID источника события стены');
      }
    }
    validateSources?.(record);
  };
  for (const event of track.events ?? []) {
    claimRecord(event, 'событие стены');
    if (typeof event.name !== 'string' || !event.name.trim().length) throw new Error('Требуется название события стены');
    if (Object.hasOwn(event, 'description') && typeof event.description !== 'string') throw new Error('Описание события стены должно быть строкой');
    integerRequired(event.delta, -LIMIT, LIMIT, 'delta события стены');
    sourceRefs(event);
    if (Object.hasOwn(event, 'effects') && !Array.isArray(event.effects)) throw new Error('Ожидается массив эффектов события стены');
    for (const effect of event.effects ?? []) {
      claimRecord(effect, 'эффект события стены');
      if (!['bonus', 'penalty'].includes(effect.kind)) throw new Error('Неверный вид эффекта события стены');
      if (typeof effect.text !== 'string') throw new Error('Текст эффекта события стены должен быть строкой');
      sourceRefs(effect);
    }
  }
  if ((Object.hasOwn(track, 'baseValue') || Object.hasOwn(track, 'events')) && calculate(track).value !== track.value) {
    throw new Error('Прогресс value стены не совпадает с последовательным расчётом событий');
  }
  return track;
}

function calculate(track) {
  const baseValue = Object.hasOwn(track, 'baseValue') ? track.baseValue : track.value;
  let value = baseValue;
  const events = (track.events ?? []).map(record => {
    const before = value;
    value = Math.max(0, Math.min(track.max, before + record.delta));
    return { ...structuredClone(record), before, after: value, appliedDelta: value - before };
  });
  return { baseValue, value, max: track.max, events };
}

export function deriveWallProgress(track) {
  validateWallConstruction(track);
  return calculate(track);
}

const snapshotTrack = snapshot => {
  recordRequired(snapshot, 'снимок атласа');
  recordRequired(snapshot.meta, 'meta снимка атласа');
  validateWallConstruction(snapshot.meta.wallConstruction);
  return snapshot.meta.wallConstruction;
};

export function updateWallEvent(snapshot, event) {
  const old = snapshotTrack(snapshot);
  recordRequired(event, 'событие стены');
  const track = {
    ...structuredClone(old),
    baseValue: Object.hasOwn(old, 'baseValue') ? old.baseValue : old.value,
    events: (old.events ?? []).map(record => structuredClone(record)),
  };
  const index = track.events.findIndex(record => record.id === event.id);
  if (index < 0) track.events.push(structuredClone(event));
  else track.events[index] = { ...track.events[index], ...structuredClone(event) };
  track.value = calculate(track).value;
  validateWallConstruction(track);
  return { ...snapshot, meta: { ...snapshot.meta, wallConstruction: track } };
}

export function removeWallEvent(snapshot, id) {
  const old = snapshotTrack(snapshot);
  if (!(old.events ?? []).some(record => record.id === id)) throw new Error(`Событие стены не найдено: ${String(id)}`);
  const track = {
    ...structuredClone(old),
    baseValue: Object.hasOwn(old, 'baseValue') ? old.baseValue : old.value,
    events: (old.events ?? []).filter(record => record.id !== id).map(record => structuredClone(record)),
  };
  track.value = calculate(track).value;
  validateWallConstruction(track);
  return { ...snapshot, meta: { ...snapshot.meta, wallConstruction: track } };
}
