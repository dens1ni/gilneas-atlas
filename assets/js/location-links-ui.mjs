import { createTypeIcon, typeName } from './object-types.mjs';
import { svgIcon } from './icons.mjs';
import { isMapLocation, resolveLocationLinks, eligibleLocationLinkTargets } from './location-links.mjs';
import { isEditingEnabled } from './edit-mode.mjs';
import { createObjectConditionTag } from './object-condition.mjs';

/** Add an inert sibling frame; the existing glyph and map anchor stay intact. */
export function decorateLocationMarker(marker, location) {
  const enabled = isMapLocation(location);
  marker.classList.toggle('location-container', enabled);
  const frames = [...marker.children].filter(node => node.classList.contains('location-container-frame'));
  if (!enabled) {
    frames.forEach(node => node.remove());
    return;
  }
  frames.slice(1).forEach(node => node.remove());
  if (!frames.length) {
    const frame = document.createElement('span');
    frame.className = 'location-container-frame';
    frame.setAttribute('aria-hidden', 'true');
    marker.append(frame);
  }
}

function make(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = String(text);
  return node;
}

const affiliation = (snapshot, location) => {
  const faction = snapshot.factions.find(record => record.id === location.faction);
  const unknown = location.provenance?.affiliationStatus === 'unknown' ||
    (location.faction == null && location.provenance?.confidence === 'reconstruction' && location.provenance?.affiliationStatus !== 'independent');
  return faction?.name ?? (unknown ? 'Принадлежность не установлена' : 'Без державы');
};

function locationIdentity(snapshot, location) {
  const identity = make('span', 'location-link-identity');
  identity.append(make('span', 'location-link-name', location.name),
    make('small', 'location-link-meta', `${typeName(location.type)} · ${affiliation(snapshot, location)}`));
  const condition = createObjectConditionTag(location);
  if (condition) identity.append(condition);
  return identity;
}

function linkRow(snapshot, location, onSelect, parent = false) {
  const button = make('button', 'location-link-row');
  button.type = 'button';
  button.dataset.locationLink = location.id;
  if (parent) button.setAttribute('aria-label', `Вернуться к локации: ${location.name}`);
  button.append(createTypeIcon(location.type, 'location-link-type-icon'), locationIdentity(snapshot, location));
  const arrow = svgIcon(parent ? 'chevron-left' : 'chevron-down');
  arrow.classList.add('location-link-arrow');
  button.append(arrow);
  button.addEventListener('click', () => onSelect(location.id));
  return button;
}

/** References only; canonical dossiers, inline objects and saving stay upstream. */
export function renderLocationLinkSections({ snapshot, locationId, onSelect, onEditLocation, editingEnabled = isEditingEnabled, body = document.getElementById('dossier-body') }) {
  if (!body) return;
  const section = id => {
    let node = body.querySelector(`#${id}`);
    if (!node) {
      node = make('section', 'location-link-section');
      node.id = id;
      const actions = body.querySelector('.dossier-actions');
      if (actions) actions.before(node);
      else body.append(node);
    }
    node.replaceChildren();
    node.hidden = true;
    return node;
  };
  const childrenSection = section('dossier-location-links');
  const parentsSection = section('dossier-parent-locations');
  if (!snapshot.locations.some(location => location.id === locationId)) return;
  const resolved = resolveLocationLinks(snapshot, locationId);
  if (isMapLocation(resolved.location)) {
    childrenSection.hidden = false;
    childrenSection.append(make('h3', '', 'Объекты локации'), make('p', 'location-links-note', 'Ссылки на метки карты'));
    for (const location of resolved.children) childrenSection.append(linkRow(snapshot, location, onSelect));
    if (!resolved.children.length) childrenSection.append(make('p', 'location-links-empty', 'Связанные метки ещё не добавлены'));
    if (typeof onEditLocation === 'function') {
      const edit = make('button', 'paper-button', 'Связать метку');
      edit.type = 'button';
      edit.id = 'dossier-link-edit';
      edit.setAttribute('data-edit-only', '');
      edit.addEventListener('click', () => { if (editingEnabled()) onEditLocation(resolved.location.id); });
      childrenSection.append(edit);
    }
  }
  if (resolved.parents.length) {
    parentsSection.hidden = false;
    parentsSection.append(make('h3', '', 'Вернуться к локации'));
    for (const location of resolved.parents) parentsSection.append(linkRow(snapshot, location, onSelect, true));
  }
}

const editorByForm = new WeakMap();

/** Unsaved helpers only. Merge readPatch() into the parent's transaction. */
export function initLocationLinksEditor({ getData }) {
  const form = document.getElementById('location-form');
  if (!form) throw new Error('Не найдена форма локации');
  const existing = editorByForm.get(form);
  if (existing) return existing;
  const fields = make('section', 'location-links-editor');
  fields.id = 'location-links-fields';
  const checkboxLabel = make('label', 'check-label location-container-check');
  const checkbox = make('input');
  checkbox.type = 'checkbox';
  checkbox.id = 'location-is-location';
  checkboxLabel.append(checkbox, make('span', '', 'Локация — объединяет метки карты'));
  const note = make('p', 'location-links-note', 'Ссылки не меняют принадлежность и модификаторы объектов.');
  const warning = make('p', 'location-links-warning', 'Уберите ссылки или снова включите «Локация»: с непустыми ссылками обычную метку сохранить нельзя.');
  warning.id = 'location-links-warning';
  warning.setAttribute('role', 'status');
  const searchLabel = make('label', '', 'Найти метку карты');
  const search = make('input');
  search.type = 'search';
  search.id = 'location-link-search';
  search.placeholder = 'Название, тип или держава…';
  searchLabel.append(search);
  const targetLabel = make('label', '', 'Метка карты');
  const target = make('select');
  target.id = 'location-link-target';
  targetLabel.append(target);
  const add = make('button', 'iron-button', 'Связать метку');
  add.type = 'button';
  add.id = 'location-link-add';
  const list = make('ul', 'location-linked-list');
  list.id = 'location-linked-list';
  fields.append(checkboxLabel, note, warning, searchLabel, targetLabel, add, list);
  const description = form.querySelector('#location-description')?.closest('label');
  if (description) description.after(fields);
  else form.append(fields);

  let original = null;
  let links = [];
  function renderList(snapshot) {
    const byId = new Map(snapshot.locations.map(location => [location.id, location]));
    list.replaceChildren(...links.map(id => {
      const location = byId.get(id);
      const row = make('li', 'location-linked-entry');
      row.dataset.locationLinkedId = id;
      if (location) row.append(createTypeIcon(location.type, 'location-link-type-icon'), locationIdentity(snapshot, location));
      else row.append(make('span', 'location-link-missing', `Метка не найдена: ${id}`));
      const remove = make('button', 'square delete');
      remove.type = 'button';
      remove.dataset.locationLinkRemove = id;
      remove.setAttribute('aria-label', `Убрать ссылку: ${location?.name ?? id}`);
      remove.append(svgIcon('close'));
      remove.addEventListener('click', () => {
        const index = links.indexOf(id);
        links = links.filter(linkedId => linkedId !== id);
        refresh();
        const nextId = links[Math.min(index, links.length - 1)];
        const next = [...list.querySelectorAll('[data-location-link-remove]')]
          .find(button => button.dataset.locationLinkRemove === nextId);
        (next ?? (target.disabled ? checkbox : target)).focus({ preventScroll: true });
      });
      row.append(remove);
      return row;
    }));
  }
  function syncAdd() {
    const option = target.selectedOptions[0];
    add.disabled = !checkbox.checked || !option || option.disabled || links.includes(option.value);
  }
  function refresh() {
    const focusedId = list.contains(document.activeElement) ? document.activeElement.dataset.locationLinkRemove : undefined;
    const snapshot = getData();
    const exists = original && snapshot.locations.some(location => location.id === original.id);
    const eligible = !original ? [] : exists
      ? eligibleLocationLinkTargets(snapshot, original.id)
      : snapshot.locations.filter(location => location.id !== original.id);
    const selectedOption = target.selectedOptions[0];
    const selectedId = selectedOption && !selectedOption.hasAttribute('data-placeholder') ? selectedOption.value : null;
    const query = search.value.normalize('NFKC').toLocaleLowerCase('ru').trim();
    const placeholder = make('option', '', 'Выберите метку карты');
    placeholder.disabled = true;
    placeholder.value = '';
    placeholder.setAttribute('data-placeholder', '');
    target.replaceChildren(placeholder);
    for (const location of eligible) {
      const label = `${location.name} · ${typeName(location.type)} · ${affiliation(snapshot, location)}`;
      if (query && location.id !== selectedId && !label.normalize('NFKC').toLocaleLowerCase('ru').includes(query)) continue;
      const option = make('option', '', label);
      option.value = location.id;
      option.disabled = links.includes(location.id);
      target.append(option);
    }
    let retained = [...target.options].find(option => !option.hasAttribute('data-placeholder') && option.value === selectedId);
    if (selectedId !== null && !retained) {
      retained = make('option', '', `Метка не найдена: ${selectedId}`);
      retained.value = selectedId;
      retained.disabled = true;
      target.append(retained);
    }
    (retained ?? placeholder).selected = true;
    search.disabled = !checkbox.checked;
    target.disabled = !checkbox.checked;
    warning.hidden = checkbox.checked || !links.length;
    syncAdd();
    renderList(snapshot);
    if (focusedId !== undefined) {
      [...list.querySelectorAll('[data-location-link-remove]')]
        .find(button => button.dataset.locationLinkRemove === focusedId)?.focus({ preventScroll: true });
    }
  }
  function fill(location) {
    original = {
      id: location.id,
      flagPresent: Object.hasOwn(location, 'isLocation'), flag: location.isLocation === true,
      linksPresent: Object.hasOwn(location, 'linkedLocationIds'), links: [...(location.linkedLocationIds || [])],
    };
    checkbox.checked = original.flag;
    links = [...original.links];
    search.value = '';
    target.replaceChildren();
    refresh();
  }
  function readPatch() {
    if (!original) return {};
    const patch = {};
    if (original.flagPresent || checkbox.checked !== original.flag) patch.isLocation = checkbox.checked;
    if (original.linksPresent || links.length !== original.links.length || links.some((id, index) => id !== original.links[index])) {
      patch.linkedLocationIds = [...links];
    }
    return patch;
  }
  checkbox.addEventListener('change', refresh);
  search.addEventListener('input', refresh);
  target.addEventListener('change', syncAdd);
  add.addEventListener('click', () => {
    const option = target.selectedOptions[0];
    if (add.disabled || !option || option.disabled || links.includes(option.value)) return;
    links = [...links, option.value];
    refresh();
  });
  refresh();
  const api = { fill, readPatch, refresh };
  editorByForm.set(form, api);
  return api;
}
