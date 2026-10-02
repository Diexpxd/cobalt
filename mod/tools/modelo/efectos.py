"""Efectos 3D de las habilidades de Cobalt (mismo estilo que el guardian: violeta profundo + azul verdoso luminoso, con runas).

  plasma   : orbe arcano con nucleo cristalino, tres anillos giroscopicos de runas y esquirlas orbitando (proyectil de plasma).
  emp_wave : circulo de runas plano que se expande desde los pies de Cobalt hasta el radio del pulso (7 bloques al escalar x7).
  drone    : esquirla arcana con anillo de runas y satelites (dron del enjambre).

Cada uno genera <nombre>.geo.json, <nombre>.animation.json, <nombre>.png y <nombre>_glowmask.png en salida/.
"""
import math
import os

from geo import Animacion, Modelo, guardar_animaciones
import pintura

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "salida")

# el signo con el que hay que girar en y un cubo largo para que quede TANGENTE a un aro en el plano xz (se comprueba con el visor)
SIGNO_Y = -1


def C(hueso, cx, cy, cz, w, h, d, mat, **kw):
    return hueso.cubo((cx - w / 2, cy - h / 2, cz - d / 2), (w, h, d), mat, **kw)


def aro_xy(hueso, cy, radio, n, largo, alto, grueso, mat="filo", mats=None, **kw):
    """Aro en el plano xy (mira al frente), centrado en (0, cy, 0). Cubos tangentes girados en z (signo negativo: GeckoLib espeja x)."""
    for k in range(n):
        a = 2 * math.pi * k / n
        m = mats[k % len(mats)] if mats else mat
        C(hueso, radio * math.cos(a), cy + radio * math.sin(a), 0, largo, alto, grueso, m, rot=[0, 0, -(math.degrees(a) + 90)], semilla=k, **kw)


def aro_xz(hueso, cy, radio, n, largo, alto, grueso, mat="filo", mats=None, **kw):
    """Aro tumbado en el plano xz (suelo), centrado en (0, cy, 0)."""
    for k in range(n):
        a = 2 * math.pi * k / n
        m = mats[k % len(mats)] if mats else mat
        C(hueso, radio * math.cos(a), cy, radio * math.sin(a), largo, alto, grueso, m, rot=[0, SIGNO_Y * (math.degrees(a) + 90), 0], semilla=k, **kw)


def diamante(hueso, cx, cy, cz, lado, prof, mat="cristal", **kw):
    return C(hueso, cx, cy, cz, lado, lado, prof, mat, rot=[0, 0, 45], **kw)


# ---------------------------------------------------------------- plasma
def plasma():
    m = Modelo("plasma_arcano", 256, 256, 5)
    m.hueso("root")
    nucleo = m.hueso("core", "root", (0, 4, 0))
    C(nucleo, 0, 4, 0, 2.6, 2.6, 2.6, "cristal", rot=[0, 45, 0])
    C(nucleo, 0, 4, 0, 2.6, 2.6, 2.6, "cristal", rot=[45, 0, 0])
    C(nucleo, 0, 4, 0, 1.4, 1.4, 1.4, "brillo")
    for nombre, rot in (("ringA", [0, 0, 0]), ("ringB", [0, 90, 0]), ("ringC", [60, 0, 35])):
        r = m.hueso(nombre, "root", (0, 4, 0), rot=rot)
        aro_xy(r, 4, 4.4, 12, 2.4, 0.5, 0.5, mat="filo")
        for k in range(3):                                   # cuentas con runa a 120 grados
            a = 2 * math.pi * k / 3 + math.pi / 6
            C(r, 4.4 * math.cos(a), 4 + 4.4 * math.sin(a), 0, 1.5, 1.5, 0.7, "runa", rot=[0, 0, -(math.degrees(a) + 90)], semilla=k + 3)
    esq = m.hueso("shards", "root", (0, 4, 0))
    for k in range(4):
        a = 2 * math.pi * k / 4
        diamante(esq, 5.9 * math.cos(a), 4 + 0.8 * (1 if k % 2 else -1), 5.9 * math.sin(a), 1.2, 0.5, "cristal")
    anim = Animacion("spin", 1.2)
    anim.rot("ringA", lambda u: [0, 0, 360 * u], 16)
    anim.rot("ringB", lambda u: [-360 * u, 0, 0], 16)
    anim.rot("ringC", lambda u: [0, 360 * u, 0], 16)
    anim.rot("shards", lambda u: [0, 720 * u, 0], 16)
    anim.esc("core", lambda u: [1 + 0.16 * math.sin(2 * math.pi * u * 2)] * 3, 16)
    return m, [anim]


# ---------------------------------------------------------------- onda EMP (circulo de runas plano)
def emp_wave():
    m = Modelo("emp_wave", 512, 512, 4)
    m.hueso("root")
    base = m.hueso("wave", "root", (0, 0, 0))
    ext = m.hueso("anillo_ext", "wave", (0, 0, 0))
    aro_xz(ext, 0.4, 15.4, 48, 2.1, 0.5, 0.7, mat="filo")
    aro_xz(ext, 0.4, 13.2, 48, 2.0, 0.3, 0.4, mat="metal")
    for k in range(12):                                       # cartuchos con runa, entre los dos aros
        a = 2 * math.pi * k / 12
        C(ext, 14.3 * math.cos(a), 0.55, 14.3 * math.sin(a), 2.6, 0.4, 1.4, "runa", rot=[0, SIGNO_Y * (math.degrees(a) + 90), 0], semilla=k + 1)
    medio = m.hueso("anillo_med", "wave", (0, 0, 0))
    aro_xz(medio, 0.5, 9.0, 32, 1.9, 0.4, 0.6, mat="filo")
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        C(medio, 9.0 * math.cos(a), 0.7, 9.0 * math.sin(a), 2.4, 0.4, 1.3, "runa", rot=[0, SIGNO_Y * (math.degrees(a) + 90), 0], semilla=k + 20)
    inte = m.hueso("anillo_int", "wave", (0, 0, 0))
    aro_xz(inte, 0.6, 4.6, 20, 1.7, 0.4, 0.5, mat="brillo")
    for k in range(16):                                       # radios (marcas) entre el anillo interior y el medio
        a = 2 * math.pi * k / 16
        r = 6.8
        C(inte, r * math.cos(a), 0.5, r * math.sin(a), 3.0, 0.3, 0.4, "cristal", rot=[0, SIGNO_Y * (math.degrees(a) + 180), 0], semilla=k)
    C(inte, 0, 0.7, 0, 3.0, 0.5, 3.0, "cristal", rot=[0, 45, 0])
    anim = Animacion("expand", 1.0, bucle=False)
    # de 0,2 a 7,0 veces (radio del pulso: 7 bloques); rapido al principio, se frena al llegar
    anim.esc("wave", lambda u: [0.25 + 6.75 * (1 - (1 - u) ** 2)] * 3, 16)
    anim.rot("anillo_ext", lambda u: [0, 60 * u, 0], 8)
    anim.rot("anillo_med", lambda u: [0, -110 * u, 0], 8)
    anim.rot("anillo_int", lambda u: [0, 180 * u, 0], 8)
    return m, [anim]


# ---------------------------------------------------------------- dron
def drone():
    m = Modelo("dron_arcano", 256, 256, 5)
    m.hueso("root")
    nucleo = m.hueso("core", "root", (0, 4, 0))
    C(nucleo, 0, 4, 0, 2.0, 5.0, 2.0, "cristal", rot=[0, 45, 0])
    C(nucleo, 0, 4, 0, 2.0, 5.0, 2.0, "cristal")
    C(nucleo, 0, 7.2, 0, 3.0, 0.6, 3.0, "metal", rot=[0, 45, 0])
    C(nucleo, 0, 0.8, 0, 3.0, 0.6, 3.0, "metal", rot=[0, 45, 0])
    anillo = m.hueso("ring", "root", (0, 4, 0))
    aro_xz(anillo, 4, 4.6, 10, 3.0, 0.5, 0.6, mat="filo")
    for k in range(5):
        a = 2 * math.pi * (k + 0.5) / 5
        C(anillo, 4.6 * math.cos(a), 4, 4.6 * math.sin(a), 1.8, 0.9, 0.8, "runa", rot=[0, SIGNO_Y * (math.degrees(a) + 90), 0], semilla=k + 40)
    sat = m.hueso("sats", "root", (0, 4, 0))
    for k in range(3):
        a = 2 * math.pi * k / 3
        diamante(sat, 6.2 * math.cos(a), 4 + (1.2 if k % 2 else -1.2), 6.2 * math.sin(a), 1.1, 0.5, "cristal")
    anim = Animacion("spin", 2.0)
    anim.rot("ring", lambda u: [0, 360 * u, 0], 16)
    anim.rot("sats", lambda u: [0, -720 * u, 0], 16)
    anim.pos("core", lambda u: [0, 0.5 * math.sin(2 * math.pi * u), 0], 16)
    anim.rot("core", lambda u: [0, 180 * u, 0], 8)
    return m, [anim]


EFECTOS = {"plasma": plasma, "emp_wave": emp_wave, "drone": drone}


def generar(nombre):
    os.makedirs(SALIDA, exist_ok=True)
    m, anims = EFECTOS[nombre]()
    m.empaquetar()
    base, brillo = pintura.pintar(m)
    m.guardar_geo(os.path.join(SALIDA, nombre + ".geo.json"))
    guardar_animaciones(anims, os.path.join(SALIDA, nombre + ".animation.json"))
    base.save(os.path.join(SALIDA, nombre + ".png"))
    brillo.save(os.path.join(SALIDA, nombre + "_glowmask.png"))
    return m


if __name__ == "__main__":
    for n in EFECTOS:
        print(n, generar(n).estadisticas())
