"""F2-5: memoria del JUGADOR. PURO: sin red, sin Minecraft, sin disco (el adaptador de cerebro.py lee y guarda perfil_jugador.json)."""
import re
import unicodedata

import nox_memoria

CATEGORIAS = ("mundo", "hambre", "inventario")   # las silenciables; fuego/aire/hostiles NO
MAX_NOTAS = 40
MAX_CHARS_NOTA = 200
MIN_CHARS_NOTA = 4

_TEMAS = {"hambre": "hambre", "comida": "hambre", "hambriento": "hambre", "inventario": "inventario", "mochila": "inventario", "noche": "mundo", "tormenta": "mundo",
          "tormentas": "mundo", "clima": "mundo", "tiempo": "mundo", "lluvia": "mundo", "anochecer": "mundo", "dia": "mundo", "todos": "todos", "todo": "todos", "todas": "todos"}
_PELIGRO = ("creeper", "creepers", "peligro", "peligros", "hostil", "hostiles", "enemigo", "enemigos", "fuego", "aire", "lava", "trampa", "trampas", "zombi", "zombis", "esqueleto")


def _ascii(t):
    return unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode("ascii").lower()


def _limpiar_mensaje(mensaje):
    t = re.sub(r"\b(?:cobalt|nox)\b", " ", _ascii(mensaje))
    t = re.sub(r"[¿?¡!.,;:]+", " ", t)
    t = re.sub(r"\b(?:por favor|porfa|please)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def saneado(texto, maximo=MAX_CHARS_NOTA):
    """Una nota apta para guardar y meter en un prompt: una línea, sin caracteres de control, llaves, corchetes ni comillas dobles, con tope de largo."""
    t = re.sub(r"[\x00-\x1f\x7f{}\[\]\"`<>\\]", " ", str(texto or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return t[:maximo].strip()


_SILENCIAR = re.compile(r"^(?:avisame menos|no me avises(?: mas)?|dejame de avisos|deja de avisarme|silencia(?:r)? (?:los )?avisos|silencia avisos|no quiero (?:mas )?avisos|callate con los avisos|no me avises nunca mas)(?: (?:de|del|sobre|con)(?: la| el| los| las)? (?P<tema>.+))?$")
_ACTIVAR = re.compile(r"^(?:vuelve a avisarme|avisame de nuevo|avisame otra vez|reactiva(?:r)? (?:los )?avisos|activa(?:r)? (?:los )?avisos|vuelve a avisarme de todo)(?: (?:de|del|sobre|con)(?: la| el| los| las)? (?P<tema>.+))?$")


def interpretar_aviso(mensaje):
    """('silenciar'|'activar', [categorías]) | ('peligro', []) si pide callar los avisos de peligro | None."""
    if not isinstance(mensaje, str) or len(mensaje) > 100:
        return None
    t = _limpiar_mensaje(mensaje)
    for patron, accion in ((_SILENCIAR, "silenciar"), (_ACTIVAR, "activar")):
        m = patron.match(t)
        if not m:
            continue
        tema = (m.group("tema") or "").strip()
        if not tema:
            return accion, list(CATEGORIAS)
        palabras = tema.split()
        if any(p in _PELIGRO for p in palabras):
            return "peligro", []
        cats = []
        for p in palabras:
            c = _TEMAS.get(p)
            if c == "todos":
                return accion, list(CATEGORIAS)
            if c and c not in cats:
                cats.append(c)
        if not cats:
            return None       # un tema que no conozco: mejor no tocar nada que adivinar
        return accion, cats
    return None


_RECUERDA = re.compile(r"^\s*(?:(?:cobalt|nox)\s*[,:]?\s*)?(?:recuerda|acu[eé]rdate|anota|apunta|ten en cuenta)(?:\s+que)?\s+(?P<txt>[^¿?]+?)\s*[.!]*\s*$", re.IGNORECASE)
_LISTA = ("que recuerdas de mi", "que sabes de mi", "que recuerdas", "mis notas", "que has anotado", "que has anotado de mi", "que sabes sobre mi", "que anotaste")
_OLVIDA_N = re.compile(r"^(?:olvida|borra|quita)(?: la)?(?: nota)?(?: numero| n| no)? (?P<n>\d{1,3})$")
_OLVIDA_TODO = ("olvida todo lo que recuerdas de mi", "olvida todo lo que sabes de mi", "borra mis notas", "olvida mis notas", "borra todas mis notas", "olvida todo lo que anotaste")


def interpretar_nota(mensaje):
    """('guardar', texto) | ('listar', None) | ('olvidar', n) | ('olvidar_todo', None) | None."""
    if not isinstance(mensaje, str) or len(mensaje) > 400:
        return None
    m = _RECUERDA.match(mensaje)
    if m:
        txt = saneado(m.group("txt"))
        if len(txt) >= MIN_CHARS_NOTA and len(m.group("txt").strip()) <= 2 * MAX_CHARS_NOTA:
            return "guardar", txt
        return None
    t = _limpiar_mensaje(mensaje)
    if t in _LISTA:
        return "listar", None
    if t in _OLVIDA_TODO:
        return "olvidar_todo", None
    m = _OLVIDA_N.match(t)
    if m:
        return "olvidar", int(m.group("n"))
    return None


class Perfil:
    """{'silenciados': [...categorías], 'notas': [{'t': marca de tiempo, 'texto': str}]}. Todo lo que llega de un archivo se valida al cargar."""

    def __init__(self, silenciados=None, notas=None):
        self.silenciados = set(c for c in (silenciados or []) if c in CATEGORIAS)
        self.notas = []
        for n in notas or []:
            if isinstance(n, dict) and isinstance(n.get("texto"), str):
                texto = saneado(n["texto"])
                if len(texto) >= MIN_CHARS_NOTA:
                    t = n.get("t")
                    self.notas.append({"t": t if isinstance(t, (int, float)) and not isinstance(t, bool) and t == t else 0, "texto": texto})
        self.notas = self.notas[-MAX_NOTAS:]

    @classmethod
    def desde_dict(cls, d):
        return cls(d.get("silenciados"), d.get("notas")) if isinstance(d, dict) and isinstance(d.get("silenciados", []), list) and isinstance(d.get("notas", []), list) else cls()

    def a_dict(self):
        return {"silenciados": sorted(self.silenciados), "notas": [dict(n) for n in self.notas]}

    def silenciar(self, categorias):
        self.silenciados |= set(c for c in categorias if c in CATEGORIAS)

    def activar(self, categorias):
        self.silenciados -= set(c for c in categorias if isinstance(c, str))

    def agregar_nota(self, texto, ahora, umbral=0.75):
        t = saneado(texto)
        if len(t) < MIN_CHARS_NOTA:
            return False, t
        tk = nox_memoria.tokens(t)
        for n in self.notas:
            if n["texto"].casefold() == t.casefold() or (tk and nox_memoria.jaccard(tk, nox_memoria.tokens(n["texto"])) >= umbral):
                return False, t
        self.notas.append({"t": ahora, "texto": t})
        self.notas = self.notas[-MAX_NOTAS:]
        return True, t

    def olvidar(self, numero):
        if isinstance(numero, bool) or not isinstance(numero, int) or not 1 <= numero <= len(self.notas):
            return None
        return self.notas.pop(numero - 1)["texto"]

    def olvidar_todo(self):
        n = len(self.notas)
        self.notas = []
        return n


def bloque_notas(perfil, consulta="", max_chars=400, k=6):
    """El texto de las notas para el prompt ('' si no hay): primero las más relevantes para 'consulta' y luego las más recientes, hasta k y max_chars, sin cortar una nota a medias."""
    notas = [n["texto"] for n in (perfil.notas if isinstance(perfil, Perfil) else [])]
    if not notas:
        return ""
    elegidas = []
    if str(consulta or "").strip():
        docs = nox_memoria.documentos_de_lecciones(notas)
        for _, d in nox_memoria.Indice(docs).buscar(consulta, k=k, minimo=0.5):
            elegidas.append(d.texto)
    for texto in reversed(notas):
        if texto not in elegidas:
            elegidas.append(texto)
    lineas, usado = [], 0
    for texto in elegidas[:k]:
        linea = "- " + texto
        if usado + len(linea) + 1 > max_chars:
            break
        lineas.append(linea)
        usado += len(linea) + 1
    return "\n".join(lineas)


def texto_notas(perfil, max_chars=220):
    """Las notas numeradas para el chat, sin pasarse del largo ('' si no hay)."""
    partes, usado = [], 0
    for i, n in enumerate(perfil.notas, 1):
        p = f"{i}) {n['texto']}"
        if usado + len(p) + 2 > max_chars:
            partes.append(f"y {len(perfil.notas) - i + 1} más")
            break
        partes.append(p)
        usado += len(p) + 2
    return "; ".join(partes)
