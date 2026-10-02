"""Pruebas del Bloque E3 (construcción): caja del plano, espera de feedback y el flujo despejar -> colocar -> reabastecer -> reintentar."""
import io
import json
import os
import tempfile
import threading
import time

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
ns["CONFIG_FILE"] = os.path.join(tmp, "cobalt_config.json")
ns["OBRAS_FILE"] = os.path.join(tmp, "obras.json")  # iniciar_construccion registra la obra: nunca en el archivo real

plano = {"layers": [
    {"y": 0, "blocks": [{"x": 0, "z": 0, "block": "minecraft:stone"}, {"x": 3, "z": 2, "block": "minecraft:stone"}]},
    {"y": 2, "blocks": [{"x": 1, "z": 1, "block": "minecraft:oak_planks"}]},
]}
r.check("caja_de_plano: esquinas mínima y máxima con el origen aplicado", ns["caja_de_plano"](plano, 100, 64, 200) == (100, 64, 200, 103, 66, 202))
r.check("caja_de_plano: plano vacío -> None", ns["caja_de_plano"]({"layers": []}, 0, 0, 0) is None and ns["caja_de_plano"]({"layers": [{"y": 0, "blocks": []}]}, 0, 0, 0) is None)

ruta = os.path.join(tmp, "fb.json")


def escribir_tarde():
    time.sleep(0.15)
    io.open(ruta, "w", encoding="utf-8").write(json.dumps({"status": "success", "cleared": 7}))


hilo = threading.Thread(target=escribir_tarde)
hilo.start()
d = ns["esperar_feedback"](ruta, 3, 0.02)
hilo.join()
r.check("esperar_feedback: recibe el archivo cuando aparece y lo borra", d == {"status": "success", "cleared": 7} and not os.path.exists(ruta))
r.check("esperar_feedback: sin archivo, devuelve None al agotar el tiempo", ns["esperar_feedback"](ruta, 0.1, 0.02) is None)
io.open(ruta, "w", encoding="utf-8").write("{roto")
t0 = time.time()
r.check("esperar_feedback: un JSON roto no revienta (devuelve None tras el plazo)", ns["esperar_feedback"](ruta, 0.15, 0.02) is None and time.time() - t0 < 2)
os.remove(ruta)

enviados = []
ns["escribir_comando"] = lambda orden, sobrescribir=True: enviados.append(orden)
ns["es_zona_segura"] = lambda x, y, z: True
ns["cargar_blueprint"] = lambda nombre: json.loads(json.dumps(plano)) if nombre == "casa" else None


def mensaje_final():
    return enviados[-1][0]["chat_message"]


# 1) todo se coloca a la primera
llamadas = []
ns["_despejar_terreno"] = lambda *a: llamadas.append("despejar")
ns["_colocar_y_esperar"] = lambda cmd: (llamadas.append("colocar") or (True, ""))
ns["_reabastecer"] = lambda b, c=16: (llamadas.append("restock") or True)
enviados.clear()
ns["iniciar_construccion"]("casa", 100, 64, 200, "Steve")
r.check("construcción normal: despeja PRIMERO y coloca los 3 bloques sin reabastecer", llamadas == ["despejar", "colocar", "colocar", "colocar"])
r.check("construcción normal: mensaje de éxito", "terminado" in mensaje_final() and "jefe" not in mensaje_final().lower())

# 2) falta material, el restock funciona -> se REINTENTA el mismo bloque
resultados = iter([(False, "no_material"), (True, ""), (True, ""), (True, "")])
llamadas.clear()
ns["_colocar_y_esperar"] = lambda cmd: (llamadas.append("colocar") or next(resultados))
enviados.clear()
ns["iniciar_construccion"]("casa", 100, 64, 200, "Steve")
r.check("sin material + restock OK: el bloque se reintenta (colocar, restock, colocar, ...) y no se pierde",
        llamadas == ["despejar", "colocar", "restock", "colocar", "colocar", "colocar"])
r.check("sin material + restock OK: éxito total", "terminado" in mensaje_final() and "jefe" not in mensaje_final().lower())

llamadas.clear()
ns["_colocar_y_esperar"] = lambda cmd: (llamadas.append("colocar") or (False, "no_material"))
ns["_reabastecer"] = lambda b, c=16: (llamadas.append("restock") or False)
enviados.clear()
ns["iniciar_construccion"]("casa", 100, 64, 200, "Steve")
r.check("sin material y sin cofres: solo se intenta el restock UNA vez por tipo de bloque (stone y oak_planks = 2)", llamadas.count("restock") == 2)
r.check("sin material y sin cofres: el mensaje final NO dice éxito y nombra el material que faltó",
        "completado con éxito" not in mensaje_final() and "0 bloques colocados" in mensaje_final() and "minecraft:stone" in mensaje_final())

llamadas.clear()
ns["_colocar_y_esperar"] = lambda cmd: (llamadas.append("colocar") or (False, "ocupado"))
enviados.clear()
ns["iniciar_construccion"]("casa", 100, 64, 200, "Steve")
r.check("hueco ocupado: NO se pide restock", "restock" not in llamadas)

# 5) plano inexistente
enviados.clear()
ns["iniciar_construccion"]("no_existe", 0, 0, 0, "Steve")
r.check("plano inexistente: avisa y no construye", len(enviados) == 1 and "No encontré el plano" in mensaje_final())

ns2 = cargar_cerebro()
ns2["CONFIG_FILE"] = os.path.join(tmp, "cobalt_config.json")
ns2["OBRAS_FILE"] = os.path.join(tmp, "obras.json")
io.open(ns2["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps({"logistica_base": False, "construccion_limpieza": False}))
ns2["_CONFIG_CACHE"]["t"] = 0.0  # fuerza la relectura sin esperar los 5 s
enviados2 = []
ns2["escribir_comando"] = lambda orden, sobrescribir=True: enviados2.append(orden)
r.check("_reabastecer con logistica_base=false no envía nada y devuelve False", ns2["_reabastecer"]("minecraft:stone") is False and enviados2 == [])
r.check("_despejar_terreno con construccion_limpieza=false no envía nada", ns2["_despejar_terreno"](plano, 0, 0, 0) is None and enviados2 == [])

r.terminar()
