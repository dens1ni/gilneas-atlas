import { normalizeData, factionMembers, sovereignOf } from './model.mjs';
import { validate, generate, paint, cellPoint, MIN_RADIUS, MAX_RADIUS } from './territory-engine.mjs';
import { geometryAsync, paths } from './smooth-territories.mjs';
export { prepareTerritoryGrid } from './territory-data.mjs';

const NS = 'http://www.w3.org/2000/svg';
const copy = value => JSON.parse(JSON.stringify(value));
const sameArray = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
const sameGrid = (a, b) => a && b && a.width === b.width && a.height === b.height && a.step === b.step &&
  a.mapWidth === b.mapWidth && a.mapHeight === b.mapHeight && sameArray(a.keys, b.keys) && sameArray(a.cells, b.cells);

/**
 * Naitroud territory renderer/controller port (assets/app.js:4776–5125,
 * pointer capture/interpolator:5643–5679), commit
 * 7df478262e6c84553f44d60bc31397be6da54ee9. Only paint/erase/camera
 * are retained. Immutable Gilneas snapshots replace the source global layer.
 * Prepare the snapshot explicitly after loading its inactive mask, before init.
 */
export function initTerritories(context) {
  const { getData, replaceData, ui, canPlace = () => true, toast = () => {} } = context;
  if (typeof getData !== 'function' || typeof replaceData !== 'function' || !ui?.toMap || !ui?.setMapInteraction)
    throw Error('Редактор границ требует getData, replaceData и API камеры UI.');
  const view = document.getElementById('viewport'), world = document.getElementById('world');
  if (!view || !world) throw Error('Не найден viewport/world для границ.');
  if (document.getElementById('boundary-tools')) throw Error('Редактор границ уже установлен.');
  const panel = document.createElement('aside');
  panel.id = 'boundary-tools';
  panel.className = 'iron-panel boundary-tools';
  panel.hidden = true;
  panel.setAttribute('aria-label', 'Редактор границ держав');
  panel.innerHTML = '<header class="panel-head"><div><span class="eyebrow">ГРАНИЦЫ ДЕРЖАВ</span><h2>Картографическая кисть</h2></div><button id="boundary-close" type="button" class="square" aria-label="Закрыть инструменты">×</button></header><div class="boundary-body"><p>Кисть заменяет владельца участка, ластик оставляет незанятые земли. Alt / Command — камера. Два пальца — масштаб и перемещение.</p><label for="boundary-faction">Фракция</label><select id="boundary-faction"></select><label for="boundary-mode">Инструмент</label><select id="boundary-mode"><option value="paint">Кисть территории</option><option value="erase">Ластик</option><option value="camera">Камера</option></select><label for="boundary-brush">Радиус кисти, единицы карты</label><input id="boundary-brush" type="range" min="8" max="220" value="48"><label for="boundary-radius">Радиус автограниц</label><input id="boundary-radius" type="number" min="40" max="600" value="260"><button id="boundary-generate" type="button" class="brass-button">Перестроить по локациям</button><div class="boundary-actions"><button id="boundary-undo" type="button" class="iron-button" disabled>↶ Отмена</button><button id="boundary-redo" type="button" class="iron-button" disabled>↷ Повтор</button></div><button id="boundary-clear" type="button" class="iron-button">Очистить границы</button><button id="boundary-save" type="button" class="brass-button">Сохранить границы</button><small id="boundary-status" role="status" aria-live="polite"></small></div>';
  (document.getElementById('atlas') || document.body).append(panel);
  const $ = suffix => document.getElementById('boundary-' + suffix);
  function node(tag, attrs, parent) {
    const el = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, String(value));
    parent.append(el);
    return el;
  }
  const vector = node('svg', { id: 'boundary-vector', 'aria-hidden': 'true' }, world);
  const preview = node('svg', { id: 'boundary-brush-preview', 'aria-hidden': 'true' }, world);
  const cursor = node('circle', { id: 'boundary-brush-cursor', fill: 'none', stroke: '#d4c297',
    'stroke-width': 1, 'vector-effect': 'non-scaling-stroke', visibility: 'hidden' }, preview);
  for (const el of [vector, preview]) Object.assign(el.style, {
    position: 'absolute', left: '0', top: '0', pointerEvents: 'none', overflow: 'hidden', zIndex: el === vector ? '1' : '2',
  });
  const legacy = document.getElementById('territory-layer');
  if (legacy) legacy.after(vector, preview);
  let sourceData = null, sourceGrid = null, layer = null, editing = false, stroke = null;
  let revision = 0, cachedRevision = -1, cachedGeometry = null, cachedPaths = [], cachedBloc = [], cachedOwners = '';
  let domRevision = -1, domOwners = '', styles = [], busy = false, scheduled = 0, failedRevision = -1, failedError = null;
  let options = {}, syncing = false, applyingCommit = false, disposed = false;
  const waiters = [];
  const undo = [], redo = [];
  const touchPan = new Set();
  let handingOffTouch = false;
  const performanceInfo = { revision: 0, geometryCalls: 0, staleResults: 0, geometryWallMs: 0, chains: 0,
    changedCells: 0, strokeMs: 0, brushHandlerMaxMs: 0 };

  function status(message) { $('status').textContent = message; }
  function historyButtons() { $('undo').disabled = !undo.length; $('redo').disabled = !redo.length; }
  function frameSize(data) {
    for (const el of [vector, preview]) {
      el.setAttribute('viewBox', `0 0 ${data.meta.width} ${data.meta.height}`);
      el.style.width = data.meta.width + 'px'; el.style.height = data.meta.height + 'px';
    }
  }
  function syncData() {
    const data = getData();
    if (data === sourceData || syncing) return;
    if (!Object.hasOwn(data, 'territoryGrid')) throw Error('Сначала вызовите prepareTerritoryGrid после загрузки маски.');
    const incoming = data.territoryGrid;
    validate(incoming, data.factions, data.meta, { clone: false });
    const changed = !sameGrid(sourceGrid, incoming);
    if (!applyingCommit && stroke) {
      const interrupted = stroke; stroke = null;
      if (view.hasPointerCapture(interrupted.id)) view.releasePointerCapture(interrupted.id);
      clearPreview();
    }
    if (!applyingCommit && changed) { undo.length = 0; redo.length = 0; historyButtons(); }
    if (changed) {
      layer = { ...copy(incoming), mapWidth: data.meta.width, mapHeight: data.meta.height };
      revision++; failedRevision = -1;
    } else {
      // Keep author extension changes even when no ownership changed.
      layer = { ...copy(incoming), keys: incoming.keys.slice(), cells: incoming.cells.slice(), mapWidth: data.meta.width, mapHeight: data.meta.height };
    }
    for (const faction of data.factions) if (!layer.keys.includes(faction.id)) layer.keys.push(faction.id);
    sourceData = data; sourceGrid = incoming;
    const previous = $('faction').value;
    $('faction').replaceChildren(...data.factions.map(f => new Option(f.name, f.id)));
    if (data.factions.some(f => f.id === previous)) $('faction').value = previous;
    $('radius').value = String(layer.radius);
    frameSize(data);
  }
  function owners() { return [0, ...layer.keys.map(key => layer.keys.indexOf(sovereignOf(getData().factions, key)) + 1)]; }
  function selectedFactions() {
    if (options.included instanceof Set) return options.included;
    const selected = document.querySelector('#faction-list [aria-pressed="true"][data-faction-id]')?.dataset.factionId;
    return selected ? new Set(factionMembers(getData().factions, selected)) : null;
  }
  function clearPreview() { preview.querySelectorAll('rect').forEach(el => el.remove()); }
  function settleReady(error = null) {
    if (!error && (stroke || busy || cachedRevision !== revision || domRevision !== cachedRevision)) return;
    for (const waiter of waiters.splice(0)) error ? waiter.reject(error) : waiter.resolve({ ...performanceInfo });
  }
  function requestRender() {
    if (!scheduled && !disposed) scheduled = requestAnimationFrame(() => { scheduled = 0; render(); });
  }
  function rebuild() {
    if (busy || stroke || cachedRevision === revision || failedRevision === revision || disposed) return;
    busy = true;
    const target = revision, snapshot = { ...layer, keys: layer.keys.slice(), cells: layer.cells.slice() }, start = performance.now();
    performanceInfo.geometryCalls++;
    geometryAsync(snapshot).then(chains => {
      if (!disposed && target === revision && !stroke) {
        cachedGeometry = chains; cachedPaths = paths(snapshot, chains); cachedRevision = target; cachedOwners = '';
        if (failedError && $('status').textContent === 'Не удалось обновить контуры: ' + failedError.message) status('');
        failedError = null;
        Object.assign(performanceInfo, { revision: target, geometryWallMs: performance.now() - start, chains: chains.length });
      } else performanceInfo.staleResults++;
    }).catch(error => {
      if (disposed || target !== revision) return;
      failedRevision = target; failedError = error; status('Не удалось обновить контуры: ' + error.message); settleReady(error);
    }).finally(() => { busy = false; requestRender(); });
  }
  function render(renderOptions) {
    if (disposed || syncing) return;
    if (renderOptions) options = renderOptions;
    syncData();
    if (!stroke) rebuild();
    const data = getData(), byKey = new Map(data.factions.map(f => [f.id, f])), ownerMap = owners(), signature = ownerMap.join(',');
    if (cachedGeometry && cachedOwners !== signature) {
      cachedBloc = paths(layer, cachedGeometry, ownerMap); cachedOwners = signature;
    }
    if (domRevision !== cachedRevision || domOwners !== signature) {
      vector.replaceChildren(); styles = [];
      const defs = node('defs', {}, vector);
      const styledPath = (region, attrs, baseOpacity, fill = false, bloc = false) => {
        const el = node('path', { d: region.d, 'data-faction-id': region.key, 'data-bloc': String(bloc), ...attrs }, vector);
        styles.push({ el, key: region.key, baseOpacity, fill, bloc }); return el;
      };
      for (const region of cachedPaths) {
        const faction = byKey.get(region.key);
        if (faction && region.d) styledPath(region, { fill: faction.color, 'fill-rule': 'evenodd' }, faction.parent ? .145 : .12, true);
      }
      // Source sovereign union and clipped inward band: same shared cubics,
      // never a separately smoothed union grid, so vassal seams cannot sliver.
      for (let i = 0; i < cachedBloc.length; i++) {
        const region = cachedBloc[i], faction = byKey.get(region.key);
        if (!faction || ownerMap[i + 1] !== i + 1 || !region.d) continue;
        const id = 'boundary-bloc-clip-' + i, clip = node('clipPath', { id, clipPathUnits: 'userSpaceOnUse' }, defs);
        node('path', { d: region.d, 'clip-rule': 'evenodd' }, clip);
        for (const [width, opacity] of [[16, .12], [2, .62]]) styledPath(region, { fill: 'none', stroke: faction.color,
          'stroke-width': width, 'stroke-linejoin': 'round', 'clip-path': `url(#${id})` }, opacity, false, true);
      }
      for (let i = 0; i < cachedPaths.length; i++) {
        const region = cachedPaths[i], faction = byKey.get(region.key);
        if (!faction || ownerMap[i + 1] === i + 1 || !region.d) continue;
        styledPath(region, { fill: 'none', stroke: faction.color, 'stroke-width': 1.15,
          'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, .38);
      }
      domRevision = cachedRevision; domOwners = signature;
    }
    const selected = selectedFactions();
    for (const item of styles) {
      const faction = byKey.get(item.key);
      if (!faction) continue;
      const faded = selected && (item.bloc ? ![...selected].some(id => ownerMap[layer.keys.indexOf(id) + 1] === ownerMap[layer.keys.indexOf(item.key) + 1]) : !selected.has(item.key));
      item.el.setAttribute(item.fill ? 'fill' : 'stroke', faction.color);
      item.el.setAttribute(item.fill ? 'fill-opacity' : 'stroke-opacity', String(item.baseOpacity * (faded ? .2 : 1)));
    }
    const visible = editing || (options.visible ?? document.getElementById('show-territories')?.checked ?? true);
    vector.toggleAttribute('hidden', !visible); preview.toggleAttribute('hidden', !visible);
    if (legacy) legacy.setAttribute('hidden', '');
    if (!stroke && cachedRevision === revision) clearPreview();
    settleReady();
  }
  function whenReady() {
    render();
    if (failedRevision === revision) return Promise.reject(failedError);
    if (cachedRevision === revision && domRevision === cachedRevision && !busy && !stroke) return Promise.resolve({ ...performanceInfo });
    return new Promise((resolve, reject) => waiters.push({ resolve, reject }));
  }
  function commitLayer(next, message) {
    const normalized = normalizeData({ ...getData(), territoryGrid: validate(next, getData().factions, getData().meta) });
    syncing = true;
    try { replaceData(normalized); } finally { syncing = false; }
    sourceData = null; applyingCommit = true;
    try { syncData(); } finally { applyingCommit = false; }
    render(); status(message);
  }
  function mapPoint(event) { return ui.toMap(event.clientX, event.clientY); }
  function swallow(event) { event.preventDefault(); event.stopImmediatePropagation(); }
  function apply(point) {
    const start = performance.now(), { last, radius, value } = stroke;
    const record = (index, previous) => {
      if (stroke.changed.has(index)) return;
      stroke.changed.set(index, previous);
      const x = index % layer.width, y = Math.floor(index / layer.width), p = cellPoint(layer, x, y);
      const width = Math.min(layer.step, layer.mapWidth - x * layer.step), height = Math.min(layer.step, layer.mapHeight - y * layer.step);
      node('rect', { x: p[0] - width / 2, y: p[1] - height / 2, width, height,
        fill: value ? stroke.color : '#a4c3d0', 'fill-opacity': .32 }, preview);
    };
    if (last) {
      const distance = Math.hypot(point[0] - last[0], point[1] - last[1]), n = Math.max(1, Math.ceil(distance / Math.max(4, radius / 3)));
      for (let i = 1; i <= n; i++) paint(layer, last[0] + (point[0] - last[0]) * i / n,
        last[1] + (point[1] - last[1]) * i / n, radius, value, canPlace, record);
    } else paint(layer, point[0], point[1], radius, value, canPlace, record);
    stroke.last = point;
    if (stroke.changed.size) { revision++; failedRevision = -1; }
    performanceInfo.brushHandlerMaxMs = Math.max(performanceInfo.brushHandlerMaxMs, performance.now() - start);
  }
  function pointerDown(event) {
    if (handingOffTouch || touchPan.size) return;
    if (!editing || event.button !== 0 || event.altKey || event.metaKey || $('mode').value === 'camera' || !view.contains(event.target)) return;
    if (stroke && event.pointerType === 'touch' && stroke.pointerType === 'touch' && event.pointerId !== stroke.id) {
      // The first finger was captured by the brush, not UI. Cancel its private
      // preview, then seed that STILL-ACTIVE pointer into the real UI camera
      // handler before allowing the second native pointerdown to reach it.
      const first = stroke;
      endStroke(null, true);
      touchPan.add(first.id); touchPan.add(event.pointerId);
      ui.setMapInteraction(null);
      handingOffTouch = true;
      try { view.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerId: first.id,
        pointerType: 'touch', isPrimary: true, clientX: first.clientX, clientY: first.clientY, button: 0, buttons: 1 })); }
      finally { handingOffTouch = false; }
      cursor.setAttribute('visibility', 'hidden');
      return;
    }
    syncData();
    if (stroke) return;
    const value = $('mode').value === 'erase' ? 0 : layer.keys.indexOf($('faction').value) + 1;
    if ($('mode').value === 'paint' && !value) return;
    swallow(event); view.setPointerCapture(event.pointerId);
    stroke = { id: event.pointerId, pointerType: event.pointerType, clientX: event.clientX, clientY: event.clientY,
      last: null, value, radius: Number($('brush').value), before: copy(layer),
      changed: new Map(), color: getData().factions.find(f => f.id === $('faction').value)?.color ?? '#d4c297', started: performance.now() };
    apply(mapPoint(event));
  }
  function pointerMove(event) {
    if (!editing || touchPan.size) return;
    const point = mapPoint(event);
    cursor.setAttribute('cx', point[0]); cursor.setAttribute('cy', point[1]); cursor.setAttribute('r', $('brush').value);
    cursor.setAttribute('visibility', $('mode').value === 'camera' ? 'hidden' : 'visible');
    if (stroke?.id !== event.pointerId) return;
    stroke.clientX = event.clientX; stroke.clientY = event.clientY;
    swallow(event);
    for (const part of event.getCoalescedEvents?.().length ? event.getCoalescedEvents() : [event]) apply(mapPoint(part));
  }
  function endStroke(event, cancel = false) {
    if (event && touchPan.has(event.pointerId)) {
      touchPan.delete(event.pointerId);
      if (!touchPan.size) queueMicrotask(() => {
        if (editing) ui.setMapInteraction($('mode').value === 'camera' ? null : () => {});
      });
      return;
    }
    if (!stroke || (event && stroke.id !== event.pointerId)) return;
    if (event) swallow(event);
    const completed = stroke;
    stroke = null;
    if (view.hasPointerCapture(completed.id)) view.releasePointerCapture(completed.id);
    Object.assign(performanceInfo, { changedCells: completed.changed.size, strokeMs: performance.now() - completed.started });
    if (cancel || !completed.changed.size) { layer = completed.before; revision++; clearPreview(); requestRender(); return; }
    try {
      commitLayer(layer, `Границы сохранены · ${completed.changed.size} ячеек`);
      undo.push(completed.before); if (undo.length > 30) undo.shift(); redo.length = 0; historyButtons();
    }
    catch (error) { layer = completed.before; revision++; clearPreview(); status(error.message); toast(error.message); requestRender(); }
  }
  function blockClick(event) {
    if (editing && $('mode').value !== 'camera' && !event.altKey && !event.metaKey && view.contains(event.target)) swallow(event);
  }
  function open() {
    syncData();
    document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
    for (const name of ['navigation', 'layers', 'dossier']) ui.setPanel(name, false);
    editing = true; panel.hidden = false; document.body.classList.add('boundary-editing');
    ui.setMapInteraction($('mode').value === 'camera' ? null : () => {}); render();
  }
  function close() {
    if (stroke) endStroke(null, true);
    editing = false; panel.hidden = true; document.body.classList.remove('boundary-editing');
    ui.setMapInteraction(null); cursor.setAttribute('visibility', 'hidden'); render();
  }
  $('close').addEventListener('click', close);
  $('mode').addEventListener('change', () => {
    if (stroke) endStroke(null, true);
    if (editing) ui.setMapInteraction($('mode').value === 'camera' ? null : () => {});
    cursor.setAttribute('visibility', 'hidden');
  });
  function restoreHistory(from, to, message) {
    if (!from.length || stroke) return;
    const previous = copy(layer), target = from.at(-1);
    try {
      commitLayer(target, message);
      from.pop(); to.push(previous); if (to.length > 30) to.shift(); historyButtons();
    } catch (error) { status(error.message); toast(error.message); }
  }
  $('undo').addEventListener('click', () => restoreHistory(undo, redo, 'Изменение границ отменено'));
  $('redo').addEventListener('click', () => restoreHistory(redo, undo, 'Изменение границ повторено'));
  function editGrid(next, message) {
    const previous = copy(layer);
    commitLayer(next, message);
    undo.push(previous); if (undo.length > 30) undo.shift(); redo.length = 0; historyButtons();
  }
  $('clear').addEventListener('click', () => {
    if (stroke || !confirm('Очистить все границы? Действие можно отменить.')) return;
    try { editGrid({ ...layer, cells: new Array(layer.cells.length).fill(0) }, 'Границы очищены'); }
    catch (error) { status(error.message); toast(error.message); }
  });
  $('generate').addEventListener('click', () => {
    if (stroke) return;
    const radius = Number($('radius').value);
    if (!Number.isFinite(radius) || radius < MIN_RADIUS || radius > MAX_RADIUS) {
      status('Радиус автограниц: 40–600'); toast('Радиус автограниц: 40–600'); return;
    }
    if (!confirm('Перестроить территории по локациям? Ручные изменения заменятся; действие можно отменить.')) return;
    try {
      const data = getData(), generated = generate(data.locations, data.factions, radius, data.meta, canPlace, layer.step);
      editGrid({ ...layer, ...generated }, 'Границы перестроены по локациям');
    } catch (error) { status(error.message); toast(error.message); }
  });
  $('save').addEventListener('click', () => {
    if (stroke) return;
    try { commitLayer(layer, 'Границы сохранены в локальном черновике'); }
    catch (error) { status(error.message); toast(error.message); }
  });
  const listeners = [['pointerdown', pointerDown], ['pointermove', pointerMove],
    ['pointerup', endStroke], ['pointercancel', event => endStroke(event, true)], ['click', blockClick], ['dblclick', blockClick]];
  for (const [name, handler] of listeners) document.addEventListener(name, handler, { capture: true, passive: false });
  const cancelOnBlur = () => { if (stroke) endStroke(null, true); cursor.setAttribute('visibility', 'hidden'); };
  const cancelWhenHidden = () => { if (document.hidden) cancelOnBlur(); };
  window.addEventListener('blur', cancelOnBlur);
  document.addEventListener('visibilitychange', cancelWhenHidden);
  render();
  return { render, open, close, whenReady, get ready() { return whenReady(); }, getGrid: () => copy(layer),
    getPerformance: () => ({ ...performanceInfo }), destroy() {
      close(); disposed = true; if (scheduled) cancelAnimationFrame(scheduled);
      for (const [name, handler] of listeners) document.removeEventListener(name, handler, true);
      window.removeEventListener('blur', cancelOnBlur);
      document.removeEventListener('visibilitychange', cancelWhenHidden);
      panel.remove(); vector.remove(); preview.remove(); settleReady(Error('Редактор закрыт.'));
    } };
}
