import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {isDeepStrictEqual} from 'node:util';
import {reconcileDraftPublication} from '../assets/js/draft-publication.mjs';
import {normalizeData} from '../assets/js/model.mjs';
const read = name => JSON.parse(fs.readFileSync(new URL(`../assets/data/${name}.json`, import.meta.url)));
const previous = read('publication-v5'), seed = read('publication-author-v5'), actual = read('publication-v6');
const clone = structuredClone;
function fixture() {
  const incoming = clone(seed); incoming.meta.publicationRevision = 'authored-estates-v6';
  return {draft: clone(seed), incoming, previous: clone(previous), seed: clone(seed)};
}
function migrate(f) {
  normalizeData(f.draft);
  const before = clone(f);
  let result;
  try { result = reconcileDraftPublication(f.draft, f.incoming, f.previous, f.seed); }
  finally { assert.deepEqual(f, before, 'all migration inputs remain immutable'); }
  normalizeData(result);
  return result;
}
test('new own JSON prototype keys in metadata and existing records stay literal without pollution', () => {
  const f = fixture(), marker = 'scenarioSafetyPollution';
  const extension = JSON.parse(`{"__proto__":{"${marker}":"literal"},"constructor":{"prototype":{"value":"own"}},"prototype":{"value":"plain"},"extra":{"nested":true}}`);
  for (const record of [f.incoming.meta, f.incoming.locations[0]]) {
    for (const [key, value] of Object.entries(extension)) Object.defineProperty(record, key, {value: clone(value), enumerable: true, writable: true, configurable: true});
  }
  normalizeData(f.incoming);
  try {
    const result = migrate(f);
    assert.equal(Object.hasOwn(Object.prototype, marker), false, 'Object.prototype must not be written');
    for (const record of [result.meta, result.locations[0]]) {
      for (const key of Object.keys(extension)) {
        assert.equal(Object.hasOwn(record, key), true, `literal own ${key}`);
        assert.deepEqual(record[key], extension[key]);
      }
      assert.equal(Object.getPrototypeOf(record), Object.prototype);
      assert.deepEqual(JSON.parse(JSON.stringify(record)), record);
    }
  } finally { delete Object.prototype[marker]; }
});
test('absent seed pins stay deleted when every positive lineage signal is gone', () => {
  for (const empty of [true, false]) {
    const f = fixture();
    f.draft = clone(previous);
    if (empty) f.draft.locations = [];
    else f.draft.locations = f.draft.locations.filter(record => seed.locations.some(authored => authored.id === record.id));
    const remaining = new Set(f.draft.locations.map(record => record.id));
    for (const record of f.draft.locations) if (record.linkedLocationIds) record.linkedLocationIds = record.linkedLocationIds.filter(id => remaining.has(id));
    delete f.draft.territoryGrid;
    const result = migrate(f);
    const seedOnly = new Set(seed.locations.filter(record => !previous.locations.some(old => old.id === record.id)).map(record => record.id));
    assert.deepEqual(result.locations.filter(record => seedOnly.has(record.id)), [], 'unknown lineage cannot justify seed resurrection');
  }
});
test('deleting only the exact author grid never re-adopts the seed grid', () => {
  for (const empty of [false, true]) {
    const f = fixture(); delete f.draft.territoryGrid;
    if (empty) f.draft.locations = [];
    assert.equal(Object.hasOwn(migrate(f), 'territoryGrid'), false);
  }
});
test('seed-only nested object UUID with unrelated name and type receives no canonical fields', () => {
  const f = fixture(), loc = 'hayward-fishery';
  const object = f.draft.locations.find(record => record.id === loc).objects[0];
  object.name = 'Unrelated author property'; object.type = 'building';
  const released = f.incoming.locations.find(record => record.id === loc).objects[0];
  released.owner = 'Canonical owner'; released.description = 'Canonical description';
  released.faction = 'walden'; released.nobleId = f.seed.nobles[0].id;
  const result = migrate(f);
  assert.deepEqual(result.locations.find(record => record.id === loc).objects[0], object);
});
test('global model ID conflicts across object modifier and location paths fail atomically', () => {
  const add = (snapshot, kind, id, where) => {
    const loc = snapshot.locations.find(record => record.id === where);
    if (kind === 'location') snapshot.locations.push({id, name:'Custom place', type:'settlement', x:10, y:10, objects:[]});
    if (kind === 'object') loc.objects.push({id, name:'Custom building', type:'building', modifiers:[]});
    if (kind === 'modifier') loc.objects.push({id:`holder-${where}-${id}`, name:'Holder', type:'building', modifiers:[{id, kind:'bonus', text:'Custom'}]});
  };
  for (const [authorKind, releaseKind] of [['object','object'], ['modifier','modifier'], ['location','object'], ['object','location'], ['modifier','object'], ['object','modifier']]) {
    const f = fixture(), id = `safety-conflict-${authorKind}-${releaseKind}`;
    add(f.draft, authorKind, id, 'gilneas-city');
    add(f.incoming, releaseKind, id, 'greymane-manor');
    normalizeData(f.draft); normalizeData(f.incoming);
    const before = clone(f);
    assert.throws(() => reconcileDraftPublication(f.draft, f.incoming, f.previous, f.seed), /ID conflict.*safety-conflict/, `${authorKind}/${releaseKind}`);
    assert.deepEqual(f, before);
  }
});
test('new records retain raw own JSON prototype extensions as plain valid data', () => {
  const f = fixture();
  const added = {id:'safety-own-prototype', name:'Literal JSON place', type:'settlement', x:10, y:10, objects:[], ...JSON.parse('{"__proto__":{"literal":"kept"},"constructor":{"prototype":{"literal":"nested"}},"prototype":{"literal":"plain"}}')};
  f.incoming.locations.push(added);
  normalizeData(f.incoming);
  const record = migrate(f).locations.find(record => record.id === added.id);
  assert.deepEqual(record, added);
  assert.equal(Object.getPrototypeOf(record), Object.prototype);
  assert.equal(Object.hasOwn(record, '__proto__'), true);
});
test('reference-like metadata and provenance extension strings are never interpreted as model references', () => {
  const f = fixture();
  const raw = {parent:'raw parent', faction:'raw faction', owner:'raw owner', nobleId:'raw noble', representativeId:'raw representative', commanderId:'raw commander', house:'raw house', overlord:'raw overlord', nested:[{parent:'array parent', faction:'array faction'}]};
  f.incoming.meta.safetyRaw = clone(raw);
  f.incoming.locations[0].provenance.safetyRaw = clone(raw);
  f.incoming.locations[0].provenance.parent = 'direct provenance parent';
  f.incoming.locations.push({id:'safety-raw-metadata', name:'Metadata place', type:'settlement', x:10, y:10, objects:[], metadata:clone(raw)});
  const result = migrate(f);
  assert.deepEqual(result.meta.safetyRaw, raw);
  assert.deepEqual(result.locations[0].provenance.safetyRaw, raw);
  assert.equal(result.locations[0].provenance.parent, 'direct provenance parent');
  assert.deepEqual(result.locations.find(record => record.id === 'safety-raw-metadata').metadata, raw);
});
test('pristine immutable v5 and exact authored seed produce actual 86-pin content with exact grid-presence semantics', () => {
  assert.equal(actual.locations.length, 86);
  for (const draft of [previous, seed]) {
    const result = migrate({draft:clone(draft), incoming:clone(actual), previous:clone(previous), seed:clone(seed)});
    const expected=clone(actual);if(draft===previous)delete expected.territoryGrid;
    for(const key of Object.keys(expected))assert.ok(isDeepStrictEqual(result[key],expected[key]),`Approved ${key} content`);
    assert.deepEqual(Object.keys(result).sort(),Object.keys(expected).sort());
    assert.equal(Object.hasOwn(result,'territoryGrid'),draft===seed,'L01 seed prior presence preserves absent v5 grid');
    assert.ok(isDeepStrictEqual(reconcileDraftPublication(result, actual, previous, seed), result),'Complete migration idempotence');
  }
});
test('custom coordinates text optional deletions sources and independent pools remain literal', () => {
  const f = {draft:clone(seed), incoming:clone(actual), previous:clone(previous), seed:clone(seed)};
  const record = f.draft.locations.find(record => record.id === 'gilneas-city');
  record.x += 1; record.description = 'Author custom text';
  delete f.draft.meta.gilneasCrest;
  f.draft.royalCouncil.influence = {royalists:7, internationalists:11};
  f.draft.meta.wallConstruction.current = 33;
  const sources = clone(f.draft.sources), wall = clone(f.draft.meta.wallConstruction), pools = clone(f.draft.royalCouncil.influence);
  const result = migrate(f), updated = result.locations.find(item => item.id === 'gilneas-city');
  assert.equal(updated.x, record.x); assert.equal(updated.description, record.description);
  assert.equal(updated.owner, actual.locations.find(record => record.id === 'gilneas-city').owner);
  assert.equal(Object.hasOwn(result.meta, 'gilneasCrest'), false);
  assert.deepEqual(result.royalCouncil.influence, pools);
  assert.deepEqual(result.meta.wallConstruction, wall);
  for (const source of sources) assert.deepEqual(result.sources.find(record => record.id === source.id), source);
});
