import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { reconcileDraftPublication, previousPublicationFile } from '../assets/js/draft-publication.mjs';
import { reconcileScenarioPublication } from '../assets/js/scenario-publication.mjs';

const read = path => fs.readFileSync(new URL(path, import.meta.url), 'utf8');
const v6Text = read('../assets/data/publication-v6.json');
const v6 = JSON.parse(v6Text);
const authorSeed = JSON.parse(read('../assets/data/publication-author-v5.json'));
const clone = structuredClone;
const byId = (records, id) => records.find(record => record.id === id);

// The parent authors the real v7 snapshot; these tests never read or write it.
function fixture() {
  const previous = clone(v6), published = clone(previous);
  published.meta.publicationRevision = 'authored-estates-v7';
  Object.assign(published.locations[0], {owner:'Reviewed v7 owner', x:1813, y:3071});
  published.locations[0].objects.push({id:'v7-new-object', name:'Reviewed marker', type:'building', modifiers:[]});
  published.locations.push({id:'v7-new-location', name:'Reviewed estate', type:'estate', x:1200, y:2300, faction:'greymane', owner:'Reviewed v7 owner', objects:[]});
  return {previous, published, draft:clone(previous)};
}

test('v7 resolves its own immutable baseline while v6 keeps its v6 baseline', () => {
  assert.equal(previousPublicationFile({publicationRevision:'authored-estates-v7'}), 'publication-v7.json');
  assert.equal(previousPublicationFile({publicationRevision:'authored-estates-v6'}), 'publication-v6.json');
});

test('pristine v6 adopts v7 owner, coordinates and new markers through scenario reconciliation', () => {
  const {previous, published, draft} = fixture();
  const before = clone(draft), publicationBefore = clone(published);
  const result = reconcileDraftPublication(draft, published, previous, authorSeed);
  assert.equal(result.locations[0].owner, 'Reviewed v7 owner');
  assert.equal(result.locations[0].x, 1813);
  assert.equal(result.locations[0].y, 3071);
  assert.deepEqual(byId(result.locations[0].objects, 'v7-new-object'), byId(published.locations[0].objects, 'v7-new-object'));
  assert.deepEqual(byId(result.locations, 'v7-new-location'), byId(published.locations, 'v7-new-location'));
  assert.deepEqual(result, reconcileScenarioPublication(draft, published, previous, authorSeed));
  assert.equal(result.meta.publicationRevision, 'authored-estates-v7');
  assert.deepEqual(draft, before);
  assert.deepEqual(published, publicationBefore);
  assert.deepEqual(previous, v6);
  assert.equal(read('../assets/data/publication-v6.json'), v6Text);
});

test('custom v6 ownership, coordinates and record/field deletions survive v7', () => {
  const {previous, published, draft} = fixture();
  Object.assign(draft.locations[0], {owner:'Author owner', x:1700, y:2900});
  delete draft.locations[0].description;
  const removedObject = draft.locations[0].objects.shift().id;
  const removedLocation = draft.locations[1].id;
  draft.locations.splice(1, 1);
  const before = clone(draft);
  const result = reconcileDraftPublication(draft, published, previous, authorSeed);
  assert.equal(result.locations[0].owner, 'Author owner');
  assert.equal(result.locations[0].x, 1700);
  assert.equal(result.locations[0].y, 2900);
  assert.ok(!Object.hasOwn(result.locations[0], 'description'));
  assert.ok(!byId(result.locations[0].objects, removedObject));
  assert.ok(!byId(result.locations, removedLocation));
  assert.ok(byId(result.locations, 'v7-new-location'));
  assert.ok(byId(result.locations[0].objects, 'v7-new-object'));
  assert.deepEqual(draft, before);
});

test('new v7 council members append only with surviving or newly adopted references', () => {
  const {previous, published, draft} = fixture();
  const sourceId = previous.sources[0].id;
  published.nobles.push({id:'v7-new-noble', name:'Reviewed noble', house:'greymane', sources:[sourceId]});
  const additions = [
    {id:'v7-council-new-person', kind:'person', refId:'v7-new-noble', party:'neutral', sources:[sourceId]},
    {id:'v7-council-new-faction', kind:'faction', refId:'greymane', party:'neutral'},
    {id:'v7-council-invalid-person', kind:'person', refId:'missing-noble', party:'neutral'},
    {id:'v7-council-invalid-faction', kind:'faction', refId:'missing-faction', party:'neutral'},
    {id:'v7-council-deleted-person', kind:'person', refId:previous.nobles[0].id, party:'neutral'},
  ];
  published.royalCouncil.members.push(...additions);
  draft.nobles.shift();
  const deletedMember = draft.royalCouncil.members.shift().id;
  draft.royalCouncil.influence = {royalists:12, internationalists:34};
  const existingMember = clone(draft.royalCouncil.members[0]);
  const result = reconcileDraftPublication(draft, published, previous, authorSeed);
  assert.deepEqual(byId(result.nobles, 'v7-new-noble'), byId(published.nobles, 'v7-new-noble'));
  for (const member of additions.slice(0, 2)) assert.deepEqual(byId(result.royalCouncil.members, member.id), member);
  for (const member of additions.slice(2)) assert.ok(!byId(result.royalCouncil.members, member.id));
  assert.ok(!byId(result.royalCouncil.members, deletedMember));
  assert.deepEqual(byId(result.royalCouncil.members, existingMember.id), existingMember);
  assert.deepEqual(result.royalCouncil.influence, draft.royalCouncil.influence);
  assert.equal(result.royalCouncil.members.length, draft.royalCouncil.members.length + 2);
});

test('literal typed IDs remain distinct and deleted crest/heraldry/grid stay absent', () => {
  const {previous, published, draft} = fixture();
  const ids = [731, '731', '__proto__', 'constructor', 'literal.id'];
  const records = ids.map((id, i) => ({id, name:`Literal ${i}`, type:'building', description:'Old description', modifiers:[]}));
  previous.locations[0].objects.push(...clone(records));
  published.locations[0].objects.push(...records.map(record => ({...clone(record), description:'Reviewed description'})));
  draft.locations[0].objects.push(...clone(records));
  draft.locations[0].objects = draft.locations[0].objects.filter(record => record.id !== 731);
  delete draft.meta.gilneasCrest;
  delete draft.meta.gilneasHeraldry;
  delete draft.territoryGrid;
  const result = reconcileDraftPublication(draft, published, previous, authorSeed);
  assert.ok(!byId(result.locations[0].objects, 731));
  for (const id of ids.slice(1)) {
    const record = byId(result.locations[0].objects, id);
    assert.equal(record.id, id);
    assert.equal(record.description, 'Reviewed description');
  }
  assert.ok(!Object.hasOwn(result.meta, 'gilneasCrest'));
  assert.ok(!Object.hasOwn(result.meta, 'gilneasHeraldry'));
  assert.ok(!Object.hasOwn(result, 'territoryGrid'));
});

test('v6 and v7 dispatch identically to the tested scenario reconciler', () => {
  for (const revision of ['authored-estates-v6', 'authored-estates-v7']) {
    const {previous, published, draft} = fixture();
    previous.meta.publicationRevision = 'royal-council-v5';
    draft.meta.publicationRevision = 'royal-council-v5';
    published.meta.publicationRevision = revision;
    assert.deepEqual(reconcileDraftPublication(draft, published, previous, authorSeed), reconcileScenarioPublication(draft, published, previous, authorSeed));
  }
});

test('startup fetches the author seed for both v6 and v7 releases', async () => {
  const app = read('../assets/js/app.mjs');
  const start = app.indexOf('      let authorSeed;');
  const end = app.indexOf('      let next=reconcileDraftPublication', start);
  assert.ok(start >= 0 && end > start);
  const run = new Function('baseline', 'fetch', 'root', `return (async()=>{${app.slice(start, end)}return authorSeed;})();`);
  for (const revision of ['authored-estates-v6', 'authored-estates-v7']) {
    const requests = [];
    const result = await run({meta:{publicationRevision:revision}}, async (url, options) => {
      requests.push({url:String(url), options});
      return {ok:true, json:async()=>clone(authorSeed)};
    }, new URL('https://example.org/atlas/'));
    assert.deepEqual(result, authorSeed);
    assert.deepEqual(requests, [{url:'https://example.org/atlas/assets/data/publication-author-v5.json', options:{cache:'no-store'}}]);
  }
});

test('runtime manifest packages the new v7 baseline without replacing v6', () => {
  const manifest = JSON.parse(read('../assets/runtime-manifest.json'));
  for (const path of ['assets/data/publication-v6.json', 'assets/data/publication-v7.json', 'assets/data/publication-author-v5.json']) {
    assert.equal(manifest.filter(entry => entry === path).length, 1, path);
  }
});
