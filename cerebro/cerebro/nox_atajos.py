"""Atajos de chat tolerantes (puros, sin dependencias): las órdenes cortas que el jugador escribe de mil maneras."""
import re
import unicodedata

RADIO_RECOGER_DEFECTO = 16
RADIO_RECOGER_MIN, RADIO_RECOGER_MAX = 3, 48


def normalizar(mensaje):
    t = unicodedata.normalize("NFKD", str(mensaje or "")).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[¡!¿?.,;:\"'()]", " ", t)
    t = re.sub(r"\b(por favor|porfa|porfavor|pls|please|oye|ey|cobalt|nox|ya|ahora|anda)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


_DETENER = re.compile(
    r"^(?:stop|detente|detenerte|detengase|para|alto|quedate|quieto|quieta|espera|esperame|frena|paraliza|"
    r"no te muevas|no me sigas|deja de seguirme|deja de acompanarme|no me acompanes)"
    r"(?: (?:ahi|aqui|alli|alla|ahi mismo|aqui mismo|un momento|un segundo|un rato|donde estas|donde estes|tantito|tantito ahi))?$")
_SEGUIR = re.compile(r"^(?:sigueme|seguime|follow me|follow|acompaname|acompanarme|vamos|ven conmigo|sigueme siempre|siguem[eé])$")
_VEN = re.compile(r"^(?:ven|ven aqui|ven aca|ven para aca|ven pa aca|acercate|ven a mi|ven hacia mi|vente|ven rapido)$")


def interpretar_detener(mensaje):
    return bool(_DETENER.match(normalizar(mensaje)))


def interpretar_seguir(mensaje):
    return bool(_SEGUIR.match(normalizar(mensaje)))


def interpretar_ven(mensaje):
    return bool(_VEN.match(normalizar(mensaje)))


_VERBO_RECOGER = re.compile(
    r"^(?:(?:puedes|podrias|quiero que|necesito que|vas a|ve a)\s+)?"
    r"(?P<verbo>recoge|recoger|recogeme|recogelo|recogela|recogelos|recogelas|recolecta|agarra|agarrame|junta|juntame|trae|traeme|traelo|traela|traelos|traelas|alcanzame)"
    r"\s+(?P<resto>.+)$")
# lo que NO es 'recoger del suelo': sacar de un contenedor, cosechar, minar
_NO_ES_SUELO = re.compile(r"\b(cofre|cofres|contenedor|contenedores|barril|barriles|baul|baules|almacen|almacenes|cosecha|cosechas|cultivo|cultivos|hornos?|mena|minerales?)\b")
_ENTREGAR = re.compile(r"\s+(?:y\s+)?(?:damel\w*|dame\w*|entregam\w*|entrega\w*|traemel\w*|pasam\w*|para mi|a mi)\b.*$")
_CLAUSULA = re.compile(r"\s+(?:que\s+(?:tire|deje|solte|cayeron|se cayeron|se cayo|hay|solto|cayo|deje caer|solto)|del suelo|en el suelo|por el suelo|de el suelo|"
                       r"por aqui|aqui cerca|por ahi|cerca|alrededor|que esta|que estan|tirad\w+)\b.*$")
_RADIO = re.compile(r"\s+en\s+(?:un\s+radio\s+de\s+)?(\d{1,3})\s+bloques?\b.*$")
_ARTICULO = re.compile(r"^(?:el|la|los|las|un|una|unos|unas|mi|mis|lo|todo|todos|todas|toda|esas|esos|esa|ese|eso|esta|estos|estas)\s+")
_GENERICO = {"", "cosas", "objetos", "items", "item", "drops", "loot", "lo", "todo", "que tire", "lo que tire", "las cosas", "los objetos", "los items", "cosas tiradas"}


def interpretar_recoger(mensaje):
    t = normalizar(mensaje)
    m = _VERBO_RECOGER.match(t)
    if not m:
        return None
    resto = m.group("resto")
    if _NO_ES_SUELO.search(resto) or resto.startswith("a "):
        return None                                   # sacar de un cofre, cosechar, minar, o 'trae a mi perro'
    verbo = m.group("verbo")
    entregar = verbo.startswith(("trae", "alcanz")) or bool(_ENTREGAR.search(resto)) or verbo.startswith(("recogeme", "agarrame", "juntame"))
    radio = RADIO_RECOGER_DEFECTO
    r = _RADIO.search(resto)
    if r:
        radio = max(RADIO_RECOGER_MIN, min(RADIO_RECOGER_MAX, int(r.group(1))))
        resto = _RADIO.sub("", resto)
    resto = _ENTREGAR.sub("", resto)
    resto = _CLAUSULA.sub("", resto).strip()
    for _ in range(3):
        nuevo = _ARTICULO.sub("", resto).strip()
        if nuevo == resto:
            break
        resto = nuevo
    material = None if resto in _GENERICO or len(resto) < 2 else resto
    return {"material": material, "radio": radio, "entregar": entregar}


_GUARDAR = re.compile(
    r"^(?:(?:puedes|podrias|quiero que)\s+)?(?:deja|dejame|guarda|guardame|mete|metelo|pon|ponlo|almacena|deposita|guarda)\s+"
    r"(?:todo\s+)?(?:(?:el|la|los|las|mi|mis|unos|unas)\s+)?(?P<obj>.+?)\s+(?:en|dentro de|al|a)\s+(?:el|un|algun|ese|este|mi)?\s*"
    r"(?:cofre|barril|baul|contenedor|almacen)(?:\s+.*)?$")
_TODO = {"todo", "todas las cosas", "las cosas", "todo lo que llevas", "lo que llevas", "cosas", "items", "objetos", "los objetos", "todos los items", "eso", "esto"}

CATEGORIAS = {
    "cultivos": ["minecraft:wheat", "minecraft:carrot", "minecraft:potato", "minecraft:beetroot", "minecraft:pumpkin", "minecraft:melon_slice", "minecraft:melon",
                 "minecraft:sweet_berries", "minecraft:glow_berries", "minecraft:nether_wart", "minecraft:cocoa_beans", "minecraft:sugar_cane", "minecraft:poisonous_potato"],
    "semillas": ["seeds", "minecraft:pitcher_pod", "minecraft:torchflower_seeds"],
}
_ALIAS_CATEGORIA = {"cultivo": "cultivos", "cosecha": "cultivos", "cosechas": "cultivos", "verduras": "cultivos", "hortalizas": "cultivos", "semilla": "semillas"}


def interpretar_guardar(mensaje):
    t = normalizar(mensaje)
    m = _GUARDAR.match(t)
    if not m:
        return None
    obj = m.group("obj").strip()
    if obj in _TODO or len(obj) < 2:
        return None                                   # 'guarda todo' es el 'store' de siempre (conserva herramientas y comida)
    clave = _ALIAS_CATEGORIA.get(obj, obj)
    csv = ",".join(CATEGORIAS[clave]) if clave in CATEGORIAS else None
    return {"material": obj, "csv": csv}


_TALAR = re.compile(
    r"^(?:(?:puedes|podrias|quiero que|necesito que|vas a|ve a|ve y)\s+)?"
    r"(?:tala|talar|talame|talanos|corta|cortar|cortame|derriba|derribar|tumba|tumbar|consigue|conseguir|consigueme|obten|obtener)"
    r"(?:\s+(?P<resto>.+))?$")
_MADERA = re.compile(r"\b(arbol|arboles|tronco|troncos|madera|lena|maderas)\b")
_NO_ES_TALAR = re.compile(r"\b(cofre|cofres|baul|baules|barril|barriles|contenedor|almacen|tabla|tablas|tablones|planks|hornos?|craftea\w*|fabrica\w*|hace\w*|palos?)\b")
_ARBOLES = re.compile(r"\barbol(?:es)?\b")
_NUMERO = re.compile(r"\b(\d{1,3})\b")
_RADIO_TALA = re.compile(r"\ben\s+(?:un\s+radio\s+de\s+)?(\d{1,3})\s+bloques?\b")
TALA_MADERA_DEFECTO, TALA_ARBOL = 32, 8
TALA_MAX = 256
RADIO_TALA_DEFECTO, RADIO_TALA_MIN, RADIO_TALA_MAX = 16, 4, 32


def interpretar_talar(mensaje):
    """'tala un árbol', 'corta 20 troncos', 'consigue madera', 'tala árboles en 25 bloques' -> {"cantidad": troncos, "radio": int}; None si no es talar (o pide otra cosa: tablas, madera de un cofre)."""
    t = normalizar(mensaje)
    m = _TALAR.match(t)
    if not m:
        return None
    resto = m.group("resto") or ""
    verbo = t[:m.start("resto")] if m.group("resto") else t
    if resto:
        if not _MADERA.search(resto) or _NO_ES_TALAR.search(resto):
            return None                                   # 'corta el pelo', 'consigue diamantes', 'consigue madera del cofre'
    elif not re.search(r"\btalar?\b|\btalame\b", verbo):
        return None                                       # 'corta', 'consigue' a secas: no se sabe qué
    radio = RADIO_TALA_DEFECTO
    r = _RADIO_TALA.search(resto)
    if r:
        radio = max(RADIO_TALA_MIN, min(RADIO_TALA_MAX, int(r.group(1))))
        resto = _RADIO_TALA.sub(" ", resto)
    n = _NUMERO.search(resto)
    pide_arboles = bool(_ARBOLES.search(resto))
    if n:
        cantidad = int(n.group(1)) * (TALA_ARBOL if pide_arboles else 1)
    elif pide_arboles and not re.search(r"\barboles\b", resto):
        cantidad = TALA_ARBOL                             # 'un árbol'
    elif re.search(r"\b(?:un|una)\s+tronco\b", resto):
        cantidad = 1                                      # 'un tronco'
    else:
        cantidad = TALA_MADERA_DEFECTO
    return {"cantidad": max(1, min(TALA_MAX, cantidad)), "radio": radio}


_PESCAR = re.compile(
    r"^(?:(?:puedes|podrias|quiero que|necesito que|vas a|ve a|ve y|ponte a|vamos a)\s+)?(?:pesca|pescar|pescame|pescanos)(?:\s+(?P<resto>.+))?$")
_PESCA_MINUTOS = re.compile(r"\b(?:durante|por|unos)?\s*(\d{1,3})\s*(?:minutos?|mins?)\b")
_PESCA_RADIO = re.compile(r"\ben\s+(?:un\s+radio\s+de\s+)?(\d{1,3})\s+bloques?\b")
_PESCA_CANTIDAD = re.compile(r"\b(\d{1,3})\s*(?:peces|pescados?|pez|capturas|veces|piezas)?\b")
_PESCA_RELLENO = re.compile(r"\b(?:por favor|unos|unas|algunos|algunas|un|una|los|las|el|la|de|del|al|en|para|mi|mis|peces|pescados?|pez|capturas|veces|piezas|bloques|minutos?|mins?|durante|por|cerca|aqui|ahi|un rato|rato|mucho|poco|tranquilamente)\b")
PESCA_DEFECTO, PESCA_MAX = 8, 64
RADIO_PESCA_DEFECTO, RADIO_PESCA_MIN, RADIO_PESCA_MAX = 16, 4, 32


def interpretar_pescar(mensaje):
    """'pesca', 've a pescar', 'pesca 10 peces', 'pesca durante 5 minutos', 'pesca en 20 bloques' -> {"cantidad", "radio", "minutos"}; None si no es pescar"""
    t = normalizar(mensaje)
    m = _PESCAR.match(t)
    if not m:
        return None
    resto = m.group("resto") or ""
    radio = RADIO_PESCA_DEFECTO
    r = _PESCA_RADIO.search(resto)
    if r:
        radio = max(RADIO_PESCA_MIN, min(RADIO_PESCA_MAX, int(r.group(1))))
        resto = _PESCA_RADIO.sub(" ", resto)
    minutos = 0
    mm = _PESCA_MINUTOS.search(resto)
    if mm:
        minutos = max(1, min(20, int(mm.group(1))))
        resto = _PESCA_MINUTOS.sub(" ", resto)
    cantidad = PESCA_DEFECTO
    n = _PESCA_CANTIDAD.search(resto)
    if n and n.group(1):
        cantidad = max(1, min(PESCA_MAX, int(n.group(1))))
        resto = resto[:n.start()] + " " + resto[n.end():]
    if minutos and not n:
        cantidad = PESCA_MAX                              # 'pesca 5 minutos': hasta que acabe el plazo
    sobra = re.sub(r"\s+", " ", _PESCA_RELLENO.sub(" ", resto)).strip()
    if sobra:
        return None                                       # pide algo más que pescar: que lo entienda el modelo
    return {"cantidad": cantidad, "radio": radio, "minutos": minutos}


_CRAFTEAR = re.compile(
    r"^(?:(?:puedes|podrias|quiero que|necesito que|vas a|ve a|ve y)\s+)?"
    r"(?P<verbo>craftea|craftear|crafteame|crafteate|fabrica|fabricar|fabricame|fabricate|hazme|hazte|haz|crea|creame|preparame)\s+(?P<resto>.+)$")
_CRAFTEO_EXPLICITO = ("craftea", "craftear", "crafteame", "crafteate")
_NUMEROS = {"un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
            "quince": 15, "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50, "docena": 12}
_ID_OBJETO = re.compile(r"\b([a-z0-9_.\-]+:[a-z0-9_./\-]+)")
_CRAFTEO_COLA = re.compile(r"\s+(?:con\s+(?:lo|los|las|el|la)\s+.+|para\s+mi|para\s+ti|usando\s+.+|de\s+mi\s+inventario|en\s+tu\s+inventario|ahora\s+mismo)$")
CRAFTEO_DEFECTO, CRAFTEO_MAX = 1, 256


def interpretar_craftear(mensaje):
    """'craftea 8 antorchas', 'hazme un pico de hierro', 'fabrica 2 hornos' -> {"objeto": 'pico de hierro', "cantidad": int, "explicito": bool}; None si no es eso."""
    t = normalizar(mensaje)
    m = _CRAFTEAR.match(t)
    if not m:
        return None
    resto = _CRAFTEO_COLA.sub("", m.group("resto")).strip()
    cantidad = CRAFTEO_DEFECTO
    n = re.match(r"^(\d{1,3})\s+(?:de\s+)?(.+)$", resto)
    if n:
        cantidad, resto = int(n.group(1)), n.group(2)
    else:
        w = re.match(r"^(media\s+docena|una\s+docena|un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|quince|veinte|treinta|cuarenta|cincuenta)\s+(?:de\s+)?(.+)$", resto)
        if w:
            palabra = w.group(1)
            cantidad = 6 if palabra.startswith("media") else _NUMEROS.get(palabra.split()[-1], 1) if palabra != "una docena" else 12
            resto = w.group(2)
    for _ in range(3):
        nuevo = _ARTICULO.sub("", resto).strip()
        if nuevo == resto:
            break
        resto = nuevo
    if len(resto) < 2 or resto in _GENERICO or resto in ("algo", "cosas", "lo que sea", "un objeto", "objeto"):
        return None
    explicito = m.group("verbo") in _CRAFTEO_EXPLICITO
    ident = _ID_OBJETO.search(str(mensaje).lower())
    if ident:
        resto, explicito = ident.group(1), True
    return {"objeto": resto, "cantidad": max(1, min(CRAFTEO_MAX, cantidad)), "explicito": explicito}


_CARNES_CRUDAS = "minecraft:beef,minecraft:porkchop,minecraft:mutton,minecraft:chicken,minecraft:rabbit"
_CARNES_COCIDAS = "minecraft:cooked_beef,minecraft:cooked_porkchop,minecraft:cooked_mutton,minecraft:cooked_chicken,minecraft:cooked_rabbit"
ITEMS = {
    "carne": _CARNES_CRUDAS + "," + _CARNES_COCIDAS + ",minecraft:rotten_flesh", "carne podrida": "minecraft:rotten_flesh", "carne cruda": _CARNES_CRUDAS,
    "carne cocida": _CARNES_COCIDAS, "filete": "minecraft:beef,minecraft:cooked_beef", "pollo": "minecraft:chicken,minecraft:cooked_chicken",
    "cerdo": "minecraft:porkchop,minecraft:cooked_porkchop", "chuleta": "minecraft:porkchop,minecraft:cooked_porkchop", "cordero": "minecraft:mutton,minecraft:cooked_mutton",
    "semilla": "seeds,minecraft:pitcher_pod,minecraft:torchflower_seeds", "semilla de trigo": "minecraft:wheat_seeds",
    "trigo": "minecraft:wheat", "zanahoria": "minecraft:carrot", "patata": "minecraft:potato", "papa": "minecraft:potato", "remolacha": "minecraft:beetroot",
    "calabaza": "minecraft:pumpkin", "sandia": "minecraft:melon_slice,minecraft:melon", "melon": "minecraft:melon_slice,minecraft:melon",
    "pan": "minecraft:bread", "manzana": "minecraft:apple,minecraft:golden_apple", "huevo": "minecraft:egg", "pescado": "minecraft:cod,minecraft:salmon,minecraft:cooked_cod,minecraft:cooked_salmon",
    "diamante": "minecraft:diamond", "esmeralda": "minecraft:emerald", "oro": "minecraft:raw_gold,minecraft:gold_ingot,minecraft:gold_nugget",
    "hierro": "minecraft:raw_iron,minecraft:iron_ingot,minecraft:iron_nugget", "cobre": "minecraft:raw_copper,minecraft:copper_ingot",
    "carbon": "minecraft:coal,minecraft:charcoal", "redstone": "minecraft:redstone", "lapis": "minecraft:lapis_lazuli", "lapislazuli": "minecraft:lapis_lazuli",
    "cuarzo": "minecraft:quartz", "netherita": "minecraft:netherite_ingot,minecraft:netherite_scrap",
    "palo": "minecraft:stick", "tabla": "planks", "madera": "log", "tronco": "log", "lena": "log", "piedra": "minecraft:cobblestone,minecraft:stone", "adoquin": "minecraft:cobblestone",
    "tierra": "minecraft:dirt", "arena": "minecraft:sand", "grava": "minecraft:gravel", "cuero": "minecraft:leather", "pluma": "minecraft:feather", "hueso": "minecraft:bone",
    "polvora": "minecraft:gunpowder", "hilo": "minecraft:string", "cuerda": "minecraft:string", "ojo de arana": "minecraft:spider_eye", "perla de ender": "minecraft:ender_pearl",
    "flecha": "minecraft:arrow", "antorcha": "minecraft:torch", "bola de slime": "minecraft:slime_ball", "slime": "minecraft:slime_ball", "lana": "wool",
}


_MATERIALES = {"madera": "wooden", "piedra": "stone", "hierro": "iron", "oro": "golden", "diamante": "diamond"}
_HERRAMIENTAS = {"pico": "pickaxe", "hacha": "axe", "pala": "shovel", "azada": "hoe", "espada": "sword"}
_MATERIALES_ARMADURA = {"cuero": "leather", "hierro": "iron", "oro": "golden", "diamante": "diamond", "malla": "chainmail"}
_ARMADURAS = {"casco": "helmet", "peto": "chestplate", "pechera": "chestplate", "pantalones": "leggings", "grebas": "leggings", "botas": "boots"}
for _mes, _men in _MATERIALES.items():
    for _tes, _ten in _HERRAMIENTAS.items():
        ITEMS[f"{_tes} de {_mes}"] = f"minecraft:{_men}_{_ten}"
for _mes, _men in _MATERIALES_ARMADURA.items():
    for _tes, _ten in _ARMADURAS.items():
        ITEMS[f"{_tes} de {_mes}"] = f"minecraft:{_men}_{_ten}"
ITEMS.update({
    "mesa de crafteo": "minecraft:crafting_table", "mesa de trabajo": "minecraft:crafting_table", "horno": "minecraft:furnace", "cofre": "minecraft:chest", "barril": "minecraft:barrel",
    "escalera de mano": "minecraft:ladder", "puerta": "door", "cama": "bed", "arco": "minecraft:bow", "cana de pescar": "minecraft:fishing_rod", "tijeras": "minecraft:shears",
    "cubo": "minecraft:bucket", "escudo": "minecraft:shield", "yunque": "minecraft:anvil", "valla": "fence", "tolva": "minecraft:hopper", "carril": "minecraft:rail",
    "vagoneta": "minecraft:minecart", "bote": "boat", "libro": "minecraft:book", "estanteria": "minecraft:bookshelf", "tablon": "planks", "tablones": "planks",
})


def ids_de(nombre):
    """ids de ítem (separados por coma) para un nombre común en español, o None si no se conoce (entonces decide el traductor con el modelo)."""
    t = normalizar(nombre)
    t = re.sub(r"^(?:el|la|los|las|un|una|unos|unas|mi|mis|de|del)\s+", "", t)
    for clave in (t, re.sub(r"(?:es|s)$", "", t), re.sub(r"s$", "", t), re.sub(r"^(\w+?)(?:es|s)(?= de |$)", r"\1", t)):
        if clave in ITEMS:
            return ITEMS[clave]
    for clave in sorted(ITEMS, key=len, reverse=True):
        if len(clave) >= 5 and re.search(r"\b" + re.escape(clave) + r"s?\b", t):
            return ITEMS[clave]
    return None
