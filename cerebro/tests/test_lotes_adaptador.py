"""F2-3 (adaptador en cerebro.py): la obra se coloca en lotes con UN resumen por lote; se reabastece y reintenta lo que falta por material; si el mod es antiguo se vuelve"""
import io
import json
import os
import tempfile

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
ns["CONFIG_FILE"] = os.path.join(tmp, "cobalt_config.json")
ns["BLUEPRINTS_DIR"] = os.path.join(tmp, "planos")
ns["FEEDBACK_BUILD"] = os.path.join(tmp, "build_feedback.json")
os.makedirs(ns["BLUEPRINTS_DIR"])
lo = ns["nox_lotes"]
enviados_chat = []
ns["escribir_comando"] = lambda ordenes, **k: enviados_chat.extend(x.get("chat_message") for x in (ordenes if isinstance(ordenes, list) else [ordenes])) or True
ns["es_zona_segura"] = lambda *a, **k: True
ns["_despejar_terreno"] = lambda *a, **k: None
ns["registrar_obra_construida"] = lambda *a, **k: None


def config(**c):
    io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps(c))
    ns["_CONFIG_CACHE"]["t"] = 0.0


def plano(nombre, bloques_por_capa):
    capas = [{"y": y, "blocks": [dict({"x": x, "z": z, "block": b}, **({"state": s} if s else {})) for x, z, b, s in bl]} for y, bl in sorted(bloques_por_capa.items())]
    io.open(os.path.join(ns["BLUEPRINTS_DIR"], nombre + ".json"), "w", encoding="utf-8").write(json.dumps({"blueprint_name": nombre, "dimensions": {"width": 30, "height": 3, "length": 30}, "layers": capas}))


class JavaFalso:

    def __init__(self, inventario=None, ocupados=(), sin_respuesta_en=(), resumen_roto_en=()):
        self.inv = dict(inventario or {})
        self.ocupados = set(ocupados)
        self.ordenes = []          # cada lote enviado (lista de bloques)
        self.puestos = []          # (x, y, z, block, state)
        self.sin_respuesta_en, self.resumen_roto_en = set(sin_respuesta_en), set(resumen_roto_en)

    def enviar(self, bloques):
        n = len(self.ordenes)
        self.ordenes.append([dict(b) for b in bloques])
        if n in self.sin_respuesta_en:
            return None, "sin_respuesta"
        if n in self.resumen_roto_en:
            return None, "resumen_invalido"
        fallos, colocados = [], 0
        for i, b in enumerate(bloques):
            pos = (b["x"], b["y"], b["z"])
            if pos in self.ocupados:
                fallos.append({"i": i, "reason": "ocupado"})
            elif self.inv.get(b["block"], 0) <= 0:
                fallos.append({"i": i, "reason": "no_material"})
            else:
                self.inv[b["block"]] -= 1
                self.ocupados.add(pos)
                self.puestos.append(pos + (b["block"], b.get("state")))
                colocados += 1
        total = len(bloques)
        resumen = {"status": "success" if colocados == total else "failed" if colocados == 0 else "partial", "placed": colocados, "total": total, "failed": fallos}
        return lo.interpretar_resumen(resumen, total), "ok"


def preparar(java, reabastece=None):
    ns["_enviar_lote"] = java.enviar
    restock = []
    ns["_LOTES"]["no_soportado"] = False

    def rea(material, cantidad=16):
        restock.append(material)
        if reabastece is None:
            return False
        reabastece(material)
        return True
    ns["_reabastecer"] = rea
    por_bloque = []

    def colocar(comando):
        por_bloque.append(dict(comando))
        return True, ""
    ns["_colocar_y_esperar"] = colocar
    enviados_chat.clear()
    return restock, por_bloque


def obra(nombre="t", origen=(100, 64, 200)):
    ns["iniciar_construccion"](nombre, origen[0], origen[1], origen[2], "Steve", registrar=False)


plano("grande", {0: [(x, z, "minecraft:stone", None) for x in range(13) for z in range(10)]})
config(construccion_por_lotes=True)
j = JavaFalso({"minecraft:stone": 500})
rest, por_bloque = preparar(j)
obra("grande")
r.check("130 bloques con lotes de 48: 3 órdenes (48, 48, 34), todos colocados y NINGÚN place_block suelto: " + str([len(x) for x in j.ordenes]),
        [len(x) for x in j.ordenes] == [48, 48, 34] and len(j.puestos) == 130 and not por_bloque and not rest)
r.check("las posiciones respetan el origen (100,64,200) y el orden de la obra: capa, luego z/x del plano", j.ordenes[0][0] == {"x": 100, "y": 64, "z": 200, "block": "minecraft:stone"} and j.ordenes[2][-1]["x"] == 112 and j.ordenes[2][-1]["z"] == 209)
r.check("el mensaje final es el de siempre ('terminado') y sin faltas: " + str(enviados_chat), len(enviados_chat) == 1 and "terminado" in enviados_chat[0] and "sin colocar" not in enviados_chat[0])

config(construccion_por_lotes=True, lotes_tamano=50)
j = JavaFalso({"minecraft:stone": 500})
preparar(j)
obra("grande")
r.check("lotes_tamano=50: lotes de 50, 50 y 30", [len(x) for x in j.ordenes] == [50, 50, 30])
config(construccion_por_lotes=True, lotes_tamano=9999)
j = JavaFalso({"minecraft:stone": 500})
preparar(j)
obra("grande")
r.check("lotes_tamano absurdo (9999): se acota a 64", [len(x) for x in j.ordenes] == [64, 64, 2])
config(construccion_por_lotes=True, lotes_tamano="mucho")
j = JavaFalso({"minecraft:stone": 500})
preparar(j)
obra("grande")
r.check("lotes_tamano que no es número: el de por defecto (48)", [len(x) for x in j.ordenes] == [48, 48, 34])
config(construccion_por_lotes=True)

plano("piedra", {0: [(x, 0, "minecraft:stone", None) for x in range(10)]})
j = JavaFalso({"minecraft:stone": 6})
rest, por_bloque = preparar(j, reabastece=lambda m: j.inv.__setitem__(m, j.inv.get(m, 0) + 20))
obra("piedra")
r.check("material insuficiente + reabastecimiento OK: 1er lote de 10 (6 colocados), se reabastece 'minecraft:stone' UNA vez y se reintentan solo los 4 que faltaron: " + str([len(x) for x in j.ordenes]) + str(rest),
        [len(x) for x in j.ordenes] == [10, 4] and rest == ["minecraft:stone"] and len(j.puestos) == 10 and "sin colocar" not in enviados_chat[0])
j = JavaFalso({"minecraft:stone": 6})
rest, por_bloque = preparar(j, reabastece=None)
obra("piedra")
r.check("material insuficiente SIN reabastecimiento: 6 colocados, 4 sin colocar, se pide reabastecer una vez y el mensaje final dice qué faltó: " + str(enviados_chat),
        len(j.puestos) == 6 and len(j.ordenes) == 1 and rest == ["minecraft:stone"] and "6 bloques colocados y 4 sin colocar" in enviados_chat[0] and "minecraft:stone" in enviados_chat[0])
plano("mucha_piedra", {0: [(x, z, "minecraft:stone", None) for x in range(10) for z in range(10)]})
j = JavaFalso({})
rest, por_bloque = preparar(j, reabastece=None)
obra("mucha_piedra")
r.check("sin ninguna piedra y sin reabastecer: el 1.er lote (48) falla, se omite el tipo entero y los lotes siguientes NO se envían (100 bloques -> 1 sola orden): " + str([len(x) for x in j.ordenes]),
        [len(x) for x in j.ordenes] == [48] and "0 bloques colocados y 100 sin colocar" in enviados_chat[0])
j = JavaFalso({"minecraft:stone": 3})
rest, por_bloque = preparar(j, reabastece=lambda m: None)  # 'reabastece' dice que sí pero no trae nada: el reintento falla otra vez
obra("piedra")
r.check("reabastece pero no llega material: el reintento se hace UNA sola vez y lo que falta se cuenta como sin colocar (no hay bucle): " + str([len(x) for x in j.ordenes]),
        [len(x) for x in j.ordenes] == [10, 7] and len(j.puestos) == 3 and "3 bloques colocados y 7 sin colocar" in enviados_chat[0])

j = JavaFalso({"minecraft:stone": 50}, ocupados={(102, 64, 200), (105, 64, 200)})
rest, por_bloque = preparar(j, reabastece=lambda m: None)
obra("piedra")
r.check("2 huecos ocupados: 8 colocados, 2 sin colocar y NO se pide material (traer más no arregla un hueco ocupado): " + str(rest), len(j.puestos) == 8 and not rest and "2 sin colocar" in enviados_chat[0])

plano("mixta", {0: [(0, 0, "minecraft:stone", None), (1, 0, "minecraft:glass", None), (2, 0, "minecraft:stone", None), (3, 0, "minecraft:glass", None), (4, 0, "minecraft:dirt", None)]})
j = JavaFalso({"minecraft:dirt": 1})
rest, por_bloque = preparar(j, reabastece=lambda m: j.inv.__setitem__(m, 10) if m == "minecraft:glass" else None)
obra("mixta")
r.check("dos materiales que faltan: se reabastece cada tipo; el vidrio llega (2 colocados en el reintento) y la piedra no (se omite): " + str(rest) + str(len(j.puestos)),
        sorted(rest) == ["minecraft:glass", "minecraft:stone"] and sorted(p[3] for p in j.puestos) == ["minecraft:dirt", "minecraft:glass", "minecraft:glass"] and "3 bloques colocados y 2 sin colocar" in enviados_chat[0])

ns["es_zona_segura"] = lambda x, y, z: x != 101
plano("dos", {0: [(0, 0, "minecraft:stone", None), (1, 0, "minecraft:stone", None), (2, 0, "minecraft:stone", None)]})
j = JavaFalso({"minecraft:stone": 10})
preparar(j)
obra("dos", origen=(100, 64, 200))
r.check("una zona no segura (x=101) se salta: no se envía ni cuenta como fallo (2 colocados, mensaje de éxito)", [b["x"] for b in j.ordenes[0]] == [100, 102] and "sin colocar" not in enviados_chat[0])
ns["es_zona_segura"] = lambda *a, **k: True

plano("est", {0: [(0, 0, "minecraft:oak_stairs", "facing=east,half=top"), (1, 0, "minecraft:stone", None)]})
j = JavaFalso({"minecraft:oak_stairs": 5, "minecraft:stone": 5})
config(construccion_por_lotes=True)
preparar(j)
obra("est")
r.check("sin schematics_estados el lote NO lleva 'state'", all("state" not in b for b in j.ordenes[0]))
j = JavaFalso({"minecraft:oak_stairs": 5, "minecraft:stone": 5})
config(construccion_por_lotes=True, schematics_estados=True)
preparar(j)
obra("est")
r.check("con schematics_estados el lote lleva 'state' solo en el bloque que lo tiene", j.ordenes[0][0].get("state") == "facing=east,half=top" and "state" not in j.ordenes[0][1])
plano("wt", {0: [(0, 0, "minecraft:wall_torch", "facing=north")]})
j = JavaFalso({})
rest, _ = preparar(j, reabastece=lambda m: j.inv.__setitem__("minecraft:wall_torch", 5))
obra("wt")
r.check("con schematics_estados y falta de material se reabastece el ÍTEM (wall_torch -> torch): " + str(rest), rest == ["minecraft:torch"])
config(construccion_por_lotes=True)

plano("cinco", {0: [(x, 0, "minecraft:stone", None) for x in range(5)]})
j = JavaFalso({"minecraft:stone": 50}, sin_respuesta_en={0})
rest, por_bloque = preparar(j)
obra("cinco")
r.check("Java sin respuesta al PRIMER lote (mod antiguo): se recuerda, NO se cuenta como fallo y la obra se hace bloque a bloque: " + str(len(por_bloque)), ns["_LOTES"]["no_soportado"] is True and len(por_bloque) == 5
        and all(c["action"] == "place_block" for c in por_bloque) and len(j.ordenes) == 1 and "sin colocar" not in enviados_chat[0])
por_bloque.clear()
obra("cinco")
r.check("la siguiente obra ya no vuelve a intentar lotes (ahorra la espera de 10 s)", len(j.ordenes) == 1 and len(por_bloque) == 5)

j = JavaFalso({"minecraft:stone": 500}, sin_respuesta_en={1})
rest, por_bloque = preparar(j)
obra("grande")
r.check("un lote sin respuesta a MITAD de obra (no el primero): se cuenta como sin colocar, NO se marca 'no soportado' y la obra sigue con el lote siguiente: " + str([len(x) for x in j.ordenes]),
        [len(x) for x in j.ordenes] == [48, 48, 34] and not ns["_LOTES"]["no_soportado"] and len(j.puestos) == 82 and "82 bloques colocados y 48 sin colocar" in enviados_chat[0])
j = JavaFalso({"minecraft:stone": 500}, resumen_roto_en={0})
rest, por_bloque = preparar(j)
obra("grande")
r.check("un resumen NO fiable en el primer lote (Java contestó, pero incoherente): tampoco es 'mod antiguo'; se cuentan sin colocar y sigue", not ns["_LOTES"]["no_soportado"] and len(j.ordenes) == 3 and len(j.puestos) == 82 and not por_bloque)

config(construccion_por_lotes=False)
j = JavaFalso({"minecraft:stone": 50})
rest, por_bloque = preparar(j)
obra("cinco")
r.check("construccion_por_lotes=false: place_block uno a uno y ningún lote", len(por_bloque) == 5 and not j.ordenes)
config()
j = JavaFalso({"minecraft:stone": 50})
rest, por_bloque = preparar(j)
obra("cinco")
r.check("sin la clave en la configuración: apagado por defecto (camino de siempre)", len(por_bloque) == 5 and not j.ordenes)

ns2 = cargar_cerebro()
ns2["FEEDBACK_BUILD"] = os.path.join(tmp, "fb2.json")
sent = []
ns2["escribir_comando"] = lambda orden, **k: sent.append(orden) or True
lote = [{"x": 1, "y": 2, "z": 3, "block": "minecraft:stone"}, {"x": 4, "y": 5, "z": 6, "block": "minecraft:dirt"}]
io.open(ns2["FEEDBACK_BUILD"], "w", encoding="utf-8").write(json.dumps({"status": "success", "placed": 99, "total": 99, "failed": []}))  # un resumen VIEJO: debe borrarse antes de enviar
ns2["esperar_feedback"] = lambda ruta, s, intervalo=0.5: (json.load(open(ruta)) if os.path.exists(ruta) else {"status": "partial", "placed": 1, "total": 2, "failed": [{"i": 1, "reason": "ocupado"}]})
res, motivo = ns2["_enviar_lote"](lote)
r.check("_enviar_lote: borra el resumen viejo, envía la orden place_blocks y devuelve el resumen validado: " + str((res, motivo)), motivo == "ok" and res == {"colocados": [0], "fallos": {1: "ocupado"}} and sent[0]["action"] == "place_blocks" and len(sent[0]["blocks"]) == 2)
ns2["esperar_feedback"] = lambda ruta, s, intervalo=0.5: None
r.check("_enviar_lote: sin respuesta -> (None, 'sin_respuesta')", ns2["_enviar_lote"](lote) == (None, "sin_respuesta"))
ns2["esperar_feedback"] = lambda ruta, s, intervalo=0.5: {"status": "success", "placed": 5, "total": 5, "failed": []}
r.check("_enviar_lote: un resumen que no cuadra con lo enviado -> (None, 'resumen_invalido')", ns2["_enviar_lote"](lote) == (None, "resumen_invalido"))
ns2["escribir_comando"] = lambda orden, **k: False
r.check("_enviar_lote: si no se pudo escribir command.json -> (None, 'envio')", ns2["_enviar_lote"](lote) == (None, "envio"))


def explota(*a, **k):
    raise OSError("disco")


ns2["escribir_comando"] = explota
r.check("_enviar_lote: una excepción al enviar -> (None, 'envio') sin lanzar", ns2["_enviar_lote"](lote) == (None, "envio"))

r.terminar()
