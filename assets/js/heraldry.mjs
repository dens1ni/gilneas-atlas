const SVG_NS = 'http://www.w3.org/2000/svg';
const SHIELD_PATH = 'M1 1H59V46.4L30 71 1 46.4Z';
const NEUTRAL = '#87918d';
// Compatibility only: new factions must never inherit a sovereign's device.
const LEGACY_GILNEAN_IDS = new Set(['greymane', 'crowley', 'silverlaine', 'godfrey', 'ashbury', 'marley', 'walden']);
const color = value => /^#[0-9a-f]{6}$/i.test(value || '') ? value : NEUTRAL;

function imageReference(value) {
  if (typeof value !== 'string' || !value || value.startsWith('//')) return null;
  try {
    if (/[\u0000-\u0020\u007f\\<>"']/.test(decodeURIComponent(value))) return null;
    const url = new URL(value, document.baseURI);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || !/\.(png|webp|jpe?g|gif|avif|svg)$/i.test(url.pathname)) return null;
    return value;
  } catch { return null; }
}

/** Render a validated image reference, never inline author-controlled SVG. */
export function createFactionShield(snapshot, factionId, { className = '', id } = {}) {
  const royalHeraldry = snapshot?.meta?.gilneasHeraldry || {};
  const records = Array.isArray(snapshot?.factions) ? snapshot.factions.filter(record => record && typeof record.id === 'string') : [];
  const factions = new Map(records.map(faction => [faction.id, faction]));
  const legacy = !records.some(record => Object.hasOwn(record, 'heraldry'));
  const faction = factions.get(factionId);
  const heraldry = factionId === 'gilneas' && Object.hasOwn(royalHeraldry, 'symbol') ? royalHeraldry : faction?.heraldry || royalHeraldry;
  const visited = new Set();
  let ancestor = faction;
  let gilneas = false;
  while (ancestor && !visited.has(ancestor.id)) {
    visited.add(ancestor.id);
    if (ancestor.id === 'gilneas') { gilneas = true; break; }
    ancestor = factions.get(ancestor.parent);
  }
  const usesHeraldry = factionId === 'gilneas' || Boolean(faction?.heraldry) || (legacy && gilneas && LEGACY_GILNEAN_IDS.has(factionId));
  const field = factionId === 'gilneas' ? color(heraldry.field) : color(faction?.color);
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', '0 0 60 72');
  svg.setAttribute('class', `faction-shield${typeof className === 'string' && className ? ` ${className}` : ''}`);
  if (typeof id === 'string' && id) svg.setAttribute('id', id);
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  svg.dataset.color = field;
  if (typeof factionId === 'string') svg.dataset.factionId = factionId;
  const path = document.createElementNS(SVG_NS, 'path');
  path.setAttribute('class', 'shield-field');
  path.setAttribute('d', SHIELD_PATH);
  path.setAttribute('fill', field);
  path.setAttribute('stroke', usesHeraldry ? color(heraldry.edge) : NEUTRAL);
  path.setAttribute('stroke-width', '2');
  svg.append(path);
  const reference = usesHeraldry && imageReference(heraldry.symbol);
  if (reference) {
    const image = document.createElementNS(SVG_NS, 'image');
    image.setAttribute('class', 'shield-device');
    image.setAttribute('href', reference);
    image.setAttribute('x', '10');
    image.setAttribute('y', '8');
    image.setAttribute('width', '40');
    image.setAttribute('height', '44');
    image.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    image.dataset.deviceColor = color(heraldry.device);
    svg.append(image);
  }
  return svg;
}
