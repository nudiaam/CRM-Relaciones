/* ============================================================================
   Relaciones — grafo.js
   La portada: todas las personas en el espacio. Pasa el ratón o toca.

   Lee GET /api/grafo. No toca nada del backend.

   Se dibuja NÍTIDA y a resolución completa. Aquí no se finge el píxel: eso lo
   pone la tipografía de los nombres. Nada de lienzos a un tercio ni de
   transparencias escalonadas, que era lo que se comió la profundidad.

   Cómo se lee la red:
     - El tamaño de cada punto lo dice cuántas veces has apuntado algo de esa
       persona. La distancia a la cámara lo corrige, no lo sustituye.
     - Las líneas, de un píxel y casi invisibles. Una red se lee cuando está
       medio vacía.
     - Los círculos se exploran desde cuadrados. Al señalarlos se iluminan sus
       personas allí donde estén, sin cambiar la posición de nadie.
     - Los nombres sólo salen en el 40% más cercano a la cámara. Al señalar a
       alguien, sólo el suyo y los de quienes están conectados con él.
   ========================================================================== */

(function () {
  'use strict';

  var lienzo = document.getElementById('lienzo');
  var panel = document.getElementById('ficha');
  var panelContenido = document.getElementById('ficha-contenido');
  var entradaBuscar = document.getElementById('grafo-buscar');
  var resultadosNombre = document.getElementById('grafo-resultados');
  var botonLimpiar = document.getElementById('grafo-limpiar');
  var listaCirculos = document.getElementById('grafo-circulos');
  var botonTodos = document.getElementById('grafo-todos');
  var mensaje = document.getElementById('grafo-mensaje');
  if (!lienzo) return;

  var ctx = lienzo.getContext('2d');
  var raiz = document.documentElement;
  var quieto = matchMedia('(prefers-reduced-motion: reduce)').matches;

  var RADIO_DIRECTO_DENTRO = 220;
  var RADIO_DIRECTO_FUERA = 430;
  var RADIO_INDIRECTO_DENTRO = 500;
  var RADIO_INDIRECTO_FUERA = 700;
  var REPULSION = 16000;
  var LARGO_LAZO = 180;
  var LARGO_DIRECTO = 300;
  var CERCANIA_NOMBRES = 0.4;   // el 40% más cercano a la cámara
  var GIRO = 0.00087;           // una vuelta cada dos minutos a 60 fotogramas

  // tintas: en reposo y con alguien señalado
  var LINEA = 0.07, LINEA_TOCA = 0.5, LINEA_LEJOS = 0.05;
  var PUNTO_MIN = 0.35, APAGADO = 0.05;

  var nodos = [], aristas = [], porId = {}, circulos = [], marcas = [];
  var central = null;
  var A = 0, ALTO = 0, dpr = 1;
  // con tanto aire, la cámara tiene que estar lejos: si no, los de delante se
  // proyectan enormes y se salen de la pantalla
  var camZ = 1500, foco = 900;
  var rotX = -0.2, rotY = 0.35;
  var vistaX = 0, vistaY = 0;
  var movimiento = !quieto;
  var giro = GIRO;
  var circuloEnFoco = '', circuloFijado = '';
  var senalado = null, fijado = null;
  var arrastrando = false, tipoArrastre = 'mover', botonArrastre = 0;
  var movido = 0, ux = 0, uy = 0;

  /* ── cargar ───────────────────────────────────────────────────────────── */

  fetch('/api/grafo')
    .then(function (r) { return r.json(); })
    .then(montar)
    .catch(function () {
      if (!panelContenido) return;
      panelContenido.innerHTML = '<p class="vacio">No se han podido cargar las personas.</p>';
      panel.classList.add('visible');
    });

  function montar(d) {
    circulos = (d.circulos || []).slice().sort(function (a, b) {
      return a.orden - b.orden;
    });
    nodos = (d.personas || []).map(function (p, indice) {
      return {
        clave: 'p' + p.id,
        id: p.id,
        nombre: p.nombre,
        nombreCompleto: p.nombre_completo || p.nombre,
        color: p.color || null,
        circulo: p.circulo || null,
        circuloId: p.circulo_id == null ? null : String(p.circulo_id),
        notas: p.notas || 0,
        hablamos: p.hablamos || 'nunca',
        pendiente: p.pendiente || [],
        preguntar: p.preguntar || [],
        datos: p.datos || [],
        quedadas: p.quedadas || [],
        relaciones: p.relaciones || [],
        foto: !!p.foto,
        central: !!p.central,
        indice: indice,
        radio: 0,
        vecinos: []
      };
    });

    porId = {};
    nodos.forEach(function (n) { porId[n.clave] = n; });
    central = d.central_id == null ? null : porId['p' + d.central_id];
    if (!central) {
      central = nodos.find(function (n) { return n.central; }) || null;
    }

    aristas = [];
    (d.aristas || []).forEach(function (e) {
      var a = porId[e.a], b = porId[e.b];
      if (!a || !b || a === b) return;
      aristas.push({ a: a, b: b, tipo: e.tipo || 'persona' });
      a.vecinos.push(b);
      b.vecinos.push(a);
    });

    colocar();
    marcas = [];
    for (var m = 0; m < 72; m++) {
      marcas.push({ x: azar(), y: azar(), grande: m % 17 === 0 });
    }
    medir();
    prepararMandos();
    addEventListener('resize', medir);
    pintar();
    requestAnimationFrame(bucle);
  }

  /* ── colocación: se calcula una vez ───────────────────────────────────── */

  var semilla = 20260725;
  function azar() { return (semilla = semilla * 16807 % 2147483647) / 2147483647; }

  function colocar() {
    semilla = 20260725;

    function repartir(grupo, dentro, fuera) {
      grupo.forEach(function (n, indice) {
        var u = azar() * 2 - 1;
        var th = azar() * Math.PI * 2;
        var s = Math.sqrt(1 - u * u);
        var parte = grupo.length <= 1 ? 0.5 :
          Math.pow((indice + 1) / (grupo.length + 1), 0.72);
        n.radio = dentro + parte * (fuera - dentro);
        var r = n.radio * (0.94 + azar() * 0.12);
        n.x = r * s * Math.cos(th);
        n.y = r * u;
        n.z = r * s * Math.sin(th);
        n.vx = n.vy = n.vz = 0;
      });
    }

    if (central) {
      central.x = central.y = central.z = 0;
      central.vx = central.vy = central.vz = 0;
      central.radio = 0;
      repartir(nodos.filter(function (n) {
        return n !== central && n.circuloId !== null;
      }), RADIO_DIRECTO_DENTRO, RADIO_DIRECTO_FUERA);
      repartir(nodos.filter(function (n) {
        return n !== central && n.circuloId === null;
      }), RADIO_INDIRECTO_DENTRO, RADIO_INDIRECTO_FUERA);
    } else {
      repartir(nodos, 64, RADIO_INDIRECTO_FUERA);
    }

    var vueltas = nodos.length > 120 ? 220 : 420;
    for (var it = 0; it < vueltas; it++) {
      for (var i = 0; i < nodos.length; i++) {
        var a = nodos[i];
        for (var j = i + 1; j < nodos.length; j++) {
          var b = nodos[j];
          var dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z;
          var d2 = dx * dx + dy * dy + dz * dz + 0.01;
          var d = Math.sqrt(d2), f = REPULSION / d2;
          dx /= d; dy /= d; dz /= d;
          if (a !== central) {
            a.vx -= dx * f; a.vy -= dy * f; a.vz -= dz * f;
          }
          if (b !== central) {
            b.vx += dx * f; b.vy += dy * f; b.vz += dz * f;
          }
        }
      }
      aristas.forEach(function (e) {
        var dx = e.b.x - e.a.x, dy = e.b.y - e.a.y, dz = e.b.z - e.a.z;
        var d = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.01;
        var largo = e.tipo === 'directa' ? LARGO_DIRECTO : LARGO_LAZO;
        var f = (d - largo) * 0.012;
        dx /= d; dy /= d; dz /= d;
        if (e.a !== central) {
          e.a.vx += dx * f; e.a.vy += dy * f; e.a.vz += dz * f;
        }
        if (e.b !== central) {
          e.b.vx -= dx * f; e.b.vy -= dy * f; e.b.vz -= dz * f;
        }
      });
      nodos.forEach(function (n) {
        if (n === central) {
          n.x = n.y = n.z = 0;
          n.vx = n.vy = n.vz = 0;
          return;
        }
        var d = Math.sqrt(n.x * n.x + n.y * n.y + n.z * n.z) + 0.01;
        var f = (d - n.radio) * 0.05;
        n.vx -= n.x / d * f; n.vy -= n.y / d * f; n.vz -= n.z / d * f;
        n.vx *= 0.82; n.vy *= 0.82; n.vz *= 0.82;
        n.x += n.vx; n.y += n.vy; n.z += n.vz;
      });
    }
  }

  /* ── medidas ──────────────────────────────────────────────────────────── */

  function medir() {
    dpr = Math.min(devicePixelRatio || 1, 2);
    A = lienzo.clientWidth; ALTO = lienzo.clientHeight;
    lienzo.width = Math.max(1, Math.round(A * dpr));
    lienzo.height = Math.max(1, Math.round(ALTO * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    camZ = A < 720 ? 1900 : 1500;
  }

  /* ── tinta ────────────────────────────────────────────────────────────── */

  var RGB = '20,18,15';
  function tinta(a) { return 'rgba(' + RGB + ',' + a + ')'; }

  // El radio lo manda la historia con esa persona: cuantas más veces has
  // apuntado algo suyo, más grande. De 2 a 5 píxeles.
  function radioBase(n) {
    return n.central ? 5 : 2 + Math.min(Math.sqrt(n.notas) * 0.9, 3);
  }

  // Y la profundidad lo corrige, sin llegar a hincharlo: los puntos son
  // pequeños siempre. De 1.2 a 8 píxeles de radio en pantalla.
  function escala(n) { return Math.max(0.6, Math.min(n.k, 1.6)); }

  function radio(n) { return Math.max(1, radioBase(n) * escala(n)); }

  function proyectar() {
    var cx = Math.cos(rotX), sx = Math.sin(rotX);
    var cy = Math.cos(rotY), sy = Math.sin(rotY);
    nodos.forEach(function (n) {
      var x1 = n.x * cy - n.z * sy;
      var z1 = n.x * sy + n.z * cy;
      var y2 = n.y * cx - z1 * sx;
      var z2 = n.y * sx + z1 * cx;
      var zc = z2 + camZ;
      var k = foco / Math.max(zc, 60);
      n.px = A / 2 + vistaX + x1 * k;
      n.py = ALTO / 2 + vistaY + y2 * k;
      n.pz = zc;
      n.k = k;
    });
  }

  function activo() { return fijado || senalado; }

  function circuloActivo() {
    return circuloFijado || circuloEnFoco;
  }

  function enCirculo(n, id) {
    if (!id) return true;
    if (id === 'ninguno') return n.circuloId === null;
    return n.circuloId === id;
  }

  function ligado(n, a) {
    return n === a || a.vecinos.indexOf(n) !== -1;
  }

  /* ── dibujo ───────────────────────────────────────────────────────────── */

  function pintar() {
    RGB = getComputedStyle(raiz).getPropertyValue('--tinta-r').trim() || '20,18,15';
    ctx.clearRect(0, 0, A, ALTO);
    var a = activo();
    var circulo = circuloActivo();
    ctx.fillStyle = tinta(0.09);
    marcas.forEach(function (marca) {
      var x = Math.round(marca.x * A), y = Math.round(marca.y * ALTO);
      if (marca.grande) {
        ctx.strokeStyle = tinta(0.09);
        ctx.strokeRect(x - 2, y - 2, 5, 5);
      } else {
        ctx.fillRect(x, y, 1, 1);
      }
    });
    proyectar();

    // el corte de profundidad para los nombres: el 40% más cercano
    var fondos = nodos.map(function (n) { return n.pz; }).sort(function (x, y) {
      return x - y;
    });
    var corte = fondos.length
      ? fondos[Math.max(0, Math.floor(fondos.length * CERCANIA_NOMBRES) - 1)]
      : 0;

    // lazos: de un píxel y al borde de no verse
    // lazos: de un píxel y al borde de no verse
    ctx.lineWidth = 1;
    aristas.forEach(function (e) {
      var toca = a && (e.a === a || e.b === a);
      var delCirculo = circulo &&
        enCirculo(e.a, circulo) && enCirculo(e.b, circulo);
      ctx.beginPath();
      ctx.moveTo(e.a.px, e.a.py);
      ctx.lineTo(e.b.px, e.b.py);
      ctx.strokeStyle = tinta(
        a ? (toca ? LINEA_TOCA : LINEA_LEJOS) :
        circulo ? (delCirculo ? 0.32 : 0.025) : LINEA
      );
      ctx.stroke();
    });

    // personas: puntos pequeños y llenos, de lejos a cerca
    var enOrden = nodos.slice().sort(function (m, n) { return n.pz - m.pz; });
    enOrden.forEach(function (n) {
      var prof = 1 - Math.min(1, Math.max(0, (n.pz - camZ + 700) / 1400));
      var cerca = PUNTO_MIN + prof * (1 - PUNTO_MIN);
      var r = radio(n);

      ctx.beginPath();
      ctx.arc(n.px, n.py, r, 0, Math.PI * 2);
      if (a) ctx.fillStyle = tinta(ligado(n, a) ? 1 : APAGADO);
      else if (circulo) ctx.fillStyle = tinta(enCirculo(n, circulo) ? 1 : APAGADO);
      else ctx.fillStyle = tinta(cerca);
      ctx.fill();

      if (n.central || n === a) {
        ctx.strokeStyle = tinta(1);
        ctx.strokeRect(
          Math.round(n.px - r - 5),
          Math.round(n.py - r - 5),
          Math.round((r + 5) * 2),
          Math.round((r + 5) * 2)
        );
      }

      // el nombre: en reposo sólo los más cercanos; señalando, sólo los suyos
      var conNombre = n.central || (a ? ligado(n, a) :
        circulo ? enCirculo(n, circulo) : n.pz <= corte);
      if (!conNombre) return;
      ctx.font = '11px "Departure", ui-monospace, Consolas, monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = tinta((a || circulo) ? 1 : cerca);
      ctx.fillText(n.nombre, Math.round(n.px), Math.round(n.py + r + 8));
    });
  }

  function bucle() {
    if (movimiento && !arrastrando && !fijado) rotY += giro;
    pintar();
    requestAnimationFrame(bucle);
  }

  /* ── interacción ──────────────────────────────────────────────────────── */

  function xy(e) {
    var c = lienzo.getBoundingClientRect();
    return { x: e.clientX - c.left, y: e.clientY - c.top };
  }

  function buscar(mx, my) {
    var mejor = null, mejorD = 20;
    nodos.forEach(function (n) {
      var d = Math.hypot(n.px - mx, n.py - my) - radio(n);
      if (d < mejorD) { mejorD = d; mejor = n; }
    });
    return mejor;
  }

  function normalizar(s) {
    return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  function seleccionar(n) {
    fijado = n || null;
    senalado = null;
    verFicha(fijado);
    if (mensaje) {
      mensaje.textContent = n ? 'Seleccionada: ' + n.nombre : mensajeDelCirculo();
    }
  }

  function mensajeDelCirculo() {
    var id = circuloActivo();
    if (!id) return 'Toda la red';
    var c = circulos.find(function (circulo) {
      return String(circulo.id) === id;
    });
    var nombre = id === 'ninguno' ? 'Sin círculo' : (c ? c.nombre : 'Círculo');
    var cuantas = nodos.filter(function (n) { return enCirculo(n, id); }).length;
    return nombre + ': ' + cuantas + (cuantas === 1 ? ' persona' : ' personas');
  }

  function camaraInicial() {
    return A < 720 ? 1900 : 1500;
  }

  function cambiarZoom(cantidad) {
    camZ = Math.max(500, Math.min(2400, camZ + cantidad));
  }

  function moverVista(dx, dy) {
    var limiteX = Math.min(320, A * 0.3);
    var limiteY = Math.min(240, ALTO * 0.3);
    vistaX = Math.max(-limiteX, Math.min(limiteX, vistaX + dx));
    vistaY = Math.max(-limiteY, Math.min(limiteY, vistaY + dy));
  }

  function prepararMandos() {
    function coincidencias() {
      var busca = normalizar(entradaBuscar ? entradaBuscar.value.trim() : '');
      if (!busca) return [];
      return nodos.filter(function (persona) {
        return normalizar(persona.nombre + ' ' + persona.nombreCompleto)
          .indexOf(busca) !== -1;
      }).slice(0, 6);
    }

    function actualizarBusqueda() {
      if (!entradaBuscar || !resultadosNombre) return;
      var resultados = coincidencias();
      resultadosNombre.innerHTML = resultados.map(function (n) {
        return '<button type="button" role="option" data-persona="' + n.id + '">' +
          '<span>' + esc(n.nombre) + '</span>' +
          (n.circulo ? '<span class="donde">' + esc(n.circulo) + '</span>' : '') +
          '</button>';
      }).join('');
      resultadosNombre.hidden = !entradaBuscar.value.trim();
      if (botonLimpiar) botonLimpiar.hidden = !entradaBuscar.value;
    }

    function irAlNombre() {
      var resultados = coincidencias();
      if (!resultados.length) {
        if (mensaje) mensaje.textContent = 'No encuentro ese nombre';
        return;
      }
      seleccionar(resultados[0]);
      entradaBuscar.value = resultados[0].nombre;
      actualizarBusqueda();
      resultadosNombre.hidden = true;
    }

    if (entradaBuscar) {
      entradaBuscar.addEventListener('input', actualizarBusqueda);
      entradaBuscar.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          irAlNombre();
        }
      });
    }
    if (resultadosNombre) {
      resultadosNombre.addEventListener('click', function (e) {
        var boton = e.target.closest('[data-persona]');
        if (!boton) return;
        var n = porId['p' + boton.dataset.persona];
        if (!n) return;
        entradaBuscar.value = n.nombre;
        seleccionar(n);
        resultadosNombre.hidden = true;
        if (botonLimpiar) botonLimpiar.hidden = false;
      });
    }
    if (botonLimpiar) {
      botonLimpiar.addEventListener('click', function () {
        entradaBuscar.value = '';
        botonLimpiar.hidden = true;
        resultadosNombre.hidden = true;
        seleccionar(null);
        // Con el dedo no se devuelve el foco: abriría el teclado otra vez.
        if (!matchMedia('(pointer: coarse)').matches) entradaBuscar.focus();
      });
    }

    montarCirculos();

    var menos = document.getElementById('grafo-menos');
    var mas = document.getElementById('grafo-mas');
    var centrar = document.getElementById('grafo-centrar');
    var mover = document.getElementById('grafo-movimiento');
    var cerrar = document.getElementById('grafo-cerrar');

    if (menos) menos.addEventListener('click', function () { cambiarZoom(180); });
    if (mas) mas.addEventListener('click', function () { cambiarZoom(-180); });
    if (centrar) centrar.addEventListener('click', function () {
      rotX = -0.2;
      rotY = 0.35;
      vistaX = 0;
      vistaY = 0;
      camZ = camaraInicial();
      seleccionar(null);
    });
    if (mover) {
      mover.setAttribute('aria-pressed', String(movimiento));
      mover.textContent = movimiento ? 'Pausar' : 'Mover';
      mover.addEventListener('click', function () {
        movimiento = !movimiento;
        mover.setAttribute('aria-pressed', String(movimiento));
        mover.textContent = movimiento ? 'Pausar' : 'Mover';
      });
    }
    if (cerrar) cerrar.addEventListener('click', function () {
      seleccionar(null);
      lienzo.focus();
    });

    // Explorar la red se pliega. De fábrica: abierto en escritorio y cerrado
    // en pantalla estrecha, donde ocupaba casi toda la red.
    var plegar = document.getElementById('grafo-plegar');
    var mandos = document.querySelector('.grafo-mandos');
    if (plegar && mandos) {
      var signo = plegar.querySelector('[data-signo]');

      function estaPlegado() {
        var marca = mandos.dataset.plegado;
        if (marca) return marca === 'si';
        return matchMedia('(max-width: 640px)').matches;
      }

      function pintarPlegado() {
        var cerrado = estaPlegado();
        plegar.setAttribute('aria-expanded', String(!cerrado));
        if (signo) signo.textContent = cerrado ? '+' : '−';
      }

      plegar.addEventListener('click', function () {
        mandos.dataset.plegado = estaPlegado() ? 'no' : 'si';
        pintarPlegado();
      });
      addEventListener('resize', pintarPlegado);
      pintarPlegado();
    }
  }

  function montarCirculos() {
    if (!listaCirculos) return;
    var opciones = circulos.map(function (c) {
      return { id: String(c.id), nombre: c.nombre };
    });
    if (nodos.some(function (n) { return n.circuloId === null; })) {
      opciones.push({ id: 'ninguno', nombre: 'Sin círculo' });
    }
    listaCirculos.innerHTML = opciones.map(function (c) {
      var cuantas = nodos.filter(function (n) { return enCirculo(n, c.id); }).length;
      return '<button type="button" data-circulo="' + c.id + '" aria-pressed="false">' +
        '<span class="circulo-cuadrado" aria-hidden="true"></span>' +
        '<span>' + esc(c.nombre) + '</span><span class="circulo-cuenta">' +
        cuantas + '</span></button>';
    }).join('');

    function refrescarBotones() {
      listaCirculos.querySelectorAll('[data-circulo]').forEach(function (boton) {
        boton.setAttribute(
          'aria-pressed', String(boton.dataset.circulo === circuloFijado)
        );
      });
      if (mensaje && !activo()) mensaje.textContent = mensajeDelCirculo();
    }

    listaCirculos.querySelectorAll('[data-circulo]').forEach(function (boton) {
      boton.addEventListener('mouseenter', function () {
        circuloEnFoco = boton.dataset.circulo;
        refrescarBotones();
      });
      boton.addEventListener('mouseleave', function () {
        circuloEnFoco = '';
        refrescarBotones();
      });
      boton.addEventListener('focus', function () {
        circuloEnFoco = boton.dataset.circulo;
        refrescarBotones();
      });
      boton.addEventListener('blur', function () {
        circuloEnFoco = '';
        refrescarBotones();
      });
      boton.addEventListener('click', function () {
        circuloFijado = circuloFijado === boton.dataset.circulo
          ? '' : boton.dataset.circulo;
        circuloEnFoco = '';
        refrescarBotones();
      });
    });

    if (botonTodos) {
      botonTodos.addEventListener('click', function () {
        circuloFijado = '';
        circuloEnFoco = '';
        refrescarBotones();
        lienzo.focus();
      });
    }
  }

  // Dedos puestos ahora mismo. Uno gira; dos desplazan y, al separarse o
  // juntarse, hacen zoom.
  var toques = new Map();
  var pellizco = 0, centroX = 0, centroY = 0;

  function medirToques() {
    var puntos = Array.from(toques.values());
    var a = puntos[0], b = puntos[1];
    pellizco = Math.hypot(a.x - b.x, a.y - b.y);
    centroX = (a.x + b.x) / 2;
    centroY = (a.y + b.y) / 2;
  }

  // Tocar la red cierra el teclado: el campo de búsqueda suelta el foco.
  function soltarTeclado() {
    var dentro = document.activeElement;
    if (dentro && /^(INPUT|TEXTAREA)$/.test(dentro.tagName)) dentro.blur();
  }

  lienzo.addEventListener('pointerdown', function (e) {
    if (e.pointerType === 'mouse') {
      if ([0, 1, 2].indexOf(e.button) === -1) return;
      // Sólo con ratón: evita que arrastrar seleccione texto de la página.
      e.preventDefault();
      arrastrando = true; movido = 0;
      botonArrastre = e.button;
      tipoArrastre = e.button === 0 ? 'girar' : 'mover';
      var p = xy(e); ux = p.x; uy = p.y;
      lienzo.classList.add('arrastrando');
      lienzo.setPointerCapture(e.pointerId);
      return;
    }
    // Con el dedo no se cancela el evento. Cancelarlo impedía que el lienzo
    // tomara el foco, así que el buscador no lo perdía nunca y Android volvía
    // a abrir el teclado en cada toque. El arrastre ya lo frena `touch-action`.
    soltarTeclado();
    var q = xy(e);
    toques.set(e.pointerId, { x: q.x, y: q.y });
    lienzo.setPointerCapture(e.pointerId);
    if (toques.size === 1) {
      arrastrando = true; movido = 0;
      botonArrastre = 0;
      tipoArrastre = 'girar';
      ux = q.x; uy = q.y;
      lienzo.classList.add('arrastrando');
    } else if (toques.size === 2) {
      tipoArrastre = 'pinza';
      movido = 99;  // dos dedos nunca son un toque para seleccionar
      medirToques();
    }
  });

  lienzo.addEventListener('pointermove', function (e) {
    var p = xy(e);
    if (e.pointerType !== 'mouse') {
      if (!toques.has(e.pointerId)) return;
      toques.set(e.pointerId, { x: p.x, y: p.y });
      if (toques.size === 1 && arrastrando) {
        var gx = p.x - ux, gy = p.y - uy;
        movido += Math.abs(gx) + Math.abs(gy);
        rotY += gx * 0.006;
        rotX = Math.max(-1.35, Math.min(1.35, rotX + gy * 0.006));
        ux = p.x; uy = p.y;
      } else if (toques.size === 2) {
        var antesD = pellizco, antesX = centroX, antesY = centroY;
        medirToques();
        if (antesD > 0 && pellizco > 0) {
          camZ = Math.max(500, Math.min(2400, camZ * (antesD / pellizco)));
        }
        moverVista(centroX - antesX, centroY - antesY);
      }
      return;
    }
    if (arrastrando) {
      var dx = p.x - ux, dy = p.y - uy;
      movido += Math.abs(dx) + Math.abs(dy);
      if (tipoArrastre === 'girar') {
        rotY += dx * 0.006;
        rotX = Math.max(-1.35, Math.min(1.35, rotX + dy * 0.006));
      } else {
        moverVista(dx, dy);
      }
      ux = p.x; uy = p.y;
    } else if (!fijado) {
      var n = buscar(p.x, p.y);
      if (n !== senalado) { senalado = n; verFicha(senalado); }
      lienzo.style.cursor = n ? 'pointer' : 'grab';
    }
  });

  function terminarToque(e) {
    if (e.pointerType === 'mouse') {
      arrastrando = false;
      lienzo.classList.remove('arrastrando');
      return;
    }
    toques.delete(e.pointerId);
    if (toques.size === 1) {
      // Al levantar uno de los dos dedos, el que queda sigue girando sin salto.
      var resto = Array.from(toques.values())[0];
      ux = resto.x; uy = resto.y;
      tipoArrastre = 'girar';
      arrastrando = true;
    } else if (toques.size === 0) {
      arrastrando = false;
      lienzo.classList.remove('arrastrando');
    }
  }

  lienzo.addEventListener('pointerup', function (e) {
    var tactil = e.pointerType !== 'mouse';
    var ultimo = !tactil || toques.size <= 1;
    var puedeSeleccionar = tactil
      ? tipoArrastre === 'girar'
      : botonArrastre === 0;
    var p = xy(e);
    var recorrido = movido;
    terminarToque(e);
    if (ultimo && recorrido < 6 && puedeSeleccionar) {
      var elegido = buscar(p.x, p.y);
      seleccionar(elegido && fijado !== elegido ? elegido : null);
    }
  });

  lienzo.addEventListener('pointercancel', terminarToque);

  lienzo.addEventListener('pointerleave', function () {
    arrastrando = false;
    if (!fijado) { senalado = null; verFicha(null); }
  });

  lienzo.addEventListener('contextmenu', function (e) {
    e.preventDefault();
  });

  lienzo.addEventListener('auxclick', function (e) {
    e.preventDefault();
  });

  lienzo.addEventListener('wheel', function (e) {
    e.preventDefault();
    cambiarZoom(e.deltaY * 0.6);
  }, { passive: false });

  addEventListener('keydown', function (e) {
    var escribiendo = /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName);
    if (e.key === 'Escape') seleccionar(null);
    if (escribiendo || document.activeElement !== lienzo) return;
    if (e.shiftKey && e.key === 'ArrowLeft') rotY -= 0.08;
    else if (e.shiftKey && e.key === 'ArrowRight') rotY += 0.08;
    else if (e.shiftKey && e.key === 'ArrowUp') {
      rotX = Math.max(-1.35, rotX - 0.08);
    } else if (e.shiftKey && e.key === 'ArrowDown') {
      rotX = Math.min(1.35, rotX + 0.08);
    } else if (e.key === 'ArrowLeft') moverVista(-24, 0);
    else if (e.key === 'ArrowRight') moverVista(24, 0);
    else if (e.key === 'ArrowUp') moverVista(0, -24);
    else if (e.key === 'ArrowDown') moverVista(0, 24);
    else if (e.key === '+' || e.key === '=') cambiarZoom(-160);
    else if (e.key === '-') cambiarZoom(160);
    else return;
    e.preventDefault();
  });

  /* ── la ficha flotante ────────────────────────────────────────────────── */

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function moduloTexto(titulo, cosas, vacio) {
    return '<section class="ficha-mini-modulo"><header><span>' + titulo +
      '</span><span>' + cosas.length + '</span></header>' +
      (cosas.length
        ? '<p>' + esc(cosas[0]) + '</p>' +
          (cosas.length > 1
            ? '<small>Y ' + (cosas.length - 1) + ' más</small>'
            : '')
        : '<p class="vacio">' + vacio + '</p>') +
      '</section>';
  }

  // Arreglo provisional del clic fantasma: en móvil la ficha aparece justo
  // donde estaba el dedo, y el `click` que el navegador dispara después del
  // toque caía sobre «Abrir su ficha». Durante un instante la tarjeta no
  // recibe pulsaciones, así que ese clic heredado se pierde en el vacío.
  var relojFicha = null;
  function protegerDelToque() {
    panel.classList.add('recien-abierta');
    clearTimeout(relojFicha);
    relojFicha = setTimeout(function () {
      panel.classList.remove('recien-abierta');
    }, 350);
  }

  function verFicha(n) {
    if (!panel || !panelContenido) return;
    if (!n) {
      panel.classList.remove('visible');
      panel.classList.remove('recien-abierta');
      panel.setAttribute('aria-hidden', 'true');
      return;
    }
    if (!panel.classList.contains('visible')) protegerDelToque();

    var quedadas = '<section class="ficha-mini-modulo ficha-mini-quedada">' +
      '<header><span>ÚLTIMA QUEDADA</span><span>' + n.quedadas.length + '</span></header>' +
      (n.quedadas.length
        ? '<p>' + esc(n.quedadas[0].texto) + '</p><small>' +
          esc(n.quedadas[0].cuando) +
          (n.quedadas[0].canal ? ' · ' + esc(n.quedadas[0].canal) : '') +
          '</small>'
        : '<p class="vacio">Todavía no habéis coincidido, o no lo has apuntado.</p>') +
      '</section>';

    var relaciones = '<section class="ficha-mini-modulo ficha-mini-relaciones">' +
      '<header><span>RELACIONES</span><span>' + n.relaciones.length + '</span></header>' +
      (n.relaciones.length
        ? '<div class="chips">' +
        n.relaciones.slice(0, 3).map(function (r) {
          return '<a class="chip" href="/persona/' + r.id + '">' + esc(r.nombre) +
            (r.etiqueta ? ' <span class="lazo">' + esc(r.etiqueta) + '</span>' : '') +
            '</a>';
        }).join('') + '</div>'
        : '<p class="vacio">No sabemos aún a quién conoce.</p>') +
      '</section>';

    panelContenido.innerHTML =
      '<header class="ficha-mini-cabecera"><div class="ficha-mini-identidad">' +
      (n.foto
        ? '<img class="foto-mini" src="/persona/' + n.id + '/foto" alt="">'
        : '<span class="foto-mini foto-vacia" aria-hidden="true"></span>') +
      '<div><h1 class="titulo">' + esc(n.nombre) + '</h1>' +
      (n.nombreCompleto !== n.nombre
        ? '<p class="ficha-mini-nombre-completo">' + esc(n.nombreCompleto) + '</p>'
        : '') +
      (n.circulo ? '<span class="donde">' + esc(n.circulo) + '</span>' : '') +
      '</div></div></header>' +
      '<dl class="ficha-mini-vistazo"><div><dt>HABLAMOS HACE</dt><dd>' +
        esc(n.hablamos) + '</dd></div><div><dt>QUEDADAS</dt><dd>' +
        n.notas + '</dd></div></dl>' +
      '<div class="ficha-mini-en-marcha">' +
        moduloTexto('QUEDA PENDIENTE', n.pendiente, 'No le debes nada ahora mismo.') +
        moduloTexto('PREGUNTAR POR', n.preguntar, 'Nada en marcha ahora mismo.') +
      '</div>' +
      moduloTexto('DATOS', n.datos, 'Aún no has apuntado nada suyo.') +
      quedadas +
      relaciones +
      '<div class="acciones ir"><a class="boton" href="/nota?volver=%2F&amp;persona=' +
        n.id + '">Apuntar algo</a><a class="boton boton-solido" href="/persona/' +
        n.id + '">Abrir su ficha</a></div>';

    panel.classList.add('visible');
    panel.setAttribute('aria-hidden', 'false');
  }
})();
