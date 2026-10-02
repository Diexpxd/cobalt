"""Pruebas del Bloque Q3: biblioteca de planos (qué toca, cuántos por día, fallos, reinicio diario)."""
import json
import os
import sys
import tempfile

from _cargar import Resultados

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_biblioteca as nb  # noqa: E402
import nox_plantillas as npl  # noqa: E402

r = Resultados()
tmp = tempfile.mkdtemp()
dia = {"d": "2026-09-20"}
hoy = lambda: dia["d"]  # noqa: E731
archivo = os.path.join(tmp, "biblioteca.json")

est = nb.EstadoBiblioteca(archivo, hoy=hoy)
r.check("la lista tiene 10 planos con ids únicos y descripciones no vacías", len(nb.WISHLIST) == 10 and len({i for i, _ in nb.WISHLIST}) == 10 and all(d.strip() for _, d in nb.WISHLIST))
r.check("nombre de archivo con prefijo lib_", nb.nombre_archivo("refugio") == "lib_refugio")
r.check("empieza por el primero de la lista (el refugio: lo más útil de noche)", nb.siguiente_pendiente(set(), est)[0] == "refugio")
r.check("salta los que ya existen", nb.siguiente_pendiente({"lib_refugio"}, est)[0] == "casa_pequena")
r.check("también reconoce las copias que el guardado nombra lib_x_2, lib_x_3", nb.siguiente_pendiente({"lib_refugio_2", "lib_casa_pequena"}, est)[0] == "corral")
r.check("un plano de otro origen (sin prefijo lib_) NO cuenta como 'ya tengo el refugio'", nb.siguiente_pendiente({"refugio", "casa"}, est)[0] == "refugio")
r.check("un nombre que solo empieza igual no cuenta: lib_refugiomas no es lib_refugio", nb.siguiente_pendiente({"lib_refugiomas"}, est)[0] == "refugio")
todos = {nb.nombre_archivo(i) for i, _ in nb.WISHLIST}
r.check("con todos hechos ya no queda nada pendiente", nb.siguiente_pendiente(todos, est) is None)

# tope por día
r.check("hoy puede generar (0 de 3)", nb.puede_generar_hoy(est, 3))
for i in range(3):
    est.registrar_exito("x%d" % i)
r.check("con 3 hechos y tope 3 ya no genera más hoy", est.hechos_hoy() == 3 and not nb.puede_generar_hoy(est, 3))
r.check("tope 0 desactiva la generación", not nb.puede_generar_hoy(nb.EstadoBiblioteca(None, hoy=hoy), 0))
r.check("tope negativo tampoco genera", not nb.puede_generar_hoy(nb.EstadoBiblioteca(None, hoy=hoy), -5))

# fallos: dos intentos por plano y día, para no gastar dinero en bucle
est2 = nb.EstadoBiblioteca(os.path.join(tmp, "b2.json"), hoy=hoy)
est2.registrar_fallo("refugio")
r.check("un fallo aún permite reintentar el mismo plano", nb.siguiente_pendiente(set(), est2)[0] == "refugio")
est2.registrar_fallo("refugio")
r.check("dos fallos el mismo día: se salta ese plano y sigue con el siguiente", nb.siguiente_pendiente(set(), est2)[0] == "casa_pequena")
est2.registrar_exito("refugio")
r.check("un éxito borra sus fallos", est2.fallos_de("refugio") == 0)
r.check("un fallo NO cuenta como plano generado (no gasta el cupo del día)", nb.EstadoBiblioteca(None, hoy=hoy).hechos_hoy() == 0)
est3 = nb.EstadoBiblioteca(os.path.join(tmp, "b3.json"), hoy=hoy)
est3.registrar_fallo("faro")
r.check("fallar no suma al cupo", est3.hechos_hoy() == 0)

# persistencia y día nuevo
est_b = nb.EstadoBiblioteca(archivo, hoy=hoy)
r.check("el cupo del día sobrevive a un reinicio", est_b.hechos_hoy() == 3)
est4 = nb.EstadoBiblioteca(os.path.join(tmp, "b2.json"), hoy=hoy)
r.check("los fallos del día también sobreviven al reinicio", est4.fallos_de("refugio") == 0 and nb.EstadoBiblioteca(os.path.join(tmp, "b3.json"), hoy=hoy).fallos_de("faro") == 1)
dia["d"] = "2026-09-21"
r.check("día nuevo: el cupo vuelve a 0 y se perdonan los fallos", est.hechos_hoy() == 0 and est3.fallos_de("faro") == 0 and nb.puede_generar_hoy(est, 3))
r.check("al releer el archivo de otro día empieza limpio", nb.EstadoBiblioteca(archivo, hoy=hoy).hechos_hoy() == 0)
open(os.path.join(tmp, "roto.json"), "w").write("{esto no es json")
r.check("un JSON corrupto no rompe: empieza en 0", nb.EstadoBiblioteca(os.path.join(tmp, "roto.json"), hoy=hoy).hechos_hoy() == 0)
open(os.path.join(tmp, "raro.json"), "w").write(json.dumps({"dia": "2026-09-21", "hechos": "muchos", "fallos": [1, 2]}))
r.check("un JSON con tipos raros no rompe", nb.EstadoBiblioteca(os.path.join(tmp, "raro.json"), hoy=hoy).hechos_hoy() == 0)

for ident, descripcion in nb.WISHLIST:
    r.check(f"la petición de '{ident}' también tiene plantilla de respaldo", npl.plano_desde_peticion(descripcion) is not None)

r.terminar()
