"""Pruebas del Bloque C (combate avanzado) del lado Python: cooldown del EMP en los reflejos y en el resumen del LLM."""
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


def mem():
    return {"ultimo_terreno": 0.0, "ultimo_radar": 0.0, "ultimo_chat_combate": 0.0, "terreno_activo": False, "combate_activo": False}


w("terreno_sensor.json", "Terreno seguro.")
w("cobalt_config.json", {})
ns["_CONFIG_CACHE"]["t"] = 0.0
MUCHOS = "Radar de Hostiles (32m): 5 detectados - Zombi (1.0m), Zombi (2.0m), Zombi (3.0m), Zombi (4.0m), Zombi (9.0m)"
w("vision.json", MUCHOS)


def acciones():
    c = cmd()
    return [o["action"] for o in c] if c else None


estado(emp_ready=True)
ns["ciclo_reflejos"](mem(), ahora=1000.0)
r.check("EMP listo + 4 hostiles a <5 m -> se ordena special_power", acciones() == ["defend", "shoot_plasma", "special_power"])

estado(emp_ready=False, emp_cooldown_s=40)
ns["ciclo_reflejos"](mem(), ahora=2000.0)
r.check("EMP en enfriamiento -> NO se ordena (solo defend + shoot_plasma)", acciones() == ["defend", "shoot_plasma"])

estado()
ns["ciclo_reflejos"](mem(), ahora=3000.0)
r.check("Java sin informar emp_ready -> se asume listo (compatibilidad)", acciones() == ["defend", "shoot_plasma", "special_power"])

# resumen para el LLM
rs = ns["resumir_estado_cobalt"]
r.check("resumen: EMP listo", "pulso EMP listo" in rs({"is_deployed": True, "emp_ready": True}))
r.check("resumen: EMP en enfriamiento con segundos", "pulso EMP en enfriamiento (40 s)" in rs({"is_deployed": True, "emp_ready": False, "emp_cooldown_s": 40}))
r.check("resumen: sin dato de EMP no dice nada de EMP", "EMP" not in rs({"is_deployed": True, "hp": 10.0, "max_hp": 50.0}))

r.terminar()
