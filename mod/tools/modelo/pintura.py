"""Pintor de la textura del guardian: paleta violeta profundo + azul verdoso oscuro luminoso, con capa de brillo aparte (nox_glowmask.png).

Cada cara del atlas se pinta segun el material de su cubo: degradado, ruido suave, bisel de 1-2 texels, lineas de panel y runas de un alfabeto propio.
"""
import math

from PIL import Image, ImageDraw

# ---------------------------------------------------------------- paleta
V0, V1, V2, V3, V4 = (14, 9, 26), (28, 19, 50), (48, 33, 82), (74, 52, 118), (112, 86, 164)
M1, M2, M3 = (50, 47, 74), (86, 82, 118), (146, 142, 182)
T1, T2, T3 = (32, 21, 58), (56, 37, 96), (84, 60, 134)
G0, G1, G2, G3, G4 = (4, 46, 52), (8, 104, 104), (18, 168, 156), (58, 224, 204), (176, 252, 238)

MATERIALES = {
    #            arriba, abajo, ruido
    "placa":  (V3, V2, 0.05),
    "placa2": (V2, V1, 0.05),
    "negro":  (V1, V0, 0.04),
    "metal":  (M2, M1, 0.06),
    "tela":   (T3, T1, 0.04),
    "runa":   (V3, V1, 0.05),
    "brillo": (G3, G2, 0.02),
    "cristal": (G3, G2, 0.02),
    "filo":   (G2, G1, 0.02),
}


def _h(x, y, s):
    n = (x * 73856093) ^ (y * 19349663) ^ (s * 83492791)
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def _mezcla(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _luz(c, f):
    return tuple(max(0, min(255, int(round(v * f)))) for v in c)


class Lienzo:
    def __init__(self, w, h):
        self.base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.brillo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.pb = self.base.load()
        self.pg = self.brillo.load()

    def px(self, x, y, c, glow=False, alpha=255):
        if 0 <= x < self.base.width and 0 <= y < self.base.height:
            self.pb[x, y] = (c[0], c[1], c[2], 255)
            if glow:
                self.pg[x, y] = (c[0], c[1], c[2], alpha)


# ---------------------------------------------------------------- runas (alfabeto propio)
def _trazos(seed, w, h):
    """Lista de polilineas en pixeles (relativas a la caja) que forman una runa: 2 o 3 modulos apilados."""
    rnd = lambda i: _h(seed, i, 7)
    modulos = 2 + int(rnd(1) * 2)
    alto = h / modulos
    lineas = []
    for k in range(modulos):
        y0, y1 = k * alto + alto * 0.14, (k + 1) * alto - alto * 0.14
        cx = w / 2
        tipo = int(rnd(10 + k) * 5)
        if tipo == 0:                                   # espina con ramas
            lineas.append([(cx, y0), (cx, y1)])
            for i in range(1, 3):
                yy = y0 + (y1 - y0) * i / 3
                lado = 1 if (i + int(rnd(20 + k) * 2)) % 2 else -1
                lineas.append([(cx, yy), (cx + lado * w * 0.32, yy - (y1 - y0) * 0.22)])
        elif tipo == 1:                                 # anillo con punto y marcas
            r = min(w * 0.30, (y1 - y0) * 0.42)
            cy = (y0 + y1) / 2
            n = 14
            lineas.append([(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)])
            lineas.append([(cx, cy), (cx, cy)])
            lineas.append([(cx, cy - r), (cx, cy - r * 1.5)])
            lineas.append([(cx, cy + r), (cx, cy + r * 1.5)])
        elif tipo == 2:                                 # chevrones
            for i in range(2):
                yy = y0 + (y1 - y0) * (0.3 + 0.4 * i)
                lineas.append([(cx - w * 0.3, yy), (cx, yy + (y1 - y0) * 0.2), (cx + w * 0.3, yy)])
        elif tipo == 3:                                 # Y invertida con barra
            lineas.append([(cx, y1), (cx, (y0 + y1) / 2)])
            lineas.append([(cx - w * 0.3, y0), (cx, (y0 + y1) / 2), (cx + w * 0.3, y0)])
            lineas.append([(cx - w * 0.22, y1 - (y1 - y0) * 0.15), (cx + w * 0.22, y1 - (y1 - y0) * 0.15)])
        else:                                           # barras escalonadas
            for i in range(3):
                yy = y0 + (y1 - y0) * (0.15 + 0.35 * i)
                ancho = w * (0.5 - 0.12 * ((i + int(rnd(30 + k) * 3)) % 3))
                lineas.append([(cx - ancho / 2, yy), (cx + ancho / 2, yy)])
    return lineas


def dibujar_runa(lienzo, x0, y0, w, h, seed, color=G3, halo=G1, grosor=None):
    if w < 8 or h < 12:
        return
    margen = max(2, int(w * 0.12))
    ancho, alto = w - 2 * margen, h - 2 * margen
    if ancho < 4 or alto < 6:
        return
    g = grosor or max(1, int(round(min(w, h) / 13)))
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for pl in _trazos(seed, ancho, alto):
        pts = [(margen + px, margen + py) for px, py in pl]
        if len(pts) == 1 or pts[0] == pts[-1] and len(pts) == 2:
            x, y = pts[0]
            d.ellipse([x - g, y - g, x + g, y + g], fill=(255, 255, 255, 255))
        else:
            d.line(pts, fill=(255, 255, 255, 255), width=g)
    pl = capa.load()
    for y in range(h):
        for x in range(w):
            if pl[x, y][3]:
                lienzo.px(x0 + x, y0 + y, color, glow=True)
    if g >= 2:   # halo tenue alrededor (solo en la base, da profundidad)
        for y in range(h):
            for x in range(w):
                if pl[x, y][3]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < w and 0 <= yy < h and pl[xx, yy][3]:
                        lienzo.px(x0 + x, y0 + y, halo, glow=True, alpha=110)
                        break


# ---------------------------------------------------------------- pintado por material
def _bisel(x, y, w, h, grosor):
    """Factor de luz por cercania al borde: arriba/izquierda claro, abajo/derecha oscuro."""
    f = 1.0
    if y < grosor:
        f += 0.20
    if x < grosor:
        f += 0.10
    if y >= h - grosor:
        f -= 0.24
    if x >= w - grosor:
        f -= 0.16
    return f


def pintar_cara(lz, cubo, cara, x0, y0, w, h, semilla):
    mat = cubo.mat
    ar, ab, ruido = MATERIALES[mat]
    op = cubo.opc
    linea = op.get("linea")
    grosor = 2 if min(w, h) >= 16 else 1
    factor_cara = {"up": 1.10, "north": 1.0, "south": 0.9, "east": 0.94, "west": 0.86, "down": 0.6}[cara]
    emisivo = mat in ("brillo", "cristal", "filo")
    for y in range(h):
        t = y / max(1, h - 1)
        for x in range(w):
            c = _mezcla(ar, ab, t)
            r = (_h(x0 + x, y0 + y, semilla) - 0.5) * 2 * ruido
            f = (1.0 + r) * factor_cara
            if not emisivo:
                f *= _bisel(x, y, w, h, grosor) if mat != "tela" else 1.0
            if mat == "metal":                                     # cepillado horizontal
                f *= 1.0 + 0.06 * math.sin(y * 1.7 + _h(0, y, semilla) * 6)
            if mat == "tela":                                      # pliegues verticales
                f *= 1.0 + 0.11 * math.sin(x * 0.85 + semilla) * (0.6 + 0.4 * t)
            if linea == "segmentos" and y % max(4, int(h / 5)) == 0:
                f *= 0.6
            c = _luz(c, f)
            if emisivo:
                # nucleo caliente al centro, borde oscuro; brilla entero
                dx, dy = (x + 0.5) / w - 0.5, (y + 0.5) / h - 0.5
                d = math.sqrt(dx * dx + dy * dy) * 2
                if mat == "cristal":
                    c = _mezcla(G4, G2, min(1.0, d * 1.3))
                    if (x + y) % 7 == 0 or abs(x - y * w / max(1, h)) < 0.6:   # facetas
                        c = _mezcla(c, G4, 0.35)
                    if d > 0.85:
                        c = _mezcla(c, G1, 0.6)
                elif mat == "filo":
                    c = _mezcla(G3, G1, min(1.0, abs(dy) * 2.2 + t * 0.3))
                else:
                    c = _mezcla(G4, G3, min(1.0, abs(dy) * 2.4)) if min(w, h) >= 3 else G3
                lz.px(x0 + x, y0 + y, c, glow=True)
            else:
                lz.px(x0 + x, y0 + y, c)

    # ---- detalles por material
    if mat in ("placa", "placa2", "metal") and linea == "borde" and w >= 12 and h >= 12:
        i = 3 if min(w, h) >= 18 else 2                               # filete luminoso hundido
        for x in range(i, w - i):
            lz.px(x0 + x, y0 + i, G1, glow=True, alpha=200)
            lz.px(x0 + x, y0 + h - 1 - i, G0)
        for y in range(i, h - i):
            lz.px(x0 + i, y0 + y, G1, glow=True, alpha=200)
            lz.px(x0 + w - 1 - i, y0 + y, G0)
        for cx, cy in ((i + 2, i + 2), (w - i - 3, i + 2), (i + 2, h - i - 3), (w - i - 3, h - i - 3)):   # remaches
            lz.px(x0 + cx, y0 + cy, M3)
    if mat == "tela" and linea == "borde" and h >= 8:                 # dobladillo luminoso
        for x in range(w):
            for k, col in enumerate((G3, G2, G1)):
                if h - 1 - k >= 0:
                    lz.px(x0 + x, y0 + h - 1 - k, col, glow=True, alpha=230 - 50 * k)
    if mat == "tela" and op.get("glifo") and cara == op.get("cara_glifo", "north"):
        dibujar_runa(lz, x0, y0, w, h, op["glifo"] + 40, color=G2, halo=G1)
    if mat == "runa":
        # marco fino: 1 texel de azul-verdoso oscuro (con un poco de brillo) y un filete interior apagado; el brillo fuerte se reserva para la runa
        for x in range(w):
            for k, (col, al) in enumerate(((G1, 150), (G0, 0))):
                if k >= h // 2:
                    break
                lz.px(x0 + x, y0 + k, col, glow=al > 0, alpha=al)
                lz.px(x0 + x, y0 + h - 1 - k, col, glow=al > 0, alpha=al)
        for y in range(h):
            for k, (col, al) in enumerate(((G1, 150), (G0, 0))):
                if k >= w // 2:
                    break
                lz.px(x0 + k, y0 + y, col, glow=al > 0, alpha=al)
                lz.px(x0 + w - 1 - k, y0 + y, col, glow=al > 0, alpha=al)
        if cara in ("north", "south") and w >= 9 and h >= 14:
            dibujar_runa(lz, x0 + 2, y0 + 2, w - 4, h - 4, op.get("semilla", 1) * 3 + (0 if cara == "north" else 1))


def pintar(modelo):
    lz = Lienzo(modelo.w, modelo.h)
    n = 0
    for _, c in modelo.todos_los_cubos():
        for cara, (u, v, w, h) in c.uv.items():
            n += 1
            pintar_cara(lz, c, cara, u, v, w, h, n)
    return lz.base, lz.brillo
