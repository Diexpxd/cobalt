"""Nucleo del generador de modelos GeckoLib (formato Bedrock geo 1.12.0, UV por cara).

Todo en 'unidades de pixel' (16 = 1 bloque), con el convenio de GeckoLib: el frente del modelo mira a -z (norte) y +x es el LADO IZQUIERDO del personaje.
Las rotaciones de cubo/hueso van en grados; GeckoLib niega X e Y al cargarlas (ver docs/modelo_guardian.md), por eso el visor las replica igual.
"""
import json
import math

CARAS = ("north", "south", "east", "west", "up", "down")


class Cubo:
    def __init__(self, origen, tam, mat="placa", rot=None, pivote=None, inflar=0.0, sin=(), **opc):
        self.origen = [float(v) for v in origen]
        self.tam = [float(v) for v in tam]
        self.mat = mat
        self.rot = [float(v) for v in rot] if rot else None
        self.pivote = [float(v) for v in pivote] if pivote else None
        self.inflar = inflar
        self.sin = set(sin)          # caras que no se dibujan (ocultas)
        self.opc = opc               # opciones para el pintor (linea, glifo, semilla...)
        self.uv = {}                 # cara -> (u, v, w, h) en texels, lo rellena Atlas

    def centro(self):
        return [self.origen[i] + self.tam[i] / 2 for i in range(3)]

    def tam_cara(self, cara, ts):
        dx, dy, dz = self.tam
        if cara in ("north", "south"):
            w, h = dx, dy
        elif cara in ("east", "west"):
            w, h = dz, dy
        else:
            w, h = dx, dz
        return max(2, int(round(w * ts))), max(2, int(round(h * ts)))


class Hueso:
    def __init__(self, nombre, padre=None, pivote=(0, 0, 0), rot=None):
        self.nombre = nombre
        self.padre = padre
        self.pivote = [float(v) for v in pivote]
        self.rot = [float(v) for v in rot] if rot else None
        self.cubos = []

    def cubo(self, origen, tam, mat="placa", **kw):
        c = Cubo(origen, tam, mat, **kw)
        self.cubos.append(c)
        return c


class Modelo:
    def __init__(self, identificador, ancho_tex, alto_tex, ts):
        self.id = identificador
        self.w = ancho_tex
        self.h = alto_tex
        self.ts = ts            # texels por unidad de modelo
        self.huesos = []
        self._por_nombre = {}

    def hueso(self, nombre, padre=None, pivote=(0, 0, 0), rot=None):
        if nombre in self._por_nombre:
            raise ValueError("hueso repetido: " + nombre)
        h = Hueso(nombre, padre, pivote, rot)
        self.huesos.append(h)
        self._por_nombre[nombre] = h
        return h

    def todos_los_cubos(self):
        for h in self.huesos:
            for c in h.cubos:
                yield h, c

    # ---------------------------------------------------------------- atlas de textura
    def empaquetar(self, relleno=1):
        """Reparte un rectangulo de textura a cada cara (estantes de arriba abajo, las mas altas primero)."""
        rects = []
        for _, c in self.todos_los_cubos():
            for cara in CARAS:
                if cara in c.sin:
                    continue
                w, h = c.tam_cara(cara, self.ts)
                rects.append((h, w, c, cara))
        rects.sort(key=lambda r: (-r[0], -r[1]))
        x = y = fila = 0
        for h, w, c, cara in rects:
            if x + w + relleno > self.w:
                x = 0
                y += fila + relleno
                fila = 0
            if y + h + relleno > self.h:
                raise RuntimeError("la textura %dx%d se queda corta (sube el tamano o baja ts)" % (self.w, self.h))
            c.uv[cara] = (x, y, w, h)
            x += w + relleno
            fila = max(fila, h)
        usado = y + fila
        return usado

    # ---------------------------------------------------------------- exportar
    def a_geo(self):
        for h in self.huesos:
            if h.padre and h.padre not in self._por_nombre:
                raise ValueError('el hueso %s tiene un padre inexistente: %s' % (h.nombre, h.padre))
        huesos = []
        for h in self.huesos:
            d = {"name": h.nombre}
            if h.padre:
                d["parent"] = h.padre
            d["pivot"] = [round(v, 3) for v in h.pivote]
            if h.rot:
                d["rotation"] = h.rot
            cubos = []
            for c in h.cubos:
                cd = {"origin": [round(v, 3) for v in c.origen], "size": [round(v, 3) for v in c.tam]}
                if c.rot:
                    cd["pivot"] = [round(v, 3) for v in (c.pivote or c.centro())]
                    cd["rotation"] = c.rot
                if c.inflar:
                    cd["inflate"] = c.inflar
                cd["uv"] = {cara: {"uv": [u, v], "uv_size": [w, hh]} for cara, (u, v, w, hh) in c.uv.items()}
                cubos.append(cd)
            if cubos:
                d["cubes"] = cubos
            huesos.append(d)
        return {
            "format_version": "1.12.0",
            "minecraft:geometry": [{
                "description": {
                    "identifier": "geometry." + self.id,
                    "texture_width": self.w,
                    "texture_height": self.h,
                    "visible_bounds_width": 6,
                    "visible_bounds_height": 5,
                    "visible_bounds_offset": [0, 1.25, 0],
                },
                "bones": huesos,
            }],
        }

    def guardar_geo(self, ruta):
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(self.a_geo(), f, indent=1)

    def estadisticas(self):
        cubos = sum(len(h.cubos) for h in self.huesos)
        alto = max((c.origen[1] + c.tam[1]) for _, c in self.todos_los_cubos())
        return {"huesos": len(self.huesos), "cubos": cubos, "alto_px": round(alto, 1), "alto_bloques": round(alto / 16, 2)}


# ---------------------------------------------------------------- animaciones
def _clave(t):
    return "%.4f" % t


class Animacion:
    """animation.json de GeckoLib: solo claves numericas (sin molang) para que el visor y el juego lean lo mismo."""

    def __init__(self, nombre, duracion, bucle=True):
        self.nombre = nombre
        self.dur = duracion
        self.bucle = bucle
        self.huesos = {}

    def _h(self, hueso):
        return self.huesos.setdefault(hueso, {})

    def _canal(self, hueso, canal, f, pasos, valor):
        """valor: funcion t(0..1) -> [x,y,z] ; se muestrea en 'pasos' puntos (linea poligonal suave)."""
        ks = {}
        for i in range(pasos + 1):
            u = i / pasos
            ks[_clave(u * self.dur)] = [round(v, 4) for v in valor(u)]
        self._h(hueso)[canal] = ks

    def rot(self, hueso, f, pasos=16):
        self._canal(hueso, "rotation", None, pasos, f)
        return self

    def pos(self, hueso, f, pasos=16):
        self._canal(hueso, "position", None, pasos, f)
        return self

    def esc(self, hueso, f, pasos=16):
        self._canal(hueso, "scale", None, pasos, f)
        return self

    def a_dict(self):
        d = {"animation_length": self.dur, "bones": self.huesos}
        if self.bucle:
            d["loop"] = True
        else:
            d["loop"] = "hold_on_last_frame"
        return d


def guardar_animaciones(anims, ruta):
    doc = {"format_version": "1.8.0", "animations": {a.nombre: a.a_dict() for a in anims}}
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)


def sen(u, vueltas=1, fase=0.0):
    return math.sin(2 * math.pi * (u * vueltas + fase))


def cos(u, vueltas=1, fase=0.0):
    return math.cos(2 * math.pi * (u * vueltas + fase))
