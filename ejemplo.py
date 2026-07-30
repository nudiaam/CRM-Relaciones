"""Gente de ejemplo para ver la red con algo dentro.

    python ejemplo.py           mete 20 personas, sus círculos y su vida
    python ejemplo.py --quitar  las borra y deja la base como estaba

Si las personas ya están, no hace nada: primero --quitar. Al quitar borra estos
veinte nombres, lo que colgaba de ellos y las quedadas que se quedan sin nadie.
"""

import sys
from datetime import date, timedelta

import app as base

# Un círculo es de dónde conoces a alguien.
CIRCULOS = ["Amigos", "Familia", "Trabajo", "Barrio", "Hípica", "Universidad"]

# nombre, apodo, círculo, color, cumple, de un vistazo
GENTE = [
    ("Marta Ruiz", "Marti", "Amigos", "#C2452D", "--03-14", "La que siempre contesta"),
    ("Javi Alonso", "", "Amigos", "#2F5D50", "1988-11-02", ""),
    ("Sara Ibáñez", "", "Amigos", "#2F7A6B", "--07-28", ""),
    ("Nacho Puig", "", "Amigos", "#B0582F", "", "Llega tarde siempre"),
    ("Carmen Salas", "mamá", "Familia", "#B03A6E", "--01-09", ""),
    ("Pablo Nieto", "", "Familia", "#4A6E8A", "1991-04-17", "Alérgico al marisco"),
    ("Elena Prat", "", "Familia", "#7A4B8F", "--05-12", ""),
    ("Lucía Ferrer", "", "Familia", "#D08A2C", "--09-21", ""),
    ("Ana Cortés", "", "Trabajo", "#8A6A2F", "1979-02-03", "Fue mi mentora"),
    ("Miguel Duarte", "", "Trabajo", "#3A4D8F", "", ""),
    ("Borja Lamas", "", "Trabajo", "#6B7A2F", "--10-08", ""),
    ("Clara Sanz", "", "Trabajo", "#8F3A4D", "1985-08-24", "Muy directa, no hay que suavizar"),
    ("Irene Vega", "", "Barrio", "#3F7A3F", "--06-30", "Vive dos portales más abajo"),
    ("Bea Company", "", "Barrio", "#2F8F7A", "--12-05", ""),
    ("Andrés Camps", "", "Barrio", "#2F4D8A", "--02-27", ""),
    ("Diego Rey", "", "Hípica", "#8F5A2F", "", "Sabe de caballos y de hardware"),
    ("Rocío Peña", "", "Hípica", "#5A6B7A", "--04-02", ""),
    ("Silvia Roca", "", "Hípica", "#8A2F5D", "", ""),
    ("Alberto Gil", "", "Universidad", "#7A6B2F", "--11-19", ""),
    ("Tomás Vidal", "", "Universidad", "#4D5A8F", "", ""),
]

# de quién, un dato que no cambia
DATOS = [
    ("Marta Ruiz", "Odia el cilantro, no es broma"),
    ("Marta Ruiz", "Nunca coge el teléfono antes de las once"),
    ("Javi Alonso", "Toca el bajo desde los catorce"),
    ("Javi Alonso", "Vegetariano, pero come pescado"),
    ("Irene Vega", "Insomne, escribe de madrugada"),
    ("Irene Vega", "Le encanta que le recomienden libros"),
    ("Carmen Salas", "No le gusta que le manden audios largos"),
    ("Lucía Ferrer", "Estudia fisioterapia, último año"),
    ("Pablo Nieto", "Colecciona vinilos de jazz"),
    ("Bea Company", "Tiene una perra, Duna, con artrosis"),
    ("Nacho Puig", "No bebe, no hace falta insistir"),
    ("Sara Ibáñez", "Prefiere llamadas cortas a mensajes largos"),
    ("Ana Cortés", "Dos gatos, Nube y Coco"),
    ("Miguel Duarte", "Su hijo se llama Bruno"),
    ("Diego Rey", "Monta sus propios ordenadores"),
    ("Clara Sanz", "Dirige un estudio de tres personas"),
    ("Alberto Gil", "Del grupo de la universidad"),
    ("Silvia Roca", "Vive en Bilbao desde 2025"),
]

# de quién, qué, hace cuántos días se abrió, tipo
COSAS = [
    ("Javi Alonso", "Pasarle el contacto del estudio de Vallecas", 12, "pendiente"),
    ("Borja Lamas", "Le dije que le montaba la demo de vídeo", 141, "pendiente"),
    ("Clara Sanz", "Hablar de trabajar juntas en otoño", 81, "pendiente"),
    ("Alberto Gil", "Devolverle el libro que me dejó", 63, "pendiente"),
    ("Nacho Puig", "Montar sesiones de trabajo los jueves", 30, "pendiente"),
    ("Marta Ruiz", "Se examina de las oposiciones en octubre", 53, "preguntar"),
    ("Marta Ruiz", "Busca piso por el centro, presupuesto justo", 11, "preguntar"),
    ("Javi Alonso", "Graban la maqueta, se les acaba el local", 67, "preguntar"),
    ("Irene Vega", "Su madre sigue ingresada", 43, "preguntar"),
    ("Carmen Salas", "Revisión médica del 12 de agosto", 24, "preguntar"),
    ("Lucía Ferrer", "Prácticas de verano, aún sin sitio", 35, "preguntar"),
    ("Bea Company", "Se apuntó a cerámica y quiere enseñarme las piezas", 25, "preguntar"),
    ("Sara Ibáñez", "Busca quien le haga el 3D de un spot", 15, "preguntar"),
    ("Ana Cortés", "Decide si acepta el puesto de Valencia", 108, "preguntar"),
    ("Elena Prat", "Dijo que igual venía en septiembre", 56, "preguntar"),
    ("Diego Rey", "Se ha comprado una yegua joven", 20, "preguntar"),
]

# hace cuántos días, por dónde, qué, con quién
QUEDADAS = [
    (1, "en persona", "Bloque en el rocódromo. Le prometí pasarle el contacto del "
     "estudio y no se me puede olvidar otra vez.", ["Javi Alonso"]),
    (3, "en persona", "Café en la plaza. Está agotada de estudiar y lo lleva peor de "
     "lo que dice. Preguntó dos veces por lo mío, con interés de verdad.",
     ["Marta Ruiz"]),
    (6, "llamada", "Domingo. Habló casi todo el rato ella, que es buena señal. La "
     "revisión la tiene más presente de lo que admite.", ["Carmen Salas"]),
    (9, "audio de whatsapp", "Audio de siete minutos. Lo de su madre no mejora. "
     "Preguntar sin que parezca el único tema.", ["Irene Vega"]),
    (12, "en persona", "Cañas los cuatro. Marta y Javi con lo del piso, Irene "
     "callada casi todo el rato.", ["Marta Ruiz", "Javi Alonso", "Irene Vega"]),
    (15, "llamada", "Me enseñó lo que está montando. Hay una colaboración posible "
     "si la empujo yo.", ["Sara Ibáñez"]),
    (18, "en persona", "Cuadra por la mañana. Diego con la yegua nueva y Rocío "
     "aguantando la broma de siempre.", ["Diego Rey", "Rocío Peña"]),
    (19, "instagram", "Historias del viaje. Estuvimos un rato. Hace un año que sólo "
     "hablamos así.", ["Lucía Ferrer"]),
    (23, "mensajes", "Cadena del grupo. Nada personal, pero contestó él primero.",
     ["Alberto Gil", "Javi Alonso"]),
    (25, "audio de whatsapp", "Muy animada con la cerámica. Dijo de quedar para verlas.",
     ["Bea Company"]),
    (28, "en persona", "Comida familiar. Pablo estuvo raro y no le pregunté.",
     ["Pablo Nieto", "Carmen Salas"]),
    (31, "en persona", "Cerveza rápida. La idea de los jueves era suya y le hizo "
     "ilusión. Cero movimiento desde entonces.", ["Nacho Puig"]),
    (36, "instagram", "Le gustó lo que publiqué y mencionó otoño. Es lo más valioso "
     "que tengo abierto y lleva dos meses parado.", ["Clara Sanz"]),
    (44, "llamada", "Media hora larga. Sigue dándole vueltas a Valencia. Pidió que le "
     "escribiera cuando decidiera algo.", ["Ana Cortés"]),
    (51, "mensajes", "Me resolvió lo de los drivers en dos mensajes.", ["Diego Rey"]),
    (58, "en persona", "Cumpleaños de Sara. Estaban Nacho y Diego, que no se veían "
     "desde hace años.", ["Sara Ibáñez", "Nacho Puig", "Diego Rey"]),
    (67, "llamada", "Corta. Bilbao le gusta más de lo que esperaba.", ["Silvia Roca"]),
    (74, "linkedin", "Le felicité por el ascenso. Respondió con una parrafada, tiene "
     "ganas de hablar.", ["Miguel Duarte"]),
    (88, "mensajes", "Me preguntó por las herramientas nuevas. Le dije que le montaba "
     "una demo. No lo hice.", ["Borja Lamas"]),
    (96, "en persona", "Cena en su casa. Silvia y Andrés recién vueltos.",
     ["Silvia Roca", "Andrés Camps"]),
    (112, "llamada", "Ana y Miguel me llamaron juntos para lo del proyecto viejo.",
     ["Ana Cortés", "Miguel Duarte"]),
    (140, "linkedin", "Contacto de cortesía. Escribe correos de una sola línea.",
     ["Tomás Vidal"]),
    (168, "instagram", "Felicitación de cumpleaños y poco más.", ["Rocío Peña"]),
    (205, "en persona", "Boda de Elena. Vi a media familia de golpe.",
     ["Elena Prat", "Carmen Salas", "Pablo Nieto"]),
    (260, "mensajes", "Andrés preguntó por el piso de arriba.", ["Andrés Camps"]),
    (330, "linkedin", "Coincidimos en el fablab, hace ya.", ["Rocío Peña", "Ana Cortés"]),
]

# A, B, qué es B de A, qué es A de B
LAZOS = [
    ("Marta Ruiz", "Lucía Ferrer", "hermana de", "hermana de"),
    ("Marta Ruiz", "Javi Alonso", "su pareja", "su pareja"),
    ("Irene Vega", "Bea Company", "vecina de", "vecina de"),
    ("Carmen Salas", "Pablo Nieto", "hijo de", "madre de"),
    ("Carmen Salas", "Elena Prat", "hermana de", "hermana de"),
    ("Ana Cortés", "Miguel Duarte", "trabajó con", "trabajó con"),
    ("Ana Cortés", "Borja Lamas", "trabajó para", "jefa de"),
    ("Sara Ibáñez", "Nacho Puig", "socio de", "socia de"),
    ("Sara Ibáñez", "Diego Rey", "amigo de", "amiga de"),
    ("Clara Sanz", "Tomás Vidal", "montó el estudio con", "montó el estudio con"),
    ("Rocío Peña", "Ana Cortés", "coincidió con", "coincidió con"),
    ("Alberto Gil", "Javi Alonso", "del grupo de la uni con", "del grupo de la uni con"),
    ("Silvia Roca", "Andrés Camps", "su pareja", "su pareja"),
    ("Nacho Puig", "Diego Rey", "primo de", "primo de"),
    ("Miguel Duarte", "Tomás Vidal", "trabaja con", "trabaja con"),
    ("Diego Rey", "Rocío Peña", "monta con", "monta con"),
]

NOMBRES = [g[0] for g in GENTE]
HUECOS = ",".join("?" * len(NOMBRES))


def hace(dias):
    return (date.today() - timedelta(days=dias)).isoformat()


def poner():
    con = base.conexion()
    ya = con.execute(
        f"SELECT COUNT(*) AS n FROM persona WHERE nombre IN ({HUECOS})", NOMBRES
    ).fetchone()["n"]
    if ya:
        con.close()
        print(f"Ya hay {ya} de estas personas dentro; no toco nada para no "
              f"duplicar lo suyo.\nPara empezar de cero: python ejemplo.py --quitar")
        return

    with con:
        for nombre in CIRCULOS:
            if not con.execute(
                "SELECT 1 FROM circulo WHERE nombre = ?", (nombre,)
            ).fetchone():
                fila = con.execute("SELECT MAX(orden) AS m FROM circulo").fetchone()
                con.execute(
                    "INSERT INTO circulo (nombre, orden) VALUES (?, ?)",
                    (nombre, (fila["m"] or 0) + 1),
                )
        circulos = {
            f["nombre"]: f["id"] for f in con.execute("SELECT id, nombre FROM circulo")
        }

        ids = {}
        for nombre, apodo, circulo, color, cumple, vistazo in GENTE:
            ids[nombre] = con.execute(
                "INSERT INTO persona (nombre, apodo, circulo_id, color, cumple,"
                " notas_rapidas, creada) VALUES (?,?,?,?,?,?,?)",
                (nombre, apodo, circulos.get(circulo), color, cumple, vistazo,
                 base.ahora_iso()),
            ).lastrowid

        for quien, texto in DATOS:
            con.execute(
                "INSERT INTO hecho (persona_id, texto, creado) VALUES (?,?,?)",
                (ids[quien], texto, base.ahora_iso()),
            )

        for quien, texto, dias, tipo in COSAS:
            con.execute(
                "INSERT INTO hilo (persona_id, texto, abierto_desde, tipo)"
                " VALUES (?,?,?,?)",
                (ids[quien], texto, hace(dias), tipo),
            )

        for dias, canal, texto, quienes in QUEDADAS:
            quedada = con.execute(
                "INSERT INTO nota (fecha, canal, texto, creada) VALUES (?,?,?,?)",
                (hace(dias), canal, texto, base.ahora_iso()),
            ).lastrowid
            for quien in quienes:
                con.execute(
                    "INSERT INTO nota_persona (nota_id, persona_id) VALUES (?,?)",
                    (quedada, ids[quien]),
                )

        for a, b, etiqueta, inversa in LAZOS:
            con.execute(
                "INSERT OR REPLACE INTO relacion (persona_a, persona_b, etiqueta,"
                " etiqueta_inversa) VALUES (?,?,?,?)",
                (ids[a], ids[b], etiqueta, inversa),
            )
    con.close()
    print(f"Puestas {len(GENTE)} personas en {len(CIRCULOS)} círculos, "
          f"{len(QUEDADAS)} quedadas, {len(COSAS)} cosas abiertas, "
          f"{len(DATOS)} datos y {len(LAZOS)} lazos.")
    print("Abre la app y mira la portada.")


def quitar():
    con = base.conexion()
    with con:
        fuera = con.execute(
            f"SELECT COUNT(*) AS n FROM persona WHERE nombre IN ({HUECOS})", NOMBRES
        ).fetchone()["n"]
        con.execute(f"DELETE FROM persona WHERE nombre IN ({HUECOS})", NOMBRES)
        # quedadas que se han quedado sin nadie
        con.execute(
            "DELETE FROM nota WHERE id NOT IN (SELECT nota_id FROM nota_persona)"
        )
        for nombre in CIRCULOS:
            con.execute(
                "DELETE FROM circulo WHERE nombre = ? AND id NOT IN"
                " (SELECT circulo_id FROM persona WHERE circulo_id IS NOT NULL)",
                (nombre,),
            )
    con.close()
    print(f"Quitadas {fuera} personas de ejemplo y lo que colgaba de ellas.")


if __name__ == "__main__":
    if "--quitar" in sys.argv:
        quitar()
    else:
        poner()
