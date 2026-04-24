/* HECORP · Reparto · Service Worker
 * Estrategia:
 *  - shell (HTML/CSS/JS/manifest/iconos): cache-first
 *  - GET /api/delivery?...     : network-first, fallback cache (entregas de hoy)
 *  - POST /api/delivery/track/<token>/ping : network-only; si falla, cola IDB
 *    (los pings se reintenta al volver online via 'sync' o mensaje del cliente)
 */
const CACHE_NAME = "hecorp-reparto-v3";
const SHELL = [
  "/static/driver-pwa/manifest.webmanifest",
  "/static/driver-pwa/icon-192.png",
  "/static/driver-pwa/icon-512.png",
  "https://cdn.tailwindcss.com",
];

self.addEventListener("install", (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE_NAME);
    await c.addAll(SHELL).catch(() => {});
    self.skipWaiting();
  })());
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)));
    self.clients.claim();
  })());
});

// IDB para cola de pings cuando no hay red
function openDb() {
  return new Promise((res, rej) => {
    const r = indexedDB.open("hecorp-reparto", 1);
    r.onupgradeneeded = () => {
      const db = r.result;
      if (!db.objectStoreNames.contains("ping_queue"))
        db.createObjectStore("ping_queue", { autoIncrement: true });
    };
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  });
}
async function enqueue(item) {
  const db = await openDb();
  return new Promise((res) => {
    const tx = db.transaction("ping_queue", "readwrite");
    tx.objectStore("ping_queue").add(item);
    tx.oncomplete = res;
  });
}
async function drain() {
  const db = await openDb();
  return new Promise((res) => {
    const tx = db.transaction("ping_queue", "readwrite");
    const store = tx.objectStore("ping_queue");
    const req = store.getAll();
    req.onsuccess = async () => {
      const items = req.result || [];
      for (const it of items) {
        try {
          const r = await fetch(it.url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: it.body,
          });
          if (!r.ok) throw new Error("HTTP " + r.status);
        } catch (e) {
          // si falla otra vez, dejamos en la cola
          return res(false);
        }
      }
      store.clear();
      tx.oncomplete = () => res(true);
    };
  });
}

self.addEventListener("message", (e) => {
  if (e.data === "drain-queue") {
    e.waitUntil(drain());
  }
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);

  // POST de ping del chofer: si offline, encola
  if (req.method === "POST" && url.pathname.startsWith("/api/delivery/track/") && url.pathname.endsWith("/ping")) {
    e.respondWith((async () => {
      try {
        return await fetch(req.clone());
      } catch (err) {
        const body = await req.clone().text();
        await enqueue({ url: req.url, body });
        return new Response(JSON.stringify({ queued: true, offline: true }),
                            { status: 202, headers: { "Content-Type": "application/json" } });
      }
    })());
    return;
  }

  // GET de la lista de entregas: network-first
  if (req.method === "GET" && url.pathname === "/api/delivery") {
    e.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        const c = await caches.open(CACHE_NAME);
        c.put(req, fresh.clone());
        return fresh;
      } catch (err) {
        const cached = await caches.match(req);
        if (cached) return cached;
        return new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } });
      }
    })());
    return;
  }

  // GET de la PWA del chofer (HTML): network-first, cache fallback
  if (req.method === "GET" && url.pathname.startsWith("/driver/")) {
    e.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        const c = await caches.open(CACHE_NAME);
        c.put(req, fresh.clone());
        return fresh;
      } catch (err) {
        const cached = await caches.match(req);
        return cached || new Response("Offline", { status: 503 });
      }
    })());
    return;
  }

  // shell estático: cache-first
  if (req.method === "GET" && (
        url.pathname.startsWith("/static/") ||
        url.origin === "https://cdn.tailwindcss.com" ||
        url.origin === "https://unpkg.com"
      )) {
    e.respondWith((async () => {
      const cached = await caches.match(req);
      if (cached) return cached;
      try {
        const fresh = await fetch(req);
        const c = await caches.open(CACHE_NAME);
        c.put(req, fresh.clone());
        return fresh;
      } catch (err) {
        return cached || new Response("", { status: 503 });
      }
    })());
    return;
  }

  // resto: pasar
});
