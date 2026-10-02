"""Comprobaciones estructurales OBJETIVAS de un plano (sobre el resultado de validar_blueprint de Cobalt)."""
from collections import deque


def voxeles(plano):
    return {(b["x"], c["y"], b["z"]): b["block"].split(":", 1)[1] for c in plano["layers"] for b in c["blocks"]}


def bbox(vox):
    xs, ys, zs = zip(*vox)
    return max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, max(zs) - min(zs) + 1


def conectado(vox):
    pend = set(vox)
    ini = next(iter(pend))
    pend.discard(ini)
    cola = deque([ini])
    while cola:
        x, y, z = cola.popleft()
        for v in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)):
            if v in pend:
                pend.discard(v)
                cola.append(v)
    return not pend


def en_suelo(vox):
    return min(p[1] for p in vox) == 0


def tamano_cerca(vox, dims, tol=1):
    w, h, l = bbox(vox)
    a, b = sorted((w, l)), sorted((dims[0], dims[2]))
    return all(abs(p - q) <= tol for p, q in zip(a, b)) and abs(h - dims[1]) <= max(tol, 1 if dims[1] < 10 else 2)


def materiales_ok(vox, minimo=2, maximo=8):
    return minimo <= len(set(vox.values())) <= maximo


def _perimetro(vox):
    xs = [p[0] for p in vox]
    zs = [p[2] for p in vox]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    return [(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1) if x in (x0, x1) or z in (z0, z1)]


def _abierto(vox, x, y, z):
    return (x, y, z) not in vox or vox[(x, y, z)].endswith("_door")


def puerta(vox):
    base = min(y for (_, y, _) in vox)
    # el suelo puede ser la capa 0: la puerta empieza sobre el, en base+1
    for y0 in (base, base + 1):
        for (x, z) in _perimetro(vox):
            if _abierto(vox, x, y0, z) and _abierto(vox, x, y0 + 1, z):
                vecinos = [(x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)]
                if any((vx, y0, vz) in vox and (vx, y0 + 1, vz) in vox for vx, vz in vecinos) and (x, y0 + 2, z) in vox:
                    return True
    return False


def techo(vox, minimo=0.6):
    xs = [p[0] for p in vox]
    zs = [p[2] for p in vox]
    huella = (max(xs) - min(xs) + 1) * (max(zs) - min(zs) + 1)
    ymax = max(p[1] for p in vox)
    cubiertas = {(x, z) for (x, y, z) in vox if y >= ymax - 1}
    return len(cubiertas) / huella >= minimo


def hueca(vox, dims, minimo_vacio=0.5):
    xs, ys, zs = zip(*vox)
    x0, y0, z0 = min(xs), min(ys), min(zs)
    w, h, l = bbox(vox)
    if w < 3 or h < 3 or l < 3:
        return False
    total = (w - 2) * (h - 2) * (l - 2)
    llenos = sum(1 for (x, y, z) in vox if x0 < x < x0 + w - 1 and y0 < y < y0 + h - 1 and z0 < z < z0 + l - 1)
    return 1 - llenos / total >= minimo_vacio


def altura_min(vox, h):
    return bbox(vox)[1] >= h


def puente_transitable(vox, largo):
    xs = [p[0] for p in vox]
    zs = [p[2] for p in vox]
    eje = 2 if (max(zs) - min(zs)) >= (max(xs) - min(xs)) else 0
    otro = 0 if eje == 2 else 2
    capas = {}
    for p in vox:
        capas.setdefault(p[1], set()).add((p[eje], p[otro]))
    for celdas in capas.values():
        a_lo = {c[0] for c in celdas}
        if len(a_lo) >= largo - 1 and all(any((v, o + 1) in celdas for (vv, o) in celdas if vv == v) for v in a_lo):
            return True
    return False


def escalonada(vox):
    cuenta = {}
    for (x, y, z) in vox:
        cuenta[y] = cuenta.get(y, 0) + 1
    ys = sorted(cuenta)
    return all(cuenta[b] <= cuenta[a] for a, b in zip(ys, ys[1:])) and cuenta[ys[-1]] <= 0.3 * cuenta[ys[0]]


def contiene(vox, *fragmentos):
    return any(any(f in b for f in fragmentos) for b in vox.values())


def cima_con(vox, *fragmentos, ultimas=4):
    ymax = max(p[1] for p in vox)
    return any(any(f in b for f in fragmentos) for (x, y, z), b in vox.items() if y >= ymax - ultimas + 1)


def evaluar(caso, plano):
    v = voxeles(plano)
    r = {
        "una_pieza": conectado(v),
        "en_suelo": en_suelo(v),
        "tamano": tamano_cerca(v, caso["dims"]),
        "materiales": materiales_ok(v),
    }
    t = caso["tipo"]
    if t in ("casa", "cabana", "invernadero"):
        r.update(puerta=puerta(v), techo=techo(v), hueca=hueca(v, caso["dims"]))
    if t == "casa":
        r["ventanas"] = contiene(v, "glass", "pane")
    if t == "cabana":
        r["tejado_inclinado"] = contiene(v, "stairs", "slab")
    if t == "invernadero":
        r["cristal"] = sum(1 for b in v.values() if "glass" in b) >= 0.4 * len(v)
    if t == "torre":
        r.update(puerta=puerta(v), altura=altura_min(v, 11), hueca=hueca(v, caso["dims"]))
    if t == "faro":
        r.update(puerta=puerta(v), altura=altura_min(v, 14), luz=cima_con(v, "lantern", "glowstone", "torch", "sea_lantern", "shroomlight", "beacon", "lamp"), hueca=hueca(v, caso["dims"]))
    if t == "puente":
        r.update(transitable=puente_transitable(v, 15), barandillas=contiene(v, "fence", "wall", "bars", "chain"))
    if t == "piramide":
        r["escalonada"] = escalonada(v)
    if t == "muro":
        r.update(puerta=puerta(v), almenas=len({p[1] for p in v}) >= 2 and altura_min(v, 5))
    return r
