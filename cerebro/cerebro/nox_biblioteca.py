"""Bloque Q3: biblioteca de planos generada mientras Cobalt estudia."""
import datetime
import json
import os
import threading

PREFIJO = "lib_"
WISHLIST = (
    ("refugio", "refugio pequeño de madera de 5x5 con puerta para pasar la noche"),
    ("casa_pequena", "casa de piedra y madera de 7x7 con 5 de alto, con puerta y ventanas"),
    ("corral", "corral de madera de 8x8 con portón"),
    ("torre_vigia", "torre de vigilancia cuadrada de 5x5 y 12 de alto con puerta abajo"),
    ("puente_piedra", "puente de piedra de 15 de largo y 3 de ancho con barandillas"),
    ("muro_defensivo", "muro defensivo de piedra de 15 de largo con almenas y una puerta en el centro"),
    ("invernadero", "invernadero de cristal de 8x6 con 4 de alto y una puerta"),
    ("cabana", "cabaña de madera de 6x8 con tejado a dos aguas y una puerta"),
    ("faro", "faro de piedra con base de 7x7, 15 de alto, y una luz arriba"),
    ("piramide", "pirámide escalonada de arenisca con base de 13x13"),
)


def nombre_archivo(ident):
    """'refugio' -> 'lib_refugio' (nombre base del plano en blueprints/)."""
    return PREFIJO + ident


class EstadoBiblioteca:
    """Cuántos planos se han generado hoy y cuántos fallos lleva cada uno hoy (se reinicia solo al cambiar de día)."""

    def __init__(self, archivo=None, hoy=None):
        self.archivo = archivo
        self.hoy = hoy or (lambda: datetime.date.today().isoformat())
        self._lock = threading.Lock()
        self._dia, self._hechos, self._fallos = self.hoy(), 0, {}
        if archivo and os.path.exists(archivo):
            try:
                with open(archivo, encoding="utf-8") as f:
                    d = json.load(f)
                if d.get("dia") == self._dia:
                    self._hechos = int(d.get("hechos", 0))
                    self._fallos = {str(k): int(v) for k, v in dict(d.get("fallos", {})).items()}
            except (OSError, ValueError, TypeError):
                pass

    def _rodar(self):
        if self.hoy() != self._dia:
            self._dia, self._hechos, self._fallos = self.hoy(), 0, {}

    def _guardar(self):
        if not self.archivo:
            return
        try:
            tmp = self.archivo + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"dia": self._dia, "hechos": self._hechos, "fallos": self._fallos}, f)
            os.replace(tmp, self.archivo)
        except OSError:
            pass

    def hechos_hoy(self):
        with self._lock:
            self._rodar()
            return self._hechos

    def fallos_de(self, ident):
        with self._lock:
            self._rodar()
            return self._fallos.get(ident, 0)

    def registrar_exito(self, ident):
        with self._lock:
            self._rodar()
            self._hechos += 1
            self._fallos.pop(ident, None)
            self._guardar()

    def registrar_fallo(self, ident):
        with self._lock:
            self._rodar()
            self._fallos[ident] = self._fallos.get(ident, 0) + 1
            self._guardar()


def puede_generar_hoy(estado, max_por_dia):
    return estado.hechos_hoy() < max(0, int(max_por_dia))


def siguiente_pendiente(existentes, estado, max_fallos=2, wishlist=WISHLIST):
    """Primer plano de la lista que aún no existe (ni como lib_<id> ni como lib_<id>_2...) y que hoy no ha fallado 'max_fallos' veces."""
    for ident, descripcion in wishlist:
        base = nombre_archivo(ident)
        if any(n == base or n.startswith(base + "_") for n in existentes):
            continue
        if estado.fallos_de(ident) >= max_fallos:
            continue
        return ident, descripcion
    return None
