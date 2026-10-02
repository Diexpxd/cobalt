"""H2 (misión autónoma): memoria que se USA. PURO: sin red, sin Minecraft, sin disco (el adaptador de cerebro.py lee y escribe los archivos)."""
import math
import re
import unicodedata
from collections import Counter, namedtuple

STOPWORDS = frozenset("""
de la que el en y a los del se las por un para con no una su al lo como mas pero sus le ya o este si porque esta entre cuando muy sin sobre tambien me hasta hay
donde quien desde todo nos durante todos uno les ni contra otros ese eso ante ellos e esto antes algunos unos yo otro otras otra el tanto esa estos mucho quienes
nada muchos cual poco ella estar estas algunas algo nosotros mi mis tu te ti tus ellas os es son ser fue era hacer haces hace cuales dime dame puedes puedo quiero
necesito cobalt hola gracias favor explica cuentame sabes saber tienes tengo vamos ahora aqui alli bien mal cosa cosas
""".split())

_BASURA = re.compile(
    r"\blo siento\b|\bno puedo (proporcionar|ayudar|generar|resumir|responder|crear|acceder|confirmar)\b|\bno tengo acceso\b|\bsin acceso a internet\b|\bno hay conexion\b"
    r"|\bcomo (una )?(ia|inteligencia artificial|modelo de lenguaje)\b|\bno se (proporcion\w*|ha proporcionado|encontr\w*|pudo|puede)\b|\bno (hay|existe|contiene|incluye) (informacion|datos|detalles|ningun)\b"
    r"|\bno (pude|logre|consegui) (encontrar|obtener|resumir|generar)\b|\bel texto (que )?(me )?(proporcionaste|diste|has dado|proporcionado)\b|\bno encontre\b"
    r"|\bsin (informacion|datos) (suficiente|clara)\b|\bno fue posible\b")

Documento = namedtuple("Documento", "clave tema texto tokens peso orden")


def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return t.lower()


def _raiz(p):
    if p.endswith("ciones") and len(p) > 8:
        return p[:-6] + "cion"
    if len(p) > 5 and p.endswith("es"):
        return p[:-2]
    if len(p) > 3 and p.endswith("s"):
        return p[:-1]
    return p


def tokens(texto):
    """Palabras significativas normalizadas: sin acentos, sin palabras vacías, sin plurales."""
    salida = []
    for p in re.findall(r"[a-z0-9]+", normalizar(texto)):
        if p in STOPWORDS or (len(p) < 3 and not any(c.isdigit() for c in p)):
            continue
        salida.append(_raiz(p))
    return salida


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a and b else 0.0


def es_basura(texto):
    """¿Esto es una disculpa/negativa/relleno de un modelo (o algo demasiado corto o largo) y no un dato aprendido?"""
    if not isinstance(texto, str):
        return True
    t = texto.strip()
    if not 40 <= len(t) <= 900:
        return True
    return bool(_BASURA.search(normalizar(t)))


def documentos_de_estudio(conocimiento, max_por_tema=2):
    """{fecha: {'tema','resumen'}} -> documentos sin basura y sin repetidos: por cada tema, hasta 'max_por_tema' resúmenes DISTINTOS, los más recientes primero."""
    if not isinstance(conocimiento, dict):
        return []
    por_tema = {}
    for fecha in sorted(conocimiento, reverse=True):  # más recientes primero
        v = conocimiento[fecha]
        if not isinstance(v, dict):
            continue
        tema, resumen = str(v.get("tema", "")).strip(), str(v.get("resumen", "")).strip()
        if not tema or es_basura(resumen):
            continue
        tk = tokens(resumen)
        elegidos = por_tema.setdefault(tema, [])
        if len(elegidos) >= max_por_tema or any(jaccard(tk, e[2]) >= 0.6 for e in elegidos):
            continue
        elegidos.append((fecha, resumen, tk))
    docs, orden = [], 0
    for tema, elegidos in por_tema.items():
        for fecha, resumen, tk in elegidos:
            orden += 1
            docs.append(Documento(f"estudio:{tema}:{fecha}", tema, resumen, tuple(tokens(tema) + tk), 0.9, orden))
    return docs


def documentos_de_lecciones(lecciones):
    docs = []
    for i, texto in enumerate(lecciones or []):
        if isinstance(texto, str) and texto.strip():
            docs.append(Documento(f"leccion:{i}", "", texto.strip(), tuple(tokens(texto)), 1.0, i))
    return docs


class Indice:
    def __init__(self, documentos, k1=1.2, b=0.5):
        self.docs, self.k1, self.b = list(documentos), k1, b
        self.n = len(self.docs)
        self.df = Counter(t for d in self.docs for t in set(d.tokens))
        self.largo_medio = (sum(len(d.tokens) for d in self.docs) / self.n) if self.n else 1.0
        self.frecuencias = [Counter(d.tokens) for d in self.docs]

    def idf(self, t):
        return math.log(1 + (self.n - self.df.get(t, 0) + 0.5) / (self.df.get(t, 0) + 0.5))

    def idf_max(self):
        return math.log(1 + (self.n + 0.5) / 1.5)

    def buscar(self, consulta, k=3, minimo=1.0):
        q = set(tokens(consulta))
        if not q or not self.n:
            return []
        resultados = []
        for d, tf in zip(self.docs, self.frecuencias):
            puntos, coincidencias = 0.0, 0
            for t in q:
                f = tf.get(t, 0)
                if not f:
                    continue
                coincidencias += 1
                norm = f + self.k1 * (1 - self.b + self.b * len(d.tokens) / self.largo_medio)
                puntos += self.idf(t) * (f * (self.k1 + 1)) / norm
            if coincidencias:
                resultados.append((puntos * d.peso * (1 + 0.05 * d.orden / max(1, self.n)), d))
        resultados.sort(key=lambda x: -x[0])
        umbral = minimo * self.idf_max()
        return [(p, d) for p, d in resultados[:k] if p >= umbral]


def bloque_conocimiento(consulta, conocimiento, lecciones=None, max_chars=600, k=3, minimo=1.0):
    """Texto con los recuerdos más relevantes para 'consulta' (viñetas cortas), o '' si no hay ninguno relevante."""
    docs = documentos_de_estudio(conocimiento) + documentos_de_lecciones(lecciones)
    lineas, usado = [], 0
    for _, d in Indice(docs).buscar(consulta, k=k, minimo=minimo):
        cuerpo = d.texto if len(d.texto) <= 300 else d.texto[:297].rsplit(" ", 1)[0] + "..."
        linea = "- " + (f"[{d.tema[:40]}] " if d.tema else "") + cuerpo
        if usado + len(linea) + 1 > max_chars:
            break
        lineas.append(linea)
        usado += len(linea) + 1
    return "\n".join(lineas)


def priorizar_lecciones(lecciones, consulta, minimo=0.5):
    """Devuelve las mismas lecciones con las RELEVANTES para 'consulta' al final (el recorte por presupuesto conserva el final) y el resto delante,"""
    lista = [x for x in (lecciones or []) if isinstance(x, str) and x.strip()]
    if not lista or not str(consulta or "").strip():
        return lista
    relevantes = {d.orden for _, d in Indice(documentos_de_lecciones(lista)).buscar(consulta, k=len(lista), minimo=minimo)}
    if not relevantes:
        return lista
    return [x for i, x in enumerate(lista) if i not in relevantes] + [x for i, x in enumerate(lista) if i in relevantes]


def guardar_estudio(conocimiento, tema, resumen, fecha, max_por_tema=5, max_total=300, umbral_repetido=0.6):
    """Añade lo estudiado."""
    nuevo = dict(conocimiento or {})
    if es_basura(resumen) or not str(tema or "").strip():
        return nuevo, "descartado"
    tk = tokens(resumen)
    accion = "guardado"
    for f, v in list(nuevo.items()):
        if isinstance(v, dict) and v.get("tema") == tema and jaccard(tk, tokens(v.get("resumen", ""))) >= umbral_repetido:
            del nuevo[f]  # el resumen nuevo sustituye al casi idéntico (queda con la fecha de hoy)
            accion = "reemplazado"
    clave, n = fecha, 1
    while clave in nuevo:
        n += 1
        clave = f"{fecha} #{n}"
    nuevo[clave] = {"tema": tema, "resumen": str(resumen).strip()}
    mismos = sorted(f for f, v in nuevo.items() if isinstance(v, dict) and v.get("tema") == tema)
    for f in mismos[:-max_por_tema]:
        del nuevo[f]
    for f in sorted(nuevo)[:-max_total] if len(nuevo) > max_total else []:
        del nuevo[f]
    return nuevo, accion


def agregar_leccion(lecciones, nueva, umbral=0.75, maximo=200):
    """(lista_nueva, agregada)."""
    lista = [x for x in (lecciones or []) if isinstance(x, str)]
    texto = str(nueva or "").strip()
    if not texto:
        return lista, False
    tk = tokens(texto)
    if any(x.strip().casefold() == texto.casefold() or (tk and jaccard(tk, tokens(x)) >= umbral) for x in lista):
        return lista, False
    lista.append(texto)
    return lista[-maximo:], True
