"""Bloque N (Python): sitio llano, estirado de planos, caminos con puentes, replicar/reparar estructuras, portales 8:1 e intenciones del chat."""
import heapq
import math
import os
import random
import sys

from _cargar import RAIZ, Resultados

sys.path.insert(0, os.path.join(RAIZ, "cerebro"))
import nox_obra as ob  # noqa: E402

r = Resultados()
S, A, L, V, O, D = ob.SUELO, ob.AGUA, ob.LAVA, ob.VACIO, ob.OBSTACULO, ob.DESCONOCIDO


def mapa(alturas, tipos=None, x1=0, z1=0):
    filas = len(alturas)
    cols = len(alturas[0])
    tipos = tipos or [[S] * cols for _ in range(filas)]
    return ob.MapaRelieve(x1, z1, x1 + cols - 1, z1 + filas - 1, alturas, tipos)


def plano_llano(n, altura=64, lado=None):
    lado = lado or n
    return mapa([[altura] * n for _ in range(lado)])


ok_json = {"status": "success", "x1": 10, "z1": 20, "x2": 12, "z2": 21, "y": [[64, 65, 66], [64, 64, 64]], "t": [[0, 0, 0], [0, 1, 0]]}
m0 = ob.MapaRelieve.desde_json(ok_json)
r.check("mapa: se lee de terrain_map.json con su caja (3 x 2)", m0 is not None and (m0.ancho, m0.largo) == (3, 2) and m0.altura(12, 20) == 66 and m0.tipo(11, 21) == A)
r.check("mapa: 'dentro' respeta los límites", m0.dentro(10, 20) and m0.dentro(12, 21) and not m0.dentro(13, 20) and not m0.dentro(10, 22))
r.check("mapa: status 'failed' -> None", ob.MapaRelieve.desde_json(dict(ok_json, status="failed")) is None)
r.check("mapa: filas de distinto tamaño -> None", ob.MapaRelieve.desde_json(dict(ok_json, y=[[64, 65], [64, 64, 64]])) is None)
r.check("mapa: faltan filas -> None", ob.MapaRelieve.desde_json(dict(ok_json, y=[[64, 65, 66]])) is None)
r.check("mapa: falta una clave o llega basura -> None", ob.MapaRelieve.desde_json({"status": "success"}) is None and ob.MapaRelieve.desde_json(None) is None
        and ob.MapaRelieve.desde_json(dict(ok_json, x2=5)) is None)

llano = plano_llano(10)
s = ob.mejor_sitio(llano, 4, 4)
r.check("sitio: un mapa llano da coste 0 a la altura del suelo", s is not None and s["coste"] == 0 and s["y"] == 64 and s["cortar"] == 0 and s["rellenar"] == 0)
s = ob.mejor_sitio(llano, 4, 4, preferido=(9, 9))
r.check("sitio: en empate elige el más cercano al punto preferido (esquina 6,6)", (s["x0"], s["z0"]) == (6, 6))
r.check("sitio: una ventana mayor que el mapa -> None", ob.mejor_sitio(llano, 11, 3) is None and ob.mejor_sitio(llano, 3, 11) is None and ob.mejor_sitio(llano, 0, 3) is None)

# colina a la izquierda (h=70) y llano a la derecha (h=64)
colina = mapa([[70 + (x + z) % 3 for x in range(5)] + [64] * 5 for z in range(10)])
s = ob.mejor_sitio(colina, 4, 4)
r.check("sitio: con un cerro irregular a la izquierda elige el llano (coste 0, x0 >= 5, y=64)", s["coste"] == 0 and s["x0"] >= 5 and s["y"] == 64)
s = ob.mejor_sitio(mapa([[70 + (x + z) % 3 for x in range(4)] for z in range(4)]), 4, 4)
r.check("sitio: en un cerro irregular de 4x4 [70..72] el coste es el de nivelar a la mediana (y=71: cortar 4 y rellenar 5 = 9... comprobado a mano)",
        s["y"] == 71 and s["coste"] == sum(abs(70 + (x + z) % 3 - 71) for x in range(4) for z in range(4)))
s = ob.mejor_sitio(mapa([[64, 64], [64, 70]]), 2, 2)
r.check("sitio: ventana [64,64,64,70]: nivela a la MEDIANA 64 (cortar 6, rellenar 0)", s["y"] == 64 and s["cortar"] == 6 and s["rellenar"] == 0 and s["coste"] == 6)
s = ob.mejor_sitio(mapa([[64, 64], [64, 58]]), 2, 2)
r.check("sitio: ventana [64,64,64,58]: mediana 64, se RELLENAN 6", s["y"] == 64 and s["cortar"] == 0 and s["rellenar"] == 6)
r.check("sitio: un desnivel de 16 (más que el máximo) se rechaza", ob.mejor_sitio(mapa([[64, 64], [64, 80]]), 2, 2) is None)
r.check("sitio: el coste máximo se respeta", ob.mejor_sitio(mapa([[64, 64], [64, 70]]), 2, 2, max_coste=5) is None and ob.mejor_sitio(mapa([[64, 64], [64, 70]]), 2, 2, max_coste=6) is not None)

# obstáculos, agua, lava, vacío y chunks sin cargar NO valen
for codigo, nombre in ((A, "agua"), (L, "lava"), (V, "vacío"), (O, "una construcción"), (D, "un chunk sin cargar")):
    tipos = [[S] * 8 for _ in range(4)]
    tipos[1][3] = codigo
    m1 = mapa([[64] * 8 for _ in range(4)], tipos)
    s = ob.mejor_sitio(m1, 3, 3)
    ok = s is not None and not (s["x0"] <= 3 <= s["x0"] + 2 and s["z0"] <= 1 <= s["z0"] + 2)
    r.check(f"sitio: la ventana evita {nombre}", ok)
r.check("sitio: si TODO es agua no hay sitio", ob.mejor_sitio(mapa([[64] * 5 for _ in range(5)], [[A] * 5 for _ in range(5)]), 2, 2) is None)

# base: la obra debe quedar a más de 34 de la base
grande = plano_llano(60)
base = (0, 64, 0)
s = ob.mejor_sitio(grande, 4, 4, base=base, preferido=(0, 0))
dx, dz = max(s["x0"] - 0, 0), max(s["z0"] - 0, 0)
r.check("sitio: respeta la distancia a la base (>34)", math.sqrt(dx * dx + dz * dz + 1) > 34.0)
# el más cercano a la base permitido: el oráculo mira todas las ventanas
mejor_d = None
for x0 in range(0, 57):
    for z0 in range(0, 57):
        d = math.sqrt(max(x0, 0) ** 2 + max(z0, 0) ** 2 + 1)
        if d > 34.0:
            c = math.hypot(x0 + 2 - 0, z0 + 2 - 0)
            mejor_d = c if mejor_d is None else min(mejor_d, c)
r.check("sitio: entre los válidos elige el más cercano al punto preferido (oráculo por fuerza bruta)", abs(math.hypot(s["x0"] + 2, s["z0"] + 2) - mejor_d) < 1e-9)
r.check("sitio: una base en el centro de un mapa pequeño deja sin sitio", ob.mejor_sitio(plano_llano(20), 4, 4, base=(10, 64, 10)) is None)

# oráculo: coste mínimo por fuerza bruta en mapas aleatorios
azar = random.Random(7)
coincide = True
for _ in range(40):
    hs = [[64 + azar.randint(0, 5) for _ in range(12)] for _ in range(12)]
    ts = [[A if azar.random() < 0.08 else S for _ in range(12)] for _ in range(12)]
    mp = mapa(hs, ts)
    w, l = azar.randint(2, 4), azar.randint(2, 4)
    esperado = None
    for z0 in range(12 - l + 1):
        for x0 in range(12 - w + 1):
            if any(ts[z][x] != S for z in range(z0, z0 + l) for x in range(x0, x0 + w)):
                continue
            valores = [hs[z][x] for z in range(z0, z0 + l) for x in range(x0, x0 + w)]
            c = min(sum(abs(v - y) for v in valores) for y in range(60, 75))
            esperado = c if esperado is None else min(esperado, c)
    obtenido = ob.mejor_sitio(mp, w, l)
    if (esperado is None) != (obtenido is None) or (obtenido is not None and obtenido["coste"] != esperado):
        coincide = False
r.check("sitio: el coste coincide con el mínimo por fuerza bruta en 40 mapas aleatorios", coincide)

m2 = mapa([[60, 62, 70], [64, 64, 64]], [[S, S, A], [S, S, S]])
r.check("nivel: mediana de las columnas de suelo (el agua no cuenta): [60,62,64,64,64] -> 64", ob.nivel_objetivo(m2, 0, 0, 2, 1) == 64)
r.check("nivel: solo cuenta lo que cae dentro del mapa", ob.nivel_objetivo(m2, -5, -5, 0, 0) == 60)
r.check("nivel: sin suelo -> None", ob.nivel_objetivo(m2, 2, 0, 2, 0) is None and ob.nivel_objetivo(m2, 50, 50, 60, 60) is None)
r.check("nivel: acepta las esquinas invertidas", ob.nivel_objetivo(m2, 1, 1, 0, 0) == ob.nivel_objetivo(m2, 0, 0, 1, 1))

def casa():
    celdas = {}
    for x in range(5):
        for z in range(5):
            celdas[(x, 0, z)] = "minecraft:cobblestone"
            if x in (0, 4) or z in (0, 4):
                for y in (1, 2):
                    celdas[(x, y, z)] = "minecraft:stone_bricks"
    celdas[(2, 1, 0)] = "minecraft:oak_door"
    celdas[(3, 1, 4)] = "minecraft:glass_pane"
    return ob._plano_desde_celdas(celdas, "casa")


c = casa()
n0 = sum(len(cp["blocks"]) for cp in c["layers"])
nuevo, motivo = ob.estirar_blueprint(c, 8, 5)
celdas_n = ob._celdas_de_plano(nuevo)
puertas = [p for p, i in celdas_n.items() if "door" in i]
ventanas = [p for p, i in celdas_n.items() if "glass" in i]
r.check("estirar: 5x5 -> 8x5 da un plano de 8 de ancho", ob.dimensiones_de_plano(nuevo)[0] == 8 and ob.dimensiones_de_plano(nuevo)[2] == 5)
r.check("estirar: la columna que se repite es la NEUTRA (x=1, sin puerta ni ventana): una sola puerta y una sola ventana", len(puertas) == 1 and len(ventanas) == 1)
r.check("estirar: la puerta (x=2) y la ventana (x=3) se desplazan +3 al estar a la derecha de la columna repetida", puertas[0] == (5, 1, 0) and ventanas[0] == (6, 1, 4))
col_x1 = sum(1 for (x, _, _) in ob._celdas_de_plano(c) if x == 1)
r.check("estirar: el recuento es el original + 3 copias de la columna repetida", sum(len(cp["blocks"]) for cp in nuevo["layers"]) == n0 + 3 * col_x1)
n2, _ = ob.estirar_blueprint(c, 5, 5)
r.check("estirar: mismo tamaño = mismo plano", ob._celdas_de_plano(n2) == ob._celdas_de_plano(c))
n3, _ = ob.estirar_blueprint(c, 7, 9)
r.check("estirar: también en la otra dimensión (7 x 9)", ob.dimensiones_de_plano(n3)[0] == 7 and ob.dimensiones_de_plano(n3)[2] == 9)
r.check("estirar: las esquinas se conservan (los cuatro pilares siguen en las esquinas del plano nuevo)",
        all(ob._celdas_de_plano(n3).get(p, "").endswith("stone_bricks") for p in ((0, 1, 0), (6, 1, 0), (0, 1, 8), (6, 1, 8))))
r.check("estirar: NO encoge", ob.estirar_blueprint(c, 4, 5)[0] is None and "agrandar" in ob.estirar_blueprint(c, 4, 5)[1])
r.check("estirar: el lado máximo es 64", ob.estirar_blueprint(c, 65, 5)[0] is None)
r.check("estirar: un plano vacío se rechaza", ob.estirar_blueprint({"layers": []}, 5, 5)[0] is None and ob.estirar_blueprint(None, 5, 5)[0] is None)
macizo = ob._plano_desde_celdas({(x, y, z): "minecraft:stone" for x in range(20) for y in range(14) for z in range(20)}, "bloque")
r.check("estirar: un plano que pasaría de 6000 bloques se rechaza", ob.estirar_blueprint(macizo, 22, 20)[0] is None and "6000" in ob.estirar_blueprint(macizo, 22, 20)[1])
# fórmula del recuento en planos aleatorios
azar = random.Random(11)
formula_ok = True
for _ in range(25):
    w, l = azar.randint(2, 6), azar.randint(2, 6)
    cel = {(x, y, z): "minecraft:stone" for x in range(w) for z in range(l) for y in range(azar.randint(1, 3)) if azar.random() < 0.8 or (x, z) == (0, 0)}
    cel[(w - 1, 0, l - 1)] = "minecraft:stone"
    pl = ob._plano_desde_celdas(cel, "azar")
    aw, _, al = ob.dimensiones_de_plano(pl)
    nw, nl = aw + azar.randint(0, 4), al + azar.randint(0, 4)
    est, _ = ob.estirar_blueprint(pl, nw, nl)
    xm, zm = ob._columna_de_estirado(ob._celdas_de_plano(pl), "x", aw), ob._columna_de_estirado(ob._celdas_de_plano(pl), "z", al)
    esperado = sum((nw - aw + 1 if x == xm else 1) * (nl - al + 1 if z == zm else 1) for (x, _, z) in ob._celdas_de_plano(pl))
    if est is None or sum(len(cp["blocks"]) for cp in est["layers"]) != esperado:
        formula_ok = False
r.check("estirar: el recuento de bloques cumple la fórmula en 25 planos aleatorios", formula_ok)

def _coste_camino(mp, camino):
    total = 0
    for a, b in zip(camino, camino[1:]):
        total += 1 + 2 * abs(mp.altura(b["x"], b["z"]) - mp.altura(a["x"], a["z"])) + (3 if mp.tipo(b["x"], b["z"]) == A else 0)
    return total


def _dijkstra(mp, ini, fin, puentes=True):
    dist = {ini: 0}
    cola = [(0, ini)]
    while cola:
        d, p = heapq.heappop(cola)
        if p == fin:
            return d
        if d > dist[p]:
            continue
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (p[0] + dx, p[1] + dz)
            if not mp.dentro(*q):
                continue
            t = mp.tipo(*q)
            if not (t == S or (puentes and t == A)):
                continue
            dh = abs(mp.altura(*q) - mp.altura(*p))
            if dh > 1:
                continue
            nd = d + 1 + 2 * dh + (3 if t == A else 0)
            if nd < dist.get(q, 1e18):
                dist[q] = nd
                heapq.heappush(cola, (nd, q))
    return None


f = plano_llano(10, 64, 3)
cam = ob.trazar_camino(f, (0, 0), (9, 0))
r.check("camino: en llano es una recta de 10 celdas a y=65 (superficie + 1) sin puentes", cam is not None and len(cam) == 10 and all(c["y"] == 65 and not c["puente"] and c["z"] == 0 for c in cam))
r.check("camino: empieza en el inicio y acaba en el fin", (cam[0]["x"], cam[0]["z"]) == (0, 0) and (cam[-1]["x"], cam[-1]["z"]) == (9, 0))
r.check("camino: inicio == fin da una sola celda", len(ob.trazar_camino(f, (2, 1), (2, 1))) == 1)

rio = mapa([[64] * 10 for _ in range(4)], [[A if 4 <= x <= 6 else S for x in range(10)] for _ in range(4)])
cam = ob.trazar_camino(rio, (0, 1), (9, 1))
r.check("camino: cruza un río de 3 de ancho con exactamente 3 celdas de puente", cam is not None and sum(1 for c in cam if c["puente"]) == 3 and all(4 <= c["x"] <= 6 for c in cam if c["puente"]))
r.check("camino: sin permitir puentes, el río lo impide", ob.trazar_camino(rio, (0, 1), (9, 1), permitir_puentes=False) is None)

muro_lava = mapa([[64] * 10 for _ in range(5)], [[L if x == 5 else S for x in range(10)] for _ in range(5)])
r.check("camino: un muro de lava completo NO se cruza", ob.trazar_camino(muro_lava, (0, 2), (9, 2)) is None)
tipos = [[L if x == 5 else S for x in range(10)] for _ in range(5)]
tipos[4][5] = S
rodeo = ob.trazar_camino(mapa([[64] * 10 for _ in range(5)], tipos), (0, 0), (9, 0))
r.check("camino: con un hueco en el muro de lava rodea por el hueco y nunca pisa lava", rodeo is not None and all(tipos[c["z"]][c["x"]] != L for c in rodeo) and any(c["z"] == 4 for c in rodeo))

escalon = mapa([[64] * 5 + [66] * 5 for _ in range(4)])
r.check("camino: un escalón de 2 de alto es impasable", ob.trazar_camino(escalon, (0, 1), (9, 1)) is None)
rampa = [[64] * 5 + [66] * 5 for _ in range(4)]
rampa[2][5] = 65
rampa[2][4] = 64
cam = ob.trazar_camino(mapa(rampa), (0, 0), (9, 0))
r.check("camino: encuentra la rampa de 1 en 1 y pasa por ella", cam is not None and any((c["x"], c["z"]) == (5, 2) for c in cam) and all(abs(a["y"] - b["y"]) <= 1 for a, b in zip(cam, cam[1:])))
r.check("camino: inicio o fin en lava/fuera del mapa -> None", ob.trazar_camino(muro_lava, (5, 2), (9, 2)) is None and ob.trazar_camino(f, (0, 0), (99, 0)) is None)
r.check("camino: un obstáculo (casa) se rodea", ob.trazar_camino(mapa([[64] * 7 for _ in range(3)], [[O if x == 3 and z < 2 else S for x in range(7)] for z in range(3)]), (0, 0), (6, 0)) is not None)

azar = random.Random(3)
optimo = True
hubo_ruta = hubo_sin = 0
for _ in range(60):
    hs = [[64 + azar.choice([0, 0, 0, 1, 2]) for _ in range(10)] for _ in range(10)]
    ts = [[azar.choices([S, A, L, O], [0.68, 0.14, 0.09, 0.09])[0] for _ in range(10)] for _ in range(10)]
    mp = mapa(hs, ts)
    ini, fin = (azar.randrange(10), azar.randrange(10)), (azar.randrange(10), azar.randrange(10))
    if ts[ini[1]][ini[0]] not in (S, A) or ts[fin[1]][fin[0]] not in (S, A):
        continue
    cam = ob.trazar_camino(mp, ini, fin)
    ref = _dijkstra(mp, ini, fin)
    if (cam is None) != (ref is None):
        optimo = False
        continue
    if cam is None:
        hubo_sin += 1
        continue
    hubo_ruta += 1
    valido = (cam[0]["x"], cam[0]["z"]) == ini and (cam[-1]["x"], cam[-1]["z"]) == fin
    for a, b in zip(cam, cam[1:]):
        valido = valido and abs(a["x"] - b["x"]) + abs(a["z"] - b["z"]) == 1 and abs(mp.altura(b["x"], b["z"]) - mp.altura(a["x"], a["z"])) <= 1
    valido = valido and all(ts[c["z"]][c["x"]] in (S, A) and c["puente"] == (ts[c["z"]][c["x"]] == A) for c in cam)
    if not valido or _coste_camino(mp, cam) != ref:
        optimo = False
r.check(f"camino: coste óptimo y camino válido frente a Dijkstra en 60 mapas aleatorios ({hubo_ruta} con ruta, {hubo_sin} sin ella)", optimo and hubo_ruta >= 10 and hubo_sin >= 1)

# ancho 3
anchoso = plano_llano(12, 64, 7)
recta = ob.trazar_camino(anchoso, (0, 3), (11, 3))
ancho3 = ob.ensanchar_camino(anchoso, recta, 3)
r.check("camino ancho 3: una recta de 12 da 3 x 12 = 36 celdas sin repetir", len(ancho3) == 36 and len({(c["x"], c["z"]) for c in ancho3}) == 36)
r.check("camino ancho 1: no cambia nada", ob.ensanchar_camino(anchoso, recta, 1) == recta)
centro = plano_llano(20, 64, 20)
tramo = ob.trazar_camino(centro, (5, 10), (14, 10))
lat = ob.ensanchar_camino(centro, tramo, 3)
r.check("camino ancho 3: sin 'tapones' en los extremos (10 celdas de largo = 30 celdas, ninguna en x=4 ni x=15)", len(lat) == 30 and not any(c["x"] in (4, 15) for c in lat))
esquina = [{"x": 5, "z": 5, "y": 65, "puente": False}, {"x": 6, "z": 5, "y": 65, "puente": False}, {"x": 6, "z": 6, "y": 65, "puente": False}]
ancho_e = ob.ensanchar_camino(centro, esquina, 3)
r.check("camino ancho 3: en una esquina cubre los laterales de los dos tramos sin repetir celdas", len({(c["x"], c["z"]) for c in ancho_e}) == len(ancho_e) and (7, 6) in {(c["x"], c["z"]) for c in ancho_e}
        and (5, 6) in {(c["x"], c["z"]) for c in ancho_e} and (6, 4) in {(c["x"], c["z"]) for c in ancho_e})
rio2 = mapa([[64] * 10 for _ in range(5)], [[A if 4 <= x <= 5 else S for x in range(10)] for _ in range(5)])
cam_r = ob.trazar_camino(rio2, (0, 2), (9, 2))
ancho_r = ob.ensanchar_camino(rio2, cam_r, 3)
r.check("camino ancho 3: sobre el agua se ensancha SOLO en el puente, y en tierra no se añade agua",
        all((c["puente"] == (rio2.tipo(c["x"], c["z"]) == A)) for c in ancho_r) and sum(1 for c in ancho_r if c["puente"]) == 2 * 3 and len(ancho_r) == len({(c["x"], c["z"]) for c in ancho_r}))

# camino_a_blueprint
bp, origen = ob.camino_a_blueprint(cam_r)
celdas_bp = ob._celdas_de_plano(bp)
r.check("plano de camino: origen = esquina mínima y los puentes son tablones, el resto adoquín",
        origen == (0, 65, 2) and sorted(set(celdas_bp.values())) == ["minecraft:cobblestone", "minecraft:oak_planks"]
        and sum(1 for i in celdas_bp.values() if i.endswith("oak_planks")) == 2 and len(celdas_bp) == len(cam_r))
r.check("plano de camino: vacío -> None con motivo", ob.camino_a_blueprint([])[0] is None)
r.check("plano de camino: más de 6000 celdas -> None", ob.camino_a_blueprint([{"x": i, "z": 0, "y": 64, "puente": False} for i in range(6001)])[0] is None)
r.check("celda cercana: encuentra suelo cerca de una celda de agua", ob.celda_transitable_cercana(rio2, 4, 2) == (3, 2) and ob.celda_transitable_cercana(rio2, 4, 2, permitir_agua=True) == (4, 2))
r.check("celda cercana: sin suelo en el radio -> None", ob.celda_transitable_cercana(mapa([[64] * 3], [[A, A, A]]), 1, 0) is None)

def celdas_de(caja):
    x1, y1, z1, x2, y2, z2 = caja
    return {(x, y, z) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1) for z in range(z1, z2 + 1)}


caja = (0, 0, 0, 29, 19, 24)
partes = ob.dividir_caja(caja, 3000)
union = set()
solapes = 0
for p in partes:
    cs = celdas_de(p)
    solapes += len(union & cs)
    union |= cs
r.check(f"dividir: una caja de 30x20x25 se parte en {len(partes)} trozos de <=3000 sin solapes ni huecos", solapes == 0 and union == celdas_de(caja) and all(len(celdas_de(p)) <= 3000 for p in partes) and len(partes) > 1)
r.check("dividir: una caja pequeña queda entera y acepta esquinas invertidas", ob.dividir_caja((5, 5, 5, 0, 0, 0), 6000) == [(0, 0, 0, 5, 5, 5)])

esc1 = {"status": "success", "x0": 100, "y0": 64, "z0": 200, "palette": ["minecraft:stone", "oak_planks"], "blocks": [[0, 0, 0, 0], [1, 0, 0, 1]], "unloaded": 0, "truncated": False}
esc2 = {"status": "success", "x0": 110, "y0": 64, "z0": 200, "palette": ["minecraft:glass"], "blocks": [[0, 1, 0, 0]], "unloaded": 3, "truncated": True}
res = ob.unir_escaneos([esc1, esc2])
mundo, sin_cargar, trunc = res
r.check("unir: junta las paletas y coloca cada bloque en su coordenada del mundo (con prefijo minecraft:)",
        mundo == {(100, 64, 200): "minecraft:stone", (101, 64, 200): "minecraft:oak_planks", (110, 65, 200): "minecraft:glass"})
r.check("unir: suma los chunks sin cargar y propaga 'truncado'", sin_cargar == 3 and trunc is True)
r.check("unir: un escaneo fallido, con índice de paleta roto o vacío -> None", ob.unir_escaneos([esc1, {"status": "failed"}]) is None
        and ob.unir_escaneos([dict(esc1, blocks=[[0, 0, 0, 9]])]) is None and ob.unir_escaneos([None]) is None)

mundo_casa = dict(ob._celdas_de_plano(casa()))
mundo_mundo = {(500 + x, 70 + y, -30 + z): i for (x, y, z), i in mundo_casa.items()}
mundo_mundo[(499, 70, -30)] = "minecraft:chest"
mundo_mundo[(499, 71, -30)] = "minecraft:water"
mundo_mundo[(499, 72, -30)] = "minecraft:white_shulker_box"
mundo_mundo[(499, 73, -30)] = "minecraft:oak_sign"
mundo_mundo[(499, 74, -30)] = "minecraft:tnt"
plano_copia, info = ob.escaneo_a_blueprint(mundo_mundo, "casa_copiada")
r.check("copiar: los cofres, el agua, los shulkers, los carteles y el TNT se omiten y se cuentan", info["copiados"] == len(mundo_casa)
        and info["omitidos"] == {"chest": 1, "water": 1, "white_shulker_box": 1, "oak_sign": 1, "tnt": 1})
r.check("copiar: el origen es la esquina mínima de lo copiado y las coordenadas del plano son relativas", info["origen"] == (500, 70, -30) and ob._celdas_de_plano(plano_copia) == mundo_casa)
r.check("copiar: un escaneo vacío o solo de bloques no copiables -> None", ob.escaneo_a_blueprint({})[0] is None and ob.escaneo_a_blueprint({(0, 0, 0): "minecraft:chest"})[0] is None)
r.check("copiar: más de 6000 bloques -> None", ob.escaneo_a_blueprint({(x, 0, z): "minecraft:stone" for x in range(80) for z in range(80)})[0] is None)

pl = casa()
origen = (500, 70, -30)
mundo_ok = {(origen[0] + x, origen[1] + y, origen[2] + z): i for (x, y, z), i in ob._celdas_de_plano(pl).items()}
d = ob.diferencias(pl, origen, mundo_ok)
r.check("reparar: una obra intacta no tiene diferencias", d["faltan"] == [] and d["distintos"] == [] and d["bien"] == len(mundo_ok))
roto = dict(mundo_ok)
falta1, falta2 = (500, 71, -30), (504, 72, -26)
del roto[falta1]
del roto[falta2]
roto[(502, 71, -30)] = "minecraft:dirt"  # donde iba la puerta ahora hay tierra
d = ob.diferencias(pl, origen, roto)
r.check("reparar: 2 huecos vacíos = 'faltan' (con su id esperado) y 1 bloque distinto = 'distintos' (no se toca)",
        sorted((f[0], f[1], f[2]) for f in d["faltan"]) == sorted([falta1, falta2]) and all(f[3] == "minecraft:stone_bricks" for f in d["faltan"])
        and d["distintos"] == [(502, 71, -30, "minecraft:oak_door", "minecraft:dirt")] and d["bien"] == len(mundo_ok) - 3)
plano_rep, origen_rep = ob.reparacion_a_blueprint(d["faltan"], "rep")
r.check("reparar: el plano de reparación solo lleva lo que falta y su origen es la esquina mínima", len(ob._celdas_de_plano(plano_rep)) == 2 and origen_rep == (500, 71, -30))
aplicado = dict(roto)
for (x, y, z), i in ob._celdas_de_plano(plano_rep).items():
    aplicado[(origen_rep[0] + x, origen_rep[1] + y, origen_rep[2] + z)] = i
d2 = ob.diferencias(pl, origen, aplicado)
r.check("reparar: tras aplicar la reparación ya no falta nada (solo queda el bloque distinto, que no se tocó)", d2["faltan"] == [] and len(d2["distintos"]) == 1)
r.check("reparar: sin nada que reponer -> None", ob.reparacion_a_blueprint([])[0] is None)
copia, inf = ob.escaneo_a_blueprint(mundo_ok, "x")
d3 = ob.diferencias(copia, inf["origen"], mundo_ok)
r.check("replicar y comprobar: lo copiado coincide bloque a bloque con el original", d3["faltan"] == [] and d3["distintos"] == [] and d3["bien"] == inf["copiados"])
r.check("caja de obra: la caja que ocupa el plano colocado en su origen", ob.caja_de_obra(pl, origen) == (500, 70, -30, 504, 72, -26) and ob.caja_de_obra({"layers": []}, origen) is None)

obras = ob.registrar_obra({}, "casa_azul", "casa", (500, 70, -30), "minecraft:overworld", 1000.0)
obras2 = ob.registrar_obra(obras, "torre", "torre_alta", (10, 64, 10), "minecraft:overworld", 2000.0)
r.check("registro: registrar devuelve una copia y no muta el original", "torre" not in obras and set(obras2) == {"casa_azul", "torre"} and obras2["casa_azul"]["x"] == 500)
r.check("registro: buscar por nombre exacto, por parte del nombre y '' = la más reciente", ob.buscar_obra(obras2, "casa_azul")[0] == "casa_azul"
        and ob.buscar_obra(obras2, "la casa")[0] == "casa_azul" and ob.buscar_obra(obras2, "")[0] == "torre" and ob.buscar_obra(obras2, "Torre")[0] == "torre")
r.check("registro: desconocida o vacía -> (None, None)", ob.buscar_obra(obras2, "castillo") == (None, None) and ob.buscar_obra({}, "") == (None, None) and ob.buscar_obra(None, "x") == (None, None))

r.check("portal: Overworld (800, -160) -> Nether (100, -20), búsqueda 16", ob.coordenadas_portal(800, -160, "minecraft:overworld") == {"dimension_destino": "nether", "x": 100, "z": -20, "radio_busqueda": 16})
r.check("portal: Nether (100, -20) -> Overworld (800, -160), búsqueda 128", ob.coordenadas_portal(100, -20, "minecraft:the_nether") == {"dimension_destino": "overworld", "x": 800, "z": -160, "radio_busqueda": 128})
r.check("portal: los negativos se redondean hacia abajo (floor): -5/8 -> -1, 7/8 -> 0", ob.coordenadas_portal(-5, 7, "overworld")["x"] == -1 and ob.coordenadas_portal(-5, 7, "overworld")["z"] == 0)
r.check("portal: en el End no hay conversión", ob.coordenadas_portal(0, 0, "minecraft:the_end") is None and ob.coordenadas_portal(0, 0, "minecraft:aether") is None)
tp = ob.texto_portal(800, -160, "minecraft:overworld", "la mina")
r.check("portal: el texto lleva el punto de origen, el convertido y el radio", "X=800, Z=-160 (la mina)" in tp and "X=100, Z=-20" in tp and "Nether" in tp and "16 bloques" in tp)
r.check("portal: el texto del End explica que no se puede", "solo se enlazan" in ob.texto_portal(0, 0, "minecraft:the_end"))

io = ob.interpretar_obra
r.check("chat aplanar: 'aplana 12x12' -> 12 x 12", io("aplana 12x12") == {"tipo": "aplanar", "ancho": 12, "largo": 12})
r.check("chat aplanar: 'nivela un área de 10 por 20'", io("nivela un área de 10 por 20") == {"tipo": "aplanar", "ancho": 10, "largo": 20})
r.check("chat aplanar: 'aplana 15 bloques' -> cuadrado 15; sin medida -> 9x9; se limita a 64",
        io("aplana 15 bloques") == {"tipo": "aplanar", "ancho": 15, "largo": 15} and io("aplana el terreno") == {"tipo": "aplanar", "ancho": 9, "largo": 9}
        and io("aplana 200x3") == {"tipo": "aplanar", "ancho": 64, "largo": 3})
r.check("chat rellenar: 'rellena la lava' -> lava radio 8", io("rellena la lava") == {"tipo": "rellenar", "fluido": "lava", "radio": 8})
r.check("chat rellenar: 'tapa el agua en 5 bloques' -> water radio 5; radio máx 16", io("tapa el agua en 5 bloques") == {"tipo": "rellenar", "fluido": "water", "radio": 5} and io("rellena la lava 99")["radio"] == 16)
r.check("chat rellenar: sin lava ni agua NO es un relleno ('rellena el inventario')", io("rellena el inventario") is None and io("tapa la olla") is None)
r.check("chat sitio: 'construye la casa_azul en un sitio plano'", io("construye la casa_azul en un sitio plano") == {"tipo": "sitio", "plano": "casa_azul"})
r.check("chat sitio: con tamaño 'construye casa de 20x12 en un lugar llano'", io("construye casa de 20x12 en un lugar llano") == {"tipo": "sitio", "plano": "casa", "ancho": 20, "largo": 12})
r.check("chat sitio: 'busca un sitio plano para la torre_alta'", io("Busca un sitio plano para la torre_alta") == {"tipo": "sitio", "plano": "torre_alta"})
r.check("chat sitio: 'construye una casa en la base' NO lo intercepta esto (lo hace el flujo normal)", io("construye una casa en la base") is None)
r.check("chat camino: 'haz un camino a la base'", io("haz un camino a la base") == {"tipo": "camino", "destino": "base", "ancho": 1})
r.check("chat camino: 'traza un camino de 3 de ancho hasta la mina' -> ancho 3, destino mina", io("traza un camino de 3 de ancho hasta la mina") == {"tipo": "camino", "destino": "mina", "ancho": 3})
r.check("chat camino: 'construye un puente hasta la isla'", io("construye un puente hasta la isla") == {"tipo": "camino", "destino": "isla", "ancho": 1})
r.check("chat camino: 'traza un camino ancho a la base' -> ancho 3", io("traza un camino ancho a la base") == {"tipo": "camino", "destino": "base", "ancho": 3})
r.check("chat camino: sin destino no es una orden ('haz un camino')", io("haz un camino") is None)
r.check("chat copiar: 'copia desde 10 64 20 hasta 25 70 35 como casa_azul' -> caja y nombre", io("copia desde 10 64 20 hasta 25 70 35 como casa_azul") == {"tipo": "copiar", "caja": (10, 64, 20, 25, 70, 35), "nombre": "casa_azul"})
r.check("chat copiar: coordenadas negativas", io("escanea de -5 60 -10 a 5 70 10 como fortaleza")["caja"] == (-5, 60, -10, 5, 70, 10))
r.check("chat copiar: entre dos lugares guardados y un nombre con 'mi_'", io("copia entre torre_a y torre_b como mi_torre") == {"tipo": "copiar", "waypoints": ("torre_a", "torre_b"), "nombre": "mi_torre"})
r.check("chat copiar: sin nombre o con 5 coordenadas NO es una copia", io("copia desde 1 2 3 hasta 4 5 6") is None and io("copia desde 1 2 3 hasta 4 5 como x") is None)
r.check("chat reparar: 'repara la casa' -> la obra más reciente; 'repara casa azul' con obras conocidas -> casa_azul",
        io("repara la casa") == {"tipo": "reparar", "obra": ""} and io("repara casa azul", ["casa_azul", "torre"]) == {"tipo": "reparar", "obra": "casa_azul"}
        and io("revisa la torre", ["torre"]) == {"tipo": "reparar", "obra": "torre"})
r.check("chat reparar: 'repara mi pico' NO es una obra", io("repara mi pico") is None and io("no repares nada") is None)
r.check("chat portal: '¿dónde pongo el portal del nether para la base?'", io("¿dónde pongo el portal del nether para la base?") == {"tipo": "portal", "destino": "base"})
r.check("chat portal: coordenadas del portal en el overworld sin destino", io("qué coordenadas tiene que tener el portal del overworld") == {"tipo": "portal", "destino": ""})
r.check("chat: frases normales y entradas raras -> None", all(io(x) is None for x in ("hola cobalt", "mina hierro", "ven aquí", "", None, "construye una casa en la base", "dónde está el portal")))

r.terminar()
