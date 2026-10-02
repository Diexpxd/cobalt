"""Animaciones del guardian arcano (GeckoLib, solo claves numericas).

Convenio de signos (comprobado con el visor, que replica GeckoLib): en el archivo, rotacion X positiva
  - en algo que CUELGA (piernas, brazos, capa) lo lleva hacia ATRAS;  en algo que esta DE PIE (torso, cabeza, cuerpo entero) lo inclina hacia ADELANTE.
Por eso aqui se usan dos ayudas: colgante(a) y erguido(a), con a > 0 = hacia adelante.
Posicion x positiva = hacia el lado izquierdo del personaje (+x del modelo).

Dos capas:
  - 'runico' (bucle de 4 s): giro del halo y flotacion de las placas; corre siempre en un controlador aparte y solo toca el halo (giro) y los huesos 'runaX_f' de cada placa (flotar).
  - animaciones de estado (idle, walk, fly, swim, attack, cast_spell, emp, death...): tocan el resto, incluida la ROTACION de las placas (se abren y se cierran).
"""
import math

from geo import Animacion


# ---------------------------------------------------------------- ayudas
def colgante(a):
    return -a


def erguido(a):
    return a


def suave(t):
    return t * t * (3 - 2 * t)


def interp(u, pts):
    """pts = [(t, valor), ...] con t creciente en 0..1; valor escalar o lista. Suaviza entre puntos."""
    def mezcla(a, b, k):
        if isinstance(a, (list, tuple)):
            return [x + (y - x) * k for x, y in zip(a, b)]
        return a + (b - a) * k
    if u <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if u <= t1:
            return mezcla(v0, v1, suave((u - t0) / (t1 - t0)))
    return pts[-1][1]


def S(u, vueltas=1, fase=0.0):
    return math.sin(2 * math.pi * (u * vueltas + fase))


def Cc(u, vueltas=1, fase=0.0):
    return math.cos(2 * math.pi * (u * vueltas + fase))


LADOS = (("_l", +1), ("_r", -1))
PLACAS = [(suf, sx, i) for suf, sx in LADOS for i in (1, 2, 3)]


def placas(a, f, pasos=16):
    """Aplica f(suf, sx, i, u) -> [x,y,z] de rotacion a las seis placas."""
    for suf, sx, i in PLACAS:
        a.rot("runa%s%d" % (suf, i), lambda u, suf=suf, sx=sx, i=i: f(suf, sx, i, u), pasos)


# ---------------------------------------------------------------- capa runica (siempre activa)
def runico():
    a = Animacion("runico", 4.0)
    a.rot("halo", lambda u: [0, 0, -90 * u], 8)          # 90 grados por vuelta: el aro (15), las marcas (45) y los cartuchos (90) encajan: bucle sin salto
    for suf, sx, i in PLACAS:
        fase = 0.17 * i + (0.5 if sx < 0 else 0.0)
        a.pos("runa%s%d_f" % (suf, i), lambda u, fase=fase: [0, 0.55 * S(u, 1, fase), 0.25 * S(u, 2, fase)], 16)
    return a


# ---------------------------------------------------------------- quieto
def idle():
    a = Animacion("idle", 4.0)
    a.pos("body", lambda u: [0, 0.30 * S(u), 0])
    a.rot("torso", lambda u: [erguido(0.8 * S(u, 1, 0.1)), 1.5 * S(u, 1, 0.25), 0])
    a.rot("head", lambda u: [erguido(1.2 * S(u, 1, 0.35)), 3.5 * S(u, 1, 0.0), 0])
    for suf, sx in LADOS:
        a.rot("arm" + suf, lambda u, sx=sx: [colgante(2 + 1.4 * S(u, 1, 0.2)), 0, sx * (3 + 0.8 * S(u))])
        a.rot("forearm" + suf, lambda u: [colgante(10 + 2 * S(u, 1, 0.35)), 0, 0])
        a.rot("hand" + suf, lambda u: [colgante(4 * S(u, 1, 0.5)), 0, 0])
    a.rot("capa", lambda u: [3 + 1.5 * S(u, 1, 0.3), 0, 0])
    a.rot("capa2", lambda u: [2.5 * S(u, 1, 0.42), 0, 0])
    a.rot("capa3", lambda u: [3.5 * S(u, 1, 0.55), 0, 0])
    a.rot("tabardo2", lambda u: [colgante(2.5 * S(u, 1, 0.3)), 0, 0])
    a.rot("tabardo3", lambda u: [colgante(3.5 * S(u, 1, 0.45)), 0, 0])
    placas(a, lambda suf, sx, i, u: [0, 0, sx * (1.5 + 3 * S(u, 1, 0.2 * i))])
    return a


# ---------------------------------------------------------------- caminar
def walk():
    a = Animacion("walk", 1.0)
    a.pos("body", lambda u: [0, 0.45 * Cc(u, 2), 0])
    a.rot("body", lambda u: [erguido(3), 0, 0])
    a.rot("torso", lambda u: [erguido(1.5 * Cc(u, 2, 0.25)), 5 * S(u), 0])
    a.rot("head", lambda u: [erguido(-2), -4 * S(u), 0])
    for suf, sx in LADOS:
        fase = 0.0 if sx > 0 else 0.5
        a.rot("leg" + suf, lambda u, fase=fase: [colgante(34 * S(u, 1, fase)), 0, 0])
        a.rot("shin" + suf, lambda u, fase=fase: [max(0.0, 46 * S(u, 1, fase + 0.25)), 0, 0])                   # la rodilla se dobla al adelantar la pierna
        a.rot("foot" + suf, lambda u, fase=fase: [colgante(-18 * S(u, 1, fase) + 8 * max(0.0, S(u, 1, fase + 0.25))), 0, 0])
        a.rot("arm" + suf, lambda u, fase=fase, sx=sx: [colgante(-26 * S(u, 1, fase)), 0, sx * 2])
        a.rot("forearm" + suf, lambda u, fase=fase: [colgante(18 + 14 * max(0.0, -S(u, 1, fase))), 0, 0])
    a.rot("capa", lambda u: [10 + 4 * Cc(u, 2, 0.1), 0, 0])
    a.rot("capa2", lambda u: [8 + 6 * Cc(u, 2, 0.2), 0, 0])
    a.rot("capa3", lambda u: [8 + 8 * Cc(u, 2, 0.32), 0, 0])
    a.rot("tabardo", lambda u: [colgante(4 * Cc(u, 2, 0.1)), 0, 0])
    a.rot("tabardo2", lambda u: [colgante(6 * Cc(u, 2, 0.2)), 0, 0])
    a.rot("tabardo3", lambda u: [colgante(8 * Cc(u, 2, 0.32)), 0, 0])
    placas(a, lambda suf, sx, i, u: [0, 0, sx * (-3 + 4 * S(u, 2, 0.15 * i))])                                  # se pliegan un poco al andar
    return a


# ---------------------------------------------------------------- volar (parado en el aire) y volar avanzando
def fly():
    a = Animacion("fly", 2.0)
    a.pos("body", lambda u: [0, 1.0 + 0.7 * S(u), 0])
    a.rot("body", lambda u: [erguido(4 + 1.5 * S(u, 1, 0.25)), 0, 0])
    a.rot("head", lambda u: [erguido(-2), 3 * S(u, 1, 0.1), 0])
    for suf, sx in LADOS:
        a.rot("leg" + suf, lambda u, sx=sx: [colgante(-14 + 4 * S(u, 1, 0.2)), 0, sx * -3])                       # piernas relajadas, un poco atras
        a.rot("shin" + suf, lambda u: [20 + 4 * S(u, 1, 0.4), 0, 0])
        a.rot("foot" + suf, lambda u: [colgante(-18), 0, 0])
        a.rot("arm" + suf, lambda u, sx=sx: [colgante(-8 + 3 * S(u, 1, 0.3)), 0, sx * (20 + 4 * S(u))])          # brazos abiertos
        a.rot("forearm" + suf, lambda u: [colgante(16), 0, 0])
        a.rot("hand" + suf, lambda u, sx=sx: [0, 0, sx * 8 * S(u, 1, 0.5)])
    a.rot("capa", lambda u: [24 + 3 * S(u, 1, 0.2), 0, 0])
    a.rot("capa2", lambda u: [16 + 5 * S(u, 1, 0.35), 0, 0])
    a.rot("capa3", lambda u: [12 + 7 * S(u, 1, 0.5), 0, 0])
    a.rot("tabardo", lambda u: [colgante(-6), 0, 0])
    a.rot("tabardo2", lambda u: [colgante(-10 + 4 * S(u, 1, 0.3)), 0, 0])
    a.rot("tabardo3", lambda u: [colgante(-14 + 6 * S(u, 1, 0.45)), 0, 0])
    placas(a, lambda suf, sx, i, u: [0, 0, sx * (26 + 5 * S(u, 1, 0.16 * i))])                                  # las placas se abren como alas
    a.pos("runas", lambda u: [0, 0, 0.6 * S(u, 2)])
    for suf, sx, i in PLACAS:
        a.pos("runa%s%d" % (suf, i), lambda u, sx=sx, i=i: [sx * (1.2 + 0.3 * i), 0, 0], 2)                        # y se separan del cuerpo
    return a


def fly_move():
    a = Animacion("fly_move", 1.6)
    a.pos("body", lambda u: [0, 0.8 + 0.5 * S(u), 0])
    a.rot("body", lambda u: [erguido(24 + 2 * S(u, 1, 0.25)), 0, 0])                                              # inclinado hacia adelante
    a.rot("torso", lambda u: [erguido(4), 0, 0])
    a.rot("head", lambda u: [erguido(-20), 2 * S(u, 1, 0.1), 0])                                                   # la cabeza mira al frente
    for suf, sx in LADOS:
        a.rot("leg" + suf, lambda u, sx=sx: [colgante(-30 + 5 * S(u, 1, 0.2)), 0, sx * -4])
        a.rot("shin" + suf, lambda u: [14 + 5 * S(u, 1, 0.4), 0, 0])
        a.rot("foot" + suf, lambda u: [colgante(-30), 0, 0])
        a.rot("arm" + suf, lambda u, sx=sx: [colgante(-32 + 4 * S(u, 1, 0.3)), 0, sx * (12 + 3 * S(u))])
        a.rot("forearm" + suf, lambda u: [colgante(8), 0, 0])
    a.rot("capa", lambda u: [58 + 4 * S(u, 2, 0.2), 0, 0])
    a.rot("capa2", lambda u: [30 + 8 * S(u, 2, 0.35), 0, 0])
    a.rot("capa3", lambda u: [22 + 10 * S(u, 2, 0.5), 0, 0])
    a.rot("tabardo", lambda u: [colgante(-30), 0, 0])
    a.rot("tabardo2", lambda u: [colgante(-32 + 5 * S(u, 2, 0.3)), 0, 0])
    a.rot("tabardo3", lambda u: [colgante(-34 + 8 * S(u, 2, 0.45)), 0, 0])
    placas(a, lambda suf, sx, i, u: [erguido(-10), 0, sx * (38 + 6 * S(u, 2, 0.14 * i))])                      # alas abiertas y echadas atras
    for suf, sx, i in PLACAS:
        a.pos("runa%s%d" % (suf, i), lambda u, sx=sx, i=i: [sx * (2.0 + 0.4 * i), 0, 1.5], 2)
    return a


# ---------------------------------------------------------------- nadar
def swim():
    a = Animacion("swim", 1.6)
    a.pos("body", lambda u: [0, 0.5 * S(u, 2), 0])
    a.rot("body", lambda u: [erguido(62 + 3 * S(u, 2, 0.25)), 0, 6 * S(u)])                                        # casi horizontal
    a.rot("head", lambda u: [erguido(-46), 0, 0])
    for suf, sx in LADOS:
        fase = 0.0 if sx > 0 else 0.5
        a.rot("arm" + suf, lambda u, fase=fase, sx=sx: [colgante(150 * S(u, 1, fase + 0.25) - 30), 0, sx * (10 + 8 * S(u, 1, fase))])   # brazada circular
        a.rot("forearm" + suf, lambda u, fase=fase: [colgante(30 + 26 * max(0.0, S(u, 1, fase + 0.5))), 0, 0])
        a.rot("leg" + suf, lambda u, fase=fase: [colgante(-10 + 24 * S(u, 2, fase)), 0, 0])                          # patada suave
        a.rot("shin" + suf, lambda u, fase=fase: [10 + 16 * max(0.0, S(u, 2, fase + 0.25)), 0, 0])
        a.rot("foot" + suf, lambda u: [colgante(-30), 0, 0])
    a.rot("capa", lambda u: [8 + 6 * S(u, 2, 0.2), 0, 0])
    a.rot("capa2", lambda u: [10 + 10 * S(u, 2, 0.35), 0, 0])
    a.rot("capa3", lambda u: [12 + 12 * S(u, 2, 0.5), 0, 0])
    a.rot("tabardo", lambda u: [colgante(-10), 0, 0])
    a.rot("tabardo2", lambda u: [colgante(-8 + 6 * S(u, 2, 0.3)), 0, 0])
    a.rot("tabardo3", lambda u: [colgante(-8 + 10 * S(u, 2, 0.45)), 0, 0])
    placas(a, lambda suf, sx, i, u: [erguido(-16), 0, sx * (16 + 8 * S(u, 2, 0.12 * i))])
    return a


# ---------------------------------------------------------------- despegue y aterrizaje (una vez)
def fly_start():
    a = Animacion("fly_start", 0.7, bucle=False)
    a.pos("body", lambda u: [0, interp(u, [(0, 0.0), (0.3, -0.8), (1, 1.0)]), 0])
    a.rot("body", lambda u: [erguido(interp(u, [(0, 0), (0.3, 8), (1, 4)])), 0, 0])
    for suf, sx in LADOS:
        a.rot("leg" + suf, lambda u: [colgante(interp(u, [(0, 0), (0.3, 18), (1, -14)])), 0, 0])
        a.rot("shin" + suf, lambda u: [interp(u, [(0, 0), (0.3, 40), (1, 20)]), 0, 0])
        a.rot("arm" + suf, lambda u, sx=sx: [colgante(interp(u, [(0, 0), (0.3, 24), (1, -8)])), 0, sx * interp(u, [(0, 3), (0.3, 6), (1, 20)])])
    placas(a, lambda suf, sx, i, u: [0, 0, sx * interp(u, [(0, 2), (0.3, -4), (1, 26)])])
    return a


def fly_end():
    a = Animacion("fly_end", 0.6, bucle=False)
    a.pos("body", lambda u: [0, interp(u, [(0, 1.0), (0.6, -0.6), (1, 0.0)]), 0])
    a.rot("body", lambda u: [erguido(interp(u, [(0, 4), (0.6, 6), (1, 0)])), 0, 0])
    for suf, sx in LADOS:
        a.rot("leg" + suf, lambda u: [colgante(interp(u, [(0, -14), (0.6, 12), (1, 0)])), 0, 0])
        a.rot("shin" + suf, lambda u: [interp(u, [(0, 20), (0.6, 36), (1, 0)]), 0, 0])
        a.rot("arm" + suf, lambda u, sx=sx: [colgante(interp(u, [(0, -8), (0.6, 10), (1, 2)])), 0, sx * interp(u, [(0, 20), (0.6, 12), (1, 3)])])
    placas(a, lambda suf, sx, i, u: [0, 0, sx * interp(u, [(0, 26), (0.6, 8), (1, 2)])])
    return a


# ---------------------------------------------------------------- atacar (golpe / disparo rapido)
def attack():
    a = Animacion("attack", 0.7, bucle=False)
    t = [(0, 0), (0.3, 1), (0.5, 0.0), (1, 0)]
    a.rot("torso", lambda u: [erguido(interp(u, [(0, 0), (0.3, -8), (0.5, 14), (1, 0)])), interp(u, [(0, 0), (0.3, -28), (0.5, 26), (1, 0)]), 0])
    a.rot("head", lambda u: [erguido(interp(u, [(0, 0), (0.3, -6), (0.5, 8), (1, 0)])), interp(u, [(0, 0), (0.3, 20), (0.5, -14), (1, 0)]), 0])
    a.rot("arm_r", lambda u: [colgante(interp(u, [(0, 0), (0.3, -140), (0.5, 92), (1, 0)])), interp(u, [(0, 0), (0.3, 12), (0.5, -8), (1, 0)]), interp(u, [(0, -3), (0.3, -12), (1, -3)])])
    a.rot("forearm_r", lambda u: [colgante(interp(u, [(0, 10), (0.3, 70), (0.5, 8), (1, 10)])), 0, 0])
    a.rot("arm_l", lambda u: [colgante(interp(u, [(0, 2), (0.3, 30), (0.5, -20), (1, 2)])), 0, 4])
    a.rot("leg_l", lambda u: [colgante(interp(u, [(0, 0), (0.3, -8), (0.5, 22), (1, 0)])), 0, 0])
    a.rot("leg_r", lambda u: [colgante(interp(u, [(0, 0), (0.3, 14), (0.5, -16), (1, 0)])), 0, 0])
    a.rot("capa", lambda u: [interp(u, [(0, 3), (0.3, 16), (0.5, -6), (1, 3)]), 0, 0])
    placas(a, lambda suf, sx, i, u: [0, 0, sx * interp(u, [(0, 2), (0.3, 16), (0.5, 40), (1, 2)])])            # destello: las placas se abren al soltar el golpe
    return a


# ---------------------------------------------------------------- lanzar hechizo (una vez)
def cast_spell():
    a = Animacion("cast_spell", 1.4, bucle=False)
    a.rot("body", lambda u: [erguido(interp(u, [(0, 0), (0.35, -6), (0.7, 8), (1, 2)])), 0, 0])
    a.rot("torso", lambda u: [erguido(interp(u, [(0, 0), (0.35, -10), (0.7, 6), (1, 0)])), 0, 0])
    a.rot("head", lambda u: [erguido(interp(u, [(0, 0), (0.35, -14), (0.7, 6), (1, 0)])), 0, 0])
    for suf, sx in LADOS:
        a.rot("arm" + suf, lambda u, sx=sx: [colgante(interp(u, [(0, 2), (0.35, 112), (0.7, 84), (1, 28)])), sx * interp(u, [(0, 0), (0.35, -8), (0.7, 6), (1, 0)]), sx * interp(u, [(0, 3), (0.35, 26), (0.7, 12), (1, 6)])])
        a.rot("forearm" + suf, lambda u: [colgante(interp(u, [(0, 10), (0.35, 26), (0.7, 6), (1, 12)])), 0, 0])
        a.rot("hand" + suf, lambda u, sx=sx: [colgante(interp(u, [(0, 0), (0.35, 30), (0.7, 8), (1, 0)])), 0, sx * interp(u, [(0, 0), (0.35, 10), (0.7, 0), (1, 0)])])
        a.rot("leg" + suf, lambda u, sx=sx: [colgante(interp(u, [(0, 0), (0.35, 6 * sx), (1, 4 * sx)])), 0, 0])
    a.rot("capa", lambda u: [interp(u, [(0, 3), (0.35, 20), (0.7, -8), (1, 4)]), 0, 0])
    a.rot("capa2", lambda u: [interp(u, [(0, 2), (0.4, 24), (0.75, -6), (1, 2)]), 0, 0])
    placas(a, lambda suf, sx, i, u: [erguido(interp(u, [(0, 0), (0.35, 12), (0.7, -6), (1, 0)])), sx * interp(u, [(0, 2), (0.35, 42), (0.7, 54), (1, 14)]), sx * interp(u, [(0, 2), (0.35, 42), (0.7, 54), (1, 14)])])
    a.pos("runas", lambda u: [0, interp(u, [(0, 0), (0.7, 1.4), (1, 0.4)]), interp(u, [(0, 0), (0.7, -1.6), (1, 0)])])
    return a


# ---------------------------------------------------------------- pulso EMP (una vez): se agacha y lo suelta en anillo
def emp():
    a = Animacion("emp", 1.2, bucle=False)
    a.pos("body", lambda u: [0, interp(u, [(0, 0), (0.35, -2.4), (0.55, 0.8), (1, 0)]), 0])
    a.rot("body", lambda u: [erguido(interp(u, [(0, 0), (0.35, 10), (0.55, -8), (1, 0)])), 0, 0])
    a.rot("head", lambda u: [erguido(interp(u, [(0, 0), (0.35, 12), (0.55, -14), (1, 0)])), 0, 0])
    for suf, sx in LADOS:
        a.rot("arm" + suf, lambda u, sx=sx: [colgante(interp(u, [(0, 2), (0.35, 34), (0.55, -8), (1, 2)])), 0, sx * interp(u, [(0, 3), (0.35, 6), (0.55, 84), (1, 8)])])
        a.rot("forearm" + suf, lambda u: [colgante(interp(u, [(0, 10), (0.35, 50), (0.55, 4), (1, 10)])), 0, 0])
        a.rot("leg" + suf, lambda u: [colgante(interp(u, [(0, 0), (0.35, 24), (0.55, 4), (1, 0)])), 0, 0])
        a.rot("shin" + suf, lambda u: [interp(u, [(0, 0), (0.35, 44), (0.55, 6), (1, 0)]), 0, 0])
    a.rot("capa", lambda u: [interp(u, [(0, 3), (0.35, -4), (0.55, 32), (1, 4)]), 0, 0])
    placas(a, lambda suf, sx, i, u: [0, 0, sx * interp(u, [(0, 2), (0.35, -8), (0.55, 70), (0.8, 46), (1, 4)])])
    for suf, sx, i in PLACAS:
        a.pos("runa%s%d" % (suf, i), lambda u, sx=sx, i=i: [sx * interp(u, [(0, 0), (0.35, -1), (0.55, 3.5 + 0.6 * i), (1, 0)]), 0, 0])
    return a


# ---------------------------------------------------------------- morir (una vez, se queda en el suelo)
def death():
    a = Animacion("death", 2.2, bucle=False)
    a.pos("root", lambda u: [0, interp(u, [(0, 0), (0.6, -0.5), (1, 2.6)]), interp(u, [(0, 0), (0.6, -1), (1, -1)])])
    a.rot("root", lambda u: [erguido(interp(u, [(0, 0), (0.3, 6), (0.6, 30), (0.85, 88), (1, 90)])), 0, interp(u, [(0, 0), (0.6, 4), (1, 6)])])
    a.rot("head", lambda u: [erguido(interp(u, [(0, 0), (0.3, 18), (1, 32)])), interp(u, [(0, 0), (0.5, 16), (1, 10)]), 0])
    for suf, sx in LADOS:
        a.rot("leg" + suf, lambda u: [colgante(interp(u, [(0, 0), (0.4, 20), (1, 8)])), 0, 0])
        a.rot("shin" + suf, lambda u: [interp(u, [(0, 0), (0.4, 56), (1, 30)]), 0, 0])
        a.rot("arm" + suf, lambda u, sx=sx: [colgante(interp(u, [(0, 2), (0.4, -30), (1, -70)])), 0, sx * interp(u, [(0, 3), (0.5, 40), (1, 62)])])
        a.rot("forearm" + suf, lambda u: [colgante(interp(u, [(0, 10), (0.5, 40), (1, 24)])), 0, 0])
    a.rot("capa", lambda u: [interp(u, [(0, 3), (0.6, 40), (1, 84)]), 0, 0])
    a.rot("capa2", lambda u: [interp(u, [(0, 2), (0.6, 30), (1, 70)]), 0, 0])
    a.rot("capa3", lambda u: [interp(u, [(0, 3), (0.6, 24), (1, 60)]), 0, 0])
    placas(a, lambda suf, sx, i, u: [0, 0, sx * interp(u, [(0, 2), (0.4, 40), (1, 84)])])                       # las placas caen abiertas
    a.esc("halo", lambda u: [interp(u, [(0, 1), (0.7, 1), (1, 0.001)])] * 3)                                     # el halo se apaga
    return a


def todas():
    return [runico(), idle(), walk(), fly(), fly_move(), swim(), fly_start(), fly_end(), attack(), cast_spell(), emp(), death()]
