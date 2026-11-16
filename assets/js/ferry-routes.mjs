const isRecord = value => value !== null && typeof value === 'object' && !Array.isArray(value);

/** Optional authored geometry; validation never seeds or rewrites a snapshot. */
export function validateFerryNetwork(snapshot, { claim } = {}) {
  if (!isRecord(snapshot)) throw new Error('Ожидается снимок атласа для паромных маршрутов');
  if (!isRecord(snapshot.meta) || !Object.hasOwn(snapshot.meta, 'ferryNetwork')) return true;
  const network = snapshot.meta.ferryNetwork;
  if (!isRecord(network)) throw new Error('Некорректное meta.ferryNetwork: ожидается запись сети паромных маршрутов');
  for (const field of ['image', 'mapRevision', 'width', 'height', 'routes']) {
    if (!Object.hasOwn(network, field)) throw new Error(`Отсутствует обязательное поле meta.ferryNetwork.${field}; укажите собственное значение JSON`);
  }
  if (typeof network.image !== 'string' || !network.image.length || network.image !== network.image.trim() ||
      /[\u0000-\u001f\u007f-\u009f]/.test(network.image)) {
    throw new Error('Некорректное meta.ferryNetwork.image: укажите непустую строку пути без краевых пробелов и управляющих символов');
  }
  if (typeof network.mapRevision !== 'string' || !network.mapRevision.length) {
    throw new Error('Некорректное meta.ferryNetwork.mapRevision: укажите непустую точную строку ревизии карты');
  }
  for (const field of ['width', 'height']) {
    if (!Number.isFinite(network[field]) || network[field] <= 0) {
      throw new Error(`Некорректное meta.ferryNetwork.${field}: укажите конечное положительное число размера карты`);
    }
  }
  if (!Array.isArray(network.routes)) throw new Error('Некорректное meta.ferryNetwork.routes: ожидается массив маршрутов; [] очищает сеть');
  if (network.routes.length > 64) throw new Error('Некорректное meta.ferryNetwork.routes: допустимо не более 64 паромных маршрутов');
  const routeIds = new Set();
  for (let index = 0; index < network.routes.length; index++) {
    const route = network.routes[index];
    const path = `meta.ferryNetwork.routes[${index}]`;
    if (!Object.hasOwn(network.routes, index) || !isRecord(route)) throw new Error(`Некорректное ${path}: ожидается собственная запись паромного маршрута`);
    for (const field of ['id', 'fromLocationId', 'toLocationId', 'points']) {
      if (!Object.hasOwn(route, field)) throw new Error(`Отсутствует обязательное поле ${path}.${field}; укажите собственное значение JSON`);
    }
    if (typeof route.id !== 'string' || route.id.length < 1 || route.id.length > 100) {
      throw new Error(`Некорректное ${path}.id: укажите точную строку ID длиной 1–100 символов`);
    }
    if (routeIds.has(route.id)) throw new Error(`Повтор ID в ${path}.id: ${route.id}; укажите уникальный ID маршрута`);
    routeIds.add(route.id);
    for (const field of ['fromLocationId', 'toLocationId']) {
      if (typeof route[field] !== 'string' || route[field].length < 1 || route[field].length > 100) {
        throw new Error(`Некорректное ${path}.${field}: укажите точную строку ID длиной 1–100 символов`);
      }
    }
    if (route.fromLocationId === route.toLocationId) {
      throw new Error(`${path}: fromLocationId и toLocationId должны указывать на разные переправы`);
    }
    if (!Array.isArray(route.points) || route.points.length < 2 || route.points.length > 4096) {
      throw new Error(`Некорректное ${path}.points: ожидается массив из 2–4096 пар координат`);
    }
    for (let pointIndex = 0; pointIndex < route.points.length; pointIndex++) {
      const point = route.points[pointIndex];
      if (!Object.hasOwn(route.points, pointIndex) || !Array.isArray(point) || point.length !== 2 ||
          !Object.hasOwn(point, 0) || !Object.hasOwn(point, 1) || !Number.isFinite(point[0]) || !Number.isFinite(point[1])) {
        throw new Error(`Некорректное ${path}.points[${pointIndex}]: ожидается пара из двух конечных чисел координат`);
      }
      if (point[0] < 0 || point[1] < 0 || point[0] > network.width || point[1] > network.height) {
        throw new Error(`${path}.points[${pointIndex}]: координаты вне границ сети 0…${network.width} × 0…${network.height}`);
      }
      const previous = route.points[pointIndex - 1];
      if (previous && point[0] === previous[0] && point[1] === previous[1]) {
        throw new Error(`${path}.points[${pointIndex}]: повтор одинаковых соседних точек; удалите одну из них`);
      }
    }
  }
  if (network.routes.length) {
    if (!Array.isArray(snapshot.locations)) throw new Error('Ожидается массив locations для ссылок паромных маршрутов');
    const byId = new Map();
    for (const location of snapshot.locations) {
      if (!isRecord(location)) continue;
      byId.set(location.id, byId.has(location.id) ? null : location);
    }
    for (let index = 0; index < network.routes.length; index++) {
      const route = network.routes[index];
      for (const field of ['fromLocationId', 'toLocationId']) {
        const path = `meta.ferryNetwork.routes[${index}].${field}`;
        const id = route[field];
        if (!byId.has(id)) throw new Error(`${path}: ID ${id} не найден в locations; укажите ID существующей переправы`);
        const location = byId.get(id);
        if (!location) throw new Error(`${path}: повтор ID ${id} в locations; ссылка неоднозначна`);
        if (location.type !== 'ferry') throw new Error(`${path}: локация ${id} должна иметь точный тип ferry`);
      }
    }
  }
  if (claim !== undefined) {
    if (typeof claim !== 'function') throw new Error('Некорректный claim паромных маршрутов: ожидается функция проверки общего пространства ID');
    for (const route of network.routes) claim(route, 'паромный маршрут');
  }
  return true;
}

const SVG_NS = 'http://www.w3.org/2000/svg';

/** View-only SVG projection; supplied world also allows DOM-free module imports. */
export function renderFerryNetwork(snapshot, world = document.getElementById('world')) {
  const existing = [...world.querySelectorAll('#ferry-routes')];
  const layer = existing.shift() ?? world.ownerDocument.createElementNS(SVG_NS, 'svg');
  for (const duplicate of existing) duplicate.remove();
  layer.replaceChildren();
  if (!isRecord(snapshot) || !isRecord(snapshot.meta)) throw new Error('Ожидается снимок атласа с записью meta для паромных маршрутов');
  const { width, height } = snapshot.meta;
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    throw new Error('Некорректные размеры текущей карты meta.width/meta.height: укажите конечные положительные числа');
  }
  for (const [name, value] of Object.entries({ id: 'ferry-routes', viewBox: `0 0 ${width} ${height}`,
    width, height, 'pointer-events': 'none', 'aria-hidden': 'true', focusable: 'false' })) {
    layer.setAttribute(name, String(value));
  }
  Object.assign(layer.style, { position: 'absolute', left: '0px', top: '0px',
    width: `${width}px`, height: `${height}px`, pointerEvents: 'none' });
  world.append(layer);
  // Validate before deriving any numeric points attribute; stale vectors are already cleared.
  validateFerryNetwork(snapshot);
  const network = Object.hasOwn(snapshot.meta, 'ferryNetwork') ? snapshot.meta.ferryNetwork : undefined;
  if (!network || network.image !== snapshot.meta.image || network.mapRevision !== snapshot.meta.mapRevision ||
      network.width !== width || network.height !== height || !network.routes.length) return layer;
  const byId = new Map(snapshot.locations.map(location => [location.id, location]));
  for (const route of network.routes) {
    const from = byId.get(route.fromLocationId);
    const to = byId.get(route.toLocationId);
    const first = route.points[0];
    const last = route.points[route.points.length - 1];
    // A moved dock invalidates this projection, not the author's stored geometry.
    if (!from || !to || first[0] !== from.x || first[1] !== from.y || last[0] !== to.x || last[1] !== to.y) continue;
    const points = route.points.map(point => point.join(',')).join(' ');
    for (const className of ['ferry-route-halo', 'ferry-route-line']) {
      const line = world.ownerDocument.createElementNS(SVG_NS, 'polyline');
      line.setAttribute('class', className);
      line.setAttribute('data-ferry-route', route.id);
      line.setAttribute('points', points);
      line.setAttribute('pointer-events', 'none');
      layer.append(line);
    }
  }
  return layer;
}
