// Interacciones comunes. Se carga en el <head> para aplicar el modo antes del
// primer pintado; el contenido y los formularios siguen siendo HTML normal.

(function () {
  'use strict';

  var raiz = document.documentElement;
  var CLAVE_POSICION = 'relaciones:posicion-scroll';

  function guardarPosicion(ruta) {
    try {
      sessionStorage.setItem(CLAVE_POSICION, JSON.stringify({
        ruta: ruta || location.pathname,
        y: window.scrollY,
        momento: Date.now()
      }));
    } catch (e) { /* sin sessionStorage */ }
  }

  function recuperarPosicion() {
    try {
      var guardada = sessionStorage.getItem(CLAVE_POSICION);
      sessionStorage.removeItem(CLAVE_POSICION);
      if (!guardada) return null;
      var posicion = JSON.parse(guardada);
      if (Date.now() - posicion.momento > 60000) return null;
      return posicion;
    } catch (e) {
      return null;
    }
  }

  var posicionPendiente = recuperarPosicion();

  // 1. Modo día/noche antes de pintar, para que no dé el fogonazo blanco.
  var guardado = null;
  try { guardado = localStorage.getItem('modo'); } catch (e) { /* sin localStorage */ }
  if (guardado === 'noche' || guardado === 'dia') raiz.dataset.modo = guardado;

  function pinta(boton) {
    boton.textContent = raiz.dataset.modo === 'noche' ? 'Día' : 'Noche';
  }

  document.addEventListener('DOMContentLoaded', function () {

    var boton = document.getElementById('modo');
    if (boton) {
      pinta(boton);
      boton.addEventListener('click', function () {
        raiz.dataset.modo = raiz.dataset.modo === 'noche' ? 'dia' : 'noche';
        try { localStorage.setItem('modo', raiz.dataset.modo); } catch (e) { /* nada */ }
        pinta(boton);
      });
    }

    // 2. Foco en el texto de la nota, aunque la ventana no honre autofocus.
    var texto = document.querySelector('textarea[autofocus]');
    if (texto) texto.focus();

    // 3. Tecla N: apuntar algo desde cualquier sitio. El destino lo calcula el
    //    servidor para conservar la pantalla a la que hay que volver.
    var escribir = document.querySelector('[data-atajo-n]');
    document.addEventListener('keydown', function (ev) {
      if (!escribir || ev.ctrlKey || ev.altKey || ev.metaKey) return;
      var etiqueta = ev.target.tagName;
      if (etiqueta === 'INPUT' || etiqueta === 'TEXTAREA' || etiqueta === 'SELECT') return;
      if (ev.key === 'n' || ev.key === 'N') {
        ev.preventDefault();
        location.href = escribir.href;
      }
    });

    // 4. Ctrl + Enter guarda desde el texto de la nota.
    document.querySelectorAll('textarea').forEach(function (area) {
      area.addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey) && area.form) {
          area.form.requestSubmit ? area.form.requestSubmit() : area.form.submit();
        }
      });
    });

    // 5. Filtro, contador y páginas al marcar a quién apuntas. La caja conserva
    //    siempre el mismo alto: nueve personas en escritorio, seis en móvil.
    var filtro = document.querySelector('[data-filtro]');
    if (filtro) {
      var etiquetas = Array.from(document.querySelectorAll('.gente label[data-nombre]'));
      var cuenta = document.getElementById('personas-marcadas');
      var limpiarFiltro = document.querySelector('[data-limpiar-filtro]');
      var paginaGente = document.querySelector('[data-gente-pagina]');
      var anteriorGente = document.querySelector('[data-gente-anterior]');
      var siguienteGente = document.querySelector('[data-gente-siguiente]');
      var paginaActual = 0;

      function contar() {
        if (!cuenta) return;
        var n = document.querySelectorAll('.gente input:checked').length;
        cuenta.textContent = n ? n + (n === 1 ? ' persona' : ' personas') : 'Nadie marcado';
      }

      function porPagina() {
        return matchMedia('(max-width: 640px)').matches ? 6 : 9;
      }

      function personasFiltradas() {
        var busca = filtro.value.trim().toLowerCase();
        return etiquetas.filter(function (l) {
          return !busca || l.dataset.nombre.indexOf(busca) !== -1;
        });
      }

      function mostrarPagina() {
        var visibles = personasFiltradas();
        var paginas = Math.max(1, Math.ceil(visibles.length / porPagina()));
        paginaActual = Math.max(0, Math.min(paginaActual, paginas - 1));
        var desde = paginaActual * porPagina();
        var enPagina = visibles.slice(desde, desde + porPagina());
        etiquetas.forEach(function (l) {
          l.hidden = enPagina.indexOf(l) === -1;
        });
        if (paginaGente) {
          paginaGente.textContent = 'PÁGINA ' + (paginaActual + 1) + ' / ' + paginas;
        }
        if (anteriorGente) anteriorGente.disabled = paginaActual === 0;
        if (siguienteGente) siguienteGente.disabled = paginaActual >= paginas - 1;
        if (limpiarFiltro) limpiarFiltro.hidden = !filtro.value;
      }

      filtro.addEventListener('input', function () {
        paginaActual = 0;
        mostrarPagina();
      });
      if (limpiarFiltro) {
        limpiarFiltro.addEventListener('click', function () {
          filtro.value = '';
          paginaActual = 0;
          mostrarPagina();
          filtro.focus();
        });
      }
      if (anteriorGente) {
        anteriorGente.addEventListener('click', function () {
          paginaActual -= 1;
          mostrarPagina();
        });
      }
      if (siguienteGente) {
        siguienteGente.addEventListener('click', function () {
          paginaActual += 1;
          mostrarPagina();
        });
      }
      etiquetas.forEach(function (l) {
        l.querySelector('input').addEventListener('change', contar);
      });
      addEventListener('resize', mostrarPagina);
      contar();
      mostrarPagina();
    }

    // 6. Confirmación sólo donde se borra algo grande.
    document.querySelectorAll('[data-confirmar]').forEach(function (f) {
      f.addEventListener('submit', function (ev) {
        if (!confirm(f.dataset.confirmar)) ev.preventDefault();
      });
    });

    // 7. Al abrir un bloque para añadir, llevar el foco a su primer campo.
    document.querySelectorAll('details.anadir').forEach(function (detalle) {
      detalle.addEventListener('toggle', function () {
        if (!detalle.open) return;
        var campo = detalle.querySelector('input:not([type="hidden"]), select, textarea');
        if (campo) campo.focus();
      });
    });

    // 8. Selectores integrados: buscan sin abrir controles nativos. El de la
    //    ficha exige una elección; los del alta son opcionales y clonables.
    var contadorSelectoresPersona = 0;
    function iniciarSelectorPersona(selector) {
      if (!selector || selector.__relacionesIniciado) return;
      selector.__relacionesIniciado = true;
      var buscar = selector.querySelector('[data-selector-buscar]');
      var limpiar = selector.querySelector('[data-selector-limpiar]');
      var valor = selector.querySelector('[data-selector-valor]');
      var eleccion = selector.querySelector('[data-selector-eleccion]');
      var resultados = selector.querySelector('[role="listbox"]');
      var opciones = Array.from(selector.querySelectorAll('[role="option"][data-id]'));
      var formulario = selector.closest('form');
      var opcional = selector.hasAttribute('data-selector-opcional');
      var nombresRelacion = formulario
        ? formulario.querySelectorAll('[data-relacion-otra]') : [];
      if (!buscar || !valor) return;
      if (resultados && !resultados.id) {
        contadorSelectoresPersona += 1;
        resultados.id = 'selector-personas-' + contadorSelectoresPersona;
      }
      if (resultados) buscar.setAttribute('aria-controls', resultados.id);

      function normalizar(texto) {
        return String(texto || '').normalize('NFD')
          .replace(/[\u0300-\u036f]/g, '').toLowerCase();
      }

      function filtrarOpciones() {
        var texto = normalizar(buscar.value.trim());
        opciones.forEach(function (opcion) {
          opcion.hidden = !!texto && normalizar(opcion.textContent).indexOf(texto) === -1;
        });
        if (limpiar) limpiar.hidden = !buscar.value;
      }

      function mostrarResultados(mostrar) {
        if (resultados) resultados.hidden = !mostrar;
        buscar.setAttribute('aria-expanded', String(mostrar));
      }

      function nombrarRelacion(nombre) {
        nombresRelacion.forEach(function (lugar) {
          lugar.textContent = nombre || 'la otra persona';
        });
      }

      opciones.forEach(function (opcion) {
        opcion.addEventListener('click', function () {
          var nombre = opcion.querySelector('span').textContent.trim();
          valor.value = opcion.dataset.id;
          opciones.forEach(function (otra) {
            otra.setAttribute('aria-selected', String(otra === opcion));
          });
          buscar.value = nombre;
          if (eleccion) {
            eleccion.textContent = 'Elegida: ' + opcion.textContent.trim().replace(/\s+/g, ' ');
          }
          nombrarRelacion(nombre);
          filtrarOpciones();
          mostrarResultados(false);
          var fila = selector.closest('[data-relacion-alta]');
          var siguiente = fila
            ? fila.querySelector('input[name="etiquetas"]')
            : (formulario ? formulario.querySelector('input[name="etiqueta"]') : null);
          if (siguiente) siguiente.focus();
        });
      });

      buscar.addEventListener('input', function () {
        if (valor.value) {
          valor.value = '';
          opciones.forEach(function (opcion) {
            opcion.setAttribute('aria-selected', 'false');
          });
          if (eleccion) {
            eleccion.textContent = opcional
              ? 'Opcional: elige una persona.'
              : 'Elige una persona de la lista.';
          }
          nombrarRelacion('');
        }
        filtrarOpciones();
        mostrarResultados(true);
      });
      buscar.addEventListener('focus', function () {
        filtrarOpciones();
        mostrarResultados(true);
      });
      buscar.addEventListener('keydown', function (ev) {
        if (ev.key !== 'Escape') return;
        mostrarResultados(false);
        buscar.blur();
      });

      if (limpiar) {
        limpiar.addEventListener('click', function () {
          buscar.value = '';
          valor.value = '';
          opciones.forEach(function (opcion) {
            opcion.setAttribute('aria-selected', 'false');
          });
          if (eleccion) {
            eleccion.textContent = opcional
              ? 'Opcional: elige una persona.'
              : 'Elige una persona de la lista.';
          }
          nombrarRelacion('');
          filtrarOpciones();
          mostrarResultados(true);
          buscar.focus();
        });
      }

      if (formulario) {
        formulario.addEventListener('submit', function (ev) {
          if (valor.value || opcional) return;
          ev.preventDefault();
          if (eleccion) eleccion.textContent = 'Elige primero una persona.';
          mostrarResultados(true);
          buscar.focus();
        });
      }
      document.addEventListener('click', function (ev) {
        if (!selector.contains(ev.target)) mostrarResultados(false);
      });
      mostrarResultados(false);
    }

    document.querySelectorAll('[data-selector-persona]').forEach(iniciarSelectorPersona);

    var selectorCanal = document.querySelector('[data-selector-canal]');
    if (selectorCanal) {
      var buscarCanal = selectorCanal.querySelector('[data-canal-buscar]');
      var limpiarCanal = selectorCanal.querySelector('[data-canal-limpiar]');
      var resultadosCanal = selectorCanal.querySelector('[role="listbox"]');
      var canales = Array.from(selectorCanal.querySelectorAll('[data-canal]'));

      function normalizarCanal(texto) {
        return String(texto || '').normalize('NFD')
          .replace(/[\u0300-\u036f]/g, '').toLowerCase();
      }

      function filtrarCanales() {
        var busca = normalizarCanal(buscarCanal.value);
        var mostrados = 0;
        canales.forEach(function (opcion) {
          var coincide = !busca || normalizarCanal(opcion.textContent).indexOf(busca) !== -1;
          opcion.hidden = !coincide || mostrados >= 6;
          if (coincide && mostrados < 6) mostrados += 1;
        });
        if (limpiarCanal) limpiarCanal.hidden = !buscarCanal.value;
      }

      function mostrarCanales(mostrar) {
        resultadosCanal.hidden = !mostrar || !canales.length;
        buscarCanal.setAttribute('aria-expanded', String(mostrar && canales.length));
      }

      buscarCanal.addEventListener('focus', function () {
        filtrarCanales();
        mostrarCanales(true);
      });
      buscarCanal.addEventListener('input', function () {
        filtrarCanales();
        mostrarCanales(true);
      });
      buscarCanal.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape') {
          mostrarCanales(false);
          buscarCanal.blur();
        }
      });
      canales.forEach(function (opcion) {
        opcion.addEventListener('click', function () {
          buscarCanal.value = opcion.dataset.canal;
          filtrarCanales();
          mostrarCanales(false);
        });
      });
      if (limpiarCanal) {
        limpiarCanal.addEventListener('click', function () {
          buscarCanal.value = '';
          filtrarCanales();
          mostrarCanales(true);
          buscarCanal.focus();
        });
      }
      document.addEventListener('click', function (ev) {
        if (!selectorCanal.contains(ev.target)) mostrarCanales(false);
      });
      filtrarCanales();
      mostrarCanales(false);
    }

    // 9. El alta de una persona admite varias relaciones sin convertir el
    //    formulario en una interfaz aparte: cada fila conserva controles HTML
    //    normales y se puede quitar antes de guardar.
    var relacionesAlta = document.querySelector('[data-relaciones-alta]');
    var anadirRelacion = document.querySelector('[data-anadir-relacion]');
    if (relacionesAlta && anadirRelacion) {
      function actualizarFilasAlta() {
        var filas = relacionesAlta.querySelectorAll('[data-relacion-alta]');
        filas.forEach(function (fila) {
          var quitar = fila.querySelector('[data-quitar-relacion]');
          if (quitar) quitar.hidden = filas.length === 1;
        });
      }

      anadirRelacion.addEventListener('click', function () {
        var modelo = relacionesAlta.querySelector('[data-relacion-alta]');
        if (!modelo) return;
        var nueva = modelo.cloneNode(true);
        nueva.querySelectorAll('input').forEach(function (campo) {
          campo.value = '';
        });
        nueva.querySelectorAll('select').forEach(function (campo) {
          campo.selectedIndex = 0;
        });
        nueva.querySelectorAll('[role="option"]').forEach(function (opcion) {
          opcion.setAttribute('aria-selected', 'false');
        });
        var resultadosNuevos = nueva.querySelector('[role="listbox"]');
        if (resultadosNuevos) {
          resultadosNuevos.hidden = true;
          resultadosNuevos.removeAttribute('id');
        }
        var buscadorNuevo = nueva.querySelector('[data-selector-buscar]');
        if (buscadorNuevo) {
          buscadorNuevo.setAttribute('aria-expanded', 'false');
          buscadorNuevo.removeAttribute('aria-controls');
        }
        var eleccion = nueva.querySelector('[data-selector-eleccion]');
        if (eleccion) eleccion.textContent = 'Opcional: elige una persona.';
        relacionesAlta.appendChild(nueva);
        iniciarSelectorPersona(nueva.querySelector('[data-selector-persona]'));
        actualizarFilasAlta();
        var primera = nueva.querySelector('[data-selector-buscar], input');
        if (primera) primera.focus();
      });

      relacionesAlta.addEventListener('click', function (ev) {
        var quitar = ev.target.closest('[data-quitar-relacion]');
        if (!quitar) return;
        var fila = quitar.closest('[data-relacion-alta]');
        if (fila) fila.remove();
        actualizarFilasAlta();
      });
      actualizarFilasAlta();
    }

    // 10. El archivador cambia carpeta, persona y página en el mismo sitio.
    //     Conserva enlaces y formularios normales como respaldo, pero con
    //     JavaScript no recarga ni mueve la ventana un solo píxel.
    var archivador = document.querySelector('.archivador');
    if (archivador) {
      var archivoCargando = false;

      function esNavegacionDelArchivo(enlace) {
        return enlace.closest(
          '.archivo-carpetas, .archivo-personas, .archivo-paginacion, ' +
          '.archivo-busqueda'
        ) || enlace.classList.contains('archivo-volver');
      }

      function urlDelArchivo(destino) {
        try {
          var url = new URL(destino, location.href);
          return url.origin === location.origin && url.pathname === '/personas'
            ? url : null;
        } catch (e) {
          return null;
        }
      }

      function reemplazarArchivo(url, guardarEnHistorial) {
        if (archivoCargando) return Promise.resolve();
        archivoCargando = true;
        var posicion = window.scrollY;
        archivador.setAttribute('aria-busy', 'true');

        return fetch(url.href, {
          headers: { 'X-Requested-With': 'relaciones-archivador' }
        }).then(function (respuesta) {
          if (!respuesta.ok) throw new Error('No se pudo abrir el archivador');
          return respuesta.text();
        }).then(function (html) {
          var documento = new DOMParser().parseFromString(html, 'text/html');
          var nuevo = documento.querySelector('.archivador');
          if (!nuevo) throw new Error('El archivador recibido no es válido');
          archivador.replaceWith(nuevo);
          archivador = nuevo;
          if (guardarEnHistorial) {
            // El ancla sigue en los enlaces como respaldo sin JavaScript, pero
            // no entra en el historial dinámico: cambiar el hash recolocaría la
            // ventana aunque el contenido se actualice en el mismo sitio.
            history.pushState({ archivador: true }, '', url.pathname + url.search);
          }
          window.scrollTo(0, posicion);
          requestAnimationFrame(function () {
            window.scrollTo(0, posicion);
            requestAnimationFrame(function () {
              window.scrollTo(0, posicion);
            });
          });
        }).catch(function () {
          location.href = url.href;
        }).finally(function () {
          archivoCargando = false;
          archivador.removeAttribute('aria-busy');
        });
      }

      document.addEventListener('click', function (ev) {
        if (
          ev.defaultPrevented || ev.button !== 0 || ev.ctrlKey || ev.metaKey
          || ev.shiftKey || ev.altKey
        ) return;
        var enlace = ev.target.closest('a[href]');
        if (!enlace || !archivador.contains(enlace) || !esNavegacionDelArchivo(enlace)) {
          return;
        }
        var url = urlDelArchivo(enlace.href);
        if (!url) return;
        ev.preventDefault();
        reemplazarArchivo(url, true);
      });

      document.addEventListener('submit', function (ev) {
        var formulario = ev.target;
        if (
          ev.defaultPrevented || !formulario.matches('.archivo-busqueda')
          || !archivador.contains(formulario)
        ) return;
        var url = urlDelArchivo(formulario.action);
        if (!url) return;
        var parametros = new URLSearchParams(new FormData(formulario));
        url.search = parametros.toString();
        ev.preventDefault();
        reemplazarArchivo(url, true);
      });

      addEventListener('popstate', function () {
        var url = urlDelArchivo(location.href);
        if (url) reemplazarArchivo(url, false);
      });
    }

    // 11. Toda recarga que vuelve a la misma pantalla conserva su posición.
    //     Los enlaces con un ancla expresa mandan: el navegador lleva al bloque
    //     indicado. Esta regla evita que añadir, editar o filtrar mande arriba.
    document.addEventListener('submit', function (ev) {
      var formulario = ev.target;
      if (ev.defaultPrevented || !formulario) return;
      try {
        var destino = new URL(formulario.action || location.href, location.href);
        if (destino.origin === location.origin) guardarPosicion(location.pathname);
      } catch (e) { /* sin sessionStorage */ }
    });

    document.addEventListener('click', function (ev) {
      if (ev.defaultPrevented || ev.button !== 0) return;
      var enlace = ev.target.closest('a[href]');
      if (!enlace || enlace.target || enlace.hasAttribute('download')) return;
      try {
        var destino = new URL(enlace.href, location.href);
        if (
          destino.origin === location.origin
          && destino.pathname === location.pathname
          && !destino.hash
        ) {
          guardarPosicion(destino.pathname);
        }
      } catch (e) { /* enlace no navegable */ }
    });

    if (posicionPendiente
        && posicionPendiente.ruta === location.pathname
        && !location.hash) {
      window.addEventListener('load', function () {
        var restaurar = function () {
          requestAnimationFrame(function () {
            requestAnimationFrame(function () {
              var limite = Math.max(
                0, document.documentElement.scrollHeight - window.innerHeight
              );
              window.scrollTo({
                left: 0,
                top: Math.max(0, Math.min(posicionPendiente.y, limite)),
                behavior: 'instant'
              });
            });
          });
        };
        if (document.fonts && document.fonts.ready) {
          document.fonts.ready.then(restaurar);
        } else {
          restaurar();
        }
      });
    }
  });
})();
