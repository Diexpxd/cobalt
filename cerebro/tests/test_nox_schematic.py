"""Pruebas del Bloque R (lector de schematics): formatos sintéticos (codificador NBT propio), ARCHIVOS REALES (1010 estructuras vanilla del juego, .schem y"""
import gzip
import json
import os
import random
import struct
import sys
import tempfile
import time
import zipfile

from _cargar import Resultados, cargar_cerebro

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_schematic as ns_  # noqa: E402

NODE_MODULES = os.environ.get("COBALT_NODE_MODULES", "node_modules")
r = Resultados()
tmp = tempfile.mkdtemp()


def cad(s):
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def carga(tipo, v):
    if tipo == 1:
        return struct.pack(">b", v)
    if tipo == 2:
        return struct.pack(">h", v)
    if tipo == 3:
        return struct.pack(">i", v)
    if tipo == 4:
        return struct.pack(">q", v)
    if tipo == 5:
        return struct.pack(">f", v)
    if tipo == 6:
        return struct.pack(">d", v)
    if tipo == 7:
        return struct.pack(">i", len(v)) + bytes(v)
    if tipo == 8:
        return cad(v)
    if tipo == 9:
        t, items = v
        return bytes([t]) + struct.pack(">i", len(items)) + b"".join(carga(t, x) for x in items)
    if tipo == 10:
        return b"".join(bytes([t]) + cad(n) + carga(t, x) for n, (t, x) in v.items()) + b"\x00"
    if tipo == 11:
        return struct.pack(">i", len(v)) + b"".join(struct.pack(">i", x) for x in v)
    if tipo == 12:
        return struct.pack(">i", len(v)) + b"".join(struct.pack(">q", x) for x in v)
    raise ValueError(tipo)


def nbt(nombre_raiz, dic, gz=True):
    crudo = b"\x0a" + cad(nombre_raiz) + carga(10, dic)
    return gzip.compress(crudo) if gz else crudo


def varint(n):
    salida = bytearray()
    while n > 127:
        salida.append((n & 0x7F) | 0x80)
        n >>= 7
    salida.append(n)
    return bytes(salida)


def esperar_error(nombre, f):
    try:
        f()
        r.check(nombre, False)
    except ns_.ErrorSchematic:
        r.check(nombre, True)
    except BaseException as e:  # noqa: BLE001
        r.check(f"{nombre} (salió {type(e).__name__}: {e})", False)


tipos = {"b": (1, -5), "s": (2, -300), "i": (3, 70000), "l": (4, -(1 << 40)), "f": (5, 1.5), "d": (6, -2.25), "ba": (7, b"\x01\x02\xff"), "str": (8, "hola ñandú"),
         "lista_i": (9, (3, [1, 2, 3])), "lista_c": (9, (10, [{"a": (3, 1)}, {"a": (3, 2)}])), "ia": (11, [1, -1, 65536]), "la": (12, [1, -(1 << 62)]),
         "anidado": (10, {"x": (10, {"y": (8, "z")})})}
_, leido = ns_.leer_nbt(nbt("raiz", tipos))
r.check("lee todos los tipos de NBT (byte..long array, listas, compuestos anidados)",
        leido["b"] == -5 and leido["s"] == -300 and leido["i"] == 70000 and leido["l"] == -(1 << 40) and abs(leido["f"] - 1.5) < 1e-6 and leido["d"] == -2.25
        and leido["ba"] == b"\x01\x02\xff" and leido["str"] == "hola ñandú" and leido["lista_i"] == [1, 2, 3] and leido["lista_c"] == [{"a": 1}, {"a": 2}]
        and leido["ia"] == [1, -1, 65536] and leido["la"] == [1, -(1 << 62)] and leido["anidado"] == {"x": {"y": "z"}})
nombre_raiz, _ = ns_.leer_nbt(nbt("Schematic", {}, gz=False))
r.check("acepta NBT sin comprimir y devuelve el nombre de la raíz", nombre_raiz == "Schematic")
esperar_error("NBT vacío -> ErrorSchematic", lambda: ns_.leer_nbt(b""))
esperar_error("bytes al azar -> ErrorSchematic", lambda: ns_.leer_nbt(bytes(random.Random(1).randrange(256) for _ in range(500))))
esperar_error("raíz que no es compuesto -> ErrorSchematic", lambda: ns_.leer_nbt(b"\x09\x00\x00"))
buena = nbt("r", {"x": (8, "a" * 100)})
esperar_error("archivo truncado -> ErrorSchematic", lambda: ns_.leer_nbt(gzip.compress(gzip.decompress(buena)[:-20])))
esperar_error("gzip dañado -> ErrorSchematic", lambda: ns_.leer_nbt(buena[:-6] + b"\x00" * 6))
profundo = b"\x0a\x00\x00" + (b"\x0a\x00\x01a" * 200) + b"\x00" * 201
esperar_error("NBT anidado 200 niveles (bomba de profundidad) -> ErrorSchematic", lambda: ns_.leer_nbt(profundo))
esperar_error("lista con 2 mil millones de elementos -> ErrorSchematic (sin reservar memoria)", lambda: ns_.leer_nbt(b"\x0a\x00\x00\x09\x00\x01a\x03\x7f\xff\xff\xff\x00"))
esperar_error("byte array con longitud negativa -> ErrorSchematic", lambda: ns_.leer_nbt(b"\x0a\x00\x00\x07\x00\x01a\xff\xff\xff\xff\x00"))
esperar_error("tipo de tag desconocido -> ErrorSchematic", lambda: ns_.leer_nbt(b"\x0a\x00\x00\x63\x00\x01a\x00"))
limite_original = ns_.LIMITE_DESCOMPRIMIDO
ns_.LIMITE_DESCOMPRIMIDO = 10_000
esperar_error("bomba de compresión (50 KB de ceros descomprimen a más del límite) -> ErrorSchematic", lambda: ns_.leer_nbt(gzip.compress(b"\x0a\x00\x00" + b"\x00" * 60_000)))
ns_.LIMITE_DESCOMPRIMIDO = limite_original

W, H, L = 3, 2, 2
pal2 = {"minecraft:air": (3, 0), "minecraft:stone": (3, 1), "minecraft:oak_stairs[half=bottom,facing=east]": (3, 2)}
celdas = [0] * (W * H * L)


def idx(x, y, z):
    return x + z * W + y * W * L


celdas[idx(0, 0, 0)] = 1
celdas[idx(2, 0, 1)] = 2
celdas[idx(1, 1, 0)] = 1
celdas[idx(2, 1, 1)] = 1
v2 = nbt("Schematic", {"Version": (3, 2), "DataVersion": (3, 3465), "Width": (2, W), "Height": (2, H), "Length": (2, L), "PaletteMax": (3, 3),
                       "Palette": (10, pal2), "BlockData": (7, b"".join(varint(c) for c in celdas)),
                       "BlockEntities": (9, (10, [{"Id": (8, "minecraft:chest")}]))})
s = ns_.leer_schematic(v2, "casita")
r.check("Sponge v2: dimensiones, versión y formato", (s.ancho, s.alto, s.largo) == (3, 2, 2) and s.formato == "sponge v2" and s.datos_version == 3465)
r.check("Sponge v2: 4 bloques en las posiciones que dice x + z*Ancho + y*Ancho*Largo (el aire no cuenta)",
        s.bloques == {(0, 0, 0): "minecraft:stone", (2, 0, 1): "minecraft:oak_stairs[facing=east,half=bottom]", (1, 1, 0): "minecraft:stone", (2, 1, 1): "minecraft:stone"})
r.check("Sponge v2: las propiedades se normalizan en orden alfabético y cuenta 1 bloque con datos", s.entidades_bloque == 1 and s.nombre == "casita")

# varints de 2 bytes (paleta con más de 127 entradas)
palgrande = {"minecraft:air": (3, 0)}
for n in range(1, 200):
    palgrande[f"minecraft:test_block_{n}"] = (3, n)
datos_v = b"".join(varint(n) for n in (0, 1, 127, 128, 199, 130))
v2b = nbt("Schematic", {"Version": (3, 2), "DataVersion": (3, 3465), "Width": (2, 6), "Height": (2, 1), "Length": (2, 1), "Palette": (10, palgrande), "BlockData": (7, datos_v)})
sb = ns_.leer_schematic(v2b)
r.check("varints de 1 y 2 bytes (índices 127, 128 y 199)", [sb.bloques.get((i, 0, 0)) for i in range(6)] == [None, "minecraft:test_block_1", "minecraft:test_block_127", "minecraft:test_block_128",
                                                                                                        "minecraft:test_block_199", "minecraft:test_block_130"])

v3 = nbt("", {"Schematic": (10, {"Version": (3, 3), "DataVersion": (3, 3465), "Width": (2, W), "Height": (2, H), "Length": (2, L),
                                 "Blocks": (10, {"Palette": (10, {k: v for k, v in pal2.items()}), "Data": (7, b"".join(varint(c) for c in celdas))})})})
s3 = ns_.leer_schematic(v3)
r.check("Sponge v3: mismo resultado que v2 con el otro contenedor", s3.formato == "sponge v3" and s3.bloques == s.bloques)
esperar_error("Sponge con menos bloques de los declarados -> ErrorSchematic", lambda: ns_.leer_schematic(nbt("Schematic", {"Version": (3, 2), "Width": (2, 9), "Height": (2, 9), "Length": (2, 9), "Palette": (10, pal2), "BlockData": (7, b"\x00\x01")})))
esperar_error("Sponge con índice de paleta inexistente -> ErrorSchematic", lambda: ns_.leer_schematic(nbt("Schematic", {"Version": (3, 2), "Width": (2, 2), "Height": (2, 1), "Length": (2, 1), "Palette": (10, pal2), "BlockData": (7, b"\x00\x09")})))
esperar_error("Sponge con varint truncado -> ErrorSchematic", lambda: ns_.leer_schematic(nbt("Schematic", {"Version": (3, 2), "Width": (2, 2), "Height": (2, 1), "Length": (2, 1), "Palette": (10, pal2), "BlockData": (7, b"\x00\x80")})))
esperar_error("Sponge con dimensiones negativas -> ErrorSchematic", lambda: ns_.leer_schematic(nbt("Schematic", {"Version": (3, 2), "Width": (2, -1), "Height": (2, 1), "Length": (2, 1), "Palette": (10, pal2), "BlockData": (7, b"\x00")})))
esperar_error("Sponge de 65535³ (volumen absurdo) -> ErrorSchematic sin reservar memoria", lambda: ns_.leer_schematic(nbt("Schematic", {"Version": (3, 2), "Width": (3, 65535), "Height": (3, 65535), "Length": (3, 65535), "Palette": (10, pal2), "BlockData": (7, b"\x00")})))
sancho = ns_.leer_schematic(nbt("Schematic", {"Version": (3, 2), "Width": (2, -25536), "Height": (2, 1), "Length": (2, 1), "Palette": (10, {"minecraft:air": (3, 0)}), "BlockData": (7, b"\x00" * 40000)}))
r.check("Width guardado como 'unsigned short' (40000 aparece como -25536 en un lector con signo) se interpreta bien", sancho.ancho == 40000)

vanilla = nbt("", {"DataVersion": (3, 3465), "size": (9, (3, [3, 2, 3])),
                   "palette": (9, (10, [{"Name": (8, "minecraft:stone")}, {"Name": (8, "minecraft:oak_stairs"), "Properties": (10, {"facing": (8, "east"), "half": (8, "bottom")})},
                                        {"Name": (8, "minecraft:jigsaw")}, {"Name": (8, "minecraft:air")}, {"Name": (8, "minecraft:chest")}])),
                   "blocks": (9, (10, [{"pos": (9, (3, [0, 0, 0])), "state": (3, 0)}, {"pos": (9, (3, [2, 0, 2])), "state": (3, 1)},
                                       {"pos": (9, (3, [1, 1, 1])), "state": (3, 2), "nbt": (10, {"final_state": (8, "minecraft:oak_planks"), "name": (8, "minecraft:empty")})},
                                       {"pos": (9, (3, [1, 0, 1])), "state": (3, 3)}, {"pos": (9, (3, [0, 1, 0])), "state": (3, 4), "nbt": (10, {"Items": (9, (10, []))})}])),
                   "entities": (9, (10, []))})
sv = ns_.leer_schematic(vanilla)
r.check("estructura vanilla: tamaño, bloques y aire omitido", (sv.ancho, sv.alto, sv.largo) == (3, 2, 3) and sv.formato == "estructura vanilla" and len(sv.bloques) == 4)
r.check("estructura vanilla: el JIGSAW se sustituye por su final_state (oak_planks), no se coloca como jigsaw", sv.bloques[(1, 1, 1)] == "minecraft:oak_planks"
        and not any("jigsaw" in b for b in sv.bloques.values()))
r.check("estructura vanilla: propiedades normalizadas y bloque con datos contado", sv.bloques[(2, 0, 2)] == "minecraft:oak_stairs[facing=east,half=bottom]" and sv.entidades_bloque == 1)
vanilla_pals = nbt("", {"size": (9, (3, [1, 1, 1])), "palettes": (9, (9, [(10, [{"Name": (8, "minecraft:dirt")}])])), "blocks": (9, (10, [{"pos": (9, (3, [0, 0, 0])), "state": (3, 0)}]))})
esperar_error("(las 'palettes' de varias variantes: se lee la primera, sin romper)", lambda: (_ for _ in ()).throw(ns_.ErrorSchematic()) if False else None) if False else None
r.check("estructura con 'palettes' (variantes de naufragios): usa la primera", ns_.leer_schematic(vanilla_pals).bloques == {(0, 0, 0): "minecraft:dirt"})
esperar_error("estructura con un bloque fuera del tamaño -> ErrorSchematic", lambda: ns_.leer_schematic(nbt("", {"size": (9, (3, [1, 1, 1])), "palette": (9, (10, [{"Name": (8, "minecraft:dirt")}])), "blocks": (9, (10, [{"pos": (9, (3, [5, 0, 0])), "state": (3, 0)}]))})))
esperar_error("estructura con estado fuera de la paleta -> ErrorSchematic", lambda: ns_.leer_schematic(nbt("", {"size": (9, (3, [1, 1, 1])), "palette": (9, (10, [{"Name": (8, "minecraft:dirt")}])), "blocks": (9, (10, [{"pos": (9, (3, [0, 0, 0])), "state": (3, 7)}]))})))

def empaquetar(indices, bits):
    total = len(indices) * bits
    longs = [0] * ((total + 63) // 64)
    for i, v in enumerate(indices):
        ini = i * bits
        a, off = ini >> 6, ini & 63
        longs[a] |= (v << off) & 0xFFFFFFFFFFFFFFFF
        if off + bits > 64:
            longs[a + 1] |= v >> (64 - off)
    return [x - (1 << 64) if x >= (1 << 63) else x for x in longs]


def region(size, pos, palette, indices):
    bits = max(2, (len(palette) - 1).bit_length())
    return {"Size": (10, {"x": (3, size[0]), "y": (3, size[1]), "z": (3, size[2])}), "Position": (10, {"x": (3, pos[0]), "y": (3, pos[1]), "z": (3, pos[2])}),
            "BlockStatePalette": (9, (10, [{"Name": (8, n)} if "[" not in n else {"Name": (8, n.split("[")[0]), "Properties": (10, {k: (8, v) for k, v in (p.split("=") for p in n.split("[")[1].rstrip("]").split(","))})} for n in palette])),
            "BlockStates": (12, empaquetar(indices, bits))}


nombres = ["minecraft:air"] + [f"minecraft:test_{n}" for n in range(1, 17)]  # 17 estados -> 5 bits (cruzan los límites de 64 bits)
rnd = random.Random(7)
ax, ay, az = 5, 4, 3
indices = [rnd.randrange(len(nombres)) for _ in range(ax * ay * az)]
lit = nbt("", {"Version": (3, 6), "MinecraftDataVersion": (3, 3465), "Regions": (10, {"A": (10, region((ax, ay, az), (0, 0, 0), nombres, indices))})})
sl = ns_.leer_schematic(lit)
esperado = {}
for i, v in enumerate(indices):
    if v:
        esperado[(i % ax, i // (ax * az), (i // ax) % az)] = nombres[v]
r.check("Litematica (17 estados = 5 bits que cruzan límites de 64 bits): TODOS los bloques en su sitio, índice (y*Z+z)*X+x", sl.bloques == esperado and sl.formato == "litematica")
lit2 = nbt("", {"Version": (3, 6), "Regions": (10, {"A": (10, region((2, 1, 1), (0, 0, 0), ["minecraft:air", "minecraft:stone", "minecraft:dirt"], [1, 2])),
                                                     "B": (10, region((2, 1, 1), (5, 0, 0), ["minecraft:air", "minecraft:gold_block"], [1, 1]))})})
s2 = ns_.leer_schematic(lit2)
r.check("Litematica con 2 regiones separadas: se combinan y el tamaño total las abarca", s2.ancho == 7 and len(s2.bloques) == 4 and s2.bloques[(0, 0, 0)] == "minecraft:stone" and s2.bloques[(6, 0, 0)] == "minecraft:gold_block")
lit3 = nbt("", {"Version": (3, 6), "Regions": (10, {"A": (10, region((-2, 1, 1), (4, 0, 0), ["minecraft:air", "minecraft:stone"], [1, 1]))})})
lit_neg = nbt("", {"Version": (3, 6), "Regions": (10, {"A": (10, region((-2, 1, 1), (4, 0, 0), ["minecraft:air", "minecraft:stone", "minecraft:dirt"], [1, 2])),
                                                        "B": (10, region((2, 1, 1), (5, 0, 0), ["minecraft:air", "minecraft:gold_block"], [1, 1]))})})
sn = ns_.leer_schematic(lit_neg)
r.check("Litematica con región de tamaño NEGATIVO junto a otra: A ocupa x=3..4 y B x=5..6 (4 bloques contiguos, sin solaparse)",
        sn.ancho == 4 and sorted(sn.bloques) == [(0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)] and sn.bloques[(0, 0, 0)] == "minecraft:stone" and sn.bloques[(1, 0, 0)] == "minecraft:dirt"
        and sn.bloques[(3, 0, 0)] == "minecraft:gold_block")
esperar_error("Litematica con región 'vacía' (tamaño 0) -> ErrorSchematic", lambda: ns_.leer_schematic(nbt("", {"Regions": (10, {"A": (10, region((0, 1, 1), (0, 0, 0), ["minecraft:air", "minecraft:stone"], [1]))})})))
r.check("Litematica con tamaño NEGATIVO: la región se extiende hacia atrás desde su posición", len(ns_.leer_schematic(lit3).bloques) == 2)
recortado = region((ax, ay, az), (0, 0, 0), nombres, indices)
recortado["BlockStates"] = (12, recortado["BlockStates"][1][:2])
esperar_error("Litematica con menos datos de los declarados -> ErrorSchematic", lambda: ns_.leer_schematic(nbt("", {"Regions": (10, {"A": (10, recortado)})})))

legacy = nbt("Schematic", {"Width": (2, 2), "Height": (2, 1), "Length": (2, 1), "Materials": (8, "Alpha"), "Blocks": (7, b"\x01\x02"), "Data": (7, b"\x00\x00")})
try:
    ns_.leer_schematic(legacy)
    r.check("MCEdit antiguo -> error claro con la solución", False)
except ns_.ErrorSchematic as e:
    r.check("MCEdit antiguo (.schematic) -> error claro que dice cómo convertirlo: " + str(e)[:70], "MCEdit" in str(e) and "WorldEdit" in str(e))
esperar_error("un NBT cualquiera que no es schematic -> ErrorSchematic ('no reconocido')", lambda: ns_.leer_schematic(nbt("x", {"hola": (8, "mundo")})))

sch = ns_.Schem("test", 20, 20, 20, {(5, 3, 7): "minecraft:stone", (6, 3, 7): "minecraft:oak_stairs[facing=east,half=bottom]", (5, 4, 7): "minecraft:oak_log[axis=y]",
                                      (9, 3, 9): "minecraft:water[level=0]", (8, 3, 8): "minecraft:tnt", (7, 3, 7): "minecraft:lava[level=0]", (8, 3, 7): "minecraft:nether_portal[axis=x]",
                                      (7, 4, 7): "minecraft:command_block[facing=up]", (7, 5, 7): "minecraft:spawner"}, entidades_bloque=2, nombre="Mi Casa Bonita!")
plano, avisos = ns_.a_plano_cobalt(sch)
todos = [(c["y"], b) for c in plano["layers"] for b in c["blocks"]]
r.check("se recortan los márgenes vacíos: el plano empieza en (0,0,0) y mide 2x2x1", plano["dimensions"] == {"width": 2, "height": 2, "length": 1} and min(b["x"] for _, b in todos) == 0 and min(y for y, _ in todos) == 0)
r.check("solo quedan los 3 bloques seguros; se OMITEN agua, TNT, lava, portal, bloque de comandos y spawner", len(todos) == 3 and not any(p in b["block"] for _, b in todos for p in ("water", "tnt", "lava", "portal", "command", "spawner")))
r.check("los estados van en un campo 'state' aparte (facing=east,half=bottom) y los bloques sin estado no lo llevan",
        {b["block"]: b.get("state") for _, b in todos} == {"minecraft:stone": None, "minecraft:oak_stairs": "facing=east,half=bottom", "minecraft:oak_log": "axis=y"})
r.check("avisa de lo omitido y de los bloques con datos", any("omitidos" in a and "tnt" in a and "lava" in a for a in avisos) and any("2 bloques con datos" in a for a in avisos))
r.check("nombre seguro (solo a-z, 0-9 y _)", plano["blueprint_name"] == "mi_casa_bonita" and ns_._nombre_seguro("../../etc/passwd") == "etc_passwd" and ns_._nombre_seguro("!!!") == "schematic")
r.check("capas ordenadas de abajo arriba y bloques ordenados", [c["y"] for c in plano["layers"]] == sorted(c["y"] for c in plano["layers"]))
grande = ns_.Schem("t", 100, 10, 10, {(x, 0, 0): "minecraft:stone" for x in range(100)})
esperar_error("un schematic que se pasa de largo (100 > 64 por lado) se rechaza con el motivo", lambda: ns_.a_plano_cobalt(grande))
r.check("...pero cabe si se sube el límite", ns_.a_plano_cobalt(grande, max_lado=128)[0]["dimensions"]["width"] == 100)
esperar_error("un schematic con demasiados bloques se rechaza", lambda: ns_.a_plano_cobalt(ns_.Schem("t", 10, 10, 10, {(x, y, z): "minecraft:stone" for x in range(10) for y in range(10) for z in range(10)}), max_bloques=500))
esperar_error("un schematic solo de aire/peligros no tiene nada colocable", lambda: ns_.a_plano_cobalt(ns_.Schem("t", 2, 2, 2, {(0, 0, 0): "minecraft:tnt"})))

# materiales
mat = ns_.materiales_necesarios(["minecraft:stone", "minecraft:stone", "minecraft:oak_slab[type=double]", "minecraft:oak_slab[type=bottom]", "minecraft:oak_door[half=lower,facing=north]",
                                 "minecraft:oak_door[half=upper,facing=north]", "minecraft:red_bed[part=foot]", "minecraft:red_bed[part=head]", "minecraft:wall_torch[facing=east]",
                                 "minecraft:oak_wall_sign[facing=north]", "minecraft:wheat[age=7]", "minecraft:redstone_wire[power=0]", "minecraft:white_wall_banner"])
r.check("materiales: losa doble = 2 losas; puerta y cama cuentan UNA vez (la mitad de arriba/cabecera no)", mat["minecraft:oak_slab"] == 3 and mat["minecraft:oak_door"] == 1 and mat["minecraft:red_bed"] == 1 and mat["minecraft:stone"] == 2)
r.check("materiales: antorcha de pared -> antorcha, cartel de pared -> cartel, trigo -> semillas, cable -> redstone, estandarte de pared -> estandarte",
        mat["minecraft:torch"] == 1 and mat["minecraft:oak_sign"] == 1 and mat["minecraft:wheat_seeds"] == 1 and mat["minecraft:redstone"] == 1 and mat["minecraft:white_banner"] == 1)

# la política de bloques prohibidos no se desincroniza de la de cerebro.py
cer = cargar_cerebro()
r.check("los bloques prohibidos del lector son EXACTAMENTE los de validar_blueprint de cerebro.py (si uno cambia, el otro también)",
        ns_.BLOQUES_PROHIBIDOS == cer["_BLOQUES_PROHIBIDOS"] and ns_.FRAGMENTOS_PROHIBIDOS == cer["_FRAGMENTOS_PROHIBIDOS"])

# importar: guarda sin pisar, atómico, JSON válido
carpeta = os.path.join(tmp, "blueprints")
archivo = os.path.join(tmp, "Casa Vieja.schem")
open(archivo, "wb").write(v2)
res1 = ns_.importar_schematic(archivo, carpeta)
res2 = ns_.importar_schematic(archivo, carpeta)
r.check("importar guarda blueprints/casa_vieja.json y un segundo import NO lo pisa (casa_vieja_2)", res1["nombre"] == "casa_vieja" and res2["nombre"] == "casa_vieja_2" and len(os.listdir(carpeta)) == 2)
guardado = json.load(open(res1["ruta"], encoding="utf-8"))
r.check("el archivo guardado es un plano de Cobalt válido (layers con x, z, block) más 'state' donde hace falta", set(guardado) >= {"blueprint_name", "layers", "dimensions"} and
        any("state" in b for c in guardado["layers"] for b in c["blocks"]) and all({"x", "z", "block"} <= set(b) for c in guardado["layers"] for b in c["blocks"]))
r.check("el resumen trae formato, dimensiones, nº de bloques y materiales", res1["formato"] == "sponge v2" and res1["bloques"] == 4 and res1["materiales"]["minecraft:stone"] == 3 and res1["avisos"])
esperar_error("importar un archivo inexistente -> ErrorSchematic", lambda: ns_.importar_schematic(os.path.join(tmp, "no_existe.schem"), carpeta))
open(os.path.join(tmp, "basura.schem"), "wb").write(b"esto no es un schematic")
esperar_error("importar un archivo que no es schematic -> ErrorSchematic", lambda: ns_.importar_schematic(os.path.join(tmp, "basura.schem"), carpeta))
r.check("una importación fallida no deja archivos a medias", len(os.listdir(carpeta)) == 2)

def real(ruta):
    return ruta if os.path.exists(ruta) else None


casa_real = real(os.path.join(NODE_MODULES, "mineflayer-builder", "schematics", "smallhouse1.schem"))
if casa_real:
    s = ns_.leer_archivo(casa_real)
    datos_crudos = ns_.leer_nbt(open(casa_real, "rb").read())[1]
    r.check(f"REAL smallhouse1.schem (Sponge v2 de WorldEdit): {s} coincide con su cabecera", (s.ancho, s.alto, s.largo) == (datos_crudos["Width"], datos_crudos["Height"], datos_crudos["Length"]) and len(s.bloques) > 20)
    r.check("REAL smallhouse1.schem: todas las posiciones caen dentro del tamaño y hay bloques de varios tipos", all(0 <= x < s.ancho and 0 <= y < s.alto and 0 <= z < s.largo for (x, y, z) in s.bloques) and len({e.split("[")[0] for e in s.bloques.values()}) >= 3)
    plano, av = ns_.a_plano_cobalt(s)
    r.check(f"REAL smallhouse1.schem: se convierte a plano de Cobalt ({plano['dimensions']}, avisos: {av})", sum(len(c['blocks']) for c in plano['layers']) == len(s.bloques) - sum(1 for e in s.bloques.values() if ns_.es_prohibido(e.split('[')[0])))
    res = ns_.importar_schematic(casa_real, os.path.join(tmp, "reales"))
    cuerpo_guardado = [b["block"] + ("[" + b["state"] + "]" if "state" in b else "") for c in json.load(open(res["ruta"], encoding="utf-8"))["layers"] for b in c["blocks"]]
    altas = sum(1 for t in cuerpo_guardado if "half=upper" in t or "part=head" in t)
    dobles = sum(1 for t in cuerpo_guardado if "type=double" in t and "half=upper" not in t)
    r.check(f"REAL smallhouse1.schem: importado como {res['nombre']} ({res['dimensiones']}, {res['bloques']} bloques, {len(res['materiales'])} materiales); "
            f"materiales = bloques - {altas} mitades altas + {dobles} losas dobles", res["bloques"] > 20 and sum(res["materiales"].values()) == res["bloques"] - altas + dobles)
else:
    print("SKIP  (no está smallhouse1.schem en node_modules)")
parkour = real(os.path.join(NODE_MODULES, "mineflayer-pathfinder", "test", "schematics", "parkour1.schem"))
if parkour:
    sp = ns_.leer_archivo(parkour)
    r.check(f"REAL parkour1.schem: {sp}", len(sp.bloques) > 0 and all(0 <= x < sp.ancho and 0 <= y < sp.alto and 0 <= z < sp.largo for (x, y, z) in sp.bloques))
viejo = real(os.path.join(NODE_MODULES, "prismarine-schematic", "test", "schematics", "viking-house1.schematic"))
if viejo:
    esperar_error("REAL viking-house1.schematic (MCEdit antiguo) -> ErrorSchematic con la explicación", lambda: ns_.leer_archivo(viejo))

jar = real(os.path.join(os.path.expanduser("~"), ".gradle", "caches", "forge_gradle", "minecraft_repo", "versions", "1.20.1", "client.jar"))
if jar:
    z = zipfile.ZipFile(jar)
    nombres_nbt = [n for n in z.namelist() if n.endswith(".nbt") and "/structures/" in n]
    fallos, sin_bloques, total_bloques, con_jigsaw_restante = [], 0, 0, 0
    t0 = time.time()
    for n in nombres_nbt:
        try:
            s = ns_.leer_schematic(z.read(n), os.path.basename(n))
            total_bloques += len(s.bloques)
            if not s.bloques:
                sin_bloques += 1
            if any("jigsaw" in e for e in s.bloques.values()):
                con_jigsaw_restante += 1
            if not all(0 <= x < s.ancho and 0 <= y < s.alto and 0 <= z_ < s.largo for (x, y, z_) in s.bloques):
                fallos.append((n, "fuera de tamaño"))
        except Exception as e:  # noqa: BLE001
            fallos.append((n, f"{type(e).__name__}: {e}"))
    r.check(f"REAL: las {len(nombres_nbt)} estructuras vanilla del juego se leen SIN error (fallos: {fallos[:3]})", len(nombres_nbt) >= 1000 and not fallos)
    r.check(f"REAL: leyó {total_bloques} bloques en {time.time() - t0:.1f} s; ninguna se queda con un jigsaw sin resolver ({con_jigsaw_restante}); vacías: {sin_bloques}", con_jigsaw_restante == 0)
    casa_v = z.read("data/minecraft/structures/village/plains/houses/plains_small_house_1.nbt")
    sc = ns_.leer_schematic(casa_v, "plains_small_house_1")
    plano, av = ns_.a_plano_cobalt(sc)
    r.check(f"REAL casa de aldea de llanura: {sc} -> plano {plano['dimensions']} con estados (puertas, escaleras, antorchas)", any("state" in b for c in plano["layers"] for b in c["blocks"]) and len(sc.bloques) > 50)
    rnd = random.Random(2026)
    muestras = [z.read(n) for n in rnd.sample(nombres_nbt, 12)] + [open(casa_real, "rb").read()] * 3 if casa_real else [z.read(n) for n in rnd.sample(nombres_nbt, 12)]
    raros, lento = [], 0
    for base in muestras:
        crudo = gzip.decompress(base) if base[:2] == b"\x1f\x8b" else base
        for _ in range(40):
            b = bytearray(crudo)
            for _ in range(rnd.randrange(1, 6)):
                b[rnd.randrange(len(b))] = rnd.randrange(256)
            if rnd.random() < 0.3:
                b = b[:rnd.randrange(1, len(b))]
            t0 = time.time()
            try:
                ns_.leer_schematic(bytes(b))
            except ns_.ErrorSchematic:
                pass
            except BaseException as e:  # noqa: BLE001
                raros.append(f"{type(e).__name__}: {str(e)[:60]}")
            lento += 1 if time.time() - t0 > 5 else 0
    r.check(f"FUZZING: {len(muestras) * 40} archivos reales corrompidos -> solo ErrorSchematic o lectura correcta (excepciones raras: {raros[:3]}; lentos: {lento})", not raros and lento == 0)
else:
    print("SKIP  (no está client.jar de Forge en la caché de Gradle)")

r.terminar()
