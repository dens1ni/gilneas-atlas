import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {normalizeData} from '../assets/js/model.mjs';
import {reconcileDraftPublication,previousPublicationFile} from '../assets/js/draft-publication.mjs';
const root=new URL('../',import.meta.url);
const read=async path=>JSON.parse(await readFile(new URL(path,root),'utf8'));

test('the family release has a distinct revision so existing Court drafts actually receive new people',async()=>{
  const current=await read('assets/data/publication-v5.json');
  const previous=await read('assets/data/publication-v4.json');
  const census=await read('docs/noble-family-census.json');
  assert.equal(current.meta.publicationRevision,'royal-council-v5');
  assert.notEqual(current.meta.publicationRevision,previous.meta.publicationRevision);
  const draft=structuredClone(previous);
  draft.locations.find(row=>row.id==='northgate-river').description='  Текст автора до семейного выпуска  ';
  draft.royalCouncil.members.find(row=>row.refId==='noble-genn').note='  Авторский протокол  ';
  draft.royalCouncil.influence={royalists:31,internationalists:27};
  draft.authorMetadata={literal:[0,'0',false,null,'  сохранено  ']};
  const original=structuredClone(draft);
  const result=normalizeData(reconcileDraftPublication(draft,current,previous));
  for(const addition of census.additions){
    assert.deepEqual(result.nobles.find(row=>row.id===addition.noble.id),addition.noble);
    assert.deepEqual(result.royalCouncil.members.find(row=>row.refId===addition.noble.id),addition.council);
  }
  assert.equal(result.locations.find(row=>row.id==='northgate-river').description,draft.locations.find(row=>row.id==='northgate-river').description);
  assert.equal(result.royalCouncil.members.find(row=>row.refId==='noble-genn').note,'  Авторский протокол  ');
  assert.deepEqual(result.royalCouncil.influence,draft.royalCouncil.influence);
  assert.deepEqual(result.authorMetadata,draft.authorMetadata);
  assert.deepEqual(result.territories,draft.territories);
  assert.deepEqual(draft,original);
  assert.deepEqual(reconcileDraftPublication(result,current,previous),result);
});

test('a family-era draft compares future releases against its own immutable family baseline',async()=>{
  assert.equal(previousPublicationFile({publicationRevision:'royal-council-v5'}),'publication-v5.json');
  const baseline=await read('assets/data/publication-v5.json');
  const current=await read('assets/data/publication-v5.json');
  assert.deepEqual(baseline,current,'The new baseline is a complete snapshot, not a recreated pre-family comparison');
  assert.equal(baseline.meta.publicationRevision,'royal-council-v5');
  const manifest=await read('assets/runtime-manifest.json');
  assert.ok(manifest.includes('assets/data/publication-v5.json'),'Family snapshots must remain downloadable in future full exports');
});

test('the distribution version identifies the Court and family release separately from Origins 1.2',async()=>{
  const metadata=await read('tests/fixtures/publication-v5-package.json');
  assert.equal(metadata.version,'1.3.0');
});

test('the approved authored-estates distribution packages its v6 snapshot, author seed and scenario helper',async()=>{
  const metadata=await read('package.json');
  assert.equal(metadata.version,'1.4.0');
  const manifest=await read('assets/runtime-manifest.json');
  for(const path of ['assets/data/publication-v6.json','assets/data/publication-author-v5.json','assets/js/scenario-publication.mjs']){
    assert.ok(manifest.includes(path),'Authored-estates migration input must remain in runtime exports: '+path);
  }
});
