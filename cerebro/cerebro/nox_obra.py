"""BLOQUE N (terreno y obra): lógica PURA (sin Minecraft, sin disco, sin red) para que Cobalt decida dónde y cómo construir."""
import heapq
import math
import re
import unicodedata

# Códigos de terrain_map.json (los escribe NoxTerreno.java)
SUELO, AGUA, LAVA, VACIO, OBSTACULO, DESCONOCIDO = 0, 1, 2, 3, 4, 9

MAX_BLOQUES_PLANO = 6000      # tope de bloques de un plano generado
MAX_LADO_MAPA = 64            # lado máximo de un escaneo de relieve
MAX_VOLUMEN_ESCANEO = 6000
MAX_DESNIVEL = 12             # coincide con NoxTerreno.MAX_CORTE / MAX_RELLENO
MAX_COSTE_APLANADO = 9500     # cavar + rellenar (Java tolera 10000 por orden)
DISTANCIA_BASE = 34.0         # la obra se rechaza a <=32 de la base; se deja 2 de margen

NO_COPIAR = {"water", "lava", "fire", "soul_fire", "tnt", "bedrock", "barrier", "spawner", "command_block", "chain_command_block",
             "repeating_command_block", "structure_block", "jigsaw", "end_portal", "end_portal_frame", "nether_portal", "end_gateway",
             "chest", "trapped_chest", "barrel", "furnace", "blast_furnace", "smoker", "hopper", "dropper", "dispenser", "brewing_stand",
             "beacon", "lectern", "jukebox", "decorated_pot", "sculk_sensor", "sculk_catalyst", "sculk_shrieker", "ender_chest"}
NO_COPIAR_FRAGMENTOS = ("shulker_box", "_sign", "_banner", "_bed", "_head", "_skull")

_ARTICULOS_INICIALES = {"el", "la", "los", "las", "un", "una", "unos", "unas", "mi", "mis", "tu", "esta", "este", "ese", "esa"}
_ARTICULOS = _ARTICULOS_INICIALES | {"de", "del", "al", "a", "en", "hasta", "hacia", "por", "para", "que", "con", "y"}

_ESPECIALES = ("door", "glass", "pane", "stairs", "slab", "fence", "gate", "torch", "lantern", "ladder", "trapdoor", "button", "lever", "sign",
               "bed", "chest", "barrel", "furnace", "table", "vine", "carpet", "banner", "head", "flower", "pot", "campfire")


def _sin_acentos(t):
    return unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode("ascii").lower()


def _ruta_id(ident):
    ident = str(ident or "").lower()
    return ident.split(":", 1)[1] if ":" in ident else ident


def _id_completo(ident):
    ident = str(ident or "").lower().strip()
    return ident if ":" in ident else "minecraft:" + ident


class MapaRelieve:
    """Alturas y tipos de superficie de una caja x1..x2, z1..z2 (filas = z, columnas = x)."""

    def __init__(self, x1, z1, x2, z2, alturas, tipos):
        self.x1, self.z1, self.x2, self.z2 = x1, z1, x2, z2
        self.h = alturas
        self.t = tipos
        self.ancho = x2 - x1 + 1
        self.largo = z2 - z1 + 1

    @classmethod
    def desde_json(cls, d):
        try:
            if not isinstance(d, dict) or d.get("status") != "success":
                return None
            x1, z1, x2, z2 = (int(d[k]) for k in ("x1", "z1", "x2", "z2"))
            if x2 < x1 or z2 < z1:
                return None
            alturas, tipos = d["y"], d["t"]
            ancho, largo = x2 - x1 + 1, z2 - z1 + 1
            if len(alturas) != largo or len(tipos) != largo:
                return None
            for fila_h, fila_t in zip(alturas, tipos):
                if len(fila_h) != ancho or len(fila_t) != ancho:
                    return None
            return cls(x1, z1, x2, z2, [[int(v) for v in f] for f in alturas], [[int(v) for v in f] for f in tipos])
        except (KeyError, TypeError, ValueError):
            return None

    def dentro(self, x, z):
        return self.x1 <= x <= self.x2 and self.z1 <= z <= self.z2

    def altura(self, x, z):
        return self.h[z - self.z1][x - self.x1]

    def tipo(self, x, z):
        return self.t[z - self.z1][x - self.x1]


def _lejos_de_base(x0, z0, ancho, largo, y_suelo, base, distancia):
    if not base:
        return True
    bx, by, bz = base
    dx = max(x0 - bx, 0, bx - (x0 + ancho - 1))
    dz = max(z0 - bz, 0, bz - (z0 + largo - 1))
    dy = y_suelo - by
    return math.sqrt(dx * dx + dz * dz + dy * dy) > distancia


def mejor_sitio(mapa, ancho, largo, base=None, distancia_base=DISTANCIA_BASE, max_desnivel=MAX_DESNIVEL,
                max_coste=MAX_COSTE_APLANADO, preferido=None):
    """El rectángulo ancho x largo con MENOS terreno que mover (cavar + rellenar hasta la altura mediana), o None."""
    if ancho < 1 or largo < 1 or ancho > mapa.ancho or largo > mapa.largo:
        return None
    malas = [[0] * (mapa.ancho + 1) for _ in range(mapa.largo + 1)]
    for j in range(mapa.largo):
        for i in range(mapa.ancho):
            malas[j + 1][i + 1] = malas[j][i + 1] + malas[j + 1][i] - malas[j][i] + (0 if mapa.t[j][i] == SUELO else 1)
    mejor, mejor_clave = None, None
    for j0 in range(mapa.largo - largo + 1):
        for i0 in range(mapa.ancho - ancho + 1):
            j1, i1 = j0 + largo, i0 + ancho
            if malas[j1][i1] - malas[j0][i1] - malas[j1][i0] + malas[j0][i0] != 0:
                continue
            alturas = [mapa.h[j][i] for j in range(j0, j1) for i in range(i0, i1)]
            ordenadas = sorted(alturas)
            y = ordenadas[(len(ordenadas) - 1) // 2]  # mediana: minimiza cavar + rellenar
            if max(abs(h - y) for h in alturas) > max_desnivel:
                continue
            cortar = sum(h - y for h in alturas if h > y)
            rellenar = sum(y - h for h in alturas if h < y)
            coste = cortar + rellenar
            if coste > max_coste:
                continue
            x0, z0 = mapa.x1 + i0, mapa.z1 + j0
            if not _lejos_de_base(x0, z0, ancho, largo, y + 1, base, distancia_base):
                continue
            cerca = 0.0
            if preferido:
                cerca = math.hypot(x0 + ancho / 2.0 - preferido[0], z0 + largo / 2.0 - preferido[1])
            clave = (coste, cerca)
            if mejor_clave is None or clave < mejor_clave:
                mejor_clave = clave
                mejor = {"x0": x0, "z0": z0, "y": y, "coste": coste, "cortar": cortar, "rellenar": rellenar}
    return mejor


def nivel_objetivo(mapa, x1, z1, x2, z2):
    """Altura a la que nivelar la zona (mediana de las columnas de suelo), o None si no hay ninguna columna de suelo dentro del mapa."""
    alturas = []
    for z in range(min(z1, z2), max(z1, z2) + 1):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if mapa.dentro(x, z) and mapa.tipo(x, z) == SUELO:
                alturas.append(mapa.altura(x, z))
    if not alturas:
        return None
    alturas.sort()
    return alturas[(len(alturas) - 1) // 2]


def dimensiones_de_plano(plano):
    """(ancho, alto, largo) que ocupa el plano; (0, 0, 0) si no tiene bloques."""
    xs, ys, zs = [], [], []
    for capa in (plano or {}).get("layers", []):
        for b in capa.get("blocks", []):
            xs.append(b["x"])
            ys.append(capa["y"])
            zs.append(b["z"])
    if not xs:
        return (0, 0, 0)
    return (max(xs) + 1, max(ys) + 1, max(zs) + 1)


def _plano_desde_celdas(celdas, nombre="plano"):
    por_y = {}
    for (x, y, z), ident in celdas.items():
        por_y.setdefault(y, []).append({"x": x, "z": z, "block": ident})
    capas = [{"y": y, "blocks": sorted(por_y[y], key=lambda b: (b["z"], b["x"]))} for y in sorted(por_y)]
    ancho = max(x for x, _, _ in celdas) + 1
    alto = max(y for _, y, _ in celdas) + 1
    largo = max(z for _, _, z in celdas) + 1
    return {"blueprint_name": nombre, "dimensions": {"width": ancho, "height": alto, "length": largo}, "layers": capas}


def _celdas_de_plano(plano):
    celdas = {}
    for capa in plano.get("layers", []):
        for b in capa.get("blocks", []):
            celdas.setdefault((b["x"], capa["y"], b["z"]), _id_completo(b["block"]))
    return celdas


def _columna_de_estirado(celdas, eje, longitud):
    centro = (longitud - 1) / 2.0
    candidatas = [i for i in range(longitud) if abs(i - centro) <= max(1.0, longitud / 6.0)] or [longitud // 2]
    mejor, mejor_clave = None, None
    for i in candidatas:
        especiales = sum(1 for (x, y, z), ident in celdas.items()
                         if (x if eje == "x" else z) == i and any(f in _ruta_id(ident) for f in _ESPECIALES))
        clave = (especiales, abs(i - centro))
        if mejor_clave is None or clave < mejor_clave:
            mejor, mejor_clave = i, clave
    return mejor


def estirar_blueprint(plano, nuevo_ancho, nuevo_largo):
    """Ensancha el plano a nuevo_ancho x nuevo_largo repitiendo la columna/fila central MÁS NEUTRA. Solo agranda (o deja igual)."""
    celdas = _celdas_de_plano(plano or {})
    if not celdas:
        return None, "el plano no tiene bloques"
    ancho, _, largo = dimensiones_de_plano(plano)
    if nuevo_ancho < ancho or nuevo_largo < largo:
        return None, f"solo sé agrandar planos (el original es {ancho}x{largo}; pediste {nuevo_ancho}x{nuevo_largo})"
    if nuevo_ancho > 64 or nuevo_largo > 64:
        return None, "el lado máximo es 64 bloques"
    xm = _columna_de_estirado(celdas, "x", ancho)
    zm = _columna_de_estirado(celdas, "z", largo)
    dx, dz = nuevo_ancho - ancho, nuevo_largo - largo
    nuevas = {}
    for (x, y, z), ident in celdas.items():
        xs = [x] if x < xm else ([x + dx] if x > xm else list(range(xm, xm + dx + 1)))
        zs = [z] if z < zm else ([z + dz] if z > zm else list(range(zm, zm + dz + 1)))
        for nx in xs:
            for nz in zs:
                nuevas[(nx, y, nz)] = ident
    if len(nuevas) > MAX_BLOQUES_PLANO:
        return None, f"el plano estirado tendría {len(nuevas)} bloques (máximo {MAX_BLOQUES_PLANO})"
    nombre = str((plano or {}).get("blueprint_name") or "plano")
    return _plano_desde_celdas(nuevas, nombre), None


def celda_transitable_cercana(mapa, x, z, radio=4, permitir_agua=False):
    """La celda de suelo más cercana a (x, z) dentro del mapa (para empezar un camino donde Cobalt está en el aire o en un árbol)."""
    mejor, mejor_d = None, None
    for dz in range(-radio, radio + 1):
        for dx in range(-radio, radio + 1):
            cx, cz = x + dx, z + dz
            if not mapa.dentro(cx, cz):
                continue
            t = mapa.tipo(cx, cz)
            if t == SUELO or (permitir_agua and t == AGUA):
                d = dx * dx + dz * dz
                if mejor_d is None or d < mejor_d:
                    mejor, mejor_d = (cx, cz), d
    return mejor


def trazar_camino(mapa, inicio, fin, permitir_puentes=True, max_nodos=20000):
    """Camino de (x, z) a (x, z) por el mapa."""
    def transitable(x, z):
        t = mapa.tipo(x, z)
        return t == SUELO or (permitir_puentes and t == AGUA)

    if not (mapa.dentro(*inicio) and mapa.dentro(*fin) and transitable(*inicio) and transitable(*fin)):
        return None
    if inicio == fin:
        return [{"x": inicio[0], "z": inicio[1], "y": mapa.altura(*inicio) + 1, "puente": mapa.tipo(*inicio) == AGUA}]

    def h(p):
        return abs(p[0] - fin[0]) + abs(p[1] - fin[1])

    abiertos = [(h(inicio), 0, 0, inicio)]
    coste = {inicio: 0}
    padre = {}
    contador = 0
    expandidos = 0
    while abiertos and expandidos < max_nodos:
        _, g, _, actual = heapq.heappop(abiertos)
        if g > coste.get(actual, float("inf")):
            continue
        if actual == fin:
            ruta = [actual]
            while ruta[-1] in padre:
                ruta.append(padre[ruta[-1]])
            ruta.reverse()
            return [{"x": x, "z": z, "y": mapa.altura(x, z) + 1, "puente": mapa.tipo(x, z) == AGUA} for x, z in ruta]
        expandidos += 1
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            v = (actual[0] + dx, actual[1] + dz)
            if not mapa.dentro(*v) or not transitable(*v):
                continue
            desnivel = abs(mapa.altura(*v) - mapa.altura(*actual))
            if desnivel > 1:
                continue
            paso = 1 + 2 * desnivel + (3 if mapa.tipo(*v) == AGUA else 0)
            ng = g + paso
            if ng < coste.get(v, float("inf")):
                coste[v] = ng
                padre[v] = actual
                contador += 1
                heapq.heappush(abiertos, (ng + h(v), ng, contador, v))
    return None


def ensanchar_camino(mapa, camino, ancho):
    """Camino de ancho 1 -> ancho 3: añade las celdas LATERALES de cada tramo (perpendiculares a la dirección de marcha; en una esquina, las de"""
    if ancho < 3 or not camino:
        return list(camino)
    ocupadas = {(c["x"], c["z"]) for c in camino}
    extra = []
    for i, c in enumerate(camino):
        direcciones = set()
        for j in (i - 1, i + 1):
            if 0 <= j < len(camino):
                direcciones.add((camino[j]["x"] - c["x"], camino[j]["z"] - c["z"]))
        for dx, dz in direcciones:
            for lx, lz in ((-dz, dx), (dz, -dx)):
                p = (c["x"] + lx, c["z"] + lz)
                if p in ocupadas or not mapa.dentro(*p):
                    continue
                t = mapa.tipo(*p)
                if t != SUELO and not (t == AGUA and c["puente"]):
                    continue
                if abs(mapa.altura(*p) + 1 - c["y"]) > 1:
                    continue
                ocupadas.add(p)
                extra.append({"x": p[0], "z": p[1], "y": mapa.altura(*p) + 1, "puente": t == AGUA})
    return list(camino) + extra


def camino_a_blueprint(camino, bloque="minecraft:cobblestone", bloque_puente="minecraft:oak_planks", nombre="camino"):
    """(plano, origen) donde origen = (x, y, z) del mundo que corresponde a la esquina mínima del plano; (None, motivo) si no cabe."""
    if not camino:
        return None, "el camino está vacío"
    if len(camino) > MAX_BLOQUES_PLANO:
        return None, f"el camino tiene {len(camino)} bloques (máximo {MAX_BLOQUES_PLANO})"
    ox, oy, oz = min(c["x"] for c in camino), min(c["y"] for c in camino), min(c["z"] for c in camino)
    celdas = {}
    for c in camino:
        celdas[(c["x"] - ox, c["y"] - oy, c["z"] - oz)] = _id_completo(bloque_puente if c["puente"] else bloque)
    return _plano_desde_celdas(celdas, nombre), (ox, oy, oz)


def dividir_caja(caja, max_volumen=MAX_VOLUMEN_ESCANEO):
    """Parte una caja (x1,y1,z1,x2,y2,z2) en cajas de <= max_volumen celdas cortando siempre por el eje más largo."""
    x1, y1, z1, x2, y2, z2 = caja
    x1, x2, y1, y2, z1, z2 = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2), min(z1, z2), max(z1, z2)
    lados = [x2 - x1 + 1, y2 - y1 + 1, z2 - z1 + 1]
    if lados[0] * lados[1] * lados[2] <= max_volumen:
        return [(x1, y1, z1, x2, y2, z2)]
    eje = lados.index(max(lados))
    if eje == 0:
        m = (x1 + x2) // 2
        return dividir_caja((x1, y1, z1, m, y2, z2), max_volumen) + dividir_caja((m + 1, y1, z1, x2, y2, z2), max_volumen)
    if eje == 1:
        m = (y1 + y2) // 2
        return dividir_caja((x1, y1, z1, x2, m, z2), max_volumen) + dividir_caja((x1, m + 1, z1, x2, y2, z2), max_volumen)
    m = (z1 + z2) // 2
    return dividir_caja((x1, y1, z1, x2, y2, m), max_volumen) + dividir_caja((x1, y1, m + 1, x2, y2, z2), max_volumen)


def unir_escaneos(escaneos):
    """Junta varios scan_blocks.json en (mundo {(x,y,z): id}, celdas_sin_cargar, truncado)."""
    mundo, sin_cargar, truncado = {}, 0, False
    for e in escaneos:
        try:
            if not isinstance(e, dict) or e.get("status") != "success":
                return None
            paleta = e["palette"]
            x0, y0, z0 = int(e["x0"]), int(e["y0"]), int(e["z0"])
            for dx, dy, dz, idx in e["blocks"]:
                mundo[(x0 + dx, y0 + dy, z0 + dz)] = _id_completo(paleta[idx])
            sin_cargar += int(e.get("unloaded", 0))
            truncado = truncado or bool(e.get("truncated", False))
        except (KeyError, TypeError, ValueError, IndexError):
            return None
    return mundo, sin_cargar, truncado


def _no_copiable(ident):
    ruta = _ruta_id(ident)
    return ruta in NO_COPIAR or any(f in ruta for f in NO_COPIAR_FRAGMENTOS)


def escaneo_a_blueprint(mundo, nombre="copia"):
    """Convierte lo escaneado en un plano. Devuelve (plano, informe) o (None, motivo)."""
    omitidos = {}
    celdas = {}
    for pos, ident in mundo.items():
        if _no_copiable(ident):
            r = _ruta_id(ident)
            omitidos[r] = omitidos.get(r, 0) + 1
        else:
            celdas[pos] = ident
    if not celdas:
        return None, "no hay bloques copiables en esa zona"
    if len(celdas) > MAX_BLOQUES_PLANO:
        return None, f"la estructura tiene {len(celdas)} bloques (máximo {MAX_BLOQUES_PLANO})"
    ox, oy, oz = min(p[0] for p in celdas), min(p[1] for p in celdas), min(p[2] for p in celdas)
    relativas = {(x - ox, y - oy, z - oz): i for (x, y, z), i in celdas.items()}
    plano = _plano_desde_celdas(relativas, nombre)
    return plano, {"copiados": len(celdas), "omitidos": omitidos, "origen": (ox, oy, oz)}


def diferencias(plano, origen, mundo):
    """Compara un plano colocado en 'origen' con lo que hay en el mundo (dict de un escaneo)."""
    ox, oy, oz = origen
    bien, faltan, distintos = 0, [], []
    for capa in plano.get("layers", []):
        for b in capa.get("blocks", []):
            pos = (ox + b["x"], oy + capa["y"], oz + b["z"])
            esperado = _id_completo(b["block"])
            actual = mundo.get(pos)
            if actual is None:
                faltan.append((pos[0], pos[1], pos[2], esperado))
            elif actual == esperado:
                bien += 1
            else:
                distintos.append((pos[0], pos[1], pos[2], esperado, actual))
    return {"bien": bien, "faltan": faltan, "distintos": distintos}


def reparacion_a_blueprint(faltan, nombre="reparacion"):
    """(plano, origen) con solo los bloques que faltan, o (None, motivo) si no hay ninguno."""
    if not faltan:
        return None, "no falta ningún bloque"
    ox, oy, oz = min(f[0] for f in faltan), min(f[1] for f in faltan), min(f[2] for f in faltan)
    celdas = {(x - ox, y - oy, z - oz): ident for x, y, z, ident in faltan}
    return _plano_desde_celdas(celdas, nombre), (ox, oy, oz)


def caja_de_obra(plano, origen):
    """Caja (x1,y1,z1,x2,y2,z2) que ocupa un plano colocado en 'origen', o None si está vacío."""
    ancho, alto, largo = dimensiones_de_plano(plano)
    if ancho == 0:
        return None
    ox, oy, oz = origen
    xs, ys, zs = [], [], []
    for capa in plano.get("layers", []):
        for b in capa.get("blocks", []):
            xs.append(b["x"])
            ys.append(capa["y"])
            zs.append(b["z"])
    return (ox + min(xs), oy + min(ys), oz + min(zs), ox + max(xs), oy + max(ys), oz + max(zs))


def registrar_obra(obras, nombre, plano, origen, dimension, ahora):
    """Devuelve una COPIA del registro con la obra añadida (o actualizada)."""
    nuevo = dict(obras or {})
    nuevo[nombre] = {"plano": plano, "x": int(origen[0]), "y": int(origen[1]), "z": int(origen[2]), "dimension": dimension or "", "t": float(ahora)}
    return nuevo


def buscar_obra(obras, texto):
    """(nombre, datos) de la obra que se nombra ('' = la más reciente); (None, None) si no hay ninguna que encaje."""
    if not obras:
        return None, None
    t = re.sub(r"[^a-z0-9]+", "_", _sin_acentos(texto)).strip("_")
    if not t:
        nombre = max(obras, key=lambda k: obras[k].get("t", 0))
        return nombre, obras[nombre]
    if t in obras:
        return t, obras[t]
    palabras = {w for w in t.split("_") if w and w not in _ARTICULOS}
    candidatas = []
    for nombre in obras:
        del_nombre = set(nombre.split("_"))
        if palabras and (palabras <= del_nombre or del_nombre <= palabras):  # 'la casa' -> casa_azul; 'la casa azul de piedra' -> casa_azul
            candidatas.append(nombre)
    if not candidatas:
        return None, None
    nombre = max(candidatas, key=lambda k: obras[k].get("t", 0))
    return nombre, obras[nombre]


def _dimension_corta(dimension):
    d = _sin_acentos(dimension)
    if "nether" in d:
        return "nether"
    if "end" in d:
        return "end"
    if "overworld" in d or d == "":
        return "overworld"
    return "otra"


def coordenadas_portal(x, z, dimension):
    """Conversión 8:1: del Overworld al Nether se DIVIDE entre 8, del Nether al Overworld se MULTIPLICA por 8. None en el End o dimensiones ajenas."""
    dim = _dimension_corta(dimension)
    if dim == "overworld":
        return {"dimension_destino": "nether", "x": math.floor(x / 8.0), "z": math.floor(z / 8.0), "radio_busqueda": 16}
    if dim == "nether":
        return {"dimension_destino": "overworld", "x": int(x) * 8, "z": int(z) * 8, "radio_busqueda": 128}
    return None


def texto_portal(x, z, dimension, nombre=""):
    conv = coordenadas_portal(x, z, dimension)
    donde = f" ({nombre})" if nombre else ""
    if conv is None:
        return "Los portales del Nether solo se enlazan entre el Overworld y el Nether; desde esta dimensión no puedo calcular nada."
    origen = "Overworld" if conv["dimension_destino"] == "nether" else "Nether"
    destino = "Nether" if conv["dimension_destino"] == "nether" else "Overworld"
    return (f"El punto X={int(x)}, Z={int(z)}{donde} del {origen} corresponde a X={conv['x']}, Z={conv['z']} en el {destino} (proporción 8:1). "
            f"Pon el portal lo más cerca posible de ahí: el juego enlaza con un portal existente a menos de {conv['radio_busqueda']} bloques del punto convertido, "
            f"y si no hay ninguno crea uno nuevo. La altura no se convierte: elige la Y que quieras.")


_VERBOS_REPARAR = r"(?:repara|reparar|restaura|restaurar|arregla|arreglar|revisa|revisar)"
_PALABRAS_OBRA = r"(?:obra|muro|muros|casa|estructura|construccion|torre|edificio|puente|camino|pared|paredes)"


_ARTICULOS_DE_NOMBRE = {"el", "la", "los", "las", "un", "una", "unos", "unas"}


def _nombre_limpio(texto, quitar=_ARTICULOS_INICIALES):
    tokens = re.findall(r"[a-z0-9]+", _sin_acentos(texto))
    while tokens and tokens[0] in quitar:
        tokens.pop(0)
    return "_".join(tokens)[:32]


def _limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, int(valor)))


def interpretar_obra(mensaje, obras_conocidas=()):
    """Intención de obra del chat -> dict con 'tipo', o None."""
    m = _sin_acentos(mensaje).strip()
    if not m:
        return None

    if re.search(r"\b(?:copia|copiar|escanea|escanear|replica|replicar|clona|clonar|guarda|guardar)\b", m) and re.search(r"\bcomo\s+[a-z0-9_]", m):
        nombre = _nombre_limpio(m.rsplit(" como ", 1)[-1], _ARTICULOS_DE_NOMBRE)  # el nombre que se pone: 'mi_torre' se queda como está
        cuerpo = m.rsplit(" como ", 1)[0]
        numeros = re.findall(r"-?\d+", cuerpo)
        if nombre and len(numeros) == 6:
            n = [int(v) for v in numeros]
            return {"tipo": "copiar", "caja": tuple(n), "nombre": nombre}
        entre = re.search(r"\bentre\s+(.+?)\s+y\s+(.+)$", cuerpo)
        if nombre and entre:
            return {"tipo": "copiar", "waypoints": (_nombre_limpio(entre.group(1)), _nombre_limpio(entre.group(2))), "nombre": nombre}

    # portales: "¿dónde pongo el portal del nether para la base?"
    if re.search(r"\bportal(?:es)?\b", m) and re.search(r"\b(?:nether|inframundo|overworld|superficie)\b", m) \
            and re.search(r"\b(?:donde|coordenadas|enlaza|enlazar|sincroniza|sincronizar|conversion|convierte|8)\b", m):
        destino = re.search(r"\bpara\s+(.+)$", m)
        return {"tipo": "portal", "destino": _nombre_limpio(destino.group(1)) if destino else ""}

    # reparar una obra construida
    if re.search(r"\b" + _VERBOS_REPARAR + r"\b", m):
        conocida = None
        for nombre in obras_conocidas:
            if nombre and nombre.replace("_", " ") in m.replace("_", " "):
                conocida = nombre
                break
        if conocida or re.search(r"\b" + _PALABRAS_OBRA + r"\b", m):
            return {"tipo": "reparar", "obra": conocida or ""}

    # construir en un sitio llano
    if re.search(r"\b(?:construye|edifica|levanta)\b", m) and re.search(r"\b(?:sitio|lugar|terreno|zona|parcela)\s+(?:plano|llano|nivelado|adecuado|libre)\b", m):
        plano = re.search(r"\b(?:construye|edifica|levanta)\s+(.+?)\s+(?:en|sobre)\s+(?:un|el|la)?\s*(?:mejor\s+)?(?:sitio|lugar|terreno|zona|parcela)", m)
        return _sitio(plano.group(1) if plano else "", m)
    plano = re.search(r"\b(?:busca|encuentra|halla|elige)\s+(?:un\s+|el\s+)?(?:mejor\s+)?(?:sitio|lugar|terreno|zona|parcela)\s+(?:plano|llano|nivelado|adecuado)\s+para\s+(.+)$", m)
    if plano:
        return _sitio(plano.group(1), m)

    # camino / puente hasta un lugar
    if re.search(r"\b(?:traza|trazar|haz|hacer|construye|pon|abre|tiende|crea)\b", m) and re.search(r"\b(?:camino|carretera|senda|puente)\b", m):
        destino = re.search(r"\b(?:hasta|hacia|a|al)\s+(?:el\s+|la\s+)?(.+)$", m.split(" camino ", 1)[-1] if " camino " in m else m)
        if destino:
            texto = re.sub(r"\b(?:de\s+)?(?:3|tres)\s+(?:bloques\s+)?de\s+ancho\b|\bancho\b|\bancha\b", " ", destino.group(1))
            nombre = _nombre_limpio(texto)
            if nombre:
                ancho = 3 if re.search(r"\b(?:ancho|ancha|3 de ancho|tres de ancho)\b", m) else 1
                return {"tipo": "camino", "destino": nombre, "ancho": ancho}

    # aplanar
    if re.search(r"\b(?:aplana|aplanar|nivela|nivelar|allana|allanar)\b", m):
        dim = re.search(r"(\d+)\s*(?:x|por|\*)\s*(\d+)", m)
        if dim:
            ancho, largo = _limitar(dim.group(1), 2, 64), _limitar(dim.group(2), 2, 64)
        else:
            lado = re.search(r"(\d+)\s*(?:bloques?)?", m)
            ancho = largo = _limitar(lado.group(1), 2, 64) if lado else 9
        return {"tipo": "aplanar", "ancho": ancho, "largo": largo}

    # rellenar lava / agua
    if re.search(r"\b(?:rellena|rellenar|tapa|tapar|sella|sellar|purga|purgar|apaga|apagar|cubre|cubrir)\b", m) and re.search(r"\b(?:lava|agua)\b", m):
        radio = re.search(r"(\d+)", m)
        return {"tipo": "rellenar", "fluido": "lava" if re.search(r"\blava\b", m) else "water", "radio": _limitar(radio.group(1), 2, 16) if radio else 8}
    return None


def _sitio(texto_plano, m):
    dim = re.search(r"(\d+)\s*(?:x|por|\*)\s*(\d+)", texto_plano) or re.search(r"(\d+)\s*(?:x|por|\*)\s*(\d+)", m)
    sin_dim = re.sub(r"\bde\s+\d+\s*(?:x|por|\*)\s*\d+\b|\d+\s*(?:x|por|\*)\s*\d+", " ", texto_plano)
    nombre = _nombre_limpio(sin_dim)
    if not nombre:
        return None
    r = {"tipo": "sitio", "plano": nombre}
    if dim:
        r["ancho"], r["largo"] = _limitar(dim.group(1), 2, 64), _limitar(dim.group(2), 2, 64)
    return r
