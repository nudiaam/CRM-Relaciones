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
     - En reposo sólo se ve la estructura raíz → círculo → persona. Las
       relaciones aparecen al señalar a alguien.
     - Los círculos activos son cuadrados con su gente alrededor.
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
  var mensaje = document.getElementById('grafo-mensaje');
  if (!lienzo) return;

  var ctx = lienzo.getContext('2d');
  var raiz = document.documentElement;
  var quieto = matchMedia('(prefers-reduced-motion: reduce)').matches;

  var CERCANIA_NOMBRES = 0.4;   // el 40% más cercano a la cámara
  var GIRO = 0.00087;           // una vuelta cada dos minutos a 60 fotogramas
  // tintas: en reposo y con alguien señalado
  var LINEA = 0.12, LINEA_TOCA = 0.62, LINEA_LEJOS = 0.025;
  var PUNTO_MIN = 0.35, APAGADO = 0.05;

  var nodos = [], nodosVisibles = [], centros = [], aristas = [], estructura = [], satelites = [];
  var porId = {}, porCirculo = {}, circulos = [], marcas = [];
  var central = null, circuloYoId = null, centroBajoPuntero = null;
  var sinCirculoEnPortada = true;
  var A = 0, ALTO = 0, dpr = 1;
  // con tanto aire, la cámara tiene que estar lejos: si no, los de delante se
  // proyectan enormes y se salen de la pantalla
  var camZ = 2800, camZObjetivo = 2800, foco = 900;
  var camX = 0, camY = 0, camProfundidad = 0;
  var camXObjetivo = 0, camYObjetivo = 0, camProfundidadObjetivo = 0;
  var rotX = -0.1, rotY = -0.9;
  var vistaX = 0, vistaY = 0, vistaXObjetivo = 0, vistaYObjetivo = 0;
  var movimiento = !quieto;
  var giro = GIRO;
  var circuloEnFoco = '', circuloFijado = '';
  var senalado = null, fijado = null, bajoPuntero = null;
  var refrescarCirculos = function () {};
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
    sinCirculoEnPortada = d.sin_circulo_en_portada !== false;
    var circuloYo = circulos.find(function (c) {
      return normalizar(c.nombre) === 'yo';
    });
    circuloYoId = circuloYo ? String(circuloYo.id) : null;
    var idsCirculosActivos = circulos.filter(function (c) {
      return !!c.en_portada && normalizar(c.nombre) !== 'yo';
    }).map(function (c) { return String(c.id); });
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
        vecinos: [],
        anclasPersona: [],
        anclasCirculo: [],
        componenteSinCirculo: -1,
        visible: false,
        fisicaX: 0,
        fisicaY: 0,
        velocidadX: 0,
        velocidadY: 0,
        realce: 1,
        velocidadRealce: 0
      };
    });

    porId = {};
    nodos.forEach(function (n) { porId[n.clave] = n; });
    central = d.central_id == null ? null : porId['p' + d.central_id];
    if (!central) {
      central = nodos.find(function (n) { return n.central; }) || null;
    }
    nodos.forEach(function (n) {
      n.visible = n === central || n.circuloId === circuloYoId ||
        (n.circuloId !== null && idsCirculosActivos.indexOf(n.circuloId) !== -1);
    });

    centros = circulos.filter(function (c) {
      return normalizar(c.nombre) !== 'yo' && !!c.en_portada;
    }).map(function (c, indice) {
      return {
        clave: 'c' + c.id,
        circuloId: String(c.id),
        nombre: c.nombre,
        indice: indice,
        centro: true,
        virtual: false,
        fisicaX: 0,
        fisicaY: 0,
        velocidadX: 0,
        velocidadY: 0,
      };
    });
    if (sinCirculoEnPortada) {
      centros.push({
        clave: 'cninguno',
        circuloId: 'ninguno',
        nombre: 'Sin círculo',
        indice: centros.length,
        centro: true,
        virtual: true,
        fisicaX: 0,
        fisicaY: 0,
        velocidadX: 0,
        velocidadY: 0,
      });
    }
    porCirculo = {};
    centros.forEach(function (c) { porCirculo[c.circuloId] = c; });

    aristas = [];
    (d.aristas || []).forEach(function (e) {
      var a = porId[e.a], b = porId[e.b];
      if (!a || !b || a === b) return;
      aristas.push({ a: a, b: b, tipo: e.tipo || 'persona' });
      a.vecinos.push(b);
      b.vecinos.push(a);
    });

    prepararAnclasSinCirculo();
    nodos.forEach(function (n) {
      if (n.circuloId === null) {
        n.visible = sinCirculoEnPortada || n.anclasPersona.length > 0;
      }
    });
    nodosVisibles = nodos.filter(function (n) { return n.visible; });

    estructura = [];
    nodosVisibles.forEach(function (n) {
      if (n === central) return;
      if (n.circuloId === null && n.anclasPersona.length) return;
      var centro = n.circuloId === circuloYoId
        ? central : porCirculo[n.circuloId === null ? 'ninguno' : n.circuloId];
      if (centro) estructura.push({ a: centro, b: n, tipo: 'persona' });
    });
    if (central) {
      centros.forEach(function (centro) {
        estructura.push({ a: central, b: centro, tipo: 'circulo' });
      });
    }

    // Sólo los puntos AISLADOS de verdad cuelgan de una línea secundaria: una
    // persona sin círculo cuya única atadura a la red es su relación, y que
    // además está sola (su componente sin círculo tiene un único miembro). Un
    // grupo de gente sin círculo ya se lee como una nube junta; no se le teje
    // una maraña de discontinuas encima. La línea es tenue para no fingir que
    // el punto pertenece a un círculo.
    var miembrosPorComponente = {};
    nodosVisibles.forEach(function (n) {
      if (n.circuloId !== null || !n.anclasPersona.length) return;
      miembrosPorComponente[n.componenteSinCirculo] =
        (miembrosPorComponente[n.componenteSinCirculo] || 0) + 1;
    });
    satelites = [];
    nodosVisibles.forEach(function (n) {
      if (n.circuloId !== null || !n.anclasPersona.length) return;
      if (miembrosPorComponente[n.componenteSinCirculo] !== 1) return;
      n.anclasPersona.forEach(function (ancla) {
        satelites.push({ a: ancla, b: n });
      });
    });

    colocar();
    marcas = [];
    for (var m = 0; m < 72; m++) {
      marcas.push({ x: azar(), y: azar(), grande: m % 17 === 0 });
    }
    medir();
    centrarCamara();
    prepararMandos();
    addEventListener('resize', medir);
    pintar();
    requestAnimationFrame(bucle);
  }

  /* ── colocación: se calcula una vez ───────────────────────────────────── */

  var semilla = 20260725;
  function azar() { return (semilla = semilla * 16807 % 2147483647) / 2147483647; }

  // Corona abierta y tridimensional. Una esfera de Fibonacci dejaba cuatro o
  // cinco círculos casi en columna al proyectarla; esta corona conserva aire
  // en ambos ejes de pantalla y alterna profundidad para que siga siendo 3D.
  function ejesDeCirculos(cuantos) {
    var ejes = [];
    for (var i = 0; i < cuantos; i++) {
      var angulo = -Math.PI / 2 + Math.PI / Math.max(2, cuantos) +
        i * Math.PI * 2 / Math.max(1, cuantos);
      ejes.push({
        x: Math.cos(angulo) * 1.18,
        y: Math.sin(angulo) * 0.76,
        z: Math.sin(angulo * 2) * 0.55
      });
    }
    return ejes;
  }

  function colocar() {
    semilla = 20260725;
    centros.concat(nodos).forEach(function (n) {
      n.x = n.y = n.z = 0;
      n.fisicaX = n.fisicaY = 0;
      n.velocidadX = n.velocidadY = 0;
      n.realce = 1;
      n.velocidadRealce = 0;
    });
    colocarPorCirculos();
  }

  function gruposConCirculo() {
    var grupos = {};
    centros.forEach(function (centro) { grupos[centro.circuloId] = []; });
    grupos.raiz = [];
    nodosVisibles.forEach(function (n) {
      if (n === central) return;
      var id;
      if (n.circuloId === null) {
        if (n.anclasPersona.length) return;
        id = 'ninguno';
      } else if (n.circuloId === circuloYoId) {
        id = 'raiz';
      } else {
        id = n.circuloId;
      }
      if (!grupos[id]) grupos[id] = [];
      grupos[id].push(n);
    });
    return grupos;
  }

  function direccionEsfera(indice, cuantos, fase) {
    var y = cuantos <= 1 ? 0 : 1 - 2 * (indice + 0.5) / cuantos;
    var r = Math.sqrt(Math.max(0, 1 - y * y));
    var th = (indice + fase) * Math.PI * (3 - Math.sqrt(5));
    return { x: Math.cos(th) * r, y: y, z: Math.sin(th) * r };
  }

  // Cada grupo (la gente de un círculo, el corro de Nuria, un satélite) se
  // reparte sobre una ESFERA alrededor de su centro, no sobre un plano. Un
  // disco, por muy inclinado que estuviera, se ve de canto desde algún ángulo y
  // vuelve a parecer plano; una esfera tiene volumen en los tres ejes, así que
  // de frente, desde arriba o de lado siempre hay profundidad y se lee. El
  // reparto es una espiral de Fibonacci (`direccionEsfera`): puntos regulares y
  // deterministas, sin huecos ni columnas.
  function colocarEnEsfera(n, centro, direccion, distancia) {
    n.x = centro.x + direccion.x * distancia;
    n.y = centro.y + direccion.y * distancia;
    n.z = centro.z + direccion.z * distancia;
  }

  // «Sin círculo» sigue siendo una clasificación propia. Estas anclas sólo
  // deciden dónde se ve cada persona: una pareja o amistad explícita puede
  // acercarla a gente clasificada sin convertirla en miembro de su círculo.
  function prepararAnclasSinCirculo() {
    var sinCirculo = nodos.filter(function (n) { return n.circuloId === null; });
    var vistos = {};
    var numeroComponente = 0;
    sinCirculo.forEach(function (inicio) {
      if (vistos[inicio.clave]) return;
      var cola = [inicio], componente = [], anclas = [];
      vistos[inicio.clave] = true;
      while (cola.length) {
        var actual = cola.shift();
        componente.push(actual);
        actual.vecinos.forEach(function (otra) {
          if (otra.circuloId === null) {
            if (!vistos[otra.clave]) {
              vistos[otra.clave] = true;
              cola.push(otra);
            }
          } else if (otra.visible && anclas.indexOf(otra) === -1) {
            anclas.push(otra);
          }
        });
      }
      componente.forEach(function (n) {
        var directas = n.vecinos.filter(function (otra) {
          return otra.circuloId !== null && otra.visible;
        });
        n.anclasPersona = directas.length ? directas : anclas.slice();
        n.anclasCirculo = [];
        n.anclasPersona.forEach(function (otra) {
          if (otra.circuloId !== circuloYoId &&
              n.anclasCirculo.indexOf(otra.circuloId) === -1) {
            n.anclasCirculo.push(otra.circuloId);
          }
        });
        n.componenteSinCirculo = numeroComponente;
      });
      numeroComponente++;
    });
  }

  function colocarCentros(radioPara) {
    var ejes = ejesDeCirculos(centros.length);
    centros.forEach(function (centro, indice) {
      var radio = radioPara(centro, indice);
      centro.x = ejes[indice].x * radio;
      centro.y = ejes[indice].y * radio;
      centro.z = ejes[indice].z * radio;
    });
  }

  function colocarAlrededor(centro, grupo, numero) {
    var total = grupo.length;
    grupo.forEach(function (n, indice) {
      var d = direccionEsfera(indice, total, numero * 0.7 + 0.3);
      var distancia = 290 + (indice % 4) * 26;
      colocarEnEsfera(n, centro, d, distancia);
    });
  }

  function colocarCercaDeRaiz(grupo) {
    var origen = { x: 0, y: 0, z: 0 };
    var total = grupo.length;
    grupo.forEach(function (n, indice) {
      var d = direccionEsfera(indice, total, 0.9);
      colocarEnEsfera(n, origen, d, 285 + (indice % 4) * 24);
    });
  }

  function colocarSatelites() {
    var porComponente = {};
    nodosVisibles.forEach(function (n) {
      if (n.circuloId !== null || !n.anclasPersona.length) return;
      var clave = String(n.componenteSinCirculo);
      if (!porComponente[clave]) porComponente[clave] = [];
      porComponente[clave].push(n);
    });
    Object.keys(porComponente).forEach(function (clave, numero) {
      var grupo = porComponente[clave];
      var anclas = [];
      grupo.forEach(function (n) {
        n.anclasPersona.forEach(function (otra) {
          if (anclas.indexOf(otra) === -1) anclas.push(otra);
        });
      });
      var promedio = anclas.reduce(function (suma, otra) {
        suma.x += otra.x; suma.y += otra.y; suma.z += otra.z;
        return suma;
      }, { x: 0, y: 0, z: 0 });
      promedio.x /= anclas.length;
      promedio.y /= anclas.length;
      promedio.z /= anclas.length;
      var total = grupo.length;
      grupo.forEach(function (n, indice) {
        var d = direccionEsfera(indice, total, numero * 0.6 + 0.4);
        var distancia = 205 + (indice % 4) * 24;
        colocarEnEsfera(n, promedio, d, distancia);
      });
    });
  }

  // Una única composición: cuadrados bien separados y estrellas regulares.
  // Las personas conservan siempre este sitio; enfocar mueve sólo la cámara.
  function colocarPorCirculos() {
    var grupos = gruposConCirculo();
    colocarCentros(function (centro, indice) { return 700 + (indice % 2) * 50; });
    centros.forEach(function (centro, numero) {
      colocarAlrededor(centro, grupos[centro.circuloId] || [], numero);
    });
    colocarCercaDeRaiz(grupos.raiz || []);
    colocarSatelites();
  }

  /* ── medidas ──────────────────────────────────────────────────────────── */

  function medir() {
    dpr = Math.min(devicePixelRatio || 1, 2);
    A = lienzo.clientWidth; ALTO = lienzo.clientHeight;
    lienzo.width = Math.max(1, Math.round(A * dpr));
    lienzo.height = Math.max(1, Math.round(ALTO * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (!fijado && !circuloFijado) camZObjetivo = camaraParaEstado();
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

  function radio(n) {
    return Math.max(1, radioBase(n) * escala(n) * (n.realce || 1));
  }

  function proyectar() {
    var cx = Math.cos(rotX), sx = Math.sin(rotX);
    var cy = Math.cos(rotY), sy = Math.sin(rotY);
    centros.concat(nodosVisibles).forEach(function (n) {
      var x = n.x - camX, y = n.y - camY, z = n.z - camProfundidad;
      var x1 = x * cy - z * sy;
      var z1 = x * sy + z * cy;
      var y2 = y * cx - z1 * sx;
      var z2 = y * sx + z1 * cx;
      var zc = z2 + camZ;
      var k = foco / Math.max(zc, 60);
      n.px = centroHorizontal() + vistaX + x1 * k;
      n.py = ALTO / 2 + vistaY + y2 * k;
      n.pz = zc;
      n.k = k;
    });
    animarFisica();
  }

  // Radio en pantalla del anillo de allegados alrededor de la persona elegida.
  function radioAnillo(cuantos) {
    return Math.max(120, Math.min(235, 96 + cuantos * 15));
  }

  // El movimiento vivo de la red. Dos cosas a la vez, ninguna toca las
  // posiciones base (todo son desvíos interpolados que vuelven a cero al soltar):
  //  1) Al SEÑALAR con el ratón, la gente cercana se aparta del puntero. Esto
  //     sigue vivo aunque haya una persona seleccionada: entrar en su ficha ya no
  //     congela ese vaivén.
  //  2) Al SELECCIONAR una persona (que no sea Nuria), sus allegados se recolocan
  //     en un anillo a su alrededor; al SELECCIONAR un círculo, su gente hace lo
  //     mismo alrededor del cuadrado. Así ni las relaciones ni un círculo entero
  //     quedan en un abanico desordenado, sino como radios ordenados y legibles.
  function animarFisica() {
    var realzada = activo();
    var repulsor = bajoPuntero || (fijado ? null : senalado);
    var anillo = anilloActivo();

    nodosVisibles.forEach(function (n) {
      var destinoX = 0, destinoY = 0;
      var enAnillo = anillo && n !== anillo.foco &&
        indiceDefinido(anillo.indices, n.clave);
      if (enAnillo) {
        var i = anillo.indices[n.clave];
        var ang = i * Math.PI * 2 / Math.max(1, anillo.total) - Math.PI / 2;
        var R = radioAnillo(anillo.total);
        destinoX = anillo.foco.px + Math.cos(ang) * R - n.px;
        destinoY = anillo.foco.py + Math.sin(ang) * R - n.py;
      } else if (repulsor && n !== repulsor && !(anillo && n === anillo.foco)) {
        var dx = n.px - repulsor.px, dy = n.py - repulsor.py;
        var distancia = Math.max(1, Math.hypot(dx, dy));
        var fuerza = Math.max(0, 1 - distancia / 210) * 34;
        destinoX = dx / distancia * fuerza;
        destinoY = dy / distancia * fuerza;
      }
      var destinoRealce = (n === realzada || n === repulsor) ? 1.48 : 1;
      if (quieto) {
        n.fisicaX = destinoX;
        n.fisicaY = destinoY;
        n.realce = destinoRealce;
      } else {
        var paso = enAnillo ? 0.12 : 0.14;
        n.fisicaX += (destinoX - n.fisicaX) * paso;
        n.fisicaY += (destinoY - n.fisicaY) * paso;
        n.realce += (destinoRealce - n.realce) * 0.14;
      }
      n.px += n.fisicaX;
      n.py += n.fisicaY;
    });
  }

  function indiceDefinido(mapa, clave) {
    return Object.prototype.hasOwnProperty.call(mapa, clave);
  }

  // El anillo que se recoloca alrededor del foco actual: los allegados de una
  // persona, o toda la gente de un círculo alrededor de su cuadrado. Devuelve
  // null si no hay nada seleccionado. Nuria no forma anillo (cuelga de círculos).
  function anilloActivo() {
    var foco = null, gente = null;
    if (fijado && fijado !== central) {
      foco = fijado;
      gente = fijado.vecinos.filter(function (v) { return v.visible; });
    } else if (!fijado && circuloFijado && porCirculo[circuloFijado]) {
      foco = porCirculo[circuloFijado];
      gente = nodosVisibles.filter(function (n) {
        return n !== central && enCirculoVisual(n, circuloFijado);
      });
    }
    if (!foco || !gente || !gente.length) return null;
    var indices = {};
    gente.forEach(function (v, i) { indices[v.clave] = i; });
    return { foco: foco, indices: indices, total: gente.length };
  }

  function activo() { return fijado || senalado; }

  function circuloActivo() {
    return circuloFijado || circuloEnFoco ||
      (centroBajoPuntero ? centroBajoPuntero.circuloId : '');
  }

  function enCirculo(n, id) {
    if (!id) return true;
    if (n.centro) return n.circuloId === id;
    if (id === 'ninguno') return n.circuloId === null;
    return n.circuloId === id;
  }

  function enCirculoVisual(n, id) {
    if (!id) return true;
    if (n.centro) return n.circuloId === id;
    if (id === 'ninguno') return n.circuloId === null;
    return n.circuloId === id || (n.circuloId === null &&
      n.anclasCirculo.indexOf(id) !== -1);
  }

  function personasDelCirculo(id) {
    return nodosVisibles.filter(function (n) {
      return n !== central && enCirculoVisual(n, id);
    }).sort(function (a, b) {
      var directaA = enCirculo(a, id) ? 0 : 1;
      var directaB = enCirculo(b, id) ? 0 : 1;
      return directaA - directaB || a.nombre.localeCompare(b.nombre, 'es');
    });
  }

  function centroHorizontal() {
    return A / 2 + (A >= 720 ? Math.min(70, A * 0.04) : 0);
  }

  function ligado(n, a) {
    return n === a || a.vecinos.indexOf(n) !== -1;
  }

  // A quién realza señalar/seleccionar a `a`. Regla normal: la persona y sus
  // relaciones. Excepción única de Nuria (`central`): sus relaciones NO se
  // realzan; su vínculo son los círculos, que se encienden aparte. Sólo ella
  // queda a plena tinta, el resto de personas en gris.
  function resaltada(n, a) {
    if (a === central) return n === central;
    return ligado(n, a);
  }

  /* ── dibujo ───────────────────────────────────────────────────────────── */

  function pintar() {
    RGB = getComputedStyle(raiz).getPropertyValue('--tinta-r').trim() || '20,18,15';
    ctx.clearRect(0, 0, A, ALTO);
    var a = activo();
    var circulo = circuloActivo();
    var etiquetasOcupadas = [];
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
    var fondos = nodosVisibles.map(function (n) { return n.pz; }).sort(function (x, y) {
      return x - y;
    });
    var corte = fondos.length
      ? fondos[Math.max(0, Math.floor(fondos.length * CERCANIA_NOMBRES) - 1)]
      : 0;

    // La estructura se lee siempre: raíz → círculo → persona. Las relaciones
    // entre personas sólo aparecen al señalar una, evitando la maraña.
    ctx.lineWidth = 1;
    estructura.forEach(function (e) {
      var idActivo = a ? circuloDePersona(a) : '';
      // La línea de la persona señalada a su cuadrado se realza. La del cuadrado
      // a Nuria (raíz → círculo) se mantiene apenas visible: sitúa el círculo
      // sin robar protagonismo a la persona ni a sus relaciones.
      var tocaPersona = a && (e.a === a || e.b === a);
      var tocaCirculo = a && e.tipo === 'circulo' && e.b.circuloId === idActivo;
      var delCirculo = circulo && e.tipo !== 'circulo' &&
        (enCirculoVisual(e.a, circulo) || enCirculoVisual(e.b, circulo));
      ctx.beginPath();
      ctx.moveTo(e.a.px, e.a.py);
      ctx.lineTo(e.b.px, e.b.py);
      ctx.strokeStyle = tinta(
        a ? (tocaPersona ? 0.44 : tocaCirculo ? 0.12 : LINEA_LEJOS) :
        circulo ? (delCirculo ? 0.38 : LINEA_LEJOS) :
        e.tipo === 'circulo' ? 0.08 : LINEA
      );
      ctx.stroke();
    });

    // Los satélites cuelgan de su relación con una línea secundaria: siempre
    // discontinua y más floja que la estructura, para que ningún punto flote.
    // Con alguien señalado, su relación pasa a la línea sólida de aristas.
    ctx.setLineDash([2, 3]);
    satelites.forEach(function (e) {
      if (!e.a.visible || !e.b.visible) return;
      if (a && (e.a === a || e.b === a)) return;
      var toca = a && (ligado(e.a, a) || ligado(e.b, a));
      var delCirculo = circulo &&
        (enCirculoVisual(e.a, circulo) || enCirculoVisual(e.b, circulo));
      ctx.beginPath();
      ctx.moveTo(e.a.px, e.a.py);
      ctx.lineTo(e.b.px, e.b.py);
      ctx.strokeStyle = tinta(
        a ? (toca ? 0.28 : LINEA_LEJOS) :
        circulo ? (delCirculo ? 0.2 : LINEA_LEJOS) :
        0.09
      );
      ctx.stroke();
    });
    ctx.setLineDash([]);

    // Excepción única de Nuria: cuando ella es la seleccionada NO se dibujan sus
    // relaciones personales, sino su conexión a los CÍRCULOS (las líneas raíz →
    // círculo, ya realzadas arriba como `tocaPersona`). Nuria siempre cuelga de
    // los cuadrados, no de las personas. El resto de la gente sí enseña sus
    // relaciones al señalarla.
    if (a && a !== central) {
      aristas.forEach(function (e) {
        if (!e.a.visible || !e.b.visible) return;
        if (e.a !== a && e.b !== a) return;
        ctx.beginPath();
        ctx.moveTo(e.a.px, e.a.py);
        ctx.lineTo(e.b.px, e.b.py);
        ctx.strokeStyle = tinta(LINEA_TOCA);
        ctx.stroke();
      });
    }

    // Sólo los círculos activados en Ajustes forman parte de la red.
    centros.slice().sort(function (m, n) { return n.pz - m.pz; })
      .forEach(function (centro) {
        var idActivo = a ? circuloDePersona(a) : '';
        // Con Nuria seleccionada, TODOS los círculos se encienden: son su vínculo.
        var encendido = (a === central) ||
          (a && centro.circuloId === idActivo) ||
          (circulo && centro.circuloId === circulo) ||
          centro === centroBajoPuntero;
        var lado = 11;
        var opacidad = (a || circulo) ? (encendido ? 1 : 0.18) : 0.86;
        ctx.setLineDash(centro.virtual ? [2, 2] : []);
        if (encendido) {
          ctx.fillStyle = tinta(1);
          ctx.fillRect(
            Math.round(centro.px - lado / 2),
            Math.round(centro.py - lado / 2), lado, lado
          );
        } else {
          ctx.strokeStyle = tinta(opacidad);
          ctx.strokeRect(
            Math.round(centro.px - lado / 2) + 0.5,
            Math.round(centro.py - lado / 2) + 0.5, lado, lado
          );
        }
        ctx.setLineDash([]);
        ctx.font = '11px "Departure", ui-monospace, Consolas, monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = tinta(opacidad);
        var etiquetaY = Math.round(centro.py + 10);
        var anchoEtiqueta = ctx.measureText(centro.nombre).width;
        ctx.fillText(centro.nombre, Math.round(centro.px), etiquetaY);
        etiquetasOcupadas.push({
          x: centro.px - anchoEtiqueta / 2 - 3,
          y: etiquetaY - 2,
          w: anchoEtiqueta + 6,
          h: 17,
        });
      });

    // personas: puntos pequeños y llenos, de lejos a cerca
    var enOrden = nodosVisibles.slice().sort(function (m, n) { return n.pz - m.pz; });
    enOrden.forEach(function (n) {
      var prof = 1 - Math.min(1, Math.max(0, (n.pz - camZ + 700) / 1400));
      var cerca = PUNTO_MIN + prof * (1 - PUNTO_MIN);
      var r = radio(n);

      ctx.beginPath();
      ctx.arc(n.px, n.py, r, 0, Math.PI * 2);
      if (a) ctx.fillStyle = tinta(resaltada(n, a) ? 1 : APAGADO);
      else if (circulo) ctx.fillStyle = tinta(enCirculoVisual(n, circulo) ? 1 : APAGADO);
      else ctx.fillStyle = tinta(cerca);
      ctx.fill();

      if (n === a) {
        ctx.beginPath();
        ctx.arc(n.px, n.py, r + 5, 0, Math.PI * 2);
        ctx.strokeStyle = tinta(1);
        ctx.stroke();
      }

      // el nombre: en reposo sólo los más cercanos; señalando, sólo los suyos
      var conNombre = n.central || (a ? resaltada(n, a) :
        circulo ? enCirculoVisual(n, circulo) : n.pz <= corte);
      if (!conNombre) return;
      ctx.font = '11px "Departure", ui-monospace, Consolas, monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      var opacidadNombre = a
        ? (resaltada(n, a) ? 1 : APAGADO)
        : circulo
          ? (enCirculoVisual(n, circulo) ? 1 : (n.central ? 0.16 : APAGADO))
          : cerca;
      ctx.fillStyle = tinta(opacidadNombre);
      var nombreY = Math.round(n.py + r + 8);
      var anchoNombre = ctx.measureText(n.nombre).width;
      var caja = {
        x: n.px - anchoNombre / 2 - 3,
        y: nombreY - 2,
        w: anchoNombre + 6,
        h: 17,
      };
      var choca = etiquetasOcupadas.some(function (otra) {
        return caja.x < otra.x + otra.w && caja.x + caja.w > otra.x &&
          caja.y < otra.y + otra.h && caja.y + caja.h > otra.y;
      });
      if (choca && n !== a && !n.central) return;
      ctx.fillText(n.nombre, Math.round(n.px), nombreY);
      etiquetasOcupadas.push(caja);
    });
  }

  function bucle() {
    if (movimiento && !arrastrando && !fijado && !circuloFijado &&
        !senalado && !circuloEnFoco && !centroBajoPuntero) rotY += giro;
    actualizarCamara();
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
    nodosVisibles.forEach(function (n) {
      var d = Math.hypot(n.px - mx, n.py - my) - radio(n);
      if (d < mejorD) { mejorD = d; mejor = n; }
    });
    return mejor;
  }

  function buscarCentro(mx, my) {
    var mejor = null, mejorD = 22;
    centros.forEach(function (centro) {
      var d = Math.hypot(centro.px - mx, centro.py - my);
      if (d < mejorD) { mejorD = d; mejor = centro; }
    });
    return mejor;
  }

  function normalizar(s) {
    return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  function circuloDePersona(n) {
    if (!n || n === central || n.circuloId === circuloYoId) return '';
    if (n.circuloId !== null) return n.circuloId;
    if (circuloFijado && enCirculoVisual(n, circuloFijado)) return circuloFijado;
    return n.anclasCirculo[0] || 'ninguno';
  }

  function seleccionarPersona(n) {
    if (!n) return;
    var contexto = circuloDePersona(n);
    if (contexto) circuloFijado = contexto;
    else circuloFijado = '';
    fijado = n;
    senalado = null;
    verFicha(fijado);
    centrarEstado();
    refrescarCirculos();
    if (mensaje) mensaje.textContent = 'Seleccionada: ' + n.nombre;
  }

  function seleccionarCirculo(id) {
    fijado = null;
    senalado = null;
    verFicha(null);
    circuloFijado = id;
    circuloEnFoco = '';
    centrarEstado();
    refrescarCirculos();
  }

  function vistaGeneral() {
    fijado = null;
    senalado = null;
    circuloFijado = '';
    circuloEnFoco = '';
    verFicha(null);
    centrarEstado();
    refrescarCirculos();
  }

  function retroceder() {
    if (fijado) {
      var contexto = circuloDePersona(fijado);
      fijado = null;
      senalado = null;
      verFicha(null);
      circuloFijado = contexto;
      if (!contexto) vistaGeneral();
      else {
        centrarEstado();
        refrescarCirculos();
      }
      return;
    }
    if (circuloFijado) vistaGeneral();
  }

  function mensajeDelCirculo() {
    var id = circuloActivo();
    if (!id) return 'Toda la red';
    var c = circulos.find(function (circulo) {
      return String(circulo.id) === id;
    });
    var nombre = id === 'ninguno' ? 'Sin círculo' : (c ? c.nombre : 'Círculo');
    var cuantas = personasDelCirculo(id).length;
    return nombre + ': ' + cuantas + (cuantas === 1 ? ' persona' : ' personas');
  }

  function camaraParaEstado() {
    if (fijado) return A < 720 ? 1900 : 1450;
    if (circuloFijado) return A < 720 ? 2100 : 1650;
    if (A < 720) return 3400;
    return ALTO < 820 ? 2900 : 2500;
  }

  function orientacionMasClara() {
    // Esta orientación abre las estrellas locales de frente y conserva una
    // profundidad visible entre círculos. Es deliberadamente estable: la red
    // no debe reaparecer con otra composición cada vez que cambia su tamaño.
    return { x: -0.16, y: -0.42 };
  }

  function centrarCamara() {
    var orientacion = orientacionMasClara();
    rotX = orientacion.x;
    rotY = orientacion.y;
    centrarEstado();
    camX = camXObjetivo;
    camY = camYObjetivo;
    camProfundidad = camProfundidadObjetivo;
    camZ = camZObjetivo;
    vistaX = vistaXObjetivo;
    vistaY = vistaYObjetivo;
  }

  function centrarEstado() {
    var objetivo = fijado || (circuloFijado ? porCirculo[circuloFijado] : null);
    camXObjetivo = objetivo ? objetivo.x : 0;
    camYObjetivo = objetivo ? objetivo.y : 0;
    camProfundidadObjetivo = objetivo ? objetivo.z : 0;
    camZObjetivo = camaraParaEstado();
    vistaXObjetivo = 0;
    vistaYObjetivo = 0;
  }

  function actualizarCamara() {
    var paso = quieto ? 1 : 0.045;
    camX += (camXObjetivo - camX) * paso;
    camY += (camYObjetivo - camY) * paso;
    camProfundidad += (camProfundidadObjetivo - camProfundidad) * paso;
    camZ += (camZObjetivo - camZ) * paso;
    vistaX += (vistaXObjetivo - vistaX) * paso;
    vistaY += (vistaYObjetivo - vistaY) * paso;
  }

  function cambiarZoom(cantidad) {
    camZObjetivo = Math.max(500, Math.min(4500, camZObjetivo + cantidad));
  }

  function moverVista(dx, dy) {
    var objetivo = fijado || (circuloFijado ? porCirculo[circuloFijado] : null);
    var ox = objetivo ? objetivo.x : 0;
    var oy = objetivo ? objetivo.y : 0;
    var oz = objetivo ? objetivo.z : 0;
    var extension = centros.concat(nodosVisibles).reduce(function (maximo, n) {
      return Math.max(maximo, Math.hypot(n.x - ox, n.y - oy, n.z - oz));
    }, 0) * foco / Math.max(600, camZ);
    var limiteX = Math.max(A * 0.3, Math.min(A * 1.5, extension));
    var limiteY = Math.max(ALTO * 0.3, Math.min(ALTO * 1.5, extension));
    vistaXObjetivo = Math.max(-limiteX, Math.min(limiteX, vistaX + dx));
    vistaYObjetivo = Math.max(-limiteY, Math.min(limiteY, vistaY + dy));
    vistaX = vistaXObjetivo;
    vistaY = vistaYObjetivo;
  }

  function prepararMandos() {
    function coincidencias() {
      var busca = normalizar(entradaBuscar ? entradaBuscar.value.trim() : '');
      if (!busca) return [];
      return nodosVisibles.filter(function (persona) {
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
      seleccionarPersona(resultados[0]);
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
        seleccionarPersona(n);
        resultadosNombre.hidden = true;
        if (botonLimpiar) botonLimpiar.hidden = false;
      });
    }
    if (botonLimpiar) {
      botonLimpiar.addEventListener('click', function () {
        entradaBuscar.value = '';
        botonLimpiar.hidden = true;
        resultadosNombre.hidden = true;
        vistaGeneral();
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

    // La ficha resumida se pliega como «Explorar la red»: el rótulo es el botón,
    // la × sigue cerrándola del todo. El estado se conserva entre selecciones.
    var plegarFicha = document.getElementById('grafo-ficha-plegar');
    if (plegarFicha && panel) {
      var signoFicha = plegarFicha.querySelector('[data-signo]');
      plegarFicha.addEventListener('click', function () {
        var cerrado = panel.dataset.plegado === 'si';
        panel.dataset.plegado = cerrado ? 'no' : 'si';
        plegarFicha.setAttribute('aria-expanded', String(cerrado));
        if (signoFicha) signoFicha.textContent = cerrado ? '−' : '+';
      });
    }

    if (menos) menos.addEventListener('click', function () { cambiarZoom(180); });
    if (mas) mas.addEventListener('click', function () { cambiarZoom(-180); });
    if (centrar) centrar.addEventListener('click', function () {
      vistaGeneral();
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
      retroceder();
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
    var opciones = circulos.filter(function (c) {
      return !!c.en_portada && normalizar(c.nombre) !== 'yo';
    }).map(function (c) {
      return { id: String(c.id), nombre: c.nombre };
    });
    if (sinCirculoEnPortada) {
      opciones.push({ id: 'ninguno', nombre: 'Sin círculo' });
    }
    listaCirculos.innerHTML = opciones.map(function (c) {
      var cuantas = nodosVisibles.filter(function (n) { return enCirculo(n, c.id); }).length;
      return '<button type="button" data-circulo="' + c.id + '" aria-pressed="false">' +
        '<span class="circulo-cuadrado" aria-hidden="true"></span>' +
        '<span>' + esc(c.nombre) + '</span><span class="circulo-cuenta">' +
        cuantas + '</span></button>';
    }).join('');

    refrescarCirculos = function () {
      listaCirculos.querySelectorAll('[data-circulo]').forEach(function (boton) {
        boton.setAttribute(
          'aria-pressed', String(boton.dataset.circulo === circuloFijado)
        );
      });
      if (mensaje && !activo()) mensaje.textContent = mensajeDelCirculo();
    };

    listaCirculos.querySelectorAll('[data-circulo]').forEach(function (boton) {
      boton.addEventListener('mouseenter', function () {
        circuloEnFoco = boton.dataset.circulo;
        refrescarCirculos();
      });
      boton.addEventListener('mouseleave', function () {
        circuloEnFoco = '';
        refrescarCirculos();
      });
      boton.addEventListener('focus', function () {
        circuloEnFoco = boton.dataset.circulo;
        refrescarCirculos();
      });
      boton.addEventListener('blur', function () {
        circuloEnFoco = '';
        refrescarCirculos();
      });
      boton.addEventListener('click', function () {
        if (circuloFijado === boton.dataset.circulo && !fijado) vistaGeneral();
        else seleccionarCirculo(boton.dataset.circulo);
      });
    });
    refrescarCirculos();
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
      bajoPuntero = null;
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
          camZObjetivo = Math.max(
            500, Math.min(4500, camZObjetivo * (antesD / pellizco))
          );
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
    } else {
      var n = buscar(p.x, p.y);
      // El punto bajo el ratón alimenta el vaivén, también con alguien elegido:
      // así entrar en una ficha no apaga el movimiento reactivo al puntero.
      bajoPuntero = n;
      if (!fijado) {
        var nuevoCentro = n ? null : buscarCentro(p.x, p.y);
        if (nuevoCentro !== centroBajoPuntero) {
          centroBajoPuntero = nuevoCentro;
          refrescarCirculos();
        }
        if (n !== senalado) { senalado = n; verFicha(senalado); }
        lienzo.style.cursor = (n || centroBajoPuntero) ? 'pointer' : 'grab';
      } else {
        lienzo.style.cursor = n ? 'pointer' : 'grab';
      }
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
      var centroElegido = elegido ? null : buscarCentro(p.x, p.y);
      if (elegido) {
        if (fijado === elegido) retroceder();
        else seleccionarPersona(elegido);
      } else if (centroElegido) {
        if (!fijado && circuloFijado === centroElegido.circuloId) vistaGeneral();
        else seleccionarCirculo(centroElegido.circuloId);
      } else {
        retroceder();
      }
    }
  });

  lienzo.addEventListener('pointercancel', terminarToque);

  lienzo.addEventListener('pointerleave', function () {
    arrastrando = false;
    centroBajoPuntero = null;
    bajoPuntero = null;
    refrescarCirculos();
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
    if (e.key === 'Escape') retroceder();
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
        // Sin foto va su inicial, como en la ficha rápida de Personas. Antes
        // era un cuadrado de tinta macizo y no decía nada de quién era.
        : '<span class="foto-mini foto-vacia" aria-hidden="true">' +
          esc((n.nombre || '?').trim().charAt(0).toUpperCase()) + '</span>') +
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
        n.id + '">Añadir nota</a><a class="boton boton-solido" href="/persona/' +
        n.id + '">Abrir su ficha</a></div>';

    panel.classList.add('visible');
    panel.setAttribute('aria-hidden', 'false');
  }
})();
