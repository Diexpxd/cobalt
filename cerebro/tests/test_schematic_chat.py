"""H5: schematics por chat («lista mis schematics», «importa el schematic X») con un .schem REAL, y el ejecutor de obras enviando el estado de cada bloque a Java"""
import io
import json
import os
import random
import shutil
import sys
import tempfile
import time

from _cargar import Resultados, cargar_cerebro
import _frases_del_codigo as fc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_schematic as sc  # noqa: E402
import nox_voz  # noqa: E402

NODE_MODULES = os.environ.get("COBALT_NODE_MODULES", "node_modules")
r = Resultados()
tmp = tempfile.mkdtemp()
REAL = os.path.join(NODE_MODULES, "mineflayer-builder", "schematics", "smallhouse1.schem")

listar = ["lista mis schematics", "Lista schematics", "lista los schematics", "muestra mis schematics", "¿qué schematics tengo?", "que schematics hay", "Cobalt, lista los esquemas",
          "dime mis schems", "cuales son mis schematics", "lista mis schematics por favor", "LISTA MIS SCHEMATICS!", "qué esquemas hay"]
r.check("listar: reconoce las formas naturales: " + str([x for x in listar if sc.interpretar_comando(x) != ("listar", None)]), all(sc.interpretar_comando(x) == ("listar", None) for x in listar))
importar = {"importa el schematic castillo": "castillo", "Importa el schematic Castillo Medieval": "castillo medieval", "carga el esquema torre_norte": "torre_norte",
            "convierte la litematica puente": "puente", "importa el schematic llamado casa pequeña": "casa pequena", "lee el schem casa.schem": "casa.schem",
            "Cobalt, importa el schematic granja-2 por favor": "granja-2", "importa mi schematic base": "base", "importa un schematic faro.": "faro"}
malos = {k: v for k, v in importar.items() if sc.interpretar_comando(k) != ("importar", v)}
r.check("importar: reconoce las formas naturales y extrae el nombre (sin acentos ni mayúsculas): " + str(malos), not malos)
no = ["", "hola", "carga el plano casa", "construye castillo", "importa el archivo", "importa el schematic", "importa el schematic ..", "importa el schematic ../../secreto", "importa el schematic c:\\windows\\system32",
      "importa el schematic " + "x" * 100, "lista mis planos", "qué es un schematic", "explícame qué es un schematic de Create",
      "importa el schematic ...", "importa el schematic -", "importa el schematic _ _", None, 5, "x" * 300]
r.check("NO se activa con otras órdenes (carga el plano X, construye...), con rutas ni con nombres vacíos o raros: " + str([x for x in no if sc.interpretar_comando(x)]), not any(sc.interpretar_comando(x) for x in no))

carpeta = os.path.join(tmp, "sch")
os.makedirs(carpeta)
for n in ("Castillo Medieval.schem", "torre_norte.nbt", "Puente.litematic", "viejo.schematic", "notas.txt", ".oculto.schem", "castillo medieval.nbt"):
    open(os.path.join(carpeta, n), "wb").write(b"x")
os.makedirs(os.path.join(carpeta, "subcarpeta.schem"))
lst = sc.listar_schematics(carpeta)
r.check("listar: solo archivos con extensión de schematic (sin .txt, ocultos ni carpetas), en orden: " + str(lst),
        lst == [("castillo medieval", ".nbt"), ("Castillo Medieval", ".schem"), ("Puente", ".litematic"), ("torre_norte", ".nbt"), ("viejo", ".schematic")])
r.check("listar: carpeta inexistente o un archivo -> [] (no lanza)", sc.listar_schematics(os.path.join(tmp, "no_existe")) == [] and sc.listar_schematics(os.path.join(carpeta, "notas.txt")) == [])
ruta, par = sc.buscar_schematic(carpeta, "castillo medieval")
r.check("buscar: 'castillo medieval' encuentra 'Castillo Medieval.schem' (sin distinguir mayúsculas) y prefiere .schem sobre .nbt", ruta == os.path.join(carpeta, "Castillo Medieval.schem") and par == [])
r.check("buscar: con guiones bajos, guiones o la extensión escrita", sc.buscar_schematic(carpeta, "torre-norte")[0] == os.path.join(carpeta, "torre_norte.nbt")
        and sc.buscar_schematic(carpeta, "TORRE_NORTE.nbt")[0] == os.path.join(carpeta, "torre_norte.nbt") and sc.buscar_schematic(carpeta, "puente")[0] == os.path.join(carpeta, "Puente.litematic"))
ruta, par = sc.buscar_schematic(carpeta, "castillo")
r.check("buscar: sin coincidencia exacta -> sin ruta y con parecidos: " + str(par), ruta is None and par == ["castillo medieval"])
r.check("buscar: las sugerencias exigen TODAS las palabras pedidas ('torre medieval' no sugiere ni la torre ni el castillo)", sc.buscar_schematic(carpeta, "torre medieval") == (None, []))
r.check("buscar: nada parecido -> ([], sin ruta); nombre vacío -> sin ruta", sc.buscar_schematic(carpeta, "dragon") == (None, []) and sc.buscar_schematic(carpeta, "")[0] is None)
r.check("buscar: nunca devuelve una ruta fuera de la carpeta aunque el nombre lleve puntos y barras", all(sc.buscar_schematic(carpeta, x)[0] is None for x in ("../sch/puente", "..\\sch\\puente", "/etc/passwd", "C:\\Windows\\win.ini")))

r.check("materiales: los más numerosos primero, con 'y N más'", sc.texto_materiales({"minecraft:stone_bricks": 120, "minecraft:oak_planks": 40, "minecraft:glass": 12, "minecraft:torch": 5}) == "120 stone bricks, 40 oak planks, 12 glass y 1 más")
r.check("materiales: justo 3 materiales no llevan 'y N más'", sc.texto_materiales({"minecraft:a": 3, "minecraft:b": 2, "minecraft:c": 1}) == "3 a, 2 b, 1 c")
r.check("materiales: pocos o ninguno", sc.texto_materiales({"minecraft:stone": 3}) == "3 stone" and sc.texto_materiales({}) == "" and sc.texto_materiales(None) == "")
sucio = sc.texto_materiales({"minecraft:oak\n{planks}[x]": 5, "minecraft:ok": "muchos", "": 3, "minecraft:cero": 0, "minecraft:neg": -2})
r.check("materiales: el nombre viene de un archivo de terceros -> se limpia (sin saltos de línea, llaves ni corchetes) y se descartan cantidades no válidas: " + repr(sucio),
        sucio == "5 oak planks x" and not any(c in sucio for c in "{}[]\n"))

r.check("el nombre del plano ya no pierde la ñ ni los acentos: 'Casa Pequeña' -> 'casa_pequena'", sc._nombre_seguro("Casa Pequeña") == "casa_pequena" and sc._nombre_seguro("Ánimo/Ñu") == "animo_nu")

ns = cargar_cerebro()
for var, nombre in [("CONFIG_FILE", "cobalt_config.json"), ("STATUS_FILE", "nox_status.json")]:
    ns[var] = os.path.join(tmp, nombre)
ns["SCHEMATICS_DIR"] = os.path.join(tmp, "schematics")
ns["BLUEPRINTS_DIR"] = os.path.join(tmp, "blueprints")
os.makedirs(ns["SCHEMATICS_DIR"])
ns["registrar_mensaje_disco_python"] = lambda *a, **k: None


def config(**c):
    io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps(c))
    ns["_CONFIG_CACHE"]["t"] = 0.0


def chat(mensaje):
    o = ns["interceptar_schematic"](mensaje, "Steve")
    return (o[0]["chat_message"] if o else None), o


config()
t, o = chat("importa el schematic casa")
r.check("apagado por defecto: reconoce la orden pero avisa de cómo activarla y NO importa nada: " + repr(t), t in nox_voz.BANCO["schem_apagado"] and not os.path.exists(ns["BLUEPRINTS_DIR"]))
r.check("y el aviso va dirigido al jugador, solo de chat", o and o[0]["action"] == "ninguna" and o[0]["target"] == "Steve")
t, _ = chat("lista mis schematics")
r.check("apagado: 'lista mis schematics' tampoco lista", t in nox_voz.BANCO["schem_apagado"])
r.check("una orden de plano normal ('carga el plano casa') NO la intercepta el módulo de schematics", ns["interceptar_schematic"]("carga el plano casa", "Steve") is None)
o = ns["aplicar_cortocircuito"]("lista mis schematics", "Steve")
r.check("y está enganchado en el cortocircuito del chat (aplicar_cortocircuito responde)", o and o[0]["chat_message"] in nox_voz.BANCO["schem_apagado"])

if os.path.exists(REAL):
    config(schematics_import=True)
    t, _ = chat("lista mis schematics")
    r.check("carpeta vacía: lo dice y da la ruta: " + repr(t), t is not None and "No hay schematics en la carpeta" in t and ns["SCHEMATICS_DIR"] in t)
    shutil.copy(REAL, os.path.join(ns["SCHEMATICS_DIR"], "Casa Pequeña.schem"))
    shutil.copy(os.path.join(NODE_MODULES, "mineflayer-pathfinder", "test", "schematics", "parkour1.schem"), os.path.join(ns["SCHEMATICS_DIR"], "parkour1.schem"))
    t, _ = chat("lista mis schematics")
    r.check("lista los 2 archivos: " + repr(t), t and "(2)" in t and "Casa Pequeña" in t and "parkour1" in t)
    t, _ = chat("importa el schematic casa")
    r.check("un nombre a medias no importa: dice que no lo encuentra y sugiere el parecido: " + repr(t), t and "No encuentro" in t and "'Casa Pequeña'" in t and not os.path.exists(ns["BLUEPRINTS_DIR"]))
    t, _ = chat("importa el schematic dragon")
    r.check("un nombre sin parecidos: solo dice que no lo encuentra", t and "No encuentro" in t and "Quizá" not in t)
    t, o = chat("importa el schematic casa pequeña")
    planos = os.listdir(ns["BLUEPRINTS_DIR"]) if os.path.exists(ns["BLUEPRINTS_DIR"]) else []
    r.check("importa el .schem real: plano guardado con nombre limpio, y el resumen dice nombre, medidas, bloques, materiales y cómo construirlo: " + repr(t) + str(planos),
            planos == ["casa_pequena.json"] and t.startswith("Importé 'casa_pequena' (") and "bloques). Necesito: " in t and "«construye casa_pequena»" in t and len(t) <= nox_voz.MAX_CHAT)
    plano = json.load(open(os.path.join(ns["BLUEPRINTS_DIR"], "casa_pequena.json"), encoding="utf-8"))
    con_estado = sum(1 for c in plano["layers"] for b in c["blocks"] if b.get("state"))
    r.check(f"el plano guardado conserva los estados ({con_estado} bloques con orientación) y sin schematics_estados el resumen avisa de que no se aplican: " + repr(t[-110:]),
            con_estado > 0 and "schematics_estados" in t)
    t2, _ = chat("importa el schematic casa pequeña")
    r.check("importar dos veces no pisa el primero: queda casa_pequena_2", sorted(os.listdir(ns["BLUEPRINTS_DIR"])) == ["casa_pequena.json", "casa_pequena_2.json"] and "'casa_pequena_2'" in t2)
    config(schematics_import=True, schematics_estados=True)
    os.remove(os.path.join(ns["BLUEPRINTS_DIR"], "casa_pequena_2.json"))
    t3, _ = chat("importa el schematic casa pequeña")
    r.check("con schematics_estados encendido ya no dice que las orientaciones no se aplican: " + repr(t3[-90:]), "schematics_estados" not in t3 and t3.startswith("Importé"))
    # archivo corrupto y demasiado grande
    open(os.path.join(ns["SCHEMATICS_DIR"], "roto.schem"), "wb").write(bytes(random.Random(3).randrange(256) for _ in range(300)))
    antes = sorted(os.listdir(ns["BLUEPRINTS_DIR"]))
    t, _ = chat("importa el schematic roto")
    r.check("archivo corrupto: mensaje de error del banco (no lanza) y no deja plano: " + repr(t), t and t.startswith("No pude importar 'roto': ") and sorted(os.listdir(ns["BLUEPRINTS_DIR"])) == antes)
    limite = sc.MAX_ARCHIVO_BYTES
    sc.MAX_ARCHIVO_BYTES = 100
    t, _ = chat("importa el schematic casa pequeña")
    sc.MAX_ARCHIVO_BYTES = limite
    r.check("archivo demasiado grande: lo rechaza sin leerlo: " + repr(t), t and "demasiado grande" in t)
    original_importar = sc.importar_schematic
    sc.importar_schematic = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    t, _ = chat("importa el schematic casa pequeña")
    r.check("un fallo inesperado del importador (no ErrorSchematic) no tumba el chat: dice que no pudo leerlo: " + repr(t), t and t.startswith("No pude importar 'casa pequena': ") and "no pude leer el archivo" in t)
    config(schematics_import=True)
    sc.importar_schematic = lambda *a, **k: {"nombre": "casa_pequena", "dimensiones": (60, 40, 50), "bloques": 19000, "avisos": [], "con_estados": 900, "ruta": "x", "formato": "sponge v2",
                                             "materiales": {f"minecraft:m{i}_material_largo_largo_largo_largo": 1000 - i for i in range(6)}}
    t, _ = chat("importa el schematic casa pequeña")
    r.check("con muchos materiales de nombre largo el resumen cabe en el chat, acorta la lista y NO pierde el aviso ni la instrucción de construir: " + repr(t) + str(len(t)),
            t and len(t) <= nox_voz.MAX_CHAT and "«construye casa_pequena»" in t and "schematics_estados" in t and t.startswith("Importé 'casa_pequena' (60x40x50, 19000 bloques)"))
    sc.importar_schematic = lambda *a, **k: {"nombre": "x", "dimensiones": (2, 2, 2), "bloques": 8, "avisos": ["bloques peligrosos omitidos: tnt×3\n{evil}"], "con_estados": 0, "ruta": "x", "formato": "nbt",
                                             "materiales": {"minecraft:stone": 8}}
    t, _ = chat("importa el schematic casa pequeña")
    r.check("los avisos del importador (texto de un archivo de terceros) se limpian antes de llegar al chat: " + repr(t), t and "tnt×3" in t and not any(c in t for c in "{}\n"))
    sc.importar_schematic = original_importar
    enviados, llamadas = [], []
    ns["escribir_comando"] = lambda ordenes: enviados.extend(x.get("chat_message") for x in ordenes)
    ns["consultar_ollama"] = lambda *a, **k: llamadas.append(a) or "[]"
    ns["consultar_gemini_o_fallback"] = lambda *a, **k: llamadas.append(a) or "[]"
    ns["procesar_mensaje_async"]("Steve", "lista mis schematics")
    r.check("procesar_mensaje_async('lista mis schematics'): responde por el chat y no llama a ningún modelo: " + repr(enviados), len(enviados) == 1 and "Schematics disponibles" in enviados[0] and not llamadas)
else:
    print("SKIP  (no está smallhouse1.schem en node_modules)")

ns["escribir_comando"] = lambda ordenes, **k: True
ns["BLUEPRINTS_DIR"] = os.path.join(tmp, "planos_obra")
os.makedirs(ns["BLUEPRINTS_DIR"])
io.open(os.path.join(ns["BLUEPRINTS_DIR"], "t.json"), "w", encoding="utf-8").write(json.dumps({"blueprint_name": "t", "dimensions": {"width": 3, "height": 1, "length": 1}, "layers": [
    {"y": 0, "blocks": [{"x": 0, "z": 0, "block": "minecraft:oak_stairs", "state": "facing=east,half=bottom"}, {"x": 1, "z": 0, "block": "minecraft:stone"},
                        {"x": 2, "z": 0, "block": "minecraft:wall_torch", "state": "facing=north"}]}]}))
enviados_obra, restock = [], []


def colocar_falso(comando):
    enviados_obra.append(dict(comando))
    if comando["block"] == "minecraft:wall_torch" and not any(x.get("_reintento") for x in enviados_obra):
        enviados_obra[-1]["_reintento"] = True
        return False, "no_material"
    return True, ""


ns["_colocar_y_esperar"] = colocar_falso
ns["_reabastecer"] = lambda material, cantidad=16: restock.append(material) or True
ns["_despejar_terreno"] = lambda *a, **k: None
ns["es_zona_segura"] = lambda *a, **k: True
for con_estados in (None, False, True):  # None = la clave no existe en la configuración: debe quedar APAGADO
    enviados_obra.clear()
    restock.clear()
    config(schematics_estados=con_estados) if con_estados is not None else config()
    ns["iniciar_construccion"]("t", 10, 64, 20, "Steve", registrar=False)
    por_bloque = {c["block"]: c for c in enviados_obra}
    if con_estados:
        r.check("schematics_estados=true: place_block lleva el 'state' de los bloques que lo tienen y no lo inventa para los demás",
                por_bloque["minecraft:oak_stairs"].get("state") == "facing=east,half=bottom" and por_bloque["minecraft:wall_torch"].get("state") == "facing=north" and "state" not in por_bloque["minecraft:stone"])
        r.check("schematics_estados=true: sin material se pide el ÍTEM (wall_torch -> torch), no el bloque: " + str(restock), restock == ["minecraft:torch"])
    else:
        r.check(f"schematics_estados={'ausente' if con_estados is None else 'false'} (defecto): place_block sale EXACTAMENTE como antes, sin 'state'", all("state" not in c for c in enviados_obra) and len(enviados_obra) >= 3)
        r.check("schematics_estados apagado: sin material se pide el bloque tal cual (camino de siempre): " + str(restock), restock == ["minecraft:wall_torch"])
    r.check("las posiciones no cambian con el estado (origen 10,64,20)", por_bloque["minecraft:stone"]["x"] == 11 and por_bloque["minecraft:stone"]["y"] == 64 and por_bloque["minecraft:stone"]["z"] == 20)

frases_h5 = [x for k in ("schem_apagado", "schem_lista", "schem_vacio", "schem_importado", "schem_no_encontrado", "schem_error") for x in nox_voz.BANCO[k]]
r.check("las frases de schematics pasan el linter de voz (sin servilismo ni exageración)", all(not nox_voz.linter_voz(x) for x in frases_h5))
r.check("el escáner de frases ve las de cerebro.py sin cadenas sueltas servil/exageradas", all(not nox_voz.linter_voz(s) for _, s in fc.frases("cerebro.py")))

r.terminar()
