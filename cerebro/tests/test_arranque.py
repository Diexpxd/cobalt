"""Arranque real de los hilos de cerebro.py (sección 10): el supervisor los registra, los inicia y el watchdog reinicia uno muerto."""
import io
import os
import tempfile
import threading
import time

from _cargar import RAIZ, Resultados, cargar_cerebro

r = Resultados()
src = io.open(os.path.join(RAIZ, "cerebro", "cerebro.py"), encoding="utf-8").read()
ini = src.index("supervisor = nox_pro.Supervisor()")
fin = src.index("tiempo_ultimo_mensaje = time.time()")
tramo = src[ini:fin]

r.check("el tramo de arranque existe y registra los hilos radar, vision y pro", all(f'supervisor.registrar("{n}"' in tramo for n in ("radar", "vision", "pro")))
r.check("el tramo de arranque lanza el watchdog", "vigilante_de_hilos" in tramo and 'name="watchdog"' in tramo)

ns = cargar_cerebro()
ns["CONFIG_FILE"] = os.path.join(tempfile.mkdtemp(), "cobalt_config.json")  # sin archivo: todo encendido
eventos = {n: threading.Event() for n in ("radar", "vision", "pro")}
arrancados = {"radar": 0, "vision": 0, "pro": 0}


def hilo_falso(nombre):
    def _cuerpo(*args, **kwargs):
        arrancados[nombre] += 1
        eventos[nombre].wait(30)  # vive hasta que la prueba lo mate
    return _cuerpo


ns["vigilante_radar"] = hilo_falso("radar")
ns["bucle_vision_continua"] = hilo_falso("vision")
ns["hilo_pro"] = hilo_falso("pro")
ns["asegurar_ollama"] = lambda *a, **k: None
exec(compile(tramo.replace("asegurar_ollama()   # la visión LLaVA y los modelos locales sí; si estaba apagado, lo inicia y espera", "asegurar_ollama()"), "arranque", "exec"), ns)

time.sleep(0.4)
r.check("arranque: los 3 hilos están vivos, cada uno arrancó una vez", all(arrancados[n] == 1 for n in arrancados)
        and all(ns["supervisor"].hilos[n]["hilo"].is_alive() for n in ("radar", "vision", "pro")))
r.check("arranque: los hilos son daemon (no bloquean el cierre del programa)", all(ns["supervisor"].hilos[n]["hilo"].daemon for n in ("radar", "vision", "pro")))
r.check("arranque: el watchdog está en marcha", any(t.name == "watchdog" and t.is_alive() for t in threading.enumerate()))

eventos["radar"].set()  # el hilo de radar "muere"
time.sleep(0.2)
r.check("el hilo de radar ha terminado (simulación de un fallo)", not ns["supervisor"].hilos["radar"]["hilo"].is_alive())
eventos["radar"] = threading.Event()  # el hilo reiniciado esperará de nuevo
hasta = time.time() + 4.0
while time.time() < hasta and arrancados["radar"] < 2:
    time.sleep(0.1)
r.check("el watchdog REINICIA el hilo muerto en menos de 4 s y el nuevo está vivo", arrancados["radar"] == 2 and ns["supervisor"].hilos["radar"]["hilo"].is_alive())
r.check("el reinicio no tocó a los otros hilos", arrancados["vision"] == 1 and arrancados["pro"] == 1)

for e in eventos.values():
    e.set()
r.terminar()
