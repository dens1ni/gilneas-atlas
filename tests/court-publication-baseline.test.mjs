import test from 'node:test';
import assert from 'node:assert/strict';
import * as publication from '../assets/js/draft-publication.mjs';

test('Origins drafts reconcile against the last Origins snapshot instead of the pre-Origins publication',()=>{
  assert.equal(typeof publication.previousPublicationFile,'function');
  assert.equal(publication.previousPublicationFile({publicationRevision:'origins-dossiers-v3'}),'publication-v3.json');
  assert.equal(publication.previousPublicationFile({publicationRevision:'faction-dossiers-v2'}),'publication-v2.json');
  assert.equal(publication.previousPublicationFile({}),'publication-v1.json');
  assert.equal(publication.previousPublicationFile({publicationRevision:'review-legacy-revision'}),'publication-v1.json');
});
