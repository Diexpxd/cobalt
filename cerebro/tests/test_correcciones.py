"""Correcciones de la primera tanda de pruebas en juego (lado Python): 'ven' no es 'sígueme', 'guarda esta base', y guardar lugares con el jugador en otra dimensión."""
import io
import json
import os
import tempfile

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
ns["WAYPOINTS_FILE"] = os.path.join(tmp, "waypoints.json")
ns["GPS_FILE"] = os.path.join(tmp, "gps.json")
ns["CONFIG_FILE"] = os.path.join(tmp, "cobalt_config.json")
ns["config_activa"] = lambda clave, defecto=True: True


def escribir(ruta, contenido):
    io.open(ruta, "w", encoding="utf-8").write(contenido if isinstance(contenido, str) else json.dumps(contenido))


o = ns["aplicar_cortocircuito"]("ven", "Steve")
r.check("ven: ahora envía la acción 'ven' (ir UNA vez y parar), NO 'follow'", o and o[0]["action"] == "ven" and o[0]["movement_mode"] == "fly")
r.check("ven: deja de marcar 'me sigue' (el flag que hacía que siguiera sin parar)", ns["COBALT_ME_SIGUE"] is False)
for frase in ("ven aquí", "ven aqui", "acércate", "acercate"):
    x = ns["aplicar_cortocircuito"](frase, "Steve")
    r.check(f"ven: la variante '{frase}' también es 'ven'", x and x[0]["action"] == "ven")
o = ns["aplicar_cortocircuito"]("sígueme", "Steve")
r.check("REGRESIÓN: 'sígueme' sigue siendo 'follow' y marca que lo sigue (no se rompe seguirme)", o and o[0]["action"] == "follow" and ns["COBALT_ME_SIGUE"] is True)
o = ns["aplicar_cortocircuito"]("follow me", "Steve")
r.check("REGRESIÓN: 'follow me' también sigue igual", o and o[0]["action"] == "follow")
ns["aplicar_cortocircuito"]("ven", "Steve")
o = ns["aplicar_cortocircuito"]("stop", "Steve")
r.check("REGRESIÓN: 'stop' sigue deteniendo (action stop y flag apagado)", o and o[0]["action"] == "stop" and ns["COBALT_ME_SIGUE"] is False)

g = ns["es_orden_guardar_lugar"]
for frase in ("guarda esta base", "Guarda esta base sin más palabras", "marca este punto", "guarda este lugar como mina", "guarda aquí como base",
              "Cobalt, guarda esta zona", "anota esta ubicación", "por favor guarda este sitio", "guarda esta base como base principal"):
    r.check(f"guardar: '{frase}' es una orden de guardar lugar", g(frase))
for frase in ("guarda todo en el cofre", "guarda la base de datos", "guardar cosas", "hola cobalt", "esta base es genial", "dónde guardaste la base", "", None, "guarda el hierro"):
    r.check(f"guardar: '{frase}' NO lo es", not g(frase))

e = ns["extraer_nombre_waypoint"]
r.check("nombre: 'guarda esta base' -> base", e("guarda esta base") == "base")
r.check("nombre: 'guarda esta base sin más palabras' -> base (el relleno NO forma parte del nombre)", e("guarda esta base sin más palabras") == "base")
r.check("nombre: 'guarda esta base como base sin más palabras' -> base", e("guarda esta base como base sin más palabras") == "base")
r.check("nombre: 'guarda este lugar como mina por favor' -> mina", e("guarda este lugar como mina por favor") == "mina")
r.check("nombre: 'Cobalt, guarda este lugar como Mina Norte' -> mina_norte", e("Cobalt, guarda este lugar como Mina Norte") == "mina_norte")
r.check("REGRESIÓN: los nombres de siempre no cambian ('como base secundaria', 'para la base', 'llamada Mina Norte')",
        e("guarda este lugar como base secundaria") == "base_secundaria" and e("guarda este lugar para la base") == "base" and e("guarda esta zona llamada Mina Norte") == "mina_norte")
r.check("REGRESIÓN: sin nombre ni 'base' sigue vacío", e("guarda este lugar") == "")

escribir(ns["GPS_FILE"], {"x": 10, "y": 64, "z": 20, "dimension": "minecraft:overworld",
                          "owner_remote": {"x": 5, "y": 70, "z": -9, "dimension": "minecraft:the_nether"}})
msg = ns["gestionar_waypoints"]("guardar", "guarda esta base")
wp = json.loads(io.open(ns["WAYPOINTS_FILE"], encoding="utf-8").read())
r.check("otra dimensión: guarda el lugar donde ESTÁ EL JUGADOR (5, 70, -9), no donde está Cobalt", wp.get("base", {}).get("x") == 5 and wp["base"]["z"] == -9)
r.check("otra dimensión: con SU dimensión (el Nether), no la de Cobalt", wp["base"].get("dimension") == "minecraft:the_nether")
r.check("otra dimensión: no se cuela ninguna clave interna ('_dimension') en el archivo", "_dimension" not in wp["base"] and "'base'" in msg)
escribir(ns["GPS_FILE"], {"x": 10, "y": 64, "z": 20, "dimension": "minecraft:overworld", "owner": {"x": 100, "y": 70, "z": 200},
                          "owner_remote": {"x": 5, "y": 70, "z": -9, "dimension": "minecraft:the_nether"}})
ns["gestionar_waypoints"]("guardar", "guarda este lugar como plaza")
wp = json.loads(io.open(ns["WAYPOINTS_FILE"], encoding="utf-8").read())
r.check("REGRESIÓN: si el jugador está en la MISMA dimensión (owner), se usa owner como siempre", wp["plaza"]["x"] == 100 and wp["plaza"].get("dimension") == "minecraft:overworld")
escribir(ns["GPS_FILE"], {"x": 10, "y": 64, "z": 20, "dimension": "minecraft:overworld"})
ns["gestionar_waypoints"]("guardar", "guarda este lugar como cueva")
wp = json.loads(io.open(ns["WAYPOINTS_FILE"], encoding="utf-8").read())
r.check("REGRESIÓN: sin dueño localizable cae en la posición de Cobalt, como siempre", wp["cueva"]["x"] == 10)

fuente = io.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro", "cerebro.py"), encoding="utf-8").read()
r.check("chat: la intercepción de 'guardar lugar' usa el nuevo reconocimiento (no solo las 3 frases exactas)", "es_orden_guardar_lugar(msg_lower)" in fuente)

r.terminar()
