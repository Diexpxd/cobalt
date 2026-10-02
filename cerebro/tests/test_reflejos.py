import io, json, os, sys, tempfile, time
from _cargar import cargar_cerebro
ns = cargar_cerebro()


tmp = tempfile.mkdtemp()
for var, nombre in [("STATUS_FILE", "nox_status.json"), ("TERRENO_FILE", "terreno_sensor.json"),
                    ("VISION_FILE", "vision.json"), ("COMMAND_FILE", "command.json")]:
    ns[var] = os.path.join(tmp, nombre)

def w(nombre, texto): io.open(os.path.join(tmp, nombre), "w", encoding="utf-8").write(texto)
def cmd():
    p = ns["COMMAND_FILE"]
    if not os.path.exists(p): return None
    d = json.load(io.open(p, encoding="utf-8")); os.remove(p); return d
def estado(**kw):
    e = {"is_deployed": True, "is_dead": False, "regen_minutes": 0, "updated_ms": int(time.time()*1000)}
    e.update(kw); w("nox_status.json", json.dumps(e))
def mem(): return {"ultimo_terreno": 0.0, "ultimo_radar": 0.0, "ultimo_chat_combate": 0.0, "terreno_activo": False, "combate_activo": False}

fallos = []
def check(nombre, cond):
    print(("OK   " if cond else "FAIL ") + nombre)
    if not cond: fallos.append(nombre)

ns["escribir_comando"]({"chat_message": "hola"})
c = cmd()
check("escribir_comando envuelve dict en Array con action/movement_mode", c == [{"chat_message": "hola", "action": "ninguna", "movement_mode": "walk", "bot_id": "Cobalt_1"}])
check("no queda command.json.tmp", not os.path.exists(ns["COMMAND_FILE"] + ".tmp"))
check("sobrescribir=False respeta orden pendiente",
      ns["escribir_comando"]({"action": "a"}) and not ns["escribir_comando"]({"action": "b"}, sobrescribir=False) and cmd()[0]["action"] == "a")

# 2. leer_estado_cobalt
check("sin nox_status.json -> no desplegado", ns["leer_estado_cobalt"]()["is_deployed"] is False)
estado(); check("estado fresco -> desplegado", ns["leer_estado_cobalt"]()["is_deployed"] is True)
estado(updated_ms=int(time.time()*1000) - 60000); check("estado caducado (60 s) -> no desplegado", ns["leer_estado_cobalt"]()["is_deployed"] is False)
w("nox_status.json", '{"is_deployed": tr'); check("JSON a medio escribir no lanza y -> no desplegado", ns["leer_estado_cobalt"]()["is_deployed"] is False)

# 3. contar_hostiles
check("contar_hostiles: 4 cercanos de 6",
      ns["contar_hostiles"]("Radar de Hostiles (32m): 6 detectados - Zombi (1.0m), Zombi (2.0m), Zombi (3.0m), Zombi (4.9m), Zombi (5.0m), Zombi (20.0m)") == (6, 4))
check("contar_hostiles: formato antiguo -> al menos 1", ns["contar_hostiles"]("Radar de Hostiles a 32 bloques: Zombi, Zombi, ") == (1, 0))

# 4. reflejos
m = mem(); estado(); w("terreno_sensor.json", "Terreno seguro."); w("vision.json", "Radar de Hostiles (32m): Despejado.")
check("terreno seguro + despejado -> no emite nada", ns["ciclo_reflejos"](m) == [] and cmd() is None)

m = mem(); w("terreno_sensor.json", "PELIGRO: ¡Lava o fuego detectado bajo los pies o adyacente! Se requiere vuelo urgente (fly).")
r = ns["ciclo_reflejos"](m, ahora=1000.0); c = cmd()
check("PELIGRO -> fly inmediato en command.json (sin LLM)", r == ["terreno:fly"] and c[0]["movement_mode"] == "fly" and "chat_message" in c[0])
r = ns["ciclo_reflejos"](m, ahora=1001.0)
check("PELIGRO dentro del cooldown (3 s) -> no reenvía", r == [] and cmd() is None)
r = ns["ciclo_reflejos"](m, ahora=1004.0); c = cmd()
check("PELIGRO tras cooldown -> reenvía, ya sin chat repetido", r == ["terreno:fly"] and "chat_message" not in c[0])

m = mem(); w("terreno_sensor.json", "Terreno seguro.")
w("vision.json", "Radar de Hostiles (32m): 2 detectados - Zombi (8.0m), Esqueleto (12.0m)")
r = ns["ciclo_reflejos"](m, ahora=2000.0); c = cmd()
check("hostiles -> defend + shoot_plasma en vuelo", r == ["radar:defend+shoot_plasma"] and [o["action"] for o in c] == ["defend", "shoot_plasma"] and all(o["movement_mode"] == "fly" for o in c))

m = mem(); w("vision.json", "Radar de Hostiles (32m): 5 detectados - Zombi (1.0m), Zombi (2.0m), Zombi (3.0m), Zombi (4.0m), Zombi (9.0m)")
ns["ciclo_reflejos"](m, ahora=3000.0); c = cmd()
check(">3 hostiles a <5 m -> añade special_power", [o["action"] for o in c] == ["defend", "shoot_plasma", "special_power"])

ar = ns["analizar_radar"]
check("analizar_radar: el visible cuenta, los ocultos lejanos no",
      ar("Radar de Hostiles (32m): 3 detectados - Zombi (6.0m), Creeper (12.0m*), Esqueleto (20.0m*)") == (3, 1, 0))
check("analizar_radar: oculto pero a <= 8 m SÍ es amenaza", ar("Radar de Hostiles (32m): 1 detectados - Zombi (7.9m*)") == (1, 1, 0))
check("analizar_radar: oculto a 8.1 m no lo es", ar("Radar de Hostiles (32m): 1 detectados - Zombi (8.1m*)")[1] == 0)
check("analizar_radar: cuenta los cercanos (<5 m) también si están ocultos", ar("Radar de Hostiles (32m): 1 detectados - Zombi (2.0m*)") == (1, 1, 1))
check("analizar_radar: el '(32m)' de la cabecera no se toma por un hostil", ar("Radar de Hostiles (32m): 1 detectados - Zombi (30.0m)") == (1, 1, 0))

m = mem(); w("vision.json", "Radar de Hostiles (32m): 2 detectados - Creeper (15.0m*), Esqueleto (22.0m*)")
r = ns["ciclo_reflejos"](m, ahora=7000.0)
check("solo hostiles ocultos y lejanos ('fantasmas') -> NO se emite combate", r == [] and cmd() is None and m["combate_activo"] is False)

m = mem(); w("vision.json", "Radar de Hostiles (32m): 2 detectados - Zombi (10.0m), Creeper (15.0m*)")
r = ns["ciclo_reflejos"](m, ahora=7100.0); c = cmd()
check("visible + oculto -> combate, y el aviso cuenta 1 amenaza (no 2)", r == ["radar:defend+shoot_plasma"] and "1 amenaza" in c[0].get("chat_message", ""))

m = mem(); despejado = "Radar de Hostiles (32m): Despejado."; amenaza = "Radar de Hostiles (32m): 1 detectados - Zombi (10.0m)"
w("vision.json", amenaza); ns["ciclo_reflejos"](m, ahora=8000.0); c1 = cmd()
w("vision.json", despejado); ns["ciclo_reflejos"](m, ahora=8006.0)
w("vision.json", amenaza); ns["ciclo_reflejos"](m, ahora=8012.0); c2 = cmd()
w("vision.json", despejado); ns["ciclo_reflejos"](m, ahora=8100.0)
w("vision.json", amenaza); ns["ciclo_reflejos"](m, ahora=8106.0); c3 = cmd()
check("1er aviso: con chat", "chat_message" in c1[0])
check("reaparece a los 12 s: sin chat (pero sí combate)", c2 is not None and "chat_message" not in c2[0] and c2[0]["action"] == "defend")
check("reaparece a los 100 s: vuelve el chat", "chat_message" in c3[0])

m = mem(); ns["escribir_comando"]({"action": "follow", "movement_mode": "fly"})
r = ns["ciclo_reflejos"](m, ahora=4000.0)
check("no pisa una orden del jugador aún sin consumir", r == [] and cmd()[0]["action"] == "follow")

m = mem(); estado(is_dead=True); ns["escribir_comando"]  # muerto
check("Cobalt muerto -> reflejos apagados", ns["ciclo_reflejos"](m, ahora=5000.0) == [] and cmd() is None)
m = mem(); w("nox_status.json", "");
check("sin telemetría (archivo vacío) -> reflejos apagados", ns["ciclo_reflejos"](m, ahora=6000.0) == [] and cmd() is None)

import requests as _rq
def _sin_ollama(*a, **k): raise _rq.exceptions.ConnectionError("conexión rechazada")
ns["requests"].post = _sin_ollama
png = os.path.join(tmp, "vision_continua.png"); io.open(png, "wb").write(b"\x89PNG")
res = ns["analizar_vision_local"](png)
check("Ollama caído: devuelve 'visión borrosa' sin lanzar excepción", "borrosa" in res)
check("Ollama caído: deja la visión en pausa (~60 s)", ns["_OLLAMA_CAIDO_HASTA"] > time.time() + 30)

print("\nRESULTADO:", "TODO OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}")
sys.exit(1 if fallos else 0)
