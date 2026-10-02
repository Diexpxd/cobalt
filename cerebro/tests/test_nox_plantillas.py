"""Pruebas del Bloque Q3: plantillas de planos por código."""
import os
import sys

from _cargar import Resultados, cargar_cerebro

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_plantillas as npl  # noqa: E402
import planos_checks as pc  # noqa: E402

ns = cargar_cerebro()
validar = ns["validar_blueprint"]
r = Resultados()

DIMS = {"casa": (7, 5, 7), "cabana": (6, 7, 8), "torre": (5, 12, 5), "faro": (7, 15, 7), "puente": (3, 3, 15), "muro": (3, 6, 15),
        "piramide": (13, 7, 13), "invernadero": (8, 4, 6), "corral": (7, 2, 7), "refugio": (5, 4, 5)}

for tipo in npl.TIPOS:
    plano = npl.construir(tipo)
    r.check(f"{tipo}: se construye", plano is not None)
    if plano is None:
        continue
    val, err = validar(plano)
    r.check(f"{tipo}: pasa el validador REAL de Cobalt (16x16x16, <=800, sin bloques prohibidos) {err[:1]}", val is not None)
    if val is None:
        continue
    chk = pc.evaluar({"tipo": tipo, "dims": DIMS[tipo]}, val)
    malos = [k for k, ok in chk.items() if not ok]
    r.check(f"{tipo}: cumple TODAS las comprobaciones estructurales {malos}", not malos)
    n = sum(len(c["blocks"]) for c in val["layers"])
    r.check(f"{tipo}: {n} bloques (<= 800)", n <= 800)

casos = [("casa de piedra y madera de 7x7 con 5 de alto, con puerta y ventanas", "casa", 7, 5, 7, "mixta"),
         ("torre de vigilancia cuadrada de 5x5 y 12 de alto con puerta abajo", "torre", 5, 12, 5, "piedra"),
         ("puente de piedra de 15 de largo y 3 de ancho con barandillas", "puente", 3, 3, 15, "piedra"),
         ("pirámide escalonada de arenisca con base de 13x13", "piramide", 13, 7, 13, "arenisca"),
         ("cabaña de madera de 6x8 con tejado a dos aguas y una puerta", "cabana", 6, 7, 8, "madera"),
         ("muro defensivo de piedra de 15 de largo con almenas y una puerta en el centro", "muro", 3, 6, 15, "piedra"),
         ("invernadero de cristal de 8x6 con 4 de alto y una puerta", "invernadero", 8, 4, 6, "madera"),
         ("faro de piedra con base de 7x7, 15 de alto, y una luz arriba", "faro", 7, 15, 7, "piedra")]
for texto, tipo, w, h, l, pal in casos:
    a = npl.analizar_peticion(texto)
    r.check(f"entiende: {texto[:40]}... -> {tipo} {w}x{h}x{l} {pal} (obtuvo {a})", a is not None and (a["tipo"], a["ancho"], a["alto"], a["largo"], a["paleta"]) == (tipo, w, h, l, pal))
    plano = npl.plano_desde_peticion(texto)
    val = validar(plano)[0] if plano else None
    if val is None:
        r.check(f"la plantilla de '{texto[:30]}...' es válida", False)
        continue
    chk = pc.evaluar({"tipo": tipo, "dims": (w, h, l)}, val)
    malos = [k for k, ok in chk.items() if not ok]
    r.check(f"la plantilla de '{texto[:30]}...' es válida y cumple las comprobaciones {malos}", not malos)

p = validar(npl.plano_desde_peticion("una casa de arenisca de 9x6 con 6 de alto"))[0]
bb = pc.bbox(pc.voxeles(p))
r.check("casa de 9x6x6 respeta las medidas pedidas", bb == (9, 6, 6))
r.check("la casa de arenisca usa arenisca (paleta por material)", any("sandstone" in b for b in pc.voxeles(p).values()))
p = validar(npl.plano_desde_peticion("casa de cuarzo"))[0]
r.check("material 'cuarzo' -> bloques de cuarzo", any("quartz" in b for b in pc.voxeles(p).values()))
p = validar(npl.plano_desde_peticion("un puente de madera de 10 de largo"))[0]
v = pc.voxeles(p)
r.check("puente de 10 de largo y madera: largo 10 y valla de madera", pc.bbox(v)[2] == 10 and any("fence" in b for b in v.values()))
r.check("'refugio' produce una casita de 5x4x5", pc.bbox(pc.voxeles(validar(npl.plano_desde_peticion("un refugio pequeño para la noche"))[0])) == (5, 4, 5))
r.check("'corral' produce una cerca con portón", any(b == "oak_fence_gate" for b in pc.voxeles(validar(npl.plano_desde_peticion("un corral de 8x8"))[0]).values()))
r.check("'sin acentos' y mayúsculas también valen", npl.analizar_peticion("PIRAMIDE de ARENISCA")["tipo"] == "piramide" and npl.analizar_peticion("CABAÑA")["tipo"] == "cabana")
r.check("'2 x 3' con espacios y 'por' se entienden como medidas", npl.analizar_peticion("casa de 8 x 6")["ancho"] == 8 and npl.analizar_peticion("casa de 8 por 6")["largo"] == 6)

vp = pc.voxeles(validar(npl.construir("puente"))[0])
r.check("puente: barandilla en TODO el largo y por los dos lados (2 x 15 bloques), no a medias", sum(1 for b in vp.values() if b.endswith("_wall")) == 30)
r.check("puente: apoyos en los dos extremos y en el centro", all((1, 0, z) in vp for z in (0, 7, 14)))

for texto in ["una casa de 40x40 con 40 de alto", "torre de 16x16 y 16 de alto", "pirámide de 30x30", "muro de 99 de largo", "faro de 2x2 y 3 de alto", "casa de 1x1 con 1 de alto",
              "puente de 200 de largo y 50 de ancho", "invernadero de 16x16 con 16 de alto", "cabaña de 16x16 con 16 de alto"]:
    plano = npl.plano_desde_peticion(texto)
    val = validar(plano)[0] if plano else None
    r.check(f"medidas extremas ('{texto}') -> plano válido de todos modos (recortado)", val is not None)
    if val:
        bb = pc.bbox(pc.voxeles(val))
        r.check(f"  y dentro de 16x16x16: {bb}", all(d <= 16 for d in bb))

for raro in ["una estatua de dragón", "un castillo con foso", "", "   ", None, 42, "hola qué tal", "una nave espacial"]:
    r.check(f"sin plantilla para {raro!r}: devuelve None", npl.plano_desde_peticion(raro) is None)
r.check("construir con un tipo desconocido devuelve None", npl.construir("castillo") is None)

a = npl.plano_desde_peticion("casa de piedra de 7x7")
b = npl.plano_desde_peticion("casa de piedra de 7x7")
r.check("misma petición -> mismo plano (determinista)", a == b)
r.check("formato de Cobalt: blueprint_name + layers[{y, blocks[{x,z,block}]}] con ids 'minecraft:...'",
        set(a) == {"blueprint_name", "layers"} and all(set(c) == {"y", "blocks"} and all(set(bl) == {"x", "z", "block"} and bl["block"].startswith("minecraft:") for bl in c["blocks"]) for c in a["layers"]))
prohibidos = ("tnt", "lava", "fire", "water", "bedrock", "command", "spawner", "portal", "barrier")
todos = {b_["block"] for tipo in npl.TIPOS for c in npl.construir(tipo)["layers"] for b_ in c["blocks"]}
r.check("ninguna plantilla usa bloques peligrosos: " + str(sorted(x for x in todos if any(p_ in x for p_ in prohibidos))), not any(any(p_ in x for p_ in prohibidos) for x in todos))

r.terminar()
