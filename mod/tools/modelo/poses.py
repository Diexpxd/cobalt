"""Hoja de poses: una animacion en varios instantes desde una camara.
    python poses.py <destino.png> anim=walk cam=lado tiempos=0,0.25,0.5,0.75 [ancho=380] [alto=520] [dist=5]
"""
import os
import sys
import tempfile

from PIL import Image

import capturar
import generar

if __name__ == "__main__":
    destino = sys.argv[1]
    op = dict(a.split("=", 1) for a in sys.argv[2:])
    tiempos = op.pop("tiempos", "0,0.25,0.5,0.75").split(",")
    ancho, alto = int(op.pop("ancho", 380)), int(op.pop("alto", 520))
    columnas = int(op.pop("columnas", len(tiempos)))
    generar.generar()
    extra = "&".join("%s=%s" % (k, v) for k, v in op.items())
    fotos = []
    for t in tiempos:
        f = os.path.join(tempfile.gettempdir(), "pose_%s.png" % t)
        if not capturar.capturar(f, "t=%s&%s" % (t, extra), ancho, alto):
            raise SystemExit("falla el instante " + t)
        fotos.append(Image.open(f).convert("RGB"))
    filas = (len(fotos) + columnas - 1) // columnas
    hoja = Image.new("RGB", (ancho * columnas, alto * filas))
    for i, im in enumerate(fotos):
        hoja.paste(im, ((i % columnas) * ancho, (i // columnas) * alto))
    hoja.save(destino)
    print("ok", destino)
