import { sovereignOf, factionMembers, effectiveFaction } from './model.mjs';

const SVG_NS = 'http://www.w3.org/2000/svg';
const FAVORITES_KEY = 'gilneas-atlas-favorites-v1';
const MOBILE_QUERY = '(max-width:760px),(max-width:1050px) and (max-height:540px)';
const HOME_BOUNDS = { x: 800, y: 2450, width: 2000, height: 1800 };
const TYPE_NAMES = Object.freeze({ city: 'Город', settlement: 'Поселение', estate: 'Поместье', fortress: 'Крепость', district: 'Квартал', harbor: 'Гавань', forest: 'Лес', mine: 'Шахта', landmark: 'Ориентир', building: 'Здание', resource: 'Ресурс' });
const glyphs = Object.freeze({
  crown: 'M3 7 7 11 12 4 17 11 21 7 19 18H5Z M6 21H18',
  city: 'M3 21V12H8V7H15V12H21V21Z M10 21V16H14V21 M10 10H12 M17 15H18 M5 15H6',
  fortress: 'M3 21V7H6V10H9V7H15V10H18V7H21V21Z M10 21V16H14V21',
  tower: 'M7 21V9L5 7V3H9V5H15V3H19V7L17 9V21Z M10 21V16H14V21 M10 10H14',
  forest: 'M12 2 5 11H8L3 17H10V22H14V17H21L16 11H19Z',
  harbor: 'M12 4V19 M7 8H17 M4 14C4 22 20 22 20 14 M2 15 4 13 6 15 M18 15 20 13 22 15 M10 3A2 2 0 1 0 14 3A2 2 0 1 0 10 3',
  mine: 'M3 21 9 5 15 3 21 21Z M7 21V14L12 10 17 14V21 M10 21V16H14V21',
  building: 'M3 10 12 3 21 10 M5 9V21H19V9 M10 21V15H14V21 M8 12H9 M15 12H16',
  resource: 'M12 2 21 8 18 20 6 20 3 8Z M3 8H21 M8 8 12 20 16 8 M8 8 12 2 16 8',
  shield: 'M4 3H20V12C20 17 16 20 12 22 8 20 4 17 4 12Z M8 8H16 M12 5V17',
  rose: 'M12 6C6 0 2 7 6 11 0 15 6 23 12 18 18 23 24 15 18 11 22 7 18 0 12 6Z M8 12A4 4 0 1 0 16 12A4 4 0 1 0 8 12 M12 10V14 M10 12H14',
  star: 'M12 2 15 9 22 10 17 15 18 22 12 18 6 22 7 15 2 10 9 9Z',
  quill: 'M3 21 7 17 M6 18 8 10 19 2 22 5 14 16Z M8 16 18 6',
  trash: 'M3 6H21 M8 6V3H16V6 M5 6 6 21H18L19 6 M10 10V17 M14 10V17',
  chevron: 'M5 9 12 16 19 9',
});

function make(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text != null) element.textContent = String(text);
  return element;
}

function icon(name, className = '') {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  if (className) svg.setAttribute('class', className);
  const path = document.createElementNS(SVG_NS, 'path');
  path.setAttribute('d', glyphs[name] || glyphs.shield);
  svg.append(path);
  return svg;
}

function locationGlyph(location) {
  if (location.capital) return 'crown';
  return { city: 'city', fortress: 'fortress', estate: 'tower', forest: 'forest', harbor: 'harbor', mine: 'mine', settlement: 'building', district: 'city' }[location.type] || 'shield';
}

const casefold = value => String(value ?? '').normalize('NFKC').toLocaleLowerCase('ru');
const colorOf = faction => /^#[0-9a-f]{6}$/i.test(faction?.color || '') ? faction.color : '#b39467';

/** Wire the static atlas DOM. Data and editing remain with the parent. */
export function initUI(context) {
  const dom = Object.fromEntries(Array.from(document.querySelectorAll('[id]'), node => [node.id, node]));
  const body = document.body;
  const viewport = dom.viewport;
  const world = dom.world;
  const mobileMedia = window.matchMedia(MOBILE_QUERY);
  let mobile = mobileMedia.matches;
  let initialized = false;
  let selectedFaction = null;
  let tab = 'all';
  let mapInteraction = null;
  const groupOpen = new Map();
  let groupsFolded = false;
  let lastSelectedId = null;
  let lastDossierId = null;
  let drag = null;
  const pointers = new Map();
  let pinch = null;
  let suppressMapClick = false;
  let flightFrame = 0;
  let flightGeneration = 0;
  let camera = { x: 0, y: 0, scale: 1 };
  const panels = { navigation: !mobile, layers: !mobile, dossier: false };
  const favorites = new Set();
  try {
    const saved = JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]');
    if (Array.isArray(saved)) saved.filter(id => typeof id === 'string').forEach(id => favorites.add(id));
  } catch { /* Favorites are optional, including in storage-restricted browsers. */ }

  const data = () => context.getData();
  const selected = () => data().locations.find(location => location.id === context.getSelectedId());
  const factionMap = () => new Map(data().factions.map(faction => [faction.id, faction]));
  const includedFactions = () => selectedFaction == null ? null : new Set(factionMembers(data().factions, selectedFaction));
  const viewRect = () => viewport.getBoundingClientRect();

  function availableRect() {
    const rect = viewRect();
    let left = 24, top = 24, right = rect.width - 24, bottom = rect.height - 24;
    for (const name of ['navigation', 'layers', 'dossier']) {
      const panel = dom[name];
      if (panel.hidden) continue;
      const box = panel.getBoundingClientRect();
      if (mobile && box.width > rect.width * 0.7) bottom = Math.min(bottom, box.top - rect.top - 20);
      else if (name === 'navigation') left = Math.max(left, box.right - rect.left + 24);
      else right = Math.min(right, box.left - rect.left - 24);
    }
    if (right - left < 120) { left = 24; right = rect.width - 24; }
    if (bottom - top < 90) { top = 12; bottom = Math.max(102, rect.height * 0.35); }
    return { x: left, y: top, width: Math.max(1, right - left), height: Math.max(1, bottom - top) };
  }

  function constrained(next) {
    const rect = viewRect();
    const meta = data().meta;
    const minimum = Math.min(rect.width / meta.width, rect.height / meta.height) * 0.55;
    const scale = Math.min(4, Math.max(minimum, next.scale));
    const marginX = Math.max(160, rect.width * 0.35);
    const marginY = Math.max(160, rect.height * 0.35);
    const minX = rect.width - meta.width * scale - marginX;
    const minY = rect.height - meta.height * scale - marginY;
    return { x: Math.min(marginX, Math.max(minX, next.x)), y: Math.min(marginY, Math.max(minY, next.y)), scale };
  }

  function applyCamera(next) {
    camera = constrained(next);
    world.style.transform = `translate(${camera.x}px, ${camera.y}px) scale(${camera.scale})`;
    world.style.setProperty('--inverse-scale', String(1 / camera.scale));
    dom['zoom-status'].textContent = `${Math.round(camera.scale * 100)}%`;
  }

  function cancelFlight() {
    flightGeneration += 1;
    if (flightFrame) cancelAnimationFrame(flightFrame);
    flightFrame = 0;
  }

  function flyTo(next, animate = true) {
    cancelFlight();
    const target = constrained(next);
    if (!animate || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { applyCamera(target); return; }
    const start = { ...camera };
    const generation = flightGeneration;
    let started = null;
    const tick = timestamp => {
      if (generation !== flightGeneration) return;
      started ??= timestamp;
      const elapsed = Math.min(1, (timestamp - started) / 430);
      const eased = 1 - (1 - elapsed) ** 3;
      applyCamera({ x: start.x + (target.x - start.x) * eased, y: start.y + (target.y - start.y) * eased,
        scale: start.scale * (target.scale / start.scale) ** eased });
      if (elapsed < 1) flightFrame = requestAnimationFrame(tick);
      else { flightFrame = 0; applyCamera(target); }
    };
    flightFrame = requestAnimationFrame(tick);
  }

  function frame(bounds, animate) {
    const area = availableRect();
    const scale = Math.min(area.width / bounds.width, area.height / bounds.height) * 0.94;
    flyTo({ x: area.x + area.width / 2 - (bounds.x + bounds.width / 2) * scale,
      y: area.y + area.height / 2 - (bounds.y + bounds.height / 2) * scale, scale }, animate);
  }

  function home(animate = true) { frame(HOME_BOUNDS, animate); }
  function fit(animate = true) { frame({ x: 0, y: 0, width: data().meta.width, height: data().meta.height }, animate); }
  function zoom(factor) {
    if (!Number.isFinite(factor) || factor <= 0) return;
    cancelFlight();
    const area = availableRect();
    const x = area.x + area.width / 2, y = area.y + area.height / 2;
    const scale = constrained({ ...camera, scale: camera.scale * factor }).scale;
    applyCamera({ x: x - (x - camera.x) * scale / camera.scale,
      y: y - (y - camera.y) * scale / camera.scale, scale });
  }
  function focusLocation(id, animate = true) {
    const location = data().locations.find(item => item.id === id);
    if (!location) return;
    const area = availableRect();
    const scale = Math.max(camera.scale, 0.65);
    flyTo({ x: area.x + area.width / 2 - location.x * scale,
      y: area.y + area.height / 2 - location.y * scale, scale }, animate);
  }
  function toMap(clientX, clientY) {
    const rect = viewRect();
    return [(clientX - rect.left - camera.x) / camera.scale, (clientY - rect.top - camera.y) / camera.scale];
  }
  function getCamera() { return { ...camera }; }
  function refreshViewport() {
    cancelFlight();
    document.documentElement.style.setProperty('--app-height', `${window.visualViewport?.height || window.innerHeight}px`);
    applyCamera(camera);
  }

  function syncPanels() {
    dom.navigation.hidden = !panels.navigation;
    dom.layers.hidden = !panels.layers || panels.dossier;
    dom.dossier.hidden = !panels.dossier || !selected();
    body.classList.toggle('nav-hidden', dom.navigation.hidden);
    body.classList.toggle('layers-hidden', dom.layers.hidden);
    body.classList.toggle('dossier-open', !dom.dossier.hidden);
    dom['nav-open'].hidden = mobile || !dom.navigation.hidden;
    for (const name of ['navigation', 'layers', 'dossier']) {
      body.classList.toggle(`mobile-panel-${name}`, mobile && !dom[name].hidden);
      dom[name].setAttribute('aria-hidden', String(dom[name].hidden));
      const button = dom[name === 'navigation' ? 'mobile-nav' : `mobile-${name}`];
      button.classList.toggle('active', !dom[name].hidden);
      button.setAttribute('aria-pressed', String(!dom[name].hidden));
    }
  }
  function setPanel(name, open) {
    if (!Object.hasOwn(panels, name)) return;
    if (name === 'dossier' && !selected()) open = false;
    if (mobile && open) for (const key of Object.keys(panels)) panels[key] = false;
    panels[name] = Boolean(open);
    syncPanels();
  }
  function setMapInteraction(callback) {
    mapInteraction = typeof callback === 'function' ? callback : null;
    body.classList.toggle('map-editing', Boolean(mapInteraction));
  }

  function selectLocation(id) {
    context.onSelect(id);
    setPanel('dossier', true);
    focusLocation(id);
  }

  viewport.style.touchAction = 'none';
  for (const type of ['dragstart', 'selectstart']) viewport.addEventListener(type, event => event.preventDefault());
  viewport.addEventListener('wheel', event => {
    event.preventDefault();
    cancelFlight();
    const rect = viewRect();
    const x = event.clientX - rect.left, y = event.clientY - rect.top;
    const units = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? rect.height : 1;
    const factor = Math.exp(-Math.max(-1200, Math.min(1200, event.deltaY * units)) * 0.002);
    const scale = constrained({ ...camera, scale: camera.scale * factor }).scale;
    applyCamera({ x: x - (x - camera.x) * scale / camera.scale,
      y: y - (y - camera.y) * scale / camera.scale, scale });
  }, { passive: false });
  function pinchGeometry() {
    const [first, second] = [...pointers.values()];
    return { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2,
      distance: Math.max(1, Math.hypot(first.x - second.x, first.y - second.y)) };
  }
  function beginPinch() {
    const geometry = pinchGeometry();
    pinch = { ...geometry, anchor: toMap(geometry.x, geometry.y), scale: camera.scale };
    suppressMapClick = true;
    if (drag) drag.moved = true;
  }
  viewport.addEventListener('pointerdown', event => {
    if (event.button !== 0 || pointers.has(event.pointerId)) return;
    cancelFlight();
    if (!pointers.size) suppressMapClick = false;
    const capture = event.target.closest('.map-marker') || viewport;
    capture.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY, capture });
    if (pointers.size === 1) {
      drag = { id: event.pointerId, x: event.clientX, y: event.clientY, camera: { ...camera }, moved: false,
        canPan: !mapInteraction || event.altKey || event.metaKey };
    } else beginPinch();
    event.preventDefault();
  });
  viewport.addEventListener('pointermove', event => {
    const pointer = pointers.get(event.pointerId);
    if (!pointer) return;
    pointer.x = event.clientX;
    pointer.y = event.clientY;
    if (pointers.size >= 2 && pinch) {
      const geometry = pinchGeometry();
      const rect = viewRect();
      const scale = constrained({ ...camera, scale: pinch.scale * geometry.distance / pinch.distance }).scale;
      applyCamera({ x: geometry.x - rect.left - pinch.anchor[0] * scale,
        y: geometry.y - rect.top - pinch.anchor[1] * scale, scale });
      viewport.classList.add('dragging');
      suppressMapClick = true;
    } else if (drag && drag.id === event.pointerId) {
      const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
      drag.moved ||= Math.hypot(dx, dy) > 4;
      if (drag.moved && (drag.canPan || event.altKey || event.metaKey)) {
        viewport.classList.add('dragging');
        applyCamera({ ...drag.camera, x: drag.camera.x + dx, y: drag.camera.y + dy });
      }
    }
    event.preventDefault();
  });
  const endDrag = event => {
    const pointer = pointers.get(event.pointerId);
    if (!pointer) return;
    suppressMapClick ||= Boolean(pinch || drag?.moved || event.type === 'pointercancel');
    pointers.delete(event.pointerId);
    if (pointer.capture.hasPointerCapture(event.pointerId)) pointer.capture.releasePointerCapture(event.pointerId);
    pinch = null;
    if (pointers.size >= 2) beginPinch();
    else if (pointers.size === 1) {
      const [id, remaining] = [...pointers.entries()][0];
      drag = { id, x: remaining.x, y: remaining.y, camera: { ...camera }, moved: true,
        canPan: !mapInteraction || event.altKey || event.metaKey };
    } else {
      drag = null;
      viewport.classList.remove('dragging');
    }
  };
  viewport.addEventListener('pointerup', endDrag);
  viewport.addEventListener('pointercancel', endDrag);
  viewport.addEventListener('click', event => {
    if (suppressMapClick) { event.preventDefault(); event.stopImmediatePropagation(); }
    else if (mapInteraction) {
      event.preventDefault();
      event.stopImmediatePropagation();
      mapInteraction(toMap(event.clientX, event.clientY), event);
    }
  }, true);
  viewport.addEventListener('dblclick', event => {
    if (!mapInteraction || suppressMapClick || event.altKey || event.metaKey) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    mapInteraction(toMap(event.clientX, event.clientY), event);
  }, true);

  function renderNavigation() {
    const snapshot = data();
    const factions = factionMap();
    const query = casefold(dom.search.value).trim();
    for (const [id, name] of [['filter-all', 'all'], ['filter-favorites', 'favorites'], ['filter-nobles', 'nobles']]) {
      dom[id].classList.toggle('active', tab === name);
      dom[id].setAttribute('aria-pressed', String(tab === name));
    }
    if (tab === 'nobles') {
      const nobles = (snapshot.nobles || []).filter(noble => !query || casefold([noble.name, noble.title, noble.house, noble.owner].join(' ')).includes(query));
      dom['location-list'].replaceChildren(...nobles.map(noble => {
        const row = make('button', 'noble-row');
        row.type = 'button';
        row.dataset.nobleId = noble.id;
        const label = make('span');
        label.append(make('span', '', noble.name), make('small', '', [noble.title, noble.house].filter(Boolean).join(' · ')));
        row.append(icon('shield'), label);
        row.addEventListener('click', () => context.onShowNoble?.(noble.id));
        return row;
      }));
      dom['result-count'].textContent = `${nobles.length} ${nobles.length === 1 ? 'персона' : nobles.length >= 2 && nobles.length <= 4 ? 'персоны' : 'персон'}`;
      dom['fold-groups'].hidden = true;
      return;
    }
    dom['fold-groups'].hidden = false;
    const included = includedFactions();
    const rows = snapshot.locations.filter(location => (!included || included.has(location.faction)) && (tab !== 'favorites' || favorites.has(location.id)) &&
      (!query || casefold([location.name, location.owner, location.house, location.englishName, ...(location.aliases || []), factions.get(location.faction)?.name].join(' ')).includes(query)));
    const groups = new Map();
    rows.forEach(location => {
      if (!groups.has(location.faction)) groups.set(location.faction, []);
      groups.get(location.faction).push(location);
    });
    const fragment = document.createDocumentFragment();
    for (const [id, locations] of groups) {
      const faction = factions.get(id);
      const group = make('details', 'group');
      group.open = query ? true : groupOpen.get(id) ?? !groupsFolded;
      group.addEventListener('toggle', () => { if (group.isConnected && !dom.search.value.trim()) groupOpen.set(id, group.open); });
      if (id != null) group.dataset.factionId = id;
      group.style.setProperty('--faction-color', colorOf(faction));
      const summary = make('summary');
      summary.append(make('span', 'group-name', faction?.name || 'Без державы'), make('span', 'group-count', locations.length), icon('chevron', 'chevron'));
      group.append(summary);
      locations.sort((a, b) => Number(Boolean(b.capital)) - Number(Boolean(a.capital)) || a.name.localeCompare(b.name, 'ru'));
      for (const location of locations) {
        const row = make('button', 'location-row');
        row.type = 'button';
        row.dataset.locationId = location.id;
        row.classList.toggle('active', location.id === context.getSelectedId());
        row.append(make('span', 'row-name', location.name), make('small', 'location-type', TYPE_NAMES[location.type] || location.type));
        if (location.capital) { const crown = make('span', 'row-capital'); crown.append(icon('crown')); row.append(crown); }
        if (favorites.has(location.id)) row.append(icon('star', 'row-favorite'));
        row.addEventListener('click', () => selectLocation(location.id));
        group.append(row);
      }
      fragment.append(group);
    }
    dom['location-list'].replaceChildren(fragment);
    dom['result-count'].textContent = `${rows.length} ${rows.length === 1 ? 'владение' : rows.length >= 2 && rows.length <= 4 ? 'владения' : 'владений'}`;
  }

  function renderMarkers() {
    const factions = factionMap();
    const included = includedFactions();
    const fragment = document.createDocumentFragment();
    for (const location of data().locations) {
      const marker = make('button', 'map-marker');
      marker.type = 'button';
      marker.dataset.locationId = location.id;
      marker.title = location.name;
      marker.setAttribute('aria-label', location.name);
      marker.style.left = `${location.x}px`;
      marker.style.top = `${location.y}px`;
      marker.style.setProperty('--marker-color', colorOf(factions.get(location.faction)));
      marker.classList.toggle('capital', Boolean(location.capital));
      marker.classList.toggle('selected', location.id === context.getSelectedId());
      marker.classList.toggle('reconstruction', location.provenance?.confidence === 'reconstruction');
      marker.classList.toggle('dimmed', Boolean(included && !included.has(location.faction) && location.id !== context.getSelectedId()));
      marker.hidden = !dom['show-reconstructions'].checked && location.provenance?.confidence === 'reconstruction' && location.id !== context.getSelectedId();
      marker.append(icon(locationGlyph(location)), make('span', 'marker-label', location.name));
      marker.addEventListener('click', () => selectLocation(location.id));
      fragment.append(marker);
    }
    dom.markers.replaceChildren(fragment);
  }

  function renderLayers() {
    const snapshot = data();
    const factions = factionMap();
    const included = includedFactions();
    const ordered = [];
    const visit = (parent, depth) => {
      for (const faction of snapshot.factions.filter(item => (item.parent ?? null) === parent)) {
        ordered.push([faction, depth]);
        visit(faction.id, depth + 1);
      }
    };
    visit(null, 0);
    dom['faction-list'].replaceChildren(...ordered.map(([faction, depth]) => {
      const row = make('button', `faction-row${depth ? ' vassal' : ''}`);
      row.type = 'button';
      row.dataset.factionId = faction.id;
      row.style.setProperty('--faction-color', colorOf(faction));
      row.classList.toggle('active', selectedFaction === faction.id);
      row.setAttribute('aria-pressed', String(selectedFaction === faction.id));
      const name = make('span', 'faction-name', faction.name);
      row.append(make('i'), name);
      if (depth) {
        const parent = factions.get(faction.parent);
        const badge = make('small', 'faction-parent', parent?.name);
        badge.style.display = 'inline';
        badge.title = `Сюзерен: ${parent?.name || ''}`;
        row.append(badge);
      }
      row.addEventListener('click', () => { selectedFaction = selectedFaction === faction.id ? null : faction.id; render(); });
      return row;
    }));
    dom['faction-clear'].hidden = selectedFaction == null;
    const territories = document.createDocumentFragment();
    for (const territory of snapshot.territories || []) {
      const polygon = document.createElementNS(SVG_NS, 'polygon');
      polygon.dataset.territoryId = territory.id;
      polygon.setAttribute('points', territory.points.map(point => point.join(',')).join(' '));
      polygon.setAttribute('fill', colorOf(factions.get(territory.faction)));
      polygon.setAttribute('stroke', colorOf(factions.get(territory.faction)));
      polygon.setAttribute('fill-opacity', '0.15');
      polygon.setAttribute('stroke-opacity', '0.55');
      polygon.setAttribute('opacity', included && !included.has(territory.faction) ? '0.12' : '1');
      territories.append(polygon);
    }
    dom['territory-layer'].replaceChildren(territories);
    dom['territory-layer'].toggleAttribute('hidden', !dom['show-territories'].checked);
    world.classList.toggle('show-labels', dom['show-labels'].checked);
  }

  function citationIds(record) {
    return [...new Set([...(record?.provenance?.sources || []), ...(record?.sources || [])])];
  }

  function safeUrl(source) {
    for (const value of [source?.url, source?.canonicalUrl]) {
      if (typeof value !== 'string' || !/^https?:\/\//i.test(value)) continue;
      try {
        const url = new URL(value);
        if (url.protocol === 'http:' || url.protocol === 'https:') return value;
      } catch { /* Untrusted source URLs stay plain text. */ }
    }
    return null;
  }

  function sourceLink(source, label) {
    const url = safeUrl(source);
    const node = make(url ? 'a' : 'span', 'source-citation', label);
    node.dataset.sourceId = String(source.id);
    if (url) {
      node.setAttribute('href', url);
      node.target = '_blank';
      node.rel = 'noopener noreferrer';
      node.title = String(source.title || url);
    }
    return node;
  }

  function appendCitations(target, record, sources) {
    for (const id of citationIds(record)) {
      const source = sources.get(id);
      if (!source) continue;
      target.append(document.createTextNode(' '), sourceLink(source.record, `[${source.number}]`));
    }
  }

  function renderDossier() {
    const location = selected();
    if (!location) { syncPanels(); return; }
    const factions = factionMap();
    const faction = factions.get(location.faction);
    const sovereign = faction ? factions.get(sovereignOf(data().factions, faction.id)) : null;
    const sameLocation = lastDossierId === location.id;
    const openObjects = new Set([...dom['dossier-objects'].querySelectorAll('details[open]')].map(node => node.dataset.objectId));
    const allSources = new Map((data().sources || []).map(source => [source.id, source]));
    const cited = new Map();
    for (const record of [location, ...(location.objects || [])]) {
      for (const id of citationIds(record)) if (allSources.has(id) && !cited.has(id)) cited.set(id, { record: allSources.get(id), number: typeof id === 'number' ? id : data().sources.findIndex(source => source.id === id) + 1 });
    }
    dom['dossier-type'].textContent = TYPE_NAMES[location.type] || 'Досье владения';
    dom['dossier-title'].textContent = location.name;
    const fields = [TYPE_NAMES[location.type] || location.type, location.capital ? 'Столица' : '', location.subtitle];
    dom['dossier-subtitle'].textContent = [...new Set(fields.filter(Boolean))].join(' · ');
    const unknownAffiliation = location.provenance?.affiliationStatus === 'unknown' || (location.faction == null && location.provenance?.confidence === 'reconstruction');
    dom['dossier-faction'].textContent = faction?.name || (unknownAffiliation ? 'Принадлежность не установлена' : 'Без державы');
    dom['dossier-sovereign'].textContent = sovereign?.name || (unknownAffiliation ? 'Не установлено' : 'Независимое владение');
    dom['dossier-owner'].textContent = location.owner || 'Не установлен';
    dom['dossier-favorite'].setAttribute('aria-pressed', String(favorites.has(location.id)));
    dom['dossier-favorite'].setAttribute('aria-label', favorites.has(location.id) ? 'Убрать из избранного' : 'В избранное');
    dom['dossier-description'].textContent = location.description || '';
    dom['dossier-description'].style.whiteSpace = 'pre-wrap';
    dom['dossier-seal'].replaceChildren(icon(faction?.id === 'gilneas' || sovereign?.id === 'gilneas' ? 'rose' : 'shield'));
    dom['dossier-seal'].setAttribute('aria-hidden', 'true');
    const provenance = dom['dossier-provenance'];
    provenance.replaceChildren();
    const confidence = location.provenance?.confidence || location.confidence;
    const status = { confirmed: 'Подтверждённая локация', reconstruction: 'Реконструкция для эпохи', custom: 'Авторская локация' }[confidence];
    if (status) provenance.append(make('span', 'confidence', status));
    if (location.provenance?.note) provenance.append(make('p', '', location.provenance.note));
    appendCitations(provenance, location, cited);
    provenance.hidden = !provenance.childNodes.length;

    dom['dossier-objects'].replaceChildren(...(location.objects || []).map(object => {
      const card = make('details', 'object-card');
      card.dataset.objectId = object.id;
      card.open = sameLocation && openObjects.has(object.id);
      const summary = make('summary');
      const symbol = make('span', 'object-icon');
      symbol.append(icon(object.type === 'building' ? 'building' : object.type === 'resource' ? 'resource' : 'shield'));
      summary.append(symbol, make('span', 'object-title', object.name), icon('chevron', 'chevron'));
      card.append(summary);
      const objectFaction = factions.get(effectiveFaction(location, object));
      const owner = object.owner || location.owner;
      card.append(make('small', 'object-ownership', `${objectFaction?.name || 'Независимый объект'} · ${owner || 'Владелец не установлен'}`));
      if (object.description) card.append(make('p', 'object-description', object.description));
      if (object.type === 'resource' && object.amount != null && String(object.amount).length) card.append(make('p', 'amount', `Запас: ${object.amount}`));
      if (object.modifiers?.length) {
        const modifiers = make('ul', 'modifiers');
        for (const modifier of object.modifiers) {
          const item = make('li', `modifier ${modifier.kind === 'penalty' ? 'penalty' : 'bonus'}`, modifier.text);
          item.dataset.modifierId = modifier.id;
          modifiers.append(item);
        }
        card.append(modifiers);
      }
      const citations = make('small', 'object-sources');
      appendCitations(citations, object, cited);
      if (citations.childNodes.length) card.append(citations);
      const actions = make('div', 'object-actions');
      for (const [kind, label, glyph, callback] of [['edit', 'Редактировать', 'quill', context.onEditObject], ['delete', 'Удалить', 'trash', context.onDeleteObject]]) {
        const button = make('button', '', label);
        button.type = 'button';
        button.dataset[kind === 'edit' ? 'objectEdit' : 'objectDelete'] = object.id;
        button.title = `${label} объект: ${object.name}`;
        button.setAttribute('aria-label', button.title);
        button.prepend(icon(glyph));
        button.addEventListener('click', () => callback?.(location.id, object.id));
        actions.append(button);
      }
      card.append(actions);
      return card;
    }));
    if (!location.objects?.length) dom['dossier-objects'].append(make('p', 'empty-objects', 'Объекты не добавлены.'));
    dom['dossier-source-list'].replaceChildren(...[...cited.values()].map(({ record, number }) => {
      const entry = make('div', 'source-entry');
      entry.append(sourceLink(record, `[${number}] ${record.title || record.url || 'Источник'}`));
      if (record.quote) entry.append(make('blockquote', '', record.quote));
      return entry;
    }));
    dom['dossier-sources'].hidden = cited.size === 0;
    if (!sameLocation) {
      dom.dossier.scrollTop = 0;
      dom.dossier.classList.remove('folded');
      dom['dossier-body'].hidden = false;
      dom['dossier-fold'].setAttribute('aria-expanded', 'true');
      dom['dossier-sources'].open = false;
    }
    lastDossierId = location.id;
    syncPanels();
  }

  function render() {
    if (selectedFaction != null && !data().factions.some(faction => faction.id === selectedFaction)) selectedFaction = null;
    const meta = data().meta;
    const id = selected()?.id ?? null;
    if (id !== lastSelectedId) {
      lastSelectedId = id;
      if (id != null) setPanel('dossier', true);
      else { panels.dossier = false; syncPanels(); }
    }
    dom['mobile-dossier'].disabled = id == null;
    dom['selection-status'].textContent = selected()?.name || 'Выберите владение на карте';
    world.style.width = `${meta.width}px`;
    world.style.height = `${meta.height}px`;
    for (const [id, src] of [['base-map', meta.image], ['mist-map', meta.mist || 'assets/maps/inactive-mist.webp']]) {
      if (src && dom[id].getAttribute('src') !== src) dom[id].setAttribute('src', src);
      dom[id].width = meta.width;
      dom[id].height = meta.height;
    }
    for (const id of ['territory-layer', 'drawing-layer']) dom[id].setAttribute('viewBox', `0 0 ${meta.width} ${meta.height}`);
    dom['region-labels'].replaceChildren(...(meta.labels || []).map(label => {
      const node = make('span', 'region-label', label.text);
      node.style.left = `${label.x}px`;
      node.style.top = `${label.y}px`;
      if (Number.isFinite(label.size)) node.style.fontSize = `${label.size}px`;
      return node;
    }));
    renderNavigation();
    renderMarkers();
    renderLayers();
    renderDossier();
    if (!initialized) { initialized = true; home(false); }
  }

  dom.search.addEventListener('input', renderNavigation);
  dom['nav-close'].addEventListener('click', () => setPanel('navigation', false));
  dom['nav-open'].addEventListener('click', () => setPanel('navigation', true));
  dom['layers-close'].addEventListener('click', () => setPanel('layers', false));
  for (const [id, name] of [['mobile-nav', 'navigation'], ['mobile-layers', 'layers'], ['mobile-dossier', 'dossier']]) {
    dom[id].addEventListener('click', () => setPanel(name, dom[name].hidden));
  }
  mobileMedia.addEventListener('change', event => {
    mobile = event.matches;
    if (mobile) {
      const open = ['dossier', 'navigation', 'layers'].find(name => !dom[name].hidden);
      for (const name of Object.keys(panels)) panels[name] = name === open;
    } else { panels.navigation = true; panels.layers = true; }
    syncPanels();
    refreshViewport();
  });
  window.addEventListener('resize', refreshViewport);
  window.visualViewport?.addEventListener('resize', refreshViewport);
  dom['zoom-in'].addEventListener('click', () => zoom(1.25));
  dom['zoom-out'].addEventListener('click', () => zoom(1 / 1.25));
  dom['map-home'].addEventListener('click', () => home());
  dom['map-fit'].addEventListener('click', () => fit());
  dom['mobile-home'].addEventListener('click', () => home());
  dom['dossier-close'].addEventListener('click', () => setPanel('dossier', false));
  dom['dossier-fold'].addEventListener('click', () => {
    dom['dossier-body'].hidden = !dom['dossier-body'].hidden;
    dom.dossier.classList.toggle('folded', dom['dossier-body'].hidden);
    dom['dossier-fold'].setAttribute('aria-expanded', String(!dom['dossier-body'].hidden));
  });
  dom['dossier-edit'].addEventListener('click', () => { if (selected()) context.onEditLocation?.(selected().id); });
  dom['dossier-add-object'].addEventListener('click', () => { if (selected()) context.onAddObject?.(selected().id); });
  dom['dossier-focus'].addEventListener('click', () => { if (selected()) focusLocation(selected().id); });
  dom['dossier-favorite'].addEventListener('click', () => {
    const location = selected();
    if (!location) return;
    if (favorites.has(location.id)) favorites.delete(location.id);
    else favorites.add(location.id);
    try { localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites])); } catch { /* Still usable for this session. */ }
    renderNavigation();
    renderDossier();
    context.onFavoriteChange?.(location.id, favorites.has(location.id));
  });
  dom['faction-clear'].addEventListener('click', () => { selectedFaction = null; render(); });
  for (const id of ['show-territories', 'show-labels', 'show-reconstructions']) dom[id].addEventListener('change', render);
  dom['layers-fold'].addEventListener('click', () => {
    dom['layer-body'].hidden = !dom['layer-body'].hidden;
    dom['layers-fold'].setAttribute('aria-expanded', String(!dom['layer-body'].hidden));
  });
  for (const [id, name] of [['filter-all', 'all'], ['filter-favorites', 'favorites'], ['filter-nobles', 'nobles']]) {
    dom[id].addEventListener('click', () => { tab = name; renderNavigation(); });
  }
  dom['fold-groups'].addEventListener('click', () => {
    groupsFolded = Boolean(dom['location-list'].querySelector('details[open]'));
    for (const group of dom['location-list'].querySelectorAll('details.group')) {
      group.open = !groupsFolded;
      groupOpen.set(group.dataset.factionId ?? null, group.open);
    }
    dom['fold-groups'].textContent = groupsFolded ? 'Развернуть' : 'Свернуть';
  });
  document.addEventListener('keydown', event => {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey || document.querySelector('dialog[open]')) return;
    if (event.target.closest('input, textarea, select, [contenteditable]:not([contenteditable="false"])')) return;
    const key = event.key.toLocaleLowerCase('ru');
    if (key === '/') { setPanel('navigation', true); dom.search.focus(); }
    else if (key === 'n' || key === 'т') setPanel('navigation', dom.navigation.hidden);
    else if (key === 'g' || key === 'п') home();
    else if (key === '0') fit();
    else if (key === '+' || key === '=') zoom(1.25);
    else if (key === '-' || key === '−') zoom(1 / 1.25);
    else return;
    event.preventDefault();
  });
  refreshViewport();
  render();
  return { render, renderDossier, focusLocation, home, fit, zoom, setPanel, toMap, getCamera, setMapInteraction, refreshViewport };
}
