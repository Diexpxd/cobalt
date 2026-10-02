"""nox_mision.py."""
import math
import re
import time

from nox_pro import _normalizar_frase, _numero, distancia_xz, orden, posicion

MATERIALES_ES = {
    "hierro": "iron_ore", "carbon": "coal_ore", "diamante": "diamond_ore", "diamantes": "diamond_ore", "oro": "gold_ore", "cobre": "copper_ore",
    "redstone": "redstone_ore", "lapis": "lapis_ore", "lapislazuli": "lapis_ore", "lapis lazuli": "lapis_ore", "esmeralda": "emerald_ore",
    "esmeraldas": "emerald_ore", "cuarzo": "nether_quartz_ore", "escombros antiguos": "ancient_debris", "ancient debris": "ancient_debris",
    "piedra": "stone", "tierra": "dirt", "arena": "sand", "troncos": "log", "madera": "log", "lena": "log", "menas": "cualquiera",
    "minerales": "cualquiera", "cualquiera": "cualquiera",
}
MAX_CANTIDAD = 64
MAX_MINUTOS = 60


def _material(texto):
    t = texto.strip()
    etiqueta = re.fullmatch(r"(forge|c) (ores|logs|ingots)(?: ([a-z_]+))?", t)  # "forge ores iron" = la etiqueta forge:ores/iron
    if etiqueta:
        return f"{etiqueta.group(1)}:{etiqueta.group(2)}" + (f"/{etiqueta.group(3)}" if etiqueta.group(3) else "")
    if t in MATERIALES_ES:
        return MATERIALES_ES[t]
    if re.fullmatch(r"[a-z0-9_]+", t) and ("_" in t or t in ("stone", "dirt", "sand", "log")):  # un id de Minecraft escrito tal cual
        return t
    return None


_VERBO = r"(?:consigue|consigueme|junta|recolecta|mina|minar|trae|traeme|extrae|saca)"
_CONECTOR = r"(?:\s+(?:o|y)\s+(?:regresa|vuelve|volver|regresar)(?:\s+a la base)?)?"
_RE_CANTIDAD_PRIMERO = re.compile(_VERBO + r"\s+(?:me\s+)?(\d+)\s+(?:de\s+)?([a-z_ ]+?)" + _CONECTOR + r"\s+(?:en|dentro de|durante|antes de)\s+(\d+)\s*(?:min|minutos)")
_RE_TIEMPO_PRIMERO = re.compile(r"(?:en|dentro de|durante)\s+(\d+)\s*(?:min|minutos)\s*,?\s*" + _VERBO + r"\s+(?:me\s+)?(\d+)\s+(?:de\s+)?([a-z_ ]+?)\s*(?:y\s+regresa.*|o\s+regresa.*|y\s+vuelve.*)?$")


def interpretar_mision(mensaje):
    """{'cantidad', 'material', 'minutos'} de "consigue 64 de hierro o regresa en 10 minutos" (u orden inversa), o None."""
    f = _normalizar_frase(mensaje)
    if not f:
        return None
    m = _RE_CANTIDAD_PRIMERO.search(f)
    if m:
        cantidad, crudo, minutos = int(m.group(1)), m.group(2), int(m.group(3))
    else:
        m = _RE_TIEMPO_PRIMERO.search(f)
        if not m:
            return None
        minutos, cantidad, crudo = int(m.group(1)), int(m.group(2)), m.group(3)
    crudo = re.sub(r"\b(o|y|regresa|vuelve|volver|regresar|a la base)\b", " ", crudo)
    crudo = re.sub(r"\s+", " ", crudo).strip()
    material = _material(crudo)
    if not material or cantidad < 1 or minutos < 1:
        return None
    return {"cantidad": min(cantidad, MAX_CANTIDAD), "material": material, "minutos": min(minutos, MAX_MINUTOS)}


class MisionTemporal:
    """Una misión: minar N de X en M minutos y volver a la base."""

    GRACIA_S = 90.0
    RADIO_BASE = 6.0
    REEMISION_S = 10.0
    MAX_REGRESO_S = 240.0

    def __init__(self):
        self.activa = None

    def iniciar(self, mision, ahora):
        self.activa = dict(mision, t0=ahora, limite=ahora + mision["minutos"] * 60.0, fase="minando", t_regreso=0.0, t_orden=0.0, obtenidos=None)

    def ordenes_de_inicio(self, mision):
        nombre = mision["material"].replace("_ore", "").replace("_", " ")
        return [orden("mine", f"Misión: {mision['cantidad']} de {nombre} en {mision['minutos']} minutos; después vuelvo a la base.",
                      material=mision["material"], amount=mision["cantidad"], minutes=mision["minutos"], modo="walk")]

    @staticmethod
    def _base(waypoints):
        b = (waypoints or {}).get("base")
        return posicion(b) if isinstance(b, dict) else None

    def _ir_a_base(self, base, chat):
        x, y, z = (int(math.floor(v)) for v in base)
        return orden("go_to", chat, modo="fly", x=x, y=y, z=z)

    def actualizar(self, estado, gps, feedback, waypoints, ahora):
        m = self.activa
        if not m:
            return []
        base = self._base(waypoints)
        if m["fase"] == "minando":
            terminado = bool(feedback) and _numero(feedback.get("mtime")) and feedback["mtime"] >= m["t0"] and feedback.get("status") in ("success", "partial", "failed")
            vencido = ahora > m["limite"] + self.GRACIA_S
            if not terminado and not vencido:
                return []
            m["fase"], m["t_regreso"], m["t_orden"] = "regreso", ahora, ahora
            salida = []
            if terminado:
                m["obtenidos"] = int(feedback.get("mined", 0) or 0)
                cumplida = m["obtenidos"] >= m["cantidad"]
                resumen = (f"Misión cumplida: {m['obtenidos']}/{m['cantidad']}." if cumplida else
                           f"Misión sin completar: {m['obtenidos']}/{m['cantidad']}" + (f" ({feedback['detalle']})" if feedback.get("detalle") else "") + ".")
            else:
                salida += [orden("flush"), orden("stop")]  # Java no respondió: se detiene todo
                resumen = f"Se acabó el plazo de {m['minutos']} minutos y no tengo el informe: me detengo."
            if base:
                salida.append(self._ir_a_base(base, resumen + " Vuelvo a la base."))
            else:
                salida.append(orden("ninguna", resumen + " No tengo un waypoint 'base' guardado, así que me quedo aquí."))
                self.activa = None
            return salida
        # fase regreso
        p = posicion(gps)
        if base is None or ahora - m["t_regreso"] > self.MAX_REGRESO_S:
            self.activa = None
            return [orden("ninguna", "No logré llegar a la base a tiempo; me quedo donde estoy.")] if base else []
        if p and distancia_xz(p, base) <= self.RADIO_BASE:
            self.activa = None
            return [orden("ninguna", "Llegué a la base.")]
        if ahora - m["t_orden"] >= self.REEMISION_S:
            m["t_orden"] = ahora
            return [self._ir_a_base(base, None)]
        return []


PREFIJOS_AUTO = ("inventario_nox_", "muerte_nox_")  # waypoints que Java crea solo (lleva la hora en milisegundos en el nombre)


def waypoints_a_purgar(waypoints, ahora_ms, max_edad_ms=24 * 3600 * 1000, conservar=3):
    """Nombres de waypoints AUTOMÁTICOS (los de Java, con sello de tiempo) que se pueden borrar: más viejos que 'max_edad_ms' y fuera de los"""
    a_borrar = []
    if not isinstance(waypoints, dict):
        return a_borrar
    for prefijo in PREFIJOS_AUTO:
        candidatos = []
        for nombre in waypoints:
            if isinstance(nombre, str) and nombre.startswith(prefijo) and nombre[len(prefijo):].isdigit():
                candidatos.append((int(nombre[len(prefijo):]), nombre))
        candidatos.sort(reverse=True)  # los más recientes primero
        for sello, nombre in candidatos[conservar:]:
            if ahora_ms - sello > max_edad_ms:
                a_borrar.append(nombre)
    return a_borrar
