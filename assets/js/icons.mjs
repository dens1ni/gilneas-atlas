export const icons = {
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  'chevron-left':'<path d="m14 5-7 7 7 7"/>',
  'chevron-up':'<path d="m5 15 7-7 7 7"/>',
  'chevron-down':'<path d="m5 9 7 7 7-7"/>',
  star:'<path d="m12 2 3 6 7 .9-5 4.9 1.3 7-6.3-3.4-6.3 3.4 1.3-7L2 8.9 9 8Z"/>',
  book:'<path d="M12 6C8 3 5 3 2 4v15c4-1 6 0 10 2 4-2 6-3 10-2V4c-3-1-6-1-10 2Zm0 0v15M5 8l4 1M5 12l4 1M16 9l3-1M16 13l3-1"/>',
  quill:'<path d="M4 20 9 8 20 3c2 7-2 11-9 12l-7 5ZM8 16 18 6M11 9l4 2M4 21l-2 1"/>',
  help:'<circle cx="12" cy="12" r="9"/><path d="M9 8a3 3 0 0 1 6 0c0 2-3 2-3 5M12 17h.01"/>',
  expand:'<path d="M4 9V4h5m6 0h5v5m0 6v5h-5M9 20H4v-5"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  upload:'<path d="M12 16V4m-5 5 5-5 5 5M4 16v5h16v-5"/>',
  layers:'<path d="m12 3 10 5-10 5L2 8l10-5Zm-10 9 10 5 10-5M2 16l10 5 10-5"/>',
  target:'<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 1v5m0 12v5M1 12h5m12 0h5"/>',
  shield:'<path d="M3 3h18v9c0 5-5 8-9 10-4-2-9-5-9-10V3Z"/><path d="m6 8 4 4 8-7"/>',
  crown:'<path d="m3 5 4 6 5-8 5 8 4-6-2 14H5L3 5ZM5 16h14"/>',
  building:'<path d="m2 10 10-7 10 7M4 9v12h16V9M9 21v-7h6v7M7 11h.01M17 11h.01"/>',
  fortress:'<path d="M3 21V5h4v3h3V5h4v3h3V5h4v16H3ZM9 21v-6a3 3 0 0 1 6 0v6M7 11h.01M17 11h.01"/>',
  tree:'<path d="m12 2-7 8h3l-5 6h7v6h4v-6h7l-5-6h3l-7-8Z"/>',
  harbor:'<path d="M12 3v16M8 5h8M5 12l-3 2c1 5 5 7 10 7s9-2 10-7l-3-2M12 2h.01"/>',
  mine:'<path d="m4 19 11-12M3 5c8-5 16-2 19 5M12 7l4 4"/>',
  resource:'<path d="m12 2 8 6-4 13H8L4 8l8-6ZM4 8h16M12 2 8 8l4 13 4-13-4-6Z"/>',
  scroll:'<path d="M5 4h13c4 0 4 6 0 6M5 4c-4 0-4 6 0 6h1v8c0 4 13 4 13 0V7M8 8h6M9 12h6M9 16h6"/>',
  rose:'<path d="M7 8C5 3 10 2 12 5c4-5 9-2 7 3 5 4 1 9-4 7-4 4-9 1-7-4-4 0-5-4-1-6ZM8 10c1-4 7-4 8-1 3 3-1 6-4 5-3 2-6-1-4-4Z"/><path d="M12 15v7m0-3-6-2m6 4 6-4"/>',
  trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>'
};
export function svgIcon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('viewBox','0 0 24 24');
  svg.setAttribute('aria-hidden','true');
  svg.innerHTML = icons[name] || icons.target;
  return svg;
}
export function decorateIcons(root = document) {
  root.querySelectorAll('[data-icon]').forEach(e => {
    if (!e.querySelector('svg')) e.append(svgIcon(e.dataset.icon));
  });
}
