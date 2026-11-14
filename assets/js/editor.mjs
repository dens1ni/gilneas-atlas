import { makeId, upsertObject, updateLocation, removeObject, normalizeData, removeLocation, upsertFaction, deleteFaction,
  upsertTerritory, removeTerritory, validatePolygon } from './model.mjs';
import { svgIcon } from './icons.mjs';

/** Editor transactions are delegated to the parent; no storage is owned here. */
export function initEditor(ctx) {
  const byId = id => document.getElementById(id);
  let objectDraft = null;
  let locationDraft = null;
  let mapTask = null;
  const getUI = () => ctx.getUI?.() ?? ctx.ui;

  function showDialog(id, titleId) {
    document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
    const dialog = byId(id);
    dialog.setAttribute('aria-labelledby', titleId);
    dialog.showModal();
    dialog.focus({ preventScroll: true });
  }

  function setError(id, error = '') {
    byId(id).textContent = error instanceof Error ? error.message : String(error);
  }

  function renderModifiers() {
    const list = byId('modifier-list');
    list.replaceChildren();
    objectDraft.modifiers.forEach(modifier => {
      const row = document.createElement('div');
      row.className = `modifier-editor-row ${modifier.kind}`;
      row.dataset.modifierId = modifier.id;
      row.style.borderLeft = `3px solid var(--${modifier.kind})`;
      const label = document.createElement('label');
      label.textContent = modifier.kind === 'bonus' ? 'Бонус' : 'Штраф';
      const field = document.createElement('textarea');
      field.rows = 2;
      field.maxLength = 20000;
      field.value = modifier.text;
      field.addEventListener('input', () => {
        objectDraft.modifiers = objectDraft.modifiers.map(item => item.id === modifier.id ? { ...item, text: field.value } : item);
      });
      label.append(field);
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'square';
      remove.dataset.modifierRemove = modifier.id;
      remove.setAttribute('aria-label', modifier.kind === 'bonus' ? 'Удалить бонус' : 'Удалить штраф');
      remove.title = remove.getAttribute('aria-label');
      remove.append(svgIcon('close'));
      remove.addEventListener('click', () => {
        objectDraft.modifiers = objectDraft.modifiers.filter(item => item.id !== modifier.id);
        renderModifiers();
        byId('modifier-bonus-add').focus();
      });
      row.append(label, remove);
      list.append(row);
    });
  }

  function appendModifier(kind) {
    if (!objectDraft) return;
    objectDraft.modifiers = [...objectDraft.modifiers, { id: makeId('modifier'), kind, text: '' }];
    renderModifiers();
    byId('modifier-list').lastElementChild.querySelector('textarea').focus();
  }

  function populateFactions(select, value, inherit = false) {
    select.replaceChildren();
    if (inherit) select.add(new Option('Наследуется от локации', '__inherit__'));
    select.add(new Option('Независимый / без державы', '__independent__'));
    ctx.getData().factions.forEach(faction => select.add(new Option(faction.name, faction.id)));
    select.value = value;
  }

  function updateObjectType() {
    const type = byId('object-type').value;
    byId('object-amount-field').hidden = type !== 'resource';
    byId('modifier-fields').hidden = type !== 'building';
  }

  function refresh() {
    const location = ctx.getData().locations.find(record => record.id === ctx.getSelectedId());
    byId('editor-selection-name').textContent = location?.name ?? 'Не выбрано';
    ['location-edit', 'location-move', 'object-create', 'location-delete'].forEach(id => { byId(id).disabled = !location; });
  }

  function open() {
    refresh();
    setError('editor-error');
    const heading = byId('editor').querySelector('h2');
    heading.id = 'editor-title';
    showDialog('editor', heading.id);
  }

  function cancelMapTask() {
    getUI()?.setMapInteraction(null);
    mapTask = null;
    byId('map-task').hidden = true;
    byId('territory-actions').hidden = true;
    byId('drawing-layer').replaceChildren();
  }

  function validPoint(point) {
    const { width, height } = ctx.getData().meta;
    if (!Array.isArray(point) || point.length !== 2 || !point.every(Number.isFinite) ||
        point[0] < 0 || point[0] > width || point[1] < 0 || point[1] > height) {
      ctx.toast?.('Выберите точку внутри карты.');
      return false;
    }
    if (ctx.canPlace && !ctx.canPlace(point)) {
      ctx.toast?.('Неактивная область: выберите точку вне тумана.');
      return false;
    }
    return true;
  }

  function beginPointTask(message, callback) {
    cancelMapTask();
    const ui = getUI();
    if (!ui?.setMapInteraction) {
      ctx.toast?.('Карта ещё не готова.');
      return;
    }
    document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
    mapTask = { kind: 'point' };
    byId('map-task-text').textContent = message;
    byId('map-task').hidden = false;
    ui.setMapInteraction(point => {
      if (!validPoint(point)) return;
      const picked = point.map(Math.round);
      cancelMapTask();
      callback(picked);
    });
    byId('viewport').focus({ preventScroll: true });
  }

  function fillLocation(location, creating = false) {
    locationDraft = { id: location.id, creating };
    byId('location-form').reset();
    byId('location-form-title').textContent = creating ? 'Новая локация' : `Досье · ${location.name}`;
    byId('location-name').value = location.name;
    byId('location-type').value = location.type;
    populateFactions(byId('location-faction'), location.faction ?? '__independent__');
    byId('location-owner').value = location.owner ?? '';
    byId('location-description').value = location.description ?? '';
    byId('location-x').value = location.x;
    byId('location-y').value = location.y;
    byId('location-capital').checked = !!location.capital;
    byId('location-confidence').value = location.provenance?.confidence ?? 'custom';
    setError('location-form-error');
    showDialog('location-editor', 'location-form-title');
  }

  function editLocation(id) {
    const location = ctx.getData().locations.find(record => record.id === id);
    if (!location) {
      ctx.toast?.('Выберите существующую локацию.');
      return;
    }
    fillLocation(location);
  }

  function createLocation() {
    beginPointTask('Нажмите на активную часть карты, чтобы разместить новую локацию. Esc — отмена.', point => {
      fillLocation({ id: makeId('location'), name: '', type: 'settlement', faction: null, owner: '',
        description: '', x: point[0], y: point[1], capital: false, provenance: { confidence: 'custom' } }, true);
    });
  }

  function moveLocation() {
    const id = ctx.getSelectedId();
    const location = ctx.getData().locations.find(record => record.id === id);
    if (!location) {
      ctx.toast?.('Выберите существующую локацию.');
      return;
    }
    beginPointTask(`Новая метка для «${location.name}»: нажмите на карту. Esc — отмена.`, point => {
      try {
        ctx.replaceData(updateLocation(ctx.getData(), id, { x: point[0], y: point[1] }));
        ctx.onSelect?.(id);
        ctx.toast?.('Метка перемещена. Области влияния не изменены.');
      } catch (error) {
        ctx.toast?.(error.message);
      }
    });
  }

  function openObject(locationId, objectId = null) {
    const location = ctx.getData().locations.find(record => record.id === locationId);
    if (!location) {
      ctx.toast?.('Выберите существующую локацию.');
      return;
    }
    const obj = objectId === null ? null : location.objects.find(record => record.id === objectId);
    if (objectId !== null && !obj) {
      ctx.toast?.('Объект больше не существует.');
      return;
    }
    objectDraft = { locationId, id: obj?.id ?? makeId('object'), existing: !!obj,
      modifiers: (obj?.modifiers ?? []).map(modifier => ({ ...modifier })) };
    byId('object-form').reset();
    byId('object-form-title').textContent = `${obj ? 'Изменить объект' : 'Новый объект'} · ${location.name}`;
    byId('object-type').value = obj?.type ?? 'building';
    byId('object-name').value = obj?.name ?? '';
    byId('object-description').value = obj?.description ?? '';
    byId('object-owner').value = obj?.owner ?? '';
    byId('object-amount').value = obj?.amount ?? '';
    const faction = obj && Object.hasOwn(obj, 'faction') ? obj.faction ?? '__independent__' : '__inherit__';
    populateFactions(byId('object-faction'), faction, true);
    setError('object-form-error');
    renderModifiers();
    updateObjectType();
    showDialog('object-editor', 'object-form-title');
  }

  function addObject(locationId) { openObject(locationId); }
  function editObject(locationId, objectId) { openObject(locationId, objectId); }

  async function deleteObject(locationId, objectId) {
    try {
      const obj = ctx.getData().locations.find(record => record.id === locationId)?.objects.find(record => record.id === objectId);
      if (!obj) throw new Error('Объект больше не существует.');
      if (!await ctx.confirm('Удалить объект?', `«${obj.name}» и его модификаторы будут удалены из владения.`)) return;
      ctx.replaceData(removeObject(ctx.getData(), locationId, objectId));
      ctx.toast?.('Объект удалён.');
    } catch (error) {
      ctx.toast?.(error.message);
    }
  }

  byId('modifier-bonus-add').addEventListener('click', () => appendModifier('bonus'));
  async function deleteLocation() {
    try {
      const id = ctx.getSelectedId();
      const location = ctx.getData().locations.find(record => record.id === id);
      if (!location) throw new Error('Выберите существующую локацию.');
      if (!await ctx.confirm('Удалить локацию?', `«${location.name}» и все её объекты будут удалены. Области влияния останутся.`)) return;
      ctx.replaceData(removeLocation(ctx.getData(), id));
      ctx.onSelect?.(null);
      byId('editor').close();
      ctx.toast?.('Локация удалена.');
    } catch (error) {
      setError('editor-error', error);
      ctx.toast?.(error.message);
    }
  }

  byId('modifier-penalty-add').addEventListener('click', () => appendModifier('penalty'));
  byId('object-type').addEventListener('change', updateObjectType);
  byId('location-form').addEventListener('submit', event => {
    event.preventDefault();
    if (!locationDraft) return;
    try {
      const data = ctx.getData();
      const location = data.locations.find(record => record.id === locationDraft.id);
      if (!locationDraft.creating && !location) throw new Error('Локация больше не существует.');
      const patch = {
        name: byId('location-name').value,
        type: byId('location-type').value,
        faction: byId('location-faction').value === '__independent__' ? null : byId('location-faction').value,
        owner: byId('location-owner').value,
        description: byId('location-description').value,
        x: Number(byId('location-x').value),
        y: Number(byId('location-y').value),
        capital: byId('location-capital').checked,
        provenance: { ...location?.provenance, confidence: byId('location-confidence').value },
      };
      const id = locationDraft.id;
      const next = locationDraft.creating ? normalizeData({ ...data, locations: [...data.locations, { id, ...patch, objects: [] }] }) :
        updateLocation(data, id, patch);
      ctx.replaceData(next);
      ctx.onSelect?.(id);
      byId('location-editor').close();
      locationDraft = null;
      ctx.toast?.('Досье сохранено.');
    } catch (error) {
      setError('location-form-error', error);
    }
  });
  byId('object-form').addEventListener('submit', event => {
    event.preventDefault();
    if (!objectDraft) return;
    try {
      let data = ctx.getData();
      const location = data.locations.find(record => record.id === objectDraft.locationId);
      if (!location) throw new Error('Локация больше не существует.');
      const existing = location.objects.find(record => record.id === objectDraft.id);
      if (objectDraft.existing && !existing) throw new Error('Объект больше не существует.');
      const obj = {
        ...existing,
        id: objectDraft.id,
        type: byId('object-type').value,
        name: byId('object-name').value,
        description: byId('object-description').value,
        owner: byId('object-owner').value,
        modifiers: byId('object-type').value === 'building' ? objectDraft.modifiers.map(modifier => ({ ...modifier })) : [],
      };
      if (obj.type === 'resource') obj.amount = byId('object-amount').value;
      const faction = byId('object-faction').value;
      if (faction === '__inherit__') {
        delete obj.faction;
        // The model merges upserts, so deliberately remove an explicit override
        // from the immutable input before that merge. This is still one commit.
        if (existing && Object.hasOwn(existing, 'faction')) {
          data = updateLocation(data, location.id, { objects: location.objects.map(record => {
            if (record.id !== obj.id) return record;
            const inherited = { ...record };
            delete inherited.faction;
            return inherited;
          }) });
        }
      } else obj.faction = faction === '__independent__' ? null : faction;
      ctx.replaceData(upsertObject(data, objectDraft.locationId, obj));
      byId('object-editor').close();
      objectDraft = null;
      ctx.toast?.('Объект сохранён.');
    } catch (error) {
      setError('object-form-error', error);
    }
  });

  byId('object-editor').querySelectorAll('[data-close="object-editor"]').forEach(button => {
    button.addEventListener('click', () => byId('object-editor').close());
  });
  byId('object-editor').addEventListener('close', () => {
    // Native close events are queued; an older event must not erase a reopened form.
    if (!byId('object-editor').open) objectDraft = null;
  });

  function populateParents(id = '') {
    const excluded = new Set(id ? [id] : []);
    const factions = ctx.getData().factions;
    let changed;
    do {
      changed = false;
      factions.forEach(faction => {
        if (excluded.has(faction.parent) && !excluded.has(faction.id)) {
          excluded.add(faction.id);
          changed = true;
        }
      });
    } while (changed);
    const select = byId('house-parent');
    select.replaceChildren(new Option('Суверенный дом / без сюзерена', ''));
    factions.filter(faction => !excluded.has(faction.id)).forEach(faction => select.add(new Option(faction.name, faction.id)));
  }

  function newHouse() {
    byId('house-form').reset();
    byId('house-id').value = '';
    populateParents();
    setError('house-error');
  }

  function editHouse(id) {
    const faction = ctx.getData().factions.find(record => record.id === id);
    if (!faction) { setError('house-error', 'Дом больше не существует.'); return; }
    byId('house-id').value = id;
    byId('house-name').value = faction.name;
    populateParents(id);
    byId('house-parent').value = faction.parent ?? '';
    byId('house-color').value = faction.color;
    byId('house-ruler').value = faction.ruler ?? '';
    byId('house-description').value = faction.description ?? '';
    setError('house-error');
    byId('house-name').focus({ preventScroll: true });
  }

  function renderHouses() {
    const data = ctx.getData();
    const registry = byId('house-registry');
    registry.replaceChildren();
    data.factions.forEach(faction => {
      const row = document.createElement('div');
      row.className = 'house-entry';
      row.dataset.houseId = faction.id;
      const swatch = document.createElement('span');
      swatch.className = 'house-swatch';
      swatch.style.cssText = 'display:inline-block;width:18px;height:18px;flex:none;border:1px solid var(--line)';
      swatch.style.backgroundColor = faction.color;
      swatch.setAttribute('aria-label', `Цвет ${faction.color}`);
      const identity = document.createElement('div');
      const name = document.createElement('strong');
      name.textContent = faction.name;
      const parent = document.createElement('p');
      parent.textContent = faction.parent ? `Вассал: ${data.factions.find(record => record.id === faction.parent)?.name ?? faction.parent}` : 'Суверенная держава';
      const ruler = document.createElement('p');
      ruler.textContent = faction.ruler || 'Правитель не установлен';
      identity.append(name, parent, ruler);
      const edit = document.createElement('button');
      edit.type = 'button';
      edit.className = 'square';
      edit.dataset.houseEdit = faction.id;
      edit.setAttribute('aria-label', `Изменить дом: ${faction.name}`);
      edit.title = edit.getAttribute('aria-label');
      edit.append(svgIcon('quill'));
      edit.addEventListener('click', () => editHouse(faction.id));
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'square';
      remove.dataset.houseDelete = faction.id;
      remove.setAttribute('aria-label', `Удалить дом: ${faction.name}`);
      remove.title = remove.getAttribute('aria-label');
      remove.append(svgIcon('trash'));
      remove.addEventListener('click', () => deleteHouse(faction.id));
      row.append(swatch, identity, edit, remove);
      registry.append(row);
    });
  }

  function openHouses() {
    renderHouses();
    newHouse();
    const heading = byId('houses-editor').querySelector('h2');
    heading.id = 'houses-title';
    showDialog('houses-editor', heading.id);
  }

  async function deleteHouse(id) {
    try {
      const faction = ctx.getData().factions.find(record => record.id === id);
      if (!faction) throw new Error('Дом больше не существует.');
      if (!await ctx.confirm('Удалить дом?', `«${faction.name}» будет удалён, если у него нет назначений и вассалов.`)) return;
      ctx.replaceData(deleteFaction(ctx.getData(), id));
      renderHouses();
      newHouse();
      ctx.toast?.('Дом удалён.');
    } catch (error) {
      const message = `${error.message} Перед удалением переназначьте его локации, объекты и области влияния; смените сюзерена у вассалов.`;
      setError('house-error', message);
      // The parent's confirmation replaces the previous modal. Return the error
      // to the registry instead of leaving it in a closed, inaccessible dialog.
      const heading = byId('houses-editor').querySelector('h2');
      heading.id = 'houses-title';
      if (!byId('houses-editor').open) showDialog('houses-editor', heading.id);
    }
  }

  byId('house-form').addEventListener('submit', event => {
    event.preventDefault();
    try {
      const id = byId('house-id').value || makeId('house');
      const faction = { id, name: byId('house-name').value, parent: byId('house-parent').value || null,
        color: byId('house-color').value, ruler: byId('house-ruler').value, description: byId('house-description').value };
      ctx.replaceData(upsertFaction(ctx.getData(), faction));
      renderHouses();
      newHouse();
      ctx.toast?.('Дом сохранён.');
    } catch (error) {
      setError('house-error', error);
    }
  });

  function renderTerritories() {
    const registry = byId('territory-registry');
    const data = ctx.getData();
    registry.replaceChildren();
    data.territories.forEach(territory => {
      const row = document.createElement('div');
      row.className = 'territory-entry';
      row.dataset.territoryId = territory.id;
      const nameLabel = document.createElement('label');
      nameLabel.textContent = 'Название области';
      const name = document.createElement('input');
      name.value = territory.name;
      name.required = true;
      name.maxLength = 160;
      name.style.minHeight = '44px';
      name.dataset.territoryName = territory.id;
      name.setAttribute('aria-label', `Название области: ${territory.name}`);
      name.addEventListener('change', () => {
        if (!name.reportValidity()) return;
        updateTerritory(territory.id, { name: name.value });
      });
      nameLabel.append(name);
      const ownerLabel = document.createElement('label');
      ownerLabel.textContent = 'Непосредственный владелец';
      const faction = document.createElement('select');
      faction.dataset.territoryOwner = territory.id;
      faction.style.minHeight = '44px';
      faction.setAttribute('aria-label', `Владелец области: ${territory.name}`);
      populateFactions(faction, territory.faction ?? '__independent__');
      faction.addEventListener('change', () => {
        updateTerritory(territory.id, { faction: faction.value === '__independent__' ? null : faction.value });
      });
      ownerLabel.append(faction);
      const redraw = document.createElement('button');
      redraw.type = 'button';
      redraw.className = 'iron-button';
      redraw.dataset.territoryRedraw = territory.id;
      redraw.setAttribute('aria-label', `Перерисовать область: ${territory.name}`);
      redraw.append(svgIcon('quill'), document.createTextNode('Перерисовать'));
      redraw.addEventListener('click', () => {
        const current = ctx.getData().territories.find(record => record.id === territory.id);
        if (!current) { setError('territory-error', 'Область больше не существует.'); return; }
        beginTerritory(current, true);
      });
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'square';
      remove.dataset.territoryDelete = territory.id;
      remove.setAttribute('aria-label', `Удалить область: ${territory.name}`);
      remove.title = remove.getAttribute('aria-label');
      remove.append(svgIcon('trash'));
      remove.addEventListener('click', () => deleteTerritory(territory.id));
      row.append(nameLabel, ownerLabel, redraw, remove);
      registry.append(row);
    });
  }

  function updateTerritory(id, patch) {
    try {
      const data = ctx.getData();
      const territory = data.territories.find(record => record.id === id);
      if (!territory) throw new Error('Область больше не существует.');
      ctx.replaceData(upsertTerritory(data, { ...territory, ...patch }));
      setError('territory-error');
      ctx.toast?.('Область обновлена.');
    } catch (error) {
      setError('territory-error', error);
    }
  }

  async function deleteTerritory(id) {
    try {
      const territory = ctx.getData().territories.find(record => record.id === id);
      if (!territory) throw new Error('Область больше не существует.');
      if (!await ctx.confirm('Удалить область?', `«${territory.name}» будет удалена. Локации и их владельцы не изменятся.`)) return;
      ctx.replaceData(removeTerritory(ctx.getData(), id));
      renderTerritories();
      setError('territory-error');
      ctx.toast?.('Область удалена.');
    } catch (error) {
      setError('territory-error', error);
      ctx.toast?.(error.message);
    }
  }

  function openTerritories() {
    renderTerritories();
    byId('territory-form').reset();
    populateFactions(byId('territory-faction'), ctx.getData().factions[0]?.id ?? '__independent__');
    setError('territory-error');
    const heading = byId('territory-editor').querySelector('h2');
    heading.id = 'territories-title';
    showDialog('territory-editor', heading.id);
  }

  function renderDrawing() {
    const layer = byId('drawing-layer');
    layer.replaceChildren();
    if (mapTask?.kind !== 'territory') return;
    const points = mapTask.points;
    const color = ctx.getData().factions.find(record => record.id === mapTask.territory.faction)?.color ?? '#c2a575';
    const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    polyline.setAttribute('points', points.map(point => point.join(',')).join(' '));
    polyline.setAttribute('fill', 'none');
    polyline.setAttribute('stroke', color);
    polyline.setAttribute('stroke-width', '3');
    polyline.setAttribute('vector-effect', 'non-scaling-stroke');
    layer.append(polyline);
    points.forEach(point => {
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', point[0]);
      circle.setAttribute('cy', point[1]);
      circle.setAttribute('r', '9');
      circle.setAttribute('fill', color);
      circle.setAttribute('stroke', '#15181a');
      circle.setAttribute('stroke-width', '2');
      circle.setAttribute('vector-effect', 'non-scaling-stroke');
      layer.append(circle);
    });
    byId('territory-undo').disabled = !points.length;
    byId('map-task-text').textContent = `«${mapTask.territory.name}»: ${points.length} вершин. Нажмите на карту; «Завершить» замкнёт область. Esc — отмена.`;
  }

  function beginTerritory(territory, replacing = false) {
    cancelMapTask();
    const ui = getUI();
    if (!ui?.setMapInteraction) { setError('territory-error', 'Карта ещё не готова.'); return; }
    document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
    mapTask = { kind: 'territory', territory: { ...territory }, points: [], replacing };
    byId('map-task').hidden = false;
    byId('territory-actions').hidden = false;
    ui.setMapInteraction((point, event) => {
      if (mapTask?.kind !== 'territory' || !validPoint(point)) return;
      if (event?.altKey || event?.metaKey) return;
      if (event?.type === 'dblclick') { finishTerritory(); return; }
      const picked = point.map(Math.round);
      const last = mapTask.points.at(-1);
      // Pointer-up is emitted twice by a double-click; keep one vertex only.
      if (last && last[0] === picked[0] && last[1] === picked[1]) return;
      mapTask.points = [...mapTask.points, picked];
      renderDrawing();
    });
    renderDrawing();
    byId('viewport').focus({ preventScroll: true });
  }

  function finishTerritory() {
    if (mapTask?.kind !== 'territory') return;
    try {
      const first = mapTask.points[0], last = mapTask.points.at(-1);
      // A clicked closing vertex is implied by SVG polygon and the model.
      const points = mapTask.points.length > 3 && first[0] === last[0] && first[1] === last[1] ?
        mapTask.points.slice(0, -1) : mapTask.points;
      validatePolygon(points);
      const data = ctx.getData();
      const existing = data.territories.find(record => record.id === mapTask.territory.id);
      if (mapTask.replacing && !existing) throw new Error('Область больше не существует. Отмените действие и откройте реестр заново.');
      ctx.replaceData(upsertTerritory(data, { ...(existing ?? mapTask.territory), points: points.map(point => [...point]) }));
      cancelMapTask();
      ctx.toast?.('Область влияния сохранена. Локации не изменены.');
    } catch (error) {
      byId('map-task-text').textContent = `${error.message}. Уберите последнюю точку или продолжите рисование. Esc — отмена.`;
      ctx.toast?.(error.message);
    }
  }

  byId('territory-form').addEventListener('submit', event => {
    event.preventDefault();
    const faction = byId('territory-faction').value;
    beginTerritory({ id: makeId('territory'), name: byId('territory-name').value,
      faction: faction === '__independent__' ? null : faction });
  });
  byId('territory-undo').addEventListener('click', () => {
    if (mapTask?.kind !== 'territory') return;
    mapTask.points = mapTask.points.slice(0, -1);
    renderDrawing();
  });
  byId('territory-finish').addEventListener('click', finishTerritory);
  byId('viewport').addEventListener('dblclick', event => {
    if (mapTask?.kind !== 'territory' || event.altKey || event.metaKey) return;
    event.preventDefault();
    event.stopPropagation();
    finishTerritory();
  });

  async function parentAction(button, callback) {
    if (button?.disabled) return;
    if (button) button.disabled = true;
    setError('editor-error');
    try {
      if (typeof callback !== 'function') throw new Error('Действие пока недоступно.');
      await callback();
    } catch (error) {
      if (!byId('editor').open) open();
      setError('editor-error', error);
      ctx.toast?.(error.message);
    } finally {
      if (button) button.disabled = false;
    }
  }

  byId('export-site').addEventListener('click', event => parentAction(event.currentTarget, ctx.onExportSite));
  byId('export-json').addEventListener('click', event => parentAction(event.currentTarget, ctx.onExportJson));
  byId('draft-reset').addEventListener('click', event => parentAction(event.currentTarget, ctx.onReset));
  byId('import-json').addEventListener('change', async event => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    input.disabled = true;
    try {
      await parentAction(null, () => ctx.onImport(file));
    } finally {
      input.value = '';
      input.disabled = false;
    }
  });

  byId('house-new').addEventListener('click', newHouse);

  byId('location-create').addEventListener('click', createLocation);
  byId('location-edit').addEventListener('click', () => editLocation(ctx.getSelectedId()));
  byId('object-create').addEventListener('click', () => addObject(ctx.getSelectedId()));
  byId('houses-open').addEventListener('click', openHouses);
  byId('territories-open').addEventListener('click', openTerritories);
  byId('location-move').addEventListener('click', moveLocation);
  byId('location-delete').addEventListener('click', deleteLocation);
  byId('map-task-cancel').addEventListener('click', cancelMapTask);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && mapTask) {
      event.preventDefault();
      cancelMapTask();
    }
  });

  ['editor', 'location-editor', 'houses-editor', 'territory-editor'].forEach(id => {
    byId(id).querySelectorAll(`[data-close="${id}"]`).forEach(button => {
      button.addEventListener('click', () => byId(id).close());
    });
  });
  byId('location-editor').addEventListener('close', () => {
    if (!byId('location-editor').open) locationDraft = null;
  });

  return { open, editLocation, addObject, editObject, deleteObject, openHouses, openTerritories, refresh };
}
