"""Bloque R (prueba de viabilidad): lector de schematics."""
import json
import os
import re
import struct
import unicodedata
import zlib

LIMITE_DESCOMPRIMIDO = 64 * 1024 * 1024
PROFUNDIDAD_MAX = 48
MAX_ELEMENTOS = 8_000_000
MAX_VOLUMEN = 40_000_000
MAX_LADO_DEFECTO = 64
MAX_BLOQUES_DEFECTO = 20000
AIRE = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air", "minecraft:structure_void"}

BLOQUES_PROHIBIDOS = {
    "tnt", "lava", "water", "fire", "soul_fire", "bedrock", "command_block", "chain_command_block", "repeating_command_block",
    "structure_block", "structure_void", "jigsaw", "spawner", "barrier", "light", "end_portal", "end_portal_frame",
    "nether_portal", "end_gateway", "respawn_anchor", "moving_piston", "piston_head", "reinforced_deepslate",
}
FRAGMENTOS_PROHIBIDOS = ("lava", "tnt", "command_block", "spawner", "portal")


class ErrorSchematic(Exception):
    """El archivo no se puede leer o no es seguro/válido. El mensaje es apto para decírselo al jugador."""


def _descomprimir(datos):
    if datos[:2] == b"\x1f\x8b":
        d = zlib.decompressobj(31)
        try:
            salida = d.decompress(datos, LIMITE_DESCOMPRIMIDO + 1)
        except zlib.error as e:
            raise ErrorSchematic(f"archivo comprimido dañado ({e})")
        if len(salida) > LIMITE_DESCOMPRIMIDO or d.unconsumed_tail:
            raise ErrorSchematic("el archivo ocupa demasiado al descomprimirse (posible bomba de compresión)")
        return salida
    if len(datos) > LIMITE_DESCOMPRIMIDO:
        raise ErrorSchematic("archivo demasiado grande")
    return datos


class _Lector:
    def __init__(self, datos):
        self.b, self.i = memoryview(datos), 0

    def tomar(self, n):
        if n < 0 or self.i + n > len(self.b):
            raise ErrorSchematic("archivo truncado o dañado")
        s = self.b[self.i:self.i + n]
        self.i += n
        return s

    def u8(self):
        return self.tomar(1)[0]

    def s8(self):
        return struct.unpack(">b", self.tomar(1))[0]

    def entero(self, fmt, n):
        return struct.unpack(">" + fmt, self.tomar(n))[0]

    def cadena(self):
        n = self.entero("H", 2)
        return bytes(self.tomar(n)).decode("utf-8", "replace")

    def carga(self, tipo, prof):
        if prof > PROFUNDIDAD_MAX:
            raise ErrorSchematic("NBT demasiado anidado")
        if tipo == 1:
            return self.s8()
        if tipo == 2:
            return self.entero("h", 2)
        if tipo == 3:
            return self.entero("i", 4)
        if tipo == 4:
            return self.entero("q", 8)
        if tipo == 5:
            return self.entero("f", 4)
        if tipo == 6:
            return self.entero("d", 8)
        if tipo == 7:
            n = self.entero("i", 4)
            return bytes(self.tomar(n))
        if tipo == 8:
            return self.cadena()
        if tipo == 9:
            t, n = self.u8(), self.entero("i", 4)
            if n < 0 or n > MAX_ELEMENTOS or (t == 0 and n > 0):
                raise ErrorSchematic("lista NBT inválida")
            if t == 3:
                return list(struct.unpack(f">{n}i", self.tomar(4 * n)))
            if t == 6:
                return list(struct.unpack(f">{n}d", self.tomar(8 * n)))
            return [self.carga(t, prof + 1) for _ in range(n)]
        if tipo == 10:
            d = {}
            while True:
                t = self.u8()
                if t == 0:
                    return d
                nombre = self.cadena()
                d[nombre] = self.carga(t, prof + 1)
        if tipo == 11:
            n = self.entero("i", 4)
            if n < 0 or n > MAX_ELEMENTOS:
                raise ErrorSchematic("array NBT inválido")
            return list(struct.unpack(f">{n}i", self.tomar(4 * n)))
        if tipo == 12:
            n = self.entero("i", 4)
            if n < 0 or n > MAX_ELEMENTOS:
                raise ErrorSchematic("array NBT inválido")
            return list(struct.unpack(f">{n}q", self.tomar(8 * n)))
        raise ErrorSchematic(f"tipo NBT desconocido ({tipo})")


def leer_nbt(datos):
    """bytes (con o sin gzip) -> (nombre_raiz, dict)."""
    try:
        lector = _Lector(_descomprimir(bytes(datos)))
        if lector.u8() != 10:
            raise ErrorSchematic("no es un archivo NBT (la raíz no es un compuesto)")
        return lector.cadena(), lector.carga(10, 0)
    except ErrorSchematic:
        raise
    except (struct.error, MemoryError, RecursionError, ValueError, OverflowError) as e:
        raise ErrorSchematic(f"NBT dañado ({type(e).__name__})")


def normalizar_estado(nombre, propiedades=None):
    """'oak_stairs' + {'half': 'bottom', 'facing': 'east'} -> 'minecraft:oak_stairs[facing=east,half=bottom]' (propiedades ordenadas)."""
    nombre = str(nombre).strip().lower()
    if "[" in nombre:
        nombre, resto = nombre.split("[", 1)
        propiedades = dict(p.split("=", 1) for p in resto.rstrip("]").split(",") if "=" in p)
    if ":" not in nombre:
        nombre = "minecraft:" + nombre
    if propiedades:
        return nombre + "[" + ",".join(f"{k}={v}" for k, v in sorted((str(k), str(v)) for k, v in propiedades.items())) + "]"
    return nombre


def partir_estado(estado):
    """'minecraft:oak_stairs[facing=east]' -> ('minecraft:oak_stairs', 'facing=east') ; sin propiedades -> (id, '')."""
    if "[" in estado:
        nombre, resto = estado.split("[", 1)
        return nombre, resto.rstrip("]")
    return estado, ""


class Schem:
    """Un schematic ya leído: dimensiones, los bloques NO vacíos {(x,y,z): estado} y lo que se ha dejado fuera."""

    def __init__(self, formato, ancho, alto, largo, bloques, datos_version=None, entidades_bloque=0, nombre=""):
        self.formato, self.ancho, self.alto, self.largo = formato, ancho, alto, largo
        self.bloques, self.datos_version, self.entidades_bloque, self.nombre = bloques, datos_version, entidades_bloque, nombre

    def __repr__(self):
        return f"Schem({self.formato}, {self.ancho}x{self.alto}x{self.largo}, {len(self.bloques)} bloques)"


def _dim(valor, nombre):
    if isinstance(valor, int) and -32768 <= valor < 0:
        valor += 65536
    if not isinstance(valor, int) or not 0 < valor <= 65535:
        raise ErrorSchematic(f"dimensión inválida ({nombre}={valor!r})")
    return valor


def _comprobar_volumen(a, b, c):
    if a * b * c > MAX_VOLUMEN:
        raise ErrorSchematic(f"el volumen del schematic ({a}x{b}x{c}) es demasiado grande para leerlo")


def _varints(datos, cuantos):
    salida, i, n = [], 0, len(datos)
    while i < n and len(salida) < cuantos + 1:
        valor, desp = 0, 0
        while True:
            if i >= n:
                raise ErrorSchematic("BlockData truncado")
            b = datos[i]
            i += 1
            valor |= (b & 0x7F) << desp
            desp += 7
            if desp > 35:
                raise ErrorSchematic("varint demasiado grande (datos dañados)")
            if not b & 0x80:
                break
        salida.append(valor)
    return salida


def _leer_sponge(raiz):
    r = raiz.get("Schematic", raiz) if isinstance(raiz.get("Schematic"), dict) else raiz
    version = r.get("Version")
    w, h, l = _dim(r.get("Width"), "Width"), _dim(r.get("Height"), "Height"), _dim(r.get("Length"), "Length")
    _comprobar_volumen(w, h, l)
    if isinstance(r.get("Blocks"), dict):  # v3
        paleta, datos, entidades = r["Blocks"].get("Palette"), r["Blocks"].get("Data"), r["Blocks"].get("BlockEntities", [])
    else:  # v1/v2
        paleta, datos, entidades = r.get("Palette"), r.get("BlockData"), r.get("BlockEntities", [])
    if not isinstance(paleta, dict) or not isinstance(datos, (bytes, bytearray)):
        raise ErrorSchematic("schematic Sponge sin paleta o sin datos de bloques")
    inversa = {}
    for nombre, idx in paleta.items():
        if not isinstance(idx, int):
            raise ErrorSchematic("paleta Sponge inválida")
        inversa[idx] = normalizar_estado(nombre)
    indices = _varints(datos, w * h * l)
    if len(indices) != w * h * l:
        raise ErrorSchematic(f"el schematic dice {w}x{h}x{l}={w * h * l} bloques pero trae {len(indices)}")
    bloques = {}
    wl = w * l
    for i, idx in enumerate(indices):
        estado = inversa.get(idx)
        if estado is None:
            raise ErrorSchematic(f"el bloque {i} usa un índice de paleta inexistente ({idx})")
        if estado in AIRE or estado.split("[", 1)[0] in AIRE:
            continue
        bloques[(i % w, i // wl, (i // w) % l)] = estado  # x + z*Ancho + y*Ancho*Largo
    return Schem(f"sponge v{version}", w, h, l, bloques, r.get("DataVersion"), len(entidades) if isinstance(entidades, list) else 0)


def _estado_de_paleta(entrada):
    if not isinstance(entrada, dict) or "Name" not in entrada:
        raise ErrorSchematic("paleta de estructura inválida")
    return normalizar_estado(entrada["Name"], entrada.get("Properties") or None)


def _leer_vanilla(raiz):
    tam = raiz.get("size")
    if not (isinstance(tam, list) and len(tam) == 3 and all(isinstance(v, int) and v > 0 for v in tam)):
        raise ErrorSchematic("estructura sin 'size' válido")
    w, h, l = tam
    _comprobar_volumen(w, h, l)
    paletas = raiz.get("palettes")
    paleta = paletas[0] if isinstance(paletas, list) and paletas else raiz.get("palette")
    if not isinstance(paleta, list):
        raise ErrorSchematic("estructura sin paleta")
    estados = [_estado_de_paleta(e) for e in paleta]
    bloques, entidades = {}, 0
    for b in raiz.get("blocks") or []:
        pos, idx = b.get("pos"), b.get("state")
        if not (isinstance(pos, list) and len(pos) == 3 and isinstance(idx, int) and 0 <= idx < len(estados)):
            raise ErrorSchematic("bloque de estructura inválido")
        x, y, z = pos
        if not (0 <= x < w and 0 <= y < h and 0 <= z < l):
            raise ErrorSchematic("un bloque cae fuera del tamaño declarado")
        estado = estados[idx]
        nbt = b.get("nbt") if isinstance(b.get("nbt"), dict) else None
        if estado.startswith("minecraft:jigsaw") and nbt and isinstance(nbt.get("final_state"), str):
            estado = normalizar_estado(nbt["final_state"])
        elif nbt:
            entidades += 1
        if estado.split("[", 1)[0] in AIRE:
            continue
        bloques[(x, y, z)] = estado
    return Schem("estructura vanilla", w, h, l, bloques, raiz.get("DataVersion"), entidades)


def _leer_region_litematica(region):
    tam, pos = region.get("Size"), region.get("Position")
    if not (isinstance(tam, dict) and isinstance(pos, dict)):
        raise ErrorSchematic("región de Litematica sin Size/Position")
    sx, sy, sz = (int(tam.get(k, 0)) for k in ("x", "y", "z"))
    px, py, pz = (int(pos.get(k, 0)) for k in ("x", "y", "z"))
    ax, ay, az = abs(sx), abs(sy), abs(sz)
    if min(ax, ay, az) <= 0:
        raise ErrorSchematic("región de Litematica vacía")
    _comprobar_volumen(ax, ay, az)
    paleta = region.get("BlockStatePalette")
    largos = region.get("BlockStates")
    if not isinstance(paleta, list) or not paleta or not isinstance(largos, list):
        raise ErrorSchematic("región de Litematica sin paleta o sin estados")
    estados = [_estado_de_paleta(e) for e in paleta]
    bits = max(2, (len(estados) - 1).bit_length())
    mascara = (1 << bits) - 1
    total = ax * ay * az
    if len(largos) * 64 < total * bits:
        raise ErrorSchematic("región de Litematica con menos datos de los declarados")
    u = [v & 0xFFFFFFFFFFFFFFFF for v in largos]
    minx, miny, minz = px + (sx + 1 if sx < 0 else 0), py + (sy + 1 if sy < 0 else 0), pz + (sz + 1 if sz < 0 else 0)
    bloques = {}
    for i in range(total):
        ini = i * bits
        a, off = ini >> 6, ini & 63
        v = (u[a] >> off) & mascara
        if off + bits > 64:
            v |= (u[a + 1] << (64 - off)) & mascara
        if v >= len(estados):
            raise ErrorSchematic("índice de paleta fuera de rango en Litematica")
        estado = estados[v]
        if estado.split("[", 1)[0] in AIRE:
            continue
        x, z, y = i % ax, (i // ax) % az, i // (ax * az)  # (y * Z + z) * X + x
        bloques[(minx + x, miny + y, minz + z)] = estado
    return bloques, (minx, miny, minz, ax, ay, az)


def _leer_litematica(raiz):
    regiones = raiz.get("Regions")
    if not isinstance(regiones, dict) or not regiones:
        raise ErrorSchematic("Litematica sin regiones")
    todos, cajas = {}, []
    for nombre, reg in regiones.items():
        if not isinstance(reg, dict):
            raise ErrorSchematic("región de Litematica inválida")
        bloques, caja = _leer_region_litematica(reg)
        todos.update(bloques)
        cajas.append(caja)
    x0, y0, z0 = min(c[0] for c in cajas), min(c[1] for c in cajas), min(c[2] for c in cajas)
    x1, y1, z1 = max(c[0] + c[3] for c in cajas), max(c[1] + c[4] for c in cajas), max(c[2] + c[5] for c in cajas)
    normal = {(x - x0, y - y0, z - z0): e for (x, y, z), e in todos.items()}
    return Schem("litematica", x1 - x0, y1 - y0, z1 - z0, normal, raiz.get("MinecraftDataVersion"), 0)


def leer_schematic(datos, nombre=""):
    """bytes de un .schem / .nbt / .litematic -> Schem."""
    _, raiz = leer_nbt(datos)
    r = raiz.get("Schematic") if isinstance(raiz.get("Schematic"), dict) else raiz
    if "Regions" in raiz:
        s = _leer_litematica(raiz)
    elif "size" in raiz and ("palette" in raiz or "palettes" in raiz):
        s = _leer_vanilla(raiz)
    elif ("Palette" in r and ("BlockData" in r or isinstance(r.get("Blocks"), dict))) or (isinstance(r.get("Blocks"), dict) and "Palette" in r["Blocks"]):
        s = _leer_sponge(raiz)
    elif isinstance(r.get("Blocks"), (bytes, bytearray)) and ("Materials" in r or "Data" in r):
        raise ErrorSchematic("es un .schematic antiguo de MCEdit (ids numéricos de 1.12): conviértelo a .schem con WorldEdit (//schem save) o Amulet")
    else:
        raise ErrorSchematic("formato de schematic no reconocido (esperaba .schem, .nbt de estructura o .litematic)")
    s.nombre = nombre
    return s


def leer_archivo(ruta):
    try:
        with open(ruta, "rb") as f:
            datos = f.read(LIMITE_DESCOMPRIMIDO + 1)
    except OSError as e:
        raise ErrorSchematic(f"no se pudo abrir el archivo ({type(e).__name__})")
    return leer_schematic(datos, os.path.splitext(os.path.basename(ruta))[0])


_ITEM_ESPECIAL = {"wall_torch": "torch", "soul_wall_torch": "soul_torch", "redstone_wall_torch": "redstone_torch", "redstone_wire": "redstone",
                  "wheat": "wheat_seeds", "carrots": "carrot", "potatoes": "potato", "beetroots": "beetroot_seeds", "melon_stem": "melon_seeds",
                  "pumpkin_stem": "pumpkin_seeds", "tripwire": "string", "sweet_berry_bush": "sweet_berries", "cocoa": "cocoa_beans", "bamboo_sapling": "bamboo",
                  "kelp_plant": "kelp", "cave_vines": "glow_berries", "cave_vines_plant": "glow_berries", "frosted_ice": "ice", "fire": "flint_and_steel"}


def item_de_bloque(bloque_id):
    """Aproximación del ítem que hace falta para colocar un bloque (en Java, Block.asItem() es la verdad; esto sirve para la lista de materiales)."""
    n = bloque_id.split(":", 1)[-1]
    if n in _ITEM_ESPECIAL:
        return "minecraft:" + _ITEM_ESPECIAL[n]
    for sufijo_bloque, sufijo_item in (("_wall_sign", "_sign"), ("_wall_hanging_sign", "_hanging_sign"), ("_wall_banner", "_banner"), ("_wall_head", "_head"),
                                       ("_wall_skull", "_skull")):
        if n.endswith(sufijo_bloque):
            return "minecraft:" + n[:-len(sufijo_bloque)] + sufijo_item
    return "minecraft:" + n


def materiales_necesarios(bloques):
    """{estado: ...} (o valores de Schem.bloques) -> {item: cantidad}. Losas dobles = 2; puertas/camas/plantas altas = 1 (solo la mitad de abajo/pie)."""
    cuenta = {}
    for estado in bloques:
        nombre, props = partir_estado(estado)
        p = dict(kv.split("=", 1) for kv in props.split(",") if "=" in kv) if props else {}
        if p.get("half") == "upper" or p.get("part") == "head":
            continue
        item = item_de_bloque(nombre)
        cuenta[item] = cuenta.get(item, 0) + (2 if p.get("type") == "double" else 1)
    return cuenta


def es_prohibido(bloque_id):
    ruta = bloque_id.split(":", 1)[-1]
    return ruta in BLOQUES_PROHIBIDOS or any(f in ruta for f in FRAGMENTOS_PROHIBIDOS)


def a_plano_cobalt(schem, nombre=None, max_lado=MAX_LADO_DEFECTO, max_bloques=MAX_BLOQUES_DEFECTO):
    """Schem -> (plano, avisos)."""
    avisos, omitidos, utiles = [], {}, {}
    for pos, estado in schem.bloques.items():
        bid, _ = partir_estado(estado)
        if es_prohibido(bid):
            omitidos[bid.split(":", 1)[-1]] = omitidos.get(bid.split(":", 1)[-1], 0) + 1
            continue
        utiles[pos] = estado
    if omitidos:
        avisos.append("bloques peligrosos omitidos: " + ", ".join(f"{k}×{v}" for k, v in sorted(omitidos.items(), key=lambda kv: -kv[1])))
    if schem.entidades_bloque:
        avisos.append(f"{schem.entidades_bloque} bloques con datos (cofres, carteles...) se colocan vacíos")
    if not utiles:
        raise ErrorSchematic("el schematic no tiene ningún bloque colocable")
    x0, y0, z0 = (min(p[i] for p in utiles) for i in range(3))
    x1, y1, z1 = (max(p[i] for p in utiles) for i in range(3))
    ancho, alto, largo = x1 - x0 + 1, y1 - y0 + 1, z1 - z0 + 1
    if max(ancho, alto, largo) > max_lado:
        raise ErrorSchematic(f"mide {ancho}x{alto}x{largo} y el máximo permitido por lado es {max_lado}")
    if len(utiles) > max_bloques:
        raise ErrorSchematic(f"tiene {len(utiles)} bloques y el máximo permitido es {max_bloques}")
    capas = {}
    for (x, y, z), estado in utiles.items():
        bid, props = partir_estado(estado)
        b = {"x": x - x0, "z": z - z0, "block": bid}
        if props:
            b["state"] = props
        capas.setdefault(y - y0, []).append(b)
    layers = [{"y": y, "blocks": sorted(bl, key=lambda d: (d["z"], d["x"]))} for y, bl in sorted(capas.items())]
    plano = {"blueprint_name": _nombre_seguro(nombre or schem.nombre or "schematic"), "dimensions": {"width": ancho, "height": alto, "length": largo},
             "layers": layers, "origen": "schematic:" + schem.formato}
    return plano, avisos


def _nombre_seguro(texto):
    t = re.sub(r"[^a-z0-9]+", "_", _ascii(texto)).strip("_")[:40].strip("_")  # sin acentos: 'Casa Pequeña' -> 'casa_pequena' (antes 'casa_peque_a')
    return t or "schematic"


def importar_schematic(ruta, carpeta_planos, nombre=None, max_lado=MAX_LADO_DEFECTO, max_bloques=MAX_BLOQUES_DEFECTO):
    """Lee un schematic, lo convierte y lo guarda en 'carpeta_planos' sin pisar uno existente."""
    schem = leer_archivo(ruta)
    plano, avisos = a_plano_cobalt(schem, nombre, max_lado, max_bloques)
    os.makedirs(carpeta_planos, exist_ok=True)
    base = plano["blueprint_name"]
    final = base
    for n in range(2, 100):
        if not os.path.exists(os.path.join(carpeta_planos, final + ".json")):
            break
        final = f"{base}_{n}"
    plano["blueprint_name"] = final
    ruta_final = os.path.join(carpeta_planos, final + ".json")
    tmp = ruta_final + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(plano, f, ensure_ascii=False)
    os.replace(tmp, ruta_final)
    todos = [b["block"] + ("[" + b["state"] + "]" if "state" in b else "") for c in plano["layers"] for b in c["blocks"]]
    return {"nombre": final, "ruta": ruta_final, "formato": schem.formato, "dimensiones": tuple(plano["dimensions"].values()), "bloques": len(todos),
            "materiales": materiales_necesarios(todos), "avisos": avisos, "con_estados": sum(1 for t in todos if "[" in t)}


EXTENSIONES_LEIBLES = (".schem", ".litematic", ".nbt")   # por este orden si hay dos archivos con el mismo nombre
EXTENSIONES_LISTADAS = EXTENSIONES_LEIBLES + (".schematic",)  # el MCEdit antiguo se lista para poder explicar por qué no se lee
MAX_ARCHIVO_BYTES = 32 * 1024 * 1024


def _ascii(texto):
    return unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii").lower()


def _clave_nombre(texto):
    t = re.sub(r"\.(schem|litematic|nbt|schematic)$", "", _ascii(texto).strip())
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


_LISTAR = re.compile(r"^(?:(?:lista|listar|muestra|mostrar|ensena|dime)\s+(?:mis\s+|los\s+|las\s+|tus\s+)?|(?:que|cuales)\s+(?:son\s+)?(?:mis\s+|los\s+|las\s+|tus\s+)?)"
                     r"(?:schematics?|schems?|esquemas?)(?:\s+(?:tengo|hay|tienes|disponibles?))?$")
_IMPORTAR = re.compile(r"^(?:importa|importar|convierte|convertir|lee|leer|carga|cargar)\s+(?:el\s+|la\s+|un\s+|una\s+|mi\s+)?(?:schematic|schem|esquema|litematica)\s+"
                       r"(?:llamado\s+|llamada\s+|de\s+nombre\s+)?(?P<nombre>[a-z0-9 ._\-]{1,80})$")


def interpretar_comando(mensaje):
    """('listar', None) | ('importar', nombre) | None."""
    if not isinstance(mensaje, str) or len(mensaje) > 200:
        return None
    t = re.sub(r"\b(?:cobalt|nox)\b", " ", _ascii(mensaje))
    t = re.sub(r"[¿?¡!,;:]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip().rstrip(".").strip()
    t = re.sub(r"\b(?:por favor|porfa|please)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if _LISTAR.match(t):
        return ("listar", None)
    m = _IMPORTAR.match(t)
    if m and _clave_nombre(m.group("nombre")):
        return ("importar", m.group("nombre").strip())
    return None


def listar_schematics(carpeta, max_n=100):
    """[(nombre_sin_extension, extension)] ordenado, de los archivos de la carpeta (sin entrar en subcarpetas)."""
    try:
        nombres = os.listdir(carpeta)
    except OSError:
        return []
    salida = []
    for n in sorted(nombres, key=str.lower):
        stem, ext = os.path.splitext(n)
        if ext.lower() in EXTENSIONES_LISTADAS and not n.startswith(".") and os.path.isfile(os.path.join(carpeta, n)):
            salida.append((stem, ext.lower()))
    return salida[:max_n]


def buscar_schematic(carpeta, nombre):
    """(ruta, parecidos)."""
    clave = _clave_nombre(nombre)
    archivos = listar_schematics(carpeta)
    iguales = [(s, e) for s, e in archivos if _clave_nombre(s) == clave]
    if iguales:
        iguales.sort(key=lambda se: EXTENSIONES_LISTADAS.index(se[1]))
        return os.path.join(carpeta, iguales[0][0] + iguales[0][1]), []
    palabras = clave.split()
    parecidos, vistos = [], set()
    for s, _ in archivos:
        c = _clave_nombre(s)
        if palabras and all(p in c for p in palabras) and c not in vistos:  # un mismo nombre con dos extensiones se sugiere una sola vez
            vistos.add(c)
            parecidos.append(s)
    return None, parecidos[:3]


def texto_materiales(materiales, max_items=3):
    """{item: cantidad} -> '120 stone bricks, 40 oak planks, 12 glass y 5 más' (los más numerosos primero)."""
    limpios = {}
    for item, n in (materiales or {}).items():
        nombre = re.sub(r"[^a-z0-9 ]", " ", str(item).split(":", 1)[-1].replace("_", " ").lower())
        nombre = re.sub(r"\s+", " ", nombre).strip()[:30].strip()
        if nombre and isinstance(n, int) and n > 0:
            limpios[nombre] = limpios.get(nombre, 0) + n
    orden = sorted(limpios.items(), key=lambda kv: (-kv[1], kv[0]))
    partes = [f"{n} {nombre}" for nombre, n in orden[:max_items]]
    texto = ", ".join(partes)
    if len(orden) > max_items:
        texto += f" y {len(orden) - max_items} más"
    return texto
