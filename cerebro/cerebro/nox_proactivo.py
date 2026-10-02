"""F2-4: proactividad sobre el JUGADOR. PURO: sin red, sin Minecraft, sin disco."""
import math

import nox_voz
from nox_pro import orden


def _num(d, clave, minimo, maximo):
    v = d.get(clave) if isinstance(d, dict) else None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not minimo <= v <= maximo:
        return None
    return v


class AvisosJugador:
    HAMBRE = 6              # a 6 o menos ya no se puede correr
    HAMBRE_REARMA = 12
    HAMBRE_CRITICA = 2
    HAMBRE_CRITICA_REARMA = 6
    AIRE = 90               # de 300 (unos 4,5 s): tiempo justo para subir
    AIRE_REARMA = 250
    INVENTARIO = 2          # huecos libres
    INVENTARIO_REARMA = 6
    CD_S = {"fuego": 15.0, "aire": 20.0, "hambre_critica": 120.0, "hambre": 300.0, "inventario_lleno": 600.0}
    ORDEN = ("fuego", "aire", "hambre_critica", "hambre", "inventario_lleno")   # de más a menos urgente
    MAX_POR_CICLO = 2

    def __init__(self):
        self.armado = {k: True for k in self.CD_S}
        self.ultimo = {}

    def _listo(self, nombre, ahora):
        return self.armado[nombre] and ahora - self.ultimo.get(nombre, -1e9) >= self.CD_S[nombre]

    def _gastar(self, nombre, ahora):
        self.armado[nombre] = False
        self.ultimo[nombre] = ahora

    SILENCIABLES = {"hambre": ("hambre", "hambre_critica"), "inventario": ("inventario_lleno",)}

    def actualizar(self, estado, gps, ahora, silenciados=()):
        dueno = gps.get("owner") if isinstance(gps, dict) else None
        if not isinstance(dueno, dict) or dueno.get("alive") is False:
            return []
        comida = _num(dueno, "food", 0, 20)
        aire, max_aire = _num(dueno, "air", -20, 1000), _num(dueno, "max_air", 1, 1000)
        libres = _num(dueno, "free_slots", 0, 100)
        fuego = dueno.get("on_fire")
        vivo = isinstance(estado, dict) and bool(estado.get("is_deployed"))

        rearma = {
            "fuego": fuego is False,
            "aire": aire is not None and aire >= min(self.AIRE_REARMA, max_aire or self.AIRE_REARMA),
            "hambre_critica": comida is not None and comida >= self.HAMBRE_CRITICA_REARMA,
            "hambre": comida is not None and comida >= self.HAMBRE_REARMA,
            "inventario_lleno": libres is not None and libres >= self.INVENTARIO_REARMA,
        }
        for k, debe in rearma.items():
            if debe:
                self.armado[k] = True
        activa = {
            "fuego": fuego is True,
            "aire": aire is not None and max_aire is not None and aire <= self.AIRE and aire < max_aire,
            "hambre_critica": comida is not None and comida <= self.HAMBRE_CRITICA,
            "hambre": comida is not None and comida <= self.HAMBRE,
            "inventario_lleno": libres is not None and libres <= self.INVENTARIO,
        }
        if not vivo:
            return []
        cats = silenciados if isinstance(silenciados, (set, frozenset, list, tuple)) else ()
        apagados = {a for cat in cats if isinstance(cat, str) for a in self.SILENCIABLES.get(cat, ())}
        candidatos = [k for k in self.ORDEN if k not in apagados and activa[k] and self._listo(k, ahora)]
        if "hambre_critica" in candidatos and "hambre" in candidatos:
            candidatos.remove("hambre")   # el aviso grave sustituye al leve
        elegidos = candidatos[:self.MAX_POR_CICLO]
        for k in elegidos:
            self._gastar(k, ahora)
        if "hambre_critica" in elegidos:
            self._gastar("hambre", ahora)  # y el leve no se dirá justo después: queda desarmado hasta que se recupere
        datos = {"food": int(comida) if comida is not None else "?", "libres": int(libres) if libres is not None else "?"}
        return [orden("ninguna", nox_voz.frase(k, **datos)) for k in elegidos]
