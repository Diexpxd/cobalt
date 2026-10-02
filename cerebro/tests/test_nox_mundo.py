"""H3: sentido del mundo."""
import os
import sys

from _cargar import Resultados
import _frases_del_codigo as fc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_mundo as m  # noqa: E402
import nox_voz  # noqa: E402

r = Resultados()


def gps(hora=6000, lluvia=False, tormenta=False, luz=15, cielo=True, tiene_cielo=True, **extra):
    d = {"day_time": hora, "raining": lluvia, "thundering": tormenta, "light": luz, "sky": cielo, "has_skylight": tiene_cielo}
    d.update(extra)
    return {"x": 0, "y": 64, "z": 0, "mundo": d}


VIVO = {"is_deployed": True}

mu = m.interpretar(gps(hora=6000, lluvia=True, luz=9))
r.check("interpreta un bloque válido: " + str(mu), mu == m.Mundo(6000, True, False, 9, True, True))
r.check("una tormenta implica lluvia aunque Java no la marque", m.interpretar(gps(tormenta=True)).lluvia is True)
r.check("la hora se normaliza al día (30000 -> 6000, -1000 -> 23000)", m.interpretar(gps(hora=30000)).hora == 6000 and m.interpretar(gps(hora=-1000)).hora == 23000)
r.check("la hora puede llegar como float entero (5999.0 -> 5999)", m.interpretar(gps(hora=5999.0)).hora == 5999)
r.check("la luz se limita a 0..15", m.interpretar(gps(luz=99)).luz == 15 and m.interpretar(gps(luz=-4)).luz == 0)
r.check("luz que no es número -> None (no se inventa)", m.interpretar(gps(luz="mucha")).luz is None and m.interpretar(gps(luz=True)).luz is None)
malos = [None, {}, {"mundo": None}, {"mundo": []}, {"mundo": "x"}, {"mundo": {}}, {"mundo": {"day_time": None}}, {"mundo": {"day_time": "6000"}}, {"mundo": {"day_time": True}},
         {"mundo": {"day_time": float("nan")}}, {"mundo": {"day_time": float("inf")}}, "gps", 5, [1]]
r.check("gps sin bloque 'mundo' (Java antiguo) o con hora inválida -> None: " + str([x for x in malos if m.interpretar(x) is not None]), all(m.interpretar(x) is None for x in malos))
r.check("los booleanos deben SER booleanos ('true', 1 y 'yes' no cuentan como tormenta, cielo ni skylight)",
        m.interpretar({"mundo": {"day_time": 1, "thundering": "true", "raining": 1, "sky": "yes", "has_skylight": 1}}) == m.Mundo(1, False, False, None, False, False))

r.check("fases: 0=dia, 11999=dia, 12000=atardecer, 12999=atardecer, 13000=noche, 22999=noche, 23000=amanecer, 23999=amanecer",
        [m.fase(x) for x in (0, 11999, 12000, 12999, 13000, 22999, 23000, 23999)] == ["dia", "dia", "atardecer", "atardecer", "noche", "noche", "amanecer", "amanecer"])
r.check("fase da la vuelta al día (24000+13000 = noche)", m.fase(37000) == "noche")
r.check("ticks hasta la noche: 0->13000, 12000->1000, 12999->1, 13000->0 (ya es de noche), 22999->0, 23000->14000, 23999->13001",
        [m.ticks_hasta_noche(x) for x in (0, 12000, 12999, 13000, 22999, 23000, 23999)] == [13000, 1000, 1, 0, 0, 14000, 13001])
r.check("hora del juego: tick 0 = 06:00, 6000 = 12:00, 12000 = 18:00, 13500 = 19:30, 18000 = 00:00, 23999 = 05:59",
        [m.hora_juego(x) for x in (0, 6000, 12000, 13500, 18000, 23999)] == ["06:00", "12:00", "18:00", "19:30", "00:00", "05:59"])
r.check("cuando(): <1 min y redondeo a minutos", m.cuando(0) == "en menos de un minuto" and m.cuando(1199) == "en menos de un minuto" and m.cuando(1200) == "en aproximadamente un minuto" and m.cuando(1799) == "en aproximadamente un minuto"
        and m.cuando(1800) == "en unos 2 min" and m.cuando(6000) == "en unos 5 min")
# un día completo: 24000 ticks = 20 min reales
r.check("propiedad: en todo el día ticks_hasta_noche está en [0,24000) y la fase cubre los 4 valores",
        all(0 <= m.ticks_hasta_noche(h) < 24000 for h in range(0, 24000, 37)) and {m.fase(h) for h in range(0, 24000, 50)} == {"dia", "atardecer", "noche", "amanecer"})

d1 = m.resumen(gps(hora=6000))
r.check("de día, despejado: " + d1, d1 == "Es de día (12:00); anochece en unos 6 min; cielo despejado.")
d2 = m.resumen(gps(hora=15000, lluvia=True, tormenta=True, luz=2, cielo=False))
r.check("de noche, tormenta, a cubierto y poca luz: " + d2, d2 == "Es de noche (21:00): aparecen monstruos en superficie; tormenta eléctrica; estoy bajo techo o bajo tierra; poca luz donde estoy (2/15): pueden aparecer monstruos.")
r.check("lluvia sin tormenta", "llueve" in m.resumen(gps(lluvia=True)) and "tormenta" not in m.resumen(gps(lluvia=True)))
r.check("atardecer y amanecer", m.resumen(gps(hora=12500)) == "Atardece (18:30); la noche empieza en menos de un minuto; cielo despejado." and m.resumen(gps(hora=23500)) == "Amanece (05:30); cielo despejado.")
r.check("en el Nether/End (sin cielo) no hay nada que describir; sin datos, tampoco", m.resumen(gps(tiene_cielo=False)) == "" and m.resumen({}) == "" and m.resumen(None) == "")
r.check("con luz desconocida no menciona la luz", "luz" not in m.resumen(gps(luz=None)))
r.check("con luz suficiente (8) no menciona la luz; con 7 sí", "luz" not in m.resumen(gps(luz=8)) and "poca luz" in m.resumen(gps(luz=7)))

a = m.AvisosMundo()
o = a.actualizar(VIVO, gps(hora=11000), 100.0)
r.check("a 2000 ticks de la noche todavía no avisa", o == [])
o = a.actualizar(VIVO, gps(hora=11200), 101.0)
r.check("a 1800 ticks (90 s de juego) avisa una vez, con una frase del banco y sin acción de juego: " + str(o),
        len(o) == 1 and o[0]["action"] == "ninguna" and o[0]["chat_message"] in [x.format(cuando="en unos 2 min") for x in nox_voz.BANCO["anochece"]])
r.check("no repite el aviso dentro del enfriamiento (15 min), aunque siga en la ventana",
        a.actualizar(VIVO, gps(hora=11400), 106.0) == [] and a.actualizar(VIVO, gps(hora=12500), 300.0) == [] and a.actualizar(VIVO, gps(hora=12900), 600.0) == [])
r.check("pasado el enfriamiento (15 min) vuelve a avisar en el día siguiente",
        len(a.actualizar(VIVO, gps(hora=11500), 101.0 + 901.0)) == 1)
a = m.AvisosMundo()
r.check("ya de noche no avisa de que anochece", a.actualizar(VIVO, gps(hora=15000), 1.0) == [] and a.actualizar(VIVO, gps(hora=23000), 2.0) == [])
r.check("en el límite exacto: 1800 sí, 1801 no",
        len(m.AvisosMundo().actualizar(VIVO, gps(hora=13000 - 1800), 1.0)) == 1 and m.AvisosMundo().actualizar(VIVO, gps(hora=13000 - 1801), 1.0) == [])
r.check("a punto de anochecer dice 'menos de un minuto'", "en menos de un minuto" in m.AvisosMundo().actualizar(VIVO, gps(hora=12500), 1.0)[0]["chat_message"])
r.check("con Cobalt sin desplegar no avisa (no habla si no está en el mundo)", m.AvisosMundo().actualizar({"is_deployed": False}, gps(hora=12000), 1.0) == []
        and m.AvisosMundo().actualizar({}, gps(hora=12000), 1.0) == [] and m.AvisosMundo().actualizar(None, gps(hora=12000), 1.0) == [])
r.check("sin cielo (Nether) no avisa de la noche", m.AvisosMundo().actualizar(VIVO, gps(hora=12500, tiene_cielo=False), 1.0) == [])
r.check("con un Java antiguo (sin bloque 'mundo') no avisa ni lanza", m.AvisosMundo().actualizar(VIVO, {"x": 1, "y": 2, "z": 3}, 1.0) == [])

a = m.AvisosMundo()
r.check("el primer dato observado (ya hay tormenta) no cuenta como transición: el jugador ya la ve", a.actualizar(VIVO, gps(tormenta=True), 1.0) == [])
a = m.AvisosMundo()
a.actualizar(VIVO, gps(), 1.0)
o = a.actualizar(VIVO, gps(lluvia=True, tormenta=True), 2.0)
r.check("de despejado a tormenta -> un aviso de chat del banco: " + str(o), len(o) == 1 and o[0]["action"] == "ninguna" and o[0]["chat_message"] in nox_voz.BANCO["tormenta"])
r.check("mientras dura la tormenta no repite", a.actualizar(VIVO, gps(tormenta=True), 3.0) == [] and a.actualizar(VIVO, gps(tormenta=True), 400.0) == [])
ll = m.AvisosMundo()
ll.actualizar(VIVO, gps(), 1.0)
r.check("solo lluvia (sin tormenta) no dispara el aviso de tormenta", ll.actualizar(VIVO, gps(lluvia=True), 2.0) == [])
b = m.AvisosMundo()
b.actualizar(VIVO, gps(), 1.0)
b.actualizar(VIVO, gps(tormenta=True), 2.0)      # aviso 1
b.actualizar(VIVO, gps(), 3.0)                    # se va
r.check("una tormenta que vuelve a empezar dentro del enfriamiento (10 min) no repite el aviso", b.actualizar(VIVO, gps(tormenta=True), 4.0) == [])
b.actualizar(VIVO, gps(), 5.0)
r.check("pasado el enfriamiento, la siguiente tormenta sí avisa", len(b.actualizar(VIVO, gps(tormenta=True), 2.0 + 601.0)) == 1)
c = m.AvisosMundo()
c.actualizar({"is_deployed": False}, gps(), 1.0)
r.check("si empezó la tormenta con Cobalt sin desplegar, al desplegarse ya no es transición (no avisa tarde)", c.actualizar({"is_deployed": False}, gps(tormenta=True), 2.0) == []
        and c.actualizar(VIVO, gps(tormenta=True), 3.0) == [])
d = m.AvisosMundo()
d.actualizar(VIVO, gps(tormenta=False), 1.0)
d.actualizar(VIVO, {"x": 0}, 2.0)                   # pierde el dato (otra dimensión / Java viejo): la historia se olvida
r.check("perder el dato borra la historia: al volver con tormenta no se avisa como si fuera nueva", d.actualizar(VIVO, gps(tormenta=True), 3.0) == [])
# Nether entre medias: mismo efecto
e = m.AvisosMundo()
e.actualizar(VIVO, gps(), 1.0)
e.actualizar(VIVO, gps(tiene_cielo=False), 2.0)
r.check("ir al Nether y volver con tormenta tampoco cuenta como transición", e.actualizar(VIVO, gps(tormenta=True), 3.0) == [])
# ambos avisos en el mismo ciclo
f = m.AvisosMundo()
f.actualizar(VIVO, gps(hora=11000), 1.0)
o = f.actualizar(VIVO, gps(hora=12000, tormenta=True, lluvia=True), 2.0)
r.check("anochece y empieza tormenta a la vez -> dos avisos en el mismo ciclo, ambos de chat", len(o) == 2 and all(x["action"] == "ninguna" for x in o))

s = m.AvisosMundo()
s.actualizar(VIVO, gps(hora=11000), 1.0, silenciados={"mundo"})
r.check("con 'mundo' silenciado no avisa de que anochece ni de la tormenta", s.actualizar(VIVO, gps(hora=11500), 2.0, silenciados={"mundo"}) == []
        and s.actualizar(VIVO, gps(hora=11500, lluvia=True, tormenta=True), 3.0, silenciados={"mundo"}) == [])
r.check("y NO gastó el aviso de la noche: al reactivarlo, si sigue en la ventana, avisa", len(s.actualizar(VIVO, gps(hora=11600), 4.0, silenciados=set())) == 1)
r.check("otras categorías silenciadas (hambre, inventario) no afectan a los avisos del mundo; silenciados raro (None, 5) tampoco",
        len(m.AvisosMundo().actualizar(VIVO, gps(hora=12000), 1.0, silenciados={"hambre", "inventario"})) == 1 and len(m.AvisosMundo().actualizar(VIVO, gps(hora=12000), 1.0, silenciados=None)) == 1
        and len(m.AvisosMundo().actualizar(VIVO, gps(hora=12000), 1.0, silenciados=5)) == 1)

frases_mundo = [x for k in ("anochece", "tormenta") for x in nox_voz.BANCO[k]]
r.check("las frases de H3 pasan el linter de voz (sin servilismo ni exageración) y caben en el chat",
        all(not nox_voz.linter_voz(x.format(cuando="en unos 2 min")) for x in frases_mundo) and all(len(x.format(cuando="en unos 2 min")) <= nox_voz.MAX_CHAT for x in frases_mundo))
generadas = []
for h in range(0, 24000, 100):
    generadas += [x["chat_message"] for x in m.AvisosMundo().actualizar(VIVO, gps(hora=h), 1.0)]
r.check("todos los avisos que puede generar en un día entero pasan el linter: " + str(len(generadas)), generadas and all(not nox_voz.linter_voz(t) for t in generadas))
r.check("el escáner de frases del código sabe leer nox_mundo (no hay cadenas sueltas para el jugador fuera del banco)", fc.frases("nox_mundo.py") == [])

import random  # noqa: E402
rng = random.Random(7)
cosas = [None, True, False, 0, -1, 1e18, float("nan"), "x", [], {}, 12000, 13000.5, {"a": 1}]
fallos = []
for i in range(3000):
    g = {"mundo": {k: rng.choice(cosas) for k in ("day_time", "raining", "thundering", "light", "sky", "has_skylight") if rng.random() < 0.8}}
    if rng.random() < 0.1:
        g = rng.choice(cosas)
    try:
        mm = m.interpretar(g)
        m.describir(mm)
        m.AvisosMundo().actualizar(rng.choice([VIVO, None, {}, {"is_deployed": "si"}]), g, rng.random() * 1000)
    except Exception as ex:  # noqa: BLE001
        fallos.append((g, repr(ex)))
r.check("fuzz (3000 entradas basura): nunca lanza: " + str(fallos[:2]), not fallos)
r.check("con day_time enorme (1e18) no se desborda ni da NaN: " + str(m.interpretar(gps(hora=10 ** 18)) is not None), m.interpretar(gps(hora=10 ** 18)).hora == (10 ** 18) % 24000)

r.terminar()
