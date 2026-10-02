"""Capturas del visor 3D con Edge sin ventana (para revisar el modelo sin abrir Minecraft).

    python capturar.py <destino.png> [cam=frente|3/4|lado|atras|arriba] [anim=idle] [t=0.5] [dist=4.3] [y=1.05] [brillo=0] [ancho=900] [alto=1000]
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import quote

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "salida")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
THREE_CDN = "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.min.js"


def preparar(directorio, modelo="nox"):
    os.makedirs(directorio, exist_ok=True)
    three = os.path.join(directorio, "three.module.min.js")
    if not os.path.exists(three):
        urllib.request.urlretrieve(THREE_CDN, three)
    shutil.copy2(os.path.join(AQUI, "visor.html"), os.path.join(directorio, "visor.html"))
    with open(os.path.join(SALIDA, modelo + ".geo.json"), encoding="utf-8") as f:
        geo = json.load(f)
    with open(os.path.join(SALIDA, modelo + ".animation.json"), encoding="utf-8") as f:
        anim = json.load(f)
    b64 = lambda ruta: "data:image/png;base64," + base64.b64encode(open(ruta, "rb").read()).decode()
    datos = {"geo": geo, "anim": anim, "texBase": b64(os.path.join(SALIDA, modelo + ".png")), "texBrillo": b64(os.path.join(SALIDA, modelo + "_glowmask.png")), "resumen": ""}
    with open(os.path.join(directorio, "datos.js"), "w", encoding="utf-8") as f:
        f.write("window.THREE_URL = './three.module.min.js';\nwindow.DATOS = " + json.dumps(datos) + ";\n")


def capturar(destino, consulta, ancho=900, alto=1000, directorio=None, modelo="nox"):
    directorio = directorio or os.path.join(os.environ.get("TEMP", "."), "visor_guardian")
    preparar(directorio, modelo)

    url = "file:///%s/visor.html?captura=1&%s" % (directorio.replace(os.sep, "/"), consulta)
    return _edge(destino, url, ancho, alto)


def _edge(destino, url, ancho, alto):
    if os.path.exists(destino):
        os.remove(destino)
    try:
        for intento in range(4):
            perfil = tempfile.mkdtemp(prefix="edge_perfil_")
            extra = ["--disable-gpu"] if intento % 2 else []
            cmd = [EDGE, "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--hide-scrollbars", "--no-first-run", "--allow-file-access-from-files",
                   "--disable-background-networking", "--user-data-dir=" + perfil, "--window-size=%d,%d" % (ancho, alto), "--virtual-time-budget=12000",
                   "--screenshot=" + os.path.abspath(destino)] + extra + [url]
            lista = ",".join("'" + a.replace("'", "''") + "'" for a in cmd[1:])
            ps = "Start-Process -FilePath '%s' -ArgumentList %s -WindowStyle Hidden" % (cmd[0], lista)
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=60)
            limite = time.time() + 60
            while time.time() < limite and not (os.path.exists(destino) and os.path.getsize(destino) > 0):
                time.sleep(0.5)
            time.sleep(0.5)
            matar = "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | Where-Object { $_.CommandLine -like '*%s*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" % os.path.basename(perfil)
            subprocess.run(["powershell", "-NoProfile", "-Command", matar], capture_output=True, timeout=60)
            shutil.rmtree(perfil, ignore_errors=True)
            if os.path.exists(destino) and os.path.getsize(destino) > 0:
                break
            print("intento %d sin foto, reintento" % (intento + 1))
    finally:
        pass
    return os.path.exists(destino)


if __name__ == "__main__":
    destino = sys.argv[1]
    opciones = dict(a.split("=", 1) for a in sys.argv[2:])
    ancho, alto = int(opciones.pop("ancho", 900)), int(opciones.pop("alto", 1000))
    modelo = opciones.pop("modelo", "nox")
    consulta = "&".join("%s=%s" % (k, quote(v, safe="")) for k, v in opciones.items())
    print("ok" if capturar(destino, consulta, ancho, alto, modelo=modelo) else "FALLO")
