const map = L.map('map', { zoomControl: true }).setView([19.4326, -99.1332], 12);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap'
}).addTo(map);

const geocoder = L.Control.geocoder({ defaultMarkGeocode: false })
  .on('markgeocode', function(e) {
    const center = e.geocode.center;
    map.setView(center, 15);
    L.marker(center).addTo(map);
  }).addTo(map);

let markerOrigen = null, markerDestino = null;
let routing = L.Routing.control({
  waypoints: [],
  routeWhileDragging: true,
  show: false,
  router: L.Routing.osrmv1({ serviceUrl: 'https://router.project-osrm.org/route/v1' })
}).addTo(map);

routing.on('routesfound', function(e) {
  const r = e.routes[0];
  const km = (r.summary.totalDistance / 1000).toFixed(2);
  const min = Math.round(r.summary.totalTime / 60);
  document.getElementById('info').innerText = `Distancia: ${km} km · Tiempo: ${min} min`;
});

function parseLatLng(s) {
  const parts = (s || '').split(',').map(x => x.trim());
  if (parts.length === 2) {
    const lat = parseFloat(parts[0]);
    const lng = parseFloat(parts[1]);
    if (!isNaN(lat) && !isNaN(lng)) return [lat, lng];
  }
  return null;
}

const $origen = document.getElementById('origen');
const $destino = document.getElementById('destino');

document.getElementById('btnMiUbicacion').addEventListener('click', () => {
  if (!navigator.geolocation) return alert('Geolocalización no soportada');
  navigator.geolocation.getCurrentPosition((pos) => {
    const { latitude, longitude } = pos.coords;
    map.setView([latitude, longitude], 15);
    if (!markerOrigen) {
      markerOrigen = L.marker([latitude, longitude], { draggable: true }).addTo(map).bindPopup('Origen').openPopup();
    } else {
      markerOrigen.setLatLng([latitude, longitude]);
    }
    $origen.value = `${latitude.toFixed(6)},${longitude.toFixed(6)}`;
  }, (err) => alert('No se pudo obtener ubicación: ' + err.message), { enableHighAccuracy: true });
});

map.on('click', (e) => {
  const { lat, lng } = e.latlng;
  if (!markerOrigen) {
    markerOrigen = L.marker([lat, lng], { draggable: true }).addTo(map).bindPopup('Origen').openPopup();
  } else if (!markerDestino) {
    markerDestino = L.marker([lat, lng], { draggable: true }).addTo(map).bindPopup('Destino').openPopup();
  } else {
    markerDestino.setLatLng([lat, lng]);
  }
});

document.getElementById('btnRuta').addEventListener('click', () => {
  let ori = markerOrigen ? markerOrigen.getLatLng() : null;
  let des = markerDestino ? markerDestino.getLatLng() : null;
  if (!ori) {
    const p = parseLatLng($origen.value);
    if (p) ori = L.latLng(p[0], p[1]);
  }
  if (!des) {
    const p = parseLatLng($destino.value);
    if (p) des = L.latLng(p[0], p[1]);
  }
  if (!ori || !des) {
    alert('Define origen y destino.');
    return;
  }
  if (!markerOrigen) markerOrigen = L.marker(ori, { draggable: true }).addTo(map).bindPopup('Origen');
  if (!markerDestino) markerDestino = L.marker(des, { draggable: true }).addTo(map).bindPopup('Destino');
  routing.setWaypoints([ori, des]);
  map.fitBounds(L.latLngBounds([ori, des]), { padding: [60, 60] });
});

document.getElementById('btnLimpiar').addEventListener('click', () => {
  if (markerOrigen) { map.removeLayer(markerOrigen); markerOrigen = null; }
  if (markerDestino) { map.removeLayer(markerDestino); markerDestino = null; }
  routing.setWaypoints([]);
  document.getElementById('info').innerText = '';
  $origen.value = '';
  $destino.value = '';
});
