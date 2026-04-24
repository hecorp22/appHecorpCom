// Mapa interactivo con draw (vía clic), puntos de interés (geocoder), trazado
// por OSRM, ETA, retraso estimado y guardado de ruta a /api/rutas.

const map = L.map('map', { zoomControl: true }).setView([18.8506, -97.0999], 12); // Orizaba
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap'
}).addTo(map);

// Geocoder (buscar direcciones / señalamientos)
L.Control.geocoder({ defaultMarkGeocode: false, placeholder: 'Buscar dirección o POI' })
  .on('markgeocode', (e) => {
    const c = e.geocode.center;
    map.setView(c, 15);
    const m = L.marker(c).addTo(map).bindPopup(e.geocode.name).openPopup();
    addWaypoint(c);
  }).addTo(map);

const waypointMarkers = [];       // markers dropables
let routing = L.Routing.control({
  waypoints: [],
  routeWhileDragging: true,
  show: false,
  addWaypoints: false,
  fitSelectedRoutes: true,
  router: L.Routing.osrmv1({ serviceUrl: 'https://router.project-osrm.org/route/v1' })
}).addTo(map);

let lastRoute = null;
routing.on('routesfound', (e) => {
  lastRoute = e.routes[0];
  const km = (lastRoute.summary.totalDistance / 1000).toFixed(2);
  const min = Math.round(lastRoute.summary.totalTime / 60);
  const eta = new Date(Date.now() + min * 60 * 1000);
  document.getElementById('info').innerHTML =
    `<b>Distancia:</b> ${km} km &middot; <b>Tiempo est.:</b> ${min} min<br>` +
    `<b>ETA:</b> ${eta.toLocaleString()}`;
});

function parseLatLng(s) {
  const parts = (s || '').split(',').map(x => x.trim());
  if (parts.length === 2) {
    const lat = parseFloat(parts[0]);
    const lng = parseFloat(parts[1]);
    if (!isNaN(lat) && !isNaN(lng)) return L.latLng(lat, lng);
  }
  return null;
}

function addWaypoint(latlng) {
  const m = L.marker(latlng, { draggable: true })
    .addTo(map)
    .bindPopup(`WP${waypointMarkers.length + 1}`);
  m.on('drag dragend', refreshRoute);
  m.on('contextmenu', () => { map.removeLayer(m);
    const i = waypointMarkers.indexOf(m); if (i >= 0) waypointMarkers.splice(i, 1);
    refreshRoute();
  });
  waypointMarkers.push(m);
  refreshRoute();
  syncOriDest();
}

function refreshRoute() {
  if (waypointMarkers.length >= 2) {
    routing.setWaypoints(waypointMarkers.map(m => m.getLatLng()));
  } else {
    routing.setWaypoints([]);
  }
}

function syncOriDest() {
  const ori = waypointMarkers[0]?.getLatLng();
  const des = waypointMarkers[waypointMarkers.length - 1]?.getLatLng();
  if (ori) document.getElementById('origen').value  = `${ori.lat.toFixed(6)},${ori.lng.toFixed(6)}`;
  if (des) document.getElementById('destino').value = `${des.lat.toFixed(6)},${des.lng.toFixed(6)}`;
}

// ubicación actual
document.getElementById('btnMiUbicacion')?.addEventListener('click', () => {
  if (!navigator.geolocation) return alert('Geolocalización no soportada');
  navigator.geolocation.getCurrentPosition((pos) => {
    const { latitude, longitude } = pos.coords;
    map.setView([latitude, longitude], 15);
    addWaypoint(L.latLng(latitude, longitude));
  }, (err) => alert('No se pudo obtener ubicación: ' + err.message), { enableHighAccuracy: true });
});

// click = agrega parada
map.on('click', (e) => addWaypoint(e.latlng));

// botón trazar (lee los inputs)
document.getElementById('btnRuta')?.addEventListener('click', () => {
  const ori = parseLatLng(document.getElementById('origen').value);
  const des = parseLatLng(document.getElementById('destino').value);
  if (ori) addWaypoint(ori);
  if (des) addWaypoint(des);
  if (waypointMarkers.length < 2) alert('Define al menos origen y destino (clic en el mapa o escribe lat,lng).');
});

// botón limpiar
document.getElementById('btnLimpiar')?.addEventListener('click', () => {
  waypointMarkers.forEach(m => map.removeLayer(m));
  waypointMarkers.length = 0;
  routing.setWaypoints([]);
  document.getElementById('info').innerText = '';
  document.getElementById('origen').value = '';
  document.getElementById('destino').value = '';
  lastRoute = null;
});

// botón guardar ruta
document.getElementById('btnGuardar')?.addEventListener('click', async () => {
  if (!lastRoute) return alert('Traza una ruta primero.');
  const nombre = prompt('Nombre de la ruta:', 'Ruta ' + new Date().toLocaleDateString());
  if (!nombre) return;
  const wp = lastRoute.waypoints || [];
  const coords = lastRoute.coordinates.map(c => [c.lng, c.lat]);
  const payload = {
    nombre,
    origen_lat: wp[0].latLng.lat,
    origen_lng: wp[0].latLng.lng,
    destino_lat: wp[wp.length - 1].latLng.lat,
    destino_lng: wp[wp.length - 1].latLng.lng,
    distancia_km: +(lastRoute.summary.totalDistance / 1000).toFixed(3),
    duracion_min: Math.round(lastRoute.summary.totalTime / 60),
    geojson: { type: 'Feature', properties: { name: nombre },
               geometry: { type: 'LineString', coordinates: coords } },
    notas: null,
  };
  try {
    const r = await fetch('/api/rutas', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!r.ok) { const t = await r.text(); alert('Error: ' + t); return; }
    const d = await r.json();
    alert('Ruta guardada #' + d.id);
  } catch(e) { alert('Error: ' + e.message); }
});
