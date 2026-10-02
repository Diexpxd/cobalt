"""Retomar la tarea anterior (nox_reanudar): la frase se detecta y se quita del mensaje, la última orden larga se recuerda y se reenvía cuando Cobalt queda libre, y si ya"""
import os
import sys

from _cargar import Resultados

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_reanudar as n  # noqa: E402

r = Resultados()

for msg, resto in (("ven atiende los hornos y continua con tu antigua tarea", "ven atiende los hornos"),
                   ("Ven, atiende los hornos y luego sigue con lo que estabas haciendo", "Ven, atiende los hornos"),
                   ("ve a la base y retoma tu tarea anterior", "ve a la base"),
                   ("continúa con tu tarea anterior", ""), ("retoma lo que hacías", ""), ("Cobalt, sigue con lo tuyo", "Cobalt"),
                   ("atiende los hornos y después continúa con la tarea de antes", "atiende los hornos")):
    limpio, pidio = n.separar_peticion(msg)
    r.check(f"petición en '{msg}' -> resto '{resto}'", pidio is True and limpio == resto)
for msg in ("sigue minando", "continúa", "sigue con la construcción", "no continúes con tu tarea", "no sigas con lo que hacías", "termina la partida", "hola", "ven"):
    limpio, pidio = n.separar_peticion(msg)
    r.check(f"NO es una petición de retomar: '{msg}'", pidio is False and limpio == msg)

orden_mina = {"action": "mine", "material": "iron_ore", "amount": 10, "target": "Steve", "movement_mode": "walk"}
estado_libre = {"is_deployed": True, "task": None, "queue": 0}
estado_ocupado = {"is_deployed": True, "task": "clear_area 3/18", "queue": 1}
feedbacks = {}
x = n.Reanudador(lambda nombre: feedbacks.get(nombre))
x.registrar(orden_mina, 100.0)
x.registrar({"action": "tend_furnaces", "radius": 10}, 110.0)      # atender hornos NO pisa la tarea larga
x.registrar({"action": "ninguna", "chat_message": "hola"}, 111.0)
r.check("lo que no es una tarea larga no pisa la anterior", x.anterior["orden"]["action"] == "mine")
x.registrar({"action": "flatten_area", "x1": 0, "z1": 0, "x2": 5, "z2": 5, "y": 64}, 120.0)
r.check("una tarea larga nueva sustituye a la anterior", x.anterior["orden"]["action"] == "flatten_area")

x = n.Reanudador(lambda nombre: feedbacks.get(nombre))
x.registrar(orden_mina, 100.0)
x.pedir(200.0)
r.check("sin haber pasado el tiempo mínimo no hace nada", x.actualizar(estado_libre, 200.5) == [])
r.check("con Cobalt ocupado (atendiendo los hornos) espera", x.actualizar(estado_ocupado, 205.0) == [] and x.actualizar(estado_ocupado, 210.0) == [])
r.check("el primer ciclo libre todavía no retoma (puede ser el hueco entre dos tareas)", x.actualizar(estado_libre, 212.0) == [])
res = x.actualizar(estado_libre, 214.0)
r.check("el segundo ciclo libre reenvía la tarea anterior", len(res) == 1 and res[0]["action"] == "mine" and res[0]["material"] == "iron_ore" and res[0]["amount"] == 10)
r.check("y lo dice en el chat", "Retomo lo que estaba haciendo: minar iron_ore" in res[0]["chat_message"])
r.check("la petición se consume (no retoma dos veces)", x.actualizar(estado_libre, 220.0) == [] and x.actualizar(estado_libre, 226.0) == [])
r.check("la orden reenviada no altera la original guardada", x.anterior["orden"].get("chat_message") is None)

x = n.Reanudador(lambda nombre: feedbacks.get(nombre))
x.registrar({"action": "flatten_area", "x1": 0, "z1": 0, "x2": 5, "z2": 5, "y": 64}, 100.0)
feedbacks["terraform_feedback.json"] = {"status": "success", "_mtime": 150.0}
x.pedir(200.0)
x.actualizar(estado_libre, 203.0)
res = x.actualizar(estado_libre, 205.0)
r.check("tarea cumplida: no la repite, dice que ya la terminó", len(res) == 1 and res[0]["action"] == "ninguna" and "ya la terminé" in res[0]["chat_message"] and "aplanar" in res[0]["chat_message"])

x = n.Reanudador(lambda nombre: feedbacks.get(nombre))
x.registrar({"action": "flatten_area", "x1": 0, "z1": 0, "x2": 5, "z2": 5, "y": 64}, 300.0)
x.pedir(400.0)
x.actualizar(estado_libre, 403.0)
res = x.actualizar(estado_libre, 405.0)
r.check("feedback viejo (de otra vez): se retoma, no se da por cumplida", len(res) == 1 and res[0]["action"] == "flatten_area")

# cancelada por 'alto' (status 'failed'/'partial'): se retoma
feedbacks["terraform_feedback.json"] = {"status": "partial", "_mtime": 350.0}
x = n.Reanudador(lambda nombre: feedbacks.get(nombre))
x.registrar({"action": "flatten_area", "x1": 0, "z1": 0, "x2": 5, "z2": 5, "y": 64}, 300.0)
x.pedir(400.0)
x.actualizar(estado_libre, 403.0)
res = x.actualizar(estado_libre, 405.0)
r.check("cancelada con 'alto' (partial): se retoma", len(res) == 1 and res[0]["action"] == "flatten_area")

# minar: solo lo que falta
feedbacks["mine_feedback.json"] = {"status": "partial", "wanted": 10, "mined": 4, "_mtime": 250.0}
x = n.Reanudador(lambda nombre: feedbacks.get(nombre))
x.registrar(orden_mina, 200.0)
x.pedir(300.0)
x.actualizar(estado_libre, 303.0)
res = x.actualizar(estado_libre, 305.0)
r.check("minar: retoma solo lo que faltaba (10 - 4 = 6)", len(res) == 1 and res[0]["amount"] == 6)

feedbacks["chop_feedback.json"] = {"status": "partial", "wanted": 32, "chopped": 12, "_mtime": 250.0}
x = n.Reanudador(lambda nombre: feedbacks.get(nombre))
x.registrar({"action": "chop_wood", "radius": 16, "amount": 32, "target": "Steve", "material": "cualquiera", "movement_mode": "walk"}, 200.0)
x.pedir(300.0)
x.actualizar(estado_libre, 303.0)
res = x.actualizar(estado_libre, 305.0)
r.check("talar: retoma solo los troncos que faltaban (32 - 12 = 20) y conserva el radio", len(res) == 1 and res[0]["action"] == "chop_wood" and res[0]["amount"] == 20 and res[0]["radius"] == 16)
r.check("talar: lo describe como talar árboles", "talar" in res[0]["chat_message"])
feedbacks["chop_feedback.json"] = {"status": "success", "wanted": 32, "chopped": 32, "_mtime": 250.0}
x = n.Reanudador(lambda nombre: feedbacks.get(nombre))
x.registrar({"action": "chop_wood", "radius": 16, "amount": 32}, 200.0)
x.pedir(300.0)
x.actualizar(estado_libre, 303.0)
res = x.actualizar(estado_libre, 305.0)
r.check("talar: si ya terminó, lo dice y no vuelve a talar", len(res) == 1 and res[0]["action"] == "ninguna" and "ya la terminé" in res[0]["chat_message"])

# pescar: se retoma con lo que falta de capturas
feedbacks["fish_feedback.json"] = {"status": "partial", "wanted": 10, "caught": 3, "_mtime": 250.0}
x = n.Reanudador(lambda nombre: feedbacks.get(nombre))
x.registrar({"action": "fish", "radius": 16, "amount": 10, "target": "Steve", "material": "cualquiera", "movement_mode": "walk"}, 200.0)
x.pedir(300.0)
x.actualizar(estado_libre, 303.0)
res = x.actualizar(estado_libre, 305.0)
r.check("pescar: retoma solo las capturas que faltaban (10 - 3 = 7) y lo describe como pescar", len(res) == 1 and res[0]["action"] == "fish" and res[0]["amount"] == 7 and "pescar" in res[0]["chat_message"])

x = n.Reanudador()
x.pedir(100.0)
x.actualizar(estado_libre, 103.0)
res = x.actualizar(estado_libre, 105.0)
r.check("sin tarea anterior: lo dice", len(res) == 1 and "ninguna tarea anterior" in res[0]["chat_message"])
x = n.Reanudador()
x.registrar(orden_mina, 100.0)
x.pedir(100.0)
r.check("ocupado más de 15 min: se olvida la petición", x.actualizar(estado_ocupado, 100.0 + n.TIMEOUT_S + 5) == [] and x.pendiente_desde is None)
x.pedir(2000.0)
r.check("Cobalt no desplegado: no hace nada (y sigue pendiente)", x.actualizar({"is_deployed": False}, 2010.0) == [] and x.pendiente_desde is not None)
r.check("sin haberlo pedido no hace nada", n.Reanudador().actualizar(estado_libre, 1.0) == [])

r.terminar()
