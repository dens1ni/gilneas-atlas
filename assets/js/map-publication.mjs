import { normalizeData } from './model.mjs';
import { cellPoint, MAX_CELLS } from './territory-engine.mjs';

const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
const pointOf = record => [record.x, record.y];

/** Project a source-map point without rounding away author placement. */
export function projectMapPoint(point, matrix) {
  if (!Array.isArray(matrix) || matrix.length !== 3 || matrix.some(row => !Array.isArray(row) || row.length !== 3 || row.some(value => !Number.isFinite(value)))) {
    throw new Error('Неверная матрица переноса карты');
  }
  const [x, y] = point;
  if (!Number.isFinite(x) || !Number.isFinite(y)) throw new Error('Неверная точка переноса карты');
  const divisor = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2];
  if (!Number.isFinite(divisor) || Math.abs(divisor) < 1e-12) throw new Error('Точка не переносится на новую карту');
  return [(matrix[0][0] * x + matrix[0][1] * y + matrix[0][2]) / divisor,
          (matrix[1][0] * x + matrix[1][1] * y + matrix[1][2]) / divisor];
}

/** Explicit map-version boundary; never saves or discards an author's draft. */
export function reconcileMapPublication(draft, published, previous, matrix) {
  if (!published.meta.mapRevision || draft.meta.mapRevision === published.meta.mapRevision) return structuredClone(draft);
  if (draft.meta.width === published.meta.width && draft.meta.height === published.meta.height && draft.meta.image === published.meta.image) return structuredClone(draft);
  if (draft.meta.width !== previous.meta.width || draft.meta.height !== previous.meta.height || draft.meta.image !== previous.meta.image) {
    throw new Error('Карта черновика отличается от предыдущей основы. Сохранён ваш снимок; перенесите его вручную через резервную копию.');
  }
  const result = structuredClone(draft);
  const source = new Map(previous.locations.map(record => [record.id, record]));
  const destination = new Map(published.locations.map(record => [record.id, record]));
  for (const record of result.locations) {
    const before = source.get(record.id), after = destination.get(record.id);
    [record.x, record.y] = before && after && same(pointOf(record), pointOf(before))
      ? pointOf(after) : projectMapPoint(pointOf(record), matrix);
  }
  const oldTerritories = new Map(previous.territories.map(record => [record.id, record]));
  const newTerritories = new Map(published.territories.map(record => [record.id, record]));
  for (const territory of result.territories) {
    const before = oldTerritories.get(territory.id), after = newTerritories.get(territory.id);
    territory.points = before && after && same(territory.points, before.points)
      ? structuredClone(after.points) : territory.points.map(point => projectMapPoint(point, matrix));
  }
  for (const field of ['width', 'height', 'image', 'mist', 'inactiveMask', 'mapRevision', 'homeBounds', 'mapRegistration', 'enhancedWidth', 'enhancedHeight']) {
    if (Object.hasOwn(published.meta, field)) result.meta[field] = structuredClone(published.meta[field]);
  }
  const previousFactions = new Map(previous.factions.map(faction => [faction.id,faction]));
  for (const faction of result.factions) {
    const before = previousFactions.get(faction.id), after = published.factions.find(record => record.id===faction.id);
    if (before && after && faction.color===before.color) faction.color=after.color;
  }
  if (same(draft.meta.labels, previous.meta.labels)) result.meta.labels = structuredClone(published.meta.labels || []);
  else if (result.meta.labels) result.meta.labels = result.meta.labels.map(label => {
    const [x, y] = projectMapPoint(pointOf(label), matrix);
    return { ...label, x, y };
  });
  // A hand-painted ownership grid requires a separate lossless owner sampler.
  if (result.territoryGrid) result.territoryGrid = relocateTerritoryGrid(result.territoryGrid, published.meta, matrix);
  return normalizeData(result);
}

function relocateTerritoryGrid(grid, meta, matrix) {
  // Inverse nearest-owner sampling preserves deliberate unclaimed cells and
  // author colors. Never regenerate a painted map from location seeds.
  const [[a,b,c],[d,e,f],[g,h,i]] = matrix;
  const determinant = a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g);
  if (!Number.isFinite(determinant) || Math.abs(determinant) < 1e-12) throw new Error('Матрица карты необратима');
  const inverse = [[e*i-f*h,c*h-b*i,b*f-c*e],[f*g-d*i,a*i-c*g,c*d-a*f],[d*h-e*g,b*g-a*h,a*e-b*d]]
    .map(row => row.map(value => value/determinant));
  const width = Math.ceil(meta.width/grid.step), height = Math.ceil(meta.height/grid.step);
  if (width*height > MAX_CELLS) throw new Error('Новая сетка территорий слишком велика');
  const next = {...structuredClone(grid),width,height,mapWidth:meta.width,mapHeight:meta.height,cells:new Array(width*height).fill(0)};
  for (let y=0;y<height;y++) for (let x=0;x<width;x++) {
    const [oldX,oldY] = projectMapPoint(cellPoint(next,x,y),inverse);
    if (oldX<0 || oldY<0 || oldX>=(grid.mapWidth??grid.width*grid.step) || oldY>=(grid.mapHeight??grid.height*grid.step)) continue;
    next.cells[y*width+x] = grid.cells[Math.floor(oldY/grid.step)*grid.width+Math.floor(oldX/grid.step)];
  }
  next.mapMigration = {method:'inverse-cell-centre-owner-sampling',sourceWidth:grid.mapWidth??grid.width*grid.step,
    sourceHeight:grid.mapHeight??grid.height*grid.step,step:grid.step,unclaimedCellsPreserved:true};
  return next;
}
