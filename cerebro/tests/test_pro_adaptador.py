"""Adaptador de nox_pro en cerebro.py: bot_id, entities.json, OMEGA por chat, registro de combates en disco y ciclo_pro."""
import io
import json
import os
import tempfile
import time

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
for var, nombre in [("STATUS_FILE", "nox_status.json"), ("GPS_FILE", "gps.json"), ("ENTIDADES_FILE", "entities.json"), ("COMMAND_FILE", "command.json"),
                    ("CONFIG_FILE", "cobalt_config.json"), ("REGISTRO_COMBATE_FILE", "registro_combate.jsonl")]:
    ns[var] = os.path.join(tmp, nombre)


def w(nombre, contenido):
    io.open(os.path.join(tmp, nombre), "w", encoding="utf-8").write(contenido if isinstance(contenido, str) else json.dumps(contenido))


def cmd():
    p = ns["COMMAND_FILE"]
    if not os.path.exists(p):
        return None
    texto = io.open(p, encoding="utf-8").read()
    os.remove(p)
    try:
        return json.loads(texto)
    except ValueError:
        return texto


def config(**claves):
    w("cobalt_config.json", claves)
    ns["_CONFIG_CACHE"]["t"] = 0.0


def estado(**campos):
    d = {"is_deployed": True, "is_dead": False, "updated_ms": time.time() * 1000, "hp": 20.0}
    d.update(campos)
    w("nox_status.json", d)


config()
ns["escribir_comando"]([{"action": "stop"}, {"action": "go_to", "bot_id": "Cobalt_2"}])
d = cmd()
r.check("bot_id: escribir_comando añade el bot_id propio y respeta uno ya puesto", d[0]["bot_id"] == "Cobalt_1" and d[1]["bot_id"] == "Cobalt_2")

vacio_ok = lambda e: e["entities"] == [] and e["hazards"] == []
r.check("entities: sin archivo -> vacío", vacio_ok(ns["leer_entidades"]()))
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "entities": [{"kind": "hostile", "dist": 4}], "hazards": []})
r.check("entities: archivo válido y fresco -> se lee", len(ns["leer_entidades"]()["entities"]) == 1)
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000 - 60000, "entities": [{"kind": "hostile"}], "hazards": []})
r.check("entities: caducado (60 s) -> vacío", vacio_ok(ns["leer_entidades"]()))
w("entities.json", {"bot_id": "Cobalt_2", "deployed": True, "updated_ms": time.time() * 1000, "entities": [{"kind": "hostile"}], "hazards": []})
r.check("entities: de OTRO bot -> vacío (multi-agente)", vacio_ok(ns["leer_entidades"]()))
w("entities.json", {"bot_id": "Cobalt_1", "deployed": False, "entities": [{"kind": "hostile"}], "hazards": []})
r.check("entities: Cobalt no desplegado -> vacío", vacio_ok(ns["leer_entidades"]()))
w("entities.json", "{roto")
r.check("entities: JSON roto -> vacío, sin excepción", vacio_ok(ns["leer_entidades"]()))

config()
o = ns["aplicar_cortocircuito"]("HALT_ALL", "Steve")
crudo = cmd()
r.check("omega: 'HALT_ALL' devuelve la orden y deja el texto suelto HALT_ALL en command.json (Java lo lee sin parsear)",
        o and o[0]["action"] == "halt_all" and crudo == "HALT_ALL")
o = ns["aplicar_cortocircuito"]("resume", "Steve")
r.check("omega: 'resume' devuelve la orden resume", o and o[0]["action"] == "resume")
config(protocolo_omega=False)
r.check("omega: con protocolo_omega=false 'HALT_ALL' no se intercepta", not (ns["aplicar_cortocircuito"]("HALT_ALL", "Steve") or [{}])[0].get("action") == "halt_all")
cmd()

config()
for i in range(3):
    ns["registrar_combate_disco"]({"rival": "Zombie", "resultado": "victoria", "danio": float(i), "duracion_s": 5.0})
io.open(ns["REGISTRO_COMBATE_FILE"], "a", encoding="utf-8").write("{linea rota\n")
ns["registrar_combate_disco"]({"rival": "Wither", "resultado": "muerte", "danio": 100.0, "duracion_s": 30.0})
reg = ns["leer_registro_combate"]()
r.check("registro: 4 combates válidos, la línea rota se ignora", len(reg) == 4 and reg[-1]["rival"] == "Wither")
ns["REGISTRO_COMBATE_MAX_BYTES"] = 300
for i in range(60):
    ns["registrar_combate_disco"]({"rival": "Zombie", "resultado": "victoria", "danio": 1.0, "duracion_s": 3.0, "i": i})
r.check("registro: si crece demasiado se recorta a lo más reciente (sin perder el final)", len(ns["leer_registro_combate"](5000)) <= 1000 and ns["leer_registro_combate"]()[-1]["i"] == 59)
ns["REGISTRO_COMBATE_MAX_BYTES"] = 400_000

config()
mem = ns["nueva_memoria_pro"]()
gps_v = {"x": 50, "y": 64, "z": 50, "dimension": "minecraft:overworld"}
w("gps.json", gps_v)
estado(task=None, queue=0)
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "entities": [], "hazards": []})
cmd()
r.check("ciclo_pro: sin novedades no emite nada", ns["ciclo_pro"](mem, 1000.0) == [] and cmd() is None)
estado(is_deployed=False, is_dead=True)
ns["ciclo_pro"](mem, 1001.0)
estado()
w("gps.json", {"x": 0, "y": 70, "z": 0, "dimension": "minecraft:overworld"})
o = ns["ciclo_pro"](mem, 1002.0)
enviado = cmd()
r.check("ciclo_pro: muerte y reaparición -> go_to hacia donde cayó, escrito en command.json con bot_id",
        len(o) == 1 and o[0]["action"] == "go_to" and enviado and enviado[0]["x"] == 50 and enviado[0]["bot_id"] == "Cobalt_1")
config(recuperacion_muerte=False)
mem2 = ns["nueva_memoria_pro"]()
w("gps.json", gps_v)
estado()
ns["ciclo_pro"](mem2, 1.0)
estado(is_deployed=False, is_dead=True)
ns["ciclo_pro"](mem2, 2.0)
estado()
r.check("ciclo_pro: con recuperacion_muerte=false no ordena nada", ns["ciclo_pro"](mem2, 3.0) == [])
config()
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "entities": [{"type": "minecraft:warden", "dist": 12.0}], "hazards": []})
mem3 = ns["nueva_memoria_pro"]()
estado(sneaking=False)
o = ns["ciclo_pro"](mem3, 5.0)
r.check("ciclo_pro: Warden cercano -> ordena sneak on", len(o) == 1 and o[0]["action"] == "sneak" and o[0]["on"] == "true")
estado(sneaking=True)
r.check("ciclo_pro: ya agachado -> no repite", ns["ciclo_pro"](mem3, 6.0) == [])
config(sigilo_warden=False)
estado(sneaking=False)
r.check("ciclo_pro: con sigilo_warden=false no se agacha", ns["ciclo_pro"](mem3, 7.0) == [])
config()
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "entities": [], "hazards": []})
mem4 = ns["nueva_memoria_pro"]()
estado(task="mine:iron_ore 1/8")
ns["ciclo_pro"](mem4, 100.0)
estado(task="mine:iron_ore 2/8")
o = ns["ciclo_pro"](mem4, 100.0 + 950.0)
r.check("ciclo_pro: una tarea de más de 15 min -> flush + stop", [x["action"] for x in o] == ["flush", "stop"])
config(vigilante_tareas=False)
mem5 = ns["nueva_memoria_pro"]()
estado(task="mine:iron_ore 1/8")
ns["ciclo_pro"](mem5, 100.0)
r.check("ciclo_pro: con vigilante_tareas=false no vigila", ns["ciclo_pro"](mem5, 100.0 + 950.0) == [])
config()

mem6 = ns["nueva_memoria_pro"]()
estado(in_combat=True, target="Zombie", hp=20.0)
ns["ciclo_pro"](mem6, 500.0)
estado(in_combat=True, target="Zombie", hp=15.0)
ns["ciclo_pro"](mem6, 504.0)
estado(in_combat=False, hp=15.0)
ns["ciclo_pro"](mem6, 505.0)
ns["ciclo_pro"](mem6, 512.0)
reg = ns["leer_registro_combate"]()
r.check("ciclo_pro: un combate completo deja UN registro en disco con el daño recibido", reg and reg[-1]["rival"] == "Zombie" and reg[-1]["danio"] == 5.0)

r.check("RAG: resumen_para_prompt con el historial real", "Zombie" in ns["nox_pro"].resumen_para_prompt(ns["leer_registro_combate"](), "Zombie"))

sup = ns["nox_pro"].Supervisor(avisar=lambda m: None)
r.check("watchdog: vigilante_de_hilos y hilo_pro existen y son invocables", callable(ns["vigilante_de_hilos"]) and callable(ns["hilo_pro"]))

def entidades_json(*lista, bot=(0.0, 64.0, 0.0)):
    w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "entities": list(lista),
                        "hazards": [], "bot": {"x": bot[0], "y": bot[1], "z": bot[2]}})


def hostil(id_, **kw):
    e = {"id": id_, "kind": "hostile", "type": "minecraft:zombie", "name": "Zombie", "x": 5.0, "y": 64.0, "z": 0.0, "dist": 5.0, "boss": False,
         "ranged": False, "los": True, "approaching": False, "targets_player": False, "targets_bot": False}
    e.update(kw)
    return e


config()
w("gps.json", {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": {"x": 0, "y": 64, "z": 0, "hp": 2.0, "max_hp": 20.0, "alive": True}})
estado(emp_ready=False)
entidades_json(hostil(7, targets_player=True))
w("command.json", json.dumps([{"action": "mine", "material": "iron_ore"}]))
memg = ns["nueva_memoria_pro"]()
o = ns["ciclo_pro"](memg, 1.0)
enviado = cmd()
r.check("ciclo_pro (G): una orden URGENTE (robo de aggro) pisa la pendiente y no lleva la marca _urgente",
        enviado and [x["action"] for x in enviado] == ["defend", "shoot_plasma"] and enviado[0]["target_id"] == 7 and all("_urgente" not in x for x in enviado))
w("gps.json", {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": {"x": 0, "y": 64, "z": 0, "hp": 20.0, "max_hp": 20.0, "alive": True}})
estado(following=True)
entidades_json(hostil(8, ranged=True, x=20.0, dist=20.0, type="minecraft:skeleton", name="Skeleton"))
w("command.json", json.dumps([{"action": "mine", "material": "iron_ore"}]))
memg2 = ns["nueva_memoria_pro"]()
o = ns["ciclo_pro"](memg2, 1.0)
pendiente = cmd()
r.check("ciclo_pro (G): una orden NO urgente (guardaespaldas) devuelve órdenes pero NO pisa la orden pendiente del jugador",
        any(x["action"] == "stand_ground" for x in o) and pendiente and pendiente[0]["action"] == "mine")
config(guardaespaldas=False)
memg3 = ns["nueva_memoria_pro"]()
r.check("ciclo_pro (G): con guardaespaldas=false no actúa", not any(x["action"] == "stand_ground" for x in ns["ciclo_pro"](memg3, 1.0)))
cmd()
config(evasion_creeper=False, alerta_sos=False, triangulacion=False, aggro_juggling=False, asistir_al_morir_dueno=False)
entidades_json(hostil(9, swelling=True, dist=3.0, x=3.0, name="Creeper"))
r.check("ciclo_pro (G): con los interruptores apagados un creeper hinchándose no provoca evasión", ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0) == [])
config()
r.check("ciclo_pro (G): con el interruptor encendido sí", any(x["action"] == "go_to" for x in ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)))
cmd()

# guardia por chat
w("gps.json", {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": {"x": 40.5, "y": 70, "z": -8.5}})
config()
o = ns["aplicar_cortocircuito"]("Cobalt, cúbreme que voy a minar", "Steve")
r.check("chat: 'cúbreme' -> stand_ground en la posición del jugador (40, 70, -9), dirigido a quien lo pidió",
        o and o[0]["action"] == "stand_ground" and (o[0]["x"], o[0]["y"], o[0]["z"]) == (40, 70, -9) and o[0]["target"] == "Steve")
r.check("chat: 'modo torreta' -> stand_ground sin coordenadas (donde está)", (lambda x: x and x[0]["action"] == "stand_ground" and "x" not in x[0])(ns["aplicar_cortocircuito"]("modo torreta", "Steve")))
r.check("chat: 'deja de guardar' -> follow", (lambda x: x and x[0]["action"] == "follow")(ns["aplicar_cortocircuito"]("deja de guardar", "Steve")))
config(guardia_por_chat=False)
r.check("chat: con guardia_por_chat=false no se intercepta", not (ns["aplicar_cortocircuito"]("modo torreta", "Steve") or [{}])[0].get("action") == "stand_ground")
config()

w("gps.json", {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": {"x": 0, "y": 64, "z": 0, "hp": 20.0, "max_hp": 20.0, "alive": True}})
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "entities": [], "hazards": [], "bot": {"x": 0, "y": 64, "z": 0},
                    "items": [{"id": 70, "item": "minecraft:diamond", "count": 2, "enchanted": False, "dist": 5.0}]})
estado(inventory={"full": False, "potions": {}, "junk": {}})
cmd()
o = ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)
enviado = cmd()
r.check("ciclo_pro (H): un diamante en el suelo y hueco libre -> pickup por id, con bot_id", [x["action"] for x in o] == ["pickup"] and enviado and enviado[0]["entity_id"] == 70 and enviado[0]["bot_id"] == "Cobalt_1")
config(triage_loot=False)
r.check("ciclo_pro (H): con triage_loot=false no recoge", ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0) == [])
config()
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "hazards": [], "bot": {"x": 0, "y": 64, "z": 0}, "items": [],
                    "entities": [{"id": 3, "kind": "hostile", "boss": True, "dist": 25.0, "type": "minecraft:warden", "name": "Warden", "x": 20.0, "y": 64.0, "z": 0.0}]})
estado(inventory={"potions": {"strength": 1}}, effects=[])
o = ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)
r.check("ciclo_pro (H): un jefe a 25 m y una poción de fuerza -> use_item effect=strength", any(x["action"] == "use_item" and x["effect"] == "strength" for x in o))
cmd()
estado(inventory={"milk": 1}, effects_bad=["minecraft:wither"])
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "entities": [], "hazards": [], "items": [], "bot": {"x": 0, "y": 64, "z": 0}})
memh = ns["nueva_memoria_pro"]()
o = ns["ciclo_pro"](memh, 1.0)
enviado = cmd()
r.check("ciclo_pro (H): Wither + leche -> purga urgente (pisa lo pendiente y sin marca interna)", o and o[0]["action"] == "use_item" and o[0]["material"] == "milk_bucket" and enviado and "_urgente" not in enviado[0])

ns["WAYPOINTS_FILE"] = os.path.join(tmp, "waypoints.json")
ns["MINE_FEEDBACK_FILE"] = os.path.join(tmp, "mine_feedback.json")
config()
estado()
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "entities": [], "hazards": [], "items": [], "bot": {"x": 0, "y": 64, "z": 0}})
cmd()
o = ns["aplicar_cortocircuito"]("Cobalt, consigue 64 de hierro o regresa en 10 minutos", "Steve")
r.check("chat (I): 'consigue 64 de hierro o regresa en 10 minutos' -> orden mine con plazo y misión activa",
        o and o[0]["action"] == "mine" and o[0]["material"] == "iron_ore" and o[0]["amount"] == 64 and o[0]["minutes"] == 10 and o[0]["target"] == "Steve" and ns["MISION_TEMPORAL"].activa)
w("waypoints.json", {"base": {"x": 100, "y": 64, "z": -50}})
w("gps.json", {"x": 300, "y": 20, "z": 300, "dimension": "minecraft:overworld"})
r.check("ciclo (I): sin resultado de Java todavía no hace nada", ns["ciclo_pro"](ns["nueva_memoria_pro"](), time.time()) == [])
w("mine_feedback.json", {"status": "success", "mined": 64, "wanted": 64, "detalle": ""})
o = ns["ciclo_pro"](ns["nueva_memoria_pro"](), time.time())
cmd()
r.check("ciclo (I): al llegar el resultado de Java, ordena volver al waypoint 'base'", len(o) == 1 and o[0]["action"] == "go_to" and (o[0]["x"], o[0]["z"]) == (100, -50) and "cumplida" in o[0]["chat_message"])
ns["MISION_TEMPORAL"].activa = None
config(mision_minera=False)
r.check("chat (I): con mision_minera=false no se intercepta", not (ns["aplicar_cortocircuito"]("consigue 64 de hierro o regresa en 10 minutos", "Steve") or [{}])[0].get("action") == "mine")
config()

# purga de waypoints automáticos (sin tocar los del jugador)
ahora_ms = int(time.time() * 1000)
dia = 24 * 3600 * 1000
wps = {"base": {"x": 1, "y": 1, "z": 1}, "mina": {"x": 2, "y": 2, "z": 2}}
for i in range(6):
    wps[f"muerte_nox_{ahora_ms - (20 - i) * dia}"] = {"x": i, "y": 0, "z": 0}
w("waypoints.json", wps)
borrados = ns["purgar_waypoints_automaticos"]()
quedan = json.load(io.open(ns["WAYPOINTS_FILE"], encoding="utf-8"))
r.check("purga (I): borra 3 de 6 muertes viejas (conserva las 3 más recientes) y NO toca 'base' ni 'mina'", borrados == 3 and "base" in quedan and "mina" in quedan
        and len([k for k in quedan if k.startswith("muerte_nox_")]) == 3)
r.check("purga (I): una segunda pasada no borra nada", ns["purgar_waypoints_automaticos"]() == 0)
w("waypoints.json", "{corrupto")
r.check("purga (I): con waypoints.json corrupto NO lo toca", ns["purgar_waypoints_automaticos"]() == 0 and io.open(ns["WAYPOINTS_FILE"], encoding="utf-8").read() == "{corrupto")
os.remove(ns["WAYPOINTS_FILE"])
r.check("purga (I): sin archivo devuelve 0", ns["purgar_waypoints_automaticos"]() == 0)

config()
w("gps.json", {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": {"x": 0, "y": 64, "z": 0, "hp": 20.0, "max_hp": 20.0, "alive": True}})
estado()
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "hazards": [], "items": [], "bot": {"x": 0, "y": 64, "z": 0},
                    "entities": [{"id": 1, "kind": "player", "owner": True, "x": 0.0, "y": 64.0, "z": 0.0, "dist": 0.0, "yaw": 0.0, "name": "Steve"},
                                 {"id": 7, "kind": "hostile", "type": "minecraft:creeper", "name": "Creeper", "x": 0.0, "y": 64.0, "z": -6.0, "dist": 6.0}]})
cmd()
o = ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)
enviado = cmd()
r.check("ciclo (J): un creeper a la espalda del jugador -> aviso por el chat de Cobalt", any("Creeper a tu espalda" in x.get("chat_message", "") for x in o) and enviado)
config(callouts_tacticos=False)
cmd()
r.check("ciclo (J): con callouts_tacticos=false no avisa", not any("espalda" in x.get("chat_message", "") for x in ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)))
config()

def gps_mundo(hora, tormenta=False, **extra):
    d = {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "mundo": {"day_time": hora, "raining": tormenta, "thundering": tormenta, "has_skylight": True, "sky": True, "light": 15}}
    d.update(extra)
    return d


def avisos_mundo(orden_lista):
    return [x.get("chat_message", "") for x in orden_lista if "noche" in x.get("chat_message", "") or "tormenta" in x.get("chat_message", "") or "tronar" in x.get("chat_message", "")]


config()
estado()
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "hazards": [], "items": [], "bot": {"x": 0, "y": 64, "z": 0}, "entities": []})
w("gps.json", gps_mundo(11500))
cmd()
mem = ns["nueva_memoria_pro"]()
o = ns["ciclo_pro"](mem, 1.0)
enviado = cmd()
r.check("ciclo (H3): a 1500 ticks de la noche avisa por el chat y llega a command.json: " + str(avisos_mundo(o)), len(avisos_mundo(o)) == 1 and enviado is not None and "noche" in json.dumps(enviado, ensure_ascii=False))
r.check("ciclo (H3): el siguiente ciclo no repite el aviso", avisos_mundo(ns["ciclo_pro"](mem, 6.0)) == [])
estado(is_deployed=False)
w("gps.json", gps_mundo(11500))
r.check("ciclo (H3): con Cobalt sin desplegar no avisa (aunque anochezca)", avisos_mundo(ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)) == [])
estado()
config(avisos_mundo=False)
r.check("ciclo (H3): con avisos_mundo=false no avisa", avisos_mundo(ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)) == [])
config()
w("gps.json", {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld"})
r.check("ciclo (H3): con un gps.json de Java antiguo (sin 'mundo') no avisa y no falla", avisos_mundo(ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)) == [])
w("gps.json", gps_mundo(11500, mundo="basura"))
r.check("ciclo (H3): con un bloque 'mundo' corrupto no avisa y no falla", avisos_mundo(ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)) == [])
mem = ns["nueva_memoria_pro"]()
w("gps.json", gps_mundo(6000))
ns["ciclo_pro"](mem, 1.0)
w("gps.json", gps_mundo(6100, tormenta=True))
r.check("ciclo (H3): despejado -> tormenta avisa una vez", len(avisos_mundo(ns["ciclo_pro"](mem, 6.0))) == 1)
cmd()

def gps_dueno(**c):
    d = {"x": 0, "y": 64, "z": 0, "hp": 20.0, "max_hp": 20.0, "alive": True, "food": 20, "air": 300, "max_air": 300, "on_fire": False, "free_slots": 20}
    d.update(c)
    return {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": d}


def avisos_jugador(lista):
    return [x.get("chat_message", "") for x in lista if "comida" in x.get("chat_message", "") or "ardiendo" in x.get("chat_message", "") or "sin aire" in x.get("chat_message", "")
            or "inventario" in x.get("chat_message", "")]


config()
estado()
w("gps.json", gps_dueno(food=4))
mem = ns["nueva_memoria_pro"]()
o = ns["ciclo_pro"](mem, 1.0)
enviado = cmd()
r.check("ciclo (F2-4): el jugador con 4 de comida -> aviso por el chat y llega a command.json: " + str(avisos_jugador(o)), len(avisos_jugador(o)) == 1 and enviado is not None and "comida" in json.dumps(enviado, ensure_ascii=False))
r.check("ciclo (F2-4): el siguiente ciclo no repite", avisos_jugador(ns["ciclo_pro"](mem, 6.0)) == [])
config(avisos_jugador=False)
r.check("ciclo (F2-4): con avisos_jugador=false no avisa", avisos_jugador(ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)) == [])
config()
estado(is_deployed=False)
r.check("ciclo (F2-4): con Cobalt sin desplegar no avisa", avisos_jugador(ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)) == [])
estado()
w("gps.json", {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": {"x": 0, "y": 64, "z": 0, "hp": 3.0, "max_hp": 20.0, "alive": True}})
r.check("ciclo (F2-4): con un gps.json de Java antiguo (owner sin food/air/...) no avisa y no falla", avisos_jugador(ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)) == [])
w("gps.json", gps_dueno(food="mucha", air=None, on_fire="si", free_slots=[]))
r.check("ciclo (F2-4): con campos corruptos no avisa y no falla", avisos_jugador(ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)) == [])
cmd()
w("gps.json", {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": {"x": 0, "y": 64, "z": 0, "hp": 20.0, "max_hp": 20.0, "alive": True}})

# Bloque L: granjeo autónomo por chat
o = ns["aplicar_cortocircuito"]("Cobalt, cosecha en 16 bloques", "Steve")
r.check("chat (L): 'cosecha en 16 bloques' -> acción harvest con radio 16, dirigida a quien la pidió", o and o[0]["action"] == "harvest" and o[0]["radius"] == 16 and o[0]["target"] == "Steve")
r.check("chat (L): 'la cosecha de trigo fue buena' NO se intercepta", not (ns["aplicar_cortocircuito"]("la cosecha de trigo fue buena", "Steve") or [{}])[0].get("action") == "harvest")
config(granjeo_autonomo=False)
r.check("chat (L): con granjeo_autonomo=false no se intercepta", not (ns["aplicar_cortocircuito"]("cosecha", "Steve") or [{}])[0].get("action") == "harvest")
config()
r.check("prompt (L): la acción 'harvest' está en la lista permitida del LLM", "'harvest'" in io.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro", "cerebro.py"), encoding="utf-8").read())

# Enjambre de drones a través del adaptador
o = ns["aplicar_cortocircuito"]("Cobalt, despliega los drones", "Steve")
r.check("chat (drones): 'despliega los drones' -> deploy_drones dirigida a quien lo pidió", o and o[0]["action"] == "deploy_drones" and o[0]["target"] == "Steve")
o = ns["aplicar_cortocircuito"]("retira los drones", "Steve")
r.check("chat (drones): 'retira los drones' -> recall_drones", o and o[0]["action"] == "recall_drones")
r.check("chat (drones): una frase que solo menciona los drones no se intercepta", not (ns["aplicar_cortocircuito"]("los drones de Create son geniales", "Steve") or [{}])[0].get("action") in ("deploy_drones", "recall_drones"))
config(enjambre_por_chat=False)
r.check("chat (drones): con enjambre_por_chat=false no se intercepta", not (ns["aplicar_cortocircuito"]("despliega los drones", "Steve") or [{}])[0].get("action") == "deploy_drones")
config()
r.check("prompt (drones): 'deploy_drones' y 'recall_drones' están en la lista permitida del LLM", all(a in io.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro", "cerebro.py"), encoding="utf-8").read() for a in ("'deploy_drones'", "'recall_drones'")))

w("gps.json", {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": {"x": 0, "y": 64, "z": 0, "hp": 20.0, "max_hp": 20.0, "alive": True}})
horda_json = [{"id": i, "kind": "hostile", "type": "minecraft:zombie", "name": "Zombie", "x": 6.0, "y": 64.0, "z": float(i), "dist": 8.0 + i * 0.1} for i in range(5)]
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "hazards": [], "items": [], "bot": {"x": 0, "y": 64, "z": 0}, "entities": horda_json})
estado(drones_ready=True, drones_active=False)
w("command.json", json.dumps([{"action": "mine", "material": "iron_ore"}]))
o = ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)
enviado = cmd()
r.check("ciclo (drones): con una horda de 5 y el enjambre listo -> deploy_drones URGENTE (pisa la orden pendiente) y sin la marca interna",
        any(x["action"] == "deploy_drones" for x in o) and enviado and enviado[0]["action"] == "deploy_drones" and all("_urgente" not in x for x in enviado))
estado(drones_ready=False, drones_cooldown_s=180)
cmd()
r.check("ciclo (drones): con el enjambre en enfriamiento (Java: drones_ready=false) no pide nada", not any(x["action"] == "deploy_drones" for x in ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)))
estado(drones_ready=True, drones_active=False)
config(enjambre_auto=False)
r.check("ciclo (drones): con enjambre_auto=false no despliega solo (sí por chat)", not any(x["action"] == "deploy_drones" for x in ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)))
config()
cmd()

w("gps.json", {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": {"x": 0, "y": 64, "z": 0, "hp": 20.0, "max_hp": 20.0, "alive": True}})
estado(following=True)
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "hazards": [], "items": [], "bot": {"x": 0, "y": 64, "z": 0},
                    "entities": [{"id": 1, "kind": "player", "owner": True, "x": 0.0, "y": 64.0, "z": 0.0, "dist": 0.0, "yaw": 90.0, "name": "Steve"},
                                 {"id": 8, "kind": "hostile", "type": "minecraft:skeleton", "name": "Skeleton", "x": 20.0, "y": 64.0, "z": 0.0, "dist": 20.0, "ranged": True, "los": True}]})
w("command.json", json.dumps([{"action": "mine", "material": "iron_ore"}]))
memr = ns["nueva_memoria_pro"]()
o = ns["ciclo_pro"](memr, 100.0)
r.check("reintento: con una orden del jugador sin consumir, la orden no urgente NO se escribe pero queda en cola", any(x["action"] == "stand_ground" for x in o)
        and cmd()[0]["action"] == "mine" and len(memr["pendientes"]) >= 1)
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "hazards": [], "items": [], "bot": {"x": 0, "y": 64, "z": 0}, "entities": []})
ns["ciclo_pro"](memr, 103.0)
reint = cmd()
r.check("reintento: 3 s después (Java ya consumió la orden) se escribe la pendiente", reint and any(x["action"] == "stand_ground" for x in reint) and memr["pendientes"] == [])
memr2 = ns["nueva_memoria_pro"]()
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "hazards": [], "items": [], "bot": {"x": 0, "y": 64, "z": 0},
                    "entities": [{"id": 1, "kind": "player", "owner": True, "x": 0.0, "y": 64.0, "z": 0.0, "dist": 0.0, "yaw": 90.0, "name": "Steve"},
                                 {"id": 8, "kind": "hostile", "type": "minecraft:skeleton", "name": "Skeleton", "x": 20.0, "y": 64.0, "z": 0.0, "dist": 20.0, "ranged": True, "los": True}]})
w("command.json", json.dumps([{"action": "mine"}]))
ns["ciclo_pro"](memr2, 200.0)
cmd()
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "hazards": [], "items": [], "bot": {"x": 0, "y": 64, "z": 0}, "entities": []})
ns["ciclo_pro"](memr2, 212.0)
r.check("reintento: una orden pendiente de hace más de 8 s se descarta (ya no vale)", cmd() is None and memr2["pendientes"] == [])

r.terminar()
