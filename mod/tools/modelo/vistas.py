"""Hoja de contacto: varias vistas del modelo en una sola imagen.   python vistas.py <destino.png> [anim=idle] [t=0.0] [vistas=frente,3/4,lado,atras]"""
import os
import sys
import tempfile

from PIL import Image

import capturar
import generar

if __name__ == "__main__":
    destino = sys.argv[1]
    op = dict(a.split("=", 1) for a in sys.argv[2:])
    vistas = op.pop("vistas", "frente,tres_cuartos,lado,atras").split(",")
    ancho, alto = int(op.pop("ancho", 600)), int(op.pop("alto", 760))
    generar.generar()
    extra = "&".join("%s=%s" % (k, v) for k, v in op.items())
    fotos = []
    for v in vistas:
        f = os.path.join(tempfile.gettempdir(), "vista_%s.png" % v.replace("/", "_"))
        if not capturar.capturar(f, "cam=%s&%s" % (v.replace("/", "%2F"), extra), ancho, alto):
            raise SystemExit("falla la vista " + v)
        fotos.append(Image.open(f).convert("RGB"))
    cols = 2 if len(fotos) > 2 else len(fotos)
    filas = (len(fotos) + cols - 1) // cols
    hoja = Image.new("RGB", (ancho * cols, alto * filas))
    for i, im in enumerate(fotos):
        hoja.paste(im, ((i % cols) * ancho, (i // cols) * alto))
    hoja.save(destino)
    print("ok", destino)
