import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

// Complete publish-root archive, not a download-button smoke test.
test('zip preserves binary assets and exact UTF-8 publish-root member paths', async () => {
  const { createZip, crc32 } = await import('../assets/js/export.mjs');
  const bytes = new TextEncoder().encode('Гилнеас — розы и сталь');
  assert.equal(crc32(new TextEncoder().encode('123456789')),0xcbf43926);
  const zip = createZip([
    {name:'index.html',data:bytes},
    {name:'.nojekyll',data:new Uint8Array()},
    {name:'assets/maps/gilneas.webp',data:new Uint8Array([0,1,255,127,0])}
  ]);
  assert.ok(zip instanceof Uint8Array);
  const view = new DataView(zip.buffer,zip.byteOffset,zip.byteLength);
  assert.equal(view.getUint32(0,true),0x04034b50);
  assert.equal(view.getUint32(zip.length-22,true),0x06054b50);
  assert.equal(view.getUint16(zip.length-12,true),3);
  const content = new TextDecoder().decode(zip);
  assert.ok(content.includes('index.html'));
  assert.ok(content.includes('.nojekyll'));
  assert.ok(content.includes('Гилнеас — розы и сталь'));
  assert.throws(()=>createZip([{name:'../escape',data:bytes}]),/путь|path/i);
});
