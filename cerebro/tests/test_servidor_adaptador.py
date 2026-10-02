"""Bloque O (adaptador en cerebro.py): el monitor de TPS, la protección de reinicios y el chat de servidor/hornos/crónica dentro de ciclo_pro y aplicar_cortocircuito."""
import datetime
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
                    ("CONFIG_FILE", "cobalt_config.json"), ("REGISTRO_COMBATE_FILE", "registro_combate.jsonl"), ("OBRAS_FILE", "obras.json"),
                    ("WAYPOINTS_FILE", "waypoints.json")]:
    ns[var] = os.path.join(tmp, nombre)
nox_servidor = ns["nox_servidor"]


def w(nombre, contenido):
    io.open(os.path.join(tmp, nombre), "w", encoding="utf-8").write(contenido if isinstance(contenido, str) else json.dumps(contenido))


def cmd():
    p = ns["COMMAND_FILE"]
    if not os.path.exists(p):
        return []
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


def acciones(ordenes):
    return [o["action"] for o in ordenes] if isinstance(ordenes, list) else []


def memoria_nueva():
    ns["MONITOR_SERVIDOR"] = nox_servidor.MonitorServidor()
    return ns["nueva_memoria_pro"]()


config()
mem = memoria_nueva()
estado(server_tps=20.0)
ns["ciclo_pro"](mem, ahora=1000.0)
r.check("ciclo: con 20 TPS no escribe nada", cmd() == [] and not mem["servidor"].en_lag)
estado(server_tps=9.0, drones_active=True)
ns["ciclo_pro"](mem, ahora=1001.0)
cmd()
ns["ciclo_pro"](mem, ahora=1012.0)
o = cmd()
r.check("ciclo: tras 10 s de lag y con drones activos escribe recall_drones (URGENTE: pisa lo pendiente) con el aviso", acciones(o) == ["recall_drones"] and "9.0 TPS" in o[0]["chat_message"] and "_urgente" not in o[0])
r.check("ciclo: el monitor compartido queda en 'lag' (lo lee también el chat)", mem["servidor"] is ns["MONITOR_SERVIDOR"] and ns["MONITOR_SERVIDOR"].en_lag)

# el enjambre automático NO se despliega en lag
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000,
                    "entities": [{"kind": "hostile", "dist": 10, "boss": True, "name": "Wither", "targets_player": True}] * 5, "hazards": []})
estado(server_tps=9.0, drones_ready=True, drones_active=False, in_combat=True, hp_pct=100)
ns["ciclo_pro"](mem, ahora=1020.0)
o = cmd()
r.check("ciclo: en lag, ni con un jefe cerca se despliega el enjambre (entidades de más empeoran el lag)", "deploy_drones" not in acciones(o))
mem2 = memoria_nueva()
estado(server_tps=20.0, drones_ready=True, drones_active=False, in_combat=True, hp_pct=100)
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000,
                    "entities": [{"kind": "hostile", "dist": 10, "boss": True, "name": "Wither", "targets_player": True}] * 5, "hazards": []})
ns["ciclo_pro"](mem2, ahora=2000.0)
r.check("ciclo: la MISMA situación sin lag SÍ despliega el enjambre (la prueba anterior no es vacía)", "deploy_drones" in acciones(cmd()))
config(monitor_servidor=False)
mem3 = memoria_nueva()
estado(server_tps=3.0)
ns["ciclo_pro"](mem3, ahora=3000.0)
ns["ciclo_pro"](mem3, ahora=3020.0)
r.check("ciclo: con monitor_servidor=false no reacciona a un lag brutal", cmd() == [] and not mem3["servidor"].en_lag)
config(limpieza_lag=False)
mem4 = memoria_nueva()
estado(server_tps=9.0, items_old_near=200, items_near=300, queue=0)
for t in (4000.0, 4010.0, 4075.0):
    ns["ciclo_pro"](mem4, ahora=t)
r.check("ciclo: con limpieza_lag=false avisa del lag pero NO recoge objetos", "pickup" not in acciones(cmd()) and mem4["servidor"].en_lag)
config()
mem5 = memoria_nueva()
estado(server_tps=9.0, items_old_near=200, items_near=300, queue=0)
todas = []
for t in (5000.0, 5010.0, 5075.0):
    ns["ciclo_pro"](mem5, ahora=t)
    todas += cmd()
pick = [x for x in todas if x["action"] == "pickup"]
r.check("ciclo: con la limpieza activa y 200 objetos viejos, tras 60 s de lag recoge (radio 16, edad mínima 2400)", len(pick) == 1 and pick[0]["radius"] == 16 and pick[0]["min_age_ticks"] == 2400)

def ts(h, m, s=0):
    return time.mktime(datetime.datetime(2026, 9, 19, h, m, s).timetuple())


config(servidor_reinicios=["04:00"], servidor_aviso_min=5)
mem = memoria_nueva()
estado(server_tps=20.0)
ns["ciclo_pro"](mem, ahora=ts(3, 40))
r.check("reinicio: a 20 min del reinicio no hace nada", cmd() == [])
ns["ciclo_pro"](mem, ahora=ts(3, 56))
o = cmd()
r.check("reinicio: a 4 min avisa con la hora y guarda el inventario ('store')", acciones(o) == ["ninguna", "store"] and "04:00" in o[0]["chat_message"])
ns["ciclo_pro"](mem, ahora=ts(3, 59, 20))
o = cmd()
r.check("reinicio: a 40 s vacía la cola y se detiene, en un solo lote", acciones(o) == ["flush", "stop"])
ns["ciclo_pro"](mem, ahora=ts(3, 59, 40))
r.check("reinicio: y no lo repite", cmd() == [])
config(servidor_reinicios=["04:00"], proteccion_reinicio=False)
mem = memoria_nueva()
ns["ciclo_pro"](mem, ahora=ts(3, 56))
r.check("reinicio: con proteccion_reinicio=false no hace nada", cmd() == [])
config(servidor_reinicios="cuatro de la mañana")
mem = memoria_nueva()
ns["ciclo_pro"](mem, ahora=ts(3, 56))
r.check("reinicio: un 'servidor_reinicios' mal escrito no revienta y no hace nada", cmd() == [])
config()

ns["MONITOR_SERVIDOR"] = nox_servidor.MonitorServidor()
estado(server_tps=14.5, server_mspt=69.0, players_online=2, items_near=50, items_old_near=10)
o = ns["interceptar_servidor"]("¿cómo va el servidor?", "Steve")
r.check("chat: '¿cómo va el servidor?' responde con los datos reales del estado", o and o[0]["action"] == "ninguna" and "14.5 TPS" in o[0]["chat_message"] and "2 jugador" in o[0]["chat_message"] and o[0]["target"] == "Steve")
o = ns["interceptar_servidor"]("limpia los objetos", "Steve")
r.check("chat: 'limpia los objetos' ordena pickup radio 16 con edad mínima (nunca lo recién tirado por un jugador)", o[0]["action"] == "pickup" and o[0]["radius"] == 16 and o[0]["min_age_ticks"] == 2400)
o = ns["interceptar_servidor"]("atiende los hornos en 12 bloques", "Steve")
r.check("chat: 'atiende los hornos en 12 bloques' ordena tend_furnaces radio 12", o[0]["action"] == "tend_furnaces" and o[0]["radius"] == 12)
for frase, clave in (("¿cómo va el servidor?", "monitor_servidor"), ("limpia los objetos", "limpieza_lag"), ("atiende los hornos", "atender_hornos"), ("escribe la crónica", "bardo_libros")):
    config(**{clave: False})
    r.check(f"chat: con {clave}=false '{frase}' no se intercepta", ns["interceptar_servidor"](frase, "Steve") is None)
config()

# crónica con datos reales de disco
w("registro_combate.jsonl", "\n".join(json.dumps(x) for x in [
    {"ts": time.time(), "duracion_s": 30.0, "danio": 8.0, "rival": "Zombie", "jefe": False, "resultado": "victoria", "dimension": "minecraft:overworld"},
    {"ts": time.time(), "duracion_s": 90.0, "danio": 30.0, "rival": "Wither", "jefe": True, "boss_name": "Wither", "resultado": "victoria", "dimension": "minecraft:overworld"},
]) + "\nlinea rota\n")
w("obras.json", {"casa": {"plano": "casa", "x": 500, "y": 70, "z": -30, "dimension": "minecraft:overworld", "t": time.time()}})
w("waypoints.json", {"base": {"x": 0, "y": 64, "z": 0}, "muerte_nox_1789000000000": {"x": 1, "y": 2, "z": 3}})
o = ns["interceptar_servidor"]("escribe la crónica", "Steve")
libro = o[0] if o else {}
r.check("crónica: la orden write_book lleva título, páginas y give=true", libro.get("action") == "write_book" and libro.get("title") == "Crónica de Cobalt" and libro.get("give") is True
        and isinstance(libro.get("pages"), list) and len(libro["pages"]) >= 2)
texto = "\n".join(libro["pages"])
r.check("crónica: usa los registros REALES del disco (2 combates, el jefe Wither, la obra 'casa', 1 muerte) e ignora la línea rota",
        "Combates: 2 (2 victorias" in texto and "Jefes vencidos: Wither" in texto and "- casa" in texto and "He caído 1 vez" in texto)
ns["escribir_comando"](o)
d = cmd()
r.check("crónica: la orden sobrevive a command.json (las páginas siguen siendo una lista de textos, con bot_id)", d[0]["action"] == "write_book" and d[0]["pages"] == libro["pages"] and d[0]["bot_id"] == "Cobalt_1")

# a través de aplicar_cortocircuito, sin robar frases normales
estado(server_tps=20.0)
r.check("aplicar_cortocircuito: 'escribe la crónica' y 'atiende los hornos' se resuelven en Python", ns["aplicar_cortocircuito"]("escribe la crónica", "Steve")[0]["action"] == "write_book"
        and ns["aplicar_cortocircuito"]("atiende los hornos", "Steve")[0]["action"] == "tend_furnaces")
r.check("aplicar_cortocircuito: una frase normal sigue sin ser interceptada por el Bloque O", ns["interceptar_servidor"]("hola cobalt, ¿qué tal?", "Steve") is None and ns["interceptar_servidor"]("mina hierro", "Steve") is None)

r.terminar()
