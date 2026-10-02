"""nox_contexto.py: presupuesto de contexto del LLM y detector de bucles (el "muro de la memoria")."""
import math
import threading
import time
from collections import deque

from nox_pro import _numero, orden

CARACTERES_POR_TOKEN = 3.0   # estimación prudente para español + JSON (el real ronda 3-4)


def estimar_tokens(texto):
    return int(math.ceil(len(str(texto or "")) / CARACTERES_POR_TOKEN))


def limitar_texto(texto, max_chars, marca="…"):
    """Recorta a 'max_chars' (incluida la marca), preferiblemente en un límite de palabra o de campo ('|')."""
    t = str(texto if texto is not None else "")
    if max_chars <= 0:
        return ""
    if len(t) <= max_chars:
        return t
    if max_chars <= len(marca):
        return marca[:max_chars]
    corte = t[:max_chars - len(marca)]
    for sep in (" | ", ". ", "; ", ", ", " "):
        i = corte.rfind(sep)
        if i >= int(len(corte) * 0.6):
            corte = corte[:i]
            break
    return corte.rstrip() + marca


def repartir(largos, pesos, total):
    """Reparto de 'total' caracteres entre campos con reparto ponderado y reasignación: los campos que caben en su cuota se quedan enteros y"""
    restante = max(0, int(total))
    activos = {k for k, v in largos.items() if v > 0}
    asignado = {k: 0 for k in largos}
    while activos:
        suma = sum(max(1e-9, pesos.get(k, 1.0)) for k in activos)
        cuota = {k: restante * max(1e-9, pesos.get(k, 1.0)) / suma for k in activos}
        caben = [k for k in activos if largos[k] <= cuota[k]]
        if not caben:
            for k in activos:
                asignado[k] = int(cuota[k])
            break
        for k in caben:
            asignado[k] = largos[k]
            restante -= largos[k]
            activos.discard(k)
    return asignado


def recortar_lecciones(lecciones, max_chars, max_n=12, max_cada=280):
    """Las lecciones más RECIENTES que quepan en 'max_chars' (enteras salvo que una pase de 'max_cada'), sin repetidas, en orden cronológico."""
    elegidas, usado, vistas = [], 0, set()
    for leccion in reversed([str(x).strip() for x in (lecciones or []) if x is not None and str(x).strip()]):
        clave = leccion.casefold()
        if clave in vistas:
            continue
        leccion = limitar_texto(leccion, max_cada)
        coste = len(leccion) + (1 if elegidas else 0)
        if len(elegidas) >= max_n or usado + coste > max_chars:
            break
        vistas.add(clave)
        elegidas.append(leccion)
        usado += coste
    return list(reversed(elegidas))


def _corto(recurso):
    return str(recurso).split(":", 1)[-1]


def resumir_waypoints(waypoints, pos=None, dimension=None, max_n=8, max_chars=700):
    """Los waypoints más útiles: 'base' siempre, luego los más cercanos a 'pos' (los de la dimensión actual antes que los de otras), hasta"""
    validos = {}
    for nombre, c in (waypoints or {}).items() if isinstance(waypoints, dict) else []:
        if isinstance(c, dict) and all(_numero(c.get(k)) for k in ("x", "y", "z")):
            validos[str(nombre)] = c
    if not validos:
        return ""

    def clave(item):
        nombre, c = item
        misma_dim = not dimension or not c.get("dimension") or c.get("dimension") == dimension
        d = math.dist((c["x"], c["y"], c["z"]), pos) if pos and misma_dim else float("inf")
        return (nombre != "base", not misma_dim, d, nombre)

    ordenados = sorted(validos.items(), key=clave)
    entradas = []
    for nombre, c in ordenados[:max_n]:
        e = f"'{nombre}': X={c['x']:g}, Y={c['y']:g}, Z={c['z']:g}"
        if c.get("dimension"):
            e += f" [{_corto(c['dimension'])}]"
        entradas.append(e)
    fuera = len(validos) - len(entradas)
    while entradas and len(" | ".join(entradas)) + (60 if fuera else 0) > max_chars:
        entradas.pop()
        fuera += 1
    texto = " | ".join(entradas)
    if fuera > 0:
        texto += f" (+{fuera} más guardados; el jugador puede pedir 'lugares guardados')"
    return texto


def aplicar_presupuesto(campos, pesos, total, lecciones=None, campo_lecciones="memoria"):
    """Recorta los campos variables del prompt para que quepan en 'total' caracteres."""
    largos = {k: len(str(v or "")) for k, v in campos.items()}
    if lecciones is not None:
        largos[campo_lecciones] = max(largos.get(campo_lecciones, 0), len(" ".join(str(x) for x in lecciones)))
    cuotas = repartir(largos, pesos, total)
    salida, informe = {}, {}
    for k, v in campos.items():
        texto = str(v or "")
        if k == campo_lecciones and lecciones is not None:
            nuevo = " ".join(recortar_lecciones(lecciones, cuotas.get(k, 0)))
        else:
            nuevo = limitar_texto(texto, cuotas.get(k, 0))
        salida[k] = nuevo
        if len(nuevo) != len(texto):
            informe[k] = (len(texto), len(nuevo))
    return salida, informe


class DetectorBucles:
    """Corta a un LLM (o a un jugador desesperado) que repite lo mismo:"""

    EXENTAS = {"halt_all", "resume", "stop", "flush", "recall_drones"}
    CLAVES_FIRMA = ("material", "x", "y", "z", "block", "target_id", "entity_id", "effect", "amount", "radius")

    def __init__(self, maximo=4, ventana_s=60.0, pausa_s=30.0, max_repetidas=3, max_por_respuesta=8):
        self.maximo = maximo
        self.ventana_s = ventana_s
        self.pausa_s = pausa_s
        self.max_repetidas = max_repetidas
        self.max_por_respuesta = max_por_respuesta
        self.historial = {}
        self.bloqueadas = {}
        self.bloqueos_totales = 0
        self._cerrojo = threading.Lock()

    def configurar(self, maximo=None, ventana_s=None, pausa_s=None):
        if maximo is not None:
            self.maximo = max(1, int(maximo))
        if ventana_s is not None:
            self.ventana_s = max(5.0, float(ventana_s))
        if pausa_s is not None:
            self.pausa_s = max(1.0, float(pausa_s))

    @classmethod
    def firma(cls, o):
        accion = str(o.get("action", "")).lower()
        if accion in ("", "ninguna", "none"):
            return ("chat", str(o.get("chat_message", ""))[:120])
        return (accion,) + tuple(str(o.get(k)) for k in cls.CLAVES_FIRMA if k in o)

    @staticmethod
    def describir(firma):
        if firma[0] == "chat":
            return f"el mensaje «{firma[1][:40]}»"
        return " ".join(str(p) for p in firma if p not in ("cualquiera", "1"))[:60]

    def revisar(self, ordenes, ahora=None):
        ahora = time.time() if ahora is None else ahora
        permitidas, avisos = [], []
        with self._cerrojo:
            en_respuesta = {}
            seguidas = {}
            recortadas = 0
            previa = None
            for o in ordenes or []:
                if not isinstance(o, dict):
                    continue
                if str(o.get("action", "")).lower() in self.EXENTAS:
                    permitidas.append(o)
                    previa = None
                    continue
                f = self.firma(o)
                # 1) repeticiones dentro de la misma respuesta
                seguidas[f] = seguidas.get(f, 0) + 1 if f == previa else 1
                previa = f
                en_respuesta[f] = en_respuesta.get(f, 0) + 1
                if seguidas[f] > self.max_repetidas or len(permitidas) >= self.max_por_respuesta:
                    recortadas += 1
                    continue
                # 2) repeticiones entre respuestas
                if self.bloqueadas.get(f, 0.0) > ahora:
                    continue
                h = self.historial.setdefault(f, deque())
                while h and ahora - h[0] > self.ventana_s:
                    h.popleft()
                if len(h) >= self.maximo:
                    self.bloqueadas[f] = ahora + self.pausa_s
                    self.bloqueos_totales += 1
                    h.clear()
                    avisos.append(orden("ninguna", f"Llevo {self.maximo} veces repitiendo {self.describir(f)} en menos de {int(self.ventana_s)} s y no avanzo: "
                                                   f"paro con eso {int(self.pausa_s)} s. Dime qué prefieres que haga."))
                    continue
                h.append(ahora)
                permitidas.append(o)
            if recortadas:
                avisos.append(orden("ninguna", f"Mi respuesta traía {recortadas} órdenes repetidas o de más: me quedo con las primeras."))
        return permitidas, avisos
