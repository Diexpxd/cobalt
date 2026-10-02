"""H4 (misión autónoma): comprensión del entorno. PURO: sin red, sin Minecraft, sin disco."""
import re
import unicodedata

import nox_mundo
import nox_voz
from nox_pro import _numero, distancia, entidades_de, hostiles, posicion

RADIO_HOSTILES = 24.0      # más lejos no cambia lo que hay que decidir ahora
RADIO_PELIGROS = 6.0
MAX_PROMPT = 420
MAX_MENSAJE_INFORME = 80
MAX_CHAT = nox_voz.MAX_CHAT

_TRAMPAS = {"tnt": "TNT expuesta", "tripwire": "un hilo trampa", "sculk_shrieker": "un sculk shrieker (invoca al Warden)", "pressure_plate": "una placa de presión",
            "cobweb": "una telaraña"}


def _limpio(texto, maximo=30):
    t = re.sub(r"[^\w '.\-]", " ", str(texto), flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()[:maximo].strip()


def _corto(recurso):
    return _limpio(str(recurso).split(":", 1)[-1].replace("_", " "))


def _bloques(d):
    return f"{int(round(d))} bloque" + ("" if int(round(d)) == 1 else "s")


def _vida(d):
    hp, mx = d.get("hp"), d.get("max_hp")
    if _numero(hp) and _numero(mx) and mx > 0:
        return hp, mx
    return None


def _hecho_jugador(gps):
    owner = gps.get("owner") if isinstance(gps, dict) else None
    if isinstance(owner, dict):
        if owner.get("alive") is False:
            return "El jugador ha muerto."
        partes = []
        yo, el = posicion(gps), posicion(owner)
        if yo and el:
            partes.append("a " + _bloques(distancia(yo, el)))
        v = _vida(owner)
        if v:
            partes.append(f"vida {v[0]:g}/{v[1]:g}" + (" (baja)" if v[0] / v[1] < 0.4 else ""))
        comida = owner.get("food")
        if _numero(comida) and 0 <= comida <= 8:
            partes.append(f"hambre {comida:g}/20")
        aire, max_aire = owner.get("air"), owner.get("max_air")
        if _numero(aire) and _numero(max_aire) and 0 < max_aire and aire <= 90 and aire < max_aire:
            partes.append("casi sin aire")
        if owner.get("on_fire") is True:
            partes.append("ardiendo")
        libres = owner.get("free_slots")
        if _numero(libres) and 0 <= libres <= 4:
            partes.append(f"inventario casi lleno ({libres:g} libres)")
        return "Jugador " + ", ".join(partes) + "." if partes else ""
    remoto = gps.get("owner_remote") if isinstance(gps, dict) else None
    if isinstance(remoto, dict) and remoto.get("dimension"):
        return f"El jugador está en otra dimensión ({_corto(remoto['dimension'])})."
    return ""


def _hecho_hostiles(entidades):
    vivo = isinstance(entidades, dict) and posicion(entidades.get("bot")) is not None
    cerca = sorted((e for e in hostiles(entidades) if _numero(e.get("dist")) and e["dist"] <= RADIO_HOSTILES), key=lambda e: e["dist"])
    if not cerca:
        return "Sin hostiles cerca." if vivo else ""
    e = cerca[0]
    nombre = _limpio(e.get("name") or "") or _corto(e.get("type", "hostil")) or "hostil"
    texto = f"Hostiles cerca: {len(cerca)} (el más cercano, {nombre} a {_bloques(e['dist'])})"
    extra = []
    if any("creeper" in str(x.get("type", "")).lower() for x in cerca):
        extra.append("hay un creeper")
    yendo = sum(1 for x in cerca if x.get("targets_player"))
    if yendo:
        extra.append(f"{yendo} va a por el jugador" if yendo == 1 else f"{yendo} van a por el jugador")
    return texto + (": " + ", ".join(extra) if extra else "") + "."


def _hecho_peligros(entidades):
    cerca = []
    for t in (entidades.get("hazards") if isinstance(entidades, dict) else None) or []:
        if isinstance(t, dict) and t.get("type") in _TRAMPAS and _numero(t.get("dist")) and t["dist"] <= RADIO_PELIGROS:
            cerca.append((t["dist"], t["type"]))
    if not cerca:
        return ""
    d, tipo = min(cerca)
    return f"Peligro junto a mí: {_TRAMPAS[tipo]} a {_bloques(d)}" + (f" (y {len(cerca) - 1} más)." if len(cerca) > 1 else ".")


def _hecho_propio(estado):
    v = _vida(estado) if isinstance(estado, dict) else None
    if v and v[0] / v[1] < 0.8:
        return f"Mi vida: {v[0]:g}/{v[1]:g}."
    return ""


def hechos(estado, gps, entidades):
    """Lista de hechos cortos (frases completas) sobre la situación; vacía si los sensores no dicen nada."""
    salida = []
    for f, args in ((_hecho_jugador, (gps,)), (_hecho_propio, (estado,)), (_hecho_hostiles, (entidades,)), (_hecho_peligros, (entidades,)),
                    (lambda g: nox_mundo.resumen(g), (gps,))):
        try:
            h = f(*args)
        except Exception:  # noqa: BLE001 - un sensor raro no debe tumbar el prompt
            h = ""
        if h:
            salida.append(h)
    return salida


def _juntar(lista, max_chars):
    texto = ""
    for h in lista:
        nuevo = (texto + " " + h) if texto else h
        if len(nuevo) > max_chars:
            break
        texto = nuevo
    return texto


def resumen_entorno(estado, gps, entidades, max_chars=MAX_PROMPT):
    """Texto para el prompt del modelo ('' si no hay nada que decir): una línea por hecho, con tope de tamaño por hechos enteros."""
    lineas, usado = [], 0
    for h in hechos(estado, gps, entidades):
        if usado + len(h) + 3 > max_chars:
            break
        lineas.append("- " + h)
        usado += len(h) + 3
    return "\n".join(lineas)


def informe_chat(estado, gps, entidades):
    """El informe en una frase para el chat ('' si no hay datos)."""
    return _juntar(hechos(estado, gps, entidades), MAX_CHAT)


_INFORME = re.compile(
    r"^(?:(?:dame|hazme|pasame|dime|quiero|necesito|cual es)\s+)?(?:(?:un|el|la|tu)\s+)?(?:informe|reporte|situacion|estado)(?:\s+de(?:l| la)?\s+(?:situacion|estado|zona|entorno))?$"
    r"|^(?:como|que tal)\s+(?:estamos|vamos|andamos|va todo|esta todo|estan las cosas|van las cosas)$"
    r"|^que\s+(?:hay|ves|tenemos)\s+(?:por aqui|alrededor|cerca)$"
    r"|^(?:hay|tenemos)\s+(?:peligro|amenazas|enemigos|hostiles)(?:\s+cerca)?$")


def _normalizar(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"\bcobalt\b|\bnox\b", " ", t)
    t = re.sub(r"[¿?¡!.,;:]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def pide_informe(mensaje):
    """¿El mensaje es SOLO una petición de informe de situación? Deliberadamente estricto: una frase larga que menciona la «situación» de otra cosa"""
    if len(str(mensaje or "")) > MAX_MENSAJE_INFORME:  # un informe se pide con pocas palabras; así ni se procesa un texto enorme
        return False
    t = _normalizar(mensaje)
    t = re.sub(r"\b(por favor|porfa|please|ahora|rapido)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return bool(t) and bool(_INFORME.match(t))


def responder_informe(estado, gps, entidades):
    """La respuesta al informe. Si los sensores no dicen nada, lo reconoce en vez de inventar."""
    texto = informe_chat(estado, gps, entidades)
    return texto or nox_voz.frase("sin_informe")
