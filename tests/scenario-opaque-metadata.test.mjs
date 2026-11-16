import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {isDeepStrictEqual} from 'node:util';
import {reconcileDraftPublication} from '../assets/js/draft-publication.mjs';
import {normalizeData} from '../assets/js/model.mjs';
const read = name => JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}.json`, import.meta.url)));
const old = read('publication-v5'), authored = read('publication-author-v5');
const clone = structuredClone;
const opaque = JSON.parse('{"parent":"literal parent","sources":["opaque",7,"7"],"sourceIds":["opaque"],"loreSources":[["opaque"]],"linkedLocationIds":["opaque"],"fieldSources":{"name":["opaque"],"nested":{"sources":["opaque"]}},"nested":[{"id":"opaque-id","sources":["opaque"],"parent":"opaque parent"}],"__proto__":{"sources":["opaque"]},"constructor":{"prototype":{"sourceIds":["opaque"]}},"prototype":{"sources":["opaque"]}}');
function fixture() {
  const seed = clone(authored), published = clone(seed);
  published.meta.publicationRevision = 'authored-estates-v6';
  return {draft:clone(seed), published, previous:clone(old), seed};
}
function migrate(f) {
  normalizeData(f.draft); normalizeData(f.published);
  const before = clone(f);
  const result = reconcileDraftPublication(f.draft, f.published, f.previous, f.seed);
  assert.deepEqual(f, before, 'all inputs immutable'); normalizeData(result);
  return result;
}
test('unchanged and custom opaque author seed extensions preserve every literal outside canonical paths', () => {
  for (const custom of [false, true]) {
    const f = fixture();
    for (const snapshot of [f.seed, f.published, f.draft]) {
      snapshot.meta.authorScenario = clone(opaque);
      snapshot.locations[0].provenance.authorScenario = clone(opaque);
      snapshot.locations[0].metadata = clone(opaque);
      snapshot.locations[0]['provenance.sources'] = ['opaque dotted path'];
      snapshot.nobles[0].fieldSources.authorScenario = ['opaque field name'];
      snapshot.nobles[0].fieldSources['lifeStatus.sources'] = ['opaque dotted field'];
    }
    if (custom) {
      f.draft.meta.authorScenario.sources.push('custom');
      f.draft.locations[0].provenance.authorScenario.sourceIds.push('custom');
    }
    const result = migrate(f);
    assert.deepEqual(result.meta.authorScenario, f.draft.meta.authorScenario);
    assert.deepEqual(result.locations[0].provenance.authorScenario, f.draft.locations[0].provenance.authorScenario);
    assert.deepEqual(result.locations[0].metadata, f.draft.locations[0].metadata);
    assert.deepEqual(result.locations[0]['provenance.sources'], ['opaque dotted path']);
    assert.deepEqual(result.nobles[0].fieldSources.authorScenario, ['opaque field name']);
    assert.deepEqual(result.nobles[0].fieldSources['lifeStatus.sources'], ['opaque dotted field']);
    assert.equal(Object.hasOwn(result.meta.authorScenario, '__proto__'), true);
    assert.equal(Object.getPrototypeOf(result.meta.authorScenario), Object.prototype);
    assert.equal(Object.hasOwn(Object.prototype, 'sources'), false);
  }
});
test('canonical evidence still filters deleted and retargeted exact sources without touching nearby opaque data', () => {
  const f = fixture();
  const ids = ['opaque-test-deleted', 'opaque-test-retargeted', 'opaque-test-kept'];
  for (const snapshot of [f.previous, f.seed, f.published, f.draft]) {
    snapshot.sources.push(...ids.map(id => ({id, title:id, url:`https://example.org/${id}`})));
  }
  f.draft.sources = f.draft.sources.filter(source => source.id !== ids[0]);
  f.draft.sources.find(source => source.id === ids[1]).url = 'https://author.example/retargeted';
  for (const snapshot of [f.seed, f.published, f.draft]) {
    snapshot.locations[0].sources = [];
    snapshot.locations[0].provenance.sources = [];
    snapshot.locations[0].loreSources = [];
    snapshot.nobles[0].sources = [];
    snapshot.nobles[0].provenance.sources = [];
    snapshot.nobles[0].fieldSources.lifeStatus = [];
    snapshot.nobles[0].relations = [{name:'Evidence relation', relation:'kin', sourceIds:[]}];
    snapshot.meta.chronicle = [{title:'Evidence', text:'Text', sources:[]}];
  }
  const loc = f.published.locations[0], noble = f.published.nobles[0];
  loc.sources = clone(ids); loc.provenance.sources = clone(ids); loc.loreSources = [clone(ids)];
  noble.sources = clone(ids); noble.provenance.sources = clone(ids);
  noble.fieldSources.lifeStatus = clone(ids); noble.relations[0].sourceIds = clone(ids);
  f.published.meta.chronicle[0].sources = clone(ids);
  const result = migrate(f), kept = [ids[2]];
  assert.deepEqual(result.locations[0].sources, kept);
  assert.deepEqual(result.locations[0].provenance.sources, kept);
  assert.deepEqual(result.locations[0].loreSources, [kept]);
  assert.deepEqual(result.nobles[0].sources, kept);
  assert.deepEqual(result.nobles[0].provenance.sources, kept);
  assert.deepEqual(result.nobles[0].fieldSources.lifeStatus, kept);
  assert.deepEqual(result.nobles[0].relations[0].sourceIds, kept);
  assert.deepEqual(result.meta.chronicle[0].sources, kept);
});

test('all canonical adopted evidence collections retain exact filtering while their extensions stay opaque', () => {
  const f = fixture(), ids = ['schema-deleted', 'schema-retargeted', 'schema-kept'];
  for (const snapshot of [f.previous, f.seed, f.published, f.draft]) snapshot.sources.push(...ids.map(id => ({id, title:id, url:`https://example.org/${id}`})));
  f.draft.sources = f.draft.sources.filter(source => source.id !== ids[0]);
  f.draft.sources.find(source => source.id === ids[1]).url = 'https://author.example/schema';
  const add = snapshot => {
    snapshot.locations[0].objects.push({id:'schema-object', name:'Evidence building', type:'building', modifiers:[], sources:[], provenance:{sources:[]}, metadata:clone(opaque)});
    snapshot.factions[0].provenance = {sources:[], authorScenario:clone(opaque)};
    snapshot.territories[0].provenance = {sources:[], authorScenario:clone(opaque)};
    snapshot.nobles[0].spouse = {name:'Evidence spouse', sourceIds:[], metadata:clone(opaque)};
    snapshot.nobles[0].localization = {sources:[], metadata:clone(opaque)};
    snapshot.royalCouncil.members[0].sources = [];
    snapshot.meta.wallConstruction = {max:100, value:0, baseValue:0, events:[{id:'schema-wall-event', name:'Evidence event', delta:0, sources:[], effects:[{id:'schema-wall-effect', kind:'bonus', text:'Evidence', sources:[], metadata:clone(opaque)}]}]};
  };
  for (const snapshot of [f.seed, f.published, f.draft]) add(snapshot);
  const obj = f.published.locations[0].objects.at(-1);
  obj.sources = clone(ids); obj.provenance.sources = clone(ids);
  f.published.factions[0].provenance.sources = clone(ids);
  f.published.territories[0].provenance.sources = clone(ids);
  f.published.nobles[0].spouse.sourceIds = clone(ids);
  f.published.nobles[0].localization.sources = clone(ids);
  f.published.royalCouncil.members[0].sources = clone(ids);
  f.published.meta.wallConstruction.events[0].sources = clone(ids);
  f.published.meta.wallConstruction.events[0].effects[0].sources = clone(ids);
  const result = migrate(f), kept = [ids[2]], object = result.locations[0].objects.at(-1);
  for (const refs of [object.sources, object.provenance.sources, result.factions[0].provenance.sources, result.nobles[0].spouse.sourceIds, result.nobles[0].localization.sources, result.royalCouncil.members[0].sources, result.meta.wallConstruction.events[0].sources, result.meta.wallConstruction.events[0].effects[0].sources]) assert.deepEqual(refs, kept);
  assert.deepEqual(result.territories, f.draft.territories, 'existing territory snapshots retain their pre-existing migration behavior');
  assert.deepEqual(object.metadata, opaque);
  assert.deepEqual(result.factions[0].provenance.authorScenario, opaque);
  assert.deepEqual(result.territories[0].provenance.authorScenario, opaque);
  assert.deepEqual(result.meta.wallConstruction.events[0].effects[0].metadata, opaque);
});

test('actual startup migration block preserves prior heraldry deletion and permits genuine legacy first adoption', async () => {
  const source = fs.readFileSync(new URL('../assets/js/app.mjs', import.meta.url), 'utf8');
  const block = source.slice(source.indexOf('  if(isDraft&&baseline.meta.publicationRevision'), source.indexOf('  const [baselineMask]'));
  assert.ok(block.includes('reconcileDraftPublication'), 'real unmodified startup block');
  const {previousPublicationFile} = await import('../assets/js/draft-publication.mjs');
  const {reconcileMapPublication} = await import('../assets/js/map-publication.mjs');
  const run = new Function('data', 'baseline', 'previousInput', 'seedInput', 'reconcileDraftPublication', 'previousPublicationFile', 'reconcileMapPublication', 'normalizeData', `return (async()=>{const isDraft=true,root=new URL('https://example.org/');const fetch=async url=>({ok:true,json:async()=>structuredClone(url.pathname.endsWith('publication-author-v5.json')?seedInput:previousInput)});const toast=message=>{throw Error(message)};${block}\nreturn data;})();`);
  for (const initial of [authored, old]) {
    const draft = clone(initial); delete draft.meta.gilneasHeraldry;
    const incoming = read('publication-v6');
    const result = await run(draft, incoming, old, authored, reconcileDraftPublication, previousPublicationFile, reconcileMapPublication, normalizeData);
    assert.equal(Object.hasOwn(result.meta, 'gilneasHeraldry'), false, 'prior presence means author deletion');
  }
  const previous = clone(old), draft = clone(old), incoming = clone(old);
  delete previous.meta.gilneasHeraldry; delete draft.meta.gilneasHeraldry;
  incoming.meta.publicationRevision = 'royal-council-v5-first-adoption-test';
  const result = await run(draft, incoming, previous, undefined, reconcileDraftPublication, previousPublicationFile, reconcileMapPublication, normalizeData);
  assert.deepEqual(result.meta.gilneasHeraldry, incoming.meta.gilneasHeraldry);
});

test('R09 seed-only prior heraldry presence preserves deletion in pure and actual startup without author lineage', async () => {
  const f = {draft:clone(old), previous:clone(old), seed:clone(authored), published:read('publication-v6')};
  delete f.draft.meta.gilneasHeraldry;
  delete f.previous.meta.gilneasHeraldry;
  assert.equal(Object.hasOwn(f.seed.meta, 'gilneasHeraldry'), true);
  for (const snapshot of Object.values(f)) normalizeData(snapshot);
  const before = clone(f);
  const source = fs.readFileSync(new URL('../assets/js/app.mjs', import.meta.url), 'utf8');
  const begin = source.indexOf('  if(isDraft&&baseline.meta.publicationRevision'), end = source.indexOf('  const [baselineMask]');
  assert.ok(begin >= 0 && end > begin, 'real unmodified startup block');
  const block = source.slice(begin, end);
  const {previousPublicationFile} = await import('../assets/js/draft-publication.mjs');
  const {reconcileMapPublication} = await import('../assets/js/map-publication.mjs');
  const run = new Function('data', 'baseline', 'previousInput', 'seedInput', 'reconcileDraftPublication', 'previousPublicationFile', 'reconcileMapPublication', 'normalizeData', `return (async()=>{const isDraft=true,root=new URL('https://example.org/');const fetch=async url=>({ok:true,json:async()=>structuredClone(url.pathname.endsWith('publication-author-v5.json')?seedInput:previousInput)});const toast=message=>{throw Error(message)};${block}\nreturn data;})();`);
  const pure = migrate(f);
  const startup = await run(f.draft, f.published, f.previous, f.seed, reconcileDraftPublication, previousPublicationFile, reconcileMapPublication, normalizeData);
  assert.deepEqual(f, before, 'all four actual inputs immutable');
  const observed = [pure, startup].map(result => Object.hasOwn(result.meta, 'gilneasHeraldry'));
  assert.deepEqual(observed, [false, false], 'seed-only prior presence preserves deletion in BOTH pure and startup');
  const expected = clone(f.published); delete expected.meta.gilneasHeraldry; delete expected.territoryGrid;
  for (const result of [pure, startup]) {
    normalizeData(result);
    assert.equal(Object.hasOwn(result,'territoryGrid'),false,'L01 seed-only prior grid presence preserves grid absence in pure and startup');
    for(const key of Object.keys(expected))assert.ok(isDeepStrictEqual(result[key],expected[key]),`All other published ${key} fields migrate unchanged`);
    assert.deepEqual(Object.keys(result).sort(),Object.keys(expected).sort());
  }
});
