import { validate, cellPoint, DEFAULT_RADIUS, DEFAULT_STEP, MIN_RADIUS, MAX_RADIUS, MAX_CELLS } from './territory-engine.mjs';
import { sovereignOf, effectiveFaction } from './model.mjs';

const fail = detail => { throw new Error(`Invalid realm territory layout: ${detail}`); };
const plain = value => value && typeof value === 'object' && !Array.isArray(value) &&
  [null, Object.prototype].includes(Object.getPrototypeOf(value));
const own = (value, key) => {
  const descriptor = Object.getOwnPropertyDescriptor(value, key);
  if (!descriptor || !Object.hasOwn(descriptor, 'value')) fail(`missing own JSON field ${key}`);
  return descriptor.value;
};
function checkJSON(value, ancestors = new Set()) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return;
  if (typeof value === 'number' && Number.isFinite(value)) return;
  if (typeof value !== 'object' || (!Array.isArray(value) && !plain(value))) fail('plan must contain only JSON');
  if (ancestors.has(value)) fail('cyclic plan');
  ancestors.add(value);
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i++) checkJSON(own(value, String(i)), ancestors);
  }
  for (const key of Reflect.ownKeys(value)) {
    if (Array.isArray(value) && key === 'length') continue;
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (typeof key !== 'string' || !descriptor.enumerable || !Object.hasOwn(descriptor, 'value')) fail('non-JSON plan property');
    if (Array.isArray(value)) {
      if (!/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= value.length) fail('non-JSON array property');
    } else checkJSON(descriptor.value, ancestors);
  }
  ancestors.delete(value);
}

/**
 * Replace every authored land domain, without consulting old polygons/grids.
 * Leaf owners are exclusive; renderers derive ancestor unions from this grid.
 * Offshore pins may seed nearby land, but pins in another realm cannot do so.
 */
export function generateRealmTerritoryLayout(snapshot, plan, { radius = DEFAULT_RADIUS } = {}) {
  if (!plain(plan) || !snapshot || !plain(snapshot.meta)) fail('missing plan or snapshot metadata');
  if (!Number.isFinite(radius) || radius < MIN_RADIUS || radius > MAX_RADIUS) fail('radius must be 40..600');
  const width = own(plan, 'width'), height = own(plan, 'height'), step = own(plan, 'step');
  if (!Number.isInteger(width) || !Number.isInteger(height) || width <= 0 || height <= 0 ||
      width > MAX_CELLS || height > MAX_CELLS || width * height > MAX_CELLS) fail('grid dimensions too large or invalid');
  const mapWidth = own(plan, 'mapWidth'), mapHeight = own(plan, 'mapHeight');
  if (own(plan, 'version') !== 1 || step !== DEFAULT_STEP ||
      !Number.isFinite(mapWidth) || !Number.isFinite(mapHeight) || mapWidth <= 0 || mapHeight <= 0 ||
      mapWidth !== snapshot.meta.width || mapHeight !== snapshot.meta.height ||
      width !== Math.ceil(mapWidth / step) || height !== Math.ceil(mapHeight / step)) fail('inexact grid dimensions');
  const image = own(plan, 'image'), mapRevision = own(plan, 'mapRevision');
  if (typeof image !== 'string' || !image.length || image !== snapshot.meta.image ||
      typeof mapRevision !== 'string' || !mapRevision.length || mapRevision !== snapshot.meta.mapRevision) fail('image or mapRevision mismatch');
  checkJSON(plan);
  if (!Array.isArray(snapshot.factions) || !Array.isArray(snapshot.locations)) fail('missing factions or locations');
  const keys = snapshot.factions.map(f => {
    if (!f || typeof f.id !== 'string') fail('invalid literal faction ID');
    return f.id;
  });
  if (new Set(keys).size !== keys.length) fail('duplicate faction ID');
  const roots = new Map(snapshot.factions.map(f => [f.id, sovereignOf(snapshot.factions, f.id)]));
  const rootKeys = own(plan, 'keys');
  if (!Array.isArray(rootKeys) || rootKeys.length !== 3 ||
      !['gilneas', 'lordaeron', 'dalaran'].every(id => rootKeys.includes(id)) ||
      rootKeys.some(id => roots.get(id) !== id)) fail('domains require existing independent sovereigns');
  validate({ ...plan, radius }, snapshot.factions, snapshot.meta, { clone: false });
  const values = new Map(keys.map((id, index) => [id, index + 1]));
  const seeds = [];
  for (const location of snapshot.locations) {
    if (!location || typeof location !== 'object') fail('invalid location');
    const faction = effectiveFaction(location);
    if (faction == null) continue;
    if (!values.has(faction)) fail('unknown literal pin faction');
    if (!Number.isFinite(location.x) || !Number.isFinite(location.y)) continue;
    if (location.x < 0 || location.y < 0 || location.x > mapWidth || location.y > mapHeight) continue;
    const column = Math.min(width - 1, Math.floor(location.x / step));
    const row = Math.min(height - 1, Math.floor(location.y / step));
    const domain = plan.cells[row * width + column];
    const root = roots.get(faction);
    if (domain !== 0 && rootKeys[domain - 1] !== root) continue;
    seeds.push({ x: location.x, y: location.y, value: values.get(faction), root });
  }
  const known = new Set(['version', 'width', 'height', 'step', 'mapWidth', 'mapHeight', 'image', 'mapRevision', 'keys', 'cells']);
  const extras = Object.fromEntries(Object.entries(plan).filter(([key]) => !known.has(key)));
  const layer = { version: 1, width, height, step, mapWidth, mapHeight, keys,
    cells: plan.cells.map(value => value ? values.get(rootKeys[value - 1]) : 0), radius,
    precision: { cellSizeMapUnits: step, sampling: 'cell-centre', clippedEdgeCells: true },
    migration: { method: 'author-full-realm-layout', legacyPolygonsRetained: false },
    realmLayout: { ...structuredClone(extras), version: 1, image, mapRevision,
      rootKeys: structuredClone(rootKeys), domainCells: structuredClone(plan.cells) } };
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const index = y * width + x, domain = plan.cells[index];
      if (!domain) continue;
      const root = rootKeys[domain - 1], point = cellPoint(layer, x, y);
      let best = radius * radius;
      for (const seed of seeds) {
        if (seed.root !== root) continue;
        const distance = (point[0] - seed.x) ** 2 + (point[1] - seed.y) ** 2;
        // Strict comparison matches the established engine and keeps first-pin ties.
        if (distance < best) { best = distance; layer.cells[index] = seed.value; }
      }
    }
  }
  return validate(layer, snapshot.factions, snapshot.meta, { clone: false });
}
