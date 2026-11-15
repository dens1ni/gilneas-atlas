/** Literal author statuses; safe to import without a DOM or application state. */
export const NOBLE_LIFE_STATUSES = Object.freeze([
  Object.freeze({ id: 'alive', label: 'Жив', color: '#5eaa78' }),
  Object.freeze({ id: 'dead', label: 'Мертв', color: '#d37978' }),
  Object.freeze({ id: 'unknown', label: 'Неизвестно', color: '#96978d' }),
]);

/** View-only fallback; resolving legacy metadata never edits the noble. */
const unknownDefinition = NOBLE_LIFE_STATUSES[2];
const isRecord = value => value !== null && typeof value === 'object' && !Array.isArray(value);

export function resolveNobleLifeStatus(noble) {
  if (!isRecord(noble)) return unknownDefinition;
  const descriptor = Object.getOwnPropertyDescriptor(noble, 'lifeStatus');
  return NOBLE_LIFE_STATUSES.find(definition => definition.id === descriptor?.value) ?? unknownDefinition;
}

/** Validate only this optional field; the parent owns full JSON validation. */
export function validateNobleLifeStatus(noble) {
  if (!isRecord(noble)) throw new Error('Ожидается объект персонажа для проверки lifeStatus');
  const descriptor = Object.getOwnPropertyDescriptor(noble, 'lifeStatus');
  if (descriptor && !NOBLE_LIFE_STATUSES.some(definition => definition.id === descriptor.value)) {
    throw new Error('Некорректное поле lifeStatus персонажа: ожидается alive, dead или unknown');
  }
  return true;
}

/** DOM-only entry point; all views share the same literal, text-only badge. */
export function createNobleLifeStatusTag(noble) {
  const definition = resolveNobleLifeStatus(noble);
  const tag = document.createElement('span');
  tag.setAttribute('class', `noble-life-status noble-life-status-${definition.id}`);
  tag.setAttribute('data-life-status', definition.id);
  tag.textContent = definition.label;
  tag.setAttribute('aria-label', `Статус: ${definition.label}`);
  tag.style.color = definition.color;
  return tag;
}
