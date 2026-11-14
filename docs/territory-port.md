# Actual Naitroud territory port

Reference: Naitroud `origin/main`, commit `7df478262e6c84553f44d60bc31397be6da54ee9`, bundled `assets/app.js`.

- Engine `territory-engine.js`: lines 1–66, nearest-location radius generation and circular paint.
- `installSmoothTerritories`: lines 4095–4628, shared planar interfaces (including owner 0), flowing/Chaikin knots, topology safeguards, Catmull–Rom cubic controls, exact control reversal, face incidence, SVG/Path2D, dependency-free serialized Blob worker.
- `territories.js`: lines 4776–5125 and pointer/history controls 5643–5757. Only paint, erase and camera are ported; no front/region subsystems.

## Parent integration (no app/UI/export/CSS changes made by this port)

```js
import { prepareTerritoryGrid, initTerritories } from './territories.mjs';
let boundaries;

// After the inactive mask has loaded. This returns an immutable normalized
// snapshot, preserves existing territoryGrid, and does NOT write a draft.
baseline = prepareTerritoryGrid(baseline, baselineCanPlace);
data = prepareTerritoryGrid(data, canPlace);

// Add this callback to the existing UI context. No arguments required.
onRenderTerritories: () => boundaries?.render()

boundaries = initTerritories({
  getData: () => data,        // stable live snapshot reference, not a fresh clone
  replaceData: commit,       // normalize -> saveDraft -> swap -> ui.render
  ui, canPlace, toast
});
await boundaries.whenReady(); // first real worker result AND SVG DOM are ready
window.gilneasApp.boundaries = boundaries;
// Only now expose gilneasApp.ready=true.

// Route just the editor launch action; keep editor.openTerritories() available
// as the legacy polygon form/import fallback.
onOpenTerritories: () => boundaries.open()
```

For legacy JSON import/reset, call `prepareTerritoryGrid(next, nextCanPlace)` before committing/swapping. A mask callback for a different incoming map must sample using **that incoming snapshot's dimensions**; the current app's closure may still reference the outgoing snapshot. Baseline/reset preparation is in memory, never a page-load save. Do not call a second commit merely to initialize the controller.

Register these four runtime modules in the parent export/Pages manifest:

- `assets/js/territory-engine.mjs` (also imported by `model.mjs`)
- `assets/js/territory-data.mjs`
- `assets/js/smooth-territories.mjs`
- `assets/js/territories.mjs`

The panel uses existing `iron-panel`, `panel-head`, `iron-button`, `brass-button`, `square` classes and `boundary-tools`, `boundary-body`, `boundary-actions` hooks. All new IDs start `boundary-`; required controls are `boundary-tools/faction/mode/brush/radius/generate/undo/redo/clear/save/close/status`. Overlay IDs: `boundary-vector`, `boundary-brush-preview`, `boundary-brush-cursor`. Parent CSS owns panel positioning/responsiveness. No magnified raw canvas is used: both overlay and changed-cell preview are SVG.

## API

- `prepareTerritoryGrid(data, canPlace=()=>true, {step=16,radius=260}={}) -> normalized cloned snapshot`
- `initTerritories({getData,replaceData,ui,canPlace,toast}) -> controller`
- controller: `render()`, optional `render({included:Set|null, visible:boolean})`, `open()`, `close()`, `whenReady() -> Promise<performance>`, `ready` promise getter, `getGrid() -> clone`, `getPerformance() -> clone`, `destroy()`.
- engine: `generate(locations,factions,radius,meta,canPlace,step)`, `validate(grid,factions,meta,{clone=true})`, `paint(privateGrid,x,y,radius,value,canPlace,onChange) -> changed count`, `cellPoint(grid,column,row)`.
- geometry: `geometry(grid)`, `geometryAsync(grid)`, `paths(grid,chains?,ownerMap?)`, `contours(grid,value)`, `SmoothTerritories` installer API.

## Snapshot and precision

`territoryGrid={version:1,width,height,step,mapWidth,mapHeight,keys,cells,radius,...extensions}`. Width/height count cells, not map pixels. For 3247×4860 at step 16 this is 203×304 = **61,712 cells**; last-cell centres and frame endpoints are clipped to exact dimensions. Cell sampling is documented in `precision`; old polygon IDs/order are recorded in `migration`, and the original `data.territories` array remains unchanged. Deeper descendants override ancestor polygons, while later equal-depth polygons preserve author precedence. Empty polygon collections use the source nearest-seed/radius algorithm. No +5.5 marker offset.

Geometry uses one shared graph. Root exterior unions remap ownership on those same curves. Vassals retain their own fill/color and a subtle continuous outline; sovereign bands are clipped inward. Physical smoothing thresholds scale with `layer.step/8`, including 0.04×scale flattening tolerance. Owner 0 holes remain holes.

Grid schema validation runs before cell cloning/storage, caps allocations at 131,072 cells, validates literal faction keys and cell/radius/dimension bounds, and preserves JSON extension/provenance fields. Missing grids remain missing in `normalizeData`, so existing polygon snapshots remain backward compatible. Deleting grid-painted owners is rejected; unused keys can be removed with lossless index remapping. Newly added keys are appended to the controller's private registry on rebuild without repainting cells.

Strokes mutate only a private working grid and SVG preview, interpolate using the source brush sampler, then make **one** validated immutable commit on pointerup. Camera/selection updates retain SVG nodes and never serialize cells to a worker. Geometry requests coalesce until pointerup and ignore stale revisions. Undo/redo/clear/generation/save are real atomic commits; incoming grid replacement cancels pending brush state and old history. Two-finger touch cancels the temporary first-finger brush and hands the active pointer to the real UI pinch handler; Alt/Command and camera mode use the existing camera API.

## Verification commands

```sh
node --test tests/new-territory*.test.mjs
/Users/daniil_si/.hermes/cache/scratch/gilneas-venv/bin/python tests/test_territory_revision.py -v
node --check assets/js/territory-engine.mjs
node --check assets/js/territory-data.mjs
node --check assets/js/smooth-territories.mjs
node --check assets/js/territories.mjs
```

Browser tests exercise the real Gilneas DOM/UI, native pointer capture/paint/erase, undo/redo, local JSON reload, mask cells, camera modes, CDP two-finger pinch, actual Path2D coverage/holes/checkerboard incidence/reversed cubics, same-curve root union, cached nodes, immutable location CRUD, registry changes and stale worker results. Only parent bootstrap is routed out; no production lore is replaced. Scratch performance evidence is under `/Users/daniil_si/.hermes/cache/scratch/gilneas-territory-evidence/` and `/Users/daniil_si/.hermes/cache/scratch/gilneas-territory-cpu.json`.
