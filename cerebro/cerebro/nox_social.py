"""nox_social.py."""
import math
import random
import re

import nox_voz
from nox_pro import _normalizar_frase, _numero, distancia, dueno, hostiles, orden, posicion


def _corto(recurso):
    return str(recurso).split(":", 1)[-1]


def _detras(dpos, yaw, epos, umbral=-0.3):
    if not _numero(yaw):
        return False
    a = math.radians(yaw)
    fx, fz = -math.sin(a), math.cos(a)
    tx, tz = epos[0] - dpos[0], epos[2] - dpos[2]
    n = math.hypot(tx, tz)
    if n < 1e-6:
        return False
    return (fx * tx + fz * tz) / n < umbral


_TRAMPAS_ES = {"tnt": "TNT expuesta", "tripwire": "un hilo trampa", "sculk_shrieker": "un sculk shrieker (invoca al Warden)",
               "pressure_plate": "una placa de presión", "cobweb": "una telaraña"}


class CalloutsTacticos:
    """Avisa por el chat de peligros invisibles para el jugador: un creeper (u otro hostil que se acerca) a su ESPALDA, trampas junto a"""

    RADIO_ESPALDA = 12.0
    RADIO_HOSTIL = 7.0
    CD_ESPALDA_S = 10.0
    CD_TRAMPA_S = 60.0
    CD_HERRAMIENTA_S = 120.0
    UMBRAL_HERRAMIENTA_PCT = 8.0
    MAX_POR_CICLO = 2

    def __init__(self):
        self.vistos = {}

    def _listo(self, clave, ahora, cooldown):
        if ahora - self.vistos.get(clave, -1e9) < cooldown:
            return False
        self.vistos[clave] = ahora
        return True

    def actualizar(self, estado, gps, entidades, ahora):
        if not estado.get("is_deployed") or not isinstance(entidades, dict):
            return []
        avisos = []
        d = dueno(entidades)
        dpos = posicion(d) if d else None
        if d and dpos:
            espalda = []
            for e in hostiles(entidades):
                epos = posicion(e)
                if not epos or not _detras(dpos, d.get("yaw"), epos):
                    continue
                dist = distancia(dpos, epos)
                creeper = "creeper" in str(e.get("type", "")).lower()
                if dist <= self.RADIO_ESPALDA and creeper:
                    espalda.append((0, dist, e))
                elif dist <= self.RADIO_HOSTIL and (e.get("approaching") or e.get("targets_player")):
                    espalda.append((1, dist, e))
            for _, dist, e in sorted(espalda, key=lambda t: (t[0], t[1])):
                if self._listo(("espalda", e.get("id", e.get("name"))), ahora, self.CD_ESPALDA_S):
                    nombre = e.get("name", "un enemigo")
                    avisos.append(nox_voz.frase("a_tu_espalda", nombre=nombre, dist=int(round(dist))))
                    break
            tool, pct = d.get("held"), d.get("held_dur_pct")
            if tool and _numero(pct) and pct < self.UMBRAL_HERRAMIENTA_PCT and self._listo(("herramienta", tool), ahora, self.CD_HERRAMIENTA_S):
                avisos.append(f"Tu {_corto(tool).replace('_', ' ')} está a punto de romperse ({int(pct)}%).")
        bot = posicion(entidades.get("bot")) or posicion(gps)
        if bot and (not dpos or distancia(bot, dpos) <= 8.0):
            for t in entidades.get("hazards") or []:
                if not isinstance(t, dict) or t.get("type") not in _TRAMPAS_ES or not _numero(t.get("dist")) or t["dist"] > 3.5:
                    continue
                if self._listo(("trampa", t.get("type"), t.get("x"), t.get("y"), t.get("z")), ahora, self.CD_TRAMPA_S):
                    avisos.append(f"Cuidado: {_TRAMPAS_ES[t['type']]} a {t['dist']:.0f} bloques.")
        return [orden("ninguna", a) for a in avisos[:self.MAX_POR_CICLO]]


class Mimetismo:
    """Cada 20-45 s de tranquilidad (sin combate, sin tarea, sin guardia, con salud normal) hace algo "humano": mirar al jugador a los ojos"""

    MIN_S = 20.0
    MAX_S = 45.0
    RADIO_MIRADA = 12.0

    def __init__(self, azar=None):
        self.azar = azar or random.Random()
        self.proximo = None

    def _tranquilo(self, estado):
        return (estado.get("is_deployed") and not estado.get("in_combat") and not estado.get("task") and not estado.get("guarding")
                and not estado.get("frozen") and not estado.get("critical_hp") and not estado.get("fleeing") and not estado.get("boss_mode"))

    def actualizar(self, estado, entidades, ahora):
        if not self._tranquilo(estado):
            self.proximo = None
            return []
        if self.proximo is None:
            self.proximo = ahora + self.azar.uniform(self.MIN_S, self.MAX_S)
            return []
        if ahora < self.proximo:
            return []
        self.proximo = ahora + self.azar.uniform(self.MIN_S, self.MAX_S)
        d = dueno(entidades) if isinstance(entidades, dict) else None
        cerca = bool(d) and _numero(d.get("dist")) and d["dist"] <= self.RADIO_MIRADA
        caminando = estado.get("movement_mode") == "walk" and estado.get("on_ground", True)
        if cerca and (not caminando or self.azar.random() < 0.6):
            return [orden("look_at", seconds=self.azar.randint(2, 4))]
        if caminando:
            return [orden("hop")]
        return []


_RE_COSECHA = re.compile(r"^(?:cobalt\s+)?(?:por favor\s+)?(?:cosecha|cosechar|recoge la cosecha|recolecta la cosecha|recolecta los cultivos|recoge los cultivos)\b")
_RE_RADIO = re.compile(r"\ben\s+(\d+)\s+bloques\b")


def interpretar_cosecha(mensaje, defecto=12, minimo=3, maximo=24):
    """Radio (bloques) si el mensaje ORDENA cosechar ('cosecha', 'cosecha los cultivos', 'recoge la cosecha en 20 bloques'), o None."""
    f = _normalizar_frase(mensaje)
    if not f or not _RE_COSECHA.search(f):
        return None
    m = _RE_RADIO.search(f)
    return max(minimo, min(maximo, int(m.group(1)))) if m else defecto
