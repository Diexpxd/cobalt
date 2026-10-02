"""Bloque N (adaptador en cerebro.py): los flujos de obra de extremo a extremo contra un 'Java falso' que responde a scan_terrain, scan_blocks y flatten_area."""
import json
import os
import tempfile
import threading
import types
import time as _time

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
ns["BLUEPRINTS_DIR"] = os.path.join(tmp, "blueprints")
ns["OBRAS_FILE"] = os.path.join(tmp, "obras.json")
ns["CONFIG_FILE"] = os.path.join(tmp, "cobalt_config.json")
os.makedirs(ns["BLUEPRINTS_DIR"])
ESTADO = {}
ns["config_activa"] = lambda clave, defecto=True: ESTADO.get(clave, defecto)
ns["time"] = types.SimpleNamespace(sleep=lambda s: None, time=_time.time, strftime=_time.strftime)  # sin esperas reales
GPS = {"x": 100.5, "y": 64.0, "z": 200.5, "dimension": "minecraft:overworld"}
ns["leer_gps"] = lambda: dict(GPS)

ordenes = []          # todas las órdenes enviadas a Java
mensajes = []         # todo lo que Cobalt dice
construcciones = []   # llamadas a iniciar_construccion
RELIEVE = {"altura": lambda x, z: 64, "tipo": lambda x, z: 0}
MUNDO = {}            # {(x,y,z): id} para scan_blocks
SIN_CARGAR = [0]
RESPUESTAS_TERRAFORMAR = []   # feedbacks que devuelve flatten_area / fill_fluid, en orden
REABASTECIDOS = []


def java_falso(orden, ruta, espera, intervalo=0.5, intentos=1):
    ordenes.append(dict(orden))
    a = orden["action"]
    if a == "scan_terrain":
        xs, zs = range(orden["x1"], orden["x2"] + 1), range(orden["z1"], orden["z2"] + 1)
        return {"status": "success", "x1": orden["x1"], "z1": orden["z1"], "x2": orden["x2"], "z2": orden["z2"],
                "y": [[RELIEVE["altura"](x, z) for x in xs] for z in zs], "t": [[RELIEVE["tipo"](x, z) for x in xs] for z in zs]}
    if a == "scan_blocks":
        x0, y0, z0 = min(orden["x1"], orden["x2"]), min(orden["y1"], orden["y2"]), min(orden["z1"], orden["z2"])
        x1, y1, z1 = max(orden["x1"], orden["x2"]), max(orden["y1"], orden["y2"]), max(orden["z1"], orden["z2"])
        paleta, bloques = [], []
        for (x, y, z), ident in MUNDO.items():
            if x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1:
                if ident not in paleta:
                    paleta.append(ident)
                bloques.append([x - x0, y - y0, z - z0, paleta.index(ident)])
        return {"status": "success", "x0": x0, "y0": y0, "z0": z0, "palette": paleta, "blocks": bloques, "unloaded": SIN_CARGAR[0], "truncated": False}
    if a in ("flatten_area", "fill_fluid"):
        return RESPUESTAS_TERRAFORMAR.pop(0) if RESPUESTAS_TERRAFORMAR else {"status": "success"}
    return None


ns["_pedir"] = java_falso
ns["_decir"] = lambda username, texto: mensajes.append(texto)
ns["iniciar_construccion"] = lambda *args, **kw: construcciones.append((args, kw))
ns["_reabastecer"] = lambda bloque, cantidad=16: REABASTECIDOS.append(bloque) or True


def reset():
    ordenes.clear()
    mensajes.clear()
    construcciones.clear()
    RESPUESTAS_TERRAFORMAR.clear()
    REABASTECIDOS.clear()
    MUNDO.clear()
    SIN_CARGAR[0] = 0
    RELIEVE["altura"], RELIEVE["tipo"] = (lambda x, z: 64), (lambda x, z: 0)
    ESTADO.clear()


def plano_de(celdas, nombre):
    ns["_guardar_plano"](ns["nox_obra"]._plano_desde_celdas(celdas, nombre), nombre, sobrescribir=True)


def caja_maciza(ancho, alto, largo, bloque="minecraft:stone_bricks"):
    return {(x, y, z): bloque for x in range(ancho) for y in range(alto) for z in range(largo)}


reset()
RELIEVE["altura"] = lambda x, z: 67 if (x, z) in ((99, 199), (101, 201)) else 64
ns["flujo_aplanar"]({"ancho": 5, "largo": 5}, "Steve")
vuelo = [o for o in ordenes if o["action"] == "flatten_area"]
r.check("aplanar: escanea la caja 5x5 centrada en Cobalt y envía flatten_area a la altura MEDIANA (64) con esa misma caja",
        len(vuelo) == 1 and (vuelo[0]["x1"], vuelo[0]["z1"], vuelo[0]["x2"], vuelo[0]["z2"], vuelo[0]["y"]) == (98, 198, 102, 202, 64)
        and ordenes[0]["action"] == "scan_terrain" and (ordenes[0]["x1"], ordenes[0]["x2"]) == (98, 102))
RESPUESTAS_TERRAFORMAR[:] = []
reset()
RESPUESTAS_TERRAFORMAR.append({"status": "success", "planned_dig": 6, "dug": 6, "planned_fill": 0, "placed": 0, "blocked_columns": 1})
ns["flujo_aplanar"]({"ancho": 5, "largo": 5}, "Steve")
r.check("aplanar: el informe final cuenta lo cavado y las columnas bloqueadas", any("cavé 6 de 6" in m and "1 columna" in m for m in mensajes))
reset()
RELIEVE["tipo"] = lambda x, z: 1  # todo agua
ns["flujo_aplanar"]({"ancho": 5, "largo": 5}, "Steve")
r.check("aplanar: si todo es agua NO se envía flatten_area y se explica", not any(o["action"] == "flatten_area" for o in ordenes) and any("no hay suelo natural" in m for m in mensajes))
reset()
ns["leer_gps"] = lambda: {}
ns["flujo_aplanar"]({"ancho": 5, "largo": 5}, "Steve")
r.check("aplanar: sin GPS no envía nada", ordenes == [] and any("sin GPS" in m for m in mensajes))
ns["leer_gps"] = lambda: dict(GPS)

reset()
ns["flujo_rellenar"]({"fluido": "lava", "radio": 8}, "Steve")
r.check("rellenar: envía fill_fluid de lava con el radio", [o for o in ordenes if o["action"] == "fill_fluid"] == [{"action": "fill_fluid", "fluid": "lava", "radius": 8, "movement_mode": "walk"}])
reset()
RESPUESTAS_TERRAFORMAR[:] = [{"status": "partial", "missing_material": True, "planned_fill": 50, "placed": 20}, {"status": "success", "planned_fill": 30, "placed": 30}]
ns["flujo_rellenar"]({"fluido": "lava", "radio": 8}, "Steve")
r.check("rellenar: si falta ripio pide cobblestone a los cofres y REPITE la orden", len([o for o in ordenes if o["action"] == "fill_fluid"]) == 2 and REABASTECIDOS == ["minecraft:cobblestone"])
reset()
RESPUESTAS_TERRAFORMAR[:] = [{"status": "partial", "missing_material": True}] * 5
ns["flujo_rellenar"]({"fluido": "water", "radio": 4}, "Steve")
r.check("rellenar: si SIEMPRE falta ripio se detiene a los 3 intentos (2 reabastecimientos), no en bucle", len([o for o in ordenes if o["action"] == "fill_fluid"]) == 3 and len(REABASTECIDOS) == 2)
reset()
ns["_reabastecer"] = lambda bloque, cantidad=16: REABASTECIDOS.append(bloque) or False
RESPUESTAS_TERRAFORMAR[:] = [{"status": "partial", "missing_material": True}] * 5
ns["flujo_rellenar"]({"fluido": "lava", "radio": 8}, "Steve")
r.check("rellenar: si los cofres no tienen ripio, no reintenta", len([o for o in ordenes if o["action"] == "fill_fluid"]) == 1)
ns["_reabastecer"] = lambda bloque, cantidad=16: REABASTECIDOS.append(bloque) or True

reset()
plano_de(caja_maciza(5, 2, 5), "casa")
ns["flujo_sitio"]({"plano": "casa"}, "Steve")
args, _ = construcciones[0]
r.check("sitio: en terreno llano no aplana y construye 'casa' sobre y=65 (suelo 64 + 1), cerca de Cobalt",
        len(construcciones) == 1 and args[0] == "casa" and args[2] == 65 and not any(o["action"] == "flatten_area" for o in ordenes)
        and abs(args[1] + 2 - 100) <= 3 and abs(args[3] + 2 - 200) <= 3 and args[4] == "Steve")
reset()
RELIEVE["altura"] = lambda x, z: 64 + ((x * 7 + z * 3) % 3)  # terreno rugoso en todas partes: hay que nivelar
plano_de(caja_maciza(5, 2, 5), "casa")
RESPUESTAS_TERRAFORMAR.append({"status": "success", "planned_dig": 10, "dug": 10})
ns["flujo_sitio"]({"plano": "casa"}, "Steve")
vuelo = [o for o in ordenes if o["action"] == "flatten_area"]
args, _ = construcciones[0] if construcciones else ((), {})
r.check("sitio: en terreno rugoso primero envía flatten_area sobre la ventana elegida y DESPUÉS construye encima (y+1)",
        len(vuelo) == 1 and vuelo[0]["x2"] - vuelo[0]["x1"] == 4 and vuelo[0]["z2"] - vuelo[0]["z1"] == 4 and len(construcciones) == 1
        and args[2] == vuelo[0]["y"] + 1 and args[1] == vuelo[0]["x1"] and args[3] == vuelo[0]["z1"])
reset()
RELIEVE["altura"] = lambda x, z: 64 + ((x * 7 + z * 3) % 3)
plano_de(caja_maciza(5, 2, 5), "casa")
RESPUESTAS_TERRAFORMAR.append({"status": "partial", "blocked_columns": 2, "dug": 3, "planned_dig": 5})
ns["flujo_sitio"]({"plano": "casa"}, "Steve")
r.check("sitio: si el aplanado deja columnas bloqueadas NO construye y lo explica", construcciones == [] and any("No construyo" in m for m in mensajes))
reset()
plano_de(caja_maciza(5, 2, 5), "casa")
ns["flujo_sitio"]({"plano": "casa", "ancho": 8, "largo": 6}, "Steve")
guardado = ns["cargar_blueprint"]("casa_8x6")
args, _ = construcciones[0] if construcciones else ((), {})
r.check("sitio: con tamaño pedido estira el plano (8x6), lo guarda como casa_8x6 y construye ESE", guardado is not None and ns["nox_obra"].dimensiones_de_plano(guardado)[0] == 8
        and ns["nox_obra"].dimensiones_de_plano(guardado)[2] == 6 and args[0] == "casa_8x6")
reset()
ns["flujo_sitio"]({"plano": "no_existe"}, "Steve")
r.check("sitio: plano inexistente -> aviso y nada más", construcciones == [] and ordenes == [] and any("No encontré el plano" in m for m in mensajes))
reset()
RELIEVE["tipo"] = lambda x, z: 1
plano_de(caja_maciza(5, 2, 5), "casa")
ns["flujo_sitio"]({"plano": "casa"}, "Steve")
r.check("sitio: si no hay ningún sitio llano lo dice y no construye", construcciones == [] and any("No encuentro un sitio" in m for m in mensajes))
reset()
ns["obtener_coordenadas_base"] = lambda: {"x": 100, "y": 64, "z": 200}
plano_de(caja_maciza(5, 2, 5), "casa")
ns["flujo_sitio"]({"plano": "casa"}, "Steve")
args, _ = construcciones[0] if construcciones else ((), {})
r.check("sitio: con la base justo aquí el sitio queda FUERA de los 32 bloques de la base (la construcción se bloquearía si no)",
        len(construcciones) == 1 and ((max(args[1] - 100, 0, 100 - (args[1] + 4)) ** 2 + max(args[3] - 200, 0, 200 - (args[3] + 4)) ** 2 + 1) ** 0.5) > 32.0)
ns["obtener_coordenadas_base"] = lambda: None

reset()
ns["buscar_waypoint"] = lambda nombre: ("mina", {"x": 130, "y": 64, "z": 200, "dimension": "minecraft:overworld"}) if "mina" in nombre else None
RELIEVE["tipo"] = lambda x, z: 1 if 115 <= x <= 116 else 0
ns["flujo_camino"]({"destino": "mina", "ancho": 1}, "Steve")
plano_c = ns["cargar_blueprint"]("camino_mina")
celdas_c = ns["nox_obra"]._celdas_de_plano(plano_c) if plano_c else {}
args, _ = construcciones[0] if construcciones else ((), {})
r.check("camino: 31 bloques de (100,200) a (130,200), 2 de ellos tablones de puente, y se construye desde la esquina mínima a y=65",
        len(celdas_c) == 31 and sum(1 for i in celdas_c.values() if i.endswith("oak_planks")) == 2 and args[:4] == ("camino_mina", 100, 65, 200))
r.check("camino: el aviso cuenta los materiales", any("29 de cobblestone y 2 de oak_planks" in m for m in mensajes))
reset()
ns["flujo_camino"]({"destino": "mina", "ancho": 3}, "Steve")
celdas_c = ns["nox_obra"]._celdas_de_plano(ns["cargar_blueprint"]("camino_mina_2") or {"layers": []})
r.check("camino: de ancho 3 ocupa 3 filas (93 celdas en llano) y se guarda SIN pisar el anterior (camino_mina_2)", len(celdas_c) == 93)
reset()
ns["buscar_waypoint"] = lambda nombre: ("lejos", {"x": 300, "y": 64, "z": 200})
ns["flujo_camino"]({"destino": "lejos", "ancho": 1}, "Steve")
r.check("camino: un destino a más de 56 bloques se rechaza SIN escanear", ordenes == [] and any("tramos de hasta 56" in m for m in mensajes))
reset()
ns["buscar_waypoint"] = lambda nombre: ("nether", {"x": 110, "y": 64, "z": 200, "dimension": "minecraft:the_nether"})
ns["flujo_camino"]({"destino": "nether", "ancho": 1}, "Steve")
r.check("camino: un destino en otra dimensión se rechaza", ordenes == [] and any("otra dimensión" in m for m in mensajes))
reset()
ns["buscar_waypoint"] = lambda nombre: None
ns["flujo_camino"]({"destino": "fantasma", "ancho": 1}, "Steve")
r.check("camino: un lugar desconocido se dice claro", any("No conozco el lugar 'fantasma'" in m for m in mensajes) and construcciones == [])
reset()
ns["buscar_waypoint"] = lambda nombre: ("mina", {"x": 130, "y": 64, "z": 200})
RELIEVE["tipo"] = lambda x, z: 2 if x == 115 else 0  # muro de lava de lado a lado
ns["flujo_camino"]({"destino": "mina", "ancho": 1}, "Steve")
r.check("camino: un muro de lava completo -> 'No hay ruta' y no se construye nada", construcciones == [] and any("No hay ruta" in m for m in mensajes))

reset()
MUNDO.update({(10 + x, 64 + y, 20 + z): i for (x, y, z), i in caja_maciza(3, 2, 3).items()})
MUNDO[(9, 64, 20)] = "minecraft:chest"
ns["flujo_copiar"]({"caja": (9, 64, 20, 13, 66, 23), "nombre": "torrecita"}, "Steve")
copia = ns["cargar_blueprint"]("torrecita")
r.check("copiar: guarda el plano (18 bloques de piedra, sin el cofre) y avisa de lo omitido y de la orientación",
        copia is not None and len(ns["nox_obra"]._celdas_de_plano(copia)) == 18 and any("No copio: 1 chest" in m and "orientación" in m for m in mensajes))
reset()
MUNDO[(0, 0, 0)] = "minecraft:stone"
SIN_CARGAR[0] = 5
ns["flujo_copiar"]({"caja": (0, 0, 0), "nombre": "x"} if False else {"caja": (0, 0, 0, 3, 3, 3), "nombre": "cargado_a_medias"}, "Steve")
r.check("copiar: con chunks sin cargar NO guarda un plano incompleto", ns["cargar_blueprint"]("cargado_a_medias") is None and any("no están cargadas" in m for m in mensajes))
reset()
ns["flujo_copiar"]({"caja": (0, 0, 0, 99, 99, 99), "nombre": "enorme"}, "Steve")
r.check("copiar: una caja de 1.000.000 de celdas se rechaza sin escanear", ordenes == [] and any("copio como máximo" in m for m in mensajes))
reset()
ns["flujo_copiar"]({"caja": (0, 0, 0, 3, 3, 3), "nombre": "vacio"}, "Steve")
r.check("copiar: una zona sin bloques da un aviso claro", ns["cargar_blueprint"]("vacio") is None and any("no hay bloques copiables" in m for m in mensajes))
reset()
ns["buscar_waypoint"] = lambda n: (n, {"x": 10 if n == "torre_a" else 12, "y": 64, "z": 20}) if n in ("torre_a", "torre_b") else None
MUNDO.update({(x, 64, 20): "minecraft:stone" for x in range(10, 13)})
ns["flujo_copiar"]({"waypoints": ("torre_a", "torre_b"), "nombre": "entre_torres"}, "Steve")
r.check("copiar: entre dos lugares guardados usa sus coordenadas como esquinas", len(ns["nox_obra"]._celdas_de_plano(ns["cargar_blueprint"]("entre_torres") or {"layers": []})) == 3)
reset()
ns["flujo_copiar"]({"waypoints": ("torre_a", "fantasma"), "nombre": "z"}, "Steve")
r.check("copiar: un lugar desconocido entre los dos se nombra", any("fantasma" in m for m in mensajes) and ordenes == [])

reset()
celdas_casa = caja_maciza(4, 3, 4)
plano_de(celdas_casa, "fortin")
ns["registrar_obra_construida"]("fortin", (500, 70, -30))
r.check("registro: la obra queda en obras.json con su origen y dimensión", ns["cargar_obras"]()["fortin"]["x"] == 500 and ns["cargar_obras"]()["fortin"]["dimension"] == "minecraft:overworld")
for (x, y, z), i in celdas_casa.items():
    MUNDO[(500 + x, 70 + y, -30 + z)] = i
ns["flujo_reparar"]({"obra": "fortin"}, "Steve")
r.check("reparar: una obra intacta solo lo dice (no construye)", construcciones == [] and any("en orden" in m and "48 bloques correctos" in m for m in mensajes))
reset()
for (x, y, z), i in celdas_casa.items():
    MUNDO[(500 + x, 70 + y, -30 + z)] = i
del MUNDO[(500, 71, -30)]
del MUNDO[(503, 72, -27)]
MUNDO[(501, 70, -30)] = "minecraft:dirt"
ns["flujo_reparar"]({"obra": ""}, "Steve")
rep = ns["cargar_blueprint"]("reparacion_fortin")
args, kw = construcciones[0] if construcciones else ((), {})
r.check("reparar: repone SOLO los 2 huecos (el bloque distinto no se toca), con registrar=False y origen en la esquina mínima de lo que falta",
        rep is not None and len(ns["nox_obra"]._celdas_de_plano(rep)) == 2 and args[:2] == ("reparacion_fortin", 500) and args[2:4] == (71, -30) and kw == {"registrar": False}
        and any("faltan 2 bloques" in m and "1 bloque(s) distintos" in m and "no los toco" in m for m in mensajes))
reset()
ns["flujo_reparar"]({"obra": "castillo"}, "Steve")
r.check("reparar: una obra desconocida lista las conocidas", construcciones == [] and any("fortin" in m for m in mensajes))
reset()
SIN_CARGAR[0] = 4
for (x, y, z), i in celdas_casa.items():
    MUNDO[(500 + x, 70 + y, -30 + z)] = i
ns["flujo_reparar"]({"obra": "fortin"}, "Steve")
r.check("reparar: con chunks sin cargar no adivina (no construye)", construcciones == [] and any("no están cargadas" in m for m in mensajes))
reset()
ns["leer_gps"] = lambda: {"x": 0, "y": 0, "z": 0, "dimension": "minecraft:the_nether"}
ns["flujo_reparar"]({"obra": "fortin"}, "Steve")
r.check("reparar: una obra de otra dimensión no se toca", ordenes == [] and any("otra dimensión" in m for m in mensajes))
ns["leer_gps"] = lambda: dict(GPS)

reset()
real_iniciar = ns.pop("iniciar_construccion")  # el 'falso' estaba en ns; se recarga el real
ns2 = cargar_cerebro()
for k in ("BLUEPRINTS_DIR", "OBRAS_FILE", "config_activa", "time", "leer_gps", "_decir"):
    ns2[k] = ns[k]
ns2["_despejar_terreno"] = lambda *a: None
ns2["es_zona_segura"] = lambda *a: True
ns2["_colocar_y_esperar"] = lambda comando: (True, "")
ns2["escribir_comando"] = lambda *a, **k: True
plano_de({(0, 0, 0): "minecraft:stone", (1, 0, 0): "minecraft:stone"}, "mini")
ns2["iniciar_construccion"]("mini", 10, 64, 10, "Steve")
r.check("iniciar_construccion: al terminar registra la obra en obras.json", ns["cargar_obras"]().get("mini", {}).get("x") == 10)
ns2["iniciar_construccion"]("mini", 99, 64, 99, "Steve", registrar=False)
r.check("iniciar_construccion(registrar=False) no pisa el registro", ns["cargar_obras"]()["mini"]["x"] == 10)
ESTADO["obra_reparar"] = False
ns2["iniciar_construccion"]("mini", 77, 64, 77, "Steve")
r.check("iniciar_construccion con obra_reparar=false no registra", ns["cargar_obras"]()["mini"]["x"] == 10)
ns["iniciar_construccion"] = lambda *args, **kw: construcciones.append((args, kw))

reset()
ns["leer_gps"] = lambda: {"x": 800.0, "y": 64.0, "z": -160.0, "dimension": "minecraft:overworld"}
o = ns["interceptar_obra"]("¿dónde pongo el portal del nether?", "Steve")
r.check("chat portal: sin destino usa la posición de Cobalt y responde con la conversión 8:1", o and "X=100, Z=-20" in o[0]["chat_message"] and o[0]["action"] == "ninguna")
ns["buscar_waypoint"] = lambda n: ("mina", {"x": 80, "y": 12, "z": 16, "dimension": "minecraft:overworld"}) if "mina" in n else None
o = ns["interceptar_obra"]("dónde pongo el portal del nether para la mina", "Steve")
r.check("chat portal: con un lugar guardado convierte SUS coordenadas", o and "X=80, Z=16 (mina)" in o[0]["chat_message"] and "X=10, Z=2" in o[0]["chat_message"])
o = ns["interceptar_obra"]("dónde pongo el portal del nether para la torre", "Steve")
r.check("chat portal: lugar desconocido -> lo dice", o and "No conozco el lugar 'torre'" in o[0]["chat_message"])
ESTADO["obra_portales"] = False
r.check("chat portal: con el interruptor apagado no lo intercepta (None)", ns["interceptar_obra"]("dónde pongo el portal del nether para la mina", "Steve") is None)
ESTADO.clear()
r.check("chat: un mensaje que no es de obra -> None", ns["interceptar_obra"]("hola cobalt, ¿qué tal?", "Steve") is None and ns["interceptar_obra"]("mina hierro", "Steve") is None)
ns["leer_gps"] = lambda: dict(GPS)

# una sola obra a la vez
liberar = threading.Event()
iniciado = threading.Event()


def flujo_lento(it, username):
    iniciado.set()
    liberar.wait(5)


ns["_FLUJOS_OBRA"]["aplanar"] = flujo_lento
o1 = ns["interceptar_obra"]("aplana 10x10", "Steve")
iniciado.wait(5)
o2 = ns["interceptar_obra"]("rellena la lava", "Steve")
r.check("obra: la primera arranca en su hilo y la segunda, mientras tanto, recibe 'ya estoy con otra obra'",
        o1 and "aplanar" in o1[0]["chat_message"] and o2 and "otra obra" in o2[0]["chat_message"])
liberar.set()
for _ in range(100):
    if not ns["_OBRA_LOCK"].locked():
        break
    _time.sleep(0.02)
r.check("obra: al terminar el hilo el cerrojo se libera", not ns["_OBRA_LOCK"].locked())


def flujo_roto(it, username):
    raise RuntimeError("boom")


ns["_FLUJOS_OBRA"]["aplanar"] = flujo_roto
mensajes.clear()
ns["interceptar_obra"]("aplana 10x10", "Steve")
for _ in range(100):
    if not ns["_OBRA_LOCK"].locked():
        break
    _time.sleep(0.02)
r.check("obra: si un flujo revienta, lo dice, no tumba el hilo y libera el cerrojo", not ns["_OBRA_LOCK"].locked() and any("error interno" in m for m in mensajes))
r.check("obra: con el interruptor apagado ('aplanado_terreno': false) no intercepta", (ESTADO.update({"aplanado_terreno": False}) or ns["interceptar_obra"]("aplana 10x10", "Steve")) is None)
ESTADO.clear()

ns["_FLUJOS_OBRA"]["aplanar"] = lambda it, u: None
res = ns["aplicar_cortocircuito"]("aplana 6x6", "Steve")
for _ in range(100):
    if not ns["_OBRA_LOCK"].locked():
        break
    _time.sleep(0.02)
r.check("aplicar_cortocircuito: 'aplana 6x6' lo resuelve la obra (no el LLM)", res and res[0]["action"] == "ninguna" and "aplanar" in res[0]["chat_message"])
ns["cargar_waypoints"] = lambda reparar=True: {}
res = ns["aplicar_cortocircuito"]("construye una casa en la base", "Steve")
r.check("aplicar_cortocircuito: 'construye una casa en la base' sigue por el flujo normal de construcción (no lo roba la obra)", bool(res) and "No encontré el waypoint" in res[0]["chat_message"])

r.terminar()
