"""Bloque Q3: plantillas de planos hechas por CÓDIGO (sin IA). PURO: sin red ni Minecraft."""
import re
import unicodedata

LADO_MAX = 16
MAX_BLOQUES = 800
TIPOS = ("invernadero", "cabana", "casa", "torre", "faro", "puente", "muro", "piramide", "corral", "refugio")

# (ancho x, alto y, largo z) por defecto de cada tipo
DEFECTOS = {"casa": (7, 5, 7), "cabana": (6, 7, 8), "torre": (5, 12, 5), "faro": (7, 15, 7), "puente": (3, 3, 15), "muro": (3, 6, 15),
            "piramide": (13, 7, 13), "invernadero": (8, 4, 6), "corral": (7, 2, 7), "refugio": (5, 4, 5)}

PALETAS = {
    "mixta": {"muro": "stone_bricks", "esquina": "oak_log", "suelo": "oak_planks", "techo": "oak_planks", "escalera": "oak_stairs", "valla": "oak_fence"},
    "piedra": {"muro": "stone_bricks", "esquina": "stone", "suelo": "cobblestone", "techo": "stone_bricks", "escalera": "stone_brick_stairs", "valla": "stone_brick_wall"},
    "madera": {"muro": "oak_planks", "esquina": "oak_log", "suelo": "spruce_planks", "techo": "spruce_planks", "escalera": "spruce_stairs", "valla": "oak_fence"},
    "arenisca": {"muro": "sandstone", "esquina": "cut_sandstone", "suelo": "smooth_sandstone", "techo": "cut_sandstone", "escalera": "sandstone_stairs", "valla": "sandstone_wall"},
    "ladrillo": {"muro": "bricks", "esquina": "stone_bricks", "suelo": "stone_bricks", "techo": "bricks", "escalera": "brick_stairs", "valla": "brick_wall"},
    "cuarzo": {"muro": "quartz_block", "esquina": "quartz_pillar", "suelo": "smooth_quartz", "techo": "quartz_block", "escalera": "quartz_stairs", "valla": "quartz_slab"},
    "abeto": {"muro": "spruce_planks", "esquina": "spruce_log", "suelo": "dark_oak_planks", "techo": "dark_oak_planks", "escalera": "spruce_stairs", "valla": "spruce_fence"},
}
PALETA_POR_TIPO = {"casa": "mixta", "cabana": "madera", "torre": "piedra", "faro": "piedra", "puente": "piedra", "muro": "piedra", "piramide": "arenisca",
                   "invernadero": "madera", "corral": "madera", "refugio": "madera"}


def _norm(texto):
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return t.lower()


def _tipo(t):
    reglas = [("invernadero", r"invernadero"), ("cabana", r"cabana|choza de troncos"), ("faro", r"\bfaro"), ("torre", r"\btorre|atalaya"),
              ("puente", r"\bpuente|pasarela"), ("muro", r"\bmuro|muralla"), ("piramide", r"piramide"), ("corral", r"corral|establo|\bcerca\b|vallado"),
              ("refugio", r"refugio|cobertizo|choza|\bcasita"), ("casa", r"\bcasa|vivienda|hogar")]
    for tipo, patron in reglas:
        if re.search(patron, t):
            return tipo
    return None


def _paleta(t, tipo):
    if re.search(r"piedra", t) and re.search(r"madera|roble|oak", t):
        return "mixta"
    for nombre, patron in (("arenisca", r"arenisca|sandstone|arena\b"), ("ladrillo", r"ladrillo"), ("cuarzo", r"cuarzo"), ("abeto", r"abeto|pino|spruce"),
                           ("piedra", r"piedra|roca|adoquin"), ("madera", r"madera|roble|oak|tronco")):
        if re.search(patron, t):
            return nombre
    return PALETA_POR_TIPO[tipo]


def analizar_peticion(texto):
    """'una torre de piedra de 5x5 y 12 de alto' -> {'tipo','ancho','alto','largo','paleta'}. None si no encaja en ninguna plantilla."""
    t = _norm(texto)
    tipo = _tipo(t)
    if not tipo:
        return None
    ancho, alto, largo = DEFECTOS[tipo]
    m = re.search(r"(\d+)\s*(?:x|por)\s*(\d+)(?:\s*(?:x|por)\s*(\d+))?", t)
    if m:
        ancho, largo = int(m.group(1)), int(m.group(2))
        if m.group(3):
            alto = int(m.group(3))
    for campo, patron in (("alto", r"(\d+)\s*(?:bloques\s*)?de\s*alt[oa]|alt[oa]\s*(?:de\s*)?(\d+)"), ("largo", r"(\d+)\s*(?:bloques\s*)?de\s*larg[oa]|larg[oa]\s*(?:de\s*)?(\d+)"),
                          ("ancho", r"(\d+)\s*(?:bloques\s*)?de\s*anch[oa]|anch[oa]\s*(?:de\s*)?(\d+)")):
        mm = re.search(patron, t)
        if mm:
            valor = int(mm.group(1) or mm.group(2))
            if campo == "alto":
                alto = valor
            elif campo == "largo":
                largo = valor
            else:
                ancho = valor
    return {"tipo": tipo, "ancho": ancho, "alto": alto, "largo": largo, "paleta": _paleta(t, tipo)}


def _anillo(x0, x1, z0, z1):
    return [(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1) if x in (x0, x1) or z in (z0, z1)]


def _caja_hueca(v, w, l, y_muro_ini, y_muro_fin, pal, y_suelo=0, techo_y=None, ventanas=True):
    for x in range(w):
        for z in range(l):
            v[(x, y_suelo, z)] = pal["suelo"]
            if techo_y is not None:
                v[(x, techo_y, z)] = pal["techo"]
    for y in range(y_muro_ini, y_muro_fin + 1):
        for (x, z) in _anillo(0, w - 1, 0, l - 1):
            esquina = x in (0, w - 1) and z in (0, l - 1)
            v[(x, y, z)] = pal["esquina"] if esquina else pal["muro"]
    if ventanas and y_muro_fin >= y_muro_ini + 1:
        yv = y_muro_ini + 1
        for (x, z) in ((0, l // 2), (w - 1, l // 2), (w // 2, l - 1)):
            v[(x, yv, z)] = "glass_pane"


def _puerta(v, w, y_ini=1):
    for y in (y_ini, y_ini + 1):
        v.pop((w // 2, y, 0), None)


def _casa(w, h, l, pal):
    v = {}
    _caja_hueca(v, w, l, 1, h - 2, pal, techo_y=h - 1)
    _puerta(v, w)
    return v


def _torre(w, h, l, pal):
    v = {}
    _caja_hueca(v, w, l, 1, h - 1, pal, techo_y=None, ventanas=False)
    for (x, z) in _anillo(0, w - 1, 0, l - 1):  # almenas: solo cada dos bloques en la corona
        if (x + z) % 2 == 1:
            v.pop((x, h - 1, z), None)
    for x in range(1, w - 1):
        for z in range(1, l - 1):
            v[(x, h - 3, z)] = pal["suelo"]
    for yv in range(3, h - 4, 4):  # ventanas en las caras laterales
        v[(0, yv, l // 2)] = "glass_pane"
        v[(w - 1, yv, l // 2)] = "glass_pane"
    _puerta(v, w)
    return v


def _faro(w, h, l, pal):
    v = {}
    _caja_hueca(v, w, l, 1, h - 4, pal, techo_y=None, ventanas=False)
    for y in range(4, h - 4, 4):  # bandas de color cada 4 capas
        for (x, z) in _anillo(0, w - 1, 0, l - 1):
            v[(x, y, z)] = "white_concrete"
    cx, cz = w // 2, l // 2
    for y in range(1, h - 3):  # columna central que sostiene la luz
        v[(cx, y, cz)] = pal["esquina"]
    for y in (h - 3, h - 2):  # cuarto de la luz: cristal alrededor
        for (x, z) in _anillo(0, w - 1, 0, l - 1):
            v[(x, y, z)] = "glass"
    v[(cx, h - 3, cz)] = "sea_lantern"
    for x in range(w):
        for z in range(l):
            v[(x, h - 1, z)] = pal["techo"]
    for x in range(1, w - 1):  # el cuarto de la luz apoya en un suelo interior
        for z in range(1, l - 1):
            v[(x, h - 4, z)] = pal["suelo"]
    _puerta(v, w)
    return v


def _puente(w, h, l, pal):
    v = {}
    for x in range(w):
        for z in range(l):
            v[(x, 1, z)] = pal["muro"]
    for z in range(l):
        v[(0, 2, z)] = pal["valla"]
        v[(w - 1, 2, z)] = pal["valla"]
    for z in sorted({0, l // 2, l - 1}):
        v[(w // 2, 0, z)] = pal["suelo"]
    return v


def _muro(w, h, l, pal):
    v = {}
    for y in range(0, h - 2):
        for x in range(w):
            for z in range(l):
                v[(x, y, z)] = pal["muro"]
    for x in range(w):
        for z in range(l):
            v[(x, h - 2, z)] = pal["suelo"]
    for x in sorted({0, w - 1}):  # almenas en ambos bordes del paseo
        for z in range(0, l, 2):
            v[(x, h - 1, z)] = pal["muro"]
    zc = l // 2
    for x in range(w):  # portón central: 2 de ancho por 2 de alto, con dintel
        for z in (zc, zc + 1):
            for y in (1, 2):
                v.pop((x, y, z), None)
    return v


def _piramide(w, h, l, pal):
    v = {}
    capas = (min(w, l) + 1) // 2
    for k in range(capas):
        for x in range(k, w - k):
            for z in range(k, l - k):
                v[(x, k, z)] = pal["muro"] if k % 2 == 0 else pal["esquina"]
    return v


def _invernadero(w, h, l, pal):
    v = {}
    for x in range(w):
        for z in range(l):
            v[(x, 0, z)] = pal["suelo"]
            v[(x, h - 1, z)] = "glass"
    for y in range(1, h - 1):
        for (x, z) in _anillo(0, w - 1, 0, l - 1):
            esquina = x in (0, w - 1) and z in (0, l - 1)
            v[(x, y, z)] = pal["esquina"] if esquina else "glass"
    _puerta(v, w)
    return v


def _corral(w, h, l, pal):
    v = {}
    for (x, z) in _anillo(0, w - 1, 0, l - 1):
        esquina = x in (0, w - 1) and z in (0, l - 1)
        v[(x, 0, z)] = pal["esquina"] if esquina else pal["valla"]
        if esquina:
            v[(x, 1, z)] = pal["esquina"]
    v[(w // 2, 0, 0)] = "oak_fence_gate"
    return v


def _refugio(w, h, l, pal):
    return _casa(w, h, l, pal)


CONSTRUCTORES = {"casa": _casa, "cabana": None, "torre": _torre, "faro": _faro, "puente": _puente, "muro": _muro, "piramide": _piramide,
                 "invernadero": _invernadero, "corral": _corral, "refugio": _refugio}


def _cabana(w, h, l, pal):
    v = {}
    hw = max(3, h - (w // 2 + 1))  # altura de las paredes
    _caja_hueca(v, w, l, 1, hw, pal, techo_y=None)
    _puerta(v, w)
    for k in range(w // 2):
        y = hw + 1 + k
        for z in range(l):
            v[(k, y, z)] = pal["escalera"]
            v[(w - 1 - k, y, z)] = pal["escalera"]
    ycum = hw + 1 + w // 2
    for x in range(w // 2, w - w // 2):
        for z in range(l):
            v[(x, ycum - (1 if w % 2 == 0 else 0), z)] = pal["techo"]
    for z in (0, l - 1):  # hastiales
        for k in range(w // 2):
            for x in range(k + 1, w - 1 - k):
                v[(x, hw + 1 + k, z)] = pal["muro"]
    return v


CONSTRUCTORES["cabana"] = _cabana


def _a_plano(v, nombre):
    capas = {}
    for (x, y, z), b in v.items():
        capas.setdefault(y, []).append({"x": x, "z": z, "block": "minecraft:" + b})
    return {"blueprint_name": nombre, "layers": [{"y": y, "blocks": sorted(bl, key=lambda d: (d["z"], d["x"]))} for y, bl in sorted(capas.items())]}


def construir(tipo, ancho=None, alto=None, largo=None, paleta=None):
    """Plano de la plantilla 'tipo' con esas medidas (recortadas a 3..16 de lado y 16 de alto; si pasa de 800 bloques se encoge)."""
    if tipo not in CONSTRUCTORES:
        return None
    d_w, d_h, d_l = DEFECTOS[tipo]
    w = min(LADO_MAX, max(3, int(ancho or d_w)))
    h = min(LADO_MAX, max(3, int(alto or d_h)))
    l = min(LADO_MAX, max(3, int(largo or d_l)))
    if tipo in ("casa", "refugio", "invernadero"):
        h = max(4, h)
    elif tipo == "torre":
        h = max(6, h)
    elif tipo == "faro":
        h, w, l = max(9, h), max(5, w), max(5, l)
    elif tipo == "muro":
        h = max(5, h)
    elif tipo == "cabana":
        w, h = max(4, w), max(6, h)
    pal = PALETAS.get(paleta or PALETA_POR_TIPO[tipo], PALETAS[PALETA_POR_TIPO[tipo]])
    for _ in range(12):
        v = CONSTRUCTORES[tipo](w, h, l, pal)
        if v and len(v) <= MAX_BLOQUES:
            return _a_plano(v, tipo)
        w, l = max(3, w - 1), max(3, l - 1)  # demasiado grande: se encoge de a un bloque
        if tipo in ("torre", "faro"):
            h = max(6, h - 1)
    return None


def plano_desde_peticion(texto):
    """Petición en español -> plano de plantilla, o None si ninguna plantilla encaja (Cobalt dirá que no puede sin la nube)."""
    p = analizar_peticion(texto)
    if not p:
        return None
    return construir(p["tipo"], p["ancho"], p["alto"], p["largo"], p["paleta"])
