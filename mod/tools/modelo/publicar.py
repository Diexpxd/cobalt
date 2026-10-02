"""Construye el visor 3D publicable (una sola pagina con el guardian y los efectos incrustados) en salida/visor_guardian.html.

    python publicar.py                    # genera la pagina
    python publicar.py --foto <destino>   # ademas hace una captura de revision con Edge (?captura=1)
"""
import base64
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import generar  # noqa: E402

SALIDA = os.path.join(AQUI, "salida")
MODELOS = ("nox", "plasma", "emp_wave", "drone")


def b64(ruta):
    with open(ruta, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def construir():
    generar.generar()
    datos = {}
    for n in MODELOS:
        with open(os.path.join(SALIDA, n + ".geo.json"), encoding="utf-8") as f:
            geo = json.load(f)
        with open(os.path.join(SALIDA, n + ".animation.json"), encoding="utf-8") as f:
            anim = json.load(f)
        datos[n] = {"geo": geo, "anim": anim, "texBase": b64(os.path.join(SALIDA, n + ".png")), "texBrillo": b64(os.path.join(SALIDA, n + "_glowmask.png"))}
    with open(os.path.join(AQUI, "visor_publicar.tpl.html"), encoding="utf-8") as f:
        tpl = f.read()
    assert tpl.count("/*DATOS*/null") == 1
    html = tpl.replace("/*DATOS*/null", json.dumps(datos, separators=(",", ":")))
    ruta = os.path.join(SALIDA, "visor_guardian.html")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(html)
    print("visor:", ruta, round(len(html) / 1e6, 2), "MB")
    return ruta, html


if __name__ == "__main__":
    ruta, html = construir()
    if "--foto" in sys.argv:
        import capturar
        destino = sys.argv[sys.argv.index("--foto") + 1]
        opciones = [a for a in sys.argv if "=" in a]
        local = os.path.join(SALIDA, "visor_guardian_local.html")
        with open(local, "w", encoding="utf-8") as f:
            f.write("<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\"></head><body>" + html + "</body></html>")
        consulta = "&".join(opciones)
        url = "file:///" + local.replace(os.sep, "/") + "?captura=1" + ("&" + consulta if consulta else "")
        print("foto" if capturar._edge(destino, url, 1200, 800) else "FALLO")
