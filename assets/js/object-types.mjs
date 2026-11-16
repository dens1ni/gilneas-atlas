/** Shared literal type IDs and 24×24 line geometry; safe to import without a DOM. */
export const TYPE_DEFINITIONS = Object.freeze([
  { id: 'city', label: 'Город', path: 'M3 21V12H8V7H15V12H21V21Z M10 21V16H14V21 M10 10H12 M17 15H18 M5 15H6' },
  { id: 'settlement', label: 'Поселение', path: 'M3 10 12 3 21 10 M5 9V21H19V9 M10 21V15H14V21 M8 12H9 M15 12H16' },
  { id: 'estate', label: 'Поместье', path: 'M7 21V9L5 7V3H9V5H15V3H19V7L17 9V21Z M10 21V16H14V21 M10 10H14' },
  { id: 'fortress', label: 'Крепость', path: 'M3 21V7H6V10H9V7H15V10H18V7H21V21Z M10 21V16H14V21' },
  { id: 'district', label: 'Квартал', path: 'M3 21V12H8V7H15V12H21V21Z M10 21V16H14V21 M10 10H12 M17 15H18 M5 15H6' },
  { id: 'harbor', label: 'Гавань', path: 'M12 4V19 M7 8H17 M4 14C4 22 20 22 20 14 M2 15 4 13 6 15 M18 15 20 13 22 15 M10 3A2 2 0 1 0 14 3A2 2 0 1 0 10 3' },
  { id: 'ferry', label: 'Паромная пристань', path: 'M3 15H21L18 20H6Z M7 15V9H17V15 M9 9V6H15V9 M12 6V3 M3 22C5 20 7 24 9 22S13 20 15 22 19 24 21 22' },
  { id: 'forest', label: 'Лес', path: 'M12 2 5 11H8L3 17H10V22H14V17H21L16 11H19Z' },
  { id: 'mine', label: 'Шахта', path: 'M3 21 9 5 15 3 21 21Z M7 21V14L12 10 17 14V21 M10 21V16H14V21' },
  { id: 'landmark', label: 'Ориентир', path: 'M4 3H20V12C20 17 16 20 12 22 8 20 4 17 4 12Z M8 8H16 M12 5V17' },
  { id: 'building', label: 'Здание', path: 'M3 10 12 3 21 10 M5 9V21H19V9 M10 21V15H14V21 M8 12H9 M15 12H16' },
  { id: 'resource', label: 'Ресурс', path: 'M12 2 21 8 18 20 6 20 3 8Z M3 8H21 M8 8 12 20 16 8 M8 8 12 2 16 8' },
  { id: 'farm', label: 'Ферма', path: 'M2 12 8 6 14 12 M4 10V20H12V10 M7 20V15H9V20 M16 20V6 M16 10 13 7 M16 14 20 10 M16 18 20 14 M2 22H22' },
  { id: 'workshop', label: 'Мастерская', path: 'M3 21V10L10 4 17 10V21Z M7 21V15H12V21 M15 3 18 6 21 3 M18 6V13 M15 10H21' },
  { id: 'barracks', label: 'Казармы', path: 'M3 21V9L12 4 21 9V21Z M9 21V15H15V21 M6 11H8 M16 11H18 M10 8H14 M12 2V5' },
  { id: 'church', label: 'Церковь', path: 'M12 2V8 M9 5H15 M8 21V11L12 8 16 11V21 M8 14H4V21H20V14H16 M10 21V17A2 2 0 0 1 14 17V21' },
  { id: 'cemetery', label: 'Кладбище', path: 'M4 21V14A4 4 0 0 1 12 14V21 M8 12V18 M6 15H10 M15 21V16A3 3 0 0 1 21 16V21 M18 15V19 M2 22H22' },
  { id: 'quarry', label: 'Каменоломня', path: 'M2 21 6 12H11L14 7H19L22 21Z M6 12 9 21 M14 7 16 15H21 M11 12 13 17H16 M3 5 9 3 14 5 M8 4 5 10' },
  { id: 'lumbermill', label: 'Лесопилка', path: 'M3 18H21V22H3Z M5 18V14H19V18 M8 14V10H16V14 M3 4 7 8 11 4 15 8 19 4 22 7 M4 9 20 2' },
  { id: 'mill', label: 'Мельница', path: 'M8 22 10 12H14L16 22Z M12 10 5 3 2 6 9 13 M12 10 19 3 22 6 15 13 M12 10 5 17 2 14 9 7 M12 10 19 17 22 14 15 7 M11 22V18H13V22' },
  { id: 'warehouse', label: 'Склад', path: 'M2 9 12 3 22 9 M4 8V21H20V8 M8 21V12H16V21 M8 15H16 M8 18H16 M5 21H19' },
  { id: 'market', label: 'Рынок', path: 'M3 9 5 3H19L21 9 M3 9V12H21V9Z M5 12V21H19V12 M3 21H21 M8 3V9 M12 3V9 M16 3V9 M9 16H15' },
  { id: 'inn', label: 'Таверна', path: 'M3 21V10L11 4 19 10V21 M7 21V15H11V21 M15 14H19 M16 2H22V8H16Z M19 8V11' },
  { id: 'stable', label: 'Конюшня', path: 'M2 10 12 3 22 10 M4 9V21H20V9 M8 21V13L11 10 15 12V16H12L10 19V21 M11 10V7 M15 12H17' },
  { id: 'watchtower', label: 'Сторожевая башня', path: 'M7 22V8H17V22 M5 8V3H8V5H11V3H14V5H17V3H20V8Z M10 12H14 M10 22V17H14V22 M4 22H20' },
  { id: 'military-camp', label: 'Военный лагерь', path: 'M2 21 10 7 18 21Z M6 21 10 14 14 21 M17 3V16 M17 3H22L20 6 22 9H17 M2 22H22' },
  { id: 'gate', label: 'Ворота', path: 'M2 21V7H7V21 M17 21V7H22V21 M7 9H17 M7 21V15A5 5 0 0 1 17 15V21 M4 7V3 M20 7V3 M10 21V14 M14 21V14' },
  { id: 'bridge', label: 'Мост', path: 'M2 11H22 M3 11V21 M21 11V21 M3 18C6 10 18 10 21 18 M6 11V7 M10 11V7 M14 11V7 M18 11V7 M2 22C5 20 7 24 10 22S15 20 18 22H22' },
  { id: 'school', label: 'Школа', path: 'M3 21V10L12 4 21 10V21Z M10 21V15H14V21 M6 12H8 M16 12H18 M12 4V1H18V4H12' },
  { id: 'library', label: 'Библиотека', path: 'M3 3H21V22H3Z M3 12H21 M6 5V10H9V5Z M12 5 14 10 17 9 15 4Z M6 15V20H9V15Z M12 15V20H15V15Z M18 15V20' },
  { id: 'hospital', label: 'Лазарет', path: 'M4 21V5H20V21Z M10 21V16H14V21 M10 7H14V9H16V12H14V14H10V12H8V9H10Z' },
  { id: 'garden', label: 'Сад', path: 'M12 21V12 M12 12C5 12 4 7 7 6 3 2 9 1 12 6 15 1 21 2 17 6 20 7 19 12 12 12Z M12 17C8 13 4 14 5 18L12 20 M12 17C16 13 20 14 19 18L12 20 M4 22H20' },
  { id: 'orchard', label: 'Фруктовый сад', path: 'M12 22V15 M8 15C3 15 2 10 5 7 3 3 9 1 12 4 15 1 21 3 19 7 22 10 21 15 16 15Z M8 8A1 1 0 1 0 10 8A1 1 0 1 0 8 8 M14 10A1 1 0 1 0 16 10A1 1 0 1 0 14 10 M7 22H17' },
  { id: 'fishery', label: 'Рыбный промысел', path: 'M4 12C8 5 16 5 19 12 16 19 8 19 4 12Z M4 12 1 8V16Z M13 7C11 10 11 14 13 17 M16 11H17 M3 21C6 19 9 23 12 21S18 19 21 21' },
  { id: 'granary', label: 'Амбар', path: 'M3 10 12 3 21 10 M5 9V21H19V9 M9 21V13H15V21 M9 13 15 21 M15 13 9 21 M10 7H14' },
  { id: 'shipyard', label: 'Верфь', path: 'M3 16H21L18 21H6Z M8 16V4H17 M12 4V13 M12 6 18 13H12 M4 2V16 M4 3H7 M2 22H22' },
  { id: 'forge', label: 'Кузница', path: 'M3 12H21L17 16H9L7 12 M10 16V20H16V16 M8 22H18 M8 7 13 2 17 6 12 11Z M14 8 20 14' },
  { id: 'ruins', label: 'Руины', path: 'M3 21V10H7V6L11 10V21 M11 16H16V10L21 14V21 M3 14H7 M16 17H21 M2 22H22 M13 3 11 6 M18 4 20 7' },
  { id: 'monument', label: 'Памятник', path: 'M8 17 10 3H14L16 17Z M6 17H18V20H6Z M3 20H21V23H3Z M10 3 12 1 14 3 M11 8H13' },
  { id: 'well', label: 'Колодец', path: 'M3 9 12 3 21 9 M5 9V21 M19 9V21 M5 18C5 15 19 15 19 18V21H5Z M8 11H16 M12 11V16 M10 13H14V16H10Z' },
  { id: 'lighthouse', label: 'Маяк', path: 'M8 5 12 2 16 5Z M9 5H15V9H9Z M12 5V9 M8 10H16 M10 10 8 22H16L14 10Z M11 22V18H13V22 M9 16H15 M6 22H18 M2 5 6 6 M2 9 6 8 M18 6 22 5 M18 8 22 9' },
].map(definition => Object.freeze(definition)));

export const OBJECT_TYPE_IDS = Object.freeze(TYPE_DEFINITIONS.map(definition => definition.id));

const definitionById = new Map(TYPE_DEFINITIONS.map(definition => [definition.id, definition]));

export function typeName(type) {
  return definitionById.get(type)?.label ?? (type == null || type === '' ? 'Не указан' : String(type));
}

export function createTypeIcon(type, className = '') {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '1.6');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  svg.setAttribute('data-type', type ?? '');
  if (className) svg.setAttribute('class', className);
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', (definitionById.get(type) ?? definitionById.get('landmark')).path);
  svg.append(path);
  return svg;
}

/** Both scopes use the same catalog; only their default selection differs. */
export function populateTypeSelect(select, { scope = 'object', currentType } = {}) {
  const selected = currentType ?? (scope === 'location' ? 'settlement' : 'building');
  select.replaceChildren();
  TYPE_DEFINITIONS.forEach(definition => {
    const option = document.createElement('option');
    option.value = definition.id;
    option.textContent = definition.label;
    select.append(option);
  });
  if (!definitionById.has(selected)) {
    const option = document.createElement('option');
    option.value = selected;
    option.textContent = typeName(selected);
    select.append(option);
  }
  select.value = selected;
}
