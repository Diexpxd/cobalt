"""Genera el modelo del guardian arcano: geo + animaciones + textura (base y brillo) en tools/modelo/salida/.

    python generar.py                 # solo genera en salida/
    python generar.py --instalar      # ademas copia al mod (assets/cobaltbot/...) guardando el modelo anterior en tools/modelo/original/
"""
import argparse
import os
import shutil
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import guardian  # noqa: E402
import animaciones  # noqa: E402
import pintura  # noqa: E402
import efectos  # noqa: E402
from geo import guardar_animaciones  # noqa: E402

SALIDA = os.path.join(AQUI, "salida")
ASSETS = os.path.normpath(os.path.join(AQUI, "..", "..", "src", "main", "resources", "assets", "cobaltbot"))


def generar():
    os.makedirs(SALIDA, exist_ok=True)
    m = guardian.construir()
    m.empaquetar()
    base, brillo = pintura.pintar(m)
    m.guardar_geo(os.path.join(SALIDA, "nox.geo.json"))
    guardar_animaciones(animaciones.todas(), os.path.join(SALIDA, "nox.animation.json"))
    base.save(os.path.join(SALIDA, "nox.png"))
    brillo.save(os.path.join(SALIDA, "nox_glowmask.png"))
    for nombre in efectos.EFECTOS:
        efectos.generar(nombre)
    return m


def instalar():
    """Copia al mod. El modelo anterior (el de WoW, 158 px de alto) se guarda una sola vez en tools/modelo/original/."""
    orig = os.path.join(AQUI, "original")
    if not os.path.isdir(orig):
        os.makedirs(orig)
        for rel in ("geo/nox.geo.json", "animations/nox.animation.json", "textures/entity/nox.png", "textures/entity/nox_e.png"):
            src = os.path.join(ASSETS, *rel.split("/"))
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(orig, os.path.basename(src)))
    destinos = {"nox.geo.json": "geo", "nox.animation.json": "animations", "nox.png": os.path.join("textures", "entity"), "nox_glowmask.png": os.path.join("textures", "entity")}
    for archivo, carpeta in destinos.items():
        shutil.copy2(os.path.join(SALIDA, archivo), os.path.join(ASSETS, carpeta, archivo))
    for nombre in efectos.EFECTOS:                      # efectos de las habilidades: plasma, onda EMP y dron
        for archivo, carpeta in ((nombre + ".geo.json", "geo"), (nombre + ".animation.json", "animations"),
                                 (nombre + ".png", os.path.join("textures", "entity")), (nombre + "_glowmask.png", os.path.join("textures", "entity"))):
            shutil.copy2(os.path.join(SALIDA, archivo), os.path.join(ASSETS, carpeta, archivo))
    print("instalado en", ASSETS)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--instalar", action="store_true")
    a = ap.parse_args()
    modelo = generar()
    print(modelo.estadisticas())
    if a.instalar:
        instalar()
