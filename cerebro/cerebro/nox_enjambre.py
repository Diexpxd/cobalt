"""nox_enjambre.py: decisión del ENJAMBRE DE DRONES (5 drones de apoyo, 60 s, enfriamiento de 4 min)."""
import re

from nox_pro import _normalizar_frase, _numero, hostiles, orden
from nox_proteccion import vida_dueno_pct

RADIO_JEFE = 30.0
RADIO_HORDA = 16.0
MIN_HORDA = 4


def motivo_de_despliegue(estado, gps, entidades):
    """Por qué merece la pena desplegar el enjambre AHORA (texto corto) o None."""
    hs = [e for e in hostiles(entidades) if _numero(e.get("dist"))]
    for e in hs:
        if e.get("boss") and e["dist"] <= RADIO_JEFE:
            return f"jefe {e.get('name', '')}".strip()
    pct = vida_dueno_pct(gps, entidades)
    if pct is not None and pct < 50.0 and any(e.get("targets_player") and e["dist"] <= 30.0 for e in hs):
        return "el jugador está en peligro"
    cerca = [e for e in hs if e["dist"] <= RADIO_HORDA]
    hp = estado.get("hp_pct")
    if estado.get("in_combat") and _numero(hp) and hp < 50 and len(cerca) >= 2:
        return "Cobalt está en apuros"
    if len(cerca) >= MIN_HORDA:
        return f"{len(cerca)} enemigos cerca"
    return None


class DespliegueDrones:
    """Pide el enjambre cuando hay motivo y Java dice que está listo."""

    REINTENTO_S = 5.0

    def __init__(self):
        self.t_ultimo = -1e9
        self.ultimo_motivo = None

    def actualizar(self, estado, gps, entidades, ahora):
        if not estado.get("is_deployed") or estado.get("frozen"):
            return []
        if not estado.get("drones_ready") or estado.get("drones_active"):
            return []
        if ahora - self.t_ultimo < self.REINTENTO_S:
            return []
        motivo = motivo_de_despliegue(estado, gps, entidades if isinstance(entidades, dict) else {})
        if not motivo:
            return []
        self.t_ultimo = ahora
        self.ultimo_motivo = motivo
        return [orden("deploy_drones", modo="fly", urgente=True)]


_RE_DESPLEGAR = re.compile(r"^(?:cobalt\s+)?(?:por favor\s+)?(?:(?:despliega|desplegar|lanza|suelta|activa|llama|manda|saca)\s+(?:a\s+)?(?:los\s+|el\s+|tus\s+)?"
                           r"(?:drones?|enjambre)|drones|drones ya|enjambre|refuerzos|apoyo aereo|apoyo de drones)\b")
_RE_RETIRAR = re.compile(r"^(?:cobalt\s+)?(?:por favor\s+)?(?:(?:retira|retirar|recoge|guarda|quita|apaga|cancela)\s+(?:a\s+)?(?:los\s+|el\s+|tus\s+)?"
                         r"(?:drones?|enjambre)|drones fuera|fuera drones)\b")


def interpretar_enjambre(mensaje):
    """'deploy' / 'recall' / None."""
    f = _normalizar_frase(mensaje)
    if not f:
        return None
    if _RE_RETIRAR.search(f):
        return "recall"
    if _RE_DESPLEGAR.search(f):
        return "deploy"
    return None


def ordenes_por_chat(tipo, usuario):
    if tipo == "deploy":
        return [{"action": "deploy_drones", "target": usuario, "amount": 1, "material": "cualquiera", "movement_mode": "walk"}]
    if tipo == "recall":
        return [{"action": "recall_drones", "target": usuario, "amount": 1, "material": "cualquiera", "movement_mode": "walk",
                 "chat_message": "Retiro los drones."}]
    return []
