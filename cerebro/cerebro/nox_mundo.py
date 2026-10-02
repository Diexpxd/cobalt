"""H3 (misión autónoma): sentido del mundo. PURO: sin red, sin Minecraft, sin disco."""
import math
from collections import namedtuple

import nox_voz
from nox_pro import orden

TICKS_DIA = 24000
INICIO_ATARDECER = 12000
INICIO_NOCHE = 13000
INICIO_AMANECER = 23000
TICKS_POR_MINUTO = 1200  # 20 ticks/s * 60 s

Mundo = namedtuple("Mundo", "hora lluvia tormenta luz cielo tiene_cielo")


def _entero(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return int(x)


def interpretar(gps):
    """gps.json (dict) -> Mundo, o None si no hay bloque 'mundo' válido."""
    m = gps.get("mundo") if isinstance(gps, dict) else None
    if not isinstance(m, dict):
        return None
    hora = _entero(m.get("day_time"))
    if hora is None:
        return None
    luz = _entero(m.get("light"))
    tormenta = m.get("thundering") is True
    return Mundo(hora % TICKS_DIA, m.get("raining") is True or tormenta, tormenta, None if luz is None else max(0, min(15, luz)),
                 m.get("sky") is True, m.get("has_skylight") is True)


def fase(hora):
    """'dia', 'atardecer', 'noche' o 'amanecer' según el tick del día."""
    h = int(hora) % TICKS_DIA
    if h < INICIO_ATARDECER:
        return "dia"
    if h < INICIO_NOCHE:
        return "atardecer"
    if h < INICIO_AMANECER:
        return "noche"
    return "amanecer"


def ticks_hasta_noche(hora):
    """Ticks que faltan para que empiece la noche; 0 si ya es de noche."""
    h = int(hora) % TICKS_DIA
    if INICIO_NOCHE <= h < INICIO_AMANECER:
        return 0
    return (INICIO_NOCHE - h) % TICKS_DIA


def hora_juego(hora):
    """'HH:MM' del reloj del juego (el tick 0 son las 06:00)."""
    h = int(hora) % TICKS_DIA
    return f"{(h // 1000 + 6) % 24:02d}:{(h % 1000) * 60 // 1000:02d}"


def cuando(ticks):
    """'en menos de un minuto' / 'en aproximadamente un minuto' / 'en unos 2 min' para un plazo en ticks."""
    if ticks < TICKS_POR_MINUTO:
        return "en menos de un minuto"
    minutos = int(ticks / TICKS_POR_MINUTO + 0.5)
    return "en aproximadamente un minuto" if minutos <= 1 else f"en unos {minutos} min"


def describir(mundo):
    """Una frase corta de la situación (para el prompt), o '' si no aplica (sin mundo, o dimensión sin cielo)."""
    if mundo is None or not mundo.tiene_cielo:
        return ""
    f = fase(mundo.hora)
    if f == "dia":
        partes = [f"Es de día ({hora_juego(mundo.hora)}); anochece {cuando(ticks_hasta_noche(mundo.hora))}"]
    elif f == "atardecer":
        partes = [f"Atardece ({hora_juego(mundo.hora)}); la noche empieza {cuando(ticks_hasta_noche(mundo.hora))}"]
    elif f == "noche":
        partes = [f"Es de noche ({hora_juego(mundo.hora)}): aparecen monstruos en superficie"]
    else:
        partes = [f"Amanece ({hora_juego(mundo.hora)})"]
    partes.append("tormenta eléctrica" if mundo.tormenta else "llueve" if mundo.lluvia else "cielo despejado")
    if not mundo.cielo:
        partes.append("estoy bajo techo o bajo tierra")
    if mundo.luz is not None and mundo.luz <= 7:
        partes.append(f"poca luz donde estoy ({mundo.luz}/15): pueden aparecer monstruos")
    return "; ".join(partes) + "."


def resumen(gps):
    """Atajo: gps.json -> frase de situación ('' si no hay datos)."""
    return describir(interpretar(gps))


class AvisosMundo:
    """Avisos proactivos, con enfriamiento y solo en las TRANSICIONES: no repite mientras dura la situación."""
    AVISO_NOCHE_TICKS = 1800
    CD_NOCHE_S = 900.0
    CD_TORMENTA_S = 600.0

    def __init__(self):
        self.vistos = {}
        self.tormenta_previa = None

    def _listo(self, clave, ahora, cooldown):
        if ahora - self.vistos.get(clave, -1e9) < cooldown:
            return False
        self.vistos[clave] = ahora
        return True

    def actualizar(self, estado, gps, ahora, silenciados=()):
        m = interpretar(gps)
        if m is None or not m.tiene_cielo:
            self.tormenta_previa = None  # sin cielo (otra dimensión) no hay historia que comparar
            return []
        empieza_tormenta = self.tormenta_previa is False and m.tormenta
        self.tormenta_previa = m.tormenta
        if not isinstance(estado, dict) or not estado.get("is_deployed"):
            return []
        avisos = []
        faltan = ticks_hasta_noche(m.hora)
        callado = isinstance(silenciados, (set, frozenset, list, tuple)) and "mundo" in silenciados
        if 0 < faltan <= self.AVISO_NOCHE_TICKS and not callado and self._listo("noche", ahora, self.CD_NOCHE_S):
            avisos.append(nox_voz.frase("anochece", cuando=cuando(faltan)))
        if empieza_tormenta and not callado and self._listo("tormenta", ahora, self.CD_TORMENTA_S):
            avisos.append(nox_voz.frase("tormenta"))
        return [orden("ninguna", a) for a in avisos]
