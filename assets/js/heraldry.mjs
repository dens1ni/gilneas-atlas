const SVG_NS = 'http://www.w3.org/2000/svg';
const SHIELD_PATH = 'M1 1H59V46.4L30 71 1 46.4Z';
const NEUTRAL = '#87918d';
const color = value => /^#[0-9a-f]{6}$/i.test(value || '') ? value : NEUTRAL;

function imageReference(value) {
  if (typeof value !== 'string' || !value || /[\u0000-\u0020\\]/.test(value) || value.startsWith('//')) return null;
  try {
    const url = new URL(value, document.baseURI);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || !/\.(png|webp|jpe?g|gif|avif|svg)$/i.test(url.pathname)) return null;
    return value;
  } catch { return null; }
}

/** Use only the supplied device, never a generated or borrowed coat of arms. */
export function createFactionShield(snapshot, factionId, { className = '', id } = {}) {
  const heraldry = snapshot.meta?.gilneasHeraldry || {};
  const factions = new Map((snapshot.factions || []).map(faction => [faction.id, faction]));
  const faction = factions.get(factionId);
  const visited = new Set();
  let ancestor = faction;
  let gilneas = false;
  while (ancestor && !visited.has(ancestor.id)) {
    visited.add(ancestor.id);
    if (ancestor.id === 'gilneas') { gilneas = true; break; }
    ancestor = factions.get(ancestor.parent);
  }
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
  path.setAttribute('stroke', gilneas ? color(heraldry.edge) : NEUTRAL);
  path.setAttribute('stroke-width', '2');
  svg.append(path);
  const reference = gilneas && imageReference(heraldry.symbol);
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
