/*
 * Petekh service worker — "yüklənən tətbiq" (PWA) üçün.
 *
 * Prinsip: TƏZƏLİK əvvəldir. İnternet olanda HƏMİŞƏ serverdən götürürük
 * (istifadəçi köhnə versiyada "ilişib" qalmasın). İnternet yoxdursa,
 * yalnız onda keşdən veririk. API sorğuları HEÇ vaxt keşlənmir.
 */
const CACHE = "petekh-v2";
// Oflayn halda lazım olan minimal "qabıq" (app shell) + ikonlar.
const SHELL = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/icon-192.png",
  "/icon-512.png",
  "/apple-touch-icon.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // API (api.petekh.com) və başqa mənbələr — heç vaxt keşləmə, birbaşa şəbəkə.
  if (url.origin !== self.location.origin) return;

  // Naviqasiya / HTML — əvvəl şəbəkə, alınmasa keşdən (oflayn).
  const isNav = req.mode === "navigate" ||
    (req.headers.get("accept") || "").includes("text/html");
  if (isNav) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put("/index.html", copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match(req).then((r) => r || caches.match("/index.html")))
    );
    return;
  }

  // Statik fayllar (ikon/manifest) — əvvəl keş (sürətli), sonra şəbəkə.
  e.respondWith(
    caches.match(req).then((cached) =>
      cached ||
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        return res;
      }).catch(() => cached)
    )
  );
});
