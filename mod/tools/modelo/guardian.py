"""Guardian arcano de Cobalt: diseno del modelo (huesos y cubos). Todo en pixeles de modelo (16 = 1 bloque), frente a -z, +x = lado izquierdo del personaje.

Idea de diseno (silueta antes que detalle):
  - Figura esbelta y alta (~2 bloques): hombros marcados, cintura estrecha, piernas largas; armadura violeta profundo con filos azul-verdoso oscuro.
  - Yelmo sin rostro con visera baja, dos ranuras de ojos brillantes, cresta barrida hacia atras y dos cuernos finos con punta luminosa.
  - Rueda de runas (halo) girando tras la cabeza, cristal arcano en el pecho, capa y tabardo en tres tramos para que oscilen.
  - Seis placas-runa flotantes a los costados (tres por lado, en abanico): son el rasgo distintivo; giran, se abren al volar y se cierran al caminar.

Signo de las rotaciones (GeckoLib espeja x): un cubo largo que debe seguir un angulo A medido en el plano del modelo (x del modelo hacia la derecha del dibujo)
lleva rot z = -A. Lo comprueba el visor, que replica el codigo de GeckoLib.
"""
import math

from geo import Modelo

TS = 5                 # texels por unidad de modelo (80 por bloque)
TEX = 512              # lado de la textura


def par(f):
    """Ejecuta f(sx, sufijo) para el lado izquierdo (+x) y el derecho (-x)."""
    f(+1, "_l")
    f(-1, "_r")


def C(hueso, cx, cy, cz, w, h, d, mat="placa", **kw):
    """Cubo por su CENTRO."""
    return hueso.cubo((cx - w / 2, cy - h / 2, cz - d / 2), (w, h, d), mat, **kw)


def diamante(hueso, cx, cy, cz, lado, prof, mat="cristal", **kw):
    """Cubo girado 45 grados en z: de frente es un rombo (punta arriba)."""
    return C(hueso, cx, cy, cz, lado, lado, prof, mat, rot=[0, 0, 45], **kw)


def gema(hueso, cx, cy, cz, lado, mat="cristal"):
    """Dos cubos cruzados (45 en y y 45 en x): se lee como un octaedro pequeno."""
    C(hueso, cx, cy, cz, lado, lado, lado, mat, rot=[0, 45, 0])
    C(hueso, cx, cy, cz, lado, lado, lado, mat, rot=[45, 0, 0])


def construir():
    m = Modelo("guardian_arcano", TEX, TEX, TS)

    m.hueso("root")
    body = m.hueso("body", "root", (0, 14.6, 0))
    torso = m.hueso("torso", "body", (0, 16.6, 0))
    head = m.hueso("head", "torso", (0, 26.8, 0))

    # ------------------------------------------------------------------ pelvis y cinturon
    C(body, 0, 15.1, 0, 6.2, 2.4, 3.9, "placa2")                                     # pelvis
    for sx in (+1, -1):
        C(body, sx * 3.35, 14.2, 0, 1.3, 3.6, 3.3, "placa", rot=[0, 0, sx * 9])       # placas de cadera (faldar)
    C(body, 0, 13.9, -2.05, 3.4, 3.0, 0.7, "placa2", rot=[-7, 0, 0])                 # escarcela delantera
    C(body, 0, 16.6, 0, 6.4, 1.0, 4.2, "metal")                                      # cinturon
    C(body, 0, 16.6, -2.15, 2.5, 2.5, 0.4, "negro", rot=[0, 0, 45])                  # marco de la hebilla
    diamante(body, 0, 16.6, -2.4, 1.7, 0.5, "cristal")                               # hebilla luminosa

    # ------------------------------------------------------------------ tabardo (3 tramos que oscilan)
    t1 = m.hueso("tabardo", "body", (0, 15.6, 0))
    t2 = m.hueso("tabardo2", "tabardo", (0, 11.8, 0))
    t3 = m.hueso("tabardo3", "tabardo2", (0, 8.0, 0))
    C(t1, 0, 13.6, -2.5, 3.6, 3.8, 0.6, "tela", glifo=3)
    C(t2, 0, 9.9, -2.85, 4.0, 3.8, 0.6, "tela")
    C(t3, 0, 6.4, -3.1, 4.4, 3.2, 0.6, "tela", linea="borde")
    diamante(t3, 0, 4.9, -3.1, 3.1, 0.6, "tela", linea="borde")                      # punta

    # ------------------------------------------------------------------ torso (V esbelta)
    C(torso, 0, 18.3, 0, 4.8, 3.0, 3.2, "negro", linea="segmentos")                  # abdomen
    C(torso, 0, 20.8, 0, 6.2, 2.4, 3.8, "placa2")                                    # costillar
    C(torso, 0, 24.0, 0, 7.8, 4.4, 4.2, "placa")                                     # pecho
    C(torso, 0, 22.9, -2.4, 5.6, 3.8, 0.9, "placa", rot=[-8, 0, 0], linea="borde")  # peto
    for sx in (+1, -1):
        C(torso, sx * 3.5, 24.4, -2.1, 1.8, 3.0, 0.8, "placa2", rot=[-6, 0, sx * -8])  # placas pectorales laterales
    diamante(torso, 0, 23.2, -3.15, 2.5, 0.7, "cristal")                             # nucleo arcano
    C(torso, 0, 23.2, -2.95, 3.5, 3.5, 0.4, "negro", rot=[0, 0, 45])                 # engarce
    C(torso, 0, 26.2, 0, 5.2, 1.4, 3.8, "metal")                                     # gorguera
    C(torso, 0, 26.0, 0, 8.6, 0.9, 4.6, "tela", linea="borde")                       # mantelete de tela sobre los hombros
    for sx in (+1, -1):                                                              # respaldo alto del cuello
        C(torso, sx * 2.4, 27.5, 1.7, 0.8, 3.2, 0.7, "placa2", rot=[0, 0, sx * 16])
    C(torso, 0, 23.4, 2.1, 5.4, 6.0, 0.8, "placa2")                                  # espalda
    for k, dx in enumerate((-1.5, 0.0, 1.5)):                                        # columna runica
        C(torso, dx, 23.4, 2.65, 0.4, 5.0 - (0.8 if k == 1 else 0), 0.3, "brillo")

    # ------------------------------------------------------------------ cabeza
    C(head, 0, 27.6, 0, 2.2, 1.4, 2.2, "negro")                                      # cuello
    C(head, 0, 29.9, 0, 4.8, 4.4, 4.8, "placa")                                      # casco
    C(head, 0, 30.6, -0.05, 5.1, 3.0, 4.9, "placa2", linea="borde")                  # frente reforzada
    C(head, 0, 31.6, -2.55, 5.2, 1.2, 0.8, "metal", rot=[-10, 0, 0])                 # visera
    C(head, 0, 29.6, -2.45, 3.7, 2.2, 0.5, "negro")                                  # oquedad del rostro
    C(head, 0, 27.9, -2.35, 3.6, 1.5, 0.8, "placa2", rot=[10, 0, 0])                 # mentonera
    for sx in (+1, -1):
        C(head, sx * 1.2, 29.9, -2.8, 1.5, 0.5, 0.3, "brillo", rot=[0, 0, -sx * 12])  # ranuras de los ojos
        C(head, sx * 2.6, 29.8, 0, 0.7, 3.0, 3.2, "metal")                            # orejeras
    C(head, 0, 32.1, -2.5, 0.8, 0.8, 0.4, "cristal", rot=[0, 0, 45])                 # runa de la frente
    C(head, 0, 32.7, -0.3, 0.8, 1.7, 2.8, "placa2", linea="borde")                   # cresta (3 tramos barridos hacia atras)
    C(head, 0, 32.7, 2.3, 0.8, 1.4, 2.8, "placa2", rot=[-14, 0, 0])
    C(head, 0, 31.8, 4.8, 0.8, 1.1, 2.4, "placa2", rot=[-26, 0, 0])
    C(head, 0, 33.5, 0.4, 0.3, 0.3, 3.4, "brillo")                                   # filo luminoso de la cresta
    for sx in (+1, -1):                                                              # cuernos finos en dos tramos
        C(head, sx * 3.1, 32.0, 0.2, 0.8, 3.0, 0.8, "placa2", rot=[0, 0, -sx * 22])
        C(head, sx * 4.2, 34.2, 0.2, 0.7, 1.6, 0.7, "cristal", rot=[0, 0, -sx * 22])

    # ------------------------------------------------------------------ rueda de runas tras la cabeza (halo): aro continuo + 4 cartuchos + marcas
    halo = m.hueso("halo", "head", (0, 30.0, 4.4))
    R = 5.4
    n = 24
    largo = 2 * math.pi * R / n * 1.10
    for k in range(n):
        a = 2 * math.pi * k / n
        C(halo, R * math.cos(a), 30.0 + R * math.sin(a), 4.4, largo, 0.5, 0.45, "filo", rot=[0, 0, -(math.degrees(a) + 90)])        # aro fino luminoso
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        C(halo, R * math.cos(a), 30.0 + R * math.sin(a), 4.4, 2.6, 1.6, 0.7, "runa", rot=[0, 0, -(math.degrees(a) + 90)], semilla=k + 1)   # cartuchos con runa
    for k in range(8):
        a = k * math.pi / 4
        C(halo, (R + 1.2) * math.cos(a), 30.0 + (R + 1.2) * math.sin(a), 4.4, 0.45, 1.3, 0.35, "brillo", rot=[0, 0, -(math.degrees(a) + 180)])   # marcas radiales
        C(halo, (R - 1.1) * math.cos(a), 30.0 + (R - 1.1) * math.sin(a), 4.4, 0.4, 0.9, 0.3, "cristal", rot=[0, 0, -(math.degrees(a) + 180)])
    diamante(halo, 0, 30.0, 4.4, 1.6, 0.4, "cristal")

    # ------------------------------------------------------------------ hombros y brazos
    def brazo(sx, suf):
        px = sx * 5.2
        pa = m.hueso("pauldron" + suf, "torso", (sx * 5.0, 25.8, 0))
        C(pa, sx * 5.5, 26.2, 0, 3.8, 1.5, 4.6, "placa", rot=[0, 0, sx * -12], linea="borde")       # domo
        C(pa, sx * 5.7, 24.7, 0, 4.1, 1.3, 4.2, "placa2", rot=[0, 0, sx * -8])                      # placa baja
        C(pa, sx * 7.0, 27.7, 0, 1.0, 3.0, 1.0, "placa2", rot=[0, 0, sx * -30])                     # pua
        C(pa, sx * 7.9, 29.3, 0, 0.7, 1.3, 0.7, "cristal", rot=[0, 0, sx * -30])                    # punta luminosa
        C(pa, sx * 5.5, 26.7, -2.25, 3.0, 0.3, 0.4, "brillo", rot=[0, 0, sx * -12])                 # filo frontal

        ar = m.hueso("arm" + suf, "torso", (px, 25.0, 0))
        C(ar, px, 22.7, 0, 2.4, 4.6, 2.4, "negro", linea="segmentos")                                # brazo bajo la armadura
        C(ar, px, 23.0, 0, 2.9, 2.8, 2.9, "placa2", linea="borde")                                   # manguito

        fa = m.hueso("forearm" + suf, "arm" + suf, (px, 20.2, 0))
        C(fa, px, 20.0, 0, 3.0, 1.4, 3.0, "metal")                                                   # codo
        C(fa, px, 20.0, 2.0, 0.9, 0.9, 1.8, "placa2", rot=[-20, 0, 0])                               # pua del codo
        C(fa, px, 17.5, 0, 2.3, 4.4, 2.3, "negro", linea="segmentos")                                # antebrazo
        C(fa, px, 17.3, 0, 3.0, 3.0, 3.0, "placa", linea="borde")                                    # canillera
        C(fa, px, 18.7, 0, 3.15, 0.3, 3.15, "brillo")                                                # anillo luminoso

        ma = m.hueso("hand" + suf, "forearm" + suf, (px, 14.8, 0))
        C(ma, px, 13.9, 0, 2.2, 2.2, 1.6, "placa2")                                                  # palma
        diamante(ma, px, 14.0, -0.95, 1.3, 0.3, "cristal")                                           # sigilo de la palma
        for i, dz in enumerate((-0.6, 0.0, 0.6)):
            C(ma, px, 12.0, dz, 0.6, 1.9, 0.6, "metal", rot=[6 * (i - 1), 0, 0])                     # dedos
        C(ma, px + sx * 1.4, 13.0, -0.2, 0.7, 1.6, 0.7, "metal", rot=[0, 0, sx * -30])               # pulgar
        m.hueso("emitter" + suf, "hand" + suf, (px, 13.0, -1.2))                                     # de aqui salen los hechizos

    par(brazo)

    # ------------------------------------------------------------------ piernas (largas)
    def pierna(sx, suf):
        cx = sx * 2.4
        pi = m.hueso("leg" + suf, "body", (cx, 14.6, 0))
        C(pi, cx, 11.5, 0, 2.9, 6.0, 3.0, "negro", linea="segmentos")                                # muslo
        C(pi, cx, 12.0, -1.75, 3.2, 4.6, 0.7, "placa2", rot=[-4, 0, 0], linea="borde")               # cuisse frontal
        C(pi, cx + sx * 1.7, 11.8, 0, 0.7, 4.6, 2.4, "placa")                                        # placa exterior

        sh = m.hueso("shin" + suf, "leg" + suf, (cx, 8.0, 0))
        C(sh, cx, 7.6, -1.75, 3.2, 1.7, 1.4, "metal", rot=[22, 0, 0])                                # rodillera en cuna
        C(sh, cx, 5.0, 0, 2.5, 5.2, 2.8, "negro", linea="segmentos")                                 # espinilla
        C(sh, cx, 5.0, -1.6, 2.5, 4.4, 0.6, "placa", linea="borde")                                  # canillera
        C(sh, cx, 4.8, 1.6, 2.3, 3.4, 0.5, "placa2")                                                 # pantorrilla
        C(sh, cx, 6.2, -1.95, 0.35, 2.8, 0.3, "brillo")                                              # filo luminoso

        fo = m.hueso("foot" + suf, "shin" + suf, (cx, 2.3, 0))
        C(fo, cx, 1.1, -0.7, 3.0, 2.2, 4.2, "placa2")                                                # bota
        C(fo, cx, 0.8, -2.9, 2.6, 1.4, 1.2, "placa", rot=[-12, 0, 0])                                # puntera
        C(fo, cx, 2.3, 0, 3.2, 0.35, 3.2, "brillo")                                                  # aro luminoso del tobillo
        C(fo, cx, 1.3, 1.7, 2.6, 1.8, 0.7, "placa")                                                  # talon

    par(pierna)

    # ------------------------------------------------------------------ capa (3 tramos)
    c1 = m.hueso("capa", "torso", (0, 25.6, 2.6))
    c2 = m.hueso("capa2", "capa", (0, 17.8, 3.0))
    c3 = m.hueso("capa3", "capa2", (0, 9.8, 3.2))
    C(c1, 0, 21.7, 3.0, 5.8, 7.8, 0.6, "tela", linea="borde", glifo=5, cara_glifo="south")
    C(c2, 0, 13.8, 3.4, 6.2, 8.0, 0.6, "tela")
    C(c3, 0, 6.8, 3.7, 6.6, 6.0, 0.6, "tela", linea="borde")
    diamante(c3, 0, 3.6, 3.7, 3.4, 0.6, "tela", linea="borde")                                        # cola en punta

    # ------------------------------------------------------------------ placas-runa flotantes (rasgo distintivo)
    runas = m.hueso("runas", "torso", (0, 21.0, 0.5))
    especif = [   # (cx, cy, cz, ancho, alto, giro_z)
        (9.0, 25.6, 3.0, 3.2, 8.6, 20),
        (10.6, 19.8, 3.4, 3.0, 7.0, 9),
        (9.2, 14.8, 3.0, 2.6, 5.4, 22),
    ]
    for i, (cx, cy, cz, w, h, giro) in enumerate(especif, start=1):
        for sx, suf in ((+1, "_l"), (-1, "_r")):
            base = m.hueso("runa%s%d" % (suf, i), "runas", (sx * cx, cy, cz), rot=[0, 0, sx * giro])   # el estado (abrir/cerrar) mueve este
            b = m.hueso("runa%s%d_f" % (suf, i), base.nombre, (sx * cx, cy, cz))                       # la capa runica (flotar) mueve este
            px = sx * cx
            C(b, px, cy, cz, w, h, 1.1, "runa", semilla=10 * i + (1 if sx > 0 else 2))                # losa con la runa
            diamante(b, px, cy + h / 2, cz, w * 0.72, 1.1, "runa", semilla=10 * i + 5)                # punta superior
            diamante(b, px, cy - h / 2, cz, w * 0.5, 1.1, "runa", semilla=10 * i + 6)                 # punta inferior
            gema(b, px - sx * (w / 2 + 1.4), cy + 0.6, cz, 0.8)                                       # gema flotante junto a la losa

    return m


if __name__ == "__main__":
    mod = construir()
    usado = mod.empaquetar()
    print(mod.estadisticas(), "| textura usada hasta y=", usado, "de", TEX)
