"""Bloque O (Python): El Bardo escribe una crónica con hechos del registro, paginada para un libro de Minecraft."""
import datetime
import os
import sys
import time

from _cargar import RAIZ, Resultados

sys.path.insert(0, os.path.join(RAIZ, "cerebro"))
import nox_bardo as bd  # noqa: E402

r = Resultados()
AHORA = datetime.datetime(2026, 9, 19, 12, 30)
TS = time.mktime(datetime.datetime(2026, 9, 18, 10, 0).timetuple())

r.check("fecha: '19 de septiembre de 2026' (meses en español sin depender del sistema)", bd.fecha_larga(AHORA) == "19 de septiembre de 2026" and bd.fecha_larga(datetime.datetime(2026, 1, 1)) == "1 de enero de 2026")

pag = bd.paginar(["uno", "dos", "tres"])
r.check("paginar: líneas cortas caben en una página, separadas por saltos de línea", pag == ["uno\ndos\ntres"])
largas = ["a" * 100, "b" * 100, "c" * 100]
pag = bd.paginar(largas, 240)
r.check("paginar: 3 líneas de 100 (con saltos = 302) se reparten en 2 páginas sin partir ninguna línea", pag == ["a" * 100 + "\n" + "b" * 100, "c" * 100])
palabras = " ".join(["palabra"] * 100)  # 799 caracteres en una sola línea
pag = bd.paginar([palabras], 240)
r.check("paginar: una línea enorme se corta por palabras, ninguna página pasa de 240 y no se pierde texto", all(len(p) <= 240 for p in pag) and len(pag) >= 4
        and " ".join(pag).replace("\n", " ").split() == palabras.split())
r.check("paginar: una 'palabra' sin espacios más larga que la página se corta a la fuerza", all(len(p) <= 240 for p in bd.paginar(["z" * 700], 240)) and "".join(bd.paginar(["z" * 700], 240)) == "z" * 700)
r.check("paginar: sin líneas o solo vacías -> sin páginas", bd.paginar([]) == [] and bd.paginar(["", "  ", ""]) == [])
r.check("paginar: nunca más de 40 páginas", len(bd.paginar(["x" * 200] * 500)) == 40)
r.check("paginar: una línea vacía en medio se conserva como separación", bd.paginar(["a", "", "b"]) == ["a\n\nb"])

REGISTROS = [
    {"ts": TS, "duracion_s": 30.0, "danio": 8.0, "rival": "Zombie", "rivales": ["Zombie"], "jefe": False, "resultado": "victoria", "dimension": "minecraft:overworld"},
    {"ts": TS, "duracion_s": 12.0, "danio": 4.0, "rival": "Zombie", "rivales": ["Zombie"], "jefe": False, "resultado": "victoria", "dimension": "minecraft:overworld"},
    {"ts": TS, "duracion_s": 95.0, "danio": 40.0, "rival": "Ender Dragon", "jefe": True, "boss_name": "Ender Dragon", "resultado": "victoria", "dimension": "minecraft:the_end"},
    {"ts": TS, "duracion_s": 20.0, "danio": 25.0, "rival": "Creeper", "jefe": False, "resultado": "muerte", "dimension": "minecraft:overworld"},
]
OBRAS = {"casa": {"plano": "casa", "x": 500, "y": 70, "z": -30, "dimension": "minecraft:overworld", "t": TS}, "torre": {"plano": "torre", "x": 10, "y": 64, "z": 10, "t": TS + 5}}
WPS = {"base": {"x": 0, "y": 64, "z": 0}, "mina": {"x": 5, "y": 10, "z": 5}, "muerte_nox_1789000000000": {"x": 1, "y": 2, "z": 3}, "inventario_nox_1": {"x": 1, "y": 2, "z": 3}}
titulo, paginas = bd.crear_cronica(REGISTROS, OBRAS, WPS, AHORA)
texto = "\n".join(paginas)
r.check("crónica: título y firma", titulo == "Crónica de Cobalt" and "Firmado: Cobalt." in texto and "19 de septiembre de 2026" in texto)
r.check("crónica: cuenta los combates (4: 3 victorias, 1 caída) y el daño total (77)", "Combates: 4 (3 victorias, 1 caídas)" in texto and "Daño recibido en total: 77" in texto)
r.check("crónica: el rival más común (Zombie, 2 veces) y el jefe vencido (Ender Dragon)", "Mi rival más común: Zombie (2 veces)" in texto and "Jefes vencidos: Ender Dragon" in texto)
r.check("crónica: el combate más largo (95 s contra Ender Dragon) y las dimensiones", "95 s contra Ender Dragon" in texto and "overworld" in texto and "the_end" in texto)
r.check("crónica: las obras (2), la más reciente primero, con coordenadas", "Obras construidas: 2." in texto and texto.index("- torre") < texto.index("- casa") and "X=500 Z=-30" in texto)
r.check("crónica: cuenta las muertes por los waypoints automáticos y no los lista entre los lugares", "He caído 1 vez" in texto and "base, mina" in texto and "muerte_nox" not in texto and "inventario_nox" not in texto)
r.check("crónica: ninguna página pasa de 240 caracteres (Java corta a 250)", all(len(p) <= 240 for p in paginas) and len(paginas) >= 2)
vacia_t, vacia = bd.crear_cronica([], {}, {}, AHORA)
vt = "\n".join(vacia)
r.check("crónica: sin datos NO inventa nada (lo dice tal cual)", "Aún no he librado ningún combate" in vt and "Todavía no he levantado ninguna obra" in vt and "He caído" not in vt and "Lugares" not in vt)
sucio_t, sucio = bd.crear_cronica([None, 5, {"resultado": "victoria", "danio": "mucho", "duracion_s": None}], {"x": 3, "y": {"t": "nunca"}}, {"muerte_nox_abc": {}, 3: 4}, AHORA)
r.check("crónica: registros rotos no revientan", isinstance(sucio, list) and len(sucio) >= 1)
grande = [{"ts": TS, "duracion_s": 1.0, "danio": 1.0, "rival": f"Mob{i}", "resultado": "victoria"} for i in range(400)]
lugares = {f"lugar_{i}": {"x": i, "y": 0, "z": 0} for i in range(100)}
_, enorme = bd.crear_cronica(grande, {f"obra{i}": {"x": i, "z": i, "t": TS} for i in range(100)}, lugares, AHORA)
r.check("crónica: con muchos datos sigue dentro de los límites (<=40 páginas de <=240)", len(enorme) <= 40 and all(len(p) <= 240 for p in enorme) and "…" in "\n".join(enorme))

i = bd.interpretar_bardo
r.check("chat: 'escribe la crónica', 'escribe un libro', 'redacta tu diario', 'haz un libro de tus aventuras' -> cronica",
        all(i(x) == "cronica" for x in ("escribe la crónica", "escribe un libro", "Cobalt, redacta tu diario", "haz un libro de tus aventuras", "escríbeme una crónica", "crónica")))
r.check("chat: frases que solo mencionan un libro NO disparan nada", all(i(x) is None for x in ("dame un libro", "he leído un libro genial", "escribe un mensaje", "mina hierro", "", None, "libro")))

r.terminar()
