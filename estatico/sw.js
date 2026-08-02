// Service worker mínimo. Existe por una sola razón: sin uno registrado, el
// navegador no ofrece instalar la app en la pantalla de inicio.
//
// NO CACHEA NADA, y es a propósito. La app vive en tu propia red, así que no
// hay latencia que compensar, y cachear sólo serviría para que el móvil
// enseñara versiones viejas justo después de tocar algo. Si algún día se
// quisiera que funcione con el ordenador apagado, eso es otra conversación.

self.addEventListener('install', function () {
  // Sin espera: la versión nueva sustituye a la vieja en cuanto llega.
  self.skipWaiting();
});

self.addEventListener('activate', function (evento) {
  evento.waitUntil(self.clients.claim());
});

// El navegador exige que exista un manejador de `fetch` para considerar la app
// instalable. Este no llama a `respondWith`, así que cada petición sigue su
// camino normal hasta el servidor. No tocar: en cuanto se responda desde aquí,
// se empieza a servir contenido viejo.
self.addEventListener('fetch', function () {
  /* a propósito, nada */
});
