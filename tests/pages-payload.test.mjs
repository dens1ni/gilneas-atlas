import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';

// A live Pages export fetches every manifest member from the published root.
test('Pages publish payload keeps every file requested by browser ZIP export', async()=>{
  const root=new URL('../',import.meta.url);
  const workflow=await readFile(new URL('.github/workflows/deploy-pages.yml',root),'utf8');
  const body=workflow.split('      - name: Prepare static publish root\n')[1]?.split('      - name: Upload Pages artifact')[0];
  assert.ok(body,'Publishing step must be discoverable');
  const script=body.split('        run: |\n')[1].split('\n').filter(line=>line.trim()).map(line=>line.replace(/^          /,'')).join('\n');
  const scratch=await mkdtemp(join(tmpdir(),'gilneas-pages-payload-'));
  try {
    const result=spawnSync('bash',['-e','-c',script.replaceAll('_site',JSON.stringify(join(scratch,'_site')))],{cwd:root,encoding:'utf8'});
    assert.equal(result.status,0,result.stderr);
    const files=JSON.parse(await readFile(new URL('assets/runtime-manifest.json',root),'utf8'));
    for(const name of files)assert.deepEqual(await readFile(join(scratch,'_site',name)),await readFile(new URL(name,root)),`Export file missing/changed in Pages payload: ${name}`);
  } finally { await rm(scratch,{recursive:true,force:true}); }
});
