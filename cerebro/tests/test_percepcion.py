"""Pruebas del Bloque A (percepción): terreno, GPS con dimensión/bioma, telemetría de salud e inventario."""
import io
import json
import os
import re
import tempfile
import time

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
for var, nombre in [("STATUS_FILE", "nox_status.json"), ("GPS_FILE", "gps.json"), ("TERRENO_FILE", "terreno_sensor.json"),
                    ("VISION_FILE", "vision.json"), ("COMMAND_FILE", "command.json"), ("WAYPOINTS_FILE", "waypoints.json")]:
    ns[var] = os.path.join(tmp, nombre)


def w(nombre, contenido):
    io.open(os.path.join(tmp, nombre), "w", encoding="utf-8").write(contenido if isinstance(contenido, str) else json.dumps(contenido))


def cmd():
    p = ns["COMMAND_FILE"]
    if not os.path.exists(p):
        return None
    d = json.load(io.open(p, encoding="utf-8"))
    os.remove(p)
    return d


def estado(**kw):
    e = {"is_deployed": True, "is_dead": False, "regen_minutes": 0, "updated_ms": int(time.time() * 1000)}
    e.update(kw)
    w("nox_status.json", e)


def mem():
    return {"ultimo_terreno": 0.0, "ultimo_radar": 0.0, "ultimo_chat_combate": 0.0, "terreno_activo": False, "combate_activo": False}


estado()
w("vision.json", "Radar de Hostiles (32m): Despejado.")
for texto, esperado in [
    ("ALERTA: caída inminente, suelo a 12 bloques bajo Cobalt.", False),
    ("ALERTA: caída al vacío (sin suelo en 32 bloques bajo Cobalt).", False),
    ("ALERTA: sofocación (Cobalt está dentro de un bloque sólido).", False),
    ("ESTADO: Sumergido en agua. Se requiere movement_mode 'swim'.", False),
    ("TERRENO: Agua detectada cerca. Usa movement_mode 'swim' para cruzar.", False),
    ("ALERTA: sofocación (Cobalt está dentro de un bloque sólido). | PELIGRO: ¡Lava o fuego detectado bajo los pies o adyacente! Se requiere vuelo urgente (fly).", True),
]:
    w("terreno_sensor.json", texto)
    m = mem()
    emitido = ns["ciclo_reflejos"](m, ahora=1000.0)
    cmd()
    r.check(f"terreno {'-> fly' if esperado else 'sin fly'}: {texto[:58]}...", (emitido == ["terreno:fly"]) == esperado)

ruta_java = os.path.join(os.environ.get("COBALT_MOD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "mod")),
                         "src", "main", "java", "com", "example", "cobaltbot", "util", "NoxSensorWriter.java")
if os.path.isfile(ruta_java):
    fuente = io.open(ruta_java, encoding="utf-8").read()
    alertas = re.findall(r'"(ALERTA:[^"]*)"', fuente)
    r.check("Java: existen los avisos ALERTA de sofocación y de caída", len(alertas) >= 3)
    prohibidas = ("peligro", "lava", "fuego")
    malas = [a for a in alertas if any(p in a.lower() for p in prohibidas)]
    r.check("Java: ninguna ALERTA contiene 'peligro', 'lava' ni 'fuego' (dispararían el vuelo de emergencia)", not malas)
else:
    print("SKIP contrato Java<->Python (no está el mod en", ruta_java, ")")

estado()
w("terreno_sensor.json", "Sin datos: Cobalt no está desplegado.")
w("vision.json", "Radar de Hostiles (32m): Despejado (Cobalt no está desplegado).")
r.check("textos neutros de Java: ni vuelo de emergencia ni combate", ns["ciclo_reflejos"](mem(), ahora=2000.0) == [] and cmd() is None)
if os.path.isfile(ruta_java):
    limpiar = re.search(r"void limpiarSensores\(\)\s*\{(.*?)\n    \}", fuente, re.S).group(1)
    neutros = re.findall(r'escribirAtomico\("[a-z_]+\.json",\s*("[^;]*)\);', limpiar)
    prohibidas_neutro = ("peligro", "lava", "fuego")
    r.check("Java: limpiarSensores escribe tres sensores neutros (terreno, radar y entities.json vacío)", len(neutros) == 3)
    r.check("Java: el entities.json neutro no lista entidades ni peligros y dice que no está desplegado", any('\\"entities\\":[]' in n and '\\"deployed\\":false' in n for n in neutros))
    r.check("Java: los textos neutros no contienen palabras que activen reflejos", not any(p in n.lower() for n in neutros for p in prohibidas_neutro))
    r.check("Java: el radar neutro incluye 'Despejado' (cerebro.py lo usa para no combatir)", any("Despejado" in n for n in neutros))

w("gps.json", {"x": 10, "y": 64, "z": 20, "dimension": "minecraft:the_nether", "biome": "minecraft:nether_wastes",
               "owner": {"x": 100, "y": 70, "z": 200}})
g = ns["leer_gps"]()
r.check("leer_gps: dimensión, bioma y posición del jugador", g["dimension"] == "minecraft:the_nether" and g["biome"] == "minecraft:nether_wastes" and g["owner"]["x"] == 100)
w("gps.json", '{"x": 1, "y"')
r.check("leer_gps: archivo a medio escribir -> {} sin excepción", ns["leer_gps"]() == {})
os.remove(ns["GPS_FILE"])
r.check("leer_gps: sin archivo -> {}", ns["leer_gps"]() == {})

# Waypoints guardan la dimensión
w("gps.json", {"x": 10, "y": 64, "z": 20, "dimension": "minecraft:the_nether", "owner": {"x": 100, "y": 70, "z": 200}})
ns["gestionar_waypoints"]("guardar", "guarda este lugar como fortaleza")
wp = json.load(io.open(ns["WAYPOINTS_FILE"], encoding="utf-8"))
r.check("waypoint guarda x/y/z Y la dimensión", wp["fortaleza"] == {"x": 100, "y": 70, "z": 200, "dimension": "minecraft:the_nether"})
ns["gestionar_waypoints"]("guardar", "guarda este lugar como casa")
r.check("listar muestra la dimensión entre corchetes", "'fortaleza': X=100, Y=70, Z=200 [the_nether]" in ns["gestionar_waypoints"]("listar"))
w("gps.json", {"x": 1, "y": 2, "z": 3})
ns["gestionar_waypoints"]("guardar", "guarda este lugar como mina")
wp = json.load(io.open(ns["WAYPOINTS_FILE"], encoding="utf-8"))
r.check("sin dimensión en el GPS no se inventa ninguna", wp["mina"] == {"x": 1, "y": 2, "z": 3})
r.check("un waypoint con dimensión sigue siendo válido para buscarlo y construir", ns["buscar_waypoint"]("fortaleza")[1]["x"] == 100)

ri = ns["resumir_inventario"]
r.check("inventario sin datos", ri(None) == "Inventario: sin datos." and ri({}) == "Inventario: sin datos.")
r.check("inventario vacío -> pide reabastecerse", "VACÍO" in ri({"slots": 36, "used": 0, "free": 36, "empty": True, "full": False}) and "reabastecerse" in ri({"slots": 36, "used": 0, "free": 36, "empty": True}))
inv = {"slots": 36, "used": 6, "free": 30, "full": False, "empty": False, "healing": 7, "blocks": 128, "tools": ["pickaxe", "sword"],
       "items": {"minecraft:cobblestone": 128, "minecraft:bread": 5, "minecraft:golden_apple": 2}, "other_types": 0}
t = ri(inv)
r.check("inventario normal: huecos, comida, bloques, herramientas y contenido",
        "6/36" in t and "comida/curación: 7" in t and "bloques: 128" in t and "pickaxe, sword" in t and "cobblestone x128" in t and "LLENO" not in t)
r.check("inventario lleno -> avisa que no recolecte", "LLENO" in ri({**inv, "used": 36, "free": 0, "full": True}))
r.check("sin herramientas -> 'ninguna'", "herramientas: ninguna" in ri({**inv, "tools": []}))
muchos = {**inv, "items": {f"minecraft:item_{i}": 100 - i for i in range(12)}, "other_types": 5}
tm = ri(muchos)
r.check("muchos tipos: solo los 8 principales y cuenta el resto (12-8+5 = 9)", "item_0 x100" in tm and "item_8" not in tm and "+9 tipos más" in tm)

rs = ns["resumir_estado_cobalt"]
r.check("no desplegado", rs({"is_deployed": False}) == "Cobalt no está desplegado en el mundo.")
e = {"is_deployed": True, "hp": 42.5, "max_hp": 50.0, "hp_pct": 85, "armor": 6, "effects": ["minecraft:regeneration"],
     "movement_mode": "fly", "in_combat": True, "target": "Zombi", "following": True}
t = rs(e, {"dimension": "minecraft:overworld", "biome": "minecraft:plains"})
r.check("estado: vida, armadura, efectos, modo, combate y ubicación",
        "vida 42.5/50 (85%)" in t and "armadura 6" in t and "regeneration" in t and "modo de movimiento fly" in t
        and "EN COMBATE contra Zombi" in t and "en overworld, bioma plains" in t and "CRÍTICA" not in t)
r.check("vida < 30% -> VIDA CRÍTICA", "VIDA CRÍTICA" in rs({**e, "hp": 10.0, "hp_pct": 20}))
r.check("sin combate pero siguiendo -> 'siguiendo al jugador'", "siguiendo al jugador" in rs({**e, "in_combat": False}))
r.check("sin GPS no inventa ubicación", "bioma" not in rs(e, {}) and " en " not in rs(e, None).split("modo")[0])

# describir_cuerpo lee los archivos (status + gps)
estado(hp=50.0, max_hp=50.0, hp_pct=100, movement_mode="walk", inventory=inv)
w("gps.json", {"x": 1, "y": 2, "z": 3, "dimension": "minecraft:the_end"})
d = ns["describir_cuerpo"]()
r.check("describir_cuerpo junta estado + inventario + dimensión", "vida 50/50" in d and "en the_end" in d and "Inventario: 6/36" in d)
estado(is_deployed=False)
r.check("describir_cuerpo con Cobalt fuera del mundo", "no está desplegado" in ns["describir_cuerpo"]() and "Inventario: sin datos." in ns["describir_cuerpo"]())

p = ns["generar_prompt_maestro"]("visión", "Terreno seguro.", "Todo en orden. | " + d, "", "", "Sin datos técnicos.", "")
r.check("el prompt del LLM contiene el estado real del cuerpo y el inventario", "Estado de tu Cuerpo (Feedback): Todo en orden. | Estado de Cobalt" in p and "Inventario: 6/36" in p)

r.terminar()
