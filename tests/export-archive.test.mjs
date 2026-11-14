import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createZip } from '../assets/js/export.mjs';

test('Python opens exported archive, verifies CRC and extracts all bytes without a wrapper directory', async ()=>{
  const path=await mkdtemp(join(tmpdir(),'gilneas-zip-validation-'));
  const entries=[{name:'index.html',data:'<!doctype html><h1>Гилнеас</h1>'},{name:'.nojekyll',data:''},{name:'assets/binary.webp',data:new Uint8Array([0,1,2,255,27,0])}];
  await writeFile(path+'/test.zip',createZip(entries));
  const output=execFileSync('python3',['-c',`import zipfile,json; z=zipfile.ZipFile('${path}/test.zip'); assert z.testzip() is None; assert z.namelist()==['index.html','.nojekyll','assets/binary.webp']; assert z.read('assets/binary.webp')==bytes([0,1,2,255,27,0]); assert z.read('index.html').decode('utf-8')=='<!doctype html><h1>Гилнеас</h1>'; print('CRC, UTF-8, binary and root paths verified')`],{encoding:'utf8'});
  assert.match(output,/verified/);
  await rm(path,{recursive:true,force:true});
});
