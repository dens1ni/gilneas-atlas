/**
 * Port of Naitroud's territory-engine.js (bundled assets/app.js:1–66,
 * origin/main 7df4782). Grid dimensions/precision now belong to the snapshot;
 * location coordinates are exact map centres, not 11px pin top-lefts.
 */
export const DEFAULT_STEP = 16;
export const DEFAULT_RADIUS = 260;
export const MAX_CELLS = 131072;
export const MIN_RADIUS = 40;
export const MAX_RADIUS = 600;

// Adapted from the source validate(t, groups). Validate BEFORE allocating or
// copying cells. Registry keys may omit newly added, as-yet-unpainted factions.
export function validate(t, factions, meta, { clone = true } = {}) {
  const fail = () => { throw Error('Неверный слой территорий (territoryGrid).'); };
  if (!t || typeof t !== 'object' || Array.isArray(t) || t.version !== 1 ||
      !Number.isInteger(t.width) || !Number.isInteger(t.height) || t.width <= 0 || t.height <= 0 ||
      t.width > MAX_CELLS || t.height > MAX_CELLS || t.width * t.height > MAX_CELLS ||
      !Number.isInteger(t.step) || t.step < 1 || t.step > 256 ||
      !Array.isArray(factions) || !Array.isArray(t.keys) ||
      t.keys.length > factions.length || new Set(t.keys).size !== t.keys.length ||
      t.keys.some(k => typeof k !== 'string' || !factions.some(f => f?.id === k)) ||
      !Array.isArray(t.cells) || t.cells.length !== t.width * t.height ||
      !Number.isFinite(t.radius) || t.radius < MIN_RADIUS || t.radius > MAX_RADIUS) fail();
  for (let i = 0; i < t.keys.length; i++) if (!Object.hasOwn(t.keys, i)) fail();
  for (let i = 0; i < t.cells.length; i++) {
    const value = t.cells[i];
    if (!Object.hasOwn(t.cells, i) || !Number.isInteger(value) || value < 0 || value > t.keys.length) fail();
  }
  if (meta) {
    if (!Number.isFinite(meta.width) || !Number.isFinite(meta.height) || meta.width <= 0 || meta.height <= 0 ||
        t.width !== Math.ceil(meta.width / t.step) || t.height !== Math.ceil(meta.height / t.step) ||
        (t.mapWidth !== undefined && t.mapWidth !== meta.width) ||
        (t.mapHeight !== undefined && t.mapHeight !== meta.height)) fail();
  } else {
    for (const [dimension, count] of [[t.mapWidth, t.width], [t.mapHeight, t.height]]) {
      if (dimension !== undefined && (!Number.isFinite(dimension) || dimension <= 0 || Math.ceil(dimension / t.step) !== count)) fail();
    }
  }
  return clone ? JSON.parse(JSON.stringify(t)) : t;
}

function emptyLayer(factions, radius, meta, step = DEFAULT_STEP) {
  if (!meta || !Number.isFinite(meta.width) || !Number.isFinite(meta.height) || meta.width <= 0 || meta.height <= 0 ||
      !Number.isInteger(step) || step < 1 || step > 256 ||
      !Number.isFinite(radius) || radius < MIN_RADIUS || radius > MAX_RADIUS) throw Error('Неверный размер сетки или радиус территорий.');
  const width = Math.ceil(meta.width / step), height = Math.ceil(meta.height / step);
  if (width * height > MAX_CELLS) throw Error('Сетка территорий слишком велика.');
  const layer = { version: 1, width, height, step, mapWidth: meta.width, mapHeight: meta.height,
    keys: factions.map(f => f.id), cells: new Array(width * height).fill(0), radius };
  return validate(layer, factions, meta, { clone: false });
}

/** Centre of a cell, including the clipped last row/column. */
export function cellPoint(layer, x, y) {
  const width = layer.mapWidth ?? layer.width * layer.step;
  const height = layer.mapHeight ?? layer.height * layer.step;
  return [x * layer.step + Math.min(layer.step, width - x * layer.step) / 2,
    y * layer.step + Math.min(layer.step, height - y * layer.step) / 2];
}

// The source nearest-seed / radius algorithm, with the grid size moved out of
// its global constants and the source's +5.5 marker offset deliberately removed.
export function generate(locations, factions, radius = DEFAULT_RADIUS, meta, canPlace = () => true, step = DEFAULT_STEP) {
  const layer = emptyLayer(factions, radius, meta, step);
  const { keys, cells, width, height } = layer;
  const values = new Map(keys.map((key, i) => [key, i + 1]));
  const points = locations.filter(p => values.has(p.faction) && Number.isFinite(p.x) && Number.isFinite(p.y))
    .map(p => ({ x: p.x, y: p.y, v: values.get(p.faction) }));
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const point = cellPoint(layer, x, y);
      if (!canPlace(point)) continue;
      let best = radius * radius, value = 0;
      for (const p of points) {
        const d = (point[0] - p.x) ** 2 + (point[1] - p.y) ** 2;
        if (d < best) { best = d; value = p.v; }
      }
      cells[y * width + x] = value;
    }
  }
  return layer;
}

/** The source circular brush; only the controller's private working layer mutates. */
export function paint(t, x, y, r, value, canPlace = () => true, onChange = null) {
  if (![x, y, r].every(Number.isFinite) || r <= 0 || r > 600 ||
      !Number.isInteger(value) || value < 0 || value > t.keys.length) throw Error('Неверная кисть территорий.');
  const { width, height, step } = t;
  const a = Math.max(0, Math.floor((x - r) / step)), b = Math.min(width - 1, Math.ceil((x + r) / step)),
    c = Math.max(0, Math.floor((y - r) / step)), d = Math.min(height - 1, Math.ceil((y + r) / step));
  let changed = 0;
  for (let j = c; j <= d; j++) {
    for (let i = a; i <= b; i++) {
      const point = cellPoint(t, i, j), index = j * width + i;
      if ((point[0] - x) ** 2 + (point[1] - y) ** 2 <= r * r && t.cells[index] !== value && canPlace(point)) {
        const previous = t.cells[index];
        t.cells[index] = value;
        changed++;
        onChange?.(index, previous, value);
      }
    }
  }
  return changed;
}
