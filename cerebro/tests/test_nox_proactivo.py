"""F2-4: avisos proactivos sobre el jugador (hambre, aire, fuego, inventario): transiciones con histéresis, enfriamientos, tope por ciclo y tolerancia a datos raros."""
import math
import random
import os
import sys

from _cargar import Resultados

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_proactivo as pa  # noqa: E402
import nox_voz  # noqa: E402

r = Resultados()
VIVO = {"is_deployed": True}


def g(**dueno):
    base = {"x": 0, "y": 64, "z": 0, "hp": 20, "max_hp": 20, "alive": True, "food": 20, "air": 300, "max_air": 300, "on_fire": False, "free_slots": 20}
    base.update(dueno)
    return {"x": 0, "y": 64, "z": 0, "owner": base}


def dicen(ordenes):
    return [o["chat_message"] for o in ordenes]


a = pa.AvisosJugador()
r.check("con todo en orden no dice nada", a.actualizar(VIVO, g(), 0.0) == [])
r.check("a 7 de comida todavía no", a.actualizar(VIVO, g(food=7), 1.0) == [])
o = a.actualizar(VIVO, g(food=6), 2.0)
r.check("a 6 de comida avisa (una orden de chat sin acción, con la frase del banco y el dato): " + str(dicen(o)), len(o) == 1 and o[0]["action"] == "ninguna" and dicen(o)[0] in [x.format(food=6) for x in nox_voz.BANCO["hambre"]])
r.check("mientras siga con hambre NO repite (ni a 5, ni a 4 ni a 3)", all(a.actualizar(VIVO, g(food=f), 3.0 + f) == [] for f in (5, 4, 3)))
r.check("comer un poco (a 8) no lo rearma: sigue sin repetir aunque haya pasado de sobra el enfriamiento (300 s)", a.actualizar(VIVO, g(food=8), 900.0) == [] and a.actualizar(VIVO, g(food=6), 901.0) == [])
a.actualizar(VIVO, g(food=12), 22.0)   # se recupera: se rearma
r.check("recuperado (12) y pasado el enfriamiento (300 s) vuelve a avisar en el siguiente apuro", len(a.actualizar(VIVO, g(food=6), 400.0)) == 1)
b = pa.AvisosJugador()
b.actualizar(VIVO, g(food=6), 0.0)
b.actualizar(VIVO, g(food=14), 1.0)
r.check("recuperado pero DENTRO del enfriamiento (300 s): no repite aunque vuelva a bajar", b.actualizar(VIVO, g(food=6), 100.0) == [] and len(b.actualizar(VIVO, g(food=6), 301.0)) == 1)

c = pa.AvisosJugador()
o = c.actualizar(VIVO, g(food=2), 0.0)
r.check("a 2 de comida (o menos) avisa SOLO del hambre crítica (no también de la leve): " + str(dicen(o)), len(o) == 1 and dicen(o)[0] in [x.format(food=2) for x in nox_voz.BANCO["hambre_critica"]])
r.check("y la leve no salta después mientras siga mal (a 1, a 5)", c.actualizar(VIVO, g(food=1), 1.0) == [] and c.actualizar(VIVO, g(food=5), 2.0) == [])
c.actualizar(VIVO, g(food=6), 3.0)    # sube a 6: rearma la crítica (>=6) pero no la leve (>=12)
r.check("a 6 la crítica se rearma; la leve sigue desarmada hasta 12", c.actualizar(VIVO, g(food=5), 500.0) == [])
r.check("crítica otra vez tras rearmarse y enfriarse", len(c.actualizar(VIVO, g(food=1), 501.0)) == 1)
d = pa.AvisosJugador()
o = d.actualizar(VIVO, g(food=0), 0.0)
r.check("comida 0 -> crítica con '0/20'", len(o) == 1 and "0/20" in dicen(o)[0])

e = pa.AvisosJugador()
r.check("aire lleno o a 91 no avisa; a 90 sí", e.actualizar(VIVO, g(air=300), 0.0) == [] and e.actualizar(VIVO, g(air=91), 1.0) == [] and len(e.actualizar(VIVO, g(air=90), 2.0)) == 1)
r.check("y no repite mientras siga sin aire; recuperar hasta 250 rearma (con enfriamiento de 20 s)", e.actualizar(VIVO, g(air=40), 3.0) == [] and e.actualizar(VIVO, g(air=250), 4.0) == []
        and e.actualizar(VIVO, g(air=80), 5.0) == [] and len(e.actualizar(VIVO, g(air=80), 30.0)) == 1)
f = pa.AvisosJugador()
r.check("un max_air pequeño (mod de respiración/efecto): con air == max_air no hay aviso aunque sea <= 90", f.actualizar(VIVO, g(air=60, max_air=60), 0.0) == [] and len(f.actualizar(VIVO, g(air=50, max_air=60), 1.0)) == 1)
r.check("y con ese max_air pequeño, recuperar el aire lleno (60) REARMA (no hace falta llegar a 250): vuelve a avisar pasado el enfriamiento", f.actualizar(VIVO, g(air=60, max_air=60), 2.0) == []
        and len(f.actualizar(VIVO, g(air=40, max_air=60), 30.0)) == 1)

h = pa.AvisosJugador()
o = h.actualizar(VIVO, g(on_fire=True), 0.0)
r.check("ardiendo -> avisa una vez: " + str(dicen(o)), len(o) == 1 and dicen(o)[0] == nox_voz.BANCO["fuego"][0])
r.check("sigue ardiendo -> no repite; se apaga y vuelve a arder DENTRO de 15 s -> no; pasados 15 s -> sí",
        h.actualizar(VIVO, g(on_fire=True), 1.0) == [] and h.actualizar(VIVO, g(on_fire=False), 2.0) == [] and h.actualizar(VIVO, g(on_fire=True), 5.0) == [] and len(h.actualizar(VIVO, g(on_fire=False), 6.0)) == 0
        and len(h.actualizar(VIVO, g(on_fire=True), 30.0)) == 1)
r.check("on_fire que no es booleano ('true', 1) NO cuenta", pa.AvisosJugador().actualizar(VIVO, g(on_fire="true"), 0.0) == [] and pa.AvisosJugador().actualizar(VIVO, g(on_fire=1), 0.0) == [])

i = pa.AvisosJugador()
r.check("3 huecos libres no avisa; 2 sí (con el dato)", i.actualizar(VIVO, g(free_slots=3), 0.0) == [] and dicen(i.actualizar(VIVO, g(free_slots=2), 1.0)) == [nox_voz.BANCO["inventario_lleno"][0].format(libres=2)])
r.check("no repite; vaciar hasta 6 rearma; el enfriamiento de 600 s se respeta", i.actualizar(VIVO, g(free_slots=0), 2.0) == [] and i.actualizar(VIVO, g(free_slots=6), 3.0) == [] and i.actualizar(VIVO, g(free_slots=1), 100.0) == []
        and len(i.actualizar(VIVO, g(free_slots=1), 602.0)) == 1)

j = pa.AvisosJugador()
mal = g(on_fire=True, air=10, food=1, free_slots=0)
o1 = dicen(j.actualizar(VIVO, mal, 0.0))
o2 = dicen(j.actualizar(VIVO, mal, 1.0))
o3 = dicen(j.actualizar(VIVO, mal, 2.0))
r.check("todo mal a la vez: como mucho 2 avisos por ciclo, por urgencia (fuego y aire; luego hambre crítica e inventario) y ninguno se pierde ni se repite: " + str((len(o1), len(o2), len(o3))),
        len(o1) == 2 and o1[0] == nox_voz.BANCO["fuego"][0] and o1[1] == nox_voz.BANCO["aire"][0] and len(o2) == 2 and "casi sin comida" in o2[0] and "inventario" in o2[1] and o3 == [])

s = pa.AvisosJugador()
r.check("con 'hambre' silenciada no avisa del hambre (ni de la crítica) y con 'inventario' silenciada tampoco del inventario",
        s.actualizar(VIVO, g(food=1), 0.0, silenciados={"hambre"}) == [] and s.actualizar(VIVO, g(free_slots=0), 1.0, silenciados={"inventario"}) == [])
o = s.actualizar(VIVO, g(food=1, free_slots=0), 2.0, silenciados=set())
r.check("y NO gastó los avisos: al reactivar, el problema que sigue se dice (crítica + inventario): " + str(dicen(o)), len(o) == 2 and "casi sin comida" in dicen(o)[0] and "inventario" in dicen(o)[1])
t = pa.AvisosJugador()
o = t.actualizar(VIVO, g(on_fire=True, air=10, food=1, free_slots=0), 0.0, silenciados={"hambre", "inventario", "mundo"})
r.check("los avisos de PELIGRO (fuego, aire) NO se pueden silenciar aunque se pidan todas las categorías: " + str(dicen(o)), dicen(o) == [nox_voz.BANCO["fuego"][0], nox_voz.BANCO["aire"][0]])
r.check("una categoría desconocida o 'peligro'/'fuego' en silenciados no apaga nada", len(pa.AvisosJugador().actualizar(VIVO, g(on_fire=True), 0.0, silenciados={"fuego", "peligro", "aire", "x"})) == 1)
r.check("silenciados con basura (None, número, texto, elementos no hashables) no rompe y equivale a nada silenciado",
        all(len(pa.AvisosJugador().actualizar(VIVO, g(food=1), 0.0, silenciados=x)) == 1 for x in (None, 5, "hambre", [[]], [None, 3], {"a": 1})))
r.check("silenciados como lista o tupla funciona igual que un conjunto", pa.AvisosJugador().actualizar(VIVO, g(food=1), 0.0, silenciados=["hambre"]) == [] and pa.AvisosJugador().actualizar(VIVO, g(food=1), 0.0, silenciados=("hambre",)) == [])

k = pa.AvisosJugador()
r.check("Cobalt sin desplegar: no avisa", k.actualizar({"is_deployed": False}, g(food=3), 0.0) == [] and k.actualizar({}, g(food=3), 1.0) == [] and k.actualizar(None, g(food=3), 2.0) == [])
r.check("y NO gastó el aviso: al desplegarse, si sigue con hambre, lo dice", len(k.actualizar(VIVO, g(food=3), 3.0)) == 1)
r.check("dueño muerto (alive false) o sin bloque 'owner': nada", pa.AvisosJugador().actualizar(VIVO, g(alive=False, food=1), 0.0) == [] and pa.AvisosJugador().actualizar(VIVO, {"x": 1}, 0.0) == []
        and pa.AvisosJugador().actualizar(VIVO, {"owner": "x"}, 0.0) == [] and pa.AvisosJugador().actualizar(VIVO, None, 0.0) == [])
viejo = {"x": 0, "owner": {"x": 0, "y": 64, "z": 0, "hp": 3, "max_hp": 20, "alive": True, "name": "Steve"}}
r.check("un Java antiguo (owner sin food/air/on_fire/free_slots): no avisa de nada", pa.AvisosJugador().actualizar(VIVO, viejo, 0.0) == [])

raros = [None, True, "x", -1, 21, 1e30, float("nan"), float("inf"), [], {}]
r.check("comida y huecos fuera de rango (-1, 21 comida, 1e30), texto, bool, NaN o infinito no disparan nada",
        all(pa.AvisosJugador().actualizar(VIVO, g(food=v, free_slots=v), 0.0) == [] for v in (None, True, "x", -1, 21, 1e30, float("nan"), float("inf"), [], {})))
r.check("aire que no es un número válido (None, bool, texto, NaN, infinito, 1e30, lista) no dispara nada", all(pa.AvisosJugador().actualizar(VIVO, g(air=v), 0.0) == [] for v in (None, True, "x", 1e30, float("nan"), float("inf"), [], {})))
r.check("un max_air inválido (0, negativo, texto) desactiva el aviso de aire (no se puede saber si falta aire)", all(pa.AvisosJugador().actualizar(VIVO, g(air=10, max_air=v), 0.0) == [] for v in (0, -5, "x", None, float("nan"))))
r.check("air negativo pequeño (ahogándose) sí cuenta: -5 <= 90", len(pa.AvisosJugador().actualizar(VIVO, g(air=-5), 0.0)) == 1)
r.check("_num acota y rechaza bool", pa._num({"a": 5}, "a", 0, 10) == 5 and pa._num({"a": True}, "a", 0, 10) is None and pa._num({"a": 11}, "a", 0, 10) is None and pa._num({}, "a", 0, 10) is None
        and pa._num(None, "a", 0, 10) is None and pa._num({"a": math.nan}, "a", 0, 10) is None)

todas = [x.format(food=3, libres=1) for k in ("hambre", "hambre_critica", "aire", "fuego", "inventario_lleno") for x in nox_voz.BANCO[k]]
r.check("las frases de F2-4 pasan el linter de voz y caben en el chat", all(not nox_voz.linter_voz(x) and len(x) <= nox_voz.MAX_CHAT for x in todas))

rng = random.Random(9)
cosas = [None, True, False, 0, -3, 2, 6, 90, 300, 1e30, float("nan"), "x", [], {}]
fallos = []
for _ in range(4000):
    av = pa.AvisosJugador()
    try:
        for paso in range(6):
            dueno = {k: rng.choice(cosas) for k in ("food", "air", "max_air", "on_fire", "free_slots", "alive") if rng.random() < 0.8}
            gp = {"owner": dueno} if rng.random() < 0.9 else rng.choice(cosas)
            res = av.actualizar(rng.choice([VIVO, None, {}, {"is_deployed": "si"}]), gp, rng.random() * 2000)
            assert isinstance(res, list) and len(res) <= pa.AvisosJugador.MAX_POR_CICLO and all(x["action"] == "ninguna" for x in res)
    except Exception as ex:  # noqa: BLE001
        fallos.append(repr(ex))
r.check("fuzz (4000 secuencias de datos basura): nunca lanza, respeta el tope y solo emite chat: " + str(fallos[:2]), not fallos)

r.terminar()
