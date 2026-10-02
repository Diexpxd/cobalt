"""Pruebas del Bloque B (supervivencia) del lado Python: los reflejos de combate respetan la vida crítica."""
import io
import json
import os
import tempfile
import time

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
for var, nombre in [("STATUS_FILE", "nox_status.json"), ("TERRENO_FILE", "terreno_sensor.json"), ("VISION_FILE", "vision.json"),
                    ("COMMAND_FILE", "command.json"), ("CONFIG_FILE", "cobalt_config.json")]:
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


def config(**kw):
    w("cobalt_config.json", kw)
    ns["_CONFIG_CACHE"]["t"] = 0.0


def mem():
    return {"ultimo_terreno": 0.0, "ultimo_radar": 0.0, "ultimo_chat_combate": 0.0, "terreno_activo": False, "combate_activo": False}


HOSTIL = "Radar de Hostiles (32m): 1 detectados - Zombi (10.0m)"
w("terreno_sensor.json", "Terreno seguro.")
w("vision.json", HOSTIL)
config()  # todo por defecto (encendido)

r.check("critical_hp=True de Java manda", ns["_vida_critica"]({"critical_hp": True, "hp_pct": 90}) is True)
r.check("critical_hp=False de Java manda aunque hp_pct sea bajo (histéresis)", ns["_vida_critica"]({"critical_hp": False, "hp_pct": 10}) is False)
r.check("sin critical_hp: se calcula con hp_pct (20 < 30)", ns["_vida_critica"]({"hp_pct": 20}) is True)
r.check("sin critical_hp: hp_pct 40 no es crítica", ns["_vida_critica"]({"hp_pct": 40}) is False)
r.check("sin datos de vida: no crítica", ns["_vida_critica"]({}) is False)
config(vida_critica_pct=50)
r.check("el umbral se lee de cobalt_config.json (hp_pct 40 < 50)", ns["_vida_critica"]({"hp_pct": 40}) is True)
config(huida_vida_critica=False)
r.check("interruptor huida_vida_critica=false: nunca crítica", ns["_vida_critica"]({"critical_hp": True}) is False)
config()

estado(hp_pct=100, critical_hp=False)
m = mem()
r.check("vida normal + amenaza -> combate", ns["ciclo_reflejos"](m, ahora=1000.0) == ["radar:defend+shoot_plasma"])
cmd()

estado(hp_pct=20, critical_hp=True)
m = mem()
salida = ns["ciclo_reflejos"](m, ahora=2000.0)
r.check("vida CRÍTICA + amenaza -> NO se ordena combate", salida == [] and cmd() is None and m["combate_activo"] is False)

# la lava sigue funcionando en vida crítica (es supervivencia)
w("terreno_sensor.json", "PELIGRO: ¡Lava o fuego detectado bajo los pies o adyacente! Se requiere vuelo urgente (fly).")
m = mem()
salida = ns["ciclo_reflejos"](m, ahora=3000.0)
r.check("vida crítica + lava -> el vuelo de emergencia SÍ se ordena", salida == ["terreno:fly"])
cmd()
w("terreno_sensor.json", "Terreno seguro.")

# con el interruptor apagado, el combate vuelve aunque esté crítica
config(huida_vida_critica=False)
estado(hp_pct=20, critical_hp=True)
m = mem()
r.check("interruptor apagado + vida crítica -> el combate se ordena como antes", ns["ciclo_reflejos"](m, ahora=4000.0) == ["radar:defend+shoot_plasma"])
cmd()
config()

# al recuperarse (critical_hp=False) el combate se reanuda
estado(hp_pct=60, critical_hp=False)
m = mem()
r.check("recuperada la vida -> el combate se reanuda", ns["ciclo_reflejos"](m, ahora=5000.0) == ["radar:defend+shoot_plasma"])
cmd()

# el estado exportado por Java llega al resumen del prompt
t = ns["resumir_estado_cobalt"]({"is_deployed": True, "hp": 12.0, "max_hp": 50.0, "hp_pct": 24, "movement_mode": "fly", "critical_hp": True, "fleeing": True})
r.check("el resumen del estado marca VIDA CRÍTICA", "VIDA CRÍTICA" in t and "vida 12/50" in t)

r.terminar()
