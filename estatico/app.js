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

  // En una pantalla táctil, llevar el foco a un campo abre el teclado y tapa
  // media pantalla. Sólo se enfoca solo cuando hay ratón.
  function enfocar(campo) {
    if (!campo) return;
    if (matchMedia('(pointer: coarse)').matches) return;
    campo.focus();
  }

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
          enfocar(filtro);
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

    // 6. Confirmación sólo donde se borra algo grande. Diálogo propio en vez
    //    del confirm() del navegador, que sale pegado arriba, sin estilo y
    //    anunciando la dirección del servidor. Si el navegador no soporta
    //    <dialog>, se cae al confirm() de siempre antes que quedarse sin aviso.
    var dialogo = document.getElementById('confirmar');
    var textoDialogo = dialogo && dialogo.querySelector('[data-confirmar-texto]');
    var puedeDialogo = dialogo && typeof dialogo.showModal === 'function';
    var pendiente = null;

    function enviarPendiente() {
      var f = pendiente;
      pendiente = null;
      if (!f) return;
      f.dataset.confirmado = 'si';
      if (f.requestSubmit) f.requestSubmit(); else f.submit();
    }

    if (puedeDialogo) {
      // La decisión cuelga del clic de cada botón, no del evento `close` del
      // diálogo: hay navegadores donde `close` no llega a dispararse, y ahí
      // borrar se quedaría en nada sin decir por qué.
      var siDialogo = dialogo.querySelector('[data-confirmar-si]');
      var noDialogo = dialogo.querySelector('[data-confirmar-no]');
      if (siDialogo) {
        siDialogo.addEventListener('click', function () {
          dialogo.close('si');
          enviarPendiente();
        });
      }
      if (noDialogo) {
        noDialogo.addEventListener('click', function () {
          pendiente = null;
          dialogo.close('no');
        });
      }
      // Escape cierra sin borrar, que es lo que se espera.
      dialogo.addEventListener('cancel', function () { pendiente = null; });
    }

    document.querySelectorAll('[data-confirmar]').forEach(function (f) {
      f.addEventListener('submit', function (ev) {
        if (f.dataset.confirmado === 'si') {
          delete f.dataset.confirmado;
          return;
        }
        ev.preventDefault();
        if (!puedeDialogo) {
          if (confirm(f.dataset.confirmar)) {
            pendiente = f;
            enviarPendiente();
          }
          return;
        }
        pendiente = f;
        textoDialogo.textContent = f.dataset.confirmar;
        dialogo.returnValue = 'no';
        dialogo.showModal();
        // El foco arranca en Cancelar: borrar nunca es el camino por inercia.
        if (noDialogo) noDialogo.focus();
      });
    });

    // 7. Al abrir un bloque para añadir, llevar el foco a su primer campo.
    //    Con el dedo no: abriría el teclado sin haber tocado ninguna caja.
    document.querySelectorAll('details.anadir').forEach(function (detalle) {
      detalle.addEventListener('toggle', function () {
        if (!detalle.open) return;
        enfocar(detalle.querySelector('input:not([type="hidden"]), select, textarea'));
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
          enfocar(fila
            ? fila.querySelector('input[name="etiquetas"]')
            : (formulario ? formulario.querySelector('input[name="etiqueta"]') : null));
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
          enfocar(buscar);
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
          enfocar(buscarCanal);
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
        enfocar(nueva.querySelector('[data-selector-buscar], input'));
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

    // 9 bis. La fecha de una quedada. Casi siempre es de estos días, así que
    //        delante van los atajos y el calendario queda detrás, plegado.
    //        Todo son botones: desplegarlo no abre el teclado.
    var campoFecha = document.querySelector('[data-fecha]');
    if (campoFecha) {
      var DIAS_CORTOS = ['DOM', 'LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB'];
      var MESES_FECHA = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
      var ATAJOS = 6;

      // El campo que se envía lo crea el JavaScript: sin él manda el
      // <noscript>, y así nunca viajan dos «fecha» a la vez.
      var valorFecha = document.createElement('input');
      valorFecha.type = 'hidden';
      valorFecha.name = 'fecha';
      campoFecha.appendChild(valorFecha);

      var atajos = campoFecha.querySelector('[data-fecha-atajos]');
      var elegida = campoFecha.querySelector('[data-fecha-elegida]');
      var abrirFecha = campoFecha.querySelector('[data-fecha-abrir]');
      var signoFecha = campoFecha.querySelector('[data-fecha-signo]');
      var calendario = campoFecha.querySelector('[data-fecha-calendario]');
      var tituloMes = campoFecha.querySelector('[data-fecha-titulo]');
      var rejilla = campoFecha.querySelector('[data-fecha-dias]');

      function aIso(d) {
        return d.getFullYear() + '-' +
          String(d.getMonth() + 1).padStart(2, '0') + '-' +
          String(d.getDate()).padStart(2, '0');
      }

      function deIso(iso) {
        var trozos = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
        if (!trozos) return null;
        var d = new Date(+trozos[1], +trozos[2] - 1, +trozos[3]);
        return isNaN(d.getTime()) ? null : d;
      }

      var hoy = new Date();
      hoy.setHours(0, 0, 0, 0);
      var seleccion = deIso(campoFecha.dataset.fechaInicial) || new Date(hoy);
      var mesVisible = new Date(
        seleccion.getFullYear(), seleccion.getMonth(), 1
      );

      function enPalabras(d) {
        var texto = d.getDate() + ' de ' + MESES_FECHA[d.getMonth()];
        return d.getFullYear() === hoy.getFullYear()
          ? texto : texto + ' de ' + d.getFullYear();
      }

      function boton(iso, texto, clase) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = clase;
        b.dataset.iso = iso;
        b.textContent = texto;
        b.setAttribute('aria-pressed', String(iso === aIso(seleccion)));
        return b;
      }

      function pintarAtajos() {
        atajos.textContent = '';
        for (var i = 0; i < ATAJOS; i++) {
          var d = new Date(hoy);
          d.setDate(hoy.getDate() - i);
          var nombre = i === 0 ? 'HOY'
            : i === 1 ? 'AYER'
            : DIAS_CORTOS[d.getDay()] + ' ' + d.getDate();
          atajos.appendChild(boton(aIso(d), nombre, 'fecha-atajo'));
        }
      }

      function pintarCalendario() {
        tituloMes.textContent = (
          MESES_FECHA[mesVisible.getMonth()] + ' ' + mesVisible.getFullYear()
        ).toUpperCase();
        rejilla.textContent = '';
        var anio = mesVisible.getFullYear(), mes = mesVisible.getMonth();
        var hueco = (new Date(anio, mes, 1).getDay() + 6) % 7;  // lunes primero
        var cuantos = new Date(anio, mes + 1, 0).getDate();
        for (var h = 0; h < hueco; h++) {
          var vacio = document.createElement('span');
          vacio.className = 'fecha-hueco';
          rejilla.appendChild(vacio);
        }
        for (var dia = 1; dia <= cuantos; dia++) {
          var iso = aIso(new Date(anio, mes, dia));
          var celda = boton(iso, String(dia), 'fecha-dia');
          if (iso === aIso(hoy)) celda.classList.add('es-hoy');
          rejilla.appendChild(celda);
        }
      }

      function pintarFecha() {
        valorFecha.value = aIso(seleccion);
        elegida.textContent = enPalabras(seleccion);
        pintarAtajos();
        pintarCalendario();
      }

      function elegirDesde(ev) {
        var b = ev.target.closest('[data-iso]');
        if (!b) return;
        var d = deIso(b.dataset.iso);
        if (!d) return;
        seleccion = d;
        mesVisible = new Date(d.getFullYear(), d.getMonth(), 1);
        pintarFecha();
      }

      atajos.addEventListener('click', elegirDesde);
      rejilla.addEventListener('click', elegirDesde);

      campoFecha.querySelector('[data-fecha-antes]')
        .addEventListener('click', function () {
          mesVisible.setMonth(mesVisible.getMonth() - 1);
          pintarCalendario();
        });
      campoFecha.querySelector('[data-fecha-despues]')
        .addEventListener('click', function () {
          mesVisible.setMonth(mesVisible.getMonth() + 1);
          pintarCalendario();
        });

      abrirFecha.addEventListener('click', function () {
        var cerrado = calendario.hidden;
        calendario.hidden = !cerrado;
        abrirFecha.setAttribute('aria-expanded', String(cerrado));
        if (signoFecha) signoFecha.textContent = cerrado ? '−' : '+';
      });

      campoFecha.hidden = false;
      pintarFecha();
    }

    // 9 ter. La ficha completa: cada bloque se pliega y entra en edición por su
    //        cuenta. Abrir uno no abre los demás. El ocultado lo enciende este
    //        JavaScript, así que sin él la ficha se ve entera, como siempre.
    document.querySelectorAll('[data-bloque]').forEach(function (bloque) {
      var plegar = bloque.querySelector('[data-plegar]');
      var cuerpo = plegar
        ? document.getElementById(plegar.getAttribute('aria-controls'))
        : null;
      var editar = bloque.querySelector('[data-editar]');

      function pintarPliegue(abierto) {
        plegar.setAttribute('aria-expanded', String(abierto));
        cuerpo.hidden = !abierto;
        var signo = plegar.querySelector('.bloque-signo');
        if (signo) signo.textContent = abierto ? '−' : '+';
      }

      if (plegar && cuerpo) {
        plegar.addEventListener('click', function () {
          pintarPliegue(plegar.getAttribute('aria-expanded') !== 'true');
        });
      }

      if (editar) {
        // Si el servidor manda un aviso, ese bloque arranca ya en edición.
        var arranca = bloque.querySelector('[data-abierto]') ? 'si' : 'no';
        bloque.dataset.edicion = arranca;
        editar.setAttribute('aria-pressed', String(arranca === 'si'));

        editar.addEventListener('click', function () {
          var editando = bloque.dataset.edicion === 'si';
          bloque.dataset.edicion = editando ? 'no' : 'si';
          editar.setAttribute('aria-pressed', String(!editando));
          // Entrar a editar un bloque plegado lo abre; no tendría sentido
          // encender los botones de algo que no se ve.
          if (!editando && cuerpo && cuerpo.hidden) pintarPliegue(true);
        });
      }
    });

    // 9 quater. Enlazar con varias personas a la vez. Los atajos marcan un
    //           círculo entero, que es de donde salen los grupos que se
    //           repiten: compañeros, primos, gente del barrio.
    //           Hay dos: el de la ficha y el del alta de una persona.
    document.querySelectorAll('[data-enlazar-varias]').forEach(function (caja) {
      var casillas = Array.from(
        caja.querySelectorAll('.gente input[type="checkbox"]')
      );
      var cuenta = caja.querySelector('[data-cuenta-varias]');

      var etiquetas = casillas.map(function (c) { return c.closest('label'); });
      var pagina = caja.querySelector('[data-varias-pagina]');
      var anterior = caja.querySelector('[data-varias-anterior]');
      var siguiente = caja.querySelector('[data-varias-siguiente]');
      var actual = 0;

      function porPagina() {
        return matchMedia('(max-width: 640px)').matches ? 6 : 9;
      }

      function contar() {
        if (!cuenta) return;
        var n = casillas.filter(function (c) { return c.checked; }).length;
        cuenta.textContent = n
          ? n + (n === 1 ? ' marcada' : ' marcadas')
          : 'Nadie marcado';
      }

      // Las que no se ven siguen marcadas y siguen viajando en el envío: sólo
      // se ocultan, no se desmarcan.
      function mostrarPagina() {
        var cuantas = porPagina();
        var paginas = Math.max(1, Math.ceil(etiquetas.length / cuantas));
        actual = Math.max(0, Math.min(actual, paginas - 1));
        etiquetas.forEach(function (l, i) {
          l.hidden = i < actual * cuantas || i >= (actual + 1) * cuantas;
        });
        if (pagina) pagina.textContent = 'PÁGINA ' + (actual + 1) + ' / ' + paginas;
        if (anterior) anterior.disabled = actual === 0;
        if (siguiente) siguiente.disabled = actual >= paginas - 1;
      }

      caja.querySelectorAll('[data-marcar-circulo]').forEach(function (boton) {
        boton.addEventListener('click', function () {
          var circulo = boton.dataset.marcarCirculo;
          casillas.forEach(function (casilla) {
            var suyo = casilla.closest('label').dataset.circulo;
            // Sin círculo en el botón: desmarcar todo.
            casilla.checked = circulo ? suyo === circulo : false;
          });
          contar();
        });
      });

      if (anterior) {
        anterior.addEventListener('click', function () {
          actual -= 1;
          mostrarPagina();
        });
      }
      if (siguiente) {
        siguiente.addEventListener('click', function () {
          actual += 1;
          mostrarPagina();
        });
      }
      addEventListener('resize', mostrarPagina);
      // También al desplegar: si el bloque nace plegado, la primera cuenta se
      // hizo con el ancho de entonces y podía quedarse obsoleta.
      var plegable = caja.closest('details');
      if (plegable) plegable.addEventListener('toggle', mostrarPagina);

      casillas.forEach(function (c) { c.addEventListener('change', contar); });
      contar();
      mostrarPagina();
    });

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
