const ROOT = new URL('../../', import.meta.url);
const DEFAULT_MIST = 'assets/maps/inactive-mist.webp';
const SVG_NS = 'http://www.w3.org/2000/svg';
const presentations = new WeakMap();

function vector(tag, attributes) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
  return node;
}

function mapDimensions(snapshot) {
  const meta = snapshot?.meta;
  if (!meta || !Number.isFinite(meta.width) || !Number.isFinite(meta.height) || meta.width <= 0 || meta.height <= 0) {
    throw new Error('Некорректные размеры карты');
  }
  return meta;
}

function resourceURL(value) {
  if (typeof value !== 'string' || !value || value !== value.trim() || /[\u0000-\u001f\u007f]/.test(value)) {
    throw new Error('Некорректный путь изображения карты');
  }
  const url = new URL(value, ROOT);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
      !/\.(png|webp|jpe?g|gif|avif|svg)$/i.test(url.pathname)) {
    throw new Error('Недопустимый URL изображения карты');
  }
  return url.href;
}

function mapResources(snapshot) {
  const { image, mist } = mapDimensions(snapshot);
  const baseURL = resourceURL(image);
  const mistURL = resourceURL(mist || DEFAULT_MIST);
  return { baseURL, mistURL, key: JSON.stringify([baseURL, mistURL]) };
}

function loadedImage(image, url) {
  return new Promise((resolve, reject) => {
    const done = () => {
      image.removeEventListener('load', done);
      image.removeEventListener('error', broken);
      if (image.naturalWidth > 0 && image.naturalHeight > 0) resolve(image);
      else reject(new Error(`Изображение карты недоступно: ${url}`));
    };
    const broken = () => {
      image.removeEventListener('load', done);
      image.removeEventListener('error', broken);
      reject(new Error(`Не удалось загрузить изображение карты: ${url}`));
    };
    image.addEventListener('load', done);
    image.addEventListener('error', broken);
    if (image.complete && image.getAttribute('src')) {
      if (image.naturalWidth > 0) done();
      else broken();
    }
  });
}

async function loadRaster(url) {
  const image = new Image();
  image.decoding = 'async';
  const loaded = loadedImage(image, url);
  image.src = url;
  await loaded;
  try {
    if (typeof image.decode === 'function') await image.decode();
  } catch {
    // Chromium can reject detached decode() for a valid large raster. A
    // readable one-pixel canvas after onload still proves raster readiness.
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 1;
    const context = canvas.getContext('2d');
    context.drawImage(image, 0, 0, 1, 1);
    context.getImageData(0, 0, 1, 1);
  }
  return image;
}

/** Initialize before fetching the publication; reveal only after geometry. */
export function initMapPresentation() {
  const world = document.getElementById('world');
  if (presentations.has(world)) return presentations.get(world);
  document.body.classList.add('map-awaiting');
  const loader = document.createElement('section');
  loader.id = 'map-loading';
  loader.setAttribute('role', 'status');
  loader.setAttribute('aria-live', 'polite');
  loader.setAttribute('aria-atomic', 'true');
  const rain = document.createElement('div');
  rain.className = 'map-loading-rain';
  rain.setAttribute('aria-hidden', 'true');
  const plate = document.createElement('div');
  plate.className = 'map-loading-plate';
  const crest = document.createElement('img');
  crest.className = 'map-loading-crest';
  crest.src = new URL('assets/ui/gilneas-royal-shield.svg', ROOT).href;
  crest.alt = '';
  const title = document.createElement('h2');
  title.textContent = 'Разворачиваем королевскую карту';
  const stage = document.createElement('p');
  stage.id = 'map-loading-stage';
  stage.textContent = 'Открываем королевский архив';
  const rose = document.createElement('img');
  rose.className = 'map-loading-rose';
  rose.src = new URL('assets/ui/rose.svg', ROOT).href;
  rose.alt = '';
  const retry = document.createElement('button');
  retry.type = 'button';
  retry.className = 'map-loading-retry';
  retry.textContent = 'Повторить загрузку';
  retry.hidden = true;
  retry.addEventListener('click', () => window.location.reload());
  plate.append(crest, title, stage, rose, retry);
  loader.append(rain, plate);
  document.body.append(loader);
  const cache = new Map();
  let ready = null;
  let active = null;

  async function prepare(snapshot) {
    const resources = mapResources(snapshot);
    let entry = cache.get(resources.key);
    if (!entry) {
      entry = { ...resources, ready: false };
      entry.promise = Promise.all([loadRaster(resources.baseURL), loadRaster(resources.mistURL)])
        .then(images => { entry.images = images; entry.ready = true; return entry; })
        .catch(error => {
          if (cache.get(resources.key) === entry) cache.delete(resources.key);
          throw error;
        });
      cache.set(resources.key, entry);
    }
    if (!active) {
      loader.dataset.state = 'loading';
      title.textContent = 'Разворачиваем королевскую карту';
      retry.hidden = true;
      stage.textContent = 'Загружаем карту и дымку неактивных земель';
      ready = null;
    }
    ready = await entry.promise;
    if (!active) stage.textContent = 'Карта загружена · готовим границы владений';
    return ready;
  }

  async function reveal() {
    if (!ready?.ready) throw new Error('Карта ещё не подготовлена');
    for (const [id, url] of [['base-map', ready.baseURL], ['mist-map', ready.mistURL]]) {
      const image = document.getElementById(id);
      if (!image || image.src !== url) throw new Error('Подготовленная карта ещё не отрисована');
      await loadedImage(image, url);
    }
    active = ready;
    loader.hidden = true;
    document.body.classList.remove('map-awaiting');
    return true;
  }

  function fail(error) {
    if (active) return false;
    ready = null;
    loader.hidden = false;
    loader.dataset.state = 'error';
    title.textContent = 'Не удалось развернуть карту';
    stage.textContent = String(error?.message || error || 'Проверьте соединение и повторите загрузку.');
    retry.hidden = false;
    document.body.classList.add('map-awaiting');
    return false;
  }

  function requirePrepared(snapshot) {
    const entry = cache.get(mapResources(snapshot).key);
    if (!entry?.ready) throw new Error('Изображения карты ещё не подготовлены');
    return entry;
  }

  function renderFrame(snapshot) {
    const { width, height } = snapshot.meta;
    let frame = document.getElementById('map-frame');
    if (!frame) {
      frame = vector('svg', { id: 'map-frame', 'aria-hidden': 'true', focusable: 'false' });
      world.append(frame);
    }
    frame.style.width = `${width}px`;
    frame.style.height = `${height}px`;
    frame.setAttribute('viewBox', `0 0 ${width} ${height}`);
    frame.setAttribute('width', width);
    frame.setAttribute('height', height);
    const edge = vector('rect', { class: 'map-frame-edge', x: 2, y: 2, width: width - 4, height: height - 4 });
    const outer = vector('rect', { class: 'map-frame-outer', x: 4, y: 4, width: width - 8, height: height - 8 });
    const inner = vector('rect', { class: 'map-frame-inner', x: 11, y: 11, width: width - 22, height: height - 22 });
    const corners = [[0, 0, 1, 1], [width, 0, -1, 1], [0, height, 1, -1], [width, height, -1, -1]].map(([x, y, sx, sy]) => {
      const corner = vector('g', { class: 'map-frame-corner', transform: `translate(${x} ${y}) scale(${sx} ${sy})` });
      corner.append(
        vector('path', { class: 'map-frame-flourish', d: 'M7 64V7H64M14 52V14H52M21 45V21H45M17 64C17 38 29 17 64 17M27 27C35 19 44 21 43 31C42 39 33 40 30 34C27 28 35 26 37 30' }),
        vector('path', { class: 'map-frame-rose', d: 'M17 18C14 13 18 10 22 14C24 8 30 11 30 16C37 14 39 20 34 24C39 30 32 35 27 31C23 36 17 33 17 28C11 28 11 21 17 18ZM21 21C22 17 28 17 30 21C34 24 30 29 26 27C22 30 18 25 21 21Z' }),
      );
      return corner;
    });
    frame.replaceChildren(edge, outer, inner, ...corners);
    return frame;
  }

  const presentation = { prepare, requirePrepared, reveal, fail, renderFrame };
  presentations.set(world, presentation);
  return presentation;
}
