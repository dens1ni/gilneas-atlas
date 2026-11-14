import { normalizeData, inPolygon } from './model.mjs';
import { generate, validate, cellPoint, DEFAULT_STEP, DEFAULT_RADIUS } from './territory-engine.mjs';

/**
 * Explicit bootstrap/import/reset migration, never an automatic response to a
 * selection or a location edit. No storage or application-global side effects.
 * The legacy polygons, locations and all author/source fields remain intact.
 */
export function prepareTerritoryGrid(raw, canPlace = () => true, { step = DEFAULT_STEP, radius = DEFAULT_RADIUS } = {}) {
  const data = normalizeData(raw);
  if (Object.hasOwn(data, 'territoryGrid')) return data;
  const layer = generate(data.territories.length ? [] : data.locations, data.factions, radius, data.meta, canPlace, step);
  if (data.territories.length) {
    const byId = new Map(data.factions.map(f => [f.id, f]));
    const depth = id => {
      let count = 0, current = byId.get(id);
      while (current.parent != null) { count++; current = byId.get(current.parent); }
      return count;
    };
    // Stable ancestor-before-descendant traversal: deep vassals override their
    // sovereign coverage; later same-depth author polygons retain precedence.
    const polygons = data.territories.map((polygon, order) => ({ polygon, order, depth: depth(polygon.faction) }))
      .sort((a, b) => a.depth - b.depth || a.order - b.order);
    const values = new Map(layer.keys.map((id, index) => [id, index + 1]));
    for (let y = 0; y < layer.height; y++) {
      for (let x = 0; x < layer.width; x++) {
        const point = cellPoint(layer, x, y);
        if (!canPlace(point)) continue;
        for (const { polygon } of polygons) {
          if (inPolygon(point, polygon.points)) layer.cells[y * layer.width + x] = values.get(polygon.faction);
        }
      }
    }
  }
  layer.precision = { cellSizeMapUnits: step, sampling: 'cell-centre', clippedEdgeCells: true };
  layer.migration = { method: data.territories.length ? 'legacy-polygons-depth-first' : 'nearest-location-radius',
    polygonIds: data.territories.map(t => t.id), legacyPolygonsRetained: true };
  data.territoryGrid = validate(layer, data.factions, data.meta);
  return data;
}
