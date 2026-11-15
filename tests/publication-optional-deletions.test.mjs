import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {normalizeData} from '../assets/js/model.mjs';
import {reconcileDraftPublication} from '../assets/js/draft-publication.mjs';

const read = name => JSON.parse(readFileSync(new URL(`../assets/data/${name}`, import.meta.url), 'utf8'));
const previous = read('publication-v4.json');
const published = read('atlas.json');
const v5 = read('publication-v5.json');
const previousNobleIds = new Set(previous.nobles.map(record => record.id));
const additions = published.nobles.filter(record => !previousNobleIds.has(record.id));

function authorDraft(baseline = previous) {
  const draft = structuredClone(baseline);
  const literal = {values: [0, '0', false, null, '  Авторский текст  ']};
  draft.authorExtensions = structuredClone(literal);
  draft.meta.authorExtensions = structuredClone(literal);
  draft.locations[0].description = '  Авторское описание места  ';
  draft.locations[0].authorExtensions = structuredClone(literal);
  draft.nobles[0].authorExtensions = structuredClone(literal);
  const step = 256;
  const width = Math.ceil(draft.meta.width / step), height = Math.ceil(draft.meta.height / step);
  draft.territoryGrid = {
    version: 1, width, height, step, mapWidth: draft.meta.width, mapHeight: draft.meta.height,
    radius: 80, keys: draft.factions.slice(0, 2).map(record => record.id),
    cells: Array.from({length: width * height}, (_, index) => index % 3),
    provenance: {sources: [draft.sources[0].id], note: '  Ручная сетка автора  '},
    authorExtensions: structuredClone(literal),
  };
  return draft;
}

function migrate(draft, baseline = previous, release = published) {
  const original = structuredClone(draft);
  const originalBaseline = structuredClone(baseline), originalRelease = structuredClone(release);
  normalizeData(draft); // The author input is a valid full snapshot before reconciliation.
  const result = normalizeData(reconcileDraftPublication(draft, release, baseline));
  assert.deepEqual(draft, original);
  assert.deepEqual(baseline, originalBaseline);
  assert.deepEqual(release, originalRelease);
  return result;
}

function verifyPreservationAndMigration(result, draft) {
  assert.deepEqual(published, v5);
  assert.equal(additions.length, 9);
  assert.equal(result.meta.publicationRevision, 'royal-council-v5');
  for (const record of additions) assert.deepEqual(result.nobles.find(row => row.id === record.id), record);
  assert.deepEqual(result.nobles.map(record => record.id), [...draft.nobles.map(record => record.id), ...additions.map(record => record.id)]);
  assert.deepEqual(result.authorExtensions, draft.authorExtensions);
  assert.deepEqual(result.meta.authorExtensions, draft.meta.authorExtensions);
  assert.deepEqual(result.locations[0].authorExtensions, draft.locations[0].authorExtensions);
  assert.equal(result.locations[0].description, draft.locations[0].description);
  assert.deepEqual(result.nobles[0].authorExtensions, draft.nobles[0].authorExtensions);
  assert.deepEqual(result.territoryGrid, draft.territoryGrid);
  assert.deepEqual(result.territories, draft.territories);
  const previousSourceIds = new Set(previous.sources.map(record => record.id));
  const draftSourceIds = new Set(draft.sources.map(record => record.id));
  const newSources = published.sources.filter(record => !previousSourceIds.has(record.id) && !draftSourceIds.has(record.id));
  assert.deepEqual(result.sources, [...draft.sources, ...newSources]); // Exact IDs retain their original number/string types.
  assert.deepEqual(normalizeData(reconcileDraftPublication(result, published, previous)), result);
  assert.deepEqual(normalizeData(reconcileDraftPublication(result, published, v5)), result);
}

test('a full v4 author draft keeps a deliberately deleted Council absent through normalized v5 migration', () => {
  assert.equal(Object.hasOwn(previous, 'royalCouncil'), true);
  const draft = authorDraft();
  delete draft.royalCouncil;
  const result = migrate(draft);
  assert.equal(Object.hasOwn(result, 'royalCouncil'), false);
  assert.deepEqual(result.meta.wallConstruction, draft.meta.wallConstruction);
  verifyPreservationAndMigration(result, draft);
});

test('a full v4 author draft keeps deliberately deleted wall progress and its event ledger absent', () => {
  assert.equal(Object.hasOwn(previous.meta, 'wallConstruction'), true);
  const draft = authorDraft();
  delete draft.meta.wallConstruction;
  const result = migrate(draft);
  assert.equal(Object.hasOwn(result.meta, 'wallConstruction'), false);
  assert.deepEqual(result.royalCouncil, published.royalCouncil);
  verifyPreservationAndMigration(result, draft);
  const release = structuredClone(published);
  release.meta.wallConstruction = {value: 13, max: 100, baseValue: 10, events: [
    {id: 'published-wall-event', name: 'Published work', delta: 3, effects: [], sources: [release.sources[0].id]},
  ]};
  normalizeData(release);
  assert.equal(Object.hasOwn(migrate(draft, previous, release).meta, 'wallConstruction'), false);
});

test('deleting both optional registries preserves both absences without blocking the nine new nobles', () => {
  const draft = authorDraft();
  delete draft.royalCouncil;
  delete draft.meta.wallConstruction;
  const result = migrate(draft);
  assert.equal(Object.hasOwn(result, 'royalCouncil'), false);
  assert.equal(Object.hasOwn(result.meta, 'wallConstruction'), false);
  verifyPreservationAndMigration(result, draft);
});

for (const missing of ['Council', 'wall', 'both']) {
  test(`first adoption still works when the previous publication also lacked ${missing}`, () => {
    const baseline = structuredClone(previous);
    if (missing !== 'wall') delete baseline.royalCouncil;
    if (missing !== 'Council') delete baseline.meta.wallConstruction;
    const draft = authorDraft(baseline);
    const result = migrate(draft, baseline);
    assert.deepEqual(result.royalCouncil, published.royalCouncil);
    assert.deepEqual(result.meta.wallConstruction, published.meta.wallConstruction);
    verifyPreservationAndMigration(result, draft);
  });
}

test('custom Council membership and a custom wall ledger remain literal while only new seats migrate', () => {
  const draft = authorDraft();
  draft.royalCouncil = {
    version: 1, influence: {royalists: 31, internationalists: 27},
    members: [{id: 'author-only-seat', kind: 'person', name: '  Авторский советник  ',
      party: 'neutral', stance: 'unknown', active: true, advisor: false, note: '  Свой протокол  ', sources: [draft.sources[0].id]}],
    authorExtensions: {literal: [0, '0', null]},
  };
  draft.meta.wallConstruction = {value: 43, max: 100, baseValue: 40, events: [
    {id: 'author-wall-event', name: '  Событие автора  ', description: '  Не менять  ', delta: 3, effects: [], sources: [draft.sources[0].id]},
  ], authorExtensions: {literal: [0, '0', null]}};
  const result = migrate(draft);
  assert.deepEqual(result.meta.wallConstruction, draft.meta.wallConstruction);
  assert.deepEqual(result.royalCouncil.influence, draft.royalCouncil.influence);
  assert.deepEqual(result.royalCouncil.authorExtensions, draft.royalCouncil.authorExtensions);
  const oldSeatIds = new Set(previous.royalCouncil.members.map(record => record.id));
  const newSeats = published.royalCouncil.members.filter(record => !oldSeatIds.has(record.id));
  assert.deepEqual(result.royalCouncil.members, [...draft.royalCouncil.members, ...newSeats]);
  verifyPreservationAndMigration(result, draft);
  const noPriorRegistries = structuredClone(previous);
  delete noPriorRegistries.royalCouncil;
  delete noPriorRegistries.meta.wallConstruction;
  const firstAdoption = migrate(draft, noPriorRegistries);
  assert.deepEqual(firstAdoption.royalCouncil, draft.royalCouncil);
  assert.deepEqual(firstAdoption.meta.wallConstruction, draft.meta.wallConstruction);
});

for (const field of ['gilneasCrest', 'crestSource']) {
  test(`metadata ${field} distinguishes an author deletion from absence before first adoption`, () => {
    const baseline = structuredClone(previous), release = structuredClone(published);
    if (field === 'crestSource') {
      baseline.meta[field] = {id: baseline.sources[0].id, note: '  Старый источник герба  '};
      release.meta[field] = {id: release.sources[0].id, note: '  Новый источник герба  '};
    }
    const draft = authorDraft(baseline);
    delete draft.meta[field];
    const result = migrate(draft, baseline, release);
    assert.equal(Object.hasOwn(result.meta, field), false);
    assert.deepEqual(normalizeData(reconcileDraftPublication(result, release, baseline)), result);
    delete baseline.meta[field];
    assert.deepEqual(migrate(draft, baseline, release).meta[field], release.meta[field]);
    draft.meta[field] = field === 'gilneasCrest' ? 'https://example.invalid/author.svg' : {id: draft.sources[0].id, note: '  Авторский источник  '};
    assert.deepEqual(migrate(draft, baseline, release).meta[field], draft.meta[field]);
  });
}

test('the explicit legacy banner exception still adopts the current crest', () => {
  const draft = authorDraft();
  draft.meta.gilneasCrest = 'assets/ui/gilneas-human-banner.png';
  const result = migrate(draft);
  assert.equal(result.meta.gilneasCrest, published.meta.gilneasCrest);
  verifyPreservationAndMigration(result, draft);
  const currentDraft = structuredClone(result);
  currentDraft.meta.gilneasCrest = 'assets/ui/gilneas-human-banner.png';
  assert.equal(normalizeData(reconcileDraftPublication(currentDraft, published, v5)).meta.gilneasCrest, published.meta.gilneasCrest);
});
