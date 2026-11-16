import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { reconcileDraftPublication, previousPublicationFile } from '../assets/js/draft-publication.mjs';
const clone = structuredClone;
const baseline = JSON.parse(fs.readFileSync(new URL('../assets/data/publication-v5.json', import.meta.url)));
const seedFile = new URL('../assets/data/publication-author-v5.json', import.meta.url);
const authorSeed = JSON.parse(fs.readFileSync(fs.existsSync(seedFile) ? seedFile : '/Users/daniil_si/.hermes/cache/scratch/gilneas-authored-v6/author-snapshot.json'));
const uuid = authorSeed.locations.find(record => !baseline.locations.some(old => old.id === record.id)).id;
function smallFixture() {
  const previous = clone(baseline);
  previous.locations = previous.locations.filter(record => ['gilneas-city', 'greymane-manor'].includes(record.id));
  const seed = clone(authorSeed);
  seed.locations = seed.locations.filter(record => ['gilneas-city', 'greymane-manor', uuid].includes(record.id));
  const incoming = clone(seed);
  incoming.meta.publicationRevision = 'authored-estates-v6';
  incoming.locations[0].description = 'Reviewed scenario description';
  incoming.locations[0].objects.push({id:'scenario-hall', name:'Scenario hall', type:'building', modifiers:[]});
  Object.assign(incoming.locations.find(record => record.id === uuid), {description:'Reviewed village description', faction:'walden', owner:'Lord Walden'});
  return {previous, seed, incoming};
}
test('v6 adopts reviewed full-snapshot fields using immutable v5 and the exact author seed', () => {
  const {previous, seed, incoming} = smallFixture();
  const draft = clone(seed), before = clone(draft);
  const result = reconcileDraftPublication(draft, incoming, previous, seed);
  assert.deepEqual(result.locations[0].objects, incoming.locations[0].objects);
  assert.equal(result.locations[0].description, incoming.locations[0].description);
  assert.equal(result.locations.find(record => record.id === uuid).faction, 'walden');
  assert.equal(result.locations[0].x, seed.locations[0].x);
  assert.deepEqual(result.territoryGrid, seed.territoryGrid);
  assert.deepEqual(draft, before);
});

function fullFixture() {
  const incoming = clone(authorSeed);
  incoming.meta.publicationRevision = 'authored-estates-v6';
  incoming.factions.push({id:'scenario-house', name:'Scenario house', parent:'gilneas', ruler:'Scenario lord'});
  for (const record of incoming.locations) {
    record.description = `Reviewed ${record.name}`;
    record.owner = 'Scenario lord';
    record.faction = 'scenario-house';
    record.type = 'estate';
    record.objects.push({id:`scenario-${record.id}`, name:'Scenario building', type:'building', modifiers:[{id:'bonus',kind:'bonus',text:'Reviewed bonus'}]});
  }
  incoming.sources.push({id:'scenario-evidence', title:'Scenario evidence', url:'https://example.org/scenario'});
  incoming.locations[0].sources = ['scenario-evidence'];
  incoming.locations[0].linkedLocationIds = [uuid];
  incoming.royalCouncil.members.find(member => member.kind === 'person').note = 'Reviewed personal note';
  return incoming;
}
test('pristine v5 adopts every release pin, owner, type and building; actual author snapshot keeps coordinates, grid and Wall', () => {
  const incoming = fullFixture();
  const pristine = reconcileDraftPublication(clone(baseline), incoming, baseline, authorSeed);
  assert.equal(pristine.locations.length, incoming.locations.length);
  for (const record of incoming.locations) assert.deepEqual(pristine.locations.find(item => item.id === record.id), record);
  const authored = reconcileDraftPublication(clone(authorSeed), incoming, baseline, authorSeed);
  for (const record of authorSeed.locations) {
    const actual = authored.locations.find(item => item.id === record.id);
    assert.equal(actual.x, record.x); assert.equal(actual.y, record.y);
    for (const object of record.objects) assert.deepEqual(actual.objects.find(item => item.id === object.id), object);
  }
  assert.deepEqual(authored.territoryGrid, authorSeed.territoryGrid);
  assert.deepEqual(authored.meta.wallConstruction, authorSeed.meta.wallConstruction);
  assert.deepEqual(reconcileDraftPublication(authored, incoming, baseline, authorSeed), authored);
});
test('absent author-seed pins never resurrect; removed custom old records and their buildings survive', () => {
  const incoming = fullFixture(), draft = clone(authorSeed);
  draft.locations = draft.locations.filter(record => record.id !== uuid);
  const retained = clone(baseline.locations.find(record => record.id === 'crowley-orchard'));
  retained.objects.push({id:'author-plot',name:'Author garden'});
  draft.locations.push(retained);
  const result = reconcileDraftPublication(draft, incoming, baseline, authorSeed);
  assert.ok(!result.locations.some(record => record.id === uuid));
  assert.deepEqual(result.locations.find(record => record.id === retained.id), retained);
  assert.ok(!result.locations[0].linkedLocationIds.includes(uuid));
});
test('UUID collisions do not acquire canonical ownership or links; custom descriptions and coordinates survive', () => {
  const incoming = fullFixture(), draft = clone(authorSeed);
  const record = draft.locations.find(record => record.id === uuid);
  record.description = 'Author description';
  const recognized = reconcileDraftPublication(draft, incoming, baseline, authorSeed);
  assert.equal(recognized.locations.find(item => item.id === uuid).description, 'Author description');
  record.x += 1;
  const collision = reconcileDraftPublication(draft, incoming, baseline, authorSeed);
  assert.deepEqual(collision.locations.find(item => item.id === uuid), record);
  assert.ok(!collision.locations[0].linkedLocationIds.includes(uuid));
});
test('nested object fields merge by typed identity while deleted modifiers, objects and optional registries remain absent', () => {
  const {previous, seed, incoming} = smallFixture();
  previous.locations[0].objects = [{id:'old-object',name:'Old',description:'Old text',modifiers:[{id:1,text:'Old modifier'}]}];
  seed.locations[0].objects = clone(previous.locations[0].objects);
  incoming.locations[0].objects = [{id:'old-object',name:'Published',description:'Published text',modifiers:[{id:1,text:'New modifier'},{id:'1',text:'New typed modifier'}]}];
  const draft = clone(seed);
  draft.locations[0].objects[0].description = 'Author text';
  draft.locations[0].objects[0].modifiers = [];
  delete draft.royalCouncil; delete draft.meta.wallConstruction; delete draft.meta.gilneasCrest;
  const result = reconcileDraftPublication(draft, incoming, previous, seed);
  assert.equal(result.locations[0].objects[0].name, 'Published');
  assert.equal(result.locations[0].objects[0].description, 'Author text');
  assert.deepEqual(result.locations[0].objects[0].modifiers, [{id:'1',text:'New typed modifier'}]);
  assert.ok(!Object.hasOwn(result, 'royalCouncil')); assert.ok(!Object.hasOwn(result.meta, 'wallConstruction')); assert.ok(!Object.hasOwn(result.meta, 'gilneasCrest'));
});
test('source conflicts are typed and atomic; deleted prior sources filter all new evidence', () => {
  const incoming = fullFixture(), draft = clone(authorSeed);
  draft.sources = draft.sources.filter(source => source.id !== 1);
  incoming.locations[0].sources = [1,'scenario-evidence'];
  const result = reconcileDraftPublication(draft, incoming, baseline, authorSeed);
  assert.deepEqual(result.locations[0].sources, ['scenario-evidence']);
  draft.sources.push({id:'scenario-evidence',url:'https://example.org/custom'});
  const before = clone(draft);
  assert.throws(() => reconcileDraftPublication(draft, incoming, baseline, authorSeed), /Source-ID conflict/);
  assert.deepEqual(draft, before);
  draft.sources.pop(); draft.sources.push({id:'1',url:'https://example.org/custom-numeric-string'});
  assert.equal(reconcileDraftPublication(draft, incoming, baseline, authorSeed).sources.find(source => source.id === '1').url, 'https://example.org/custom-numeric-string');
});
test('new faction collision fails closed before author records are modified', () => {
  const incoming = fullFixture(), draft = clone(authorSeed);
  draft.factions.push({id:'scenario-house',name:'Unrelated author house'});
  const before = clone(draft);
  assert.throws(() => reconcileDraftPublication(draft, incoming, baseline, authorSeed), /Faction-ID conflict/);
  assert.deepEqual(draft, before);
});
test('Council personal identity edits and deleted nobles cannot receive canonical appointments', () => {
  const {previous, seed, incoming} = smallFixture();
  const old = previous.royalCouncil.members.find(member => member.kind === 'person');
  const next = incoming.royalCouncil.members.find(member => member.id === old.id);
  next.note = 'New canonical note'; next.influence = 999;
  incoming.royalCouncil.influence = {royalists:999, internationalists:999};
  const draft = clone(seed), custom = draft.royalCouncil.members.find(member => member.id === old.id);
  custom.refId = 'author-person'; custom.note = old.note;
  const result = reconcileDraftPublication(draft, incoming, previous, seed);
  assert.deepEqual(result.royalCouncil.members.find(member => member.id === old.id), custom);
  assert.deepEqual(result.royalCouncil.influence, draft.royalCouncil.influence);
});
test('new releases do not bind locations to absent dependent factions or deleted seed evidence', () => {
  const {previous, seed, incoming} = smallFixture();
  seed.sources.push({id:'seed-evidence',url:'https://example.org/seed'});
  incoming.sources.push({id:'seed-evidence',url:'https://example.org/seed'});
  incoming.locations[0].provenance.sources = ['seed-evidence'];
  incoming.factions.push({id:'dangling-house',name:'Dangling',parent:'missing-parent'});
  incoming.locations.push({id:'dangling-place',name:'Dangling',type:'estate',x:1,y:1,faction:'dangling-house',owner:'Wrong owner',objects:[]});
  const result = reconcileDraftPublication(clone(seed), incoming, previous, seed);
  assert.ok(!result.locations.some(record => record.id === 'dangling-place'));
  const deleted = clone(seed); deleted.sources = deleted.sources.filter(record => record.id !== 'seed-evidence');
  const migrated = reconcileDraftPublication(deleted, incoming, previous, seed);
  assert.ok(!migrated.sources.some(record => record.id === 'seed-evidence'));
  assert.deepEqual(migrated.locations[0].provenance.sources, []);
});
test('independent custom fields do not match seed fallback by similarity; existing custom grids never change', () => {
  const {previous, seed, incoming} = smallFixture();
  seed.locations[0].owner = 'Seed owner'; incoming.locations[0].owner = 'Reviewed owner';
  const draft = clone(seed); draft.locations[0].owner = 'Seed owner (author)';
  draft.territoryGrid.customExtra = {literal:'preserve'};
  const before = clone(draft.territoryGrid);
  const result = reconcileDraftPublication(draft, incoming, previous, seed);
  assert.equal(result.locations[0].owner, 'Seed owner (author)');
  assert.deepEqual(result.territoryGrid, before);
  delete draft.territoryGrid; previous.territoryGrid = {cells:{custom:0},extra:'old'};
  assert.ok(!Object.hasOwn(reconcileDraftPublication(draft, incoming, previous, seed), 'territoryGrid'));
});
test('baseline people and objects stay deleted while unchanged Council notes adopt without changing ratings', () => {
  const {previous, seed, incoming} = smallFixture();
  previous.locations[0].objects = [{id:'deleted-object',name:'Old'}];
  seed.locations[0].objects = []; incoming.locations[0].objects.push({id:'deleted-object',name:'New'});
  const draft = clone(seed), deleted = previous.nobles[0].id;
  draft.nobles = draft.nobles.filter(record => record.id !== deleted);
  const person = incoming.royalCouncil.members.find(member => member.kind === 'person' && member.refId !== deleted);
  person.note = 'Reviewed personal note'; person.influence = {party:999,kingdom:999};
  const old = draft.royalCouncil.members.find(member => member.id === person.id);
  const result = reconcileDraftPublication(draft, incoming, previous, seed);
  assert.ok(!result.nobles.some(record => record.id === deleted));
  assert.ok(!result.locations[0].objects.some(record => record.id === 'deleted-object'));
  const actual = result.royalCouncil.members.find(member => member.id === person.id);
  assert.equal(actual.note, 'Reviewed personal note'); assert.deepEqual(actual.influence, old.influence);
});
test('v6 immutable baseline lookup does not fall back to v1', () => {
  assert.equal(previousPublicationFile({publicationRevision:'authored-estates-v6'}), 'publication-v6.json');
});
