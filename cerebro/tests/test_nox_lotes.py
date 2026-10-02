"""F2-3: colocación por lotes (parte pura): partir la obra, armar la orden y leer el resumen de Java SIN fiarse de él."""
import random
import os
import sys

from _cargar import Resultados

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_lotes as lo  # noqa: E402

r = Resultados()

r.check("tam_valido: se acota a [1, 64]; lo que no es número da el de por defecto (48)", [lo.tam_valido(x) for x in (10, 1, 0, -5, 64, 65, 999, 12.9)] == [10, 1, 1, 1, 64, 64, 64, 12]
        and all(lo.tam_valido(x) == 48 for x in (None, "x", True, float("nan"), [], {})))
lotes = lo.partir_en_lotes(list(range(130)), 48)
r.check("partir_en_lotes: 130 elementos en lotes de 48 -> 48, 48 y 34, en orden y sin perder ni repetir ninguno", [len(x) for x in lotes] == [48, 48, 34] and [v for x in lotes for v in x] == list(range(130)))
r.check("partir_en_lotes: vacío/None -> []; un elemento -> 1 lote; exactamente el tamaño -> 1 lote; tamaño absurdo se acota", lo.partir_en_lotes([]) == [] and lo.partir_en_lotes(None) == [] and lo.partir_en_lotes([1]) == [[1]]
        and len(lo.partir_en_lotes(list(range(48)), 48)) == 1 and len(lo.partir_en_lotes(list(range(49)), 48)) == 2 and max(len(x) for x in lo.partir_en_lotes(list(range(200)), 9999)) == 64)

o = lo.orden_lote([{"x": 1, "y": 2, "z": 3, "block": "minecraft:stone", "movement_mode": "fly", "extra": 5}, {"x": 4, "y": 5, "z": 6, "block": "minecraft:oak_stairs", "state": "facing=east"}, {"x": 0, "y": 0, "z": 0, "block": "a", "state": ""}])
r.check("orden_lote: action, movement_mode y solo x/y/z/block (y state si lo hay); descarta claves ajenas y el state vacío",
        o["action"] == "place_blocks" and o["movement_mode"] == "walk" and o["blocks"] == [{"x": 1, "y": 2, "z": 3, "block": "minecraft:stone"}, {"x": 4, "y": 5, "z": 6, "block": "minecraft:oak_stairs", "state": "facing=east"},
                                                                                        {"x": 0, "y": 0, "z": 0, "block": "a"}])

ok = lo.interpretar_resumen({"status": "success", "placed": 3, "total": 3, "failed": []}, 3)
r.check("resumen válido: success con todo colocado", ok == {"colocados": [0, 1, 2], "fallos": {}})
par = lo.interpretar_resumen({"status": "partial", "placed": 3, "total": 5, "failed": [{"i": 1, "reason": "ocupado"}, {"i": 4, "reason": "no_material"}]}, 5)
r.check("resumen válido: parcial -> colocados y fallos con su motivo", par == {"colocados": [0, 2, 3], "fallos": {1: "ocupado", 4: "no_material"}})
r.check("resumen válido: failed con todo fallando", lo.interpretar_resumen({"status": "failed", "placed": 0, "total": 2, "failed": [{"i": 0, "reason": "ocupado"}, {"i": 1, "reason": "ocupado"}]}, 2)["colocados"] == [])
r.check("resumen válido: un motivo desconocido se llama 'error' (no se inventa uno)", lo.interpretar_resumen({"status": "partial", "placed": 1, "total": 2, "failed": [{"i": 1, "reason": "algo raro"}]}, 2)["fallos"] == {1: "error"}
        and lo.interpretar_resumen({"status": "partial", "placed": 1, "total": 2, "failed": [{"i": 1}]}, 2)["fallos"] == {1: "error"})
r.check("resumen válido: 'ignored' (Java recortó lotes de más de 64) no rompe si total == enviados", lo.interpretar_resumen({"status": "success", "placed": 2, "total": 2, "failed": [], "ignored": 5}, 2) is not None)

base = {"status": "partial", "placed": 3, "total": 5, "failed": [{"i": 1, "reason": "ocupado"}, {"i": 4, "reason": "no_material"}]}


def var(**cambios):
    d = dict(base)
    d.update(cambios)
    return d


malos = {
    "no es un dict": None, "lista": [], "texto": "success", "sin status": {k: v for k, v in base.items() if k != "status"}, "status raro": var(status="ok"), "status None": var(status=None),
    "placed bool": var(placed=True), "placed texto": var(placed="3"), "placed float": var(placed=3.0), "total bool": var(total=True), "total distinto de lo enviado": var(total=6),
    "placed negativo": var(placed=-1), "placed > total": var(placed=6), "failed no es lista": var(failed="x"), "failed None": var(failed=None), "failed_more": var(failed_more=3),
    "indice fuera de rango": var(failed=[{"i": 1, "reason": "ocupado"}, {"i": 5, "reason": "ocupado"}]), "indice negativo": var(failed=[{"i": -1, "reason": "x"}, {"i": 4}]),
    "indice repetido": var(failed=[{"i": 1, "reason": "ocupado"}, {"i": 1, "reason": "ocupado"}]), "indice bool": var(failed=[{"i": True}, {"i": 4}]), "indice texto": var(failed=[{"i": "1"}, {"i": 4}]),
    "fallo que no es dict": var(failed=[5, {"i": 4}]), "placed + fallos != total": var(placed=2), "success con fallos": var(status="success"),
    "partial sin fallos y todo colocado": {"status": "partial", "placed": 5, "total": 5, "failed": []},
    "partial con 0 colocados": {"status": "partial", "placed": 0, "total": 5, "failed": [{"i": 0}, {"i": 1}, {"i": 2}, {"i": 3}, {"i": 4}]},
    "failed pero con colocados": {"status": "failed", "placed": 1, "total": 5, "failed": [{"i": 0}, {"i": 1}, {"i": 2}, {"i": 3}]},
    "success con menos colocados": {"status": "success", "placed": 4, "total": 5, "failed": []},
    "total distinto de lo enviado aunque todo lo demas cuadre": {"status": "partial", "placed": 4, "total": 6, "failed": [{"i": 1, "reason": "ocupado"}, {"i": 4, "reason": "ocupado"}]},
    "indice repetido aunque la suma cuadre": {"status": "partial", "placed": 4, "total": 5, "failed": [{"i": 1, "reason": "ocupado"}, {"i": 1, "reason": "ocupado"}]},
}
mal = [k for k, v in malos.items() if lo.interpretar_resumen(v, 5) is not None]
r.check("resumen NO fiable -> None (" + str(len(malos)) + " casos): falla " + str(mal), not mal)
r.check("'enviados' inválido -> None (0, negativo, bool, texto, None)", all(lo.interpretar_resumen(base, x) is None for x in (0, -1, True, "5", None, 5.0)))

bloques = [{"block": "minecraft:stone"}, {"block": "minecraft:oak_planks"}, {"block": "minecraft:stone"}, {"block": "minecraft:glass"}, {"block": "minecraft:stone"}]
g = lo.agrupar_fallos({0: "no_material", 1: "ocupado", 2: "no_material", 3: "no_material", 4: "bloque_invalido"}, bloques)
r.check("agrupar_fallos: el material que falta por tipo de bloque (para reabastecer) y el resto aparte: " + str(g), g == {"no_material": {"minecraft:stone": [0, 2], "minecraft:glass": [3]}, "otros": [1, 4]})
r.check("agrupar_fallos: sin fallos", lo.agrupar_fallos({}, bloques) == {"no_material": {}, "otros": []})

rng = random.Random(3)
cosas = [None, True, False, 0, -1, 3, 5, 1e30, float("nan"), "x", [], {}, [1], {"i": 1}, [{"i": 1, "reason": "ocupado"}], [{"i": 0}], {"a": 1}]
fallos = []
for _ in range(5000):
    d = {k: rng.choice(cosas) for k in ("status", "placed", "total", "failed", "failed_more", "ignored") if rng.random() < 0.85}
    if rng.random() < 0.1:
        d = rng.choice(cosas)
    try:
        res = lo.interpretar_resumen(d, rng.choice([1, 2, 3, 5, 64, 0, None, "x", True]))
        if res is not None:
            assert set(res) == {"colocados", "fallos"} and all(isinstance(i, int) for i in res["colocados"]) and not set(res["colocados"]) & set(res["fallos"])
        lo.partir_en_lotes(rng.choice(cosas), rng.choice(cosas))
    except Exception as ex:  # noqa: BLE001
        fallos.append(repr(ex))
r.check("fuzz (5000 resúmenes basura): nunca lanza y, cuando lo acepta, es coherente: " + str(fallos[:2]), not fallos)

r.terminar()
