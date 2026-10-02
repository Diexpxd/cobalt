"""Carga cerebro.py SIN arrancar hilos ni el bucle infinito (corta antes de la sección 10) para poder probar sus funciones."""
import io
import os
import sys

for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cargar_cerebro():
    src = io.open(os.path.join(RAIZ, "cerebro", "cerebro.py"), encoding="utf-8").read()
    corte = src.index("# 10. EL BUCLE PRINCIPAL")
    ns = {"__name__": "test", "__file__": os.path.join(RAIZ, "cerebro", "cerebro.py")}
    exec(compile(src[:corte], "cerebro_parcial", "exec"), ns)
    return ns


class Resultados:
    def __init__(self):
        self.fallos = []

    def check(self, nombre, condicion):
        print(("OK   " if condicion else "FAIL ") + nombre)
        if not condicion:
            self.fallos.append(nombre)

    def terminar(self):
        print("\nRESULTADO:", "TODO OK" if not self.fallos else f"{len(self.fallos)} FALLOS: {self.fallos}")
        raise SystemExit(1 if self.fallos else 0)
