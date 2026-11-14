import test from 'node:test';
import assert from 'node:assert/strict';

const fixture = (width, height, cells, patch = {}) => ({ version: 1, width, height, step: 16,
  keys: ['test-root', 'test-house'], cells, radius: 260, ...patch });

test('ported shared-interface geometry honors snapshot step and the exact partial-cell frame', async () => {
  const S = await import('../assets/js/smooth-territories.mjs').catch(() => ({}));
  assert.equal(typeof S.geometry, 'function', 'port installSmoothTerritories rather than inventing independent paths');
  const layer = fixture(3, 2, [1, 1, 2, 1, 2, 2], { mapWidth: 35, mapHeight: 29 });
  const chains = S.geometry(layer);
  assert.ok(chains.length > 0);
  for (const chain of chains) {
    assert.ok(chain.segments.length);
    for (const s of chain.segments) for (const point of [s.a, s.b, s.c1, s.c2]) {
      assert.ok(point[0] >= 0 && point[0] <= 35 && point[1] >= 0 && point[1] <= 29, JSON.stringify(point));
    }
  }
  const paths = S.paths(layer, chains);
  assert.deepEqual(paths.map(p => p.key), layer.keys);
  assert.ok(paths.every(p => p.d.includes('C') && p.d.endsWith('Z')));
  const union = S.paths(layer, chains, [0, 1, 1]);
  assert.equal(union[1].d, '');
  assert.ok(union[0].d.includes('35 29'));
  const original = JSON.stringify(layer);
  S.geometry(layer);
  assert.equal(JSON.stringify(layer), original, 'geometry cannot edit ownership');
});
