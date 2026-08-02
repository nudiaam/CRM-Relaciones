// Captura por voz (paso 1). Graba en el móvil con MediaRecorder, guarda el
// audio en IndexedDB para no perderlo si el servidor no responde, y lo sube por
// fetch a /audio. Reintenta al abrir la app y al recuperar conexión. No cachea
// nada ni toca el service worker. En escritorio no hace nada: el botón sólo
// aparece en pantalla táctil.

(function () {
  'use strict';

  // ── ¿Se puede grabar aquí? Sólo móvil (puntero grueso) y con las piezas del
  //    navegador. Si no, el botón flotante no aparece. ─────────────────────
  function puedeGrabar() {
    return !!(
      window.matchMedia && matchMedia('(pointer: coarse)').matches
      && navigator.mediaDevices && navigator.mediaDevices.getUserMedia
      && window.MediaRecorder && window.indexedDB
    );
  }

  // ── La cola local en IndexedDB. Cada pendiente es {blob, mime, grabado}. ──
  var NOMBRE_BD = 'relaciones-voz';
  var ALMACEN = 'pendientes';

  function abrirBD() {
    return new Promise(function (ok, mal) {
      var pet = indexedDB.open(NOMBRE_BD, 1);
      pet.onupgradeneeded = function () {
        pet.result.createObjectStore(ALMACEN, { keyPath: 'id', autoIncrement: true });
      };
      pet.onsuccess = function () { ok(pet.result); };
      pet.onerror = function () { mal(pet.error); };
    });
  }

  function conAlmacen(modo, tarea) {
    return abrirBD().then(function (bd) {
      return new Promise(function (ok, mal) {
        var tx = bd.transaction(ALMACEN, modo);
        var res = tarea(tx.objectStore(ALMACEN));
        tx.oncomplete = function () { ok(res && res.result); };
        tx.onerror = function () { mal(tx.error); };
        tx.onabort = function () { mal(tx.error); };
      });
    });
  }

  function guardarPendiente(reg) {
    return conAlmacen('readwrite', function (almacen) { return almacen.add(reg); });
  }

  function borrarPendiente(id) {
    return conAlmacen('readwrite', function (almacen) { almacen.delete(id); });
  }

  function listarPendientes() {
    return abrirBD().then(function (bd) {
      return new Promise(function (ok, mal) {
        var pet = bd.transaction(ALMACEN, 'readonly').objectStore(ALMACEN).getAll();
        pet.onsuccess = function () { ok(pet.result || []); };
        pet.onerror = function () { mal(pet.error); };
      });
    });
  }

  // ── Elegir contenedor: Opus donde se pueda, y si no, lo que el móvil dé. ──
  function elegirMime() {
    var candidatos = [
      'audio/webm;codecs=opus', 'audio/ogg;codecs=opus',
      'audio/webm', 'audio/mp4', 'audio/aac'
    ];
    for (var i = 0; i < candidatos.length; i++) {
      if (MediaRecorder.isTypeSupported(candidatos[i])) return candidatos[i];
    }
    return '';
  }

  document.addEventListener('DOMContentLoaded', function () {
    prepararReproductor();  // la lista de /audios funciona sin poder grabar
    if (!puedeGrabar()) return;
    document.body.classList.add('puede-grabar');

    var caja = document.querySelector('[data-voz]');
    if (!caja) return;
    caja.hidden = false;

    var lanzar = caja.querySelector('[data-voz-lanzar]');
    var panel = caja.querySelector('[data-voz-panel]');
    var cerrar = caja.querySelector('[data-voz-cerrar]');
    var botonGrabar = caja.querySelector('[data-voz-grabar]');
    var estado = caja.querySelector('[data-voz-estado]');
    var tiempo = caja.querySelector('[data-voz-tiempo]');
    var reloj = caja.querySelector('[data-voz-reloj]');
    var cola = caja.querySelector('[data-voz-cola]');
    var colaTexto = caja.querySelector('[data-voz-cola-texto]');
    var reintentar = caja.querySelector('[data-voz-reintentar]');
    var cuenta = caja.querySelector('[data-voz-cuenta]');

    var grabadora = null;
    var trozos = [];
    var pista = null;
    var inicio = 0;
    var cronometro = null;
    var subiendo = false;

    function palabra(n) { return n < 10 ? '0' + n : '' + n; }

    function pintarReloj() {
      var seg = Math.floor((Date.now() - inicio) / 1000);
      reloj.textContent = palabra(Math.floor(seg / 60)) + ':' + palabra(seg % 60);
    }

    function abrirPanel(abrir) {
      panel.hidden = !abrir;
      lanzar.setAttribute('aria-expanded', abrir ? 'true' : 'false');
      lanzar.hidden = abrir;
      if (abrir) actualizarCola();
    }

    function marcarGrabando(si) {
      caja.dataset.grabando = si ? 'si' : 'no';
      botonGrabar.textContent = si ? 'Parar' : 'Grabar';
      tiempo.hidden = !si;
      estado.textContent = si
        ? 'Grabando… toca parar cuando termines.'
        : 'Toca grabar y habla.';
    }

    // ── Grabar / parar ─────────────────────────────────────────────────────
    function empezar() {
      var mime = elegirMime();
      navigator.mediaDevices.getUserMedia({ audio: true }).then(function (flujo) {
        pista = flujo;
        trozos = [];
        try {
          grabadora = mime ? new MediaRecorder(flujo, { mimeType: mime })
                           : new MediaRecorder(flujo);
        } catch (e) {
          grabadora = new MediaRecorder(flujo);
        }
        grabadora.ondataavailable = function (ev) {
          if (ev.data && ev.data.size) trozos.push(ev.data);
        };
        grabadora.onstop = function () { cerrarGrabacion(); };
        inicio = Date.now();
        grabadora.start();
        marcarGrabando(true);
        pintarReloj();
        cronometro = setInterval(pintarReloj, 500);
      }).catch(function () {
        estado.textContent = 'No se pudo acceder al micrófono.';
      });
    }

    function parar() {
      if (grabadora && grabadora.state !== 'inactive') grabadora.stop();
    }

    function cerrarGrabacion() {
      clearInterval(cronometro);
      var tipo = (grabadora && grabadora.mimeType) || 'audio/webm';
      var blob = new Blob(trozos, { type: tipo });
      if (pista) { pista.getTracks().forEach(function (t) { t.stop(); }); pista = null; }
      marcarGrabando(false);
      if (!blob.size) { estado.textContent = 'No se grabó nada. Prueba otra vez.'; return; }
      var reg = { blob: blob, mime: tipo, grabado: new Date(inicio).toISOString() };
      guardarPendiente(reg).then(function () {
        estado.textContent = 'Guardado. Subiendo…';
        return actualizarCola();
      }).then(subirTodo).catch(function () {
        estado.textContent = 'Guardado en el móvil. Se subirá luego.';
      });
    }

    // ── Subir la cola. Guarda primero, sube después: si el servidor no está,
    //    el audio ya está a salvo en el móvil y se reintenta más tarde. ──────
    function subirTodo() {
      if (subiendo) return Promise.resolve();
      if (navigator.onLine === false) return actualizarCola();
      subiendo = true;
      return listarPendientes().then(function (lista) {
        return lista.reduce(function (cadena, reg) {
          return cadena.then(function (cortado) {
            if (cortado) return true;               // hubo fallo de red: parar
            var ext = (reg.mime.indexOf('ogg') >= 0) ? '.ogg'
                    : (reg.mime.indexOf('mp4') >= 0 || reg.mime.indexOf('aac') >= 0) ? '.m4a'
                    : '.webm';
            var forma = new FormData();
            forma.append('archivo', reg.blob, 'voz' + ext);
            forma.append('grabado', reg.grabado);
            return fetch('/audio', { method: 'POST', body: forma }).then(function (res) {
              if (!res.ok) return false;            // el servidor contestó mal, pero contestó
              return res.json().then(function (d) {
                if (d && d.ok) return borrarPendiente(reg.id).then(function () { return false; });
                return false;
              });
            }).catch(function () { return true; }); // sin red: cortar y reintentar luego
          });
        }, Promise.resolve(false));
      }).then(function () {
        subiendo = false;
        return actualizarCola();
      }).catch(function () { subiendo = false; });
    }

    function actualizarCola() {
      return listarPendientes().then(function (lista) {
        var n = lista.length;
        if (cuenta) { cuenta.hidden = n === 0; cuenta.textContent = n; }
        cola.hidden = n === 0;
        if (n) {
          colaTexto.textContent = n === 1 ? '1 sin subir' : n + ' sin subir';
          if (caja.dataset.grabando !== 'si') estado.textContent = 'Toca grabar y habla.';
        }
      }).catch(function () {});
    }

    lanzar.addEventListener('click', function () { abrirPanel(true); });
    cerrar.addEventListener('click', function () {
      if (caja.dataset.grabando === 'si') return;   // no cerrar a media grabación
      abrirPanel(false);
    });
    botonGrabar.addEventListener('click', function () {
      if (caja.dataset.grabando === 'si') parar(); else empezar();
    });
    reintentar.addEventListener('click', subirTodo);

    addEventListener('online', subirTodo);
    actualizarCola().then(subirTodo);
  });

  // ── El reproductor de la lista de audios: un botón propio, sin control
  //    nativo. Un solo Audio compartido; al tocar otro, se para el anterior. ─
  function prepararReproductor() {
    var botones = document.querySelectorAll('[data-oir]');
    if (!botones.length) return;
    var sonido = new Audio();
    var activo = null;

    function soltar() {
      if (activo) { activo.textContent = 'Escuchar'; activo = null; }
    }
    sonido.addEventListener('ended', soltar);
    sonido.addEventListener('pause', function () { if (sonido.ended) soltar(); });

    botones.forEach(function (boton) {
      boton.addEventListener('click', function () {
        var fuente = boton.getAttribute('data-oir');
        if (activo === boton) { sonido.pause(); soltar(); return; }
        soltar();
        sonido.src = fuente;
        sonido.play().then(function () {
          activo = boton; boton.textContent = 'Parar';
        }).catch(function () { boton.textContent = 'No se pudo'; });
      });
    });
  }
})();
