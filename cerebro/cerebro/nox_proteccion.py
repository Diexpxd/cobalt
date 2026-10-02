"""nox_proteccion.py."""
import math
import re
from collections import deque

import nox_voz
from nox_pro import (_normalizar_frase, _numero, distancia, distancia_xz, dueno, entidades_de, hostiles, orden, posicion)


def _posicion_entidad(e):
    return posicion(e) if isinstance(e, dict) else None


def _unitario_xz(desde, hacia):
    dx, dz = hacia[0] - desde[0], hacia[2] - desde[2]
    n = math.hypot(dx, dz)
    return (dx / n, dz / n) if n > 1e-9 else (0.0, 0.0)


def vida_dueno_pct(gps, entidades=None):
    """% de vida del jugador dueño: de entities.json (jugador con owner) o, si no, de gps.json['owner']. None si no se sabe."""
    d = dueno(entidades) if entidades else None
    if d and _numero(d.get("hp")) and _numero(d.get("max_hp")) and d["max_hp"] > 0:
        return 100.0 * d["hp"] / d["max_hp"]
    o = gps.get("owner") if isinstance(gps, dict) else None
    if isinstance(o, dict) and _numero(o.get("hp")) and _numero(o.get("max_hp")) and o["max_hp"] > 0:
        return 100.0 * o["hp"] / o["max_hp"]
    return None


def _pos_dueno(gps, entidades):
    d = dueno(entidades) if entidades else None
    return _posicion_entidad(d) or posicion(gps.get("owner") if isinstance(gps, dict) else None)


def _pos_bot(gps, entidades):
    yo = entidades.get("bot") if isinstance(entidades, dict) else None
    return posicion(yo) or posicion(gps)


def mayor_amenaza(entidades, radio=30.0):
    """El hostil más peligroso: jefe > creeper a punto de estallar > agresor del jugador > arquero con línea de vista > el que se acerca > el más cercano."""
    candidatos = [e for e in hostiles(entidades) if _numero(e.get("dist")) and e["dist"] <= radio]

    def puntos(e):
        s = -e["dist"]
        if e.get("boss"):
            s += 100
        if e.get("swelling"):
            s += 60
        if e.get("targets_player"):
            s += 40
        if e.get("ranged") and e.get("los"):
            s += 30
        if e.get("approaching"):
            s += 15
        return s

    return max(candidatos, key=puntos, default=None)


class Guardaespaldas:
    """Ante un jefe o un enemigo a distancia con línea de vista, Cobalt se coloca ENTRE el jugador y la amenaza (a ~3 bloques del jugador)"""

    DIST_AL_DUENO = 3.0
    RADIO_PUESTO = 3
    REAJUSTE_S = 1.5
    MIN_MOVIMIENTO = 1.5
    CALMA_S = 4.0
    ALCANCE = 30.0

    def __init__(self):
        self.activo = False
        self.ultima_ancla = None
        self.t_ultimo = -1e9
        self.t_calma = None
        self.restaurar_follow = False

    def actualizar(self, estado, gps, entidades, ahora):
        salida = []
        dpos = _pos_dueno(gps, entidades)
        amenaza = None
        if dpos and estado.get("is_deployed") and not estado.get("critical_hp"):
            aptos = []
            for e in hostiles(entidades):
                epos = _posicion_entidad(e)
                if epos and (e.get("boss") or (e.get("ranged") and e.get("los"))) and distancia(epos, dpos) <= self.ALCANCE:
                    aptos.append(e)
            amenaza = mayor_amenaza({"entities": aptos}, radio=self.ALCANCE + 64)
        if amenaza:
            self.t_calma = None
            apos = _posicion_entidad(amenaza)
            ux, uz = _unitario_xz(dpos, apos)
            d = min(self.DIST_AL_DUENO, distancia_xz(dpos, apos) / 2.0)
            ancla = (dpos[0] + ux * d, dpos[1] + 1.0, dpos[2] + uz * d)
            if not self.activo:
                self.activo = True
                self.restaurar_follow = bool(estado.get("following"))
                salida.append(orden("ninguna", nox_voz.frase("cubrir", amenaza=amenaza.get('name', 'la amenaza'))))
            movio = self.ultima_ancla is None or distancia(ancla, self.ultima_ancla) > self.MIN_MOVIMIENTO
            if movio and ahora - self.t_ultimo >= self.REAJUSTE_S:
                self.t_ultimo = ahora
                self.ultima_ancla = ancla
                salida.append(orden("stand_ground", modo="fly", x=int(math.floor(ancla[0])), y=int(math.floor(ancla[1])),
                                    z=int(math.floor(ancla[2])), radius=self.RADIO_PUESTO))
        elif self.activo:
            if self.t_calma is None:
                self.t_calma = ahora
            elif ahora - self.t_calma >= self.CALMA_S:
                self.activo = False
                self.ultima_ancla = None
                if self.restaurar_follow:
                    salida.append(orden("follow", "Amenaza controlada: vuelvo contigo."))
        return salida


class RoboDeAggro:
    """Si el jugador está a punto de morir (< 20 % de vida) y hay algo atacándole, Cobalt lo ataca A ÉL (por su 'target_id') con plasma y,"""

    UMBRAL_PCT = 20.0
    COOLDOWN_S = 3.0
    ALCANCE = 35.0

    def __init__(self):
        self.t_ultimo = -1e9
        self.activo = False

    def actualizar(self, estado, gps, entidades, ahora):
        pct = vida_dueno_pct(gps, entidades)
        if pct is None or pct >= self.UMBRAL_PCT or not estado.get("is_deployed") or estado.get("critical_hp"):
            self.activo = False
            return []
        atacantes = [e for e in hostiles(entidades) if e.get("targets_player") and _numero(e.get("dist")) and e["dist"] <= self.ALCANCE and _numero(e.get("id"))]
        if not atacantes:
            self.activo = False
            return []
        if ahora - self.t_ultimo < self.COOLDOWN_S:
            return []
        objetivo = max(atacantes, key=lambda e: (bool(e.get("boss")), -e["dist"]))  # primero el jefe; si no, el más cercano
        self.t_ultimo = ahora
        chat = None if self.activo else nox_voz.frase("provocar", objetivo=objetivo.get('name', 'Eh'))
        self.activo = True
        salida = [orden("defend", chat, modo="fly", target_id=int(objetivo["id"]), urgente=True),
                  orden("shoot_plasma", modo="fly", target_id=int(objetivo["id"]), urgente=True)]
        if estado.get("emp_ready") and not objetivo.get("boss") and objetivo["dist"] <= 6.0:
            salida.append(orden("special_power", modo="fly", urgente=True))
        return salida


class AsistenciaMuerteDueno:
    """Si el jugador muere, Cobalt va al lugar, limpia un perímetro de 10 bloques y monta guardia sobre sus ítems (5 min: lo que tardan"""

    RADIO = 10
    MAX_S = 300.0
    RECOGIDA_M = 12.0
    ESPERA_TRAS_LLEGAR_S = 8.0

    def __init__(self):
        self.fase = "idle"
        self.ultima = None
        self.punto = None
        self.t0 = 0.0
        self.t_llegada = None

    def actualizar(self, estado, gps, ahora):
        o = gps.get("owner") if isinstance(gps, dict) else None
        if not isinstance(o, dict) or not estado.get("is_deployed"):
            return []
        pos = posicion(o)
        vivo = bool(o.get("alive", True)) and not (_numero(o.get("hp")) and o["hp"] <= 0)
        if self.fase == "idle":
            if vivo and pos:
                self.ultima = pos
                return []
            if not vivo and self.ultima:
                self.fase, self.punto, self.t0, self.t_llegada = "guardia", self.ultima, ahora, None
                x, y, z = (int(math.floor(v)) for v in self.punto)
                return [orden("go_to", "Tranquilo, cuido tus cosas: limpio el perímetro y monto guardia.", modo="fly", x=x, y=y, z=z, urgente=True),
                        orden("stand_ground", modo="fly", x=x, y=y, z=z, radius=self.RADIO, urgente=True)]
            return []
        # fase guardia
        if vivo and pos and distancia_xz(pos, self.punto) <= self.RECOGIDA_M:
            if self.t_llegada is None:
                self.t_llegada = ahora
            elif ahora - self.t_llegada >= self.ESPERA_TRAS_LLEGAR_S:
                self.fase = "idle"
                return [orden("follow", "Ya recogiste tus cosas: vuelvo contigo.")]
        if ahora - self.t0 > self.MAX_S:
            self.fase = "idle"
            return [orden("follow", "Han pasado 5 minutos: dejo la guardia y vuelvo contigo.")]
        return []


class EvasionCreeper:
    """Un creeper que se hincha (el 'Creeper Hisses' que Java reporta como 'swelling') a menos de 8 bloques: Cobalt se aparta 10 bloques en"""

    RADIO_ALERTA = 8.0
    HUIDA = 10.0
    COOLDOWN_S = 2.0
    PELIGRO_DUENO = 7.0

    def __init__(self):
        self.t_ultimo = -1e9
        self.avisados = set()

    def actualizar(self, estado, gps, entidades, ahora):
        bot = _pos_bot(gps, entidades)
        if not bot or not estado.get("is_deployed"):
            return []
        creepers = [e for e in entidades_de(entidades) if e.get("swelling") and _numero(e.get("dist")) and e["dist"] <= self.RADIO_ALERTA and _posicion_entidad(e)]
        if not creepers:
            self.avisados.clear()
            return []
        c = min(creepers, key=lambda e: e["dist"])
        salida = []
        d = dueno(entidades)
        dpos = _posicion_entidad(d)
        if dpos and _numero(c.get("id")) and c["id"] not in self.avisados and distancia(dpos, _posicion_entidad(c)) <= self.PELIGRO_DUENO:
            self.avisados.add(c["id"])
            salida.append(orden("ninguna", nox_voz.frase("creeper_cerca"), urgente=True))
        if ahora - self.t_ultimo >= self.COOLDOWN_S:
            self.t_ultimo = ahora
            ux, uz = _unitario_xz(_posicion_entidad(c), bot)
            if ux == 0.0 and uz == 0.0:
                ux = 1.0
            destino = (bot[0] + ux * self.HUIDA, bot[1] + 1.0, bot[2] + uz * self.HUIDA)
            salida.append(orden("go_to", nox_voz.frase("creeper_me_aparto"), modo="fly", x=int(math.floor(destino[0])),
                                y=int(math.floor(destino[1])), z=int(math.floor(destino[2])), urgente=True))
        return salida


class AlertaSOS:
    """Si la vida de Cobalt cae de golpe (>= 30 puntos porcentuales en 6 s), avisa por el chat dónde está y quién le ataca."""

    VENTANA_S = 6.0
    CAIDA_PCT = 30.0
    COOLDOWN_S = 60.0

    def __init__(self):
        self.historial = deque()
        self.t_ultimo = -1e9

    def actualizar(self, estado, gps, entidades, ahora):
        pct = estado.get("hp_pct")
        if not estado.get("is_deployed") or not _numero(pct):
            self.historial.clear()
            return []
        self.historial.append((ahora, pct))
        while self.historial and ahora - self.historial[0][0] > self.VENTANA_S:
            self.historial.popleft()
        caida = max(p for _, p in self.historial) - pct
        if caida < self.CAIDA_PCT or ahora - self.t_ultimo < self.COOLDOWN_S:
            return []
        self.t_ultimo = ahora
        p = posicion(gps)
        donde = f" en [{int(p[0])}, {int(p[1])}, {int(p[2])}]" if p else ""
        cerca = [e for e in hostiles(entidades) if _numero(e.get("dist")) and e["dist"] <= 24]
        nombres = []
        for e in sorted(cerca, key=lambda e: e["dist"]):
            n = e.get("name", "?")
            if n not in nombres:
                nombres.append(n)
        quien = f" Me atacan {len(cerca)}: {', '.join(nombres[:3])}." if cerca else ""
        return [orden("ninguna", nox_voz.frase("emboscada", donde=donde, pct=int(pct), quien=quien), urgente=True)]


_PUNTOS_CARDINALES = [("este", 0), ("sur", 90), ("oeste", 180), ("norte", 270)]  # +x = este, +z = sur (convención de Minecraft)


def _cardinal(dx, dz):
    ang = math.degrees(math.atan2(dz, dx)) % 360
    return min(_PUNTOS_CARDINALES, key=lambda c: min(abs(ang - c[1]), 360 - abs(ang - c[1])))[0]


def triangular_agresor(dano, entidades, bot_pos=None):
    """A partir de 'last_damage' (nox_status.json) localiza al tirador."""
    if not isinstance(dano, dict) or not dano.get("projectile"):
        return None, None, None
    hs = [e for e in hostiles(entidades) if _posicion_entidad(e)]
    if _numero(dano.get("sx")) and _numero(dano.get("sz")):
        cand = [e for e in hs if math.hypot(e["x"] - dano["sx"], e["z"] - dano["sz"]) <= 3.0]
        if cand:
            return min(cand, key=lambda e: math.hypot(e["x"] - dano["sx"], e["z"] - dano["sz"])), "conocido", (dano["sx"], dano["sz"])
    if all(_numero(dano.get(k)) for k in ("dx", "dz", "dvx", "dvz")):
        vx, vz = dano["dvx"], dano["dvz"]
        v = math.hypot(vx, vz)
        if v < 0.05:
            return None, None, None
        ux, uz = -vx / v, -vz / v  # hacia atrás: de donde vino
        mejor, mejor_perp = None, 4.0
        for e in hs:
            rx, rz = e["x"] - dano["dx"], e["z"] - dano["dz"]
            t = rx * ux + rz * uz
            if t < 0 or t > 60:
                continue
            perp = abs(rx * uz - rz * ux)
            if perp <= mejor_perp:
                mejor, mejor_perp = e, perp
        if mejor:
            return mejor, "triangulado", (mejor["x"], mejor["z"])
        return None, "direccion", (dano["dx"] + ux * 20, dano["dz"] + uz * 20)
    return None, None, None


class Triangulacion:
    """Reacciona al daño por proyectil: contraataca al tirador si lo localiza; si no, avisa de qué dirección vinieron los disparos."""

    COOLDOWN_S = 3.0
    AVISO_DIRECCION_S = 20.0

    def __init__(self):
        self.ultimo = None
        self.t_ultimo = -1e9
        self.t_aviso = -1e9

    def actualizar(self, estado, gps, entidades, ahora):
        dano = estado.get("last_damage")
        if not estado.get("is_deployed") or not isinstance(dano, dict):
            return []
        firma = (dano.get("type"), dano.get("dx"), dano.get("dz"), dano.get("dvx"), dano.get("sx"), dano.get("sz"))
        if firma == self.ultimo or ahora - self.t_ultimo < self.COOLDOWN_S:
            return []
        self.ultimo = firma
        entidad, metodo, punto = triangular_agresor(dano, entidades, _pos_bot(gps, entidades))
        if metodo is None:
            return []
        self.t_ultimo = ahora
        if entidad is not None and _numero(entidad.get("id")):
            chat = f"Me disparan: {entidad.get('name', 'un enemigo')} ({'lo veo' if metodo == 'conocido' else 'lo localicé por la trayectoria'}). Contraataco."
            return [orden("defend", chat, modo="fly", target_id=int(entidad["id"]), urgente=True),
                    orden("shoot_plasma", modo="fly", target_id=int(entidad["id"]), urgente=True)]
        bot = _pos_bot(gps, entidades)
        if punto and bot and ahora - self.t_aviso >= self.AVISO_DIRECCION_S:
            self.t_aviso = ahora
            return [orden("ninguna", f"Me disparan desde el {_cardinal(punto[0] - bot[0], punto[1] - bot[2])}, pero no veo al tirador.", urgente=True)]
        return []


def interpretar_guardia(mensaje):
    """'cubrir' (montar guardia sobre el jugador), 'torreta' (guardia en el sitio actual), 'seguir' (dejar la guardia) o None."""
    f = _normalizar_frase(mensaje)
    if not f:
        return None
    if re.search(r"\bcubreme\b|cubre mi espalda|cuida mi espalda|protegeme mientras", f):
        return "cubrir"
    if any(k in f for k in ("modo torreta", "monta guardia", "haz guardia", "defiende aqui", "defiende esta posicion", "quedate aqui y defiende")):
        return "torreta"
    if any(k in f for k in ("deja de guardar", "fin de guardia", "ya termine de minar", "puedes seguirme")):
        return "seguir"
    return None


def ordenes_guardia(tipo, gps, radio_cubrir=10, radio_torreta=12):
    """Órdenes para 'cubrir' (en la posición del jugador), 'torreta' (donde está Cobalt) o 'seguir'."""
    if tipo == "seguir":
        return [orden("follow", "Vale, vuelvo a seguirte.")]
    if tipo == "torreta":
        return [orden("stand_ground", "Modo torreta: defiendo esta posición.", radius=radio_torreta)]
    if tipo == "cubrir":
        p = posicion(gps.get("owner") if isinstance(gps, dict) else None)
        if p:
            return [orden("stand_ground", "Te cubro. Avísame cuando termines.", modo="fly", x=int(math.floor(p[0])), y=int(math.floor(p[1])),
                          z=int(math.floor(p[2])), radius=radio_cubrir)]
        return [orden("stand_ground", "Te cubro desde aquí. Avísame cuando termines.", radius=radio_cubrir)]
    return []
