"""Cableado de nox_reanudar en cerebro.py: las órdenes largas enviadas se recuerdan, «continúa con tu tarea anterior» se quita del mensaje y se anota, y el ciclo de reflejos"""
import io
import json
import os
import tempfile
import time

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
for var, nombre in [("CONFIG_FILE", "cobalt_config.json"), ("STATUS_FILE", "nox_status.json"), ("GPS_FILE", "gps.json"), ("ENTIDADES_FILE", "entities.json"),
                    ("COMMAND_FILE", "command.json")]:
    ns[var] = os.path.join(tmp, nombre)
ns["BASE_DIR"] = tmp
ns["registrar_mensaje_disco_python"] = lambda *a, **k: None
RE = ns["REANUDADOR"]


def recargar():
    ns["_CONFIG_CACHE"]["t"] = 0.0


def estado(task=None, queue=0):
    io.open(ns["STATUS_FILE"], "w", encoding="utf-8").write(json.dumps({"is_deployed": True, "is_dead": False, "task": task, "queue": queue, "updated_ms": time.time() * 1000}))


recargar()
# 1) una orden larga enviada se recuerda; una que no lo es, no pisa
ns["escribir_comando"]({"action": "mine", "material": "iron_ore", "amount": 5, "target": "Steve", "movement_mode": "walk"})
r.check("una orden larga ENVIADA a Java se recuerda", RE.anterior and RE.anterior["orden"]["action"] == "mine")
ns["escribir_comando"]({"action": "tend_furnaces", "radius": 10, "target": "Steve", "movement_mode": "walk"})
r.check("atender hornos no pisa la tarea larga recordada", RE.anterior["orden"]["action"] == "mine")

estado(task="mine 2")
if os.path.exists(ns["COMMAND_FILE"]):
    os.remove(ns["COMMAND_FILE"])
ns["procesar_mensaje_async"]("Steve", "continúa con tu tarea anterior")
r.check("«continúa con tu tarea anterior» queda anotado como petición pendiente", RE.pendiente_desde is not None)
r.check("y, si solo pedía eso, NO se manda nada más a Java (ni se lo pregunta al modelo)", not os.path.exists(ns["COMMAND_FILE"]))

RE.pendiente_desde = time.time() - 30
mem = ns["nueva_memoria_pro"]()
r.check("la memoria de reflejos incluye al reanudador", mem.get("reanudar") is RE)
estado(task="tend_furnaces", queue=1)
ordenes = ns["ciclo_pro"](mem, ahora=time.time())
r.check("ocupado: no reenvía todavía", not any(o.get("action") == "mine" for o in ordenes))
estado(task=None, queue=0)
ns["ciclo_pro"](mem, ahora=time.time())
ordenes = ns["ciclo_pro"](mem, ahora=time.time())
mina = [o for o in ordenes if o.get("action") == "mine"]
r.check("libre: el ciclo reenvía la mina anterior", len(mina) == 1 and mina[0]["material"] == "iron_ore" and mina[0].get("reanudada") is True)

# 4) con el interruptor apagado no se toca nada
io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps({"reanudar_tareas": False}))
recargar()
RE.pendiente_desde = None
ns["procesar_mensaje_async"]("Steve", "sígueme y continúa con tu tarea anterior")
r.check("reanudar_tareas=false: no anota la petición", RE.pendiente_desde is None)

r.terminar()
