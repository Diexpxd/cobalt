"""Contrato Java -> Python: los archivos que el mod REAL escribe (instantánea de tests/fixtures_java, tomada en un servidor de Minecraft sin ventana con un dueño, un husk y un"""
import copy
import json
import os
import sys

from _cargar import Resultados, cargar_cerebro

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_diagnostico  # noqa: E402
import nox_entorno  # noqa: E402
import nox_mundo  # noqa: E402
import nox_proactivo  # noqa: E402

r = Resultados()
CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures_java")


def leer(nombre):
    with open(os.path.join(CARPETA, nombre), encoding="utf-8") as f:
        return f.read()


def leer_json(nombre):
    return json.loads(leer(nombre))


gps, entidades, estado, mods = (leer_json(n) for n in ("gps.json", "entities.json", "nox_status.json", "mods.json"))

r.check("gps.json: posición, dimensión, bioma y bot_id", all(k in gps for k in ("x", "y", "z", "dimension", "biome", "bot_id")))
dueno = gps.get("owner", {})
r.check("gps.json: el dueño trae nombre, vida, comida, aire, huecos libres y fuego (lo que lee la proactividad)",
        all(k in dueno for k in ("name", "hp", "max_hp", "alive", "food", "air", "max_air", "free_slots", "on_fire")))
r.check("gps.json: bloque 'mundo' con hora, lluvia, tormenta, luz y cielo", all(k in gps.get("mundo", {}) for k in ("day_time", "raining", "thundering", "light", "sky", "has_skylight")))
r.check("entities.json: lista de entidades con tipo, clase y distancia", entidades.get("entities") and all(k in entidades["entities"][0] for k in ("type", "kind", "dist", "hp")))
r.check("entities.json: la posición del propio Cobalt y su bot_id", "bot" in entidades and entidades.get("bot_id") == gps.get("bot_id"))
r.check("nox_status.json: vida, inventario y despliegue", all(k in estado for k in ("hp", "max_hp", "inventory", "is_deployed")))
r.check("mods.json: versión de Minecraft y lista de mods con id y versión", mods.get("minecraft") and all("id" in m and "version" in m for m in mods.get("mods", [])))
r.check("vision.json es el radar de hostiles en texto", "Radar de Hostiles" in leer("vision.json"))

hechos = nox_entorno.hechos(estado, gps, entidades)
texto = " ".join(hechos)
r.check("entorno: menciona al jugador y su distancia", any(h.startswith("Jugador a ") for h in hechos))
r.check("entorno: menciona al husk como hostil cercano", "Husk" in texto and "Hostiles cerca: 1" in texto)
r.check("entorno: describe el mundo (noche, luz)", "de noche" in texto.lower() and "0/15" in texto)
mundo = nox_mundo.interpretar(gps)
r.check("mundo: la hora, la luz y el cielo salen del gps real", mundo.hora == gps["mundo"]["day_time"] and mundo.luz == gps["mundo"]["light"] and mundo.tiene_cielo is True)

r.check("proactividad: con el dueño sano no avisa", nox_proactivo.AvisosJugador().actualizar(estado, gps, 1000.0) == [])
for campo, valor, esperado in (("food", 1, "comida"), ("on_fire", True, "fuego"), ("air", 20, "aire"), ("free_slots", 0, "inventario")):
    g = copy.deepcopy(gps)
    g["owner"][campo] = valor
    ordenes = nox_proactivo.AvisosJugador().actualizar(estado, g, 1000.0)
    r.check(f"proactividad: '{campo}' en peligro produce un aviso ({esperado})", len(ordenes) == 1 and ordenes[0].get("chat_message"))

# diagnóstico y resumen del cerebro
resumen = nox_diagnostico.resumen_mods(mods)
r.check("diagnóstico: cuenta los mods y conoce la versión de Minecraft", resumen and resumen["total"] == mods["count"] and resumen["minecraft"] == "1.20.1")
r.check("diagnóstico: entre los mods aparece geckolib", any(i.startswith("geckolib@") for i in resumen["ids"]))
cerebro = cargar_cerebro()
estado_txt = cerebro["resumir_estado_cobalt"](estado, gps)
r.check("cerebro: resume el estado de Cobalt con vida, combate, dimensión y bioma", "vida 50/50" in estado_txt and "Husk" in estado_txt and "overworld" in estado_txt and "cold_ocean" in estado_txt)
inv_txt = cerebro["resumir_inventario"](estado["inventory"])
r.check("cerebro: resume el inventario real (herramienta y objeto)", "pickaxe" in inv_txt and "iron_pickaxe" in inv_txt)

JAVA_ENTIDAD = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "mod", "src", "main", "java", "com", "example", "cobaltbot", "entity", "CobaltEntity.java")
if os.path.exists(JAVA_ENTIDAD):
    import re

    fuente = open(os.path.join(os.path.dirname(CARPETA), "..", "cerebro", "cerebro.py"), encoding="utf-8").read()
    linea = fuente[fuente.index("VALORES DE ACCI"):].split("\n")[0]
    en_prompt = set(re.findall(r"'([a-z_]+)'", linea))
    java = open(JAVA_ENTIDAD, encoding="utf-8", errors="replace").read()
    cuerpo = java[java.index("private void ejecutarAccion(JsonObject t)"):][:40000]
    implementadas = {"ninguna", "halt_all", "resume"}
    for grupo in re.findall(r'case\s+((?:"[a-z_0-9]+"\s*,?\s*)+)->', cuerpo):
        implementadas.update(re.findall(r'"([a-z_0-9]+)"', grupo))
    r.check("prompt del planificador: lista de acciones leída (más de 10)", len(en_prompt) > 10)
    r.check("prompt del planificador: TODAS las acciones permitidas existen en Java (sobran: %s)" % sorted(en_prompt - implementadas), en_prompt <= implementadas)
else:
    print("SALTADA la comprobación de acciones: no está el código fuente del mod en", JAVA_ENTIDAD)

r.terminar()
